# -*- coding: utf-8 -*-
"""把候选图拼成对照表（带编号+质检分数），方便一次看一批、快速判定。

用法:
  python tools/images/montage.py out.png bad 24        # 分数最高的 24 张（最像广告）
  python tools/images/montage.py out.png ok 24         # 随机 24 张干净的
  python tools/images/montage.py out.png herb 黄芪      # 某味药的全部候选
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
QC = os.path.join(HD, "qc.json")

CELL = 300
PAD = 6
COLS = 6


def load_qc():
    if os.path.exists(QC):
        return json.load(io.open(QC, encoding="utf-8"))
    return {}


def pick_files(mode, arg=None, n=24):
    qc = load_qc()
    files = sorted(f for f in os.listdir(HD) if f.endswith(".jpg"))
    if mode == "herb":
        return sorted(f for f in files if f.startswith(arg + "_c"))
    if mode == "bad":
        fs = sorted(files, key=lambda f: -(qc.get(f, {}).get("text") or 0))
        return fs[:n]
    if mode == "ok":
        fs = [f for f in files if (qc.get(f, {}).get("v") == "ok")]
        step = max(1, len(fs) // n)
        return fs[::step][:n]
    return files[:n]


def main():
    out = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "bad"
    arg = None
    n = 24
    if mode == "herb":
        arg = sys.argv[3]
    else:
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    files = pick_files(mode, arg, n)
    if not files:
        print("没有匹配的图")
        return 1
    qc = load_qc()
    cols = min(COLS, len(files))
    rows = (len(files) + cols - 1) // cols
    W = cols * (CELL + PAD) + PAD
    H = rows * (CELL + 34 + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (245, 247, 246))
    d = ImageDraw.Draw(sheet)
    for i, fn in enumerate(files):
        r, c = divmod(i, cols)
        x = PAD + c * (CELL + PAD)
        y = PAD + r * (CELL + 34 + PAD)
        try:
            im = Image.open(os.path.join(HD, fn))
            im = im.convert("RGB")
            im.thumbnail((CELL, CELL))
        except Exception:
            continue
        sheet.paste(im, (x + (CELL - im.size[0]) // 2, y + (CELL - im.size[1]) // 2))
        q = qc.get(fn, {})
        label = "%d. %s  字=%.2f %s" % (i + 1, fn.replace(".jpg", ""),
                                        q.get("text", -1), q.get("v", "?"))
        d.rectangle([x, y + CELL, x + CELL, y + CELL + 30], fill=(255, 255, 255))
        d.text((x + 4, y + CELL + 4), label, fill=(20, 40, 32))
    sheet.save(out, quality=88)
    print("拼图 -> %s  (%dx%d, %d 张)" % (out, W, H, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
