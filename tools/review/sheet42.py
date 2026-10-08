# -*- coding: utf-8 -*-
"""为待换图片的药材生成候选对照表（每张 14 味 × 8 候选）。"""
import io
import os

from PIL import Image, ImageDraw

ROOT = r"E:\正常玩\中药复习程序"
CAND = os.path.join(ROOT, "review", "c360")
OUT = os.path.join(ROOT, "review")
NAMES = [x.strip() for x in io.open(os.path.join(ROOT, "review", "fix42.txt"),
                                    encoding="utf-8").read().split("\n") if x.strip()]

C, L, COLS, PER = 140, 16, 8, 14


def main():
    pages = 0
    for s in range(0, len(NAMES), PER):
        chunk = NAMES[s:s + PER]
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
        cv.save(os.path.join(OUT, "fix42_%02d.png" % pages))
        print("fix42_%02d.png  %d 味" % (pages, len(chunk)))
    print("共 %d 味，%d 张" % (len(NAMES), pages))


if __name__ == "__main__":
    main()
