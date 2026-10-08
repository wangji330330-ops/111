# -*- coding: utf-8 -*-
"""生成单文件离线版网页（不需要服务器、不需要 Git、双击即用）。

输出：发布\中药学复习系统（离线版）.html
  - 题库 / 同义词 / 图片索引全部内嵌到 HTML 里
  - 图片仍从 web/images/ 相对读取；若不存在，则改为读取 exe 同级 images/ 或联网地址
  - 直接把该文件放到 web/ 目录里即可（图片路径相对 web/images/）
"""
import io
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
OUT_DIR = os.path.join(HERE, "发布")


def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()


def main():
    html = read(os.path.join(WEB, "index.html"))
    css = read(os.path.join(WEB, "style.css"))
    js = read(os.path.join(WEB, "app.js"))
    herbs = read(os.path.join(WEB, "data", "herbs.json"))
    syn = read(os.path.join(WEB, "data", "synonyms.json"))
    imgs = read(os.path.join(WEB, "data", "images_manifest.json"))
    ver = read(os.path.join(WEB, "version.json"))

    # 校验 JSON 合法性并压缩
    data = {
        "herbs": json.loads(herbs),
        "synonyms": json.loads(syn),
        "images": json.loads(imgs),
        "version": json.loads(ver),
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    # 内嵌样式
    html = html.replace('<link rel="stylesheet" href="style.css">',
                        "<style>\n" + css + "\n</style>")
    # 内嵌数据（放在 app.js 之前）
    payload = ('<script>window.__TCM_DATA__ = ' + blob + ';</script>\n')
    # 内嵌脚本
    html = html.replace('<script src="app.js"></script>',
                        payload + "<script>\n" + js + "\n</script>")

    # 离线版会放在 发布/ 下，图片目录在 web/images/，改写成相对可用的候选路径
    html = html.replace('src="images/', 'src="images/')

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    out = os.path.join(OUT_DIR, "中药学复习系统（离线版）.html")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(out)
    print("单文件离线版: %s  (%.1f MB)" % (out, size / 1048576.0))
    print("提示：把它复制到 web/ 目录下双击使用，图片即可正常显示。")


if __name__ == "__main__":
    main()
