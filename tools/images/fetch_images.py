# -*- coding: utf-8 -*-
"""联网抓取中药真实图片（A+医学百科条目图 + Bing 图片搜索），并发 8 线程。

输出：
  images/<药名>_<序号>.jpg    处理后的图片（最长边 520px，JPEG）
  images_manifest.json        来源页、标题、许可、尺寸
  images_credits.txt          来源清单（程序内展示用）
  fetch_log.txt               抓取日志

用法：
  python fetch_images.py --workers 8
  python fetch_images.py --limit 10
  python fetch_images.py --report
"""
import concurrent.futures as cf
import io
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = ROOT
IMG_DIR = os.path.join(HERE, "images")
MANIFEST = os.path.join(HERE, "images_manifest.json")
LOG = os.path.join(HERE, "fetch_log.txt")

socket.setdefaulttimeout(12)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# 维基共享资源镜像（部分网络下 wikimedia 主站不可达，但镜像可用）
COMMONS_MIRRORS = [
    "commons.m.wikimedia.org",
    "commons.wikimedia.org",
]
# 维基/Mirror 直链镜像
UPLOAD_MIRRORS = [
    None,                                  # 原始 upload.wikimedia.org
    "upload.wikimedia.beta.wmcloud.org",
]

GOOD_HOSTS = ("ayxbk.com", "a-hospital.com", "yixue.com", "baike", "bcebos",
              "zhongyoo", "yaocai", "zysj", "39.net", "xywy", "120ask",
              "sohu", "163.com", "sina", "qq.com", "ifeng", "haodf", "tcm")
BAD_HOSTS = ("redocn", "iituku", "tuchong", "veer", "zcool", "51yuansu",
             "ooopic", "photophoto", "gettyimages", "shutterstock",
             "dreamstime", "istockphoto", "nanduxing", "alibaba", "1688",
             "taobao", "tmall", "jd.com", "logo", "iconfont", "pexels",
             "unsplash", "pixabay", "freepik")
BAD_TITLE = ("logo", "icon", "图标", "矢量", "壁纸", "地图", "旗帜", "二维码",
             "表情", "广告", "插画", "手绘", "简笔", "卡通", "漫画", "ppt",
             "模板", "海报", "设计", "剪影")

_lock = threading.Lock()
_log_lock = threading.Lock()
_used_urls = set()


def log(msg):
    with _log_lock:
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def http_get(url, referer=None, timeout=12, binary=False):
    hdr = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9"}
    if referer:
        hdr["Referer"] = referer
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


# ---------------- 来源 1：A+医学百科 ----------------
def ayxbk_images(name):
    out = []
    page = "https://www.a-hospital.com/w/" + urllib.parse.quote(name)
    try:
        html = http_get(page, timeout=10)
    except Exception:
        return out
    for m in re.finditer(r'<img[^>]+src="(https?://[^"]+?)"', html):
        src = m.group(1)
        low = src.lower()
        if any(w in low for w in ("/common/images/", "feed-icon", "magnify",
                                  "logo", "icon", "button", "blank")):
            continue
        orig = re.sub(r"/images/thumb/(.+?)/\d+px-[^/]+$", r"/images/\1", src)
        out.append({"url": orig, "page": page, "title": name + "（A+医学百科）",
                    "license": "CC BY-SA（A+医学百科）", "src": "a-hospital"})
    return out[:3]


# ---------------- 来源 2：Bing 图片搜索 ----------------
def bing_images(name, extra="中药 饮片", limit=16):
    url = ("https://cn.bing.com/images/search?q=" +
           urllib.parse.quote(name + " " + extra) + "&form=HDRSC2&first=1")
    try:
        html = http_get(url, timeout=12)
    except Exception:
        return []
    rows = []
    for m in re.finditer(r'm="(\{[^"]*?murl[^"]*?\})"', html):
        raw = m.group(1).replace("&quot;", '"').replace("&amp;", "&")
        try:
            j = json.loads(raw)
        except Exception:
            continue
        u = j.get("murl") or ""
        if u:
            rows.append({"url": u, "title": j.get("t", ""), "page": j.get("purl", ""),
                         "license": "网络图片（见来源页）", "src": "bing"})
    if not rows:
        for m in re.finditer(r'murl&quot;:&quot;(.*?)&quot;', html):
            rows.append({"url": m.group(1), "title": "", "page": "",
                         "license": "网络图片（见来源页）", "src": "bing"})
    return rows[:limit]


