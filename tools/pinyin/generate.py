# -*- coding: utf-8 -*-
"""一键跑完拼音生成 + 双引擎比对 + 药典核对 + 冻结成表。

  python tools/pinyin/generate.py

前置：
  pip install pypinyin
  pnpm add pinyin-pro   （装到项目根的 _pytmp/ 下即可，仅开发期用）

产物：
  tools/pinyin/py_pypinyin.json     pypinyin 结果
  tools/pinyin/py_pinyinpro.json    pinyin-pro 结果
  tools/pinyin/review_all.txt       446 味全量对照表（人工看这张）
  tools/pinyin/review_diff.txt      两引擎不一致清单（重点裁定）
  tools/pinyin/review_chp.txt       与《中国药典》汉语拼音的差异
  pinyin_table.py                   冻结的审定表（题库构建读它）
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable
NODE = os.environ.get("DSH_NODE") or "node"
HERBS = os.path.join(ROOT, "herbs.json")


def run(cmd, desc):
    print("\n=== %s ===" % desc)
    r = subprocess.call(cmd)
    if r != 0:
        print("  ! 退出码 %d（%s）" % (r, desc))


def main():
    run([PY, os.path.join(HERE, "py_base.py")], "1/5 pypinyin 生成")
    node_gen = os.path.join(HERE, "node_gen.mjs")
    run([NODE, node_gen, HERBS, os.path.join(HERE, "py_pinyinpro.json")],
        "2/5 pinyin-pro 生成（交叉校验）")
    run([PY, os.path.join(HERE, "review.py")], "3/5 双引擎比对")
    run([PY, os.path.join(HERE, "verify_chp.py"), "--report"], "4/5 中国药典核对")
    run([PY, os.path.join(HERE, "gen_table.py")], "5/5 冻结 pinyin_table.py")
    print("\n完成。请人工过一遍 tools/pinyin/review_all.txt，"
          "有误读就写进 overrides.py 后重跑。")


if __name__ == "__main__":
    main()
