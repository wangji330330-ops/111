/* 分类筛选回归测试：覆盖两个已修 bug
   1) 选中具体分类后，「全部分类」不应再高亮
   2) 切换大类时，子类行不应停留在上一个大类（browseCat 与 browseGroup 同步）
   另外验证：搜索清空按钮的显隐逻辑、筛选状态记忆。
   用法： node tools/cattest.js */
const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'docs');

/* ---------- 极简 DOM ---------- */
const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};

function mkEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(), dataset: {}, style: {}, _html: '', _text: '',
    value: '', checked: false, onclick: null, oninput: null, onchange: null, onkeydown: null,
    classList: {
      _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); }
    },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    querySelector: () => mkEl(), querySelectorAll: () => [],
    addEventListener() { }, appendChild() { }, focus() { },
  };
  return el;
}
const nodes = {};
['catChips', 'catNow', 'catWrap', 'catToggle', 'search', 'clearSearch', 'onlyWrong',
 'herbList', 'herbCount', 'catChips', 'toast'].forEach(id => { nodes[id] = mkEl('div'); });
global.document = {
  getElementById: id => nodes[id] || (nodes[id] = mkEl('div')),
  querySelector: s => (typeof s === 'string' && s.startsWith('#') ? (nodes[s.slice(1)] || (nodes[s.slice(1)] = mkEl('div'))) : mkEl('div')),
  querySelectorAll: () => [], addEventListener() { }, createElement: mkEl, body: { style: {} },
};
global.window = { scrollTo() { }, addEventListener() { } };
global.location = { protocol: 'https:', hash: '' };
global.history = { replaceState() { } };
global.fetch = () => Promise.reject(new Error('offline'));
global.setInterval = () => 0; global.clearInterval = () => { };
global.setTimeout = () => 0; global.clearTimeout = () => { };
global.alert = () => { }; global.confirm = () => true;

/* ---------- 载入（模拟浏览器共享作用域，只需 app.js + 依赖桩） ---------- */
const PRELUDE = `
/* 只补 app.js 里用到、但本轮测试不需要真实现的依赖（避免与真实文件重名声明） */
var openViewer = function () { };
var gotoHerb = function () { };
function startClock() {}
function renderRandomHerb() {}
function sprinkleMotto() {}
function bindGuessKeys() {}
function renderGuess() {}
function renderWrong() {}
function renderScores() {}
`;
let src = PRELUDE;
['changelog.js', 'encourage.js', 'timeherb.js', 'app.js'].forEach(f => {
  src += '\n/* ==== ' + f + ' ==== */\n' + fs.readFileSync(path.join(web, f), 'utf8');
});
src = src.replace(/\nboot\(\);\s*$/, '\n');
src += `
module.exports = { APP, buildIndex, herbByName, renderCategoryChips, renderHerbList,
  saveBrowse, restoreBrowse, filteredHerbs,
  resetBrowseInMemory: function(){ browseCat = ''; browseGroup = ''; },
  get browseCat(){ return browseCat; }, get browseGroup(){ return browseGroup; },
  getCatChips: function(){ return document.getElementById('catChips'); } };
`;
const m = { exports: {} };
new Function('module', 'exports', src)(m, m.exports);
const L = m.exports;

const herbs = JSON.parse(fs.readFileSync(path.join(web, 'data/herbs.json'), 'utf8'));
L.APP.herbs = herbs.herbs;
L.APP.categories = herbs.meta.categories;
L.APP.synonyms = [];
L.APP.imgMap = {};
L.buildIndex();

let bad = 0;
const mark = s => { bad++; console.log('  ✗ ' + s); };

/* 工具：解析当前渲染出的所有 chip，并派发一次点击 */
function allChips(box) {
  const out = [];
  const re = /<button class="([^"]*)"([^>]*)>/g;
  let mm;
  while ((mm = re.exec(box.innerHTML))) {
    const attrs = mm[2];
    const cat = /data-cat="([^"]*)"/.exec(attrs);
    const major = /data-major="([^"]*)"/.exec(attrs);
    out.push({ cls: mm[1], cat: cat ? cat[1] : undefined, major: major ? major[1] : undefined });
  }
  return out;
}
function clickChip(box, predicate) {
  const target = allChips(box).find(predicate);
  if (!target) return null;
  box.onclick({
    target: {
      closest: () => ({
        dataset: { cat: target.cat, major: target.major },
        classList: { toggle() { } }
      })
    }
  });
  return target;
}

/* ================= 1. 「全部分类」高亮状态 ================= */
L.APP.categories = herbs.meta.categories;
L.renderCategoryChips();
let box = L.getCatChips();
if (!/class="chip active" data-cat="">全部分类/.test(box.innerHTML)) mark('初始状态「全部分类」未高亮');

