# -*- coding: utf-8 -*-
"""交叉比对两份拼音，输出人工审定表。

产物（都在 tools/pinyin/ 下）：
  review_all.txt    446 味全量对照表（汉字 / pypinyin / pinyin-pro）
  review_diff.txt   两个引擎不一致的条目（重点裁定）
  review_poly.txt   含多音字的条目及其全部候选读音
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from py_base import gen, load_names  # noqa: E402

TONE_MAP = {
    "ā": "a", "á": "a", "ǎ": "a", "à": "a",
    "ē": "e", "é": "e", "ě": "e", "è": "e",
    "ī": "i", "í": "i", "ǐ": "i", "ì": "i",
    "ō": "o", "ó": "o", "ǒ": "o", "ò": "o",
    "ū": "u", "ú": "u", "ǔ": "u", "ù": "u",
    "ǖ": "v", "ǘ": "v", "ǚ": "v", "ǜ": "v", "ü": "v",
}


def load(fn):
    with io.open(os.path.join(HERE, fn), "r", encoding="utf-8") as f:
        return json.load(f)


def strip_tone(s):
    return "".join(TONE_MAP.get(c, c) for c in s)


def main():
    names = load_names()
    mine = gen(names)
    theirs = load("py_pinyinpro.json")
    alt = load("py_pinyinpro_alt.json")

    han = re.compile(r"[\u4e00-\u9fff]")

    diff, poly, problems = [], [], []
    lines = []
    for n in names:
        a, b = mine[n], theirs.get(n, "")
        cnt = len(han.findall(n))
        na, nb = len(a.split()), len(b.split())
        flag = ""
        if na != cnt:
            flag += " [!音节数]"
            problems.append((n, a, "音节 %d != 汉字 %d" % (na, cnt)))
        if nb != cnt:
            flag += " [pro音节数]"
        if strip_tone(a) != strip_tone(b):
            flag += " [读音差]"
            diff.append((n, a, b, "读音"))
        elif a != b:
            flag += " [声调差]"
            diff.append((n, a, b, "声调"))
        chars = [c for c in n if han.match(c)]
        ps = [c for c in chars if len(alt.get(c, [c])) > 1]
        if ps:
            poly.append((n, a, b, "".join("%s=%s " % (c, "/".join(alt[c])) for c in ps)))
        lines.append("%s\t%s\t%s%s" % (n, a, b, flag))

    with io.open(os.path.join(HERE, "review_all.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with io.open(os.path.join(HERE, "review_diff.txt"), "w", encoding="utf-8") as f:
        f.write("共 %d 条差异（读音差=声母韵母不同，声调差=仅声调不同）\n\n" % len(diff))
        for n, a, b, kind in diff:
            f.write("%s\t[%s]\tpypinyin=%s\tpinyin-pro=%s\n" % (n, kind, a, b))
    with io.open(os.path.join(HERE, "review_poly.txt"), "w", encoding="utf-8") as f:
        f.write("共 %d 条含多音字\n\n" % len(poly))
        for n, a, b, info in poly:
            f.write("%s\t%s\t%s\n\t%s\n" % (n, a, b, info))

    print("all=%d diff=%d poly=%d problems=%d" % (len(lines), len(diff), len(poly), len(problems)))
    for p in problems:
        print("  ", p)


if __name__ == "__main__":
    main()
