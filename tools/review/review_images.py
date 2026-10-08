# -*- coding: utf-8 -*-
"""图片审查：自动挑出可疑图片，并生成对照表（contact sheet）供人工逐张核验。

可疑判定：
  1) 与同药另一张图差异极大（A/B 图中必有一张不对）
  2) 明显是图表/公式/线稿：颜色少、白底占比极高、纯色块占比高
  3) 尺寸过小
输出：
  review/sheet_XX.png    对照表（每格标注 药名_序号）
  review/flagged.txt     可疑清单 + 原因
  review/missing.txt     缺图药味
"""
import colorsys
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "review")

CELL = 190
COLS = 6
LABEL_H = 20


def analyze(path):
    """返回图片特征：尺寸、颜色数、白底占比、平均饱和、边缘密度、主色占比"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((64, 64))
    px = list(small.getdata())

    # 量化颜色数
    q = set()
    white = 0
    sat_sum = 0.0
    for (r, g, b) in px:
        q.add((r >> 5, g >> 5, b >> 5))
        if r > 236 and g > 236 and b > 236:
            white += 1
        mx, mn = max(r, g, b), min(r, g, b)
        sat_sum += 0.0 if mx == 0 else (mx - mn) / float(mx)
    n = float(len(px))

    # 主色占比（最多的量化色）
    cnt = Counter((r >> 4, g >> 4, b >> 4) for (r, g, b) in px)
    top_ratio = cnt.most_common(1)[0][1] / n

    # 边缘密度（Sobel 近似：横向、纵向灰度差）
    gray = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in px]
    edges = 0
    for y in range(64):
        for x in range(63):
            i = y * 64 + x
            if abs(gray[i] - gray[i + 1]) > 30:
                edges += 1
    edge_density = edges / (64.0 * 63)

    return dict(w=w, h=h, colors=len(q), white=white / n,
                sat=sat_sum / n, top=top_ratio, edge=edge_density)


def ahash(path, size=8):
    im = Image.open(path).convert("L").resize((size, size))
    px = list(im.getdata())
    avg = sum(px) / float(len(px))
    return [1 if p > avg else 0 for p in px]


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def load_names():
    with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
        return [h["name"] for h in json.load(f)["herbs"]]


def sheets(names, manifest, flagged, per_sheet=24):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    # 组装所有 (药名, 序号, 路径)
    cells = []
    for name in names:
        files = manifest.get(name, {}).get("files", [])
        for f in files:
            p = os.path.join(IMG, f)
            if os.path.exists(p):
                cells.append((name, f, p))
    rows = (per_sheet + COLS - 1) // COLS
    sheet_w = COLS * CELL
    sheet_h = rows * (CELL + LABEL_H)
    made = 0
    for start in range(0, len(cells), per_sheet):
        chunk = cells[start:start + per_sheet]
        canvas = Image.new("RGB", (sheet_w, sheet_h), (250, 250, 250))
        d = ImageDraw.Draw(canvas)
        for i, (name, f, p) in enumerate(chunk):
            r, c = divmod(i, COLS)
            x, y = c * CELL, r * (CELL + LABEL_H)
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((CELL - 6, CELL - 6))
                canvas.paste(im, (x + 3, y + 3))
            except Exception:
                d.rectangle([x, y, x + CELL, y + CELL], outline=(200, 0, 0))
            mark = "!" if f in flagged else " "
            d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(180, 185, 182))
            d.text((x + 5, y + CELL + 3), mark + f.replace(".jpg", ""), fill=(20, 60, 45))
        made += 1
        canvas.save(os.path.join(OUT, "sheet_%02d.png" % made))
    return made, len(cells)


def main():
    names = load_names()
    with open(os.path.join(HERE, "images_manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    flagged = set()
    reasons = {}
    suspicious = []
    missing = []

    stats = {}
    for name in names:
        files = [f for f in manifest.get(name, {}).get("files", [])
                 if os.path.exists(os.path.join(IMG, f))]
        if not files:
            missing.append(name)
            continue
        feats = []
        for f in files:
            p = os.path.join(IMG, f)
            try:
                a = analyze(p)
                a["path"] = p
                a["file"] = f
                a["hash"] = ahash(p)
                feats.append(a)
                stats[f] = a
            except Exception as e:
                reasons[f] = "无法读取: %s" % e
                flagged.add(f)
                continue

        for a in feats:
            why = []
            # 图表/公式特征：颜色少 + 白底多，或纯色块过大，或几乎没有纹理
            if a["colors"] <= 90 and a["white"] > 0.55:
                why.append("疑似白底图表/公式(颜色%d,白底%.0f%%)" % (a["colors"], a["white"] * 100))
            if a["top"] > 0.62:
                why.append("单一色块占比%.0f%%" % (a["top"] * 100))
            if a["edge"] < 0.012 and a["colors"] < 140:
                why.append("几乎无纹理(边缘%.3f)" % a["edge"])
            if a["sat"] < 0.06 and a["colors"] < 120:
                why.append("近似灰度图")
            if a["w"] < 200 or a["h"] < 160:
                why.append("尺寸过小 %dx%d" % (a["w"], a["h"]))
            if why:
                flagged.add(a["file"])
                reasons[a["file"]] = "；".join(why)
                suspicious.append((name, a["file"], "；".join(why)))

        # A/B 图差异过大
        if len(feats) >= 2:
            d = hamming(feats[0]["hash"], feats[1]["hash"])
            if d >= 30:
                for a in feats[:2]:
                    flagged.add(a["file"])
                    reasons.setdefault(a["file"], "")
                    reasons[a["file"]] = (reasons[a["file"]] + "；" if reasons[a["file"]] else "") + \
                        "与同药另一张图差异极大(汉明距%d)，二者必有一错" % d
                suspicious.append((name, feats[0]["file"], "与 %s 差异极大(%d)" % (feats[1]["file"], d)))

    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with open(os.path.join(OUT, "flagged.txt"), "w", encoding="utf-8") as f:
        f.write("可疑图片清单（共 %d 张）\n" % len(flagged))
        f.write("=" * 70 + "\n")
        for name, fn, why in suspicious:
            f.write("%-10s %-16s %s\n" % (name, fn, why))
    with open(os.path.join(OUT, "missing.txt"), "w", encoding="utf-8") as f:
        f.write("缺图药味（共 %d 味）：\n" % len(missing))
        f.write("".join(missing))

    made, total = sheets(names, manifest, flagged)
    print("images=%d flagged=%d missing=%d sheets=%d" % (total, len(flagged), len(missing), made))
    print("see review/flagged.txt, review/missing.txt, review/sheet_*.png")


if __name__ == "__main__":
    main()
