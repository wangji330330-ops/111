# -*- coding: utf-8 -*-
"""为扩充药味批量抓取候选图（360 图片接口）。

用法: python tools/images/fetch_new_batch.py          # 抓 ENABLED_BATCHES 里所有新药
输出: review/c360new/<药名>_cNN.jpg （每味最多 8 张候选）
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
OUT = os.path.join(ROOT, "review", "c360new")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

TERM_SUFFIX = ["中药饮片 实物", "中药材 干品", "饮片 特写"]
DROP_HOST = ("redocn", "699pic", "zcool", "58pic", "ooopic", "tukuppt", "51yuansu",
             "pngtree", "zhimg.com/v2-")
BAD_TITLE = ("胶囊", "颗粒", "口服液", "注射液", "说明书", "批准文号", "价格", "包邮",
             "多少钱", "功效与作用", "禁忌", "配方", "图片大全")


def load_new_names():
    """读取要抓图的新药名（已启用批次的条目中、当前 images_manifest 里没有图的）"""
    sys.path.insert(0, ROOT)
    import herbs_additions as A
    enabled = getattr(A, "ENABLED_BATCHES", [1])
    names = []
    for n in enabled:
        for rec in getattr(A, "ADDITIONS_%d" % n, []):
            names.append(rec[0])
    with io.open(os.path.join(ROOT, "images_manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    todo = [n for n in names if not man.get(n, {}).get("files")]
    return names, todo


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


def main():
    allnames, todo = load_new_names()
    print("启用批次药味: %d 味，其中待抓图: %d 味" % (len(allnames), len(todo)))
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if only:
        todo = [n for n in todo if n in only]
        print("限定抓取: %d 味" % len(todo))

    for idx, name in enumerate(todo, 1):
        got = 0
        for suf in TERM_SUFFIX:
            term = "%s %s" % (name, suf)
            try:
                j = api(term, 0, 30)
            except Exception as e:
                print("  [%d/%d] %s api fail: %s" % (idx, len(todo), name, e))
                continue
            lst = j.get("list") or []
            for it in lst:
                u = it.get("img") or ""
                title = it.get("title") or ""
                host = ""
                try:
                    host = urllib.parse.urlparse(u).netloc.lower()
                except Exception:
                    pass
                if not u.startswith("http"):
                    continue
                if any(b in host for b in DROP_HOST):
                    continue
                if name not in title:
                    continue
                if any(b in title for b in BAD_TITLE):
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
                got += 1
                fn = "%s_c%02d.jpg" % (name, got)
                with open(os.path.join(OUT, fn), "wb") as f:
                    f.write(jpg)
                print("  [%d/%d] OK %s | %s" % (idx, len(todo), fn,
                                                title[:26].encode("unicode_escape").decode("ascii")))
                if got >= 8:
                    break
            if got >= 8:
                break
            time.sleep(0.25)
        print("[%d/%d] --- %s: %d" % (idx, len(todo),
                                      name.encode("unicode_escape").decode("ascii"), got))
    print("DONE")


if __name__ == "__main__":
    main()
