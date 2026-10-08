# -*- coding: utf-8 -*-
"""精确关键词补抓（最后几味）：中文医药/百科域名白名单 + 标题相关性校验。

每个药味按顺序尝试多组关键词，取前 2 张通过校验的图片。
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

# 可信中文医药/百科/植物类域名
TRUST_HOST = (
    "ayxbk.com", "a-hospital.com", "yixue.com", "bcebos", "baike", "zhongyoo",
    "cnkang", "39.net", "youlai", "120ask", "xywy", "39yst", "zysj", "zyctd",
    "tcm", "herb", "iflora", "huabaike", "plant", "botany", "bucm.edu.cn",
    "zhiwuwang", "cvv", "dayi", "yaocai", "pharm", "med", "doctor",
    "360tres", "scimall", "ppbc", "cfh.ac.cn", "nsi", "eol.cn",
)
# 明显无关的域名
BAD_HOST = ("699pic", "zhimg", "woshipm", "sohucs", "playbyone", "hjkxyj",
            "gdchunlei", "myevaporator", "njwds", "websiteonline", "qpic",
            "cidianwang", "hanyu", "jiqie", "1qi.cn", "39017", "zgyoujiao",
            "visitbeijing", "maps4gis", "arkoo", "pingguolv", "phb123")

TERMS = {
    "磁石": ["磁石 中药材 磁铁矿 饮片", "磁铁矿 矿石 标本", "磁石 中药 煅磁石"],
    "西洋参": ["西洋参 中药材 饮片", "西洋参 干燥根 药材", "西洋参 切片 中药"],
    "青黛": ["青黛 中药材 饮片", "青黛 中药 粉末 药材", "马蓝 植物 青黛"],
    "雷公藤": ["雷公藤 中药材", "雷公藤 植物 昆明山海棠", "雷公藤 根 药材"],
    "丁香": ["丁香 花蕾 中药材", "丁香 中药 饮片", "公丁香 药材"],
}


def rel(title, name):
    t = title or ""
    return name in t or (name == "丁香" and "丁香" in t)


def good_host(u):
    h = F.host_of(u)
    if any(b in h for b in BAD_HOST):
        return False
    return True


def trusted(u):
    h = F.host_of(u)
    return any(g in h for g in TRUST_HOST)


def ok_image(path):
    im = Image.open(path)
    w, h = im.size
    if w < 240 or h < 180:
        return False
    g = im.convert("L").resize((320, 240))
    px = list(g.getdata())
    white = sum(1 for p in px if p > 228) / float(len(px))
    dark = sum(1 for p in px if p < 110) / float(len(px))
    ep = list(g.filter(ImageFilter.FIND_EDGES).getdata())
    emid = sum(1 for p in ep if 60 < p < 200) / float(len(ep))
    if white > 0.55 and emid > 0.05:
        return False
    if white > 0.42 and dark > 0.02 and emid > 0.09:
        return False
    return True


def gather(name, terms):
    cands = F.ayxbk_images(name) + F.commons_images(name)
    for t in terms:
        cands += F.bing_images(name, t, 20)
    out = []
    seen = set()
    for c in cands:
        u = c["url"]
        if u in seen or not good_host(u):
            continue
        seen.add(u)
        # 标题必须与药名相关，且来自可信域名
        if not trusted(u) and not rel(c.get("title"), name):
            continue
        if not trusted(u) and not rel(c.get("title"), name):
            continue
        out.append(c)
    # 可信域名优先
    out.sort(key=lambda c: (0 if trusted(c["url"]) else 1, 0 if rel(c.get("title"), name) else 1))
    return out


def fetch(name, terms, manifest, want=2):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    tmp = os.path.join(IMG, "_tmpq.jpg")
    for c in gather(name, terms):
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
        try:
            good = ok_image(tmp)
        except Exception:
            good = False
        if not good:
            continue
        fn = "%s_%d.jpg" % (re.sub(r'[\\/:*?"<>|]', "_", name),
                            len(manifest[name]["files"]) + 1)
        os.replace(tmp, os.path.join(IMG, fn))
        manifest[name]["files"].append(fn)
        manifest[name]["sources"].append({
            "file": fn, "src": c.get("src", ""), "title": (c.get("title") or "")[:150],
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
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(TERMS.keys())
    ok = 0
    for i, n in enumerate(names):
        try:
            got = fetch(n, TERMS.get(n, [n + " 中药材"]), manifest)
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
