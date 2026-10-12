/* v1.6.0 自测：题型模式 / 测一下子页 / 空状态 / 分类状态 / 遮住选项
   用法: node tools/v16test.js */
const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'docs');

let bad = 0;
const mark = s => { bad++; console.log('  ✗ ' + s); };
const ok = s => console.log('  ✓ ' + s);

/* ---------- 极简 DOM ---------- */
const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};
function makeEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(), children: [], dataset: {}, style: {},
    value: '', checked: false, disabled: false, onclick: null, _html: '', _text: '',
    classList: {
      _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); }, contains(c) { return this._s.has(c); }
    },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    querySelector: () => null, querySelectorAll: () => [], appendChild() { },
    addEventListener() { }, click() { }, get firstElementChild() { return makeEl('div'); },
    closest: () => null,
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 })
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
  querySelectorAll: () => [], addEventListener() { },
  createElement: makeEl, body: { style: {} }
};
global.window = { scrollTo() { }, addEventListener() { } };
global.location = { protocol: 'http:', hash: '' };
global.history = { replaceState() { } };
global.fetch = () => Promise.reject(new Error('offline'));
global.setInterval = () => 0; global.clearInterval = () => { };
global.setTimeout = () => 0; global.clearTimeout = () => { };
global.alert = () => { }; global.confirm = () => true;

const files = ['encourage.js', 'timeherb.js', 'app.js'];
let bundle = '';
files.forEach(f => { bundle += '\n/* ==== ' + f + ' ==== */\n' + fs.readFileSync(path.join(web, f), 'utf8'); });
bundle = bundle.replace(/\nboot\(\);\s*$/, '\n');
const m = { exports: {} };
new Function('module', 'exports', bundle + `
  module.exports = { APP, POINTS, QMODES, randomMixQty, totalScore, buildIndex,
    renderHerbList, filteredHerbs, switchTab, switchExamSub, getExamSub: () => EXAM_SUB,
    MISS_LIST_HTML, MISS_DETAIL_HTML, setSearch,
    G: { newGuessQuestion, renderGuess, guessStats, GUESS_KEY,
         current: () => GUESS, setMasked: v => { GUESS.masked = v; } } };`
)(m, m.exports);
const L = m.exports;

const herbs = JSON.parse(fs.readFileSync(path.join(web, 'data', 'herbs.json'), 'utf8'));
L.APP.herbs = herbs.herbs;
L.APP.categories = herbs.meta.categories;
L.APP.imgMap = JSON.parse(fs.readFileSync(path.join(web, 'data', 'images_manifest.json'), 'utf8'));
L.buildIndex();

const html = fs.readFileSync(path.join(web, 'index.html'), 'utf8');

/* ---------------- 4) 题型模式 + 分值 ---------------- */
console.log('\n【题型与分值】');
if (L.POINTS.single !== 4 || L.POINTS.fill !== 4 || L.POINTS.multi !== 5 || L.POINTS.judge !== 2)
  mark('分值不是 单选4/多选5/判断2/填空4：' + JSON.stringify(L.POINTS));
else ok('分值 = 单选 4 / 多选 5 / 判断 2 / 填空 4');

const want = { all1: [25, 0, 0, 0], all2: [0, 20, 0, 0], all3: [0, 0, 50, 0], all4: [0, 0, 0, 25] };
let qbad = 0;
for (const k of Object.keys(want)) {
  const q = L.QMODES[k].qty();
  const arr = [q.n1, q.n2, q.n3, q.n4];
  const sum = L.totalScore(Object.assign({}, q));
  if (arr.join() !== want[k].join() || sum !== 100) {
    qbad++; mark(`${L.QMODES[k].name} 题量 ${arr} 合计 ${sum}，应为 ${want[k]} / 100`);
  }
}
if (!qbad) ok('四个「全是X」模式题量正确且都正好 100 分（25 / 20 / 50 / 25 题）');

let mixBad = 0, kindHist = {};
for (let i = 0; i < 300; i++) {
  const q = L.randomMixQty();
  const sum = L.totalScore(Object.assign({}, q));
  const kinds = [q.n1, q.n2, q.n3, q.n4].filter(x => x > 0).length;
  kindHist[kinds] = (kindHist[kinds] || 0) + 1;
  if (sum !== 100 || kinds < 3) {
    mixBad++;
    if (mixBad < 4) mark(`随机题型不合规：${JSON.stringify(q)} 合计 ${sum}，题型数 ${kinds}`);
  }
}
if (!mixBad) ok('随机题型 300 次抽样：全部 100 分且至少混搭 3 种题型（' +
  Object.keys(kindHist).sort().map(k => k + '种×' + kindHist[k]).join('、') + '）');

if (!html.includes('id="qmodeRow"')) mark('index.html 缺少题型模式按钮行 #qmodeRow');
else if (!/全是单选[\s\S]*全是多选[\s\S]*全是判断[\s\S]*全是填空[\s\S]*随机题型/.test(html))
  mark('题型模式按钮不全');
else ok('index.html 五个模式按钮齐全');
if (!/id="n1"[^>]*value="10"/.test(html) || !/id="n4"[^>]*value="5"/.test(html))
  mark('默认题量没有改成 10/4/10/5（应正好 100 分）');
else ok('默认题量 10/4/10/5 = 100 分');

