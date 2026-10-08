# -*- coding: utf-8 -*-
"""最后一轮：只收“图片直链 + 内容合格”的结果（标题不含药名也接受，取质量最好的 2 张）。"""
import json
import os
import re
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F
from fetch_safe import bing_safe, url_ok, ok_image, score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

# 每味药人工指定的搜索词（按优先级）
TERMS = {
    "丁香": ["丁香 花蕾 中药 饮片", "丁香 药材 实物 特写", "丁香 花蕾 干燥"],
    "槟榔": ["槟榔 饮片 切片 药材", "槟榔 种子 实物", "槟榔 干燥 果实"],
    "竹沥": ["竹沥 中药 饮片", "竹沥 液体 中药", "鲜竹沥 药材"],
    "磁石": ["磁石 矿物 标本", "磁铁矿 矿石 标本", "磁石 中药材 实物"],
    "西洋参": ["西洋参 饮片 切片", "西洋参 药材 实物", "西洋参 干燥 根"],
    "青黛": ["青黛 中药 饮片 实物", "青黛 药材 粉末"],
    "雷公藤": ["雷公藤 植物 花果", "雷公藤 药材 根"],
}


def loose_bing(name, extra, limit=24):
    """只要 murl 合法 + 是图片链接，标题不强制含药名"""
    out = []
    url = ("https://cn.bing.com/images/search?q=" +
           F.urllib.parse.quote(name + " " + extra) + "&form=HDRSC2&first=1")
    try:
        html = F.http_get(url, timeout=15)
    except Exception:
        return out
    if "murl" not in html:
        return out
    for m in re.finditer(r'm="(\{[^"]*?murl[^"]*?\})"', html):
        raw = m.group(1).replace("&quot;", '"').replace("&amp;", "&")
        try:
            j = json.loads(raw)
        except Exception:
            continue
        u = j.get("murl") or ""
        t = j.get("t") or ""
        if not url_ok(u):
            continue
        if any(b in (u + t).lower() for b in ("convert", "editor", "online", "template")):
            continue
        out.append({"url": u, "title": t, "page": j.get("purl", ""),
                    "license": "网络图片（见来源页）", "src": "bing"})
        if len(out) >= limit:
            break
    return out


def fetch(name, manifest, want=2):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    cands = F.ayxbk_images(name) + F.commons_images(name)
    for t in TERMS.get(name, [name + " 中药 饮片"]):
        cands += loose_bing(name, t, 24)

    seen = set()
    ordered = []
    for c in sorted(cands, key=lambda c: score(c) + (30 if name in (c.get("title") or "") else 0),
                    reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    tmp = os.path.join(IMG, "_tmpl.jpg")
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
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not names:
        names = list(TERMS.keys())
    ok = 0
    for i, n in enumerate(names):
        try:
            got = fetch(n, manifest)
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
