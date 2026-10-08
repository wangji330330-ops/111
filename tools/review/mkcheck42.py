# -*- coding: utf-8 -*-
"""生成 42 味图片核验页面（离线可用）：点击标记“有问题”+ 一键复制反馈"""
import io
import os

ROOT = r"E:\正常玩\中药复习程序"
names = [x.strip() for x in
         io.open(os.path.join(ROOT, "review", "fix42.txt"), encoding="utf-8").read().split("\n")
         if x.strip()]

cards = []
for i, n in enumerate(names, 1):
    imgs = []
    for k in (1, 2):
        fn = "%s_%d.jpg" % (n, k)
        if os.path.exists(os.path.join(ROOT, "images", fn)):
            imgs.append('<img src="../images/%s" alt="%s" onclick="zoom(this)">' % (fn, n))
    cards.append(
        '<div class="c" data-n="%s"><div class="hd"><b>%d. %s</b>'
        '<button class="mk" onclick="mark(this)">✗ 有问题</button></div>'
        '<div class="im">%s</div></div>' % (n, i, n, "".join(imgs)))

CSS = """
body{font:14px/1.5 "Microsoft YaHei",system-ui,sans-serif;margin:16px 16px 70px;background:#f6f8f7;color:#1f2a26}
h1{font-size:20px;margin:0 0 6px}
.tip{color:#5b6b64;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.c{background:#fff;border:1px solid #e2e8e5;border-radius:12px;padding:10px;box-shadow:0 1px 6px rgba(20,40,32,.05)}
.c.marked{border-color:#e05a4c;background:#fff6f5}
.hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:15px}
.im{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.im img{width:100%;height:150px;object-fit:cover;border-radius:8px;border:1px solid #eceeed;cursor:zoom-in;background:#fafbfa}
button{font:inherit;font-size:12.5px;border:1px solid #d7ded9;background:#fff;border-radius:999px;padding:3px 12px;cursor:pointer}
button:hover{background:#f0f4f2}
.c.marked button{background:#e05a4c;border-color:#e05a4c;color:#fff}
#bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #dfe5e1;padding:10px 16px;display:flex;gap:12px;align-items:center;box-shadow:0 -2px 12px rgba(0,0,0,.06)}
#out{flex:1;font-size:13px;color:#2b6b52;font-weight:700}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.86);display:none;place-items:center;z-index:9}
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
  document.getElementById('out').textContent = a.length ? a.join('、') : '（无）';
}
function zoom(im){document.getElementById('lbi').src=im.src;document.getElementById('lb').style.display='grid';}
function copyOut(){
  const a=[...marked];
  const t = a.length ? ('需要重换：'+a.join('、')) : '42 味全部正确';
  if(navigator.clipboard) navigator.clipboard.writeText(t);
  alert(t);
}
"""

html = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>42 味中药图片核验</title>
<style>@@CSS@@</style></head>
<body>
<h1>42 味中药 · 新图片核验</h1>
<div class="tip">每味显示 2 张（左=图1，右=图2）。<b>哪一味不对，就点它右上角「✗ 有问题」</b>；点图片可放大。
看完后把底部绿色那行文字发我即可。</div>
<div class="grid">@@CARDS@@</div>
<div id="bar"><span>已标记：</span><span id="out">（无）</span>
<button onclick="copyOut()">复制反馈</button></div>
<div id="lb" onclick="this.style.display='none'"><img id="lbi" alt=""></div>
<script>@@JS@@</script>
</body></html>"""

html = html.replace("@@CSS@@", CSS).replace("@@CARDS@@", "".join(cards)).replace("@@JS@@", JS)

out = os.path.join(ROOT, "review", "check42.html")
io.open(out, "w", encoding="utf-8").write(html)
print("生成:", out, os.path.getsize(out), "字节，42 味")
