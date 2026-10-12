# -*- coding: utf-8 -*-
"""按 review/picks_user.txt 里的「药名:列号」批量入库，并给出四份清单：

  ① 我抓到候选、但用户一张都没选的药味
  ② 入库后题库里仍然完全没有图片的药味
  ③ 列号越界、没能入库的（选了但一列都没生效）
  ④ 只选了 1 张图的药味

用法:
  python tools/review/apply_user_picks.py            # 只预演 + 报告（不落盘）
  python tools/review/apply_user_picks.py --apply    # 真入库
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PICKS = os.path.join(ROOT, "review", "picks_user.txt")
HD = os.path.join(ROOT, "review", "hd")
INDEX = os.path.join(HD, "index.json")
NAMES_FILE = os.path.join(ROOT, "review", "refetch_names.txt")
REPORT = os.path.join(ROOT, "review", "picks_report.txt")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_hd  # noqa: E402
from apply_hd import candidates, main as apply_main  # noqa: E402


def use_round2():
    """切到第二轮：review/picks_user2.txt + review/hd2/"""
    global PICKS, HD, INDEX, NAMES_FILE, REPORT
    PICKS = os.path.join(ROOT, "review", "picks_user2.txt")
    HD = os.path.join(ROOT, "review", "hd2")
    INDEX = os.path.join(HD, "index.json")
    NAMES_FILE = os.path.join(ROOT, "review", "refetch_names2.txt")
    REPORT = os.path.join(ROOT, "review", "picks_report2.txt")
    # apply_hd 里也有自己的一份 HD/INDEX，必须一起切，否则列号会对到别的目录
    apply_hd.HD = HD
    apply_hd.INDEX = INDEX


def parse_picks():
    specs, want = [], {}
    for line in io.open(PICKS, encoding="utf-8"):
        line = line.strip().replace("：", ":")
        if not line or ":" not in line:
            continue
        name, cols = line.split(":", 1)
        cols = cols.replace("，", ",").replace("、", ",").replace(" ", "")
        nums = [int(c) for c in cols.split(",") if c.strip().isdigit()]
        if nums:
            specs.append("%s:%s" % (name, ",".join(str(n) for n in nums)))
            want[name] = nums
    return specs, want


def report(want, applied_note=""):
    idx = json.load(io.open(INDEX, encoding="utf-8"))
    names = [l.strip() for l in io.open(NAMES_FILE, encoding="utf-8") if l.strip()]
    herbs = json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]
    manifest = json.load(io.open(os.path.join(ROOT, "images_manifest.json"), encoding="utf-8"))

    L = []
    L.append("挑图结果核对")
    L.append("=" * 40)
    L.append("重挑清单 %d 味；你选了 %d 味%s" % (len(names), len(want), applied_note))
    L.append("")

    not_picked = [n for n in names if n not in want and (idx.get(n) or [])]
    no_cand = [n for n in names if not (idx.get(n) or [])]
    L.append("① 有候选、但你没选的（%d 味）——这些还是原来的旧图：" % len(not_picked))
    L.append("   " + ("、".join(not_picked) if not_picked else "无"))
    if no_cand:
        L.append("   （另有 %d 味连候选都没抓到：%s）" % (len(no_cand), "、".join(no_cand)))
    L.append("")

    bad = []
    for n, cols in want.items():
        cs = candidates(n, idx)
        over = [c for c in cols if c < 1 or c > len(cs)]
        if over or not cs:
            bad.append("%s（选了第 %s 列，但该味只有 %d 张候选）"
                       % (n, "、".join(map(str, over)) or "无", len(cs)))
    L.append("③ 列号越界 / 没入库的（%d 味）：" % len(bad))
    L.append("   " + ("；".join(bad) if bad else "无"))
    L.append("")

    thin = sorted(n for n, c in want.items() if len(c) == 1)
    L.append("④ 选中的图 ≤1 张的（%d 味）——需要补图：" % (len(not_picked) + len(thin)))
    L.append("   · 一张都没选（0 张，%d 味）：%s" % (len(not_picked), "、".join(not_picked) or "无"))
    L.append("   · 只选了 1 张（1 张，%d 味）：%s" % (len(thin), "、".join(thin) or "无"))
    L.append("   合计：%s" % "、".join(not_picked + thin))
    L.append("")

    # 全库口径：不管在不在本次清单里，只要最终图片 ≤1 张就列出来
    allthin = sorted(h["name"] for h in herbs
                     if len(manifest.get(h["name"], {}).get("files", [])) <= 1)
    L.append("⑤ 全库图片 ≤1 张的（%d 味，含不在本次清单里的）：" % len(allthin))
    L.append("   " + ("、".join(allthin) if allthin else "无"))

    noimg = [h["name"] for h in herbs if not manifest.get(h["name"], {}).get("files")]
    outside = [n for n in noimg if n not in names]
    L.append("② 题库里仍然没有图片的（%d 味）：" % len(noimg))
    L.append("   " + ("、".join(noimg) if noimg else "无"))
    if outside:
        L.append("   其中不在本次重挑清单里的（%d 味，需要另外补图）：" % len(outside))
        L.append("   " + "、".join(outside))

    text = "\n".join(L)
    io.open(REPORT, "w", encoding="utf-8").write(text + "\n")
    print(text)
    print("\n-> review/picks_report.txt")


def main():
    if "--round2" in sys.argv:
        use_round2()
    specs, want = parse_picks()
    print("解析到 %d 条选择（%s）\n" % (len(specs), "第二轮" if "--round2" in sys.argv else "第一轮"))
    note = ""
    if "--apply" in sys.argv:
        sys.argv = [sys.argv[0]] + specs
        apply_main()
        note = "（已入库）"
    report(want, note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
