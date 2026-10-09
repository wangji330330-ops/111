# -*- coding: utf-8 -*-
"""按 review/new_picks.txt 把候选图入库（带文件存在性校验）。

用法: python tools/review/apply_new_picks.py
挑选表格式: 每行 "药名<TAB>编号,编号"，编号对应 review/c360new/<药名>_cNN.jpg
（与 tools/review/sheet_new.py 生成的对照表顺序一致）
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
PICKS = os.path.join(ROOT, "review", "new_picks.txt")


def sheet_order():
    """与 sheet_new.py 完全一致的药味顺序，用于校验挑选表是否对得上"""
    sys.path.insert(0, ROOT)
    import herbs_additions as A
    enabled = getattr(A, "ENABLED_BATCHES", [1])
    names = []
    for n in enabled:
        for rec in getattr(A, "ADDITIONS_%d" % n, []):
            names.append(rec[0])
    return [n for n in names if os.path.exists(os.path.join(CAND, "%s_c01.jpg" % n))]


def main():
    if not os.path.exists(PICKS):
        print("找不到挑选表: %s" % PICKS)
        return 2
    lines = [ln.strip() for ln in io.open(PICKS, encoding="utf-8").read().split("\n")]
    picks = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        if "\t" not in ln:
            print("  跳过格式错误行: %s" % ln)
            continue
        name, nums = ln.split("\t", 1)
        nlist = [x.strip() for x in nums.split(",") if x.strip()]
        picks.append((name.strip(), nlist))

    order = sheet_order()
    order_set = set(order)
    # 顺序一致性检查
    pick_names = [n for n, _ in picks if n in order_set]
    mismatched = [n for n in pick_names if n not in order_set]
    if mismatched:
        print("警告：以下药名不在候选清单中: %s" % " ".join(mismatched))

    ok, missing_files, not_in_order = 0, [], []
    with io.open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    for d in (IMG, WEBIMG):
        if not os.path.isdir(d):
            os.makedirs(d)

    for name, nums in picks:
        if name not in order_set:
            not_in_order.append(name)
            continue
        files = []
        for k in nums:
            try:
                fn = "%s_c%02d.jpg" % (name, int(k))
            except ValueError:
                print("  编号非法: %s %s" % (name, k))
                continue
            if os.path.exists(os.path.join(CAND, fn)):
                files.append(fn)
            else:
                missing_files.append(fn)
        if not files:
            print("  %s 无有效候选，跳过" % name)
            continue
        # 清旧图
        for old in list(m.get(name, {}).get("files", [])):
            for d in (IMG, WEBIMG):
                p = os.path.join(d, old)
                if os.path.exists(p):
                    os.remove(p)
        rec = {"files": [], "sources": []}
        for i, cf in enumerate(files, 1):
            dst = "%s_%d.jpg" % (name, i)
            shutil.copyfile(os.path.join(CAND, cf), os.path.join(IMG, dst))
            rec["files"].append(dst)
            rec["sources"].append({
                "file": dst, "src": "360图片",
                "title": "%s 中药饮片（人工核验挑选）" % name,
                "descurl": "", "license": "网络图片（见来源页）", "url": "", "size": [],
            })
        m[name] = rec
        ok += 1

    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)

    total = sum(len(v.get("files", [])) for v in m.values())
    withimg = sum(1 for v in m.values() if v.get("files"))
    print("")
    print("挑选条目: %d 味 | 成功入库: %d 味" % (len(picks), ok))
    if missing_files:
        print("缺失的候选文件（编号可能对错了，请核对）: %d 个" % len(missing_files))
        for x in missing_files[:20]:
            print("   !", x)
    if not_in_order:
        print("不在候选清单中的药名: %s" % " ".join(not_in_order))
    print("图库现状: %d 味有图 / %d 张" % (withimg, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
