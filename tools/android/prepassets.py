# -*- coding: utf-8 -*-
"""把 Android 资源里的中文文件名全部换成 ASCII —— aapt2 打不开中文文件名。

要动两处，必须一起改，否则页面里的图全裂：
  1. assets/images/ 下的图片改成 img_0001.jpg 这样的名字
  2. index.html 里内联的图片清单（JSON）里对应的文件名一起替换

用法: python _android/prepassets.py
"""
import io
import json
import os
import re
import shutil
import sys
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = r"E:\正常玩\中药复习程序"
SRC_HTML = os.path.join(SRC_ROOT, "docs", "离线版.html")
SRC_IMAGES = os.path.join(SRC_ROOT, "docs", "images")

APP = os.path.join(BASE, "app")
DST_HTML = os.path.join(APP, "assets", "index.html")
DST_IMAGES = os.path.join(APP, "assets", "images")


def main():
    files = sorted(f for f in os.listdir(SRC_IMAGES)
                   if os.path.isfile(os.path.join(SRC_IMAGES, f)))
    print("源图片 %d 张" % len(files))

    mapping = {}
    for i, f in enumerate(files, 1):
        ext = os.path.splitext(f)[1].lower() or ".jpg"
        mapping[f] = "img_%04d%s" % (i, ext)

    html = io.open(SRC_HTML, encoding="utf-8").read()
    before = len(html)
    replaced = 0
    for orig, new in mapping.items():
        for key in {orig, urllib.parse.quote(orig)}:
            if key in html:
                html = html.replace(key, new)
                replaced += 1

    io.open(DST_HTML, "w", encoding="utf-8").write(html)
    print("index.html: %d -> %d 字节，替换 %d 处" % (before, len(html), replaced))

    if os.path.isdir(DST_IMAGES):
        shutil.rmtree(DST_IMAGES, ignore_errors=True)
    os.makedirs(DST_IMAGES)
    for orig, new in mapping.items():
        shutil.copyfile(os.path.join(SRC_IMAGES, orig), os.path.join(DST_IMAGES, new))

    left = [f for f in mapping if f in html]
    print("拷贝完成，剩余未替换的中文名: %d" % len(left))
    if left:
        print("  例如: %s" % left[:3])
        return 1

    refs = set(re.findall(r"images/(img_\d{4}\.[a-z]+)", html))
    missing = [r for r in refs if not os.path.exists(os.path.join(DST_IMAGES, r))]
    print("页面引用 %d 个图片名，缺失 %d 个" % (len(refs), len(missing)))
    if missing:
        print("  例如: %s" % missing[:3])
        return 1

    json.dump(mapping, io.open(os.path.join(BASE, "imgmap.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())