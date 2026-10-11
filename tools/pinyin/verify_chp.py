# -*- coding: utf-8 -*-
"""用《中国药典》(drugfuture 镜像) 的官方汉语拼音核对本地拼音。

药典的汉语拼音是**不带声调**的（Bichengqie / Baizhu / Chuanxiong），
因此它能校验“音节/声母韵母”层面的多音字误读（白术 bái zhú vs bái shù、
川芎 chuān xiōng vs chuān qiōng、玄参 xuán shēn vs xuán cān……），
这正是通用拼音词典最容易出错的地方。声调仍由人工审定。

用法：
  python tools/pinyin/verify_chp.py            # 抓取并缓存药典拼音
  python tools/pinyin/verify_chp.py --report   # 只做比对
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from py_base import gen, load_names  # noqa: E402
from review import strip_tone  # noqa: E402

CACHE = os.path.join(HERE, "chp_pinyin.json")
URL = "https://www.drugfuture.com/chp2005/show_content.asp?title=%s"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def chp_url(name):
    return URL % urllib.parse.quote(name.encode("gb2312"), safe="")


def fetch(name, timeout=25):
    req = urllib.request.Request(chp_url(name), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    txt = raw.decode("utf-8", "replace")
    # 页面是 HTML，先剥标签再取“汉语拼音:”后面的内容（否则会抓到 span 等标签名）
    txt = re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = txt.replace("&nbsp;", " ")
    m = re.search(r"汉语拼音\s*[:：]?\s*([A-Za-z\u00b7][A-Za-z\u00b7\s]{2,60})", txt)
    if not m:
        return None
    py = re.sub(r"\s+", " ", m.group(1)).strip()
    return py or None


def crawl(names, force=False):
    cache = {}
    if os.path.exists(CACHE) and not force:
        with io.open(CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    todo = [n for n in names if n not in cache]
    print("待抓取 %d 味（已缓存 %d）" % (len(todo), len(cache)))
    for i, n in enumerate(todo):
        try:
            cache[n] = fetch(n)
        except Exception as e:
            cache[n] = {"error": str(e)[:80]}
        if (i + 1) % 25 == 0 or i + 1 == len(todo):
            print("  %d/%d %s -> %s" % (i + 1, len(todo), n, cache[n]))
            with io.open(CACHE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=0)
        time.sleep(0.35)
    with io.open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0)
    return cache


def report():
    names = load_names()
    mine = gen(names)
    with io.open(CACHE, "r", encoding="utf-8") as f:
        ref = json.load(f)
    hit, miss, err, bad = 0, 0, 0, []
    for n in names:
        v = ref.get(n)
        if isinstance(v, dict):
            err += 1
            continue
        if not v:
            miss += 1
            continue
        hit += 1
        a = strip_tone(mine[n]).replace(" ", "").lower()
        b = re.sub(r"[^a-z]", "", v.lower())
        if a != b:
            bad.append((n, mine[n], v, a, b))
    out = os.path.join(HERE, "review_chp.txt")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("药典命中 %d 味，未收录 %d 味，抓取失败 %d 味；音节层面不一致 %d 条\n\n"
                % (hit, miss, err, len(bad)))
        for n, my, v, a, b in bad:
            f.write("%s\t本地=%s(%s)\t药典=%s(%s)\n" % (n, my, a, v, b))
    print("药典命中 %d，未收录 %d，失败 %d，不一致 %d -> %s" % (hit, miss, err, len(bad), out))
    for row in bad:
        print("  ", row[0], row[3], "vs", row[4])


if __name__ == "__main__":
    names = load_names()
    if "--report" in sys.argv:
        report()
    else:
        crawl(names, force="--force" in sys.argv)
        report()
