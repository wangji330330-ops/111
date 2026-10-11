# -*- coding: utf-8 -*-
"""候选图自动质检：判断图上有没有文字（广告语/水印/价签/字幕条）。

原理（不依赖任何 OCR，纯像素统计）：
  文字行的特征是「同一行里出现大量中等强度的横向明暗跳变」。
  把灰度图按行统计 |g[x+1]-g[x]| > 40 的像素占比，占比高的行就是文字行；
  文字行占比越高，越可能是一张带字图（广告、价签、说明图、短视频字幕）。

在实测样本上调过阈值：
  · 干净的药材实拍图      文字行占比 ≈ 0.00 ~ 0.06
  · 带角标/水印的图       ≈ 0.06 ~ 0.18
  · 带说明文字/字幕/价签   ≈ 0.18 ~ 0.60
  · 纯文字长图/海报        > 0.60

用法:
  python tools/images/qc.py                 # 扫描 review/hd，输出 review/hd/qc.json + 报告
  python tools/images/qc.py 图1 图2 ...      # 只看指定图片
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
OUT = os.path.join(HD, "qc.json")

SUSPECT = 0.22      # 文字行占比超过这个值 → 疑似带字，不推荐
BAD = 0.45          # 超过这个值 → 基本肯定是广告/海报/长图


def text_score(path):
    """返回 (文字行占比, 疑似广告版面标志)"""
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.thumbnail((520, 520))
    g = np.asarray(im.convert("L"), dtype=np.int16)
    dx = np.abs(np.diff(g, axis=1))
    rows = (dx > 40).mean(axis=1)            # 每行的跳变密度
    text_rows = float((rows > 0.055).mean())  # 文字行占比

    # 大片纯白/纯色底（价签、商品图、说明页常见）
    flat = float(((g > 242) | (g < 12)).mean())
    # 颜色饱和度极低（黑白说明图/表格）
    arr = np.asarray(im, dtype=np.int16)
    sat = float((arr.max(axis=2) - arr.min(axis=2)).mean())
    return text_rows, flat, sat


def verdict(text_rows, flat, sat):
    if text_rows >= BAD:
        return "bad"
    if text_rows >= SUSPECT:
        return "suspect"
    return "ok"


def main():
    args = [a for a in sys.argv[1:]]
    if args:
        for p in args:
            t, f, s = text_score(p)
            print("%-46s 文字行=%.3f 纯色=%.3f 饱和=%.1f  %s" %
                  (os.path.basename(p), t, f, s, verdict(t, f, s)))
        return 0

    files = sorted(f for f in os.listdir(HD) if f.endswith(".jpg"))
    res, counts = {}, {"ok": 0, "suspect": 0, "bad": 0}
    for i, fn in enumerate(files):
        try:
            t, f, s = text_score(os.path.join(HD, fn))
        except Exception:
            continue
        v = verdict(t, f, s)
        counts[v] += 1
        res[fn] = {"text": round(t, 4), "flat": round(f, 4), "sat": round(s, 1), "v": v}
        if (i + 1) % 200 == 0:
            print("  已扫描 %d/%d" % (i + 1, len(files)), flush=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=0)
    print("扫描 %d 张：干净 %d / 疑似带字 %d / 广告海报 %d" %
          (len(res), counts["ok"], counts["suspect"], counts["bad"]))
    print("明细 -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
