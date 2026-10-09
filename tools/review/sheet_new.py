# -*- coding: utf-8 -*-
"""为新增药味生成候选对照表（每张 12 味 × 8 候选，编号 1-8 便于勾选）。

用法: python tools/review/sheet_new.py
输出: review/new_01.png ...
"""
import io
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAND = os.path.join(ROOT, "review", "c360new")
OUT = os.path.join(ROOT, "review")
PER = 12          # 每张表多少味
COLS = 8          # 每味多少候选
C, L = 150, 16    # 单元格边长 / 文字高度


def load_names():
    import sys
    sys.path.insert(0, ROOT)
    import herbs_additions as A
    enabled = getattr(A, "ENABLED_BATCHES", [1])
    names = []
    for n in enabled:
        for rec in getattr(A, "ADDITIONS_%d" % n, []):
            names.append(rec[0])
    # 只保留有候选图的
    return [n for n in names if os.path.exists(os.path.join(CAND, "%s_c01.jpg" % n))]


def main():
    names = load_names()
    pages = 0
    idx = []
    for s in range(0, len(names), PER):
        chunk = names[s:s + PER]
        rows = len(chunk)
        cv = Image.new("RGB", (COLS * C, rows * (C + L)), (250, 250, 250))
        d = ImageDraw.Draw(cv)
        for r, n in enumerate(chunk):
            for c in range(COLS):
                p = os.path.join(CAND, "%s_c%02d.jpg" % (n, c + 1))
                x, y = c * C, r * (C + L)
                if os.path.exists(p):
                    im = Image.open(p).convert("RGB")
                    im.thumbnail((C - 4, C - 4))
                    cv.paste(im, (x + 2, y + 2))
                d.rectangle([x, y, x + C - 1, y + C - 1], outline=(175, 182, 178))
                d.text((x + 3, y + 2), str(c + 1), fill=(200, 40, 30))
            d.text((3, r * (C + L) + C + 1), n, fill=(180, 40, 30))
        pages += 1
        cv.save(os.path.join(OUT, "new_%02d.png" % pages))
        idx.append("new_%02d.png (%d 味): %s" % (pages, len(chunk), "、".join(chunk)))
        print("new_%02d.png  %d 味" % (pages, len(chunk)))
    io.open(os.path.join(OUT, "new_sheet_index.txt"), "w", encoding="utf-8").write("\n".join(idx))
    print("共 %d 味，%d 张对照表" % (len(names), pages))


if __name__ == "__main__":
    main()
