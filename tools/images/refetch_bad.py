# -*- coding: utf-8 -*-
"""按“严格模式”重抓指定药物的图片：删掉旧图，只用可信来源，并做内容特征过滤。

用法：
  python refetch_bad.py 蒲公英 青黛 生地黄 ...        # 指定药名
  python refetch_bad.py --file review/badlist.txt     # 从文件读（每行一个药名）
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

# 严格模式下排除的可疑来源关键词（标题/来源页里出现就跳过）
STRICT_BAD_TITLE = (
    "函数", "公式", "图像", "曲线", "图表", "流程图", "框图", "示意", "结构图",
    "书法", "字帖", "毛笔", "字典", "汉字", "拼音", "笔画", "偏旁",
    "logo", "标志", "字体", "水墨", "剪纸", "卡通", "漫画", "表情包",
    "壁纸", "风景", "旅游", "海报", "宣传", "广告", "包装", "礼盒",
    "价格", "行情", "种植技术", "栽培技术", "视频", "教程", "课件", "ppt",
    "股票", "理财", "财经", "游戏", "动漫", "美女", "头像", "壁纸",
)
STRICT_BAD_HOST = (
    "zcool", "logo", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt",
    "ziti", "font", "shufazidian", "guoxuedashi", "hanyu", "zdic", "cidian",
    "baike.baidu.com/pic", "tieba", "zhihu", "douban", "bilibili",
    "pexels", "unsplash", "pixabay", "freepik", "dreamstime", "shutterstock",
    "wallpaper", "desktoppr", "toutiao", "ixigua",
)
# 期望出现的“中药/植物”类关键词（加分）
STRICT_GOOD_TITLE = (
    "饮片", "药材", "中药", "炮制", "生品", "制品", "切片", "干燥", "植物",
    "herb", "中药学", "药典", "本草", "叶", "根", "茎", "花", "果实", "种子",
    "医学百科", "百科", "性状", "鉴别",
)


def strict_score(c):
    s = F.score(c)
    t = ((c.get("title") or "") + " " + (c.get("page") or "")).lower()
    h = F.host_of(c["url"])
    for w in STRICT_BAD_TITLE:
        if w in t:
            s -= 80
    for w in STRICT_BAD_HOST:
        if w in h:
            s -= 80
    for w in STRICT_GOOD_TITLE:
        if w in t:
            s += 12
    return s


def content_ok(path, name):
    """内容特征校验：排除白底图表、纯色块、近灰度、动漫色块等"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w < 220 or h < 170:
        return False, "尺寸过小"
    small = im.resize((64, 64))
    px = list(small.getdata())
    white = sum(1 for (r, g, b) in px if r > 236 and g > 236 and b > 236) / 4096.0
    q = set()
    sat = 0.0
    for (r, g, b) in px:
        q.add((r >> 5, g >> 5, b >> 5))
        mx, mn = max(r, g, b), min(r, g, b)
        sat += 0.0 if mx == 0 else (mx - mn) / float(mx)
    sat /= 4096.0
    from collections import Counter
    top = Counter((r >> 4, g >> 4, b >> 4) for (r, g, b) in px).most_common(1)[0][1] / 4096.0
    gray = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in px]
    edges = 0
    for y in range(64):
        for x in range(63):
            i = y * 64 + x
            if abs(gray[i] - gray[i + 1]) > 30:
                edges += 1
    edge = edges / (64.0 * 63)
    if len(q) <= 100 and white > 0.55:
        return False, "白底图表/公式"
    if top > 0.68:
        return False, "纯色块过多"
    if edge < 0.010 and len(q) < 120:
        return False, "几乎无纹理"
    if sat < 0.05 and len(q) < 110:
        return False, "近似灰度图"
    return True, "ok"


def refetch(name, manifest):
    # 1) 删除旧图
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest.pop(name, None)

    # 2) 收集严格候选
    cands = F.ayxbk_images(name)
    cands += F.commons_images(name)
    cands += F.bing_images(name, "中药 饮片 药材", 24)
    cands += F.bing_images(name, "饮片 炮制", 16)
    if len(cands) < 6:
        cands += F.bing_images(name, "植物 原植物", 16)

    seen = set()
    ordered = []
    for c in sorted(cands, key=strict_score, reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    saved = []
    for c in ordered:
        if len(saved) >= 2:
            break
        if strict_score(c) < 0:
            continue
        raw = F.download_image(c)
        if raw is None:
            continue
        try:
            jpg, size = F.process(raw)
        except Exception:
            continue
        tmp = os.path.join(IMG, "_tmp_check.jpg")
        with open(tmp, "wb") as f:
            f.write(jpg)
        ok, why = content_ok(tmp, name)
        if not ok:
            continue
        fn = "%s_%d.jpg" % (re.sub(r'[\\/:*?"<>|]', "_", name), len(saved) + 1)
        os.replace(tmp, os.path.join(IMG, fn))
        saved.append(fn)
        rec = manifest.setdefault(name, {"files": [], "sources": []})
        rec["files"] = list(saved)
        rec["sources"].append({
            "file": fn, "src": c.get("src", ""), "title": c.get("title", "")[:150],
            "descurl": c.get("page", ""), "license": c.get("license", ""),
            "url": c["url"], "size": list(size)})
        time.sleep(0.1)
    tmp = os.path.join(IMG, "_tmp_check.jpg")
    if os.path.exists(tmp):
        os.remove(tmp)
    return saved


def main():
    args = sys.argv[1:]
    names = []
    if "--file" in args:
        i = args.index("--file")
        with open(args[i + 1], "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    names.append(line.split()[0])
    else:
        names = [a for a in args if not a.startswith("--")]

    if not names:
        print("no herb names given")
        return 2

    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    ok = 0
    for i, n in enumerate(names):
        try:
            got = refetch(n, manifest)
        except Exception as e:
            got = []
            print("ERR %s: %s" % (n.encode("unicode_escape").decode("ascii"), e), flush=True)
        if got:
            ok += 1
        print("[%d/%d] %s -> %d" % (i + 1, len(names),
              n.encode("unicode_escape").decode("ascii"), len(got or [])), flush=True)
        if (i + 1) % 5 == 0 or i + 1 == len(names):
            with open(MANIFEST, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("DONE refetched=%d/%d" % (ok, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
