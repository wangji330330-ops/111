# -*- coding: utf-8 -*-
"""生成根目录下的 pinyin_table.py（审定后的药名→拼音表）。

pinyin_table.py 是**冻结产物**：构建题库时只读它，不再依赖 pypinyin，
这样换台机器、没装 pypinyin 也能正确重建 herbs.json。

用法：
  python tools/pinyin/py_base.py      # 1. pypinyin 生成
  node tools/pinyin/node_gen.mjs ...  # 2. pinyin-pro 生成（交叉校验）
  python tools/pinyin/review.py       # 3. 差异清单（人工裁定）
  python tools/pinyin/gen_table.py    # 4. 冻结成表
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from py_base import gen, load_names  # noqa: E402

DST = os.path.join(ROOT, "pinyin_table.py")

HEADER = '''# -*- coding: utf-8 -*-
"""药名 → 拼音（已审定，自动生成，请勿手工修改）。

生成链路：tools/pinyin/generate.py
审定依据：
  1. pypinyin 与 pinyin-pro 双引擎交叉比对，逐条人工裁定；
  2. 《中国药典》汉语拼音核对音节（tools/pinyin/verify_chp.py）；
  3. 中医专用读音表（tools/pinyin/overrides.py），如
     白术 bái zhú、大黄 dài huáng、阿胶 ē jiāo、厚朴 hòu pò、
     没药 mò yào、桔梗 jié gěng、黄柏 huáng bò、射干 yè gān、
     重楼 chóng lóu、槟榔 bīng láng、莪术 é zhú、石韦 shí wéi、
     川芎 chuān xiōng、玄参 xuán shēn、菟丝子 tù sī zǐ、
     桑螵蛸 sāng piāo xiāo、海蛤壳 hǎi gé ké、萹蓄 biān xù、狗脊 gǒu jǐ。

体例：逐字本调（每个音节都标声调，“子”读 zǐ 不读轻声），首音节首字母大写。
"""

PY = {
'''


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def titlecase(py):
    """'má huáng' -> 'Má Huáng'（逐音节首字母大写）"""
    return " ".join(w[:1].upper() + w[1:] for w in py.split())


def main():
    names = load_names()
    py = gen(names)
    missing = [n for n in names if not py.get(n)]
    if missing:
        raise SystemExit("缺少拼音: %s" % missing)
    lines = [HEADER]
    for n in names:
        lines.append('    "%s": "%s",\n' % (esc(n), esc(titlecase(py[n]))))
    lines.append("}\n")
    with io.open(DST, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print("pinyin_table.py written: %d 条" % len(py))


if __name__ == "__main__":
    main()
