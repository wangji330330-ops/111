# -*- coding: utf-8 -*-
"""为新增药味生成可点击的图片核验页（离线可用）。

用法: python tools/review/mkcheck_new.py
输出: review/check_new.html
  · 每味一张卡片，显示 2 张图 + 药名，点击图片放大
  · 点「✗ 有问题」标记，底部汇总，一键复制反馈
  · 图片路径指向 ../docs/images/（与网页版同一批文件）
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "check_new.html")


def main():
    sys.path.insert(0, ROOT)
    import herbs_additions as A
    with io.open(os.path.join(ROOT, "images_manifest.json"), encoding="utf-8") as f:
        man = json.load(f)

    # 新增药味（按批次顺序，去重）
    names = []
    for b in getattr(A, "ENABLED_BATCHES", [1, 2, 3, 4]):
        for rec in getattr(A, "ADDITIONS_%d" % b, []):
            n = rec[0]
            if n not in names and man.get(n, {}).get("files"):
                names.append(n)

    cards = []
    for i, n in enumerate(names, 1):
        files = man[n]["files"][:2]
        # 分类信息（用于卡片副标题）
        cat = ""
        for b in getattr(A, "ENABLED_BATCHES", [1, 2, 3, 4]):
            for rec in getattr(A, "ADDITIONS_%d" % b, []):
                if rec[0] == n:
                    cat = rec[1]
                    break
            if cat:
                break
        imgs = "".join(
            '<img src="../docs/images/%s" alt="%s" loading="lazy" onclick="zoom(this)">' % (f, n)
            for f in files)
        cards.append(
            '<div class="c" data-n="%s"><div class="hd"><b>%d. %s</b>'
            '<span class="cat">%s</span>'
            '<button class="mk" onclick="mark(this)">✗ 有问题</button></div>'
            '<div class="im">%s</div></div>' % (n, i, n, cat, imgs))

    CSS = """
body{font:14px/1.55 "Microsoft YaHei",system-ui,sans-serif;margin:16px 16px 78px;background:#f6f8f7;color:#1f2a26}
h1{font-size:20px;margin:0 0 6px}
.tip{color:#5b6b64;margin-bottom:14px;line-height:1.7}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.c{background:#fff;border:1px solid #e2e8e5;border-radius:12px;padding:10px;box-shadow:0 1px 6px rgba(20,40,32,.05)}
.c.marked{border-color:#e05a4c;background:#fff6f5}
.hd{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:15px;flex-wrap:wrap}
.hd b{font-size:15.5px}
.cat{font-size:11.5px;color:#6e7874;background:#f2f5f3;border:1px solid #e2e8e5;border-radius:999px;padding:1px 8px}
.mk{margin-left:auto}
.im{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.im img{width:100%;height:150px;object-fit:cover;border-radius:8px;border:1px solid #eceeed;cursor:zoom-in;background:#fafbfa}
button{font:inherit;font-size:12.5px;border:1px solid #d7ded9;background:#fff;border-radius:999px;padding:3px 12px;cursor:pointer}
button:hover{background:#f0f4f2}
.c.marked button.mk{background:#e05a4c;border-color:#e05a4c;color:#fff}
#bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #dfe5e1;padding:10px 16px;display:flex;gap:12px;align-items:center;box-shadow:0 -2px 12px rgba(0,0,0,.06)}
#out{flex:1;font-size:13px;color:#2b6b52;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;place-items:center;z-index:9;cursor:zoom-out}
#lb img{max-width:94vw;max-height:94vh;border-radius:8px}
"""

    JS = """
const marked=new Set();
function mark(b){
  const c=b.closest('.c'), n=c.dataset.n;
  if(marked.has(n)){marked.delete(n);c.classList.remove('marked');b.textContent='✗ 有问题';}
  else{marked.add(n);c.classList.add('marked');b.textContent='✓ 待换';}
  paint();
}
function paint(){
  const a=[...marked];
  document.getElementById('out').textContent = a.length ? ('待换 '+a.length+' 味：'+a.join('、')) : '尚未标记任何问题';
}
function zoom(im){document.getElementById('lbi').src=im.src;document.getElementById('lb').style.display='grid';}
function copyOut(){
  const a=[...marked];
  const t = a.length ? ('需要重换：'+a.join('、')) : '全部正确';
  if(navigator.clipboard) navigator.clipboard.writeText(t);
  alert(t);
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').style.display='none';});
"""

    html = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>新增药味图片核验（%d 味）</title>
<style>@@CSS@@</style></head>
<body>
<h1>新增药味 · 图片核验（共 %d 味）</h1>
<div class="tip">
每味显示 2 张图（左=图1，右=图2），标题右侧灰字是该药的分类。<br>
<b>哪一味不对，就点它右上角「✗ 有问题」</b>；点图片可放大（Esc 关闭）。<br>
核完点底部「复制反馈」，把绿色那行发我即可 —— 我会立刻重抓替换。
</div>
<div class="grid">@@CARDS@@</div>
<div id="bar"><span>已标记：</span><span id="out">尚未标记任何问题</span>
<button onclick="copyOut()">复制反馈</button></div>
<div id="lb" onclick="this.style.display='none'"><img id="lbi" alt=""></div>
<script>@@JS@@</script>
</body></html>"""

    html = (html.replace("@@CSS@@", CSS)
                .replace("@@CARDS@@", "".join(cards))
                .replace("@@JS@@", JS)
                .replace("%d", str(len(names)), 1)
                .replace("%d", str(len(names))))
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("生成: %s (%d 字节, %d 味)" % (OUT, os.path.getsize(OUT), len(names)))


if __name__ == "__main__":
    main()
