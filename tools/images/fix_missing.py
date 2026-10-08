# -*- coding: utf-8 -*-
"""补抓缺失图片：带重试与断网等待，尽量把所有药味补齐。

用法:
  python fix_missing.py             # 抓所有缺失的（含 retry 4 次 + 退避）
  python fix_missing.py 羌活 白芷   # 指定药名
"""
import io
import json
import os
import re
import socket
import sys
import time
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

HARD_BAD_HOST = ("zcool", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt",
                 "ziti", "font", "shufazidian", "zdic", "cidian", "pexels",
                 "unsplash", "pixabay", "freepik", "dreamstime", "shutterstock",
                 "wallpaper", "desktoppr", "tieba", "bilibili")
HARD_BAD_TITLE = ("logo", "标志", "字体", "书法", "字帖", "毛笔", "字典", "笔画",
                  "函数", "公式", "曲线", "流程图", "结构图", "示意", "ppt",
                  "壁纸", "头像", "表情包", "动漫", "漫画", "游戏", "海报",
                  "宣传", "广告", "价格", "行情", "股票", "教程", "视频",
                  "包装", "礼盒", "军事", "航母", "电影", "电视剧", "风景", "旅游")
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
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w < 190 or h < 140:
        return False
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
    if white > 0.84 and len(q) < 90:
        return False
    if top > 0.82:
        return False
    if edge < 0.008:
        return False
    return True


def candidates(name):
    c = []
    c += F.ayxbk_images(name)
    c += F.commons_images(name)
    c += F.bing_images(name, "中药 饮片 药材", 24)
    c += F.bing_images(name, "饮片 炮制 切片", 16)
    c += F.bing_images(name, "原植物 植物", 16)
    c += F.bing_images(name, "中药", 16)
    c += F.bing_images(name, "", 16)
    seen = set()
    out = []
    for x in sorted(c, key=sc, reverse=True):
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        out.append(x)
    return out


def grab(name, manifest, tries=4):
    # 清掉旧记录与文件
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    for attempt in range(tries):
        cands = candidates(name)
        if not cands:
            time.sleep(2 + attempt * 3)
            continue
        tmp = os.path.join(IMG, "_tmpf.jpg")
        for c in cands:
            if len(manifest[name]["files"]) >= 2:
                break
            if sc(c) < -100:
                continue
            raw = None
            for k in range(2):     # 单个 URL 也重试
                raw = F.download_image(c)
                if raw is not None:
                    break
                time.sleep(1.0)
            if raw is None:
                continue
            try:
                jpg, size = F.process(raw)
            except Exception:
                continue
            with open(tmp, "wb") as f:
                f.write(jpg)
            try:
                ok = weak_ok(tmp)
            except Exception:
                ok = False
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
        if manifest[name]["files"]:
            return manifest[name]["files"]
        time.sleep(3 + attempt * 4)      # 断网/限流退避
    return []


def main():
    ok = 0
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        names = args
    else:
        with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
            allnames = [h["name"] for h in json.load(f)["herbs"]]
        names = [n for n in allnames if not manifest.get(n, {}).get("files")]
    print("TODO=%d" % len(names), flush=True)

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
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    have = [n for n in manifest if manifest[n].get("files")]
    print("DONE ok=%d total_with_image=%d" % (ok, len(have)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
