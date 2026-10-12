# -*- coding: utf-8 -*-
"""从《天津市中药饮片炮制规范》2022 年版抽「药用部位 / 产地 / 别名」。

为什么用它（权威性）：
  它是天津市药品监督管理局批准颁布的**省级中药饮片炮制规范**，
  属于国家药品标准的重要补充，是法定技术标准；正文按
  【品名】【来源】【炮制】【性状】…书写，其中【来源】的写法是：

      本品为茜草科植物红大戟 Knoxia valerianoides …的干燥块根。
      主产于福建、广西、广东、云南等地。秋、冬二季采挖…

  一条里同时给出了「药用部位（干燥块根）」和「主要产地（福建、广西…）」。
  别名在书末「附表Ⅲ 天津市中药饮片常用别名」。

用法: python tools/review/parse_tj.py
输出: review/_src/tj_fields.json  {药名: {part, area, alias, src}}
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "review", "_src", "tj.txt")
OUT = os.path.join(ROOT, "review", "_src", "tj_fields.json")
DUMP = os.path.join(ROOT, "review", "_src", "tj_rows.txt")

# 「的干燥块根」「的新鲜茎」「的干燥成熟果实」……
PART_RE = re.compile(r"的(?:干燥|新鲜|鲜)([^。，、；]{2,12}?)(?:[。，、；]|$)")
# 「主产于福建、广西、广东、云南等地」「产于四川」「主产河南」
AREA_RE = re.compile(r"(?:主产于|主产|产于)([^。]{2,80}?)(?:等地|等省|等区|一带|及周边|$)")


def clean(s):
    return re.sub(r"[\s\u3000]+", "", s or "")


def norm_name(s):
    return re.sub(r"[\s\u3000]+", "", s or "")


def parse_entries(text):
    """按【来源】切段，往前找品名行（品名 / 拼音 / 拉丁名 三行）"""
    out = []
    for m in re.finditer(r"【来源】", text):
        head = text[max(0, m.start() - 220):m.start()]
        lines = [l.strip() for l in head.split("\n") if l.strip()]
        name = None
        # 从后往前找：遇到「拼音行 + 拉丁名行」前面那行就是品名
        for i in range(len(lines) - 1, 0, -1):
            a, b = lines[i - 1], lines[i]
            if re.match(r"^[A-Z][A-Za-z\-\s]{3,}$", b.replace(" ", "")) and \
               re.match(r"^[\u4e00-\u9fff\s\u3000]{2,12}$", a) and \
               not re.search(r"[【】]", a):
                name = norm_name(a)
                break
        if not name or name in ("【来源】",):
            continue
        seg = text[m.start():m.start() + 900]
        body = seg.split("【炮制】")[0]
        pm = PART_RE.search(body)
        am = AREA_RE.search(body)
        out.append({
            "name": name,
            "part": clean(pm.group(1)) if pm else "",
            "area": clean(am.group(1)) if am else "",
            "raw": clean(body)[:150],
        })
    return out


def parse_alias(text):
    """附表Ⅲ 天津市中药饮片常用别名：表格是「序号 品名 别名」三列。

    注意：附表Ⅳ 是「调剂处方应付」（写麻黄付麻黄、写炙麻黄付蜜麻黄…），
    那不是别名，必须在下表开始处截断，否则会把调剂术语当成别名。
    """
    i = text.rfind("常用别名")
    if i < 0:
        return {}
    seg = text[i:i + 90000]
    cut = seg.find("调剂处方应付")
    if cut > 0:
        seg = seg[:cut]
    out = {}
    for line in seg.split("\n"):
        line = line.strip()
        if not line or "【" in line:
            continue
        m = re.match(r"^(\d{1,3})[\s\u3000]+([\u4e00-\u9fff]{2,10})[\s\u3000]+(.{2,60})$", line)
        if not m:
            continue
        name, alias = m.group(2), m.group(3).strip()
        if re.search(r"[\u4e00-\u9fff]", alias):
            out.setdefault(name, alias)
    return out


def main():
    text = io.open(SRC, encoding="utf-8").read()
    entries = parse_entries(text)
    alias = parse_alias(text)
    herbs = [h["name"] for h in
             json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]]
    hset = set(herbs)

    data = {}
    for e in entries:
        n = e["name"]
        if n not in hset:
            continue
        if n in data:
            continue
        data[n] = {"part": e["part"], "area": e["area"], "alias": alias.get(n, ""),
                   "src": "天津市中药饮片炮制规范2022"}

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with io.open(DUMP, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write("%s\t%s\t%s\t%s\n" % (k, v["part"], v["area"], v["alias"]))

    have_part = sum(1 for v in data.values() if v["part"])
    have_area = sum(1 for v in data.values() if v["area"])
    have_alias = sum(1 for v in data.values() if v["alias"])
    print("正文条目 %d 条，别名表 %d 条" % (len(entries), len(alias)))
    print("命中题库 %d 味 / %d：药用部位 %d，产地 %d，别名 %d"
          % (len(data), len(herbs), have_part, have_area, have_alias))
    for k in list(data)[:8]:
        v = data[k]
        print("  %-6s 部位=%-8s 产地=%-22s 别名=%s" % (k, v["part"], v["area"][:22], v["alias"][:30]))
    print("-> %s" % DUMP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
