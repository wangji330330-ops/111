# -*- coding: utf-8 -*-
"""对少量药味做“最严格”重抓：加入文字/图表检测（拒绝文章截图、图表、包装图）。"""
import io
import json
import os
import re
import sys
import time

from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

BAD_HOST = ("zcool", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt", "ziti",
            "font", "shufazidian", "zdic", "cidian", "pexels", "unsplash",
            "pixabay", "freepik", "dreamstime", "shutterstock", "wallpaper",
            "desktoppr", "tieba", "bilibili", "tmall", "taobao", "1688",
            "jd.com", "alibaba", "baidu.com/pic")
BAD_TITLE = ("logo", "标志", "字体", "书法", "字帖", "字典", "笔画", "函数", "公式",
             "曲线", "流程图", "结构图", "图表", "示意", "ppt", "壁纸", "头像",
             "表情包", "动漫", "漫画", "游戏", "海报", "宣传", "广告", "价格",
             "行情", "股票", "教程", "视频", "包装", "礼盒", "功效与作用", "性味归经",
             "中药与健康", "每天认识", "认识中药", "大全", "排行", "品牌", "旗舰店",
             "多少钱", "斤", "克", "包邮", "销量", "评价", "小儿", "股票", "走势")
GOOD_TITLE = ("饮片", "药材", "中药", "炮制", "切片", "植物", "herb", "本草",
              "百科", "性状", "鉴别", "生品", "制品", "干燥", "原植物", "饮片图")


def text_likeness(path):
    """估算“文字/图表”程度：白底 + 大量细小深色笔画"""
    im = Image.open(path).convert("L")
    im = im.resize((320, 240))
    px = list(im.getdata())
    white = sum(1 for p in px if p > 225) / float(len(px))
    dark = sum(1 for p in px if p < 110) / float(len(px))
    edges = im.filter(ImageFilter.FIND_EDGES)
    ep = list(edges.getdata())
    emid = sum(1 for p in ep if 60 < p < 200) / float(len(ep))
    return white, dark, emid


def strict_ok(path):
    im = Image.open(path)
    w, h = im.size
    if w < 260 or h < 200:
        return False, "too small"
    white, dark, emid = text_likeness(path)
    if white > 0.45 and dark > 0.02 and emid > 0.10:
        return False, "疑似文字/图表"
    if white > 0.72 and emid > 0.06:
        return False, "疑似白底图文"
    small = im.convert("RGB").resize((64, 64))
    px = list(small.getdata())
    q = set()
    for (r, g, b) in px:
        q.add((r >> 5, g >> 5, b >> 5))
    from collections import Counter
    top = Counter((r >> 4, g >> 4, b >> 4) for (r, g, b) in px).most_common(1)[0][1] / 4096.0
    if top > 0.78:
        return False, "单一色块"
    return True, "ok"


def sc(c):
    s = F.score(c)
    t = ((c.get("title") or "") + " " + (c.get("page") or "")).lower()
    h = F.host_of(c["url"])
    for w in BAD_HOST:
        if w in h:
            s -= 250
    for w in BAD_TITLE:
        if w in t:
            s -= 250
    for w in GOOD_TITLE:
        if w in t:
            s += 18
    return s


def grab(name, manifest, want=1):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    cands = F.ayxbk_images(name)
    cands += F.bing_images(name, "饮片 药材 切片", 24)
    cands += F.bing_images(name, "药材 炮制", 16)
    cands += F.bing_images(name, "原植物 植物", 16)
    cands += F.bing_images(name, "", 16)

    seen = set()
    ordered = []
    for c in sorted(cands, key=sc, reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    tmp = os.path.join(IMG, "_tmps.jpg")
    for c in ordered:
        if len(manifest[name]["files"]) >= want:
            break
        if sc(c) < -100:
            continue
        raw = F.download_image(c)
        if raw is None:
            continue
        try:
            jpg, size = F.process(raw)
        except Exception:
            continue
        with open(tmp, "wb") as f:
            f.write(jpg)
        ok, why = strict_ok(tmp)
        if not ok:
            continue
        fn = "%s_%d.jpg" % (re.sub(r'[\\/:*?"<>|]', "_", name),
                            len(manifest[name]["files"]) + 1)
        os.replace(tmp, os.path.join(IMG, fn))
        manifest[name]["files"].append(fn)
        manifest[name]["sources"].append({
            "file": fn, "src": c.get("src", ""), "title": c.get("title", "")[:150],
            "descurl": c.get("page", ""), "license": c.get("license", ""),
            "url": c["url"], "size": list(size)})
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
    if os.path.exists(tmp):
        os.remove(tmp)
    return manifest[name]["files"]


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    ok = 0
    for i, n in enumerate(names):
        try:
            got = grab(n, manifest)
        except Exception as e:
            got = []
            print("ERR %s: %s" % (n.encode("unicode_escape").decode("ascii"), e), flush=True)
        if got:
            ok += 1
        print("[%d/%d] %s -> %d" % (i + 1, len(names),
              n.encode("unicode_escape").decode("ascii"), len(got or [])), flush=True)
    print("DONE ok=%d/%d" % (ok, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
