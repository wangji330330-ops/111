# -*- coding: utf-8 -*-
"""挑图页自检：确认页面上每个图片路径、每个「看大图」链接都能真正落到文件。

这个检查是补上之前那个坑：把 pick.html 复制到项目根目录时没改相对路径，
打开后满屏「未找到文件」。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 默认检查第一轮挑图页；第二轮加 --suffix=2
_SUF = ""
for _a in sys.argv[1:]:
    if _a.startswith("--suffix="):
        _SUF = _a.split("=", 1)[1]
PAGES = [os.path.join(ROOT, "挑图%s.html" % _SUF),
         os.path.join(ROOT, "review", "pick%s.html" % _SUF)]


def main():
    bad_total = 0
    for page in PAGES:
        if not os.path.exists(page):
            print("✗ 缺少 %s" % page)
            bad_total += 1
            continue
        h = io.open(page, encoding="utf-8").read()
        srcs = re.findall(r'src="([^"]+\.jpg)"', h)
        zooms = re.findall(r'href="([^"]+\.jpg)"', h)
        base = os.path.dirname(page)
        bad = [s for s in srcs if not os.path.exists(os.path.join(base, s.replace("/", os.sep)))]
        badz = [z for z in zooms if not os.path.exists(os.path.join(base, z.replace("/", os.sep)))]
        figs = h.count("<figure ")
        secs = h.count('<section class="row"')
        print("%-28s 药味 %d / 图 %d / 大图链接 %d  失效：图 %d，链接 %d"
              % (os.path.relpath(page, ROOT), secs, len(srcs), len(zooms), len(bad), len(badz)))
        if bad:
            print("   例：%s" % bad[:3])
        if badz:
            print("   例：%s" % badz[:3])
        if figs != len(srcs):
            print("   ! figure 数(%d) 与 img 数(%d) 不一致" % (figs, len(srcs)))
        bad_total += len(bad) + len(badz)
    print("")
    print("PICK PAGE CHECK %s" % ("PASS" if bad_total == 0 else "FAIL - %d 处失效" % bad_total))
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
