# -*- coding: utf-8 -*-
"""pypinyin 生成拼音（带声调符号），使用 overrides.py 中的中医专用读音表。

用法：
  python tools/pinyin/py_base.py            # 生成 py_pypinyin.json
"""
import io
import json
import os
import sys

from pypinyin import Style, lazy_pinyin, load_phrases_dict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from overrides import CHAR_OVERRIDE, OVERRIDES  # noqa: E402


def build_phrases(overrides):
    """{词: 'pīn yīn'} -> pypinyin 的 phrases_dict 格式"""
    d = {}
    for word, py in overrides.items():
        parts = py.split()
        if len(parts) != len(word):
            raise ValueError("词组 %s 与拼音 %s 音节数不一致" % (word, py))
        d[word] = [[p] for p in parts]
    return d


def gen(names, overrides=None, char_override=None):
    """返回 {药名: 'Pīn Yīn'}（音节空格分隔，保留声调）

    词组覆盖交给 pypinyin 的词组表处理；单字覆盖走“按位置替换”的后处理，
    保证人工审定结果一定生效（pypinyin 自带的轻声后缀规则优先级更高，
    例如“苍耳子”会被读成轻声 zi，必须在后处理里改回 zǐ）。
    """
    overrides = OVERRIDES if overrides is None else overrides
    char_override = CHAR_OVERRIDE if char_override is None else char_override
    if overrides:
        load_phrases_dict(build_phrases(overrides))

    out = {}
    for n in names:
        syl = lazy_pinyin(n, style=Style.TONE)
        if len(syl) != len(n):
            raise ValueError("%s 音节数 %d != 字数 %d" % (n, len(syl), len(n)))
        if char_override:
            syl = [char_override.get(ch, s) for ch, s in zip(n, syl)]
        out[n] = " ".join(syl)
    return out


def load_names(root=None):
    root = root or os.path.dirname(os.path.dirname(HERE))
    with io.open(os.path.join(root, "herbs.json"), "r", encoding="utf-8") as f:
        return [h["name"] for h in json.load(f)["herbs"]]


if __name__ == "__main__":
    names = load_names()
    res = gen(names)
    with io.open(os.path.join(HERE, "py_pypinyin.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=0)
    print("pypinyin wrote %d entries (overrides=%d, chars=%d)"
          % (len(res), len(OVERRIDES), len(CHAR_OVERRIDE)))
