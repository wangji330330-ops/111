# -*- coding: utf-8 -*-
"""候选图质检 v2：判断图上有没有文字 / 是不是商品包装图 / 风景图。

为什么不用 v1 那一版：单一「行跳变密度」会把**薄片药材**（麦冬片、黄芪片、
槟榔片——整图都是密集边缘）误判成文字，又会漏掉**大字广告**
（蚕沙那种「今年新货 一斤包邮」大字，笔画稀疏，行密度并不高）。

v2 用四个互补信号：
  1. 局部峰值   peak/base —— 一部分行明显比其余行"花"（横幅/字幕条的特征），
                 薄片药材整图都花，peak≈base，不会被误伤；
  2. 全局中位   median    —— 整幅都是字（说明书长图、海报）；
  3. 大色块占比 flat      —— 近白/近黑底色比例（价签、商品白底图）；
  4. 主体占比   subject   —— 去掉底色后剩下的主体占多少（白底商品图主体很小）。

判定：
  ad      广告模板（有字 + 大面积纯色底）      → 直接丢掉
  text    整幅是文字（说明图/海报）            → 直接丢掉
  product 白底商品图（主体小）                 → 降权，排到最后
  scene   大面积纯绿/纯蓝低饱和（风景）        → 降权
  clean   正常药材实拍                          → 优先
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
QC = os.path.join(HD, "qc.json")

ROW_EDGE = 35        # 行内相邻像素差超过它算一次"跳变"


def analyse(path):
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.thumbnail((480, 480))
    g = np.asarray(im.convert("L"), dtype=np.int16)
    rgb = np.asarray(im, dtype=np.int16)
    h, w = g.shape

    dx = np.abs(np.diff(g, axis=1))
    d = (dx > ROW_EDGE).mean(axis=1)          # 每行跳变密度
    med = float(np.median(d))
    peak = float(np.percentile(d, 93))
    base = float(np.percentile(d, 30))
    local = peak / max(base, 1e-4)             # 局部峰值倍数

    flat = float(((g > 238) | (g < 16)).mean())
    sat = float((rgb.max(axis=2) - rgb.min(axis=2)).mean())

    # 主体占比：把近白/近黑底去掉后，剩下的像素比例
    mask = (g <= 238) & (g >= 16)
    subject = float(mask.mean())

    # 绿色占比（风景图常见）
    r, gg, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    green = float(((gg > r + 18) & (gg > b + 18)).mean())

    return dict(med=round(med, 4), peak=round(peak, 4), base=round(base, 4),
                local=round(local, 2), flat=round(flat, 3), sat=round(sat, 1),
                subject=round(subject, 3), green=round(green, 3))


def verdict(s):
    # 整幅是字：中位跳变密度高，且底色浅
    if s["med"] > 0.055 and s["flat"] > 0.10:
        return "text"
    # 广告模板：一条明显比周围"花"的横幅 + 大面积纯色底
    if s["local"] > 6.0 and s["peak"] > 0.030 and s["flat"] > 0.16:
        return "ad"
    if s["local"] > 9.0 and s["peak"] > 0.045:
        return "ad"
    # 白底商品图：大片纯色，主体只占很小一块
    if s["flat"] > 0.55 and s["subject"] < 0.45:
        return "product"
    # 风景：大面积绿色且几乎无跳变
    if s["green"] > 0.45 and s["med"] < 0.02:
        return "scene"
    # 轻度可疑
    if s["local"] > 4.5 and s["peak"] > 0.025:
        return "warn"
    if s["med"] > 0.045:
        return "warn"
    return "clean"


RANK = {"clean": 0, "warn": 1, "product": 2, "scene": 2, "ad": 9, "text": 9}
DROP = ("ad", "text")


def scan(files=None, verbose=False):
    files = files or sorted(f for f in os.listdir(HD) if f.endswith(".jpg"))
    res, counts = {}, {}
    for i, fn in enumerate(files):
        try:
            s = analyse(os.path.join(HD, fn))
        except Exception as e:
            s = {"err": str(e)[:40]}
        v = verdict(s) if "err" not in s else "clean"
        s["v"] = v
        res[fn] = s
        counts[v] = counts.get(v, 0) + 1
        if verbose and i % 200 == 0:
            print("  %d/%d" % (i, len(files)), flush=True)
    return res, counts


def main():
    if "--report" in sys.argv:
        res, counts = scan(verbose=True)
        json.dump(res, io.open(QC, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("扫描 %d 张：%s" % (len(res), counts))
        return 0
    for p in sys.argv[1:]:
        s = analyse(p)
        print("%-40s %s  %s" % (os.path.basename(p), verdict(s), s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
