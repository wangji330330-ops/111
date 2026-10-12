# -*- coding: utf-8 -*-
"""把《道地药材产品认证目录》匹配到题库药名，并统计覆盖率。

匹配优先级（从可靠到宽松）：
  1. 产品名称去掉产地前缀后正好等于题库药名（浙白术 → 白术）
  2. 别名列表里出现题库药名（浙元胡 别名含「延胡索」→ 延胡索）
  3. 药用部位里的原植物名等于题库药名（本品为玄参科植物玄参的干燥根 → 玄参）
  4. 产品名称包含题库药名（杭白芍 ⊃ 白芍）

用法: python tools/review/match_daodi.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAODI = os.path.join(ROOT, "review", "_src", "daodi.json")
OUT = os.path.join(ROOT, "review", "_src", "daodi_match.json")
REPORT = os.path.join(ROOT, "review", "_src", "daodi_report.txt")

# 道地药材名前面的产地前缀
PREFIX = ("浙", "川", "云", "贵", "广", "怀", "杭", "台", "温", "淳", "亳", "怀",
          "东北", "关", "西", "南", "北", "蒙", "藏", "维", "秦", "岷", "江",
          "建", "苏", "鲁", "豫", "湘", "鄂", "赣", "闽", "桂", "琼", "渝", "甘")

NOPLANT = re.compile(r"(本品为|本品以|为|的|干燥|新鲜|近成熟|成熟|未成熟|或|、|，|。)")


def plant_names(part):
    """从「本品为玄参科植物玄参的干燥根」里抽出植物名"""
    m = re.search(r"植物([^的]+)的", part)
    if not m:
        m = re.search(r"真菌([^的]+)的", part)
    if not m:
        m = re.search(r"动物([^的]+)的", part)
    if not m:
        return []
    seg = m.group(1)
    seg = seg.split("（")[0]
    seg = re.split(r"[、或及]", seg)
    out = []
    for x in seg:
        x = NOPLANT.sub("", x).strip()
        if 1 <= len(x) <= 8:
            out.append(x)
    return out


def main():
    daodi = json.load(io.open(DAODI, encoding="utf-8"))
    herbs = [h["name"] for h in
             json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]]
    hset = set(herbs)

    def strip_prefix(n):
        for p in PREFIX:
            if n.startswith(p) and len(n) > len(p) + 1 and n[len(p):] in hset:
                return n[len(p):]
        return n

    match, why = {}, {}
    for prod, v in daodi.items():
        base = strip_prefix(prod)
        hit = None
        if base in hset:
            hit, w = base, "产品名"
        else:
            for a in re.split(r"[、,，;；]", v["alias"]):
                a = a.strip()
                if a in hset:
                    hit, w = a, "别名"
                    break
        if not hit:
            for p in plant_names(v["part"]):
                if p in hset:
                    hit, w = p, "原植物"
                    break
        if not hit:
            for h in herbs:
                if len(h) >= 2 and h in prod:
                    hit, w = h, "包含"
                    break
        if hit:
            if hit not in match:
                match[hit] = {
                    "prod": prod, "origin": v["origin"], "area": v["area"],
                    "alias": v["alias"], "part": v["part"], "how": w,
                }
                why[w] = why.get(w, 0) + 1

    json.dump(match, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    miss = [h for h in herbs if h not in match]
    L = ["道地药材目录 241 条 → 命中题库 %d 味 / 共 %d 味（覆盖 %.0f%%）"
         % (len(match), len(herbs), 100.0 * len(match) / len(herbs)),
         "匹配方式：%s" % why, "",
         "未覆盖的 %d 味：" % len(miss), "、".join(miss), "",
         "样例："]
    for k in list(match)[:10]:
        v = match[k]
        L.append("  %s(←%s/%s) | %s | 别名:%s | %s"
                 % (k, v["prod"], v["how"], v["origin"], v["alias"][:36], v["part"][:34]))
    io.open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:6]))
    print("-> %s" % REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