/* ---------------- 5) 测一下：子页 ---------------- */
console.log('\n【测一下页面】');
const tabNames = (html.match(/class="tab[^"]*" data-tab="([a-z]+)"/g) || [])
  .map(s => s.match(/data-tab="([a-z]+)"/)[1]);
if (tabNames.join() !== 'browse,random,exam,guess') mark('顶栏标签应为 速查/随机/测一下/看图猜药，实际 ' + tabNames);
else ok('顶栏只剩 4 个标签：中药速查 / 随机中药 / 测一下 / 看图猜药');
if (!/data-tab="exam">测一下</.test(html)) mark('「开始测试」没有改名成「测一下」');
else ok('页面名已改为「测一下」');
if (!html.includes('examSubTabs') || !html.includes('id="sub-wrong"') || !html.includes('id="sub-scores"'))
  mark('测一下里没有错题本/成绩记录子页');
else if (!/id="page-wrong"|id="page-scores"/.test(html)) ok('错题本与成绩记录已并入「测一下」的子页');
else mark('旧的 page-wrong / page-scores 还在，没并进去');

L.switchTab('wrong');
if (L.getExamSub() !== 'wrong') mark('switchTab("wrong") 没有切到错题本子页');
else ok('旧链接 #wrong 仍可用（自动进「测一下 → 错题本」）');
L.switchTab('scores');
if (L.getExamSub() !== 'scores') mark('switchTab("scores") 没有切到成绩记录子页');
else ok('旧链接 #scores 仍可用（自动进「测一下 → 成绩记录」）');
L.switchExamSub('setup');

/* ---------------- 2/3) 空状态 ---------------- */
console.log('\n【搜不到药材时】');
if (!L.MISS_LIST_HTML.includes('看不懂~，TAT呜呜呜~')) mark('列表区文案不是「看不懂~，TAT呜呜呜~」');
else ok('分类筛选/列表区显示「看不懂~，TAT呜呜呜~」');
if (L.MISS_LIST_HTML.includes('wangji330330')) mark('列表区不该出现邮箱');
else ok('列表区不再显示邮箱那一大段');
if (!L.MISS_DETAIL_HTML.includes('wangji330330@gmail.com')) mark('详情区没有邮箱');
else ok('详情区保留「暂时没有该药材哦~OVO」+ 邮箱');

/* 真跑一遍：先搜到药（有图），再搜一个搜不到的词，图片必须清空 */
const searchEl = document.querySelector('#search');
searchEl.value = '麻黄';
L.renderHerbList();
const hadImgs = nodes['imgBox'].innerHTML.includes('<img');
searchEl.value = 'zzz不存在的药zzz';
L.renderHerbList();
const nowImgs = nodes['imgBox'].innerHTML.includes('<img');
if (!hadImgs) mark('前置条件不成立：搜「麻黄」时图片区是空的');
else if (nowImgs) mark('搜不到时图片区还留着上一次的图片');
else ok('搜不到时右侧图片彻底清空（不再残留上一味的图）');
if (nodes['hidBox'].innerHTML !== '') mark('搜不到时「已隐藏图片」面板没清空');
else ok('「已隐藏图片」面板也一并清空');
searchEl.value = '';

/* ---------------- 1) 分类状态 ---------------- */
console.log('\n【分类选中状态】');
const catSrc = fs.readFileSync(path.join(web, 'timeherb.js'), 'utf8');
if (/catChips \.chip'\)\.forEach/.test(catSrc) && !/renderCategoryChips\(\)/.test(catSrc))
  mark('timeherb.js 的 gotoHerb 还在手动切 active，没走 renderCategoryChips');
else if (!/renderCategoryChips\(\)/.test(catSrc)) mark('gotoHerb 没有重渲染分类');
else ok('「推荐参考」跳转改为重渲染分类（browseCat/browseGroup 都清空）');
const appSrc = fs.readFileSync(path.join(web, 'app.js'), 'utf8');
if (!/goBrowse'\)\.onclick[\s\S]{0,220}browseGroup = ''/.test(appSrc))
  mark('错题本「在速查中查看」没有清 browseGroup');
else ok('错题本「在速查中查看」也清掉了 browseGroup');

/* ---------------- 6) 遮住选项 ---------------- */
console.log('\n【看图猜药：遮住选项】');
const enc = fs.readFileSync(path.join(web, 'encourage.js'), 'utf8');
if (/先遮住图片|显示图片|🙈/.test(enc)) mark('encourage.js 里还有「先遮住图片」或🙈');
else ok('按钮文案已改为「遮住选项 / 显示选项」，🙈 已去掉');

/* 跑一遍真渲染：遮住时选项应显示 ？？？ 且不泄漏答案 */
let leak = 0;
for (let i = 0; i < 20; i++) {
  L.G.newGuessQuestion();
  L.G.setMasked(true);
  L.G.renderGuess();
  const h = nodes['guessBox'].innerHTML;
  const g = L.G.current();
  if (!h.includes('veiled')) { leak++; mark('遮住时选项没有 veiled 样式'); break; }
  if (h.includes('>' + g.answer + '<')) { leak++; mark('遮住时答案仍出现在选项里：' + g.answer); break; }
  if (!h.includes('g-veilnote')) { leak++; mark('遮住时没有提示文字'); break; }
  if (!h.includes('<img')) { leak++; mark('遮住选项时图片不该被遮住'); break; }
}
if (!leak) ok('遮住状态：选项显示 ？？？、图片仍可见、答案不泄漏（20 次抽样）');
L.G.setMasked(false);
L.G.renderGuess();
if (nodes['guessBox'].innerHTML.includes('veiled')) mark('关掉遮住后选项仍被遮');
else ok('关掉遮住后选项正常显示');

console.log('');
if (bad) { console.log('V1.6 SELFTEST FAIL - %d 个问题', bad); process.exit(1); }
console.log('V1.6 SELFTEST PASS');
