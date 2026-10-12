# -*- coding: utf-8 -*-
"""从《道地药材产品认证目录》（CQC 道地药材产品认证实施规则 附件2）里抽表格。

为什么要专门抽表：这份 PDF 的单元格是「一格多行」，纯文本流里
道地产区 / 别名 / 药用部位 三列会连成一片，靠正则切不干净。
表格没有框线，pypdf 的 extract_tables() 抽不出来（实测 0 页），
所以改用 pdfplumber —— 它按文字坐标分列，对这种无框线表格有效。

输出: review/_src/daodi.json  {产品名: {origin, area, alias, part}}
用法: python tools/review/parse_daodi.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = os.path.join(ROOT, "review", "_src", "cqc.pdf")
OUT = os.path.join(ROOT, "review", "_src", "daodi.json")
DUMP = os.path.join(ROOT, "review", "_src", "daodi_rows.txt")


def cell(v):
    if v is None:
        return ""
    return re.sub(r"\s+", "", str(v)).strip()


def main():
    import pdfplumber

    rows = []
    with pdfplumber.open(PDF) as pdf:
        for page in pdf.pages:
            for tb in (page.extract_tables() or []):
                for row in tb:
                    cells = [cell(c) for c in row]
                    joined = "".join(cells)
                    if "产品名称" in joined or "药用部位" in joined:
                        continue
                    while cells and cells[0] == "":
                        cells.pop(0)
                    if len(cells) >= 6 and re.match(r"^\d+$", cells[0]):
                        rows.append(cells)
                    elif len(cells) >= 5 and cells[0] and cells[0] != "":
                        # 跨页续行：没有序号，把内容并到上一行
                        if rows:
                            rows[-1] = [rows[-1][i] + (cells[i] if i < len(cells) else "")
                                        for i in range(len(rows[-1]))]

    data = {}
    for c in rows:
        origin, name, area, alias, part = c[1], c[2], c[3], c[4], c[5]
        if not name:
            continue
        data[name] = {"origin": origin, "area": area, "alias": alias, "part": part}

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with io.open(DUMP, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write("%s\t%s\t%s\t%s\t%s\n" % (k, v["origin"], v["area"], v["alias"], v["part"]))

    print("抽到 %d 条" % len(data))
    print("-> %s" % DUMP)
    return 0


if __name__ == "__main__":
    sys.exit(main())

