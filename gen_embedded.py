# -*- coding: utf-8 -*-
"""把 herbs.json 转成 C# 源码 EmbeddedData.cs（编译进 exe，无需外部文件）。

注意：早期实现把整个 JSON 用 "+" 连成一个超长字符串表达式，
题库扩充到 400+ 味后触发 csc 的 CS1647（表达式太长或太复杂）。
现改为字符串数组 + string.Concat，表达式长度可控。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "herbs.json")
DST = os.path.join(HERE, "src", "EmbeddedData.cs")


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        js = f.read()
    if "\u2028" in js or "\u2029" in js:
        js = js.replace("\u2028", " ").replace("\u2029", " ")
    lines = js.split("\n")

    parts = []
    parts.append("// 自动生成，请勿手工修改。源文件: herbs.json")
    parts.append("namespace TcmReview")
    parts.append("{")
    parts.append("    public static class EmbeddedData")
    parts.append("    {")
    parts.append("        // 每行一个字符串，运行时用 string.Concat 拼接")
    parts.append("        public static readonly string[] HerbsJsonLines = new string[]")
    parts.append("        {")
    for line in lines:
        esc = line.replace("\\", "\\\\").replace('"', '\\"')
        parts.append('            "' + esc + '",')
    parts.append("        };")
    parts.append("")
    parts.append("        public static string HerbsJson()")
    parts.append("        {")
    parts.append("            return string.Concat(HerbsJsonLines);")
    parts.append("        }")
    parts.append("    }")
    parts.append("}")
    parts.append("")
    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("EmbeddedData.cs written:", os.path.getsize(DST), "bytes,", len(lines), "lines")


if __name__ == "__main__":
    main()
