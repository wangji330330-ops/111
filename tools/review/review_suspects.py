# -*- coding: utf-8 -*-
"""生成“高精度可疑图片”对照表，便于逐张人工确认。

判定只用高精度特征（图表/公式/纯色块/无纹理/尺寸过小），
不做 A/B 图差异判定（植物图与饮片图本来就会不同）。
"""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "review")

CELL = 230
COLS = 5
LABEL_H = 22


def feats(path):
    from collections import Counter
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((64, 64))
    px = list(small.getdata())
    q = set()
    white = 0
    sat = 0.0
    for (r, g, b) in px:
        q.add((r >> 5, g >> 5, b >> 5))
        if r > 236 and g > 236 and b > 236:
            white += 1
        mx, mn = max(r, g, b), min(r, g, b)
        sat += 0.0 if mx == 0 else (mx - mn) / float(mx)
    n = float(len(px))
    cnt = Counter((r >> 4, g >> 4, b >> 4) for (r, g, b) in px)
    top = cnt.most_common(1)[0][1] / n
    gray = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in px]
    edges = 0
    for y in range(64):
        for x in range(63):
            i = y * 64 + x
            if abs(gray[i] - gray[i + 1]) > 30:
                edges += 1
    return dict(w=w, h=h, colors=len(q), white=white / n, sat=sat / n,
                top=top, edge=edges / (64.0 * 63))


def main():
    with open(os.path.join(HERE, "images_manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
        names = [h["name"] for h in json.load(f)["herbs"]]

    bad = []
    for name in names:
        for fn in manifest.get(name, {}).get("files", []):
            p = os.path.join(IMG, fn)
            if not os.path.exists(p):
                continue
            try:
                a = feats(p)
            except Exception:
                bad.append((name, fn, "无法读取"))
                continue
            why = []
            if a["colors"] <= 100 and a["white"] > 0.6:
                why.append("白底图表/公式(色%d 白%.0f%%)" % (a["colors"], a["white"] * 100))
            if a["top"] > 0.7:
                why.append("纯色块%.0f%%" % (a["top"] * 100))
            if a["edge"] < 0.010 and a["colors"] < 120:
                why.append("无纹理")
            if a["w"] < 200 or a["h"] < 160:
                why.append("过小%dx%d" % (a["w"], a["h"]))
            if why:
                bad.append((name, fn, "；".join(why)))

    rows = (len(bad) + COLS - 1) // COLS
    if rows == 0:
        print("no suspicious images")
        return
    canvas = Image.new("RGB", (COLS * CELL, rows * (CELL + LABEL_H)), (250, 250, 250))
    d = ImageDraw.Draw(canvas)
    for i, (name, fn, why) in enumerate(bad):
        r, c = divmod(i, COLS)
        x, y = c * CELL, r * (CELL + LABEL_H)
        try:
            im = Image.open(os.path.join(IMG, fn)).convert("RGB")
            im.thumbnail((CELL - 6, CELL - 6))
            canvas.paste(im, (x + 3, y + 3))
        except Exception:
            pass
        d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(190, 60, 50), width=2)
        d.text((x + 5, y + CELL + 4), fn.replace(".jpg", ""), fill=(150, 30, 20))
    p = os.path.join(OUT, "suspects.png")
    canvas.save(p)
    with open(os.path.join(OUT, "suspects.txt"), "w", encoding="utf-8") as f:
        for name, fn, why in bad:
            f.write("%s\t%s\t%s\n" % (name, fn, why))
    print("suspects=%d -> %s (%dx%d)" % (len(bad), p, canvas.size[0], canvas.size[1]))


if __name__ == "__main__":
    main()
