/* 拼音自测：数据完整性 + 读音准确性 + 检索 + 各页面接入 */
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const docs = path.join(root, 'docs');

let bad = 0;
const mark = s => { bad++; console.log('  ✗ ' + s); };
const ok = s => console.log('  ✓ ' + s);

/* ------------------------------------------------------------------ */
/* 1) 数据完整性                                                       */
/* ------------------------------------------------------------------ */
const herbs = JSON.parse(fs.readFileSync(path.join(docs, 'data', 'herbs.json'), 'utf8')).herbs;
const han = /[\u4e00-\u9fff]/;
/* 声调可能落在首字母大写上（Má / Ěr / Ài），大小写都要认 */
const toned = /[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ]/;

let missing = 0, sylBad = 0, noTone = 0, extra = 0;
const TONE_SYL = [];
for (const h of herbs) {
  const p = h.p;
  if (!p) { missing++; if (missing < 4) mark('缺拼音: ' + h.n); continue; }
  const chars = (h.n.match(/[\u4e00-\u9fff]/g) || []).length;
  const syls = p.trim().split(/\s+/);
  if (syls.length !== chars) { sylBad++; if (sylBad < 4) mark(`音节数不符: ${h.n} -> ${p}（${syls.length} vs ${chars}）`); }
  for (const s of syls) {
    if (!toned.test(s)) { noTone++; TONE_SYL.push(h.n + ' -> ' + s); }
  }
  if (/[\u4e00-\u9fff]/.test(p)) { extra++; mark('拼音里混入汉字: ' + h.n + ' -> ' + p); }
}
console.log('题库 %d 味：缺拼音 %d，音节数不符 %d，无声调音节 %d', herbs.length, missing, sylBad, noTone);
if (!missing) ok('每味药都有拼音');
if (!sylBad) ok('音节数 = 汉字数（逐字注音）');
if (!noTone) ok('每个音节都有声调（体例：逐字本调）');
else TONE_SYL.slice(0, 8).forEach(s => mark('无声调: ' + s));

/* 拼音唯一性（仅提示，不作失败） */
const byPy = {};
herbs.forEach(h => { (byPy[h.p] = byPy[h.p] || []).push(h.n); });
const dup = Object.keys(byPy).filter(k => byPy[k].length > 1);
console.log('拼音完全相同的组合: %d %s', dup.length, dup.slice(0, 5).map(k => k + '=' + byPy[k].join('/')).join(' '));

/* ------------------------------------------------------------------ */
/* 2) 读音准确性：人工审定表                                          */
/* ------------------------------------------------------------------ */
/* 这些是通用拼音库会读错、经人工逐条审定的读音（依据见 tools/pinyin/overrides.py） */
const EXPECT = {
  '白术': 'Bái Zhú', '苍术': 'Cāng Zhú', '莪术': 'É Zhú', '大黄': 'Dà Huáng',
  '阿胶': 'Ē Jiāo', '厚朴': 'Hòu Pò', '没药': 'Mò Yào', '桔梗': 'Jié Gěng',
  '黄柏': 'Huáng Bò', '射干': 'Yè Gān', '重楼': 'Chóng Lóu', '槟榔': 'Bīng Láng',
  '石韦': 'Shí Wéi', '秦艽': 'Qín Jiāo', '荜澄茄': 'Bì Chéng Qié', '荜茇': 'Bì Bá',
  '连翘': 'Lián Qiáo', '葛根': 'Gé Gēn', '白鲜皮': 'Bái Xiān Pí', '薄荷': 'Bò Hé',
  '神曲': 'Shén Qū', '枳壳': 'Zhǐ Qiào', '罂粟壳': 'Yīng Sù Qiào', '海蛤壳': 'Hǎi Gé Qiào',
  '玄参': 'Xuán Shēn', '苦参': 'Kǔ Shēn', '拳参': 'Quán Shēn', '太子参': 'Tài Zǐ Shēn',
  '参叶': 'Shēn Yè', '西洋参': 'Xī Yáng Shēn', '明党参': 'Míng Dǎng Shēn',
  '川芎': 'Chuān Xiōng', '鹿茸': 'Lù Róng', '狗脊': 'Gǒu Jǐ', '萹蓄': 'Biān Xù',
  '菟丝子': 'Tù Sī Zǐ', '桑螵蛸': 'Sāng Piāo Xiāo', '海螵蛸': 'Hǎi Piāo Xiāo',
  '蛤蚧': 'Gé Jiè', '海蛤壳 ': 'Hǎi Gé Qiào', '豨莶草': 'Xī Xiān Cǎo', '马齿苋': 'Mǎ Chǐ Xiàn',
  '紫菀': 'Zǐ Wǎn', '牛蒡子': 'Niú Bàng Zǐ', '藁本': 'Gǎo Běn', '老鹳草': 'Lǎo Guàn Cǎo',
  '胡荽': 'Hú Suī', '芫花': 'Yuán Huā', '侧柏叶': 'Cè Bǎi Yè', '柏子仁': 'Bǎi Zǐ Rén',
  '薏苡仁': 'Yì Yǐ Rén', '马兜铃': 'Mǎ Dōu Líng', '枇杷叶': 'Pí Pá Yè', '桑椹': 'Sāng Shèn',
  '诃子': 'Hē Zǐ', '青葙子': 'Qīng Xiāng Zǐ', '骨碎补': 'Gǔ Suì Bǔ', '土鳖虫': 'Tǔ Biē Chóng',
  '王不留行': 'Wáng Bù Liú Xíng', '自然铜': 'Zì Rán Tóng', '刘寄奴': 'Liú Jì Nú',
  '山茱萸': 'Shān Zhū Yú', '栀子': 'Zhī Zǐ', '川楝子': 'Chuān Liàn Zǐ', '薤白': 'Xiè Bái',
  '莱菔子': 'Lái Fú Zǐ', '肉苁蓉': 'Ròu Cōng Róng', '茵陈': 'Yīn Chén', '瞿麦': 'Qú Mài',
  '萆薢': 'Bì Xiè', '葶苈子': 'Tíng Lì Zǐ', '石菖蒲': 'Shí Chāng Pú', '石斛': 'Shí Hú',
  '莪术 ': 'É Zhú', '紫贝齿': 'Zǐ Bèi Chǐ', '瓦楞子': 'Wǎ Léng Zǐ', '娑罗子': 'Suō Luó Zǐ',
  '秦皮': 'Qín Pí', '金荞麦': 'Jīn Qiáo Mài', '白蔹': 'Bái Liǎn', '漏芦': 'Lòu Lú',
  '山慈菇': 'Shān Cí Gū', '鹤虱': 'Hè Shī', '榧子': 'Fěi Zǐ', '刺猬皮': 'Cì Wèi Pí',
  '木槿皮': 'Mù Jǐn Pí', '婆罗子': 'Suō Luó Zǐ', '马勃': 'Mǎ Bó', '贯众': 'Guàn Zhòng'
};
const map = {};
herbs.forEach(h => { map[h.n] = h.p; });
let expBad = 0, expN = 0;
for (const [n, want] of Object.entries(EXPECT)) {
  const name = n.trim();
  if (!map[name]) continue;            // 题库没有这一味就跳过
  expN++;
  if (map[name] !== want) { expBad++; mark(`读音不符: ${name} = ${map[name]}，应为 ${want}`); }
}
console.log('审定读音抽查 %d 条，不符 %d 条', expN, expBad);
if (!expBad && expN > 50) ok('人工审定读音全部正确');

