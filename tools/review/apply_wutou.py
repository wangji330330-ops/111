# -*- coding: utf-8 -*-
"""把核验过的 360 候选图写入图库（川乌/附子），并同步到 docs/。"""
import io
import json
import os
import shutil

ROOT = r"E:\正常玩\中药复习程序"
CAND = os.path.join(ROOT, "review", "c360")
IMG = os.path.join(ROOT, "images")
WEBIMG = os.path.join(ROOT, "docs", "images")
MANIFEST = os.path.join(ROOT, "images_manifest.json")

# 人工核验后挑选（都是制川乌 / 附子饮片实物图）
PICK = {
    "川乌": ["川乌_c02.jpg", "川乌_c03.jpg"],   # 盘装黑褐色制川乌饮片、带"制川乌"标签
    "附子": ["附子_c05.jpg", "附子_c07.jpg"],   # 浅褐色炮附子片、深色附子片
}


def main():
    with io.open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)

    for name, files in PICK.items():
        # 清掉可能的旧图
        for fn in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(files, 1):
            src = os.path.join(CAND, cf)
            if not os.path.exists(src):
                print("missing candidate:", cf.encode("unicode_escape").decode("ascii"))
                continue
            dst = "%s_%d.jpg" % (name, i)
            shutil.copyfile(src, os.path.join(IMG, dst))
            rec["files"].append(dst)
            rec["sources"].append({
                "file": dst, "src": "360图片", "title": "%s 中药饮片（人工核验挑选）" % name,
                "descurl": "", "license": "网络图片（见来源页）", "url": "", "size": []})
        m[name] = rec
        print("%s -> %d 张" % (name.encode("unicode_escape").decode("ascii"), len(rec["files"])))

    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)

    total = sum(len(v.get("files", [])) for v in m.values())
    miss = [n for n, v in m.items() if not v.get("files")]
    print("images=%d missing=%d %s" % (total, len(miss),
          " ".join(miss).encode("unicode_escape").decode("ascii")))


if __name__ == "__main__":
    main()
