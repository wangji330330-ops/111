# -*- coding: utf-8 -*-
﻿# -*- coding: utf-8 -*-
"""把 images/ 打包成 C# 源码 src/EmbeddedImages.cs（编译进 exe）。

为控制 exe 体积，打包前统一再压缩：最长边 470px、质量 72。
结果缓存在 src/.packed/，避免重复压缩。

包格式：
    magic  "TCMIMGV1"       8 字节
    version int32           4 字节
    count   int32           4 字节
    count × [路径长 int32][路径 UTF-8][数据偏移 int32][数据长度 int32]
    数据区（各图片原始字节）
"""
import base64
import hashlib
import io
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG_DIR = os.path.join(HERE, "images")
CACHE = os.path.join(HERE, "src", ".packed")
OUT = os.path.join(HERE, "src", "EmbeddedImages.cs")
CHUNK = 12000

MAX_SIDE = 420
QUALITY = 70


def pack_one(src_path):
    """压缩单张图片，缓存到 src/.packed/<md5>.jpg"""
    from PIL import Image
    with open(src_path, "rb") as f:
        raw = f.read()
    key = hashlib.md5(raw + ("%d-%d" % (MAX_SIDE, QUALITY)).encode()).hexdigest()
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    dst = os.path.join(CACHE, key + ".jpg")
    if os.path.exists(dst):
        with open(dst, "rb") as f:
            return f.read()
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode in ("P", "LA", "RGBA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im2 = im.convert("RGBA")
        bg.paste(im2, mask=im2.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if max(w, h) > MAX_SIDE:
        k = float(MAX_SIDE) / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True)
    data = buf.getvalue()
    with open(dst, "wb") as f:
        f.write(data)
    return data


def build_bundle():
    entries = []
    if os.path.isdir(IMG_DIR):
        for fn in sorted(os.listdir(IMG_DIR)):
            if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            try:
                data = pack_one(os.path.join(IMG_DIR, fn))
            except Exception as e:
                print("skip %s: %s" % (fn.encode("unicode_escape").decode("ascii"), e))
                continue
            if len(data) < 500:
                continue
            entries.append((fn, data))

    header = bytearray()
    header += b"TCMIMGV1"
    header += struct.pack("<ii", 1, len(entries))
    body = bytearray()
    offset = 0
    for fn, data in entries:
        nb = fn.encode("utf-8")
        header += struct.pack("<i", len(nb))
        header += nb
        header += struct.pack("<ii", offset, len(data))
        body += data
        offset += len(data)
    return bytes(header + body), len(entries), offset


def main():
    bundle, count, total = build_bundle()
    b64 = base64.b64encode(bundle).decode("ascii")
    chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]

    lines = []
    lines.append("// 自动生成，请勿手工修改。源：images/ 目录（见 images_credits.txt）")
    lines.append("// 图片数量: %d，打包字节: %d (%.1f MB)，base64: %.1f MB" %
                 (count, total, total / 1048576.0, len(b64) / 1048576.0))
    lines.append("namespace TcmReview")
    lines.append("{")
    lines.append("    public static class EmbeddedImages")
    lines.append("    {")
    lines.append("        public static string Data()")
    lines.append("        {")
    lines.append("            return string.Concat(Parts);")
    lines.append("        }")
    lines.append("")
    lines.append("        private static readonly string[] Parts = new string[]")
    lines.append("        {")
    for c in chunks:
        lines.append('            "' + c + '",')
    lines.append("        };")
    lines.append("    }")
    lines.append("}")
    lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("EmbeddedImages.cs: images=%d packed=%.1fMB base64=%.1fMB chunks=%d" %
          (count, total / 1048576.0, len(b64) / 1048576.0, len(chunks)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
