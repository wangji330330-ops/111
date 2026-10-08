# -*- coding: utf-8 -*-
"""手工关键词抓取：为指定药物用人工挑选的关键词抓 1~2 张可信图片。

用法: python manual_fetch.py
规则写在 MANUAL 字典里：药名 -> [关键词1, 关键词2, ...]
"""
import json
import os
import re
import sys
import time

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

# 绝不接受的来源/标题（软件、素材、地图、电商等）
REJECT_HOST = ("zcool", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt",
               "ziti", "font", "shufazidian", "zdic", "cidian", "pexels",
               "unsplash", "pixabay", "freepik", "dreamstime", "shutterstock",
               "wallpaper", "desktoppr", "tieba", "bilibili", "tmall", "taobao",
               "1688", "jd.com", "alibaba", "iloveimg", "imageto", "jpg", "png",
               "convert", "online", "tool", "editor")
REJECT_TITLE = ("logo", "图标", "字体", "书法", "字帖", "字典", "函数", "公式",
                "曲线", "流程图", "结构图", "图表", "示意", "ppt", "壁纸",
                "头像", "表情包", "动漫", "漫画", "游戏", "海报", "宣传",
                "广告", "价格", "行情", "股票", "教程", "视频", "包装", "礼盒",
                "功效与作用", "性味归经", "中药与健康", "每天认识", "认识中药",
                "大全", "排行", "品牌", "旗舰店", "多少钱", "包邮", "销量",
                "png", "jpg", "jpeg", "webp", "convert", "edit", "online",
                "map", "地图", "军事", "航母", "电影", "旅游", "风景", "美女")

MANUAL = {
    "青黛": ["青黛 中药 饮片 实物", "青黛 药材 粉末 深蓝", "青黛 植物 马蓝"],
    "雷公藤": ["雷公藤 植物 花", "雷公藤 药材 根", "雷公藤 原植物"],
    "丁香": ["丁香 中药 药材 实物", "丁香 花蕾 药材", "丁香 饮片"],
    "槟榔": ["槟榔 饮片 实物", "槟榔 种子 药材", "槟榔 切片"],
    "竹沥": ["竹沥 药材", "竹沥 中药 液体 饮片", "鲜竹沥 中药"],
    "磁石": ["磁石 矿物 药材", "磁石 中药 矿石", "磁铁矿 矿石"],
    "西洋参": ["西洋参 饮片 实物", "西洋参 切片 药材", "西洋参 根"],
}


def text_heavy(path):
    im = Image.open(path).convert("L").resize((320, 240))
    px = list(im.getdata())
    white = sum(1 for p in px if p > 228) / float(len(px))
    dark = sum(1 for p in px if p < 110) / float(len(px))
    edges = im.filter(ImageFilter.FIND_EDGES)
    ep = list(edges.getdata())
    emid = sum(1 for p in ep if 60 < p < 200) / float(len(ep))
    return white, dark, emid


def ok_image(path):
    im = Image.open(path)
    w, h = im.size
    if w < 260 or h < 200:
        return False, "too small"
    white, dark, emid = text_heavy(path)
    if white > 0.55 and emid > 0.05:
        return False, "白底图文"
    if white > 0.40 and dark > 0.02 and emid > 0.09:
        return False, "疑似文字"
    return True, "ok"


def score(c):
    s = 0
    t = ((c.get("title") or "") + " " + (c.get("page") or "")).lower()
    h = F.host_of(c["url"])
    for w in REJECT_HOST:
        if w in h:
            return -999
    for w in REJECT_TITLE:
        if w in t:
            return -999
    if c.get("src") == "a-hospital":
        s += 50
    if c.get("src") == "commons":
        s += 40
    if "ayxbk" in h or "a-hospital" in h or "yixue" in h:
        s += 40
    if "bcebos" in h or "baike" in h:
        s += 20
    for w in ("饮片", "药材", "中药", "植物", "原植物", "饮片图", "性状"):
        if w in t:
            s += 10
    return s


def fetch(name, terms, manifest, want=2):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    cands = F.ayxbk_images(name)
    cands += F.commons_images(name)
    for t in terms:
        cands += F.bing_images(name, t, 20)

    seen = set()
    ordered = []
    for c in sorted(cands, key=score, reverse=True):
        if score(c) < 0:
            continue
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    tmp = os.path.join(IMG, "_tmpm.jpg")
    for c in ordered:
        if len(manifest[name]["files"]) >= want:
            break
        raw = F.download_image(c)
        if raw is None:
            continue
        try:
            jpg, size = F.process(raw)
        except Exception:
            continue
        with open(tmp, "wb") as f:
            f.write(jpg)
        good, why = ok_image(tmp)
        if not good:
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
        time.sleep(0.1)
    if os.path.exists(tmp):
        os.remove(tmp)
    return manifest[name]["files"]


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if len(sys.argv) > 1:
        names = [a for a in sys.argv[1:] if not a.startswith("--")]
    else:
        names = list(MANUAL.keys())
    ok = 0
    for i, n in enumerate(names):
        try:
            got = fetch(n, MANUAL.get(n, [n + " 中药 饮片"]), manifest)
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
