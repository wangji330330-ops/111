# -*- coding: utf-8 -*-
"""应用人工挑选结果（第二轮候选）。"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
CAND = os.path.join(HERE, "review", "cand2")
MANIFEST = os.path.join(HERE, "images_manifest.json")

PICK = {
    "西洋参": ["西洋参_c01.jpg", "西洋参_c08.jpg"],
}


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    for name, files in PICK.items():
        for fn in list(manifest.get(name, {}).get("files", [])):
            p = os.path.join(IMG, fn)
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
            rec["sources"].append({"file": dst, "src": "manual-pick",
                                   "title": "%s（人工核验挑选）" % name,
                                   "descurl": "", "license": "网络图片", "url": "", "size": []})
        manifest[name] = rec
        print("%s -> %d" % (name.encode("unicode_escape").decode("ascii"), len(rec["files"])))
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    total = sum(len(v.get("files", [])) for v in manifest.values())
    miss = [n for n, v in manifest.items() if not v.get("files")]
    print("total=%d missing=%d %s" % (total, len(miss),
          "".join(miss).encode("unicode_escape").decode("ascii")))


if __name__ == "__main__":
    main()
