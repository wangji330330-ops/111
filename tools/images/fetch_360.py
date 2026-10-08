# -*- coding: utf-8 -*-
"""用 360 图片接口为指定药味抓候选图（先核验，不直接入库）。"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

ROOT = r"E:\正常玩\中药复习程序"
OUT = os.path.join(ROOT, "review", "c360")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

TERMS = {
    "川乌": ["川乌 中药饮片", "制川乌 中药材", "川乌头 饮片", "川乌 附子 中药"],
    "附子": ["附子 中药饮片", "制附子 中药材", "附片 中药饮片", "黑顺片 附子"],
}


def api(q, pn=0, rn=30):
    url = ("https://image.so.com/j?q=" + urllib.parse.quote(q) +
           "&src=srp&correct=%s&sn=%d&pn=%d" % (urllib.parse.quote(q), pn, rn))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/",
        "Accept": "application/json, text/plain, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def download(u):
    req = urllib.request.Request(u, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def process(data, max_side=520):
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode in ("P", "LA", "RGBA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im2 = im.convert("RGBA")
        bg.paste(im2, mask=im2.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if max(w, h) > max_side:
        k = float(max_side) / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return buf.getvalue(), im.size


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    else:
        for f in os.listdir(OUT):
            os.remove(os.path.join(OUT, f))

    for name, terms in TERMS.items():
        n = 0
        for t in terms:
            try:
                j = api(t, 0, 30)
            except Exception as e:
                print("api fail %s: %s" % (t.encode("unicode_escape").decode("ascii"), e))
                continue
            lst = j.get("list") or []
            print("term=%s items=%d" % (t.encode("unicode_escape").decode("ascii"), len(lst)))
            for it in lst:
                u = it.get("img") or it.get("thumb") or ""
                title = (it.get("title") or "")
                if not u.startswith("http"):
                    continue
                try:
                    raw = download(u)
                except Exception:
                    continue
                if len(raw) < 5000:
                    continue
                try:
                    jpg, size = process(raw)
                except Exception:
                    continue
                if size[0] < 240 or size[1] < 180:
                    continue
                n += 1
                fn = "%s_c%02d.jpg" % (name, n)
                with open(os.path.join(OUT, fn), "wb") as f:
                    f.write(jpg)
                print("  OK %s | %s" % (fn.encode("unicode_escape").decode("ascii"),
                                        title[:34].encode("unicode_escape").decode("ascii")))
                if n >= 8:
                    break
            if n >= 8:
                break
            time.sleep(0.3)
        print("--- %s: %d\n" % (name.encode("unicode_escape").decode("ascii"), n))


if __name__ == "__main__":
    main()
