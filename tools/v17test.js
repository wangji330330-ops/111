/* v1.7.0 自测：别名 / 产地分布 / 药用部位 —— 数据、来源标注、别名搜索、界面接入 */
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const web = path.join(root, 'docs');

let bad = 0;
const mark = s => { bad++; console.log('  ✗ ' + s); };
const ok = s => console.log('  ✓ ' + s);

const herbs = JSON.parse(fs.readFileSync(path.join(web, 'data', 'herbs.json'), 'utf8')).herbs;
const SRC = { T: '天津市中药饮片炮制规范', C: '道地药材产品认证目录', P: '药典' };

/* ---------------- 数据完整性 ---------------- */
console.log('\n【数据】');
let nA = 0, nG = 0, nQ = 0, badSrc = 0, noSrc = 0, dirty = 0;
for (const h of herbs) {
  if (h.a) { nA++; if (!SRC[h.as]) { badSrc++; if (badSrc < 4) mark('别名来源代号无效: ' + h.n + ' -> ' + h.as); } }
  if (h.g) { nG++; if (!SRC[h.gs]) { badSrc++; if (badSrc < 4) mark('产地来源代号无效: ' + h.n + ' -> ' + h.gs); } }
  if (h.q) { nQ++; if (!SRC[h.qs]) { badSrc++; if (badSrc < 4) mark('药用部位来源代号无效: ' + h.n + ' -> ' + h.qs); } }
  /* 字段里不该出现控制字符或超长的整句基原 */
  for (const [k, v] of [['a', h.a], ['g', h.g], ['q', h.q]]) {
    if (!v) continue;
    if (/[\x00-\x1f]/.test(v)) { dirty++; if (dirty < 4) mark(`${h.n} 的 ${k} 含控制字符`); }
    if (k === 'q' && v.length > 12) { dirty++; if (dirty < 4) mark(`${h.n} 的药用部位过长（疑似抓成整句）: ${v}`); }
  }
}
const pct = x => Math.round(100 * x / herbs.length) + '%';
console.log('题库 %d 味：别名 %d（%s）、产地分布 %d（%s）、药用部位 %d（%s）',
  herbs.length, nA, pct(nA), nG, pct(nG), nQ, pct(nQ));
if (!badSrc) ok('每一项都标了来源代号，且代号合法（T/C/P）');
if (!dirty) ok('字段干净：无控制字符、药用部位没有抓成整句');
if (nA < herbs.length * 0.5) mark('别名覆盖不足一半：' + nA);
else ok('别名覆盖 ' + pct(nA));
if (nQ < herbs.length * 0.5) mark('药用部位覆盖不足一半：' + nQ);
else ok('药用部位覆盖 ' + pct(nQ));
console.log('  产地分布覆盖 %s（其余留空，不编数据）', pct(nG));

/* 抽查几条，确认内容像话 */
const probe = { '大黄': '川军', '三七': '田七', '人参': '生晒参', '菊花': '杭菊', '麻黄': '草麻黄' };
let pbad = 0;
for (const [n, kw] of Object.entries(probe)) {
  const h = herbs.find(x => x.n === n);
  if (!h || !h.a || !h.a.includes(kw)) { pbad++; mark(`${n} 的别名里应含「${kw}」，实际：${h ? h.a : '(无)'}`); }
}
if (!pbad) ok('别名抽查通过（' + Object.keys(probe).join('、') + '）');

/* ---------------- 界面接入 ---------------- */
console.log('\n【界面】');
const appSrc = fs.readFileSync(path.join(web, 'app.js'), 'utf8');
const pairs = [
  ['详情页显示别名', /<dt>别名<\/dt>/.test(appSrc)],
  ['详情页显示药用部位', /<dt>药用部位<\/dt>/.test(appSrc)],
  ['详情页显示产地分布', /<dt>产地分布<\/dt>/.test(appSrc)],
  ['别名参与搜索', /h\.n \+ \(h\.a \|\| ''\)/.test(appSrc)],
  ['三项都带来源标注', /srcTag\(h\.as\)/.test(appSrc) && /srcTag\(h\.qs\)/.test(appSrc) && /srcTag\(h\.gs\)/.test(appSrc)],
  ['有资料来源图例', /src-legend/.test(appSrc)],
  ['搜索框提示含别名', fs.readFileSync(path.join(web, 'index.html'), 'utf8').includes('搜索药名 / 别名')],
  ['样式已加', /\.src-tag/.test(fs.readFileSync(path.join(web, 'style2.css'), 'utf8'))],
  ['桌面版解析了三个字段', ['Alias = Str', 'Area = Str', 'Part = Str']
    .every(s => fs.readFileSync(path.join(root, 'src', 'Core.cs'), 'utf8').includes(s))],
  ['桌面版详情页显示', /【别名】/.test(fs.readFileSync(path.join(root, 'src', 'HomeForm.cs'), 'utf8'))],
  ['桌面版搜索含别名', /h\.Name \+ h\.Alias/.test(fs.readFileSync(path.join(root, 'src', 'HomeForm.cs'), 'utf8'))]
];
let pbad2 = 0;
for (const [name, good] of pairs) { if (good) ok(name); else { pbad2++; mark('未接入: ' + name); } }

