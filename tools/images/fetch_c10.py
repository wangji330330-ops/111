# -*- coding: utf-8 -*-
"""批量抓候选图（每味 10 张），供人工挑选。

输出: review/c10/<药名>_c01.jpg ... _c10.jpg

设计要点（吃过亏的地方）：
  · 360 图片接口（Bing 会当机器人拦掉）；
  · 标题里必须出现药名，否则会混进“同名人物/地名/商品”（曾把川乌抓成蒋介石）；
  · 拉黑一图多站的设计素材站与广告标题；
  · 对易混药名给专门的检索词（如「白头翁」也是鸟、「两面针」也是牙膏品牌、
    「丁香」也是丁香花、「沉香」也是电视剧），靠后缀把结果拉回中药；
  · 断点续抓：已有 10 张的药味直接跳过，重跑不会白干。

用法:
  python tools/images/fetch_c10.py                # 读取 review/refetch_names.txt
  python tools/images/fetch_c10.py 麻黄 桂枝       # 指定药味
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "c10")
NAMES_FILE = os.path.join(ROOT, "review", "refetch_names.txt")
LOG = os.path.join(ROOT, "review", "fetch_c10.log")
WANT = 10

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

DROP_HOST = ("redocn", "699pic", "zcool", "58pic", "ooopic", "tukuppt", "51yuansu",
             "pngtree", "fr-trading", "huitu", "51yuansu", "it168", "duitang")

DROP_TITLE = ("批发", "包邮", "价格", "报价", "旗舰店", "专卖", "促销", "特价", "多少钱",
              "招商", "供应", "厂家", "药店", "淘宝", "天猫", "京东", "拼多多", "优惠券",
              "种植", "种苗", "种子价格", "亩产", "收购", "行情", "功效与作用", "禁忌",
              "怎么吃", "配方", "图片大全", "简笔画", "卡通", "矢量", "素材", "海报", "壁纸")

# 易混药名的专用检索词（优先级从高到低）
HINT = {
    "白头翁": ["白头翁 中药 根", "白头翁 饮片", "白头翁 植物 药材"],
    "两面针": ["两面针 中药 根", "两面针 药材 饮片", "两面针 植物"],
    "丁香": ["丁香 公丁香 药材", "丁香 花蕾 中药", "丁香 饮片"],
    "沉香": ["沉香 药材 木", "沉香 中药 饮片", "沉香 香料 原材"],
    "檀香": ["檀香 木材 原木", "檀香 中药 药材", "檀香 檀木"],
    "洋金花": ["洋金花 干燥花 中药", "洋金花 曼陀罗花 药材"],
    "满山红": ["满山红 中药 叶", "满山红 兴安杜鹃 药材"],
    "山慈菇": ["山慈菇 中药 药材", "山慈菇 饮片 假鳞茎"],
    "龙骨": ["龙骨 中药 化石", "龙骨 药材 饮片"],
    "龙齿": ["龙齿 中药 化石"],
    "竹沥": ["竹沥 竹沥液 中药", "竹沥 鲜竹沥"],
    "熊胆": ["熊胆粉 中药", "熊胆 干燥胆囊"],
    "牛黄": ["牛黄 天然牛黄 药材", "牛黄 中药"],
    "麝香": ["麝香 中药材 麝香仁", "麝香 毛壳麝香"],
    "阿胶": ["阿胶 胶块 中药", "阿胶 驴皮胶"],
    "鹿角胶": ["鹿角胶 胶块 中药"],
    "龟甲胶": ["龟甲胶 胶块 中药"],
    "蜂蜜": ["蜂蜜 原蜜 蜂巢", "蜂蜜 中药 药材"],
    "饴糖": ["饴糖 麦芽糖 块", "饴糖 中药"],
    "冰片": ["冰片 龙脑 结晶", "冰片 中药"],
    "苏合香": ["苏合香 树脂 中药"],
    "安息香": ["安息香 树脂 中药"],
    "血竭": ["血竭 树脂 中药", "血竭 龙血竭"],
    "乳香": ["乳香 树脂 中药", "乳香 滴乳香"],
    "没药": ["没药 树脂 中药", "没药 天然没药"],
    "儿茶": ["儿茶 中药 提取物", "孩儿茶 药材"],
    "五倍子": ["五倍子 虫瘿 中药", "五倍子 角倍"],
    "雷丸": ["雷丸 菌核 中药"],
    "雷公藤": ["雷公藤 根 药材", "雷公藤 植物"],
    "猪苓": ["猪苓 菌核 中药"],
    "茯苓": ["茯苓 茯苓个 药材", "茯苓 饮片 白茯苓"],
    "海金沙": ["海金沙 孢子 中药", "海金沙 药材"],
    "琥珀": ["琥珀 原石 中药", "琥珀 药材"],
    "自然铜": ["自然铜 黄铁矿 药材", "自然铜 矿物 中药"],
    "磁石": ["磁石 磁铁矿 药材", "磁石 矿物 中药"],
    "代赭石": ["代赭石 赤铁矿 药材"],
    "朱砂": ["朱砂 辰砂 矿物", "朱砂 中药 药材"],
    "雄黄": ["雄黄 矿物 中药", "雄黄 块"],
    "硫黄": ["硫黄 硫磺 块", "硫黄 中药"],
    "白矾": ["白矾 明矾 结晶", "白矾 中药"],
    "炉甘石": ["炉甘石 矿物 中药"],
    "硼砂": ["硼砂 结晶 中药", "硼砂 月石"],
    "铅丹": ["铅丹 四氧化三铅 中药"],
    "升药": ["升药 红升丹 中药", "升药 升丹"],
    "轻粉": ["轻粉 甘汞 中药"],
    "砒石": ["砒石 砒霜 矿物"],
    "胆矾": ["胆矾 硫酸铜 结晶"],
    "瓜蒂": ["瓜蒂 甜瓜蒂 中药"],
    "常山": ["常山 中药 根", "常山 饮片"],
    "藜芦": ["藜芦 中药 根", "藜芦 药材"],
    "洋金花": ["洋金花 干燥花 中药"],
    "矮地茶": ["矮地茶 紫金牛 中药", "矮地茶 药材"],
    "金荞麦": ["金荞麦 根茎 中药"],
    "白蔹": ["白蔹 中药 根", "白蔹 饮片"],
    "漏芦": ["漏芦 中药 根", "漏芦 饮片"],
    "四季青": ["四季青 叶 中药"],
    "地锦草": ["地锦草 中药 全草", "地锦草 药材"],
    "铁苋菜": ["铁苋菜 中药 全草"],
    "翻白草": ["翻白草 中药 全草"],
    "椿皮": ["椿皮 椿根皮 中药"],
    "臭梧桐": ["臭梧桐 叶 中药", "臭梧桐 海州常山"],
    "海桐皮": ["海桐皮 刺桐皮 中药"],
    "千年健": ["千年健 根茎 中药"],
    "鹿衔草": ["鹿衔草 中药 全草"],
    "两面针": ["两面针 中药 根"],
    "刀豆": ["刀豆 成熟种子 中药", "刀豆 药材"],
    "娑罗子": ["娑罗子 七叶树 种子"],
    "橘核": ["橘核 橘子核 中药", "橘核 饮片"],
    "橘红": ["橘红 化橘红 中药"],
    "香橼": ["香橼 果实 中药", "香橼 饮片"],
    "绿萼梅": ["绿萼梅 花蕾 中药", "绿萼梅 白梅花"],
    "玫瑰花": ["玫瑰花 花蕾 中药", "玫瑰花 干花"],
    "月季花": ["月季花 花蕾 中药", "月季花 干花"],
    "凌霄花": ["凌霄花 干燥花 中药"],
    "鸡冠花": ["鸡冠花 花序 中药"],
    "辛夷": ["辛夷 花蕾 中药"],
    "款冬花": ["款冬花 花蕾 中药"],
    "旋覆花": ["旋覆花 头状花序 中药"],
    "密蒙花": ["密蒙花 花蕾 中药"],
    "野菊花": ["野菊花 头状花序 中药"],
    "菊花": ["菊花 杭白菊 药材"],
    "金银花": ["金银花 忍冬 花蕾"],
    "槐花": ["槐花 花蕾 中药", "槐米 槐花"],
    "蒲黄": ["蒲黄 花粉 中药"],
    "松花粉": ["松花粉 中药"],
    "海金沙": ["海金沙 孢子 中药"],
    "车前子": ["车前子 种子 中药"],
    "菟丝子": ["菟丝子 种子 中药"],
    "沙苑子": ["沙苑子 种子 中药"],
    "决明子": ["决明子 种子 中药"],
    "青葙子": ["青葙子 种子 中药"],
    "茺蔚子": ["茺蔚子 种子 中药"],
    "鹤虱": ["鹤虱 果实 中药"],
    "榧子": ["榧子 香榧 种子"],
    "南瓜子": ["南瓜子 种子 干燥"],
    "韭菜子": ["韭菜子 种子 中药"],
    "核桃仁": ["核桃仁 种仁 中药"],
    "酸枣仁": ["酸枣仁 种子 中药"],
    "柏子仁": ["柏子仁 种仁 中药"],
    "益智仁": ["益智仁 果实 中药"],
    "蛇床子": ["蛇床子 果实 中药"],
    "地肤子": ["地肤子 果实 中药"],
    "川楝子": ["川楝子 果实 中药"],
    "栀子": ["栀子 果实 中药"],
    "使君子": ["使君子 果实 中药", "使君子 君子仁"],
    "鸦胆子": ["鸦胆子 果实 中药"],
    "马兜铃": ["马兜铃 果实 中药"],
    "巴豆霜": ["巴豆霜 中药 粉末"],
    "千金子": ["千金子 续随子 种子"],
    "京大戟": ["京大戟 大戟 根"],
    "甘遂": ["甘遂 根 中药"],
    "芫花": ["芫花 花蕾 中药"],
    "商陆": ["商陆 根 饮片", "商陆 药材"],
    "穿山甲": ["穿山甲 鳞片 中药", "穿山甲 甲片"],
    "水牛角": ["水牛角 角 中药", "水牛角 刨片"],
    "山羊角": ["山羊角 角 中药"],
    "羚羊角": ["羚羊角 角 中药", "赛加羚羊角"],
    "鹿角": ["鹿角 梅花鹿 角", "鹿角 药材"],
    "鹿茸": ["鹿茸 药材 切片"],
    "鹿角霜": ["鹿角霜 中药"],
    "珍珠母": ["珍珠母 贝壳 中药"],
    "牡蛎": ["牡蛎 贝壳 中药", "生牡蛎 药材"],
    "石决明": ["石决明 鲍鱼壳 中药"],
    "瓦楞子": ["瓦楞子 毛蚶 壳"],
    "海蛤壳": ["海蛤壳 蛤壳 中药"],
    "海螵蛸": ["海螵蛸 乌贼骨 中药"],
    "桑螵蛸": ["桑螵蛸 卵鞘 中药"],
    "蝉蜕": ["蝉蜕 蝉衣 中药"],
    "僵蚕": ["僵蚕 白僵蚕 中药"],
    "僵蛹": ["僵蛹 中药"],
    "土鳖虫": ["土鳖虫 地鳖 中药"],
    "虻虫": ["虻虫 牛虻 中药"],
    "斑蝥": ["斑蝥 芫菁 中药"],
    "蜈蚣": ["蜈蚣 药材 干燥", "蜈蚣 中药"],
    "全蝎": ["全蝎 蝎子 药材", "全蝎 中药"],
    "水蛭": ["水蛭 蚂蟥 药材", "水蛭 中药"],
    "地龙": ["地龙 蚯蚓 药材", "地龙 中药"],
    "九香虫": ["九香虫 椿象 中药"],
    "蝼蛄": ["蝼蛄 中药"],
    "蚕沙": ["蚕沙 蚕屎 中药"],
    "五灵脂": ["五灵脂 鼯鼠 粪便", "五灵脂 中药"],
    "夜明砂": ["夜明砂 蝙蝠粪 中药"],
    "紫河车": ["紫河车 中药 干燥"],
    "海狗肾": ["海狗肾 中药"],
    "鸡内金": ["鸡内金 中药"],
    "刺猬皮": ["刺猬皮 中药"],
    "乌梢蛇": ["乌梢蛇 药材 干燥"],
    "蕲蛇": ["蕲蛇 五步蛇 药材"],
    "金钱白花蛇": ["金钱白花蛇 药材"],
    "蛇蜕": ["蛇蜕 中药"],
    "蜂蜜": ["蜂蜜 原蜜 蜂巢"],
    "蜂房": ["蜂房 蜂巢 中药", "露蜂房 药材"],
    "蜂蜜 ": ["蜂蜜 原蜜"],
}

TERM_SUFFIX = ["中药饮片", "中药材 实物", "药材 特写", "中药 药材图片"]


def load_names():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        return args
    with io.open(NAMES_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def api(q, pn=0, rn=30):
    url = ("https://image.so.com/j?q=" + urllib.parse.quote(q) +
           "&src=srp&sn=%d&pn=%d" % (pn, rn))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/",
        "Accept": "application/json, text/plain, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def download(u):
    req = urllib.request.Request(u, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def process(data, max_side=520):
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode in ("P", "LA", "RGBA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im2 = im.convert("RGBA")
        bg.paste(im2, mask=im2.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if max(w, h) > max_side:
        k = float(max_side) / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return buf.getvalue(), im.size


def log(msg):
    print(msg)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def terms_for(name):
    ts = list(HINT.get(name, []))
    for suf in TERM_SUFFIX:
        ts.append("%s %s" % (name, suf))
    return ts


def fetch_one(name):
    got, seen_urls = 0, set()
    for term in terms_for(name):
        if got >= WANT:
            break
        for pn in (0, 30):
            if got >= WANT:
                break
            try:
                j = api(term, pn, 30)
            except Exception as e:
                log("  ! api fail %s: %s" % (name, e))
                break
            for it in (j.get("list") or []):
                if got >= WANT:
                    break
                u = it.get("img") or it.get("thumb") or ""
                title = it.get("title") or ""
                if not u.startswith("http") or u in seen_urls:
                    continue
                seen_urls.add(u)
                host = ""
                try:
                    host = urllib.parse.urlparse(u).netloc.lower()
                except Exception:
                    pass
                if any(b in host for b in DROP_HOST):
                    continue
                if any(b in title for b in DROP_TITLE):
                    continue
                if name not in title:
                    continue
                try:
                    raw = download(u)
                except Exception:
                    continue
                if len(raw) < 6000:
                    continue
                try:
                    jpg, size = process(raw)
                except Exception:
                    continue
                if size[0] < 240 or size[1] < 180:
                    continue
                got += 1
                fn = "%s_c%02d.jpg" % (name, got)
                with io.open(os.path.join(OUT, fn), "wb") as f:
                    f.write(jpg)
            time.sleep(0.25)
    return got


def main():
    names = load_names()
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    log("=== 开始抓图 %d 味（每味目标 %d 张）%s" %
        (len(names), WANT, time.strftime("%Y-%m-%d %H:%M:%S")))
    done, short = 0, []
    for i, name in enumerate(names, 1):
        have = len([f for f in os.listdir(OUT)
                    if f.startswith(name + "_c") and f.endswith(".jpg")])
        if have >= WANT:
            done += 1
            continue
        n = fetch_one(name)
        done += 1
        if n < WANT:
            short.append("%s(%d)" % (name, n))
        log("[%3d/%d] %-8s 抓到 %d 张%s" %
            (i, len(names), name, n, "  ← 不足" if n < WANT else ""))
    log("=== 完成：%d 味，其中不足 %d 张的 %d 味 %s" %
        (done, WANT, len(short), " ".join(short)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