# ---------------- 来源 3：维基共享资源（含镜像） ----------------
def commons_api(host, params):
    params = dict(params)
    params["format"] = "json"
    url = "https://" + host + "/w/api.php?" + urllib.parse.urlencode(params)
    return json.loads(http_get(url, timeout=10))


def commons_images(name):
    out = []
    for term in (name, name + " 中药", name + " herb"):
        for host in COMMONS_MIRRORS:
            try:
                j = commons_api(host, {
                    "action": "query", "generator": "search", "gsrsearch": term,
                    "gsrnamespace": 6, "gsrlimit": 6, "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata", "iiurlwidth": 800})
            except Exception:
                continue
            pages = (j.get("query") or {}).get("pages") or {}
            for _, p in pages.items():
                ii = (p.get("imageinfo") or [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if not u:
                    continue
                meta = ii.get("extmetadata") or {}
                title = p.get("title", "")
                if any(w in title.lower() for w in ("logo", "icon", "map", "flag")):
                    continue
                out.append({
                    "url": u, "title": title + "（维基共享资源）",
                    "page": ii.get("descriptionurl", ""),
                    "license": (meta.get("LicenseShortName") or {}).get("value", "见来源页"),
                    "src": "commons"})
            if out:
                return out[:5]
    return out


def download_image(c):
    """下载图片：直链失败时尝试 Bing 图片代理，维基直链再试镜像。"""
    urls = [c["url"]]
    # Bing 缩略图代理（很多站点防盗链时可用）
    if c["url"].startswith("http"):
        q = urllib.parse.quote(c["url"], safe="")
        urls.append("https://tse1.mm.bing.net/th?q=" + q)
        urls.append("https://tse2.mm.bing.net/th?q=" + q)
    if "upload.wikimedia.org" in c["url"]:
        for m in UPLOAD_MIRRORS:
            if m:
                urls.append(c["url"].replace("upload.wikimedia.org", m))
    for u in urls:
        try:
            raw = http_get(u, referer=c.get("page") or "https://cn.bing.com/",
                           timeout=12, binary=True)
            if looks_like_image(raw):
                return raw
        except Exception:
            continue
    return None


def host_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""


def score(c):
    s = 0
    h = host_of(c["url"])
    if any(g in h for g in GOOD_HOSTS):
        s += 40
    if any(b in h for b in BAD_HOSTS):
        s -= 100
    t = (c.get("title") or "") + " " + c.get("page", "")
    if any(w in t.lower() for w in BAD_TITLE):
        s -= 60
    if c.get("src") == "a-hospital":
        s += 30
    if re.search(r"\.(jpg|jpeg|png)(\?|$)", c["url"], re.I):
        s += 5
    return s


def looks_like_image(data):
    if len(data) < 5000:
        return False
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def process(data):
    from PIL import Image
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
    if w < 170 or h < 130:
        raise ValueError("too small %dx%d" % (w, h))
    if max(w, h) > 520:
        k = 520.0 / max(w, h)
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=76, optimize=True)
    return buf.getvalue(), im.size


def load_manifest():
    if os.path.exists(MANIFEST):
        try:
            with open(MANIFEST, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_manifest(m):
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MANIFEST)


def write_credits(m, names):
    lines = ["中药图片资料来源清单", "=" * 60,
             "程序内嵌图片均由下列公开页面抓取，仅用于个人学习复习。",
             "如来源为 CC BY-SA 等许可，来源页即为署名页；如需再分发请遵守相应许可。", ""]
    for n in names:
        rec = m.get(n)
        if not rec or not rec.get("files"):
            continue
        lines.append("%s：" % n)
        for s in rec.get("sources", []):
            lines.append("    %s  ←  %s  [%s]  %s" %
                         (s.get("file", ""), s.get("title", ""),
                          s.get("license", ""), s.get("descurl") or s.get("page", "")))
    with open(os.path.join(HERE, "images_credits.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def herb_names():
    with open(os.path.join(HERE, "herbs.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return [h["name"] for h in data["herbs"]]


def try_one(name, manifest, max_images=2, extra_terms=None):
    if not os.path.isdir(IMG_DIR):
        os.makedirs(IMG_DIR)

    cands = []
    if extra_terms:
        # 二次补抓：专门找炮制品/饮片形态
        for t in extra_terms:
            cands += bing_images(name, t, 12)
    else:
        cands += ayxbk_images(name)
        cands += bing_images(name, "中药 饮片 药材", 16)
        if len(cands) < 4:
            cands += commons_images(name)
        if len(cands) < 4:
            cands += bing_images(name, "植物 药材", 10)
        if len(cands) < 2:
            cands += bing_images(name, "", 10)

    seen = set()
    ordered = []
    for c in sorted(cands, key=score, reverse=True):
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        ordered.append(c)

    saved = []
    for c in ordered:
        if len(saved) >= max_images:
            break
        if score(c) < -50:
            continue
        with _lock:
            if c["url"] in _used_urls:
                continue
        raw = download_image(c)
        if raw is None:
            continue
        try:
            jpg, size = process(raw)
        except Exception:
            continue
        if len(jpg) < 4000:
            continue
        rec = manifest.setdefault(name, {"files": [], "sources": []})
        start = 1 if extra_terms else len(rec["files"]) + 1
        fn = "%s_%d.jpg" % (re.sub(r'[\\/:*?"<>|]', "_", name), start)
        with open(os.path.join(IMG_DIR, fn), "wb") as f:
            f.write(jpg)
        with _lock:
            _used_urls.add(c["url"])
        saved.append(fn)
        with _lock:
            if fn not in rec["files"]:
                rec["files"].append(fn)
            rec["sources"].append({
                "file": fn, "src": c.get("src", ""), "title": c.get("title", "")[:150],
                "descurl": c.get("page", ""), "license": c.get("license", ""),
                "url": c["url"], "size": list(size)})
            save_manifest(manifest)
    return saved


def main():
    args = sys.argv[1:]
    manifest = load_manifest()
    names = herb_names()

    if "--report" in args:
        have = [n for n in names if manifest.get(n, {}).get("files")]
        total_imgs = sum(len(manifest.get(n, {}).get("files", [])) for n in names)
        log("REPORT herbs=%d with_image=%d images=%d coverage=%.1f%%" %
            (len(names), len(have), total_imgs, 100.0 * len(have) / len(names)))
        miss = [n for n in names if not manifest.get(n, {}).get("files")]
        log("missing(%d): %s" % (len(miss), "".join(miss).encode("unicode_escape").decode("ascii")[:3000]))
        return 0

    limit = None
    workers = 8
    retry_missing = "--retry" in args
    second = "--second" in args
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        if a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])

    for n in names:
        for s in manifest.get(n, {}).get("sources", []):
            if s.get("url"):
                _used_urls.add(s["url"])

    extra = ["药材 炮制", "饮片 切片", "中药 生品 制品"]
    if second:
        # 只处理“已有 1 张图”的药，补第 2 张（尽量是炮制品/饮片形态）
        todo = [n for n in names if len(manifest.get(n, {}).get("files", [])) == 1]
    elif retry_missing:
        todo = [n for n in names if not manifest.get(n, {}).get("files")]
    else:
        todo = [n for n in names if not manifest.get(n, {}).get("files")]
    if limit:
        todo = todo[:limit]

    log("START todo=%d already=%d workers=%d mode=%s" %
        (len(todo), len(names) - len(todo), workers, "second" if second else "normal"))
    ok = 0
    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {}
        for n in todo:
            if second:
                futs[ex.submit(try_one, n, manifest, 1, extra)] = n
            else:
                futs[ex.submit(try_one, n, manifest, 2, None)] = n
        for fut in cf.as_completed(futs):
            n = futs[fut]
            done += 1
            try:
                got = fut.result()
            except Exception as e:
                got = []
                log("ERR %s: %s" % (n.encode("unicode_escape").decode("ascii"), e))
            if got:
                ok += 1
            if done % 5 == 0 or done == len(todo) or got:
                el = time.time() - t0
                log("[%d/%d] %s -> %d  (%.1f min elapsed, %.1f/min)" %
                    (done, len(todo), n.encode("unicode_escape").decode("ascii"),
                     len(got or []), el / 60.0, done / max(0.001, el / 60.0)))

    write_credits(manifest, names)
    have = [n for n in names if manifest.get(n, {}).get("files")]
    log("DONE fetched=%d total_with_image=%d/%d (%.1f%%) in %.1f min" %
        (ok, len(have), len(names), 100.0 * len(have) / len(names), (time.time() - t0) / 60.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
