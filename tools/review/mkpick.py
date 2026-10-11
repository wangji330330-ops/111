# -*- coding: utf-8 -*-
"""生成挑图页：每味一行 10 张高清候选，点选后复制结果给我。

输出: review/pick.html

要点：
  · 每张图下方烙着「第 N 列」，报列号即可精确取文件，绝不会错位；
  · 图上标出真实分辨率（都是 ≥800×600 的高清图，接口尺寸已用 PIL 复核）；
  · 被自动裁掉文字条的图会标「已裁文字条」；
  · 每张图标一个「干净度」徽章（文字行占比），帮你一眼跳过带字的图；
  · 加 --rank 时会把每味药的候选按干净度重排（干净的排前面），列号同步重编；
  · 点缩略图可选中/取消，右上「🔍 看大图」在新标签打开原图；
  · 选择结果存在浏览器 localStorage，刷新不丢；底部可「复制结果」。
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HD = os.path.join(ROOT, "review", "hd")
INDEX = os.path.join(HD, "index.json")
NAMES_FILE = os.path.join(ROOT, "review", "refetch_names.txt")
OUT = os.path.join(ROOT, "review", "pick.html")

HERBS = json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]
PY = {h["name"]: h.get("pinyin", "") for h in HERBS}
CAT = {h["name"]: h.get("cat", "") for h in HERBS}


def text_rows(path):
    """图上「文字行」占比（0 ~ 1）。实测：干净实拍 ≈0.00~0.10，带字幕/广告 ≥0.20"""
    try:
        import numpy as np
        from PIL import Image
        im = Image.open(path)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((460, 460))
        g = np.asarray(im.convert("L"), dtype=np.int16)
        dx = np.abs(np.diff(g, axis=1))
        rows = (dx > 40).mean(axis=1)
        return float((rows > 0.055).mean())
    except Exception:
        return -1.0


def rank(idx):
    """把每味药的候选按干净度升序重排并重新编号。

    坑：直接 in-place 改名会撞名 —— 第 3 个要改成 c01，而 c01 还是第 1 个的名字，
    旧代码会先 os.remove(dst) 把别人的图删掉（实测差点毁掉 900 张候选）。
    所以分两步：先全部改成临时名，再落到最终名。
    """
    qc_path = os.path.join(HD, "qc.json")
    qc = json.load(io.open(qc_path, encoding="utf-8")) if os.path.exists(qc_path) else {}
    moved = 0
    for name, items in idx.items():
        if not items:
            continue
        items = [m for m in items if os.path.exists(os.path.join(HD, m["file"]))]
        if not items:
            idx[name] = []
            continue
        for m in items:
            if m["file"] not in qc:
                qc[m["file"]] = {"text": text_rows(os.path.join(HD, m["file"]))}
        items.sort(key=lambda m: qc.get(m["file"], {}).get("text", 9))

        staged = []
        for i, m in enumerate(items):
            src = os.path.join(HD, m["file"])
            t = os.path.join(HD, "__tmp_%04d.jpg" % i)
            if os.path.exists(src):
                os.replace(src, t)
                staged.append((m, t))
        for i, (m, t) in enumerate(staged, 1):
            new = "%s_c%02d.jpg" % (name, i)
            dst = os.path.join(HD, new)
            if os.path.exists(dst):
                os.remove(dst)
            os.replace(t, dst)
            if m["file"] != new:
                moved += 1
            m["file"] = new
        idx[name] = [m for m, _ in staged]

    json.dump(qc, io.open(qc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(idx, io.open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("重排候选 %d 个文件（干净的排前面）" % moved)
    return qc

CSS = """
:root{--brand:#1f6f52;--accent:#b4602f;--line:#e2e8e5;--sub:#7b8a84}
*{box-sizing:border-box}
body{font:14px/1.55 "Microsoft YaHei",system-ui,sans-serif;margin:0;background:#f5f7f6;color:#1f2a26}
header{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);
  padding:10px 14px;box-shadow:0 2px 10px rgba(20,40,32,.06)}
.h1{font-size:17px;font-weight:800;color:var(--brand);margin:0 0 4px}
.tip{font-size:12.5px;color:var(--sub);line-height:1.7}
.tip b{color:#c0392b}
.bar{display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap}
input[type=search]{font:inherit;font-size:13px;padding:5px 12px;border:1px solid var(--line);
  border-radius:999px;width:220px;outline:none}
input[type=search]:focus{border-color:var(--brand)}
.stat{font-size:12.5px;color:var(--brand);font-weight:700}
button{font:inherit;font-size:13px;border:1px solid #d7ded9;background:#fff;border-radius:999px;
  padding:5px 14px;cursor:pointer}
button:hover{background:#f0f4f2}
button.primary{background:var(--brand);color:#fff;border-color:var(--brand)}
button.primary:hover{background:#1a5c44}
main{padding:14px 14px 96px}
section.row{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;
  margin-bottom:12px;box-shadow:0 1px 5px rgba(20,40,32,.05)}
section.row.done{border-color:#9ed0bb;background:#f7fdfa}
h3{margin:0 0 8px;font-size:16px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
h3 .py{font-size:12.5px;color:var(--sub);font-weight:400}
h3 .cat{font-size:12px;color:#9aa5a0;font-weight:400}
h3 .picked{margin-left:auto;font-size:12.5px;color:var(--brand);font-weight:700}
.cells{display:flex;gap:9px;overflow-x:auto;padding:2px 2px 6px}
figure{margin:0;flex:0 0 auto;width:186px;border:2px solid #e6ebe8;border-radius:10px;
  overflow:hidden;cursor:pointer;background:#fafbfa;position:relative}
figure:hover{border-color:#b9cec5}
figure img{display:block;width:186px;height:150px;object-fit:cover;background:#eef1ef}
figcaption{font-size:11.5px;text-align:center;color:#5d6a65;padding:3px 0 4px;background:#f2f5f3;
  line-height:1.45}
figcaption b{color:#2b6b52}
figure.sel{border-color:#2b8a68;box-shadow:0 0 0 3px rgba(43,138,104,.18)}
figure.sel::after{content:"已选";position:absolute;left:5px;top:5px;background:#2b8a68;color:#fff;
  font-size:11px;border-radius:5px;padding:1px 7px}
.zoom{position:absolute;right:5px;top:5px;background:rgba(0,0,0,.55);color:#fff;font-size:11px;
  border-radius:5px;padding:2px 7px;text-decoration:none}
.zoom:hover{background:rgba(0,0,0,.78)}
.trim{position:absolute;left:5px;bottom:34px;background:rgba(180,96,47,.9);color:#fff;font-size:10.5px;
  border-radius:4px;padding:1px 6px}
.qb{display:inline-block;border-radius:4px;padding:0 5px;font-size:10.5px;color:#fff}
.q1{background:#2b8a68}.q2{background:#c99a2e}.q3{background:#c0392b}.q0{background:#9aa5a0}
.site{color:#a8b3ae;font-size:10.5px}
footer{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);
  padding:9px 16px;display:flex;gap:12px;align-items:center;box-shadow:0 -2px 12px rgba(0,0,0,.07)}
#out{flex:1;font-size:12.5px;color:#2b6b52;font-weight:700;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.hide{display:none !important}
@media (max-width:640px){figure{width:150px}figure img{width:150px;height:122px}}
"""

JS = """
const picked = JSON.parse(localStorage.getItem('tcmpick') || '{}');
function save(){ localStorage.setItem('tcmpick', JSON.stringify(picked)); }
function pick(fig){
  const herb = fig.dataset.herb, col = parseInt(fig.dataset.col, 10);
  const cur = picked[herb] || [];
  const i = cur.indexOf(col);
  if (i >= 0) { cur.splice(i,1); fig.classList.remove('sel'); }
  else { cur.push(col); cur.sort((a,b)=>a-b); fig.classList.add('sel'); }
  if (cur.length) picked[herb] = cur; else delete picked[herb];
  const row = fig.closest('section.row');
  const lbl = row.querySelector('.picked');
  lbl.textContent = (picked[herb] && picked[herb].length)
    ? ('已选：第 ' + picked[herb].join('、') + ' 列') : '未选';
  row.classList.toggle('done', !!(picked[herb] && picked[herb].length));
  save(); paint();
}
function paint(){
  const keys = Object.keys(picked);
  document.getElementById('stat').textContent = '已选 ' + keys.length + ' / ' + TOTAL + ' 味';
  document.getElementById('out').textContent = keys.length
    ? keys.slice(0,40).map(k => k + ':' + picked[k].join(',')).join('  ')
      + (keys.length > 40 ? ' …' : '')
    : '尚未选择（点缩略图即可选中/取消）';
}
function copyOut(){
  const keys = Object.keys(picked);
  const t = keys.length ? keys.map(k => k + ':' + picked[k].join(',')).join('\\n') : '（未选）';
  if (navigator.clipboard) navigator.clipboard.writeText(t).then(
    ()=>alert('已复制 '+keys.length+' 味，粘贴发我即可：\\n\\n'+t.slice(0,1500)),
    ()=>alert(t));
  else alert(t);
}
function filter(){
  const kw = document.getElementById('q').value.trim();
  document.querySelectorAll('section.row').forEach(s => {
    s.classList.toggle('hide', !!kw && s.dataset.herb.indexOf(kw) < 0);
  });
}
function onlyUndone(){
  const on = document.getElementById('onlyUndone').checked;
  document.querySelectorAll('section.row').forEach(s => {
    if (on && s.classList.contains('done')) s.classList.add('hide');
    else if (!document.getElementById('q').value.trim()) s.classList.remove('hide');
  });
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('figure').forEach(f => {
    if ((picked[f.dataset.herb] || []).indexOf(parseInt(f.dataset.col,10)) >= 0) f.classList.add('sel');
  });
  document.querySelectorAll('section.row').forEach(s => {
    const p = picked[s.dataset.herb];
    if (p && p.length) {
      s.classList.add('done');
      s.querySelector('.picked').textContent = '已选：第 ' + p.join('、') + ' 列';
    }
  });
  const q = document.getElementById('q');
  q.addEventListener('input', filter);
  document.getElementById('onlyUndone').addEventListener('change', onlyUndone);
  paint();
});
"""


def main():
    idx = json.load(io.open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) else {}
    qc = rank(idx) if "--rank" in sys.argv else (
        json.load(io.open(os.path.join(HD, "qc.json"), encoding="utf-8"))
        if os.path.exists(os.path.join(HD, "qc.json")) else {})
    names = [l.strip() for l in io.open(NAMES_FILE, encoding="utf-8") if l.strip()]
    rows, total_imgs = [], 0
    for n in names:
        items = idx.get(n) or []
        items = [m for m in items if os.path.exists(os.path.join(HD, m["file"]))]
        total_imgs += len(items)
        cells = []
        for i, m in enumerate(items, 1):
            badge = '%d×%d' % (m["w"], m["h"])
            t = (qc.get(m["file"]) or {}).get("text", -1)
            if t < 0:
                cls, tip = "q0", "未质检"
            elif t <= 0.12:
                cls, tip = "q1", "干净"
            elif t <= 0.25:
                cls, tip = "q2", "轻微文字"
            else:
                cls, tip = "q3", "疑似带字"
            trim = '<span class="trim">已裁文字条</span>' if m.get("trimmed") else ''
            cells.append(
                '<figure data-herb="%s" data-col="%d" onclick="pick(this)">'
                '<a class="zoom" href="hd/%s" target="_blank" '
                'onclick="event.stopPropagation()" title="在新标签看原图">🔍看大图</a>'
                '<img src="hd/%s" alt="%s 第%d列" loading="lazy">%s'
                '<figcaption><b>第 %d 列</b> · %s<br>'
                '<span class="qb %s" title="文字行占比 %.2f">%s</span> '
                '<span class="site">%s</span></figcaption>'
                '</figure>' % (n, i, m["file"], m["file"], n, i, trim, i, badge,
                               cls, max(t, 0), tip, (m.get("site") or "")[:16]))
        if not items:
            cells.append('<div style="color:#c0392b;font-size:13px;padding:8px">'
                         '（还没抓到候选，脚本可能仍在跑，稍后刷新本页）</div>')
        rows.append(
            '<section class="row" data-herb="%s"><h3>%s<span class="py">%s</span>'
            '<span class="cat">%s</span><span class="picked">未选</span></h3>'
            '<div class="cells">%s</div></section>'
            % (n, n, PY.get(n, ""), CAT.get(n, ""), "".join(cells)))

    html = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>挑图 · 高清候选（@@N@@ 味 / @@M@@ 张）</title><style>@@CSS@@</style></head>
<body>
<header>
  <div class="h1">挑图：每味 10 张高清候选（已就绪 @@N@@ 味 / @@M@@ 张）</div>
  <div class="tip">
    ① 横向滑动看完 10 张，点你要的（可多选，选中显示绿框「已选」）；<br>
    ② 图上「<b>第 N 列</b>」就是我取文件的编号，报列号绝不会错位；<br>
    ③ 每张图下面有个小徽章：<span class="qb q1">干净</span> 优先看这些，
       <span class="qb q2">轻微文字</span> 要仔细看，<span class="qb q3">疑似带字</span> 基本可以直接跳过；<br>
    ④ <b>只要图上有文字、数字、水印、广告语、价格、店铺名，就不要选它</b>；风景图/商品包装图也不要；<br>
    ⑤ 想看清楚就点右上「🔍看大图」在新标签打开原图（都是 ≥800×600 的高清真图）；<br>
    ⑥ 选完点右下「复制结果」，把那串「药名:列号」发我即可。
  </div>
  <div class="bar">
    <input type="search" id="q" placeholder="输入药名快速定位…">
    <label style="font-size:12.5px;color:#5b6b64"><input type="checkbox" id="onlyUndone"> 只显示还没选的</label>
    <span class="stat" id="stat">已选 0 / @@N@@ 味</span>
    <button class="primary" onclick="copyOut()">复制结果</button>
    <button onclick="if(confirm('清空全部选择？')){localStorage.removeItem('tcmpick');location.reload();}">清空</button>
  </div>
</header>
<main>@@ROWS@@</main>
<footer><span style="font-size:12.5px;color:#5b6b64">已选：</span><span id="out"></span>
<button class="primary" onclick="copyOut()">复制结果</button></footer>
<script>const TOTAL=@@N@@;</script>
<script>@@JS@@</script>
</body></html>"""

    html = (html.replace("@@CSS@@", CSS).replace("@@ROWS@@", "".join(rows))
            .replace("@@JS@@", JS).replace("@@N@@", str(len(names)))
            .replace("@@M@@", str(total_imgs)))
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("生成 %s（%d 味 / %d 张候选，%.1f MB）" %
          (OUT, len(names), total_imgs, os.path.getsize(OUT) / 1048576.0))


if __name__ == "__main__":
    main()
