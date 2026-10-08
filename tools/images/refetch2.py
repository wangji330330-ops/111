# -*- coding: utf-8 -*-
"""第二轮补抓：放宽特征过滤（只封杀素材/字体/logo 站与明显无关标题）。"""
import io
import json
import os
import re
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

HARD_BAD_HOST = (
    "zcool", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt", "ziti",
    "font", "shufazidian", "zdic", "cidian", "pexels", "unsplash", "pixabay",
    "freepik", "dreamstime", "shutterstock", "wallpaper", "desktoppr",
    "tieba", "bilibili", "ixigua",
)
HARD_BAD_TITLE = (
    "logo", "标志", "字体", "书法", "字帖", "毛笔", "字典", "笔画", "偏旁",
    "函数", "公式", "曲线", "流程图", "框图", "结构图", "示意", "ppt", "课件",
    "壁纸", "头像", "表情包", "动漫", "漫画", "游戏", "海报", "宣传", "广告",
    "价格", "行情", "股票", "理财", "教程", "视频", "包装", "礼盒", "军事",
    "航母", "电影", "电视剧", "美女", "风景", "旅游",
)
GOOD_TITLE = ("饮片", "药材", "中药", "炮制", "切片", "植物", "herb", "本草",
              "百科", "性状", "鉴别", "生品", "制品", "干燥")


def sc(c):
    s = F.score(c)
    t = ((c.get("title") or "") + " " + (c.get("page") or "")).lower()
    h = F.host_of(c["url"])
    for w in HARD_BAD_HOST:
        if w in h:
            s -= 200
    for w in HARD_BAD_TITLE:
        if w in t:
            s -= 200
    for w in GOOD_TITLE:
        if w in t:
            s += 15
    return s


def weak_ok(path):
    """宽松校验：排除白底线条图、纯色块、极小图"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w < 200 or h < 150:
        return False, "too small"
    small = im.resize((64, 64))
    px = list(small.getdata())
    white = sum(1 for (r, g, b) in px if r > 238 and g > 238 and b > 238) / 4096.0
    q = set()
    for (r, g, b) in px:
        q.add((r >> 5, g >> 5, b >> 5))
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
    if white > 0.82 and len(q) < 90:
        return False, "白底线条图"
    if top > 0.80:
        return False, "纯色块"
    if edge < 0.008:
        return False, "无纹理"
    return True, "ok"


def grab(name, manifest):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest.pop(name, None)

    cands = F.ayxbk_images(name)
    cands += F.bing_images(name, "中药 饮片 药材", 24)
    cands += F.bing_images(name, "饮片 炮制 切片", 16)
    if len(cands) < 6:
        cands += F.commons_images(name)
    if len(cands) < 6:
        cands += F.bing_images(name, "植物 原植物", 16)
    if len(cands) < 4:
        cands += F.bing_images(name, "", 16)

    seen = set()
    ordered = []
    for c in sorted(cands, key=sc, reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    saved = []
    tmp = os.path.join(IMG, "_tmp2.jpg")
    for c in ordered:
        if len(saved) >= 2:
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
        ok, why = weak_ok(tmp)
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
        time.sleep(0.08)
    if os.path.exists(tmp):
        os.remove(tmp)
    return saved


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not names:
        print("no names")
        return 2
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
        if (i + 1) % 4 == 0 or i + 1 == len(names):
            with open(MANIFEST, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("DONE ok=%d/%d" % (ok, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
