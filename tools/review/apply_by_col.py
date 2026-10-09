# -*- coding: utf-8 -*-
"""按“列号”入库（列号 = 候选文件按文件名排序后的序号）。

用法: python tools/review/apply_by_col.py 禹余粮:8 藜芦:3 浮小麦:3,8 ...
说明: 列号与 review/numbered/*.png 及 review/numbered_check.html 上标注的「第N列」一致，
      避免在缩略图里认图导致的错位。
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAND = os.path.join(ROOT, "review", "c360fix2")
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")


def candidates(name):
    return sorted(f for f in os.listdir(CAND)
                  if f.startswith(name + "_c") and f.endswith(".jpg"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    with io.open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    done, skipped = 0, []
    for spec in sys.argv[1:]:
        if ":" not in spec:
            continue
        name, cols = spec.split(":", 1)
        cand = candidates(name)
        pick = []
        for c in cols.split(","):
            c = c.strip()
            if not c.isdigit():
                continue
            i = int(c) - 1
            if 0 <= i < len(cand):
                pick.append(cand[i])
            else:
                skipped.append("%s第%s列(超出%d)" % (name, c, len(cand)))
        if not pick:
            skipped.append("%s(无有效列)" % name)
            continue
        # 清旧图
        for old in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, old)
                if os.path.exists(p):
                    os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(pick, 1):
            dst = "%s_%d.jpg" % (name, i)
            shutil.copyfile(os.path.join(CAND, cf), os.path.join(IMG, dst))
            if os.path.isdir(WEBIMG):
                shutil.copyfile(os.path.join(CAND, cf), os.path.join(WEBIMG, dst))
            rec["files"].append(dst)
            rec["sources"].append({"file": dst, "src": "360图片",
                "title": "%s 中药饮片（人工核验挑选）" % name, "descurl": "",
                "license": "网络图片（见来源页）", "url": "", "size": []})
        m[name] = rec
        done += 1
        print("  %-6s 第%-6s -> %s" % (name, cols, rec["files"]))
    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
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
