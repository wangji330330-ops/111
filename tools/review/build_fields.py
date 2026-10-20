# -*- coding: utf-8 -*-
"""合并三个权威来源，生成题库的【别名】【产地分布】【药用部位】。

来源与优先级（高 → 低）：
  1. 《天津市中药饮片炮制规范》2022 年版
     —— 天津市药监局批准颁布的**省级中药饮片炮制规范**（法定技术标准）
     【来源】给出「…的干燥块根。主产于福建、广西、广东、云南等地。」
     附表Ⅲ 给出饮片常用别名
  2. 《道地药材产品认证目录》（中国质量认证中心 CQC/SSGZ YC2001-2023 附件2）
     —— 道地药材产品认证目录，含 产地 / 道地产区 / 别名 / 药用部位
  3. 《中华人民共和国药典》2020 年版一部 基原
     —— 只用来补「药用部位」（从「本品为…的干燥XX」里取）

每味药记录三个字段各自的来源，界面上可以看到依据，绝不含糊。

用法: python tools/review/build_fields.py
输出: review/_src/fields.json   {药名: {alias, area, part, srcAlias, srcArea, srcPart}}
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "review", "_src")
OUT = os.path.join(SRC, "fields.json")
REPORT = os.path.join(SRC, "fields_report.txt")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_tj as TJ  # noqa: E402

SRC_TJ = "天津市中药饮片炮制规范（2022年版）"
SRC_CQC = "道地药材产品认证目录（中国质量认证中心 CQC/SSGZ YC2001-2023）"
SRC_CHP = "《中华人民共和国药典》2020年版一部"


def split_alias(s):
    return [x.strip() for x in re.split(r"[、,，;；\s]+", s or "") if 1 < len(x.strip()) <= 10]


# 人工核对过的「题库药名 → 标准里的品名」映射。
# 只用同物异名（产地前缀、饮片习称），绝不做盲目子串匹配 ——
# 子串规则会把「土茯苓←茯苓」「胡黄连←黄连」「莲子←苦石莲子」这类全配错。
MANUAL_PAIRS = {
    # 道地药材产品的产地前缀 / 习称
    "菊花": ["杭白菊", "亳菊", "滁菊", "贡菊", "怀菊"],
    "黄芪": ["北芪"],
    "沙苑子": ["潼沙苑"],
    "茯苓": ["云苓", "茯苓（安苓）"],
    "何首乌": ["广首乌"],
    "天花粉": ["安阳花粉"],
    "白附子": ["禹白附"],
    "密蒙花": ["密印花"],
    "薏苡仁": ["祁薏米"],
    "金银花": ["东银花"],
    "枸杞子": ["宁夏枸杞"],
    "全蝎": ["青州蝎"],
    "艾叶": ["蕲艾"],
    "牡丹皮": ["川丹皮"],
    "吴茱萸": ["江吴萸", "常吴萸"],
    "刺蒺藜": ["蒺藜"],
    # 天津规范里的品名
    "生地黄": ["地黄"],
    "熟地黄": ["地黄"],
    "益智仁": ["益智"],
    "海浮石": ["浮石"],
    "厚朴花": ["厚朴"],
    "茯苓皮": ["茯苓"],
}


def manual_lookup(name):
    """题库药名 → 标准里的候选品名列表"""
    return MANUAL_PAIRS.get(name, [])


def clean_alias(s, self_name):
    """别名只留真正好用的那些（精简规则，宁可少而准）：

    1. 去掉药名本身；
    2. 去掉**包含药名**的（「草麻黄」「川升麻」这类是原植物／产地变体名，
       不是别名，也是最容易让人看懵的一类）；
    3. 去掉调剂应付术语（「写麻黄付麻黄」「蜜麻黄均付蜜麻黄」）；
    4. 长度限 2~6 字；最后最多保留 4 条。
    """
    out = []
    for a in split_alias(s):
        a = a.strip("。；，、")
        if a == self_name:
            continue
        if self_name and self_name in a:
            continue
        if "付" in a or "写" in a or "均" in a:
            continue
        if not (2 <= len(a) <= 6):
            continue
        out.append(a)
    seen, res = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            res.append(a)
    return "、".join(res[:4])


def pick_part(text):
    """从「…植物草麻黄 Ephedra … 的干燥草质茎。」里只取「草质茎」

    坑一：直接截「的(干燥)」后面会把拉丁学名一起带进来 —— 取**最后**一个匹配
          （「科植物X …的干燥Y」里的「的」总是在最后）。
    坑二：有些句子有多个「的」，所以宁可取最后一个也不要取第一个。
    """
    ms = list(re.finditer(r"的(?:干燥|新鲜|鲜)([^。，、；（）()]{1,10})", text or ""))
    if not ms:
        return ""
    s = ms[-1].group(1)
    s = re.sub(r"^[或及和、]+", "", s).strip()
    if "植物" in s or "科" in s or "的" in s:
        return ""
    return s if 2 <= len(s) <= 10 else ""


def trim_area(s, limit=60):
    """产区描述太长就按标点收尾，别截到半个词"""
    s = re.sub(r"\s+", "", s or "")
    if len(s) <= limit:
        return s
    cut = s[:limit]
    for ch in ("，", "、", "。", "；", "及", "等"):
        i = cut.rfind(ch)
        if i >= limit // 2:
            return cut[:i]
    return cut


# 这些开头描述的是「生境/海拔」，不是产地，收进【产地分布】会误导
HABITAT_HEAD = ("海拔", "生", "长于", "喜", "分布于海拔", "生长于", "野生于")


def clean_area(s):
    """产地字段的最后一道过滤：去掉生境描述，只留地名"""
    s = re.sub(r"\s+", "", s or "").strip("。；，、")
    if not s:
        return ""
    if s.startswith(HABITAT_HEAD):
        # 「海拔2500m以下潮湿山坡…包括绵阳、达州」这种：把「包括/位于」后面的地名捞出来
        m = re.search(r"(?:包括|位于|产于)([^。]{2,40})", s)
        return trim_area(m.group(1)) if m else ""
    return trim_area(s)


def main():
    herbs = [h["name"] for h in
             json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]]
    hset = set(herbs)

    # ---- 1. 天津规范 ----
    text = io.open(os.path.join(SRC, "tj.txt"), encoding="utf-8").read()
    entries = TJ.parse_entries(text)
    by_name = {}
    for e in entries:
        by_name.setdefault(e["name"], e)
    alias_tbl = TJ.parse_alias(text)
    # 别名 → 品名 的反向表，用于「生地黄」这类题库名与规范品名不一致的情况
    alias2name = {}
    for pname, al in alias_tbl.items():
        for a in split_alias(al):
            alias2name.setdefault(a, pname)

    fields = {}
    for h in herbs:
        rec = {}
        e = by_name.get(h)
        if not e:
            # 反向映射：题库名是规范里某个品名的别名
            p = alias2name.get(h)
            if p:
                e = by_name.get(p)
        if not e:
            # 人工核对过的同物异名（地黄→生地黄、蒺藜→刺蒺藜…）
            for alt in manual_lookup(h):
                if alt in by_name:
                    e = by_name[alt]
                    break
        if e:
            if e["part"]:
                rec["part"], rec["srcPart"] = e["part"], SRC_TJ
            if e["area"]:
                ca = clean_area(e["area"])
                if ca:
                    rec["area"], rec["srcArea"] = ca, SRC_TJ
        al = alias_tbl.get(h)
        if not al:
            p = alias2name.get(h)
            if p and p != h:
                al = alias_tbl.get(p)
                # 反向映射时，规范里的品名本身也是本题库药的别名
                if p:
                    al = (al + "、" + p) if al else p
        if al:
            ca = clean_alias(al, h)
            if ca:
                rec["alias"], rec["srcAlias"] = ca, SRC_TJ
        if rec:
            fields[h] = rec

    # ---- 2. CQC 道地药材目录 ----
    cqc = json.load(io.open(os.path.join(SRC, "daodi_match.json"), encoding="utf-8"))
    # 人工映射：题库药名 ← 道地产品名（杭白菊→菊花、北芪→黄芪…）
    for h, alts in MANUAL_PAIRS.items():
        for alt in alts:
            if alt in cqc and h not in cqc:
                cqc[h] = cqc[alt]
                break
    for h, v in cqc.items():
        r = fields.setdefault(h, {})
        if not r.get("alias"):
            ca = clean_alias(v["alias"], h)
            if ca:
                r["alias"], r["srcAlias"] = ca, SRC_CQC
        if not r.get("area") and v["area"]:
            ca = clean_area(v["area"])
            if ca:
                r["area"], r["srcArea"] = ca, SRC_CQC
        if not r.get("part") and v["part"]:
            p = pick_part(v["part"])
            if p:
                r["part"], r["srcPart"] = p, SRC_CQC

    # ---- 3. 药典基原补药用部位 ----
    chp_path = os.path.join(SRC, "chp_jigen.json")
    if os.path.exists(chp_path):
        chp = json.load(io.open(chp_path, encoding="utf-8"))
        for h, jigen in chp.items():
            if not jigen:
                continue
            r = fields.setdefault(h, {})
            if not r.get("part"):
                p = pick_part(jigen)
                if p:
                    r["part"], r["srcPart"] = p, SRC_CHP

    # 药用部位里可能带「药材以…为佳」之类的尾巴，统一清一下；
    # 另外 PDF 抽取偶尔会带出 \x00 之类的控制字符，不清掉会让
    # 生成的 herb_fields.py 直接变成「含空字节、无法 import」的废文件。
    def sanitize(s):
        s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s or "")
        return re.sub(r"\s+", "", s).strip("。；，、")

    for r in fields.values():
        for k in ("alias", "area", "part"):
            if r.get(k):
                r[k] = sanitize(r[k])
        # 药用部位里别再带「干燥/新鲜」这类加工字眼，只留部位本身
        if r.get("part"):
            r["part"] = re.sub(r"^(?:干燥|新鲜|鲜)", "", r["part"]).strip()

    json.dump(fields, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 冻结成根目录的 herb_fields.py —— 构建题库时只读它，
    # 换台机器没装 pdfplumber / 没下过规范 PDF 也能正确重建 herbs.json
    SRC_CODE = {SRC_TJ: "T", SRC_CQC: "C", SRC_CHP: "P"}
    lines = ['# -*- coding: utf-8 -*-',
             '"""药名 → 别名 / 产地分布 / 药用部位（自动生成，请勿手工修改）。',
             '',
             '生成链路：tools/review/{parse_tj,match_daodi,build_fields}.py',
             '',
             '数据来源（都是法定标准或国家级目录，不用网络百科）：',
             '  T = 《天津市中药饮片炮制规范》2022 年版',
             '      （天津市药品监督管理局批准颁布的省级中药饮片炮制规范，',
             '        正文【来源】给出「…的干燥块根。主产于福建、广西…等地。」，',
             '        书末附表Ⅲ 给出饮片常用别名）',
             '  C = 《道地药材产品认证目录》',
             '      （中国质量认证中心 CQC/SSGZ YC2001-2023 附件2：',
             '        产地 / 道地产区 / 别名 / 药用部位 四列）',
             '  P = 《中华人民共和国药典》2020 年版一部【基原】',
             '      （只用来补「药用部位」）',
             '',
             '体例：FIELDS[药名] = (别名, 别名来源, 产地分布, 产地来源, 药用部位, 部位来源)',
             '      来源为 "" 表示该项缺（不做猜测，宁缺毋滥）',
             '"""',
             '',
             'FIELDS = {']
    for h in sorted(fields):
        r = fields[h]
        lines.append('    "%s": ("%s", "%s", "%s", "%s", "%s", "%s"),' % (
            h,
            (r.get("alias") or "").replace('"', '\\"'),
            SRC_CODE.get(r.get("srcAlias", ""), ""),
            (r.get("area") or "").replace('"', '\\"'),
            SRC_CODE.get(r.get("srcArea", ""), ""),
            (r.get("part") or "").replace('"', '\\"'),
            SRC_CODE.get(r.get("srcPart", ""), ""),
        ))
    lines.append("}")
    io.open(os.path.join(ROOT, "herb_fields.py"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    n = len(fields)
    ca = sum(1 for v in fields.values() if v.get("alias"))
    cr = sum(1 for v in fields.values() if v.get("area"))
    cp = sum(1 for v in fields.values() if v.get("part"))
    L = ["题库 %d 味，覆盖情况：" % len(herbs),
         "  别名     %3d 味（%.0f%%）" % (ca, 100.0 * ca / len(herbs)),
         "  产地分布 %3d 味（%.0f%%）" % (cr, 100.0 * cr / len(herbs)),
         "  药用部位 %3d 味（%.0f%%）" % (cp, 100.0 * cp / len(herbs)),
         "", "样例："]
    for h in list(fields)[:12]:
        v = fields[h]
        L.append("  %-6s 别名=%s | 产地=%s | 部位=%s"
                 % (h, v.get("alias", "-")[:30], v.get("area", "-")[:26], v.get("part", "-")))
    io.open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    print("-> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
