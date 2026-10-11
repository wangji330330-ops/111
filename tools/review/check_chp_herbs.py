# -*- coding: utf-8 -*-
"""用《中国药典》核对新增药材的「性味/归经/功效/用法」（drugfuture 2005 镜像）。

用法:
  python tools/review/check_chp_herbs.py 香薷 穿心莲 ...
  python tools/review/check_chp_herbs.py --new     # 核对 ADDITIONS_5 全部
输出: review/_book/chp_new.txt（药典原文 vs 本地记录，逐条对照）
"""
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
URL = "https://www.drugfuture.com/chp2005/show_content.asp?title=%s"


def fetch(name):
    u = URL % urllib.parse.quote(name.encode("gb2312", "ignore"), safe="")
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        txt = r.read().decode("utf-8", "replace")
    txt = re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [l.strip() for l in txt.split("\n")]
    lines = [l for l in lines if l]
    return lines


def section(lines, key, nxt=("性味", "归经", "功效", "主治", "用法用量", "贮藏", "检查", "鉴别")):
    for i, l in enumerate(lines):
        if l.startswith(key):
            out = []
            for l in lines[i + 1: i + 6]:
                if any(l.startswith(k) for k in nxt):
                    break
                out.append(l)
            return " ".join(out)[:200]
    return ""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--new" in sys.argv:
        import herbs_additions as add
        args = [r[0] for r in add.ADDITIONS_5]
    import json
    local = {h["name"]: h for h in
             json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]}

    out = []
    for name in args:
        try:
            lines = fetch(name)
        except Exception as e:
            out.append("### %s  抓取失败: %s\n" % (name, e))
            continue
        chp = {k: section(lines, k) for k in ("性味", "归经", "功效", "用法用量")}
        h = local.get(name, {})
        out.append("### %s\n" % name)
        out.append("  药典 性味: %s\n  本地 性味: %s\n" % (chp["性味"] or "（未收录）", h.get("nature", "")))
        out.append("  药典 归经: %s\n  本地 归经: %s\n" % (chp["归经"] or "（未收录）", h.get("meridian", "")))
        out.append("  药典 功效: %s\n  本地 功效: %s\n" % (chp["功效"] or "（未收录）", "；".join(h.get("fx", []))))
        out.append("  药典 用法: %s\n  本地 用法: %s\n\n" % (chp["用法用量"] or "（未收录）", h.get("usage", "")))
        print("%-8s 药典性味=%s | 功效=%s" % (name, chp["性味"][:30], chp["功效"][:40]), flush=True)
        time.sleep(0.4)

    p = os.path.join(ROOT, "review", "_book", "chp_new.txt")
    io.open(p, "w", encoding="utf-8").write("".join(out))
    print("\n-> %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
