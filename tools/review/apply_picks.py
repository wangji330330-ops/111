# -*- coding: utf-8 -*-
"""从人工挑选的候选图里确定最终图片，写入 images/ 与 manifest。"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
CAND = os.path.join(HERE, "review", "cand")
MANIFEST = os.path.join(HERE, "images_manifest.json")

# 人工挑选结果：药名 -> [候选文件名, ...]（按显示顺序）
PICK = {
    "雷公藤": ["雷公藤_c01.jpg", "雷公藤_c02.jpg"],     # 根皮饮片 + 本草图谱
    "丁香": ["丁香_c03.jpg", "丁香_c04.jpg"],           # 丁香花蕾（紫/白）
    "西洋参": ["西洋参_c02.jpg", "西洋参_c03.jpg"],     # 切片 + 根
    "槟榔": ["槟榔_c01.jpg", "槟榔_c03.jpg"],           # 果实/饮片
    "磁石": ["磁石_c01.jpg"],                           # 磁铁矿矿石
}


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for name, files in PICK.items():
        # 删掉旧的最终图
        for fn in list(manifest.get(name, {}).get("files", [])):
            p = os.path.join(IMG, fn)
            if os.path.exists(p):
                os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(files, 1):
            src = os.path.join(CAND, cf)
            if not os.path.exists(src):
                print("missing candidate:", cf.encode("unicode_escape").decode("ascii"))
                continue
            dst_name = "%s_%d.jpg" % (name, i)
            shutil.copyfile(src, os.path.join(IMG, dst_name))
            rec["files"].append(dst_name)
            rec["sources"].append({
                "file": dst_name, "src": "manual-pick",
                "title": "%s（人工核验挑选）" % name,
                "descurl": "", "license": "网络图片（见来源页）", "url": "", "size": []})
        manifest[name] = rec
        print("%s -> %d 张" % (name.encode("unicode_escape").decode("ascii"), len(rec["files"])))

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    # 统计
    names_missing = [n for n, v in manifest.items() if not v.get("files")]
    total = sum(len(v.get("files", [])) for v in manifest.values())
    print("total_images=%d missing_herbs=%d" % (total, len(names_missing)))
    if names_missing:
        print("missing:", "".join(names_missing).encode("unicode_escape").decode("ascii"))


if __name__ == "__main__":
    main()