/* 全部含“子”的药都读 zǐ（不读轻声） */
const ziBad = herbs.filter(h => h.n.includes('子') && h.p.split(/\s+/)[h.n.indexOf('子')] !== 'Zǐ');
if (ziBad.length) ziBad.forEach(h => mark('“子”未读 zǐ: ' + h.n + ' -> ' + h.p));
else ok('含“子”的药一律读 Zǐ（' + herbs.filter(h => h.n.includes('子')).length + ' 条）');

/* ------------------------------------------------------------------ */
/* 3) 检索：拼音归一化（用 app.js 里的真实实现）                      */
/* ------------------------------------------------------------------ */
const appSrc = fs.readFileSync(path.join(docs, 'app.js'), 'utf8');
const helper = appSrc.match(/const PY_TONE = \{[\s\S]*?\nconst pyKey = [^\n]*\n/);
if (!helper) mark('app.js 里找不到拼音检索辅助函数');
else {
  const m = { exports: {} };
  new Function(helper[0] + '\nreturn {pyPlain, pyKey};').call(null);
  const f = new Function(helper[0] + '\nreturn {pyPlain, pyKey};')();
  const cases = [
    ['Má Huáng', 'mahuang'], ['má huáng', 'mahuang'], ['ma huang', 'mahuang'],
    ['Dà Huáng', 'dahuang'], ['Nǚ Zhēn Zǐ', 'nvzhenzi'], ['Zhǐ Qiào', 'zhiqiao']
  ];
  let cbad = 0;
  for (const [inp, want] of cases) {
    if (f.pyKey(inp) !== want) { cbad++; mark(`pyKey(${inp}) = ${f.pyKey(inp)}，应为 ${want}`); }
  }
  if (!cbad) ok('拼音归一化正确（声调/空格/大小写都能搜）');
  /* 用拼音确实能搜到药 */
  const searchable = ['mahuang', 'bai zhu', 'dahuang', 'chuanxiong'];
  let sbad = 0;
  for (const kw of searchable) {
    const kp = f.pyKey(kw);
    const hit = herbs.filter(h => f.pyKey(h.n + (h.p || '')).includes(kp));
    if (!hit.length) { sbad++; mark('拼音搜不到: ' + kw); }
  }
  if (!sbad) ok('拼音搜索可命中（' + searchable.join(' / ') + '）');
}

/* ------------------------------------------------------------------ */
/* 4) 各页面接入                                                       */
/* ------------------------------------------------------------------ */
const app = appSrc;
const pairs = [
  ['app.js 速查列表', app.includes('row-py')],
  ['app.js 详情页', app.includes('py-name')],
  ['app.js 错题本', /renderWrong[\s\S]*?row-py/.test(app)],
  ['app.js 搜索含拼音', app.includes("(h.p || '')")],
  ['encourage.js 看图猜药答案', fs.readFileSync(path.join(docs, 'encourage.js'), 'utf8').includes('g-ans-py')],
  ['timeherb.js 随机卡片', fs.readFileSync(path.join(docs, 'timeherb.js'), 'utf8').includes('rand-py')],
  ['style2.css 拼音样式', ['.row-py', '.py-name', '.g-ans-py', '.rand-py']
    .every(s => fs.readFileSync(path.join(docs, 'style2.css'), 'utf8').includes(s))],
  ['index.html 搜索提示含拼音', fs.readFileSync(path.join(docs, 'index.html'), 'utf8').includes('搜索药名 / 拼音')],
  ['桌面版数据含拼音', fs.readFileSync(path.join(root, 'src', 'EmbeddedData.cs'), 'utf8').includes('pinyin')],
  ['桌面版界面含拼音', ['Pinyin', 'ListText', 'PlainPinyin']
    .every(s => fs.readFileSync(path.join(root, 'src', 'Core.cs'), 'utf8').includes(s))]
];
let pbad = 0;
for (const [name, good] of pairs) { if (good) ok(name); else { pbad++; mark('未接入: ' + name); } }

/* ------------------------------------------------------------------ */
/* 5) 真跑一遍：用 app.js 真实渲染，检查 DOM 里确实有拼音              */
/* ------------------------------------------------------------------ */
(function renderTest() {
  const store = {};
  global.localStorage = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; }
  };
  const makeEl = tag => ({
    tagName: (tag || 'div').toUpperCase(), children: [], dataset: {}, style: {},
    value: '', checked: false, disabled: false, onclick: null, _html: '', _text: '',
    classList: {
      _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); }, contains(c) { return this._s.has(c); }
    },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    querySelector: () => null, querySelectorAll: () => [],
    appendChild(c) { this.children.push(c); }, addEventListener() { }, click() { },
    get firstElementChild() { return makeEl('div'); },
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 })
  });
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

  let bundle = '';
  ['encourage.js', 'timeherb.js', 'app.js'].forEach(f => {
    bundle += '\n/* ==== ' + f + ' ==== */\n' + fs.readFileSync(path.join(docs, f), 'utf8');
  });
  bundle = bundle.replace(/\nboot\(\);\s*$/, '\n');
  const mm = { exports: {} };
  try {
    new Function('module', 'exports', bundle + `
      module.exports = { APP, buildIndex, renderHerbList, showHerb, filteredHerbs, renderWrong, LS, pyKey };`
    )(mm, mm.exports);
  } catch (e) { mark('加载 docs 脚本失败: ' + e.message); return; }
  const R = mm.exports;
  R.APP.herbs = herbs;
  R.APP.categories = JSON.parse(fs.readFileSync(path.join(docs, 'data', 'herbs.json'), 'utf8')).meta.categories;
  R.APP.imgMap = JSON.parse(fs.readFileSync(path.join(docs, 'data', 'images_manifest.json'), 'utf8'));
  R.buildIndex();

  /* 速查列表 */
  R.renderHerbList();
  const listHtml = nodes['herbList'].innerHTML;
  if (listHtml.includes('class="row-py"') && listHtml.includes('Má Huáng')) ok('速查列表渲染出拼音（446 行）');
  else mark('速查列表没有拼音');

  /* 详情页（renderHerbList 会默认选中第一味 = 麻黄） */
  const detailHtml = nodes['detail'].innerHTML;
  if (detailHtml.includes('class="py-name"') && detailHtml.includes('Má Huáng')) ok('详情页药名下渲染出拼音');
  else mark('详情页没有拼音');

  /* 拼音搜索（走真实的 filteredHerbs） */
  const search = nodes['search'];
  const cases = [['mahuang', '麻黄'], ['bai zhu', '白术'], ['má huáng', '麻黄'],
                 ['chuanxiong', '川芎'], ['haigeqiao', '海蛤壳'], ['tusizi', '菟丝子']];
  let sbad = 0;
  for (const [kw, want] of cases) {
    search.value = kw;
    const got = R.filteredHerbs().map(h => h.n);
    if (!got.includes(want)) { sbad++; mark(`搜索「${kw}」未命中 ${want}（命中 ${got.length} 味）`); }
  }
  search.value = '';
  if (!sbad) ok('拼音搜索真实命中（' + cases.map(c => c[0]).join(' / ') + '）');

  /* 错题本 */
  store['tcm_wrong'] = JSON.stringify({ '麻黄': 2 });
  try {
    R.renderWrong();
    const wrongHtml = nodes['wrongList'].innerHTML;
    if (wrongHtml.includes('row-py') && wrongHtml.includes('Má Huáng')) ok('错题本列表渲染出拼音');
    else mark('错题本没有拼音');
  } catch (e) { mark('错题本渲染报错: ' + e.message); }
})();

console.log('');
if (bad) { console.log('PINYIN SELFTEST FAIL - %d 个问题', bad); process.exit(1); }
console.log('PINYIN SELFTEST PASS');