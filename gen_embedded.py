# -*- coding: utf-8 -*-
"""把 herbs.json 转成 C# 源码 EmbeddedData.cs（编译进 exe，无需外部文件）。"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "herbs.json")
DST = os.path.join(HERE, "src", "EmbeddedData.cs")

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        js = f.read()
    if "\u2028" in js or "\u2029" in js:
        js = js.replace("\u2028", " ").replace("\u2029", " ")
    parts = []
    parts.append("// 自动生成，请勿手工修改。源文件: herbs.json")
    parts.append("namespace TcmReview")
    parts.append("{")
    parts.append("    public static class EmbeddedData")
    parts.append("    {")
    parts.append("        public const string HerbsJson =")
    # 按行拆分，每行一个字符串字面量，末尾用 + 连接
    lines = js.split("\n")
    for i, line in enumerate(lines):
        esc = line.replace("\\", "\\\\").replace('"', '\\"')
        suffix = " +" if i < len(lines) - 1 else ";"
        parts.append('            "' + esc + '\\n"' + suffix)
    parts.append("    }")
    parts.append("}")
    parts.append("")
    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("EmbeddedData.cs written:", os.path.getsize(DST), "bytes,", len(lines), "lines")

if __name__ == "__main__":
    main()
