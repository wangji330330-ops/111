/* 看图猜药 + 图片隐藏/恢复 功能自测
   用法： node tools/featuretest.js   （在项目根目录执行）

   说明：本测试把 docs/ 下三个脚本按 index.html 的顺序拼在一个作用域里执行，
   尽量还原浏览器的共享作用域语义（后加载的脚本能看见先加载的声明）。 */
const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'docs');

/* ================= 极简 DOM / 存储桩 ================= */
const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};

function makeEl(tag) {
  return {
    tagName: (tag || 'div').toUpperCase(), children: [], dataset: {}, style: {},
    _html: '', _text: '', disabled: false, onclick: null,
    classList: {
      _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); }
    },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    querySelector: () => null, querySelectorAll: () => [],
    appendChild(c) { this.children.push(c); }, addEventListener() { },
  };
}

const nodes = {};
['guessBox', 'mottoLine', 'footMotto', 'imgBox', 'hidBox', 'toast',
 'viewerImg', 'viewerCap', 'viewerPrev', 'viewerNext', 'viewerHide', 'viewerRestore',
 'loading', 'subLine', 'verLabel'].forEach(id => { nodes[id] = makeEl('div'); });

global.document = {
  getElementById: id => nodes[id] || (nodes[id] = makeEl('div')),
  querySelector: sel => {
    /* 支持 '#id' 与标签/类选择器：本测试只关心按 id 取节点 */
    if (typeof sel === 'string' && sel.startsWith('#')) {
      const id = sel.slice(1);
      return nodes[id] || (nodes[id] = makeEl('div'));
    }
    return makeEl('div');
  },
  querySelectorAll: () => [],
  addEventListener: () => { },
  createElement: makeEl,
  body: { style: {} },
};
global.window = { scrollTo() { }, addEventListener() { } };
global.location = { protocol: 'https:', hash: '' };
global.history = { replaceState() { } };
global.fetch = () => Promise.reject(new Error('offline'));
global.setInterval = () => 0; global.clearInterval = () => { };
global.setTimeout = () => 0; global.clearTimeout = () => { };
global.alert = () => { }; global.confirm = () => true;

/* ================= 数据（在 APP 之前准备好） ================= */
const dataDir = path.join(web, 'data');
const herbsJson = JSON.parse(fs.readFileSync(path.join(dataDir, 'herbs.json'), 'utf8'));
const imgmapJson = JSON.parse(fs.readFileSync(path.join(dataDir, 'images_manifest.json'), 'utf8'));

/* ================= 按 index.html 顺序拼装脚本 =================
   index.html 的顺序是：encourage.js → timeherb.js → app.js
   encourage.js 需要 app.js 里的 LS/toast/esc/herbByName/APP，浏览器里靠 hoisting 解决，
   这里在拼接前先补上最小同名实现（app.js 中的 function 声明会覆盖它们）。 */
/* ================= 按 index.html 顺序拼装脚本 =================
   index.html 顺序：encourage.js → timeherb.js → app.js
   三个脚本在浏览器里共享同一个全局作用域，后加载的脚本处于 TDZ，
   但由于所有调用都发生在函数体内（加载时不执行），实际运行没问题。
   这里把三者拼进同一个作用域。
   注意：app.js 用 const 声明了 APP / LS / $ / $$ / esc / herbByName / toast，
   它们会声明整个作用域，因此本桩只补 app.js 中完全不存在、且加载期不会冲突的名字。 */
const PRELUDE = `
/* 加载期不需要任何额外桩：app.js 用 const 声明了 APP/LS/$/$$/esc/herbByName/toast，
   它们在整个作用域内声明，测试代码在全部加载完成后才调用，故不存在 TDZ 问题。 */
`;

const files = ['encourage.js', 'timeherb.js', 'app.js'];
let bundle = PRELUDE;
files.forEach(f => { bundle += '\n/* ==== ' + f + ' ==== */\n' + fs.readFileSync(path.join(web, f), 'utf8'); });

/* 去掉 app.js 末尾的 boot() 自动执行，改为手动初始化 */
bundle = bundle.replace(/\nboot\(\);\s*$/, '\n');

const EXPORTS = `
  module.exports = {
    APP: APP,
    buildIndex: buildIndex,
    herbByName: herbByName,
    renderImages: renderImages,
    renderHiddenBox: renderHiddenBox,
    hideViewerImage: hideViewerImage,
    restoreViewerImage: restoreViewerImage,
    openViewer: openViewer,
    viewerState: function () { return viewerState; },
    guessGame: {
      PRAISE: PRAISE, ENCOURAGE: ENCOURAGE, MOTTO: MOTTO,
      mottoText: mottoText, praiseText: praiseText, encourageText: encourageText,
      newGuessQuestion: newGuessQuestion, renderGuess: renderGuess,
      guessStats: guessStats, GUESS_KEY: GUESS_KEY,
      current: function () { return GUESS; }
    }
  };
`;

