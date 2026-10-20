# -*- coding: utf-8 -*-
"""把用户直接提供的图片入库（用户发图 = 直接指定这一味药要用这张）。

用法:
  python tools/review/apply_user_photo.py 樟脑 "C:\\path\\to\\photo.jpg" ["备注"]

做的事：
  · 原图存 images/樟脑_1.jpg（保持原分辨率，桌面版打包时再压）
  · 网页版存 docs/images/樟脑_1.jpg（420px / q70）
  · 更新 images_manifest.json 与 images_credits.txt，并清掉这味的旧图
"""
import io
import json
import os
import shutil
import sys
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")
CREDITS = os.path.join(ROOT, "images_credits.txt")
MAX_SIDE = 420
QUALITY = 70


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    name, src = sys.argv[1], sys.argv[2]
    note = sys.argv[3] if len(sys.argv) > 3 else "用户提供"
    if not os.path.exists(src):
        print("找不到图片: %s" % src)
        return 2

    m = json.load(io.open(MANIFEST, encoding="utf-8"))
    for old in list(m.get(name, {}).get("files", [])):
        for d in (IMG, WEBIMG):
            p = os.path.join(d, old)
            if os.path.exists(p):
                os.remove(p)

    if not os.path.isdir(IMG):
        os.makedirs(IMG)
    dst = "%s_1.jpg" % name
    shutil.copyfile(src, os.path.join(IMG, dst))

    im = Image.open(src)
    if im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if max(w, h) > MAX_SIDE:
        k = float(MAX_SIDE) / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    im.save(os.path.join(WEBIMG, dst), "JPEG", quality=QUALITY, optimize=True)

    m[name] = {
        "files": [dst],
        "sources": [{
            "file": dst, "src": "用户提供", "title": "%s（%s）" % (name, note),
            "descurl": "", "license": "用户提供的图片", "url": "",
            "size": [w, h],
        }],
    }
    json.dump(m, io.open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with io.open(CREDITS, "a", encoding="utf-8") as f:
        f.write("\n%s\t%s\t%dx%d\t用户提供（%s）\n"
                % (name, dst, w, h, time.strftime("%Y-%m-%d")))

    total = sum(len(v.get("files", [])) for v in m.values())
    print("%s -> %s（原图 %dx%d，网页版压到 %dpx）" % (name, dst, w, h, MAX_SIDE))
    print("图库: %d 味有图 / %d 张" % (sum(1 for v in m.values() if v.get("files")), total))
    thin = [k for k, v in m.items() if len(v.get("files", [])) <= 1]
    print("仍然 ≤1 张的 %d 味" % len(thin))
    return 0


if __name__ == "__main__":
    sys.exit(main())
