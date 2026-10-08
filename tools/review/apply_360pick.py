# -*- coding: utf-8 -*-
"""通用：把核验过的 360 候选图写入图库（可多次调用）。
用法: python apply_360pick.py 五灵脂:五灵脂_c01.jpg,五灵脂_c08.jpg
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAND = os.path.join(ROOT, "review", "c360")
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")


def main():
    if len(sys.argv) < 2:
        print("usage: apply_360pick.py 药名:文件1,文件2")
        return 2
    with io.open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)

    for spec in sys.argv[1:]:
        if ":" not in spec:
            continue
        name, files = spec.split(":", 1)
        files = [x for x in files.split(",") if x.strip()]
        for fn in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(files, 1):
            src = os.path.join(CAND, cf)
            if not os.path.exists(src):
                print("missing:", cf.encode("unicode_escape").decode("ascii"))
                continue
            dst = "%s_%d.jpg" % (name, i)
            shutil.copyfile(src, os.path.join(IMG, dst))
            rec["files"].append(dst)
            rec["sources"].append({
                "file": dst, "src": "360图片", "title": "%s 中药饮片（人工核验挑选）" % name,
                "descurl": "", "license": "网络图片（见来源页）", "url": "", "size": []})
        m[name] = rec
        print("%s -> %d" % (name.encode("unicode_escape").decode("ascii"), len(rec["files"])))

    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    total = sum(len(v.get("files", [])) for v in m.values())
    miss = [n for n, v in m.items() if not v.get("files")]
    print("images=%d missing=%d %s" % (total, len(miss),
          " ".join(miss).encode("unicode_escape").decode("ascii")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