const m = { exports: {} };
new Function('module', 'exports', bundle + '\n' + EXPORTS)(m, m.exports);
const L = m.exports;

/* 注入真实数据 */
L.APP.herbs = herbsJson.herbs;
L.APP.categories = herbsJson.meta.categories;
L.APP.synonyms = herbsJson.meta.synonyms || [];
L.APP.imgMap = imgmapJson;
L.buildIndex();

const G = L.guessGame;
console.log('（已按 encourage.js → timeherb.js → app.js 顺序加载）');
console.log('题库: %d 味，有图: %d 味', L.APP.herbs.length, Object.keys(L.APP.imgMap).length);

let problems = 0;
const bad = [];
const mark = msg => { problems++; if (bad.length < 8) bad.push(msg); };

/* ================= 1. 看图猜药出题自洽 ================= */
let okCount = 0, sameCat = 0;
for (let i = 0; i < 300; i++) {
  G.newGuessQuestion();
  const g = G.current();
  if (!g) { mark('未生成题目'); break; }
  if (g.options.length !== 4) mark('选项数不是4: ' + g.options.length);
  if (new Set(g.options).size !== 4) mark('选项有重复');
  if (!g.options.includes(g.answer)) mark('正确答案不在选项中');
  if (!g.file) mark('题目没有图片');
  if (!(L.APP.imgMap[g.answer] || []).includes(g.file)) mark('图片与答案药味不匹配: ' + g.answer);
  g.options.forEach(o => { if (!L.herbByName(o)) mark('干扰项不是题库药材: ' + o); });
  const cats = new Set(g.options.map(o => ((L.herbByName(o) || {}).c || '').split('·')[0]));
  if (cats.size === 1) sameCat++;
  okCount++;
}
console.log('出题自洽: %d 题通过（其中 %d 题为同分类干扰项，更难）', okCount, sameCat);

/* ================= 2. 答对/答错都要显示答案 ================= */
function answerOne(pickRight) {
  G.newGuessQuestion();
  const g = G.current();
  const box = nodes['guessBox'];
  box.innerHTML = '';
  G.renderGuess();               // 未作答状态
  const picked = pickRight ? g.answer : g.options.find(o => o !== g.answer);
  g.picked = picked;
  const st = G.guessStats();
  st.total++;
  if (pickRight) { st.right++; st.streak++; st.best = Math.max(st.best, st.streak); }
  else st.streak = 0;
  localStorage.setItem('tcm_' + G.GUESS_KEY, JSON.stringify(st));
  G.renderGuess();               // 已作答状态（应显示答案）
  return { html: box.innerHTML, answer: g.answer, picked, pickRight };
}

const rRight = answerOne(true);
const rWrong = answerOne(false);
if (!rRight.html.includes('答对了')) mark('答对后未显示“答对了”');
if (!rWrong.html.includes('答错了')) mark('答错后未显示“答错了”');
if (!rRight.html.includes('正确答案')) mark('答对后未显示“正确答案”栏');
if (!rWrong.html.includes('正确答案')) mark('答错后未显示“正确答案”栏');
if (!rRight.html.includes(rRight.answer)) mark('答对后未显示答案药名');
if (!rWrong.html.includes(rWrong.answer)) mark('答错后未显示答案药名');
if (!rRight.html.includes('g-opt right')) mark('答对后未高亮正确项');
if (!rWrong.html.includes('g-opt wrong')) mark('答错后未标出错误项');
if (!rWrong.html.includes('g-opt right')) mark('答错后未同时标出正确项');
console.log('答对显示答案: %s ｜ 答错显示答案: %s ｜ 答错同时标出正确项: %s',
  rRight.html.includes(rRight.answer), rWrong.html.includes(rWrong.answer),
  rWrong.html.includes('g-opt right'));

/* 鼓励语/勉励语是否真的渲染出来 */
const praiseHit = G.PRAISE.some(p => rRight.html.includes(p));
const encourageHit = G.ENCOURAGE.some(p => rWrong.html.includes(p));
if (!praiseHit) mark('答对后未出现鼓励语');
if (!encourageHit) mark('答错后未出现勉励语');
console.log('鼓励语渲染: %s ｜ 勉励语渲染: %s', praiseHit, encourageHit);

/* ================= 3. 语料与随机性 ================= */
if (G.PRAISE.length < 8) mark('鼓励语偏少');
if (G.ENCOURAGE.length < 8) mark('勉励语偏少');
if (G.MOTTO.length < 8) mark('名言偏少');
const seen = new Set();
for (let i = 0; i < 80; i++) seen.add(G.mottoText());
if (seen.size < 6) mark('名言随机性不足: ' + seen.size);
console.log('语料: 鼓励 %d / 勉励 %d / 名言 %d（随机命中 %d 种）',
  G.PRAISE.length, G.ENCOURAGE.length, G.MOTTO.length, seen.size);

