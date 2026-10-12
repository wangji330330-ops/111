# -*- coding: utf-8 -*-
"""同 sheet_rows.py，但读第二轮候选目录 review/hd2。

用法: python tools/images/sheet_rows2.py out.png 樟脑 穿山甲
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheet_rows  # noqa: E402

ROOT = sheet_rows.ROOT
sheet_rows.HD = os.path.join(ROOT, "review", "hd2")
sheet_rows.INDEX = os.path.join(sheet_rows.HD, "index.json")

if __name__ == "__main__":
    sheet_rows.main()
