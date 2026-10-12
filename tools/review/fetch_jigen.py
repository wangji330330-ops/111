# -*- coding: utf-8 -*-
"""抓《中国药典》各药材的「基原」原文（只为了取药用部位），带缓存。

来源: drugfuture 的中国药典 2005 版镜像（与 2020 版基原表述基本一致）。
缓存: review/_src/chp_jigen.json，断了重跑不会白干。

用法: python tools/review/fetch_jigen.py
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "_src", "chp_jigen.json")
URL = "https://www.drugfuture.com/chp2005/show_content.asp?title=%s"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(name, timeout=25):
    u = URL % urllib.parse.quote(name.encode("gb2312", "ignore"), safe="")
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode("utf-8", "replace")
    txt = re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "\n", txt).replace("&nbsp;", " ")
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    for i, l in enumerate(lines):
        if l.startswith("基原"):
            return " ".join(lines[i + 1:i + 4])[:400]
    return ""


def main():
    herbs = [h["name"] for h in
             json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]]
    cache = {}
    if os.path.exists(OUT):
        cache = json.load(io.open(OUT, encoding="utf-8"))
    todo = [h for h in herbs if h not in cache]
    print("待抓 %d 味（已缓存 %d）" % (len(todo), len(cache)), flush=True)

    def work(n):
        try:
            return n, fetch(n)
        except Exception:
            return n, ""

    with ThreadPoolExecutor(max_workers=10) as ex:
        for i, (n, j) in enumerate(ex.map(work, todo), 1):
            cache[n] = j
            if i % 40 == 0:
                json.dump(cache, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("  %d/%d" % (i, len(todo)), flush=True)
            time.sleep(0.05)
    json.dump(cache, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for v in cache.values() if v)
    print("抓完：%d 味有基原 / %d" % (ok, len(cache)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