/* ---------------- 真跑一遍别名搜索 ---------------- */
console.log('\n【别名搜索（真实渲染）】');
const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }
};
function makeEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(), children: [], dataset: {}, style: {},
    value: '', checked: false, disabled: false, onclick: null, _html: '', _text: '',
    classList: { _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); }, contains(c) { return this._s.has(c); } },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    querySelector: () => null, querySelectorAll: () => [], appendChild() { },
    addEventListener() { }, click() { }, get firstElementChild() { return makeEl('div'); },
    closest: () => null, getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 })
  };
  return el;
}
const nodes = {};
global.document = {
  getElementById: id => nodes[id] || (nodes[id] = makeEl('div')),
  querySelector: sel => {
    if (typeof sel === 'string' && sel.startsWith('#')) {
      const id = sel.slice(1);
      return nodes[id] || (nodes[id] = makeEl('div'));
    }
    return makeEl('div');
  },
  querySelectorAll: () => [], addEventListener() { }, createElement: makeEl, body: { style: {} }
};
global.window = { scrollTo() { }, addEventListener() { } };
global.location = { protocol: 'http:', hash: '' };
global.history = { replaceState() { } };
global.fetch = () => Promise.reject(new Error('offline'));
global.setInterval = () => 0; global.clearInterval = () => { };
global.setTimeout = () => 0; global.clearTimeout = () => { };
global.alert = () => { }; global.confirm = () => true;

let bundle = '';
['encourage.js', 'timeherb.js', 'app.js'].forEach(f => {
  bundle += '\n/* ==== ' + f + ' ==== */\n' + fs.readFileSync(path.join(web, f), 'utf8');
});
bundle = bundle.replace(/\nboot\(\);\s*$/, '\n');
const m = { exports: {} };
new Function('module', 'exports', bundle + `
  module.exports = { APP, buildIndex, filteredHerbs, renderHerbList, showHerb };`)(m, m.exports);
const L = m.exports;
L.APP.herbs = herbs;
L.APP.categories = JSON.parse(fs.readFileSync(path.join(web, 'data', 'herbs.json'), 'utf8')).meta.categories;
L.APP.imgMap = JSON.parse(fs.readFileSync(path.join(web, 'data', 'images_manifest.json'), 'utf8'));
L.buildIndex();

const search = document.querySelector('#search');
const cases = [['田七', '三七'], ['川军', '大黄'], ['杭菊', '菊花'], ['生晒参', '人参'], ['龙沙', '麻黄']];
let sbad = 0;
for (const [kw, want] of cases) {
  search.value = kw;
  const got = L.filteredHerbs().map(h => h.n);
  if (!got.includes(want)) { sbad++; mark(`别名搜索「${kw}」没搜到 ${want}（命中 ${got.join('/') || '无'}）`); }
}
search.value = '';
if (!sbad) ok('别名搜索命中：' + cases.map(c => c[0] + '→' + c[1]).join('、'));

/* 详情页真的渲染出三项 */
const h = herbs.find(x => x.n === '大黄');
L.showHerb('大黄');
const html = nodes['detail'].innerHTML;
const hasAll = /别名/.test(html) && /药用部位/.test(html) && /产地分布/.test(html)
  && html.includes('川军') && /src-tag/.test(html) && /src-legend/.test(html);
if (hasAll) ok('详情页渲染出别名/药用部位/产地分布 + 来源标注 + 图例');
else mark('详情页渲染不完整');

console.log('');
if (bad) { console.log('V1.7 SELFTEST FAIL - %d 个问题', bad); process.exit(1); }
console.log('V1.7 SELFTEST PASS');
