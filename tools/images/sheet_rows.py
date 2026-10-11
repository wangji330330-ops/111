# -*- coding: utf-8 -*-
"""按「每味一行」拼图，用来快速目检某一批药的候选图质量。

用法: python tools/images/sheet_rows.py out.png 蜂蜜 熊胆 牛黄 阿胶 竹沥 沉香
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
INDEX = os.path.join(HD, "index.json")
CELL, LABEL, PAD = 190, 22, 5


def main():
    out, names = sys.argv[1], sys.argv[2:]
    idx = json.load(io.open(INDEX, encoding="utf-8"))
    rows = [(n, idx.get(n) or []) for n in names]
    cols = max((len(v) for _, v in rows), default=1)
    W = PAD + cols * (CELL + PAD)
    H = PAD + len(rows) * (CELL + LABEL + PAD)
    sheet = Image.new("RGB", (W, H), (245, 247, 246))
    d = ImageDraw.Draw(sheet)
    for r, (name, items) in enumerate(rows):
        y = PAD + r * (CELL + LABEL + PAD)
        d.text((PAD + 2, y), "%s（%d 张）" % (name, len(items)), fill=(20, 60, 45))
        for c, m in enumerate(items):
            x = PAD + c * (CELL + PAD)
            p = os.path.join(HD, m["file"])
            if not os.path.exists(p):
                continue
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((CELL, CELL))
            except Exception:
                continue
            sheet.paste(im, (x + (CELL - im.size[0]) // 2, y + LABEL))
            d.rectangle([x, y + LABEL + CELL, x + CELL, y + LABEL + CELL + 14], fill=(255, 255, 255))
            d.text((x + 3, y + LABEL + CELL + 1),
                   "第%d列 %dx%d" % (c + 1, m["w"], m["h"]), fill=(40, 60, 52))
    sheet.save(out, quality=88)
    print("拼图 -> %s (%dx%d)" % (out, W, H))


if __name__ == "__main__":
    main()
