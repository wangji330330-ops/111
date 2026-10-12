# -*- coding: utf-8 -*-
"""把 PDF 转成文本，方便核对权威资料（香港中药材标准等）。

用法: python tools/review/pdftext.py input.pdf [out.txt] [起始页] [结束页]
"""
import io
import os
import sys

from pypdf import PdfReader


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".txt"
    a = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    b = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    r = PdfReader(src)
    n = len(r.pages)
    if b <= 0 or b > n:
        b = n
    buf = []
    for i in range(a, b):
        try:
            t = r.pages[i].extract_text() or ""
        except Exception as e:
            t = "(提取失败 %s)" % e
        # 有些 PDF 的字体映射会吐出孤立代理项，直接写盘会炸
        t = t.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
        buf.append("\n=== p%d ===\n" % (i + 1) + t)
    io.open(out, "w", encoding="utf-8").write("".join(buf))
    print("%s：%d 页 -> %s (%d 字节)" % (os.path.basename(src), n, os.path.basename(out),
                                        os.path.getsize(out)))


if __name__ == "__main__":
    main()
