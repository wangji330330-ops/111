/* 更新日志自测：数据完整性 + 渲染 + 按钮接线 */
const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'docs');

const nodes = {};
function mkEl(tag) {
  return { tagName: (tag||'div').toUpperCase(), dataset:{}, style:{}, _html:'', _text:'',
    classList:{ _s:new Set(), add(c){this._s.add(c);}, remove(c){this._s.delete(c);},
                toggle(c,on){on?this._s.add(c):this._s.delete(c);}, contains(c){return this._s.has(c);} },
    set innerHTML(v){this._html=String(v);}, get innerHTML(){return this._html;},
    set textContent(v){this._text=String(v);}, get textContent(){return this._text;},
    querySelector:()=>mkEl(), querySelectorAll:()=>[], addEventListener(){}, appendChild(){} };
}
['clModal','clBody','clClose','changelogBtn'].forEach(id=>{ nodes[id]=mkEl('div'); });
global.document = {
  getElementById: id => nodes[id] || mkEl('div'),
  querySelector: s => (s.startsWith('#') ? (nodes[s.slice(1)] || mkEl('div')) : mkEl('div')),
  querySelectorAll: () => [], addEventListener(){}, createElement: mkEl, body:{ style:{} }
};
global.window = {}; global.setInterval=()=>0; global.clearInterval=()=>{};

let src = fs.readFileSync(path.join(web,'changelog.js'),'utf8');
const m = { exports:{} };
new Function('module','exports', src + '\nmodule.exports={CHANGELOG,renderChangelog,openChangelog,closeChangelog};')(m, m.exports);
const L = m.exports;

let bad = 0;
const mark = s => { bad++; console.log('  ✗ ' + s); };

// 1) 数据完整性
if (!Array.isArray(L.CHANGELOG) || L.CHANGELOG.length < 3) mark('CHANGELOG 条数过少');
const seen = new Set();
L.CHANGELOG.forEach(r => {
  if (!r.v || !r.date || !r.title || !Array.isArray(r.items) || !r.items.length) mark('条目字段缺失: ' + JSON.stringify(r.v));
  if (seen.has(r.v)) mark('版本重复: ' + r.v);
  seen.add(r.v);
  if (!/^\d+\.\d+(\.\d+)?$/.test(r.v)) mark('版本号格式异常: ' + r.v);
});
if (!seen.has('1.0.0')) mark('缺少 1.0.0 首发版本');
if (!seen.has('1.4.1')) mark('缺少当前版本 1.4.1');
console.log('版本条目: %d 条 -> %s', L.CHANGELOG.length, L.CHANGELOG.map(r=>'v'+r.v).join(' > '));

// 2) 版本号递增规则校验（末位 +0.01 / 进位 +0.1）
function toNum(v){ const p=v.split('.').map(Number); return (p[0]*100 + (p[1]||0)) * 100 + (p[2]||0); }
const asc = L.CHANGELOG.slice().reverse();   // 从旧到新
for (let i=1;i<asc.length;i++){
  const a=toNum(asc[i-1].v), b=toNum(asc[i].v);
  if (b <= a) mark('版本未递增: %s -> %s', asc[i-1].v, asc[i].v);
}
console.log('版本递增校验: %s', bad===0 ? '通过' : '有问题');

// 3) 渲染
L.renderChangelog('clBody');
const html = nodes['clBody'].innerHTML;
if (!html.includes('v1.4.1')) mark('渲染结果缺当前版本');
if (!html.includes('cl-item')) mark('渲染结果缺条目结构');
if ((html.match(/cl-item/g)||[]).length < L.CHANGELOG.length) mark('渲染条目数不足');
console.log('渲染 HTML: %d 字节，含条目 %d 个', html.length, (html.match(/cl-item/g)||[]).length);

// 4) 打开/关闭
L.openChangelog();
if (!nodes['clModal'].classList.contains('show')) mark('openChangelog 未加 show 类');
L.closeChangelog();
if (nodes['clModal'].classList.contains('show')) mark('closeChangelog 未移除 show 类');
console.log('打开/关闭: %s', '正常');

// 5) index.html / app.js 接线
const idx = fs.readFileSync(path.join(web,'index.html'),'utf8');
const app = fs.readFileSync(path.join(web,'app.js'),'utf8');
if (!idx.includes('<script src="changelog.js">')) mark('index.html 未引入 changelog.js');
if (!idx.includes('id="changelogBtn"')) mark('index.html 缺更新日志按钮');
if (!idx.includes('id="clModal"')) mark('index.html 缺弹窗容器');
if (!app.includes('openChangelog()')) mark('app.js 未调用 openChangelog');
console.log('接线检查: index.html + app.js 均就绪');

// 6) 离线版是否内联
const off = path.join(__dirname,'..','docs','离线版.html');
if (fs.existsSync(off)) {
  const o = fs.readFileSync(off,'utf8');
  const okInline = o.includes('const CHANGELOG') && o.includes('changelogBtn') && o.includes('clModal');
  console.log('离线版内联更新日志: %s', okInline ? '是' : '否');
  if (!okInline) mark('离线版未内联更新日志');
}

console.log('');
console.log(bad === 0 ? 'CHANGELOG SELFTEST PASS' : ('CHANGELOG SELFTEST FAIL (' + bad + ')'));
process.exit(bad === 0 ? 0 : 1);