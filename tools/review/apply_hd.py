# -*- coding: utf-8 -*-
"""按「列号」把挑好的高清候选入库（列号 = review/hd/ 下该药候选按文件名排序的序号）。

与旧脚本 tools/review/apply_by_col.py 的区别：
  · 数据源是 review/hd/（高清候选，含 index.json 记录分辨率与来源）；
  · 入库时保留高清原图到 images/（桌面版打包会自行压到 420px），
    同时压一份到 docs/images/（网页版用），并把来源写进 images_manifest.json；
  · 会更新 images_credits.txt。

用法:
  python tools/review/apply_hd.py 黄芪:1,3,5 白术:2 甘草:10,4
  python tools/review/apply_hd.py --list 黄芪         # 先看这味有哪些候选

裁掉文字条：列号后面加 @t<上>b<下>l<左>r<右>（百分数），例如
  甘草:10@t12        把第 10 列上面 12% 裁掉（那一条通常是字幕/水印）
  甘草:10@t12b8      上下都裁
"""
import io
import json
import os
import re
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
INDEX = os.path.join(HD, "index.json")
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")
CREDITS = os.path.join(ROOT, "images_credits.txt")
MAX_SIDE = 420
QUALITY = 70


def parse_crop(spec):
    """'t12b8' -> (上, 右, 下, 左) 百分比"""
    c = {"t": 0.0, "r": 0.0, "b": 0.0, "l": 0.0}
    for k, v in re.findall(r"([trbl])(\d+(?:\.\d+)?)", spec or ""):
        c[k] = max(0.0, min(45.0, float(v)))
    return c["t"], c["r"], c["b"], c["l"]


def apply_crop(im, crop):
    t, r, b, l = crop
    if not (t or r or b or l):
        return im
    w, h = im.size
    box = (int(w * l / 100.0), int(h * t / 100.0),
           int(w * (1 - r / 100.0)), int(h * (1 - b / 100.0)))
    if box[2] - box[0] < 80 or box[3] - box[1] < 80:
        return im
    return im.crop(box)


def load_index():
    return json.load(io.open(INDEX, encoding="utf-8"))


def candidates(name, idx):
    items = idx.get(name) or []
    return [m for m in items if os.path.exists(os.path.join(HD, m["file"]))]


def save_web(src_path, dst_path, crop=None):
    im = Image.open(src_path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    if crop:
        im = apply_crop(im, crop)
    w, h = im.size
    if max(w, h) > MAX_SIDE:
        k = float(MAX_SIDE) / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    im.save(dst_path, "JPEG", quality=QUALITY, optimize=True)


def save_origin(src_path, dst_path, crop=None):
    if not crop or not any(crop):
        shutil.copyfile(src_path, dst_path)
        return
    im = Image.open(src_path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im = apply_crop(im, crop)
    im.save(dst_path, "JPEG", quality=92, optimize=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    idx = load_index()

    if "--list" in sys.argv:
        for name in args:
            cs = candidates(name, idx)
            print("%s：%d 张候选" % (name, len(cs)))
            for i, m in enumerate(cs, 1):
                print("   第%-2d列  %4dx%-5d %s  %s" %
                      (i, m["w"], m["h"], "已裁文字条" if m.get("trimmed") else "          ",
                       m["src"][:80]))
        return 0

    if not args:
        print(__doc__)
        return 2

    m = json.load(io.open(MANIFEST, encoding="utf-8"))
    credit_lines = []
    done, skipped = 0, []

    for spec in args:
        if ":" not in spec:
            continue
        name, cols = spec.split(":", 1)
        cs = candidates(name, idx)
        pick = []
        for c in cols.replace("，", ",").split(","):
            c = c.strip()
            crop = (0.0, 0.0, 0.0, 0.0)
            if "@" in c:
                c, spec_crop = c.split("@", 1)
                crop = parse_crop(spec_crop)
            if not c.isdigit():
                continue
            i = int(c) - 1
            if 0 <= i < len(cs):
                pick.append((cs[i], crop))
            else:
                skipped.append("%s第%s列(超出%d)" % (name, c, len(cs)))
        if not pick:
            if name not in [s.split("(")[0] for s in skipped]:
                skipped.append("%s(无有效列)" % name)
            continue

        # 清掉旧图（images/ 与 docs/images/ 都要清）
        for old in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, old)
                if os.path.exists(p):
                    os.remove(p)

        rec = {"files": [], "sources": []}
        for i, (item, crop) in enumerate(pick, 1):
            src = os.path.join(HD, item["file"])
            dst = "%s_%d.jpg" % (name, i)
            if not os.path.isdir(IMG):
                os.makedirs(IMG)
            save_origin(src, os.path.join(IMG, dst), crop)
            if os.path.isdir(WEBIMG):
                save_web(src, os.path.join(WEBIMG, dst), crop)
            rec["files"].append(dst)
            rec["sources"].append({
                "file": dst, "src": item.get("site") or "网络图片",
                "title": (item.get("title") or "")[:60], "descurl": item.get("src") or "",
                "license": "网络图片（见来源页）", "url": item.get("src") or "",
                "size": [item["w"], item["h"]],
                "crop": crop if any(crop) else None,
            })
            credit_lines.append("%s\t%s\t%dx%d%s\t%s" %
                                (name, dst, item["w"], item["h"],
                                 ("（裁 %s）" % ",".join(
                                     "%s%.0f%%" % (k, v) for k, v in
                                     zip("trbl", crop) if v)) if any(crop) else "",
                                 item.get("src") or ""))
        m[name] = rec
        done += 1
        print("  %-8s 第%-10s -> %s" % (name, cols, rec["files"]))

    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    if credit_lines:
        with io.open(CREDITS, "a", encoding="utf-8") as f:
            f.write("\n# ---- 高清重挑 %s ----\n" % __import__("time").strftime("%Y-%m-%d %H:%M"))
            f.write("\n".join(credit_lines) + "\n")

    print("")
    print("替换 %d 味" % done)
    if skipped:
        print("跳过: %s" % " ".join(skipped))
    total = sum(len(v.get("files", [])) for v in m.values())
    withimg = sum(1 for v in m.values() if v.get("files"))
    print("图库: %d 味有图 / %d 张" % (withimg, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
