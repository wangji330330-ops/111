# -*- coding: utf-8 -*-
"""生成单文件离线版网页（不需要服务器、不需要 Git、双击即用）。

输出：发布\\中药学复习系统（离线版）.html
  - 题库 / 同义词 / 图片索引全部内嵌到 HTML 里
  - 所有 CSS 与 JS（style.css / style2.css / timeherb.js / app.js）全部内联，
    新增样式或脚本时无需改本文件
  - 图片仍从同目录 docs/images/ 相对读取

注意：内联脚本顺序必须与 index.html 中一致（timeherb.js 要在 app.js 之前），
      因为 app.js 的 boot() 会调用 timeherb.js 里的 startClock()/renderRandomHerb()。
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "docs")
OUT_DIR = os.path.join(HERE, "发布")

CSS_FILES = ["style.css", "style2.css"]
JS_FILES = ["changelog.js", "encourage.js", "timeherb.js", "app.js"]


def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()


def main():
    html = read(os.path.join(WEB, "index.html"))

    # ---- 内联全部样式表 ----
    for name in CSS_FILES:
        tag = '<link rel="stylesheet" href="%s">' % name
        if tag not in html:
            print("警告：index.html 中未找到 %s 的引用，已跳过" % name)
            continue
        css = read(os.path.join(WEB, name))
        html = html.replace(tag, "<style>\n/* ==== %s ==== */\n%s\n</style>" % (name, css))

    # ---- 内嵌数据（必须在脚本之前） ----
    data = {
        "herbs": json.loads(read(os.path.join(WEB, "data", "herbs.json"))),
        "synonyms": json.loads(read(os.path.join(WEB, "data", "synonyms.json"))),
        "images": json.loads(read(os.path.join(WEB, "data", "images_manifest.json"))),
        "version": json.loads(read(os.path.join(WEB, "version.json"))),
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = '<script>window.__TCM_DATA__ = ' + blob + ';</script>\n'

    # ---- 内联全部脚本（保持顺序） ----
    first = True
    for name in JS_FILES:
        tag = '<script src="%s"></script>' % name
        if tag not in html:
            print("警告：index.html 中未找到 %s 的引用，已跳过" % name)
            continue
        js = read(os.path.join(WEB, name))
        block = "<script>\n/* ==== %s ==== */\n%s\n</script>" % (name, js)
        if first:
            block = payload + block
            first = False
        html = html.replace(tag, block)
    if first:
        # 一个脚本都没替换到：兜底，至少把数据塞进去
        html = html.replace("</body>", payload + "</body>")

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    out = os.path.join(OUT_DIR, "中药学复习系统（离线版）.html")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(out)
    print("单文件离线版: %s  (%.1f MB)" % (out, size / 1048576.0))
    print("已内联样式: %s" % ", ".join(CSS_FILES))
    print("已内联脚本: %s" % ", ".join(JS_FILES))
    print("提示：把它复制到 docs/ 目录下双击使用，图片即可正常显示。")


if __name__ == "__main__":
    main()
