# -*- coding: utf-8 -*-
"""生成程序图标 app.ico（当归/药叶意象的简化图标）。"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "res", "app.ico")


def make(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0

    def r(x):
        return int(round(x * s))

    # 圆角底板
    d.rounded_rectangle([r(8), r(8), r(248), r(248)], radius=r(52),
                        fill=(31, 111, 84, 255))
    # 药叶（两片）
    d.ellipse([r(52), r(52), r(150), r(150)], fill=(232, 244, 238, 255))
    d.ellipse([r(104), r(88), r(206), r(190)], fill=(193, 105, 62, 255))
    # 叶脉
    d.line([r(60), r(148), r(140), r(64)], fill=(31, 111, 84, 255), width=max(1, r(9)))
    d.line([r(112), r(184), r(198), r(98)], fill=(150, 76, 40, 255), width=max(1, r(8)))
    return img


def main():
    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [make(x) for x in sizes]
    imgs[0].save(OUT, format="ICO", sizes=[(x, x) for x in sizes])
    print("icon written:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
