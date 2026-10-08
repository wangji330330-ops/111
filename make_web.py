# -*- coding: utf-8 -*-
"""生成网页版数据：docs/data/*.json + 图片目录 + 版本信息。

输出：
  docs/index.html                单页应用（另写）
  docs/data/herbs.json           题库（含功效/性味/用法等）
  docs/data/chunk_XX.json        分块题库（便于增量加载，默认用 herbs.json）
  docs/data/synonyms.json        同义词表（填空判分容错）
  docs/data/images_manifest.json 药名 -> 图片文件名
  docs/images/*.jpg              图片（从 images/ 复制，压缩到 420px）
  docs/version.json              版本与更新信息
"""
import io
import json
import os
import shutil
import struct

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "docs")
DATA = os.path.join(WEB, "data")
IMGSRC = os.path.join(HERE, "images")
IMGDST = os.path.join(WEB, "images")

VERSION = "1.3.0"

NOTES = ("新增：看图猜药（四选一识药，答对答错都显示答案）+ 鼓励与勉励语（含中医经典名言）；"
         "图片「删除」改为「隐藏/恢复」（可逆）；单文件离线版自动内联全部样式与脚本")
MAX_SIDE = 420
QUALITY = 70


def ensure(p):
    if not os.path.isdir(p):
        os.makedirs(p)


def load_json(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj, indent=None):
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def pack_images(manifest):
    """复制并压缩图片到 docs/images，返回 药名_序号 -> 文件名 映射"""
    ensure(IMGDST)
    count = 0
    total = 0
    for name, rec in manifest.items():
        for fn in rec.get("files", []):
            src = os.path.join(IMGSRC, fn)
            if not os.path.exists(src):
                continue
            dst = os.path.join(IMGDST, fn)
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                count += 1
                total += os.path.getsize(dst)
                continue
            im = Image.open(src)
            if im.mode != "RGB":
                im = im.convert("RGB")
            w, h = im.size
            if max(w, h) > MAX_SIDE:
                k = float(MAX_SIDE) / max(w, h)
                im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=QUALITY, optimize=True)
            with open(dst, "wb") as f:
                f.write(buf.getvalue())
            count += 1
            total += os.path.getsize(dst)
    return count, total


def main():
    ensure(DATA)

    herbs = load_json(os.path.join(HERE, "herbs.json"))
    manifest = load_json(os.path.join(HERE, "images_manifest.json"))

    # ---- 题库（精简字段名，减小体积） ----
    out_herbs = []
    imgmap = {}
    for h in herbs["herbs"]:
        name = h["name"]
        files = [f for f in manifest.get(name, {}).get("files", [])
                 if os.path.exists(os.path.join(IMGSRC, f))]
        if files:
            imgmap[name] = files
        out_herbs.append({
            "n": name, "c": h["cat"], "x": h["nature"], "m": h["meridian"],
            "f": h["fx"], "u": h["usage"], "k": h["caution"],
        })

    save_json(os.path.join(DATA, "herbs.json"), {
        "meta": {
            "title": herbs["meta"]["title"],
            "version": VERSION,
            "count": len(out_herbs),
            "categories": herbs["meta"]["categories"],
        },
        "herbs": out_herbs,
    }, indent=None)

    save_json(os.path.join(DATA, "synonyms.json"), herbs["meta"]["synonyms"])
    save_json(os.path.join(DATA, "images_manifest.json"), imgmap)

    # ---- 图片 ----
    n_img, size_img = pack_images(manifest)

    # ---- 版本/更新信息 ----
    save_json(os.path.join(WEB, "version.json"), {
        "name": "中药学复习系统（网页版）",
        "version": VERSION,
        "buildDate": __import__("time").strftime("%Y-%m-%d"),
        "notes": NOTES,
        "files": ["index.html", "app.js", "timeherb.js", "style.css", "style2.css",
                  "data/herbs.json", "data/synonyms.json", "data/images_manifest.json"],
        "updateUrl": "version.json",
        "homepage": "https://wangji330330-ops.github.io/111/",
        "license": "MIT",
    }, indent=1)

    print("herbs=%d images=%d (%.1f MB) -> docs/" % (len(out_herbs), n_img, size_img / 1048576.0))
    print("version=%s" % VERSION)


if __name__ == "__main__":
    main()