/* ================= 4. 图片隐藏 / 恢复 ================= */
const name = L.APP.herbs[0].n;
const files0 = L.APP.imgMap[name];
console.log('测试药味: %s，图片 %d 张', name, files0.length);

const setHidden = arr => localStorage.setItem('tcm_hidden', JSON.stringify(arr));

setHidden([]);
L.renderImages(name);
if (!nodes['imgBox'].innerHTML.includes('figure')) mark('初始未渲染图片');
if (nodes['hidBox'].innerHTML.includes('已隐藏')) mark('未隐藏时不该出现“已隐藏”面板');

/* 隐藏第一张 */
setHidden([name + '|' + files0[0]]);
L.renderImages(name);
const afterHide = nodes['imgBox'].innerHTML;
const hidPanel = nodes['hidBox'].innerHTML;
if (files0.length > 1 && afterHide.includes(encodeURIComponent(files0[0]))) mark('隐藏后仍显示该图');
if (!hidPanel.includes('已隐藏')) mark('未显示“已隐藏”面板');
if (!hidPanel.includes('hid-restore')) mark('未提供恢复按钮');
console.log('隐藏 1 张 → 面板含“已隐藏”: %s，含恢复按钮: %s',
  hidPanel.includes('已隐藏'), hidPanel.includes('hid-restore'));

/* 恢复 */
setHidden([]);
L.renderImages(name);
if (!nodes['imgBox'].innerHTML.includes(encodeURIComponent(files0[0]))) mark('恢复后未重新显示该图');
if (nodes['hidBox'].innerHTML.includes('已隐藏')) mark('恢复后面板未清空');
console.log('恢复 → 图片回来了: %s，面板已清空: %s',
  nodes['imgBox'].innerHTML.includes(encodeURIComponent(files0[0])),
  !nodes['hidBox'].innerHTML.includes('已隐藏'));

/* 全部隐藏的兜底提示 */
setHidden(files0.map(f => name + '|' + f));
L.renderImages(name);
if (!nodes['imgBox'].innerHTML.includes('都被隐藏')) mark('全部隐藏时未给提示');
console.log('全部隐藏 → 兜底提示: %s', nodes['imgBox'].innerHTML.includes('都被隐藏'));
setHidden([]);

/* ================= 5. 查看器按钮：隐藏 / 恢复（真实路径） ================= */
setHidden([]);
L.renderImages(name);
L.openViewer(name, files0[0]);
let vs = L.viewerState();
if (!vs) mark('openViewer 未建立查看器状态');
else {
  if (vs.name !== name) mark('查看器药味错误');
  if (!vs.files.includes(files0[0])) mark('查看器未包含该图');
  /* 点“隐藏这张图” */
  L.hideViewerImage();
  const hidAfter = JSON.parse(localStorage.getItem('tcm_hidden') || '[]');
  if (!hidAfter.includes(name + '|' + files0[0])) mark('查看器隐藏后未写入 hidden');
  if (nodes['imgBox'].innerHTML.includes(encodeURIComponent(files0[0]))) mark('查看器隐藏后详情区仍显示该图');
  console.log('查看器隐藏 → hidden 已写入: %s', hidAfter.includes(name + '|' + files0[0]));

  /* 再点“恢复这张图” */
  L.restoreViewerImage();
  const hidAfter2 = JSON.parse(localStorage.getItem('tcm_hidden') || '[]');
  if (hidAfter2.includes(name + '|' + files0[0])) mark('查看器恢复后 hidden 未清除');
  if (!nodes['imgBox'].innerHTML.includes(encodeURIComponent(files0[0]))) mark('查看器恢复后详情区未重新显示');
  console.log('查看器恢复 → hidden 已清除: %s，详情区已恢复: %s',
    !hidAfter2.includes(name + '|' + files0[0]),
    nodes['imgBox'].innerHTML.includes(encodeURIComponent(files0[0])));
}
setHidden([]);

/* ================= 6. 隐藏的图不再出现在猜药里 ================= */
setHidden(files0.map(f => name + '|' + f));
let appeared = 0;
for (let i = 0; i < 200; i++) {
  G.newGuessQuestion();
  const g = G.current();
  if (g && g.answer === name) appeared++;
}
if (files0.length && appeared > 0) mark('已全部隐藏图片的药味仍被抽中出题: ' + appeared + ' 次');
console.log('全部隐藏图片的药味，200 次出题中被抽中: %d 次（应为 0）', appeared);
setHidden([]);

/* ================= 结果 ================= */
console.log('');
console.log('问题数: %d', problems);
if (bad.length) console.log('问题样例:', bad);
console.log(problems === 0 ? 'FEATURE SELFTEST PASS' : 'FEATURE SELFTEST FAIL');
process.exit(problems === 0 ? 0 : 1);
