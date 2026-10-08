# -*- coding: utf-8 -*-
"""生成逐张核对用的对照表（清晰版）：每格 250px，5 列，每张表 20 格。"""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "review")

CELL = 250
COLS = 5
PER_SHEET = 20
LABEL_H = 24


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with open(os.path.join(HERE, "images_manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
        names = [h["name"] for h in json.load(f)["herbs"]]

    cells = []
    for name in names:
        for fn in manifest.get(name, {}).get("files", []):
            p = os.path.join(IMG, fn)
            if os.path.exists(p):
                cells.append((fn, p))

    rows = (PER_SHEET + COLS - 1) // COLS
    w, h = COLS * CELL, rows * (CELL + LABEL_H)
    n = 0
    for start in range(0, len(cells), PER_SHEET):
        chunk = cells[start:start + PER_SHEET]
        canvas = Image.new("RGB", (w, h), (248, 248, 248))
        d = ImageDraw.Draw(canvas)
        for i, (fn, p) in enumerate(chunk):
            r, c = divmod(i, COLS)
            x, y = c * CELL, r * (CELL + LABEL_H)
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((CELL - 6, CELL - 6))
                canvas.paste(im, (x + 3, y + 3))
            except Exception:
                pass
            d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(170, 178, 174))
            d.rectangle([x, y + CELL, x + CELL - 1, y + CELL + LABEL_H - 1], fill=(240, 244, 242))
            d.text((x + 6, y + CELL + 5), fn.replace(".jpg", ""), fill=(20, 60, 45))
        n += 1
        canvas.save(os.path.join(OUT, "chk_%02d.png" % n))
    print("sheets=%d cells=%d cell=%d" % (n, len(cells), CELL))


if __name__ == "__main__":
    main()