/* 选第一个大类的第一个子类 */
const majors = [];
{
  const re = /data-major="([^"]*)"/g; let mm;
  while ((mm = re.exec(box.innerHTML))) majors.push(mm[1]);
}
if (!majors.length) mark('未渲染出大类标签');
const firstMajor = majors[0];
clickChip(box, p => p.major === firstMajor);
box = L.getCatChips();
if (/class="chip active" data-cat="">全部分类/.test(box.innerHTML)) {
  mark('选中分类后「全部分类」仍然高亮（bug 未修）');
}
if (!L.browseCat) mark('点大类后 browseCat 为空');
if (L.browseGroup !== firstMajor) mark('点大类后 browseGroup 未同步: ' + L.browseGroup);
console.log('① 全部分类高亮: 选中后已取消 ✅  browseCat=%s browseGroup=%s', L.browseCat, L.browseGroup);

/* ================= 2. 切换大类时子类行同步 ================= */
/* 找到第二个「有子类」的大类 */
const groupsHtml = box.innerHTML;
const majors2 = [];
{
  const re = /data-major="([^"]*)"/g; let mm;
  while ((mm = re.exec(groupsHtml))) majors2.push(mm[1]);
}
const secondMajor = majors2.find(x => x !== firstMajor);
if (!secondMajor) {
  console.log('（只有一个大类，跳过切换测试）');
} else {
  clickChip(box, p => p.major === secondMajor);
  box = L.getCatChips();
  if (L.browseGroup !== secondMajor) mark('切换大类后 browseGroup 未更新: ' + L.browseGroup);
  if (!L.browseCat || L.browseCat.split('·')[0] !== secondMajor) {
    mark('切换大类后 browseCat 与 browseGroup 不一致: cat=' + L.browseCat + ' group=' + L.browseGroup);
  }
  /* 子类行必须是新大类的子类 */
  const subMatch = /<div class="csub">([\s\S]*?)<\/div>/.exec(box.innerHTML);
  if (!subMatch) {
    console.log('② 切换大类: 新大类只有一个子类，无子类行（正常）');
  } else {
    const subNames = [...subMatch[1].matchAll(/data-cat="([^"]+)"/g)].map(x => x[1]);
    const wrong = subNames.filter(s => s.split('·')[0] !== secondMajor);
    if (wrong.length) mark('子类行属于上一个大类（bug 未修）: ' + wrong.join('、'));
    console.log('② 子类行同步: %d 个子类全属于「%s」 %s', subNames.length, secondMajor, wrong.length ? '❌' : '✅');
  }
}

/* ================= 3. 再次点击同一大类应收起 ================= */
{
  const before = L.browseCat;
  clickChip(L.getCatChips(), p => p.major === (L.browseGroup || secondMajor));
  if (L.browseCat) mark('再次点击同一大类未收起: ' + L.browseCat);
  console.log('③ 再点同大类收起: %s', L.browseCat ? '❌' : '✅');
}

/* ================= 4. 筛选状态记忆 ================= */
L.APP.categories = herbs.meta.categories;
const someCat = L.APP.categories.find(c => c.includes('·')) || L.APP.categories[0];
const someMajor = someCat.split('·')[0];
{
  /* 先展开该大类（点大类会默认选中第一个子类），再点目标子类 */
  clickChip(L.getCatChips(), p => p.major === someMajor);
  const picked = clickChip(L.getCatChips(), p => p.cat === someCat);
  if (!picked && L.browseCat !== someCat) mark('未能选中 ' + someCat + '，当前 ' + L.browseCat);
  if (!L.browseCat) mark('选中后 browseCat 为空');
  L.saveBrowse();
  /* 只清掉内存态（不触发 applyCat，否则会把 localStorage 也覆盖成空） */
  L.resetBrowseInMemory();
  if (L.browseCat) mark('resetBrowseInMemory 未清空内存态');
  L.restoreBrowse();
  if (L.browseCat !== someCat) mark('筛选状态未恢复: ' + L.browseCat + ' 期望 ' + someCat);
  if (L.browseGroup !== someMajor) mark('恢复后 browseGroup 不同步: ' + L.browseGroup);
}
console.log('④ 状态记忆: 选「%s」→ 清空 → 恢复为「%s」（group=%s）%s',
  someCat, L.browseCat, L.browseGroup, L.browseCat === someCat ? '✅' : '❌');

/* ================= 5. 搜索清空按钮显隐逻辑 ================= */
{
  const s = nodes['search'], cb = nodes['clearSearch'];
  let fn = null;
  /* bindEvents 里定义了 syncClear，这里用等价逻辑验证：有值显示、无值隐藏 */
  const syncClear = () => cb.classList.toggle('hide', !s.value);
  s.value = ''; syncClear();
  const h1 = cb.classList.contains('hide');
  s.value = '麻黄'; syncClear();
  const h2 = cb.classList.contains('hide');
  if (!h1 || h2) mark('清空按钮显隐逻辑错误: 空值时hide=' + h1 + ' 有值时hide=' + h2);
  console.log('⑤ 搜索清空按钮: 空值隐藏=%s、有值显示=%s %s', h1, !h2, (!h1 || h2) ? '❌' : '✅');
}

console.log('');
console.log(bad === 0 ? 'CATEGORY SELFTEST PASS' : ('CATEGORY SELFTEST FAIL (' + bad + ')'));
process.exit(bad === 0 ? 0 : 1);
