# -*- coding: utf-8 -*-
"""把 review/c360new/ 里核验过的候选图写入图库（支持每味 1~2 张）。

用法:
    python tools/review/apply_new_pick.py 紫苏梗:紫苏梗_c01.jpg,紫苏梗_c02.jpg 葱白:葱白_c03.jpg ...
仅指定 1 张也可以。

写入内容:
    images/<药名>_1.jpg  ...        原始图库（桌面版打包用）
    docs/images/<药名>_1.jpg ...    网页版图库
    images_manifest.json            图片索引（同步更新）
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAND = os.path.join(ROOT, "review", "c360new")
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    with io.open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    if not os.path.isdir(IMG):
        os.makedirs(IMG)
    if not os.path.isdir(WEBIMG):
        os.makedirs(WEBIMG)

    ok_count = 0
    for spec in sys.argv[1:]:
        if ":" not in spec:
            continue
        name, files = spec.split(":", 1)
        picks = [x for x in files.split(",") if x.strip()]
        # 清掉旧图
        for fn in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(picks, 1):
            src = os.path.join(CAND, cf)
            if not os.path.exists(src):
                print("  缺候选文件: %s" % cf)
                continue
            dst = "%s_%d.jpg" % (name, i)
            shutil.copyfile(src, os.path.join(IMG, dst))
            rec["files"].append(dst)
            rec["sources"].append({
                "file": dst, "src": "360图片",
                "title": "%s 中药饮片（人工核验挑选）" % name,
                "descurl": "", "license": "网络图片（见来源页）", "url": "", "size": [],
            })
        if rec["files"]:
            m[name] = rec
            ok_count += 1
            print("  %s -> %d 张" % (name.encode("unicode_escape").decode("ascii"),
                                     len(rec["files"])))
        else:
            print("  %s 无有效图片，已跳过" % name.encode("unicode_escape").decode("ascii"))

    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    total = sum(len(v.get("files", [])) for v in m.values())
    withimg = sum(1 for v in m.values() if v.get("files"))
    print("本次写入 %d 味；图库共 %d 味有图 / %d 张" % (ok_count, withimg, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
