# -*- coding: utf-8 -*-
"""修复 review/hd：以**磁盘上的真实文件**为准重建 index.json。

背景：早先一次「按干净度重排」的改名写错了（in-place 改名撞名先删后改），
后来又按错误的名字表重编了索引，导致 index.json 里的文件名与磁盘对不上。
本脚本不猜、不补，只做一件事：扫描真实文件，重建一份自洽的索引。

  · 文件名 药名_cNN.jpg 是唯一真相；
  · 能按文件名对上旧记录的，保留它的 src/site/title；
  · 对不上的，来源标成「图片平台（来源未记录）」，不编造；
  · 重新编号成 c01..cNN，保证「第 N 列」连续。

用法: python tools/review/repair_hd.py
"""
import io
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
INDEX = os.path.join(HD, "index.json")
PAT = re.compile(r"^(?P<name>.+)_c\d+\.jpg$")


def main():
    old = {}
    if os.path.exists(INDEX):
        try:
            for name, items in json.load(io.open(INDEX, encoding="utf-8")).items():
                for m in items:
                    old.setdefault(m.get("file") or "", m)
        except Exception:
            pass

    groups = {}
    for fn in sorted(os.listdir(HD)):
        if not fn.lower().endswith(".jpg"):
            continue
        m = PAT.match(fn)
        if not m:
            continue
        groups.setdefault(m.group("name"), []).append(fn)

    idx, orphan, meta_kept, meta_lost = {}, 0, 0, 0
    total = 0
    for name, files in groups.items():
        items = []
        # 先全部改成临时名，避免撞名（这次学乖了）
        staged = []
        for i, fn in enumerate(sorted(files)):
            t = os.path.join(HD, "__r_%03d.jpg" % i)
            os.replace(os.path.join(HD, fn), t)
            staged.append((fn, t))
        for i, (fn, t) in enumerate(staged, 1):
            new = "%s_c%02d.jpg" % (name, i)
            os.replace(t, os.path.join(HD, new))
            rec = old.get(fn)
            try:
                with Image.open(os.path.join(HD, new)) as im:
                    w, h = im.size
            except Exception:
                w, h = 0, 0
            if rec:
                meta_kept += 1
                items.append({"file": new, "w": w, "h": h,
                              "src": rec.get("src") or "", "title": rec.get("title") or "",
                              "site": rec.get("site") or "", "trimmed": rec.get("trimmed", False)})
            else:
                meta_lost += 1
                items.append({"file": new, "w": w, "h": h, "src": "",
                              "title": "", "site": "图片平台", "trimmed": False})
        idx[name] = items
        total += len(items)

    # 清掉不认识的散图（临时文件之类）
    for fn in os.listdir(HD):
        if fn.lower().endswith(".jpg") and not PAT.match(fn):
            os.remove(os.path.join(HD, fn))
            orphan += 1

    with io.open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    short = [(n, len(v)) for n, v in idx.items() if len(v) < 10]
    print("重建索引：%d 味 / %d 张（来源记录完整 %d，丢失 %d，清散图 %d）"
          % (len(idx), total, meta_kept, meta_lost, orphan))
    print("不足 10 张的 %d 味" % len(short))
    return 0


if __name__ == "__main__":
    sys.exit(main())
