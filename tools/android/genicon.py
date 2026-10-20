# -*- coding: utf-8 -*-
"""生成安卓启动图标（圆角深绿底 + 白色「药」字）。"""
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "app", "res", "mipmap-xxhdpi", "ic_launcher.png")
S = 432

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

c1, c2 = (126, 190, 150), (38, 104, 74)
for y in range(S):
    t = y / float(S - 1)
    d.line([(0, y), (S, y)],
           fill=(int(c1[0] + (c2[0] - c1[0]) * t),
                 int(c1[1] + (c2[1] - c1[1]) * t),
                 int(c1[2] + (c2[2] - c1[2]) * t), 255))

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
img.putalpha(mask)

font = None
for fp in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
           r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, int(S * 0.62))
            break
        except Exception:
            pass

d = ImageDraw.Draw(img)
if font:
    bb = d.textbbox((0, 0), "药", font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((S - w) / 2 - bb[0], (S - h) / 2 - bb[1] - S * 0.02), "药",
           font=font, fill=(255, 255, 255, 255))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG")
print("OK %s %dx%d font=%s" % (OUT, S, S, bool(font)))