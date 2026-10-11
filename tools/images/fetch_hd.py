# -*- coding: utf-8 -*-
"""高清候选图抓取（每味 10 张，全部 ≥800×600，自动裁掉纯色文字条）。

为什么这么写：
  · 抖音/快手/小红书的搜索页是 SPA，直接抓 HTML 拿不到图（实测 0 张）。
    但 360 图片接口的索引里本身就含大量字节跳动 CDN（pstatp/weili）图片，
    也就是短视频平台上的图，且**接口直接返回 width/height**，可以据此卡分辨率。
  · 接口里还有 downurl_true / downurl（原图）——优先取最大的那个，别拿缩略图充数。
  · 先按接口给的尺寸筛，再下载，再 PIL 复核真实像素；三层都过才算数（接口尺寸会说谎）。
  · 自动裁掉上下纯色条（短视频截图常见的黑边/白底字幕条），裁完仍保留原始备份信息。

输出:
  review/hd/<药名>_c01.jpg … _c10.jpg
  review/hd/index.json   {药名: [{file,w,h,src,title,site,trimmed}]}

用法:
  python tools/images/fetch_hd.py                      # 读 review/refetch_names.txt
  python tools/images/fetch_hd.py 黄芪 白术             # 指定药味
  python tools/images/fetch_hd.py --min 1000           # 提高长边门槛
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "hd")
NAMES_FILE = os.path.join(ROOT, "review", "refetch_names.txt")
INDEX = os.path.join(OUT, "index.json")
LOG = os.path.join(ROOT, "review", "fetch_hd.log")

WANT = 10
MIN_SHORT = 600          # 短边下限
MIN_LONG = 800           # 长边下限
MIN_BYTES = 60000        # 原图至少 60KB，滤掉压缩过度的

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

DROP_HOST = ("redocn", "699pic", "zcool", "58pic", "ooopic", "tukuppt", "51yuansu",
             "pngtree", "fr-trading", "huitu", "it168", "duitang", "sucai", "aigei",
             "51miz", "ztupic", "qiantucdn", "tukuchina")

DROP_TITLE = ("批发", "包邮", "价格", "报价", "旗舰", "专卖", "专营", "正品", "促销", "特价",
              "多少钱", "招商", "供应", "厂家", "淘宝", "天猫", "京东", "拼多多", "优惠券",
              "秒杀", "种植", "种苗", "亩产", "收购", "行情", "功效与作用", "禁忌", "怎么吃",
              "配方", "图片大全", "简笔画", "卡通", "矢量", "素材", "海报", "壁纸",
              "风景", "旅游", "景区", "酒店", "民宿", "美食", "菜谱", "做法",
              "同仁堂", "大药房", "药房直售", "药业", "饮片厂", "无硫", "打粉", "抓药",
              "现货", "直销", "直供", "克装", "袋装", "瓶装", "礼盒", "泡酒", "茶饮",
              "自营", "厂家直销")

# 电商 / 招商 / 企业信息站：图基本都是商品图或带价签的广告图。
# 实测 169 张候选里，京东 33、有赞 15、1688 8、淘宝 6 全是商品广告 ——
# 按「站点域名」拉黑比按图片内容判断准得多，也不会误伤薄片药材实拍。
DROP_SHOP = ("jd.com", "youzan.com", "1688.com", "taobao.com", "tmall.com",
             "yangkeduo.com", "pinduoduo.com", "suning.com", "vip.com",
             "hooos.com", "ymt.com", "aiqicha.baidu.com", "b2b.baidu.com",
             "qgyyzs.net", "maigoo.com", "5757.net", "book118.com",
             "ximalaya.com", "chinapp.com", "yiyaojd.com", "yaozs.com",
             "yaocai.com", "zgycsc.com", "5169.com")

# 易混药名：靠专用检索词把结果拉回中药（同名前缀会混进人物/地名/商品/别的动植物）
HINT = {
    "白头翁": ["白头翁 中药 根部", "白头翁 饮片 药材"],
    "两面针": ["两面针 中药 根 药材", "两面针 植物 叶"],
    "丁香": ["丁香 公丁香 花蕾 药材", "丁香 中药 饮片"],
    "沉香": ["沉香 药材 木块", "沉香 中药 饮片"],
    "檀香": ["檀香 原木 木材", "檀香 中药 药材"],
    "洋金花": ["洋金花 干燥花 中药"],
    "满山红": ["满山红 叶 中药 药材", "兴安杜鹃 叶"],
    "山慈菇": ["山慈菇 假鳞茎 药材"],
    "龙骨": ["龙骨 中药 化石 药材"],
    "龙齿": ["龙齿 中药 化石"],
    "竹沥": ["鲜竹沥 竹沥液"],
    "熊胆": ["熊胆粉 中药"],
    "牛黄": ["天然牛黄 药材"],
    "麝香": ["麝香仁 毛壳麝香 药材"],
    "阿胶": ["阿胶 胶块 中药"],
    "蜂蜜": ["蜂蜜 原蜜 蜂巢 特写"],
    "饴糖": ["饴糖 麦芽糖 块"],
    "冰片": ["冰片 龙脑 结晶"],
    "苏合香": ["苏合香 树脂 药材"],
    "血竭": ["血竭 树脂 药材"],
    "乳香": ["乳香 树脂 药材 颗粒"],
    "没药": ["没药 树脂 药材 颗粒"],
    "五倍子": ["五倍子 虫瘿 药材"],
    "雷丸": ["雷丸 菌核 药材"],
    "雷公藤": ["雷公藤 根 药材"],
    "猪苓": ["猪苓 菌核 药材"],
    "茯苓": ["茯苓 茯苓个 药材", "茯苓 饮片 白茯苓"],
    "海金沙": ["海金沙 孢子 药材"],
    "琥珀": ["琥珀 原石 矿石"],
    "自然铜": ["自然铜 黄铁矿 矿石"],
    "磁石": ["磁石 磁铁矿 矿石"],
    "代赭石": ["代赭石 赤铁矿 矿石"],
    "朱砂": ["朱砂 辰砂 矿石"],
    "雄黄": ["雄黄 矿石 块"],
    "硫黄": ["硫磺 结晶 块"],
    "白矾": ["白矾 明矾 结晶"],
    "炉甘石": ["炉甘石 矿石"],
    "硼砂": ["硼砂 结晶 月石"],
    "铅丹": ["铅丹 粉末 中药"],
    "升药": ["红升丹 升药"],
    "轻粉": ["轻粉 中药 粉末"],
    "砒石": ["砒石 矿石"],
    "胆矾": ["胆矾 硫酸铜 结晶"],
    "瓜蒂": ["甜瓜蒂 药材"],
    "常山": ["常山 根 中药 饮片"],
    "藜芦": ["藜芦 根 药材"],
    "矮地茶": ["矮地茶 紫金牛 全草"],
    "金荞麦": ["金荞麦 根茎 药材"],
    "白蔹": ["白蔹 根 药材"],
    "漏芦": ["漏芦 根 药材"],
    "四季青": ["四季青 叶 药材"],
    "地锦草": ["地锦草 全草 药材"],
    "铁苋菜": ["铁苋菜 全草 药材"],
    "翻白草": ["翻白草 全草 药材"],
    "椿皮": ["椿根皮 药材"],
    "臭梧桐": ["臭梧桐 叶 药材"],
    "海桐皮": ["海桐皮 刺桐皮 药材"],
    "千年健": ["千年健 根茎 药材"],
    "鹿衔草": ["鹿衔草 全草 药材"],
    "刀豆": ["刀豆 种子 药材"],
    "娑罗子": ["娑罗子 七叶树 种子"],
    "橘核": ["橘核 种子 药材"],
    "橘红": ["化橘红 药材"],
    "香橼": ["香橼 果实 药材"],
    "绿萼梅": ["绿萼梅 花蕾 药材"],
    "月季花": ["月季花 花蕾 干花"],
    "凌霄花": ["凌霄花 干燥花 药材"],
    "鸡冠花": ["鸡冠花 花序 药材"],
    "辛夷": ["辛夷 花蕾 药材"],
    "款冬花": ["款冬花 花蕾 药材"],
    "旋覆花": ["旋覆花 花序 药材"],
    "密蒙花": ["密蒙花 花蕾 药材"],
    "野菊花": ["野菊花 花序 药材"],
    "金银花": ["金银花 花蕾 药材"],
    "槐花": ["槐米 槐花 药材"],
    "蒲黄": ["蒲黄 花粉 药材"],
    "松花粉": ["松花粉 粉末 药材"],
    "车前子": ["车前子 种子 药材"],
    "菟丝子": ["菟丝子 种子 药材"],
    "沙苑子": ["沙苑子 种子 药材"],
    "决明子": ["决明子 种子 药材"],
    "青葙子": ["青葙子 种子 药材"],
    "茺蔚子": ["茺蔚子 种子 药材"],
    "鹤虱": ["鹤虱 果实 药材"],
    "榧子": ["香榧 种子 药材"],
    "南瓜子": ["南瓜子 种子 干燥"],
    "韭菜子": ["韭菜子 种子 药材"],
    "核桃仁": ["核桃仁 种仁 药材"],
    "酸枣仁": ["酸枣仁 种子 药材"],
    "柏子仁": ["柏子仁 种仁 药材"],
    "益智仁": ["益智仁 果实 药材"],
    "蛇床子": ["蛇床子 果实 药材"],
    "地肤子": ["地肤子 果实 药材"],
    "川楝子": ["川楝子 果实 药材"],
    "栀子": ["栀子 果实 药材"],
    "使君子": ["使君子 果实 药材"],
    "鸦胆子": ["鸦胆子 果实 药材"],
    "马兜铃": ["马兜铃 果实 药材"],
    "巴豆霜": ["巴豆霜 粉末 中药"],
    "千金子": ["千金子 续随子 种子"],
    "京大戟": ["京大戟 根 药材"],
    "甘遂": ["甘遂 根 药材"],
    "芫花": ["芫花 花蕾 药材"],
    "商陆": ["商陆 根 饮片"],
    "穿山甲": ["穿山甲 鳞片 甲片"],
    "水牛角": ["水牛角 角 刨片"],
    "山羊角": ["山羊角 角 药材"],
    "羚羊角": ["羚羊角 角 药材"],
    "鹿角": ["鹿角 药材 角"],
    "鹿茸": ["鹿茸 切片 药材"],
    "鹿角霜": ["鹿角霜 药材"],
    "珍珠母": ["珍珠母 贝壳 药材"],
    "牡蛎": ["牡蛎 贝壳 药材"],
    "石决明": ["石决明 鲍鱼壳 药材"],
    "瓦楞子": ["瓦楞子 毛蚶 壳"],
    "海蛤壳": ["蛤壳 药材 贝壳"],
    "海螵蛸": ["海螵蛸 乌贼骨 药材"],
    "桑螵蛸": ["桑螵蛸 卵鞘 药材"],
    "蝉蜕": ["蝉蜕 药材 蝉衣"],
    "僵蚕": ["白僵蚕 药材"],
    "土鳖虫": ["土鳖虫 地鳖 药材"],
    "虻虫": ["虻虫 牛虻 药材"],
    "斑蝥": ["斑蝥 芫菁 药材"],
    "蜈蚣": ["蜈蚣 干燥 药材"],
    "全蝎": ["全蝎 蝎子 药材"],
    "水蛭": ["水蛭 蚂蟥 药材"],
    "地龙": ["地龙 蚯蚓 药材"],
    "九香虫": ["九香虫 药材"],
    "蝼蛄": ["蝼蛄 药材"],
    "蚕沙": ["蚕沙 蚕粪 药材"],
    "五灵脂": ["五灵脂 药材"],
    "夜明砂": ["夜明砂 药材"],
    "紫河车": ["紫河车 药材"],
    "海狗肾": ["海狗肾 药材"],
    "鸡内金": ["鸡内金 药材"],
    "刺猬皮": ["刺猬皮 药材"],
    "乌梢蛇": ["乌梢蛇 干燥 药材"],
    "蕲蛇": ["蕲蛇 五步蛇 药材"],
    "金钱白花蛇": ["金钱白花蛇 药材"],
    "蜂房": ["露蜂房 蜂巢 药材"],
    "青蒿": ["青蒿 全草 药材"],
    "淡竹叶": ["淡竹叶 全草 药材"],
    "紫苏叶": ["紫苏叶 药材"],
    "紫苏梗": ["紫苏梗 药材"],
    "生地黄": ["生地黄 饮片 药材"],
    "熟地黄": ["熟地黄 饮片 药材"],
    "赤芍": ["赤芍 饮片 药材"],
    "白芍": ["白芍 饮片 药材"],
    "白术": ["白术 饮片 药材"],
    "苍术": ["苍术 饮片 药材"],
    "茯苓": ["茯苓 饮片 药材"],
    "泽泻": ["泽泻 饮片 药材"],
    "干姜": ["干姜 饮片 药材"],
    "炮姜": ["炮姜 饮片 药材"],
    "生姜": ["生姜 鲜姜 药材"],
    "大蓟": ["大蓟 全草 药材"],
    "小蓟": ["小蓟 全草 药材"],
    "茜草": ["茜草 根 药材"],
    "棕榈炭": ["棕榈炭 药材"],
    "血余炭": ["血余炭 药材"],
    "侧柏叶": ["侧柏叶 药材"],
    "白茅根": ["白茅根 药材"],
    "苎麻根": ["苎麻根 药材"],
    "仙鹤草": ["仙鹤草 全草 药材"],
    "艾叶": ["艾叶 药材"],
    "三棱": ["三棱 饮片 药材"],
    "莪术": ["莪术 饮片 药材"],
    "姜黄": ["姜黄 饮片 药材"],
    "郁金": ["郁金 饮片 药材"],
    "川芎": ["川芎 饮片 药材"],
    "乳香": ["乳香 药材 颗粒"],
    "桃仁": ["桃仁 种子 药材"],
    "骨碎补": ["骨碎补 药材"],
    "续断": ["续断 饮片 药材"],
    "天南星": ["天南星 块茎 药材"],
    "白附子": ["白附子 块茎 药材"],
    "芥子": ["芥子 种子 药材"],
    "川贝母": ["川贝母 药材 松贝"],
    "浙贝母": ["浙贝母 药材 大贝"],
    "瓜蒌": ["瓜蒌 果实 药材"],
    "前胡": ["前胡 根 药材"],
    "昆布": ["昆布 海带 药材"],
    "百部": ["百部 块根 药材"],
    "紫菀": ["紫菀 根 药材"],
    "桑白皮": ["桑白皮 药材"],
    "葶苈子": ["葶苈子 种子 药材"],
    "远志": ["远志 根皮 药材"],
    "石菖蒲": ["石菖蒲 根茎 药材"],
    "太子参": ["太子参 药材"],
    "仙茅": ["仙茅 根茎 药材"],
    "肉苁蓉": ["肉苁蓉 药材"],
    "补骨脂": ["补骨脂 果实 药材"],
    "冬虫夏草": ["冬虫夏草 药材"],
    "当归": ["当归 饮片 药材"],
    "龙眼肉": ["龙眼肉 桂圆肉 药材"],
    "北沙参": ["北沙参 药材"],
    "南沙参": ["南沙参 药材"],
    "天冬": ["天冬 天门冬 药材"],
    "黄精": ["黄精 药材 饮片"],
    "女贞子": ["女贞子 果实 药材"],
    "肉豆蔻": ["肉豆蔻 果实 药材"],
    "赤石脂": ["赤石脂 矿石 药材"],
    "金樱子": ["金樱子 果实 药材"],
    "重楼": ["重楼 七叶一枝花 根茎"],
    "草乌": ["草乌 药材 根"],
    "川乌": ["川乌 药材 根"],
    "海金沙": ["海金沙 孢子 药材"],
    "虎杖": ["虎杖 根茎 药材"],
    "吴茱萸": ["吴茱萸 果实 药材"],
    "胡椒": ["胡椒 白胡椒 黑胡椒"],
    "麦芽": ["麦芽 大麦芽 药材"],
    "莱菔子": ["莱菔子 种子 药材"],
    "蛇床子": ["蛇床子 果实 药材"],
}

TERMS = ["中药饮片 高清", "中药材 实物 高清", "药材 特写 高清", "中药 药材 图片"]


def load_names():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        return args
    with io.open(NAMES_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def api(q, sn=0, pn=30):
    url = ("https://image.so.com/j?q=" + urllib.parse.quote(q) +
           "&src=srp&sn=%d&pn=%d" % (sn, pn))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/",
        "Accept": "application/json, text/plain, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def download(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA,
                                             "Referer": "https://image.so.com/"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def _solid_band(g, w, h, from_top, max_frac=0.22, frac=0.80, tol=16):
    """从顶部/底部往里看，连续的「纯色条」有多少像素（文字条通常底色占 80%+）"""
    px = g.load()
    step = max(1, w // 80)
    limit = int(h * max_frac)
    n = 0
    while n < limit:
        y = n if from_top else (h - 1 - n)
        vals = [px[x, y] for x in range(0, w, step)]
        vals.sort()
        med = vals[len(vals) // 2]
        hit = sum(1 for v in vals if abs(v - med) <= tol)
        if hit < frac * len(vals):
            break
        n += 1
    return n


def trim_bars(im):
    """裁掉上下纯色条（黑边/白底字幕条），保守：最多各裁 22%，且至少保留 60% 高度"""
    w, h = im.size
    g = im.convert("L")
    top = _solid_band(g, w, h, True)
    bot = _solid_band(g, w, h, False)
    if top + bot < 10:
        return im, False
    if h - top - bot < h * 0.60:
        return im, False
    return im.crop((0, top, w, h - bot)), True


def process(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode in ("P", "LA", "RGBA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im2 = im.convert("RGBA")
        bg.paste(im2, mask=im2.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    im, trimmed = trim_bars(im)
    if max(im.size) > 1600:
        k = 1600.0 / max(im.size)
        im = im.resize((max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue(), im.size, trimmed


def parse_size(v):
    """接口的 imgsize 可能是 3782（字节）或 '3782KB' 这种字符串，统一成字节"""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().upper().replace(" ", "")
    k = 1
    if s.endswith("KB"):
        k, s = 1024, s[:-2]
    elif s.endswith("MB"):
        k, s = 1048576, s[:-2]
    elif s.endswith("B"):
        s = s[:-1]
    try:
        return int(float(s) * k)
    except ValueError:
        return 0


def candidates(name, min_long, enough=54, relaxed=False):
    """先按接口给的尺寸筛，返回 (url, w, h, title, site) 列表（不下载）。

    够 enough 条就收工，别把 8 个检索词 × 3 页全跑完——那是纯浪费配额和时间。
    relaxed=True 供「补货」用：放宽到允许电商站，但标题里的广告词仍然拦，
    并追加更"实物"的检索词（特写/原植物/干燥品），避免补回来的还是广告。
    """
    out, seen = [], set()
    terms = list(HINT.get(name, [])) + ["%s %s" % (name, t) for t in TERMS]
    if relaxed:
        terms += ["%s 特写 实物" % name, "%s 原植物 干燥" % name,
                  "%s 干燥品 药材" % name, "%s 高清 实拍" % name]

    # 检索页并发拿：串行 8 词 × 2 页要 30 秒以上，并发后只要几秒
    jobs = [(t, sn) for t in terms for sn in (0, 30)]

    def get(job):
        term, sn = job
        try:
            return api(term, sn, 30).get("list") or []
        except Exception:
            return []

    items = []
    with ThreadPoolExecutor(max_workers=14) as ex:
        for lst in ex.map(get, jobs):
            items.extend(lst)

    for it in items:
        w = int(it.get("width") or 0)
        h = int(it.get("height") or 0)
        title = it.get("title") or ""
        if min(w, h) < MIN_SHORT or max(w, h) < min_long:
            continue
        if not (0.55 <= (float(w) / h if h else 0) <= 1.9):
            continue
        if 0 < parse_size(it.get("imgsize")) < MIN_BYTES // 2:
            continue
        if any(b in title for b in DROP_TITLE):
            continue
        # 站点拉黑要同时看「图片来源页」(link/site)，商品图常常托管在 CDN 上，
        # 单看图片 URL 的域名是认不出来的。
        page = "%s %s" % (it.get("link") or "", it.get("site") or "")
        if not relaxed and any(b in page.lower() for b in DROP_SHOP):
            continue
        if name not in title and name not in (it.get("litetitle") or ""):
            continue
        # 原图优先
        urls = [it.get("downurl_true"), it.get("downurl"), it.get("img"), it.get("thumb")]
        u = next((x for x in urls if x and x.startswith("http")), "")
        if not u:
            continue
        host = ""
        try:
            host = urllib.parse.urlparse(u).netloc.lower()
        except Exception:
            pass
        if any(b in host for b in DROP_HOST):
            continue
        if not relaxed and any(b in host for b in DROP_SHOP):
            continue
        key = u.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        out.append((u, w, h, title, it.get("site") or host))
    out.sort(key=lambda r: -max(r[1], r[2]))
    return out


def fetch_one(name, min_long, idx, relaxed=False, base=None):
    """先拿到足够的候选 URL，再并行下载 + 复核分辨率。

    base：已有的候选（补货时传入），新抓到的会**接在后面**，不会把好的挤掉。
    """
    base = list(base or [])
    need = WANT - len(base)
    if need <= 0:
        return base
    cands = candidates(name, min_long, relaxed=relaxed)
    if not cands:
        return base
    meta = list(base)
    have_urls = set((m.get("src") or "").split("?")[0] for m in base)

    def work(item):
        u, w, h, title, site = item
        try:
            raw = download(u)
        except Exception:
            return None
        if len(raw) < MIN_BYTES // 2:
            return None
        try:
            jpg, size, trimmed = process(raw)
        except Exception:
            return None
        if min(size) < MIN_SHORT or max(size) < min_long:
            return None
        return (jpg, size, trimmed, u, title, site)

    # 多下一些候选（有些会不合格），并跳过已有的同一张图
    pool = [c for c in cands if (c[0].split("?")[0] not in have_urls)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(work, pool[:max(WANT * 4, need * 4)]):
            if len(meta) >= WANT:
                break
            if res is None:
                continue
            jpg, size, trimmed, u, title, site = res
            fn = "%s_c%02d.jpg" % (name, len(meta) + 1)
            with io.open(os.path.join(OUT, fn), "wb") as f:
                f.write(jpg)
            meta.append({"file": fn, "w": size[0], "h": size[1], "src": u,
                         "title": title[:60], "site": site, "trimmed": trimmed})
    return meta


def purge_bad_hosts():
    """把已经抓下来、但来源是电商/招商站的候选删掉，让主循环重新补货。

    index.json 里记了 src（图片直链）和 site（来源站），两者任一命中黑名单就删。
    """
    if not os.path.exists(INDEX):
        print("还没有 index.json，无需清理")
        return 0
    idx = json.load(io.open(INDEX, encoding="utf-8"))
    removed = 0
    for name in list(idx.keys()):
        keep = []
        for m in idx[name]:
            blob = ("%s %s %s" % (m.get("src") or "", m.get("site") or "",
                                  m.get("title") or "")).lower()
            if any(b in blob for b in DROP_SHOP):
                p = os.path.join(OUT, m["file"])
                if os.path.exists(p):
                    os.remove(p)
                removed += 1
            else:
                keep.append(m)
        # 重新编号，保证列号连续（用户是按列号报的）
        for i, m in enumerate(keep, 1):
            old = m["file"]
            new = "%s_c%02d.jpg" % (name, i)
            if old != new and os.path.exists(os.path.join(OUT, old)):
                os.rename(os.path.join(OUT, old), os.path.join(OUT, new))
            m["file"] = new
        idx[name] = keep
    with io.open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print("清掉 %d 张电商/广告图，%d 味需要补货" %
          (removed, sum(1 for v in idx.values() if len(v) < WANT)))
    return removed


def log(msg):
    print(msg, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def main():
    names = load_names()
    min_long = MIN_LONG
    for a in sys.argv[1:]:
        if a.startswith("--min"):
            min_long = int(a.split("=")[-1]) if "=" in a else MIN_LONG
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    if "--purge" in sys.argv:
        purge_bad_hosts()
        return 0
    idx = {}
    if os.path.exists(INDEX):
        try:
            idx = json.load(io.open(INDEX, encoding="utf-8"))
        except Exception:
            idx = {}
    log("=== 高清抓图开始 %d 味，门槛 ≥%dx%d，%s" %
        (len(names), MIN_SHORT, min_long, time.strftime("%Y-%m-%d %H:%M:%S")))
    short = []
    topup = "--topup" in sys.argv
    for i, name in enumerate(names, 1):
        if not topup and len(idx.get(name) or []) >= WANT and all(
                os.path.exists(os.path.join(OUT, m["file"])) for m in idx[name]):
            continue
        if topup and len(idx.get(name) or []) >= WANT:
            continue
        # 已有候选一律保留、新抓的接在后面 —— 这样「第 N 列」的编号永远稳定，
        # 用户中途挑好的结果不会因为我再补一批图而错位。
        meta = fetch_one(name, min_long, idx, relaxed=topup, base=idx.get(name))
        idx[name] = meta
        if len(meta) < WANT:
            short.append("%s(%d)" % (name, len(meta)))
        log("[%3d/%d] %-8s %2d 张  最小 %s" %
            (i, len(names), name, len(meta),
             min(("%dx%d" % (m["w"], m["h"]) for m in meta), default="-")))
        with io.open(INDEX, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
    log("=== 完成：不足 %d 张的 %d 味 %s" % (WANT, len(short), " ".join(short)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
