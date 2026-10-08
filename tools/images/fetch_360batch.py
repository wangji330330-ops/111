# -*- coding: utf-8 -*-
"""用 360 图片接口抓指定药味的候选图（可批量），输出到 review/c360/。
用法: python fetch_360batch.py 五灵脂 蒲黄 ...
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "c360")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# 每个药味用多组更精确的关键词
TERM_SUFFIX = ["中药饮片", "中药材 实物", "饮片 特写", "药材"]


def api(q, pn=0, rn=30):
    url = ("https://image.so.com/j?q=" + urllib.parse.quote(q) +
           "&src=srp&sn=%d&pn=%d" % (pn, rn))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://image.so.com/",
        "Accept": "application/json, text/plain, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def download(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA,
                                             "Referer": "https://image.so.com/"})
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


DROP_HOST = ("redocn", "699pic", "zcool", "58pic", "ooopic", "tukuppt", "51yuansu")


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not names:
        print("usage: fetch_360batch.py 药名 [药名...]")
        return 2
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    else:
        for f in os.listdir(OUT):
            os.remove(os.path.join(OUT, f))

    for name in names:
        n = 0
        for suf in TERM_SUFFIX:
            term = "%s %s" % (name, suf)
            try:
                j = api(term, 0, 30)
            except Exception as e:
                print("api fail %s: %s" % (term.encode("unicode_escape").decode("ascii"), e))
                continue
            lst = j.get("list") or []
            print("term=%s items=%d" % (term.encode("unicode_escape").decode("ascii"), len(lst)))
            for it in lst:
                u = it.get("img") or it.get("thumb") or ""
                title = (it.get("title") or "")
                host = ""
                try:
                    host = urllib.parse.urlparse(u).netloc.lower()
                except Exception:
                    pass
                if not u.startswith("http"):
                    continue
                if any(b in host for b in DROP_HOST):
                    continue
                # 标题里必须出现药名（避免“5”这类歧义）
                if name not in title:
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
                                        title[:32].encode("unicode_escape").decode("ascii")))
                if n >= 8:
                    break
            if n >= 8:
                break
            time.sleep(0.3)
        print("--- %s: %d" % (name.encode("unicode_escape").decode("ascii"), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
