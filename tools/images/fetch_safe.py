# -*- coding: utf-8 -*-
"""带严格校验的图片抓取（修掉断网时抓到无关图片的问题）。

校验规则：
  1) JSON 必须含 murl 字段，且 URL 以图片扩展名结尾（或来自图片 CDN）
  2) 结果标题里必须出现药名，否则丢弃（防止无关内容）
  3) 拒绝素材/字体/软件/电商站
用法: python fetch_safe.py 青黛 雷公藤 ...   （或 --missing 抓所有缺图的）
"""
import json
import os
import re
import sys
import time

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fetch_images as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")

IMG_EXT = re.compile(r"\.(jpg|jpeg|png|webp|bmp)(\?|#|$)", re.I)
IMG_CDN = ("bcebos", "ayxbk", "cnkang", "39.net", "youlai", "360tres", "scimall",
           "zhongyoo", "yixue", "a-hospital", "img.", "pic.", "photo.", "file.",
           "static.", "cdn.", "images.")

REJECT_HOST = ("zcool", "58pic", "zsucai", "51yuansu", "ooopic", "tukuppt",
               "ziti", "font", "shufazidian", "zdic", "cidian", "pexels",
               "unsplash", "pixabay", "freepik", "dreamstime", "shutterstock",
               "wallpaper", "desktoppr", "tieba", "bilibili", "tmall", "taobao",
               "1688", "jd.com", "alibaba", "iloveimg", "convert", "jpg", "png")
REJECT_TITLE = ("logo", "图标", "字体", "书法", "字帖", "字典", "函数", "公式",
                "曲线", "流程图", "结构图", "图表", "ppt", "壁纸", "头像",
                "表情包", "动漫", "漫画", "游戏", "海报", "宣传", "广告",
                "教程", "视频", "转换", "在线", "编辑", "电脑", "手机", "汽车",
                "地图", "军事", "电影", "旅游", "风景", "美女", "软件")


def url_ok(u):
    if not u or not u.startswith("http"):
        return False
    h = F.host_of(u)
    if any(b in h for b in REJECT_HOST):
        return False
    if IMG_EXT.search(u):
        return True
    if any(c in h for c in IMG_CDN):
        return True
    return False


def bing_safe(name, extra, limit=20):
    """严格版 Bing 抓取：过滤无关结果"""
    out = []
    url = ("https://cn.bing.com/images/search?q=" +
           F.urllib.parse.quote(name + " " + extra) + "&form=HDRSC2&first=1")
    try:
        html = F.http_get(url, timeout=15)
    except Exception:
        return out
    if "murl" not in html:
        return out
    for m in re.finditer(r'm="(\{[^"]*?murl[^"]*?\})"', html):
        raw = m.group(1).replace("&quot;", '"').replace("&amp;", "&")
        try:
            j = json.loads(raw)
        except Exception:
            continue
        u = j.get("murl") or ""
        title = j.get("t") or ""
        if not url_ok(u):
            continue
        tl = title.lower()
        if any(b in tl for b in REJECT_TITLE):
            continue
        # 标题必须与药名相关
        if name not in title:
            continue
        out.append({"url": u, "title": title, "page": j.get("purl", ""),
                    "license": "网络图片（见来源页）", "src": "bing"})
        if len(out) >= limit:
            break
    return out


def text_heavy(path):
    im = Image.open(path).convert("L").resize((320, 240))
    px = list(im.getdata())
    white = sum(1 for p in px if p > 228) / float(len(px))
    dark = sum(1 for p in px if p < 110) / float(len(px))
    ep = list(im.filter(ImageFilter.FIND_EDGES).getdata())
    emid = sum(1 for p in ep if 60 < p < 200) / float(len(ep))
    return white, dark, emid


def ok_image(path):
    im = Image.open(path)
    w, h = im.size
    if w < 240 or h < 180:
        return False
    white, dark, emid = text_heavy(path)
    if white > 0.55 and emid > 0.05:
        return False
    if white > 0.42 and dark > 0.02 and emid > 0.09:
        return False
    return True


def score(c):
    s = 0
    h = F.host_of(c["url"])
    if c.get("src") == "a-hospital":
        s += 60
    if c.get("src") == "commons":
        s += 50
    if "ayxbk" in h or "a-hospital" in h or "yixue" in h:
        s += 40
    if "cnkang" in h or "39.net" in h or "youlai" in h or "bcebos" in h:
        s += 25
    t = (c.get("title") or "")
    for w in ("饮片", "药材", "中药", "植物", "原植物", "性状"):
        if w in t:
            s += 10
    return s


def fetch(name, manifest, want=2):
    for fn in list(manifest.get(name, {}).get("files", [])):
        p = os.path.join(IMG, fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    manifest[name] = {"files": [], "sources": []}

    cands = F.ayxbk_images(name) + F.commons_images(name)
    cands += bing_safe(name, "中药 饮片 药材", 20)
    cands += bing_safe(name, "饮片 炮制", 16)
    cands += bing_safe(name, "原植物", 16)

    seen = set()
    ordered = []
    for c in sorted(cands, key=score, reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    tmp = os.path.join(IMG, "_tmpsafe.jpg")
    for c in ordered:
        if len(manifest[name]["files"]) >= want:
            break
        raw = F.download_image(c)
        if raw is None:
            continue
        try:
            jpg, size = F.process(raw)
        except Exception:
            continue
        with open(tmp, "wb") as f:
            f.write(jpg)
        try:
            good = ok_image(tmp)
        except Exception:
            good = False
        if not good:
            continue
        fn = "%s_%d.jpg" % (re.sub(r'[\\/:*?"<>|]', "_", name),
                            len(manifest[name]["files"]) + 1)
        os.replace(tmp, os.path.join(IMG, fn))
        manifest[name]["files"].append(fn)
        manifest[name]["sources"].append({
            "file": fn, "src": c.get("src", ""), "title": (c.get("title") or "")[:150],
            "descurl": c.get("page", ""), "license": c.get("license", ""),
            "url": c["url"], "size": list(size)})
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        time.sleep(0.1)
    if os.path.exists(tmp):
        os.remove(tmp)
    return manifest[name]["files"]


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--missing" in sys.argv:
        with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
            allnames = [h["name"] for h in json.load(f)["herbs"]]
        names = [n for n in allnames if not manifest.get(n, {}).get("files")]
    else:
        names = args
    if not names:
        print("no names")
        return 2
    ok = 0
    for i, n in enumerate(names):
        try:
            got = fetch(n, manifest)
        except Exception as e:
            got = []
            print("ERR %s: %s" % (n.encode("unicode_escape").decode("ascii"), e), flush=True)
        if got:
            ok += 1
        print("[%d/%d] %s -> %d" % (i + 1, len(names),
              n.encode("unicode_escape").decode("ascii"), len(got or [])), flush=True)
    print("DONE ok=%d/%d" % (ok, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
