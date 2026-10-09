# -*- coding: utf-8 -*-
"""生成「编号核验页」：用户只要报“药名 + 第几列”，脚本按列号精确取候选文件。

输出: review/numbered_check.html
  · 26 味，每味一行：标题 + 8 张候选（图上烙有“第N列”）
  · 点击候选图 = 选中（边框变绿并显示「已选」）；再点取消
  · 底部「复制结果」输出形如：禹余粮	第8列 ; 藜芦	第3列
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAND = os.path.join(ROOT, "review", "c360fix2")
OUT = os.path.join(ROOT, "review", "numbered_check.html")
NAMES = ["槐角", "泽兰", "榧子", "绿萼梅", "冬瓜子", "秦皮", "海蛤壳", "刘寄奴", "禹余粮", "浮小麦",
         "藜芦", "瓜蒂", "胆矾", "土荆皮", "硫黄", "轻粉", "铅丹", "硼砂", "刺五加", "鹿角霜",
         "核桃仁", "紫河车", "锁阳", "胆南星", "安息香", "虻虫"]


def main():
    rows = []
    for n in NAMES:
        files = sorted([f for f in os.listdir(CAND)
                        if f.startswith(n + "_c") and f.endswith(".jpg")])
        cells = []
        for i, f in enumerate(files, 1):
            cells.append(
                '<figure class="cell" data-herb="%s" data-col="%d" onclick="pick(this)">'
                '<img src="../review/c360fix2/%s" alt="%s 第%d列" loading="lazy">'
                '<figcaption>第 %d 列</figcaption></figure>' % (n, i, f, n, i, i))
        rows.append(
            '<section class="row"><h3>%s <span class="cnt">（%d 张）</span>'
            '<span class="picked" id="pk_%s">未选</span></h3>'
            '<div class="cells">%s</div></section>' % (n, len(files), n, "".join(cells)))

    CSS = """
body{font:14px/1.5 "Microsoft YaHei",system-ui,sans-serif;margin:14px 14px 84px;background:#f6f8f7;color:#1f2a26}
h1{font-size:19px;margin:0 0 4px}
.tip{color:#5b6b64;margin-bottom:12px;line-height:1.75}
.tip b{color:#c0392b}
.row{background:#fff;border:1px solid #e2e8e5;border-radius:12px;padding:10px 12px;margin-bottom:12px;box-shadow:0 1px 5px rgba(20,40,32,.05)}
.row h3{margin:0 0 8px;font-size:16px}
.cnt{font-size:12px;color:#8b9791;font-weight:400}
.picked{margin-left:10px;font-size:12.5px;color:#2b6b52;font-weight:700}
.cells{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px}
.cell{flex:0 0 auto;margin:0;border:2px solid #e6ebe8;border-radius:10px;overflow:hidden;cursor:pointer;background:#fafbfa;position:relative}
.cell img{display:block;width:150px;height:150px;object-fit:cover}
.cell figcaption{font-size:11.5px;text-align:center;color:#6e7874;padding:2px 0;background:#f2f5f3}
.cell.sel{border-color:#2b8a68;box-shadow:0 0 0 3px rgba(43,138,104,.18)}
.cell.sel::after{content:"已选";position:absolute;left:4px;top:4px;background:#2b8a68;color:#fff;font-size:11px;border-radius:4px;padding:1px 6px}
#bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #dfe5e1;padding:10px 16px;display:flex;gap:12px;align-items:center;box-shadow:0 -2px 12px rgba(0,0,0,.06)}
#out{flex:1;font-size:12.5px;color:#2b6b52;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
button{font:inherit;font-size:13px;border:1px solid #d7ded9;background:#fff;border-radius:999px;padding:4px 14px;cursor:pointer}
button:hover{background:#f0f4f2}
"""

    JS = """
const picked={};   // herb -> Array(col)
function pick(fig){
  const herb=fig.dataset.herb, col=parseInt(fig.dataset.col,10);
  const row=fig.closest('.row');
  const cur=picked[herb]||[];
  const idx=cur.indexOf(col);
  if(idx>=0){ cur.splice(idx,1); fig.classList.remove('sel'); }
  else { cur.push(col); cur.sort((a,b)=>a-b); fig.classList.add('sel'); }
  if(cur.length) picked[herb]=cur; else delete picked[herb];
  const lbl=row.querySelector('.picked');
  lbl.textContent = (picked[herb]&&picked[herb].length) ? ('已选：第 '+picked[herb].join('、')+' 列') : '未选';
  paint();
}
function paint(){
  const keys=Object.keys(picked);
  document.getElementById('out').textContent = keys.length
    ? keys.map(k=> k+' 第'+picked[k].join('、')+'列').join(' ； ')
    : '尚未选择（点上方缩略图即可选中/取消）';
}
function copyOut(){
  const keys=Object.keys(picked);
  const t = keys.length ? keys.map(k=> k+'\\t第'+picked[k].join(',')+'列').join('\\n') : '（未选）';
  if(navigator.clipboard) navigator.clipboard.writeText(t);
  alert(t);
}
"""

    html = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>26 味候选编号核验</title><style>@@CSS@@</style></head>
<body>
<h1>26 味 · 候选编号核验（报“第几列”即可）</h1>
<div class="tip">
每味一行，横向 8 张候选，<b>图下方写着「第 N 列」</b>。<br>
① 横向滑动看完，点你要的那张（可多选，选中会显示绿框「已选」）；<br>
② 每行右侧会显示「已选：第 x、y 列」；<br>
③ 全选完点底部「复制结果」，把那几行发我 —— 我按列号精确取文件，绝不会错位。<br>
<b>判断标准：只要图上有任何文字、数字、水印、广告语，就不要选它。</b>
</div>
@@ROWS@@
<div id="bar"><span>已选：</span><span id="out">尚未选择（点上方缩略图即可选中/取消）</span>
<button onclick="copyOut()">复制结果</button></div>
<script>@@JS@@</script>
</body></html>"""

    html = html.replace("@@CSS@@", CSS).replace("@@ROWS@@", "".join(rows)).replace("@@JS@@", JS)
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("生成: %s (%d KB, %d 味)" % (OUT, os.path.getsize(OUT) // 1024, len(NAMES)))


if __name__ == "__main__":
    main()
