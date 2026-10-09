/* =====================================================================
   中药学复习系统 · 网页版
   单页应用：中药速查 / 限时测试（100 分制）/ 错题本 / 成绩记录
   数据与图片同目录加载，纯静态托管即可（GitHub Pages / Cloudflare Pages）
   ===================================================================== */
'use strict';

const APP = {
  version: '1.1.0',
  herbs: [],
  categories: [],
  synonyms: [],
  imgMap: {},
  imgCache: new Map(),
  timer: null,
  cfg: {
    n1: 10, n2: 4, n3: 10, n4: 10,   // 单选 多选 判断 填空
    minutes: 30, immediate: false, mode: 'random', cats: []
  }
};

const POINTS = { single: 3, multi: 5, judge: 2, fill: 3 };

/* ------------------------------------------------------------------ */
/* 工具                                                                */
/* ------------------------------------------------------------------ */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
const pick = a => a[Math.floor(Math.random() * a.length)];

/* 答案归一化：去标点与虚词 */
const NOISE = /[能可有善主且以之为者也的和与及或、，,。；;：: 　（）()“”"'！!？?·\-—～~\/\\＋+]/g;
const norm = s => String(s == null ? '' : s).replace(NOISE, '').trim();

function levenshtein(a, b) {
  const n = a.length, m = b.length;
  if (!n) return m;
  if (!m) return n;
  let prev = Array.from({ length: m + 1 }, (_, j) => j);
  let cur = new Array(m + 1);
  for (let i = 1; i <= n; i++) {
    cur[0] = i;
    for (let j = 1; j <= m; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
    }
    [prev, cur] = [cur, prev];
  }
  return prev[m];
}

function similarity(user, answer) {
  const a = norm(user), b = norm(answer);
  if (!a || !b) return 0;
  if (a === b) return 1;
  for (const g of APP.synonyms) {
    const gn = g.map(norm);
    if (gn.includes(a) && gn.includes(b)) return 1;
  }
  if (a.includes(b)) return b.length >= 2 ? 0.95 : 0.7;
  if (b.includes(a)) return a.length >= 2 ? 0.9 : 0.65;
  const d = levenshtein(a, b);
  let sim = 1 - d / Math.max(a.length, b.length);
  if (Math.max(a.length, b.length) >= 4 && d <= 1) sim = Math.max(sim, 0.85);
  return Math.max(0, sim);
}
const isCorrect = (u, a) => similarity(u, a) >= 0.75;

/* 本地存储 */
const LS = {
  get(k, d) {
    try {
      const v = localStorage.getItem('tcm_' + k);
      return v == null ? d : JSON.parse(v);
    } catch (e) { return d; }
  },
  set(k, v) {
    try { localStorage.setItem('tcm_' + k, JSON.stringify(v)); } catch (e) { }
  }
};

/* ------------------------------------------------------------------ */
/* 题库：出题引擎（与桌面版逻辑一致）                                   */
/* ------------------------------------------------------------------ */
const fxIndex = new Map();     // 功效 -> [药名]

function buildIndex() {
  fxIndex.clear();
  for (const h of APP.herbs) {
    for (const f of h.f) {
      const k = norm(f);
      if (!fxIndex.has(k)) fxIndex.set(k, []);
      const arr = fxIndex.get(k);
      if (!arr.includes(h.n)) arr.push(h.n);
    }
  }
}

const herbByName = n => APP.herbs.find(h => h.n === n);
const hasFx = (h, item) => h.f.some(f => norm(f) === norm(item));
function fxOverlap(h, item) {
  const n = norm(item);
  if (!n) return false;
  return h.f.some(f => {
    const m = norm(f);
    return m === n || m.includes(n) || n.includes(m);
  });
}
const owners = fx => (fxIndex.get(norm(fx)) || []);
function fxAmbiguous(item) {
  const n = norm(item);
  if (n.length < 2) return true;
  for (const h of APP.herbs) {
    if (fxOverlap(h, item)) continue;
    for (const f of h.f) {
      const m = norm(f);
      if (!m) continue;
      if (m.includes(n) || n.includes(m)) return true;
    }
  }
  return false;
}
const sameFxSet = (a, b) =>
  a.f.length === b.f.length && a.f.every(f => hasFx(b, f));
const twins = h => APP.herbs.filter(o => o !== h && sameFxSet(h, o));

class Engine {
  constructor(cfg) {
    this.cfg = cfg;
    this.used = new Set();
    this.pool = cfg.cats.length && cfg.mode !== 'wrong'
      ? APP.herbs.filter(h => cfg.cats.includes(h.c))
      : APP.herbs.slice();
    if (cfg.mode === 'wrong') {
      const wrong = Object.keys(LS.get('wrong', {}));
      const p = APP.herbs.filter(h => wrong.includes(h.n));
      if (p.length) this.pool = p;
    }
  }
  decoys(target, fx, n) {
    const sameCat = [], other = [];
    for (const o of this.pool) {
      if (o === target || fxOverlap(o, fx) || sameFxSet(o, target)) continue;
      (o.c === target.c ? sameCat : other).push(o);
    }
    return shuffle(sameCat).concat(shuffle(other)).slice(0, n);
  }
  makeSingle() {
    const style = Math.floor(Math.random() * 4);
    if (style === 0) return this.singleByFunction();
    if (style === 1) return this.singleByHerb();
    if (style === 2) return this.singleNotFx();
    return this.singleByNature();
  }
  singleByFunction() {
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      if (!h.f.length) continue;
      const fx = pick(h.f);
      if (owners(fx).length !== 1 || fxAmbiguous(fx)) continue;
      const d = this.decoys(h, fx, 3);
      if (d.length < 3) continue;
      const names = shuffle([h.n, ...d.map(x => x.n)]);
      return {
        type: 'single', herb: h.n, q: `具有「${fx}」功效的药物是：`,
        options: names, answer: names.indexOf(h.n),
        ref: `${h.n}：${h.f.join('；')}。性味${h.x}，归${h.m}。`, tip: h.c
      };
    }
    return null;
  }
  singleByHerb() {
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      if (!h.f.length) continue;
      const fx = pick(h.f);
      if (fxAmbiguous(fx)) continue;
      const opts = [fx], tw = twins(h);
      let guard = 0;
      while (opts.length < 4 && guard++ < 200) {
        const o = pick(this.pool);
        if (o === h || tw.includes(o)) continue;
        const f2 = pick(o.f);
        if (fxOverlap(h, f2) || norm(f2) === norm(fx) || opts.includes(f2)) continue;
        opts.push(f2);
      }
      if (opts.length < 4) continue;
      shuffle(opts);
      return {
        type: 'single', herb: h.n, q: `「${h.n}」的功效是：`, options: opts,
        answer: opts.indexOf(fx), ref: `${h.n}：${h.f.join('；')}`, tip: h.c + '　性味：' + h.x
      };
    }
    return null;
  }
  singleNotFx() {
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      if (h.f.length < 3) continue;
      const tw = twins(h);
      const reals = shuffle(h.f.slice());
      let fake = null, guard = 0;
      while (!fake && guard++ < 200) {
        const o = pick(this.pool);
        if (o === h || tw.includes(o)) continue;
        const f = pick(o.f);
        if (fxOverlap(h, f)) continue;
        if (reals.some(r => norm(r) === norm(f))) continue;
        fake = f;
      }
      if (!fake) continue;
      const opts = shuffle([fake, reals[0], reals[1], reals[2]]);
      return {
        type: 'single', herb: h.n, q: `下列哪一项不是「${h.n}」的功效？`,
        options: opts, answer: opts.indexOf(fake),
        ref: `${h.n}：${h.f.join('；')}（“${fake}”为其他药物的功效）`, tip: h.c
      };
    }
    return null;
  }
  singleByNature() {
    const mode = Math.floor(Math.random() * 3);
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      let correct, q, pool;
      if (mode === 0) { correct = h.x; q = `「${h.n}」的性味是：`; pool = APP.herbs.map(x => x.x); }
      else if (mode === 1) { correct = h.m; q = `「${h.n}」的归经是：`; pool = APP.herbs.map(x => x.m); }
      else { correct = h.c; q = `「${h.n}」属于下列哪一类药物？`; pool = APP.categories; }
      if (!correct) continue;
      const opts = [correct];
      let guard = 0;
      const share = (a, b) => {
        const pa = a.split(/[、，,]/), pb = b.split(/[、，,]/);
        return pa.some(x => x.trim() && pb.some(y => y.trim() === x.trim()));
      };
      while (opts.length < 4 && guard++ < 200) {
        const cand = pick(pool);
        if (!cand || cand === correct || opts.includes(cand)) continue;
        if (mode !== 2 && share(cand, correct)) continue;
        opts.push(cand);
      }
      if (opts.length < 4) continue;
      shuffle(opts);
      return {
        type: 'single', herb: h.n, q, options: opts, answer: opts.indexOf(correct),
        ref: `${h.n}：性味${h.x}，归${h.m}；功效：${h.f.join('；')}`, tip: h.c
      };
    }
    return null;
  }
  makeMulti() {
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      if (h.f.length < 2) continue;
      const tw = twins(h);
      const correct = h.f.slice();
      const fake = [];
      let guard = 0;
      while (fake.length < Math.max(2, 4 - correct.length) && guard++ < 300) {
        const o = pick(this.pool);
        if (o === h || tw.includes(o)) continue;
        const f = pick(o.f);
        const nf = norm(f);
        if (fxOverlap(h, f)) continue;
        if (correct.some(c => norm(c) === nf) || fake.some(c => norm(c) === nf)) continue;
        fake.push(f);
      }
      if (fake.length < Math.max(2, 4 - correct.length)) continue;
      const opts = shuffle(correct.concat(fake));
      const ans = opts.map((o, i) => correct.some(c => norm(c) === norm(o)) ? i : -1).filter(i => i >= 0);
      if (ans.length < 2) continue;
      return {
        type: 'multi', herb: h.n, q: `「${h.n}」的功效包括（多选）：`, options: opts,
        answers: ans, ref: `${h.n}：${h.f.join('；')}`, tip: '多选：全对满分，漏选一半，错选不得分'
      };
    }
    return null;
  }
  makeJudge() {
    for (let k = 0; k < 40; k++) {
      const h = pick(this.pool);
      if (!h.f.length) continue;
      const isTrue = Math.random() < 0.5;
      if (isTrue) {
        const stat = Math.random() < 0.3 && h.x
          ? `「${h.n}」性${h.x}，归${h.m}经。`
          : `「${h.n}」的功效是${h.f.join('；')}。`;
        return {
          type: 'judge', herb: h.n, q: '判断下列说法是否正确：' + stat,
          options: ['正确', '错误'], answer: 0,
          ref: `${h.n}：性味${h.x}，归${h.m}；功效：${h.f.join('；')}`, tip: '判断题'
        };
      }
      const tw = twins(h);
      let bad = null, guard = 0;
      while (!bad && guard++ < 200) {
        const o = pick(this.pool);
        if (o === h || tw.includes(o)) continue;
        const f = pick(o.f);
        if (fxOverlap(h, f) || norm(f).length < 2) continue;
        bad = f;
      }
      if (!bad) continue;
      return {
        type: 'judge', herb: h.n, q: `判断下列说法是否正确：「${h.n}」的功效是${bad}。`,
        options: ['正确', '错误'], answer: 1,
        ref: `${h.n} 的正确功效是：${h.f.join('；')}。`, tip: '判断题'
      };
    }
    return null;
  }
  makeFill() {
    for (let k = 0; k < 60; k++) {
      const style = Math.floor(Math.random() * 4);
      const h = pick(this.pool);
      if (!h.f.length) continue;
      if (style === 0 && h.f.length >= 2) {
        const fx = pick(h.f);
        if (norm(fx).length < 2) continue;
        const body = h.f.join('；').replace(fx, '＿＿＿＿');
        return {
          type: 'fill', herb: h.n, q: `「${h.n}」的功效是：${body}\n请填写空缺的功效：`,
          answer: fx, ref: `${h.n}：${h.f.join('；')}`, tip: '填空题（自动容错判分）'
        };
      }
      if (style === 1) {
        if (!h.x || !h.m) continue;
        if (Math.random() < 0.5) {
          return {
            type: 'fill', herb: h.n, q: `「${h.n}」的性味是：＿＿＿＿\n请填写其性味（如：辛，温）：`,
            answer: h.x, ref: `${h.n}：性味${h.x}，归${h.m}；功效：${h.f.join('；')}`, tip: '填空题'
          };
        }
        return {
          type: 'fill', herb: h.n, q: `「${h.n}」归＿＿＿＿经。\n请填写归经（如：肺、胃经）：`,
          answer: h.m, ref: `${h.n}：性味${h.x}，归${h.m}；功效：${h.f.join('；')}`, tip: '填空题'
        };
      }
      if (style === 2) {
        const fx = pick(h.f);
        if (owners(fx).length !== 1 || fxAmbiguous(fx)) continue;
        return {
          type: 'fill', herb: h.n, q: `具有「${fx}」功效的药物是：＿＿＿＿\n请填写药名：`,
          answer: h.n, ref: `${h.n}：${h.f.join('；')}（性味${h.x}）`, tip: '填空题'
        };
      }
      if (style === 3) {
        const main = h.c.split('·')[0], sub = h.c.split('·')[1] || '';
        if (sub && Math.random() < 0.5) {
          return {
            type: 'fill', herb: h.n, q: `「${h.n}」属于${main}中的哪一类？\n请填写（如：发散风寒药）：`,
            answer: sub, ref: `${h.n}　分类：${h.c}`, tip: '填空题'
          };
        }
        return {
          type: 'fill', herb: h.n, q: `「${h.n}」属于哪一类药物？\n请填写（如：解表药）：`,
          answer: main, ref: `${h.n}　分类：${h.c}`, tip: '填空题'
        };
      }
    }
    return null;
  }
  build(cfg) {
    const items = [];
    const add = (type, count, points, maker) => {
      if (count <= 0) return;
      let made = 0, guard = 0, fail = 0;
      while (made < count && guard++ < count * 80 + 900 && fail < 400) {
        let it = null;
        try { it = maker.call(this); } catch (e) { it = null; }
        if (!it) { fail++; continue; }
        const stem = type + '|' + it.q;
        if (this.used.has(stem)) { fail++; continue; }
        this.used.add(stem);
        fail = 0;
        it.points = points;
        items.push(it);
        made++;
      }
    };
    add('single', cfg.n1, POINTS.single, this.makeSingle);
    add('multi', cfg.n2, POINTS.multi, this.makeMulti);
    add('judge', cfg.n3, POINTS.judge, this.makeJudge);
    add('fill', cfg.n4, POINTS.fill, this.makeFill);
    return shuffle(items);
  }
}

/* 判分 */
function scoreOf(it) {
  if (it.type === 'single') {
    return it.pick != null && it.pick === it.answer ? it.points : 0;
  }
  if (it.type === 'judge') {
    return it.pick != null && it.pick === it.answer ? it.points : 0;
  }
  if (it.type === 'fill') {
    return isCorrect(it.input || '', it.answer) ? it.points : 0;
  }
  if (it.type === 'multi') {
    const p = it.picks || [];
    if (!p.length) return 0;
    let wrong = false, hit = 0;
    for (const i of p) {
      if (it.answers.includes(i)) hit++; else wrong = true;
    }
    if (wrong) return 0;
    if (hit === it.answers.length) return it.points;
    return it.points * 0.5;
  }
  return 0;
}
const typeName = t => ({ single: '单项选择题', multi: '多项选择题', judge: '判断题', fill: '填空题' }[t] || '题目');

/* ------------------------------------------------------------------ */
/* 界面：通用                                                            */
/* ------------------------------------------------------------------ */
function toast(msg, ms) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('show'), ms || 2200);
}

function switchTab(name) {
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  if (name === 'wrong') renderWrong();
  if (name === 'scores') renderScores();
  if (name === 'random') renderRandomHerb();
  if (name === 'guess') { renderGuess(); sprinkleMotto(); }
  /* 支持链接直达：#browse / #random / #exam / #guess / #wrong / #scores
     也支持 #browse/麻黄 定位到某味药（切换药时不覆盖带药名的 hash） */
  try {
    const cur = (location.hash || '').replace('#', '');
    const mine = (tab === 'browse') ? (browseName ? 'browse/' + encodeURIComponent(browseName) : 'browse') : name;
    if (cur !== mine && !(cur.startsWith('browse/') && tab === 'browse')) {
      history.replaceState(null, '', '#' + mine);
    }
  } catch (e) { }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* 从 URL hash 恢复标签页；支持 #browse/麻黄 直达某味药 */
function tabFromHash() {
  const raw = (location.hash || '').replace('#', '');
  const [tab, arg] = raw.split('/');
  const ok = ['browse', 'random', 'exam', 'guess', 'wrong', 'scores'];
  return { tab: ok.includes(tab) ? tab : 'browse', arg: arg ? decodeURIComponent(arg) : '' };
}

/* 应用 hash：切换标签页，若带药名则定位到该药 */
function applyHash() {
  const { tab, arg } = tabFromHash();
  switchTab(tab);
  if (tab === 'browse' && arg) {
    const h = herbByName(arg);
    if (h) {
      const s = $('#search');
      if (s) s.value = arg;
      browseCat = '';
      renderHerbList();
      showHerb(arg);
    }
  }
}

/* ------------------------------------------------------------------ */
/* 速查                                                                */
/* ------------------------------------------------------------------ */
let browseCat = '';
let browseName = '';   /* 当前查看的药名（用于 #browse/药名 直达与分享） */
let browseGroup = '';  /* 当前展开的大类（空=未展开，只显示大类标签） */

/* 记住筛选状态，避免刷新/切换标签后错位或丢失 */
function saveBrowse() {
  try { LS.set('browseCat', browseCat || ''); } catch (e) { }
}
function restoreBrowse() {
  try {
    const c = LS.get('browseCat', '');
    if (c && APP.categories.includes(c)) { browseCat = c; browseGroup = c.split('·')[0]; }
    else { browseCat = ''; browseGroup = ''; }
  } catch (e) { browseCat = ''; browseGroup = ''; }
}

/* 把 43 个子分类按“大类”归组：大类·小类 -> 大类 -> [小类...] */
function groupCategories() {
  const g = [];
  const map = {};
  APP.categories.forEach(c => {
    const i = c.indexOf('·');
    const major = i < 0 ? c : c.slice(0, i);
    if (!map[major]) { map[major] = []; g.push({ major, subs: map[major] }); }
    map[major].push(c);
  });
  return g;
}

function renderCategoryChips() {
  const box = $('#catChips');
  const groups = groupCategories();
  const cur = APP.categories.includes(browseCat) ? browseCat : '';
  /* 当前展开的大类：优先用 browseGroup，否则由已选分类推断 */
  const openMajor = browseGroup || (cur ? cur.split('·')[0] : '');

  /* 折叠式：平时只显示大类（一行装得下），点大类才展开它的子类。
     注意：browseCat 与 browseGroup 必须始终一致，否则子类行会停留在上一个大类。 */
  const allActive = !browseCat;
  let html = '<div class="cgroup">' +
    `<button class="chip${allActive ? ' active' : ''}" data-cat="">全部分类</button>`;
  groups.forEach(gr => {
    const hasSub = gr.subs.length > 1 || gr.subs[0] !== gr.major;
    const open = openMajor === gr.major;
    /* 该大类下是否命中当前筛选 */
    const inThis = !!browseCat && browseCat.split('·')[0] === gr.major;
    const cls = ['chip', 'major'];
    if (open) cls.push('open');
    if (inThis) cls.push('active');
    if (hasSub) cls.push('has-sub');
    html += `<button class="${cls.join(' ')}" data-major="${esc(gr.major)}"` +
            `${hasSub ? '' : ` data-cat="${esc(gr.subs[0])}"`}>` +
            `${esc(gr.major)}<span class="n">${gr.subs.length}</span>` +
            `${hasSub ? '<span class="ar">' + (open ? '▾' : '▸') + '</span>' : ''}</button>`;
  });
  html += '</div>';

  if (openMajor) {
    const gr = groups.find(x => x.major === openMajor);
    const subs = gr ? gr.subs : [];
    if (subs.length > 1) {
      html += '<div class="csub">' +
        subs.map(s => `<button class="chip sub${s === cur ? ' active' : ''}" data-cat="${esc(s)}">` +
                      `${esc(s.split('·')[1] || s)}</button>`).join('') +
        '</div>';
    }
  }
  box.innerHTML = html;

  /* 当前筛选状态提示 */
  const now = $('#catNow');
  if (now) {
    const cnt = filteredHerbs().length;
    now.textContent = browseCat ? `当前：${browseCat}（${cnt} 味）` : `当前：全部分类（${cnt} 味）`;
  }

  /* 统一的“应用筛选”入口：一次点击只渲染一次，且保证状态一致 + 记忆 */
  const applyCat = (cat, group) => {
    browseCat = cat || '';
    if (group !== undefined) browseGroup = group || '';
    else browseGroup = browseCat ? browseCat.split('·')[0] : '';
    if (!browseCat) browseGroup = '';
    saveBrowse();
    renderCategoryChips();
    renderHerbList();
  };

  box.onclick = e => {
    const b = e.target.closest('.chip');
    if (!b) return;
    /* ① 全部分类 */
    if (b.dataset.cat === '') { applyCat('', ''); return; }
    /* ② 具体子类 */
    if (b.dataset.cat) { applyCat(b.dataset.cat, b.dataset.cat.split('·')[0]); return; }
    /* ③ 大类：有子类则展开（默认选第一个）；已在其中则收起 */
    const major = b.dataset.major;
    const gr = groupCategories().find(x => x.major === major);
    if (!gr) return;
    if (gr.subs.length > 1) {
      if (browseGroup === major && browseCat) applyCat('', '');
      else applyCat(gr.subs[0], major);
    } else {
      applyCat(gr.subs[0], '');
    }
  };
}

function filteredHerbs() {
  const key = $('#search').value.trim();
  const onlyWrong = $('#onlyWrong').checked;
  const wrong = LS.get('wrong', {});
  return APP.herbs.filter(h => {
    if (browseCat && h.c !== browseCat) return false;
    if (onlyWrong && !wrong[h.n]) return false;
    if (key) {
      const blob = h.n + h.x + h.m + h.f.join('') + h.c;
      if (blob.indexOf(key) < 0) return false;
    }
    return true;
  });
}

function renderHerbList() {
  const list = filteredHerbs();
  $('#herbCount').textContent = `共 ${list.length} 味（题库 ${APP.herbs.length} 味）`;
  const box = $('#herbList');
  box.innerHTML = list.map(h =>
    `<div class="row" data-name="${esc(h.n)}">
       <span class="row-name">${esc(h.n)}</span>
       <span class="row-cat">${esc(h.c.split('·')[0])}</span>
     </div>`).join('') || '<div class="empty">没有匹配的药物</div>';
  // 点击（含触摸）选中药物 —— 修复：之前速查列表漏绑事件，点不动
  box.onclick = e => {
    const row = e.target.closest('.row');
    if (row && row.dataset.name) showHerb(row.dataset.name);
  };
  if (list.length) showHerb(list[0].n);
  else $('#detail').innerHTML = '';
}

function showHerb(name) {
  const h = herbByName(name);
  if (!h) return;
  browseName = name;
  $$('#herbList .row').forEach(r => r.classList.toggle('active', r.dataset.name === name));
  const wrong = LS.get('wrong', {});
  $('#detail').innerHTML = `
    <h2>${esc(h.n)}</h2>
    <dl>
      <dt>分类</dt><dd>${esc(h.c)}</dd>
      <dt>性味</dt><dd>${esc(h.x)}</dd>
      <dt>归经</dt><dd>${esc(h.m)}</dd>
      <dt>功效</dt><dd class="fx">${esc(h.f.join('；'))}</dd>
      <dt>用法用量</dt><dd>${esc(h.u)}</dd>
      <dt>使用注意</dt><dd>${esc(h.k)}</dd>
    </dl>
    ${wrong[h.n] ? `<div class="warnbox">※ 该药在你的错题本中（累计错 ${wrong[h.n]} 次）</div>` : ''}`;
  renderImages(h.n);
}

function renderImages(name) {
  const box = $('#imgBox');
  const files = APP.imgMap[name] || [];
  const hidden = LS.get('hidden', []);
  const shown = files.filter(f => !hidden.includes(name + '|' + f));
  if (!shown.length) {
    box.innerHTML = files.length
      ? `<div class="img-all-hidden">这一味的图都被隐藏了（可在下方恢复）</div>` : '';
    renderHiddenBox(name);
    return;
  }
  box.innerHTML = shown.map((f, i) =>
    `<figure class="ph" data-name="${esc(name)}" data-file="${esc(f)}">
       <img src="images/${encodeURIComponent(f)}" alt="${esc(name)}" loading="lazy">
       <figcaption>图 ${i + 1}/${shown.length} · 点击放大</figcaption>
     </figure>`).join('');
  renderHiddenBox(name);
}

/* 图片查看器 */
let viewerState = null;
function openViewer(name, file) {
  const files = (APP.imgMap[name] || []).filter(f => !LS.get('hidden', []).includes(name + '|' + f));
  viewerState = { name, files, index: Math.max(0, files.indexOf(file)) };
  const v = $('#viewer');
  v.classList.add('show');
  drawViewer();
  document.body.style.overflow = 'hidden';
}
function drawViewer() {
  if (!viewerState) return;
  const { name, files, index } = viewerState;
  const f = files[index];
  $('#viewerImg').src = 'images/' + encodeURIComponent(f);
  $('#viewerCap').textContent = `${name} · 图 ${index + 1}/${files.length}`;
  $('#viewerPrev').style.visibility = files.length > 1 ? 'visible' : 'hidden';
  $('#viewerNext').style.visibility = files.length > 1 ? 'visible' : 'hidden';
  /* 当前这张是否已被隐藏 → 决定按钮可用状态 */
  const isHidden = LS.get('hidden', []).includes(name + '|' + f);
  const hb = $('#viewerHide'), rb = $('#viewerRestore');
  if (hb) {
    hb.disabled = isHidden;
    hb.textContent = isHidden ? '已隐藏' : '🙈 隐藏这张图';
  }
  if (rb) {
    rb.disabled = !isHidden;
    rb.style.opacity = isHidden ? '1' : '.5';
  }
}
function closeViewer() {
  $('#viewer').classList.remove('show');
  document.body.style.overflow = '';
}
function stepViewer(d) {
  if (!viewerState || viewerState.files.length < 2) return;
  viewerState.index = (viewerState.index + d + viewerState.files.length) % viewerState.files.length;
  drawViewer();
}
function deleteViewerImage() {
  /* 兼容旧调用：改为“隐藏” */
  hideViewerImage();
}

/* 隐藏当前这张图（可恢复，不再叫“删除”） */
function hideViewerImage() {
  if (!viewerState) return;
  const { name, files, index } = viewerState;
  const f = files[index];
  if (!f) return;
  const hidden = LS.get('hidden', []);
  if (!hidden.includes(name + '|' + f)) hidden.push(name + '|' + f);
  LS.set('hidden', hidden);
  toast('🙈 已隐藏这张图（可在图片下方「已隐藏」里点恢复）');
  renderImages(name);
  /* 记住刚隐藏的是哪张，方便「恢复这张图」按钮把它找回来 */
  const lastHidden = f;
  const left = files.filter(x => x !== f);
  if (left.length) {
    viewerState = { name, files: left, index: Math.min(index, left.length - 1), lastHidden };
    drawViewer();
  } else {
    closeViewer();
  }
}

/* 恢复当前这张图 */
function restoreViewerImage() {
  if (!viewerState) return;
  const { name, files, index } = viewerState;
  /* 若当前这张没被隐藏，就尝试恢复“刚被隐藏的那张” */
  const cur = files[index];
  const target = LS.get('hidden', []).includes(name + '|' + cur) ? cur : viewerState.lastHidden;
  if (!target) { toast('这张图没有被隐藏，无需恢复'); return; }
  const key = name + '|' + target;
  LS.set('hidden', LS.get('hidden', []).filter(x => x !== key));
  toast('↩ 已恢复这张图');
  /* 重新取该药全部图片，并定位到刚恢复的这张 */
  const all = (APP.imgMap[name] || []).filter(x => !LS.get('hidden', []).includes(name + '|' + x));
  viewerState = { name, files: all, index: Math.max(0, all.indexOf(target)) };
  drawViewer();
  renderImages(name);
}

/* 「已隐藏」面板：一键全部恢复 */
function renderHiddenBox(name) {
  const box = $('#hidBox');
  if (!box) return;
  const hidden = LS.get('hidden', []);
  const mine = hidden.filter(x => x.startsWith(name + '|'));
  if (!mine.length) { box.innerHTML = ''; return; }
  box.innerHTML = `
    <div class="hid-title">已隐藏 ${mine.length} 张（可恢复）</div>
    <div class="hid-list">
      ${mine.map(k => {
        const f = k.slice(name.length + 1);
        return `<span class="hid-item" data-file="${esc(f)}">
                  <img src="images/${encodeURIComponent(f)}" alt="已隐藏" loading="lazy">
                  <button class="hid-restore" data-file="${esc(f)}">恢复</button>
                </span>`;
      }).join('')}
    </div>
    <button class="btn small" id="hidRestoreAll">↩ 全部恢复</button>`;
  box.querySelectorAll('.hid-restore').forEach(b => {
    b.onclick = () => {
      const f = b.dataset.file;
      LS.set('hidden', LS.get('hidden', []).filter(x => x !== name + '|' + f));
      toast('↩ 已恢复');
      renderImages(name); renderHiddenBox(name);
    };
  });
  const all = box.querySelector('#hidRestoreAll');
  if (all) all.onclick = () => {
    LS.set('hidden', LS.get('hidden', []).filter(x => !x.startsWith(name + '|')));
    toast('↩ 已恢复该药全部图片');
    renderImages(name); renderHiddenBox(name);
  };
}

/* ------------------------------------------------------------------ */
/* 测试                                                                */
/* ------------------------------------------------------------------ */
function readCfgFromUI() {
  const cfg = APP.cfg;
  cfg.n1 = +$('#n1').value; cfg.n2 = +$('#n2').value;
  cfg.n3 = +$('#n3').value; cfg.n4 = +$('#n4').value;
  cfg.minutes = +$('#minutes').value;
  cfg.immediate = $('#immediate').checked;
  cfg.mode = $('#mode').value;
  cfg.cats = $$('#cats input:checked').map(i => i.value);
  return cfg;
}

function totalScore(cfg) {
  return cfg.n1 * POINTS.single + cfg.n2 * POINTS.multi +
    cfg.n3 * POINTS.judge + cfg.n4 * POINTS.fill;
}

function updateTotal() {
  const cfg = readCfgFromUI();
  const total = totalScore(cfg);
  const qs = cfg.n1 + cfg.n2 + cfg.n3 + cfg.n4;
  let txt = `本次试卷：${qs} 题　合计 ${total} 分`;
  const ok = total === 100 && qs > 0;
  txt += ok ? '　✔ 正好 100 分，可以开考'
    : (total > 100 ? `　✘ 超出 ${total - 100} 分，请减少题量`
      : `　✘ 还差 ${100 - total} 分，请增加题量`);
  const el = $('#totalInfo');
  el.textContent = qs === 0 ? '请至少设置一种题型' : txt;
  el.className = 'total ' + (ok ? 'ok' : 'bad');
  $('#startBtn').disabled = !ok;
  LS.set('cfg', cfg);
}

function applyCfgToUI() {
  const c = Object.assign({}, APP.cfg, LS.get('cfg', {}));
  APP.cfg = c;
  $('#n1').value = c.n1; $('#n2').value = c.n2;
  $('#n3').value = c.n3; $('#n4').value = c.n4;
  $('#minutes').value = c.minutes;
  $('#immediate').checked = !!c.immediate;
  $('#mode').value = c.mode || 'random';
  $('#cats').innerHTML = APP.categories.map(cat =>
    `<label class="cbx"><input type="checkbox" value="${esc(cat)}"${c.cats && c.cats.includes(cat) ? ' checked' : ''}> ${esc(cat)}</label>`).join('');
  updateTotal();
}

let QUIZ = null;

function startQuiz() {
  const cfg = readCfgFromUI();
  if (totalScore(cfg) !== 100) { toast('合计必须是 100 分'); return; }
  LS.set('cfg', cfg);
  const eng = new Engine(cfg);
  const items = eng.build(cfg);
  if (!items.length) { toast('未能生成题目，请扩大抽题范围'); return; }
  if (items.length < cfg.n1 + cfg.n2 + cfg.n3 + cfg.n4) {
    toast(`当前范围内可生成的不重复题目有限，本次共 ${items.length} 题`);
  }
  QUIZ = {
    items, index: 0, elapsed: 0, limit: cfg.minutes * 60,
    cfg, finished: false, modeName: cfg.mode === 'wrong' ? '错题强化' : (cfg.immediate ? '练习模式' : '模拟测试')
  };
  $('#setupPage').classList.add('hide');
  $('#quizPage').classList.remove('hide');
  renderQuestion();
  startTimer();
}

function startTimer() {
  stopTimer();
  APP.timer = setInterval(() => {
    if (!QUIZ || QUIZ.finished) return;
    QUIZ.elapsed++;
    updateTimer();
    if (QUIZ.limit > 0 && QUIZ.elapsed >= QUIZ.limit) {
      stopTimer();
      alert('考试时间到，系统将自动交卷。');
      finishQuiz();
    }
  }, 1000);
  updateTimer();
}
function stopTimer() { if (APP.timer) { clearInterval(APP.timer); APP.timer = null; } }

function fmt(sec) {
  const m = Math.floor(sec / 60), s = sec % 60;
  return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}
function updateTimer() {
  const t = $('#timer');
  if (!QUIZ) return;
  if (QUIZ.limit > 0) {
    const left = Math.max(0, QUIZ.limit - QUIZ.elapsed);
    t.textContent = '剩余 ' + fmt(left);
    t.className = 'timer ' + (left <= 60 ? 'danger' : left <= 300 ? 'warn' : '');
  } else {
    t.textContent = '已用 ' + fmt(QUIZ.elapsed);
    t.className = 'timer';
  }
  const answered = QUIZ.items.filter(isAnswered).length;
  $('#progressText').textContent = `已答 ${answered} / ${QUIZ.items.length}`;
  $('#progressBar > i').style.width = (answered / QUIZ.items.length * 100) + '%';
}
function isAnswered(it) {
  if (it.type === 'multi') return (it.picks || []).length > 0;
  if (it.type === 'fill') return !!(it.input && it.input.trim());
  return it.pick != null;
}

function renderQuestion() {
  const it = QUIZ.items[QUIZ.index];
  $('#qIndex').textContent = `第 ${QUIZ.index + 1} 题 / 共 ${QUIZ.items.length} 题`;
  $('#qMeta').textContent = `${typeName(it.type)}　本题 ${it.points} 分`;
  $('#qText').textContent = it.q;
  const box = $('#options');
  box.innerHTML = '';
  if (it.type === 'single' || it.type === 'judge') {
    it.options.forEach((o, i) => {
      const label = document.createElement('label');
      label.className = 'opt' + (it.pick === i ? ' picked' : '') +
        (it.graded ? (i === it.answer ? ' right' : (it.pick === i ? ' wrong' : '')) : '');
      label.innerHTML = `<input type="radio" name="opt" ${it.pick === i ? 'checked' : ''} ${it.graded ? 'disabled' : ''}>
        <span class="mark">${String.fromCharCode(65 + i)}</span><span>${esc(o)}</span>`;
      label.querySelector('input').onchange = () => {
        it.pick = i; renderQuestion(); updateTimer();
      };
      box.appendChild(label);
    });
  } else if (it.type === 'multi') {
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.textContent = '多选：全对满分，漏选一半，错选不得分';
    box.appendChild(hint);
    it.picks = it.picks || [];
    it.options.forEach((o, i) => {
      const on = it.picks.includes(i);
      const label = document.createElement('label');
      label.className = 'opt' + (on ? ' picked' : '') +
        (it.graded ? (it.answers.includes(i) ? ' right' : (on ? ' wrong' : '')) : '');
      label.innerHTML = `<input type="checkbox" ${on ? 'checked' : ''} ${it.graded ? 'disabled' : ''}>
        <span class="mark">${String.fromCharCode(65 + i)}</span><span>${esc(o)}</span>`;
      label.querySelector('input').onchange = e => {
        if (e.target.checked) it.picks.push(i);
        else it.picks = it.picks.filter(x => x !== i);
        renderQuestion(); updateTimer();
      };
      box.appendChild(label);
    });
  } else if (it.type === 'fill') {
    const wrap = document.createElement('div');
    wrap.className = 'fillwrap';
    wrap.innerHTML = `<input id="fillInput" class="fill" type="text" placeholder="在此输入答案（支持同义与错别字容错）"
        value="${esc(it.input || '')}" ${it.graded ? 'disabled' : ''}>
      <div class="hint">提示：可填功效、性味、归经或药名；系统自动容错判定。</div>`;
    box.appendChild(wrap);
    const inp = $('#fillInput');
    inp.oninput = () => { it.input = inp.value; updateTimer(); };
    if (!it.graded) setTimeout(() => inp.focus(), 30);
  }
  if (it.graded) renderFeedback(it);
  renderNav();
  updateTimer();
}

function renderFeedback(it) {
  const ok = it.score >= it.points - 1e-6;
  const part = !ok && it.score > 0;
  let correct = '';
  if (it.type === 'single' || it.type === 'judge') correct = it.options[it.answer];
  else if (it.type === 'multi') correct = it.answers.map(i => it.options[i]).join('　');
  else correct = it.answer;
  const div = document.createElement('div');
  div.className = 'feedback ' + (ok ? 'ok' : part ? 'part' : 'bad');
  div.innerHTML = `<div class="fb-head">${ok ? '✔ 回答正确' : part ? '◐ 部分正确' : '✘ 回答错误'}
      　得分 ${fmtScore(it.score)} / ${it.points}</div>
    <div class="fb-correct">【正确答案】${esc(correct)}</div>
    <div class="fb-ref">【解析】${esc(it.ref)}（${esc(it.tip)}）</div>`;
  $('#options').appendChild(div);
}

function fmtScore(v) {
  return Math.abs(v - Math.round(v)) < 1e-6 ? String(Math.round(v)) : v.toFixed(1);
}

function renderNav() {
  const nav = $('#navGrid');
  nav.innerHTML = QUIZ.items.map((it, i) => {
    let cls = 'navbtn';
    if (it.graded) cls += it.score >= it.points - 1e-6 ? ' right' : (it.score > 0 ? ' part' : ' wrong');
    else if (i === QUIZ.index) cls += ' cur';
    else if (isAnswered(it)) cls += ' done';
    return `<button class="${cls}" data-i="${i}">${i + 1}</button>`;
  }).join('');
  nav.onclick = e => {
    const b = e.target.closest('.navbtn');
    if (!b) return;
    QUIZ.index = +b.dataset.i;
    renderQuestion();
  };
}

function confirmCurrent() {
  const it = QUIZ.items[QUIZ.index];
  if (!isAnswered(it)) { toast('请先作答'); return; }
  if (it.graded) return;
  it.score = scoreOf(it);
  it.graded = true;
  renderQuestion();
  if (it.score < it.points - 1e-6) addWrong(it.herb);
}

function go(d) {
  const n = QUIZ.index + d;
  if (n < 0 || n >= QUIZ.items.length) return;
  QUIZ.index = n;
  renderQuestion();
}

function addWrong(name) {
  const w = LS.get('wrong', {});
  w[name] = (w[name] || 0) + 1;
  LS.set('wrong', w);
}

function finishQuiz() {
  if (!QUIZ || QUIZ.finished) return;
  stopTimer();
  QUIZ.finished = true;
  let total = 0, score = 0, correct = 0, wrongCount = 0;
  for (const it of QUIZ.items) {
    if (!it.graded) { it.score = scoreOf(it); it.graded = true; }
    total += it.points;
    score += it.score;
    if (it.score >= it.points - 1e-6) correct++;
    else { wrongCount++; addWrong(it.herb); }
  }
  score = Math.round(score);
  const rec = {
    time: new Date().toLocaleString('zh-CN'),
    mode: QUIZ.modeName, score, total, correct, count: QUIZ.items.length,
    seconds: QUIZ.elapsed, wrong: wrongCount
  };
  const hist = LS.get('history', []);
  hist.push(rec);
  LS.set('history', hist.slice(-200));
  renderResult(score, total, correct, wrongCount);
}

function renderResult(score, total, correct, wrongCount) {
  const pct = total ? score / total : 0;
  const comment = pct >= 0.95 ? '优秀！基础扎实' : pct >= 0.85 ? '良好，继续巩固'
    : pct >= 0.75 ? '中等，注意易混药' : pct >= 0.6 ? '及格，建议重做题库' : '不及格，建议先看速查表';
  const list = QUIZ.items.map((it, i) => {
    const ok = it.score >= it.points - 1e-6;
    const part = !ok && it.score > 0;
    let mine = '', std = '';
    if (it.type === 'single' || it.type === 'judge') {
      mine = it.pick != null ? it.options[it.pick] : '（未作答）';
      std = it.options[it.answer];
    } else if (it.type === 'multi') {
      mine = (it.picks || []).map(x => it.options[x]).join('、') || '（未作答）';
      std = it.answers.map(x => it.options[x]).join('、');
    } else {
      mine = it.input || '（未作答）';
      std = it.answer;
    }
    return `<div class="ana ${ok ? 'ok' : part ? 'part' : 'bad'}">
      <div class="ana-head">${ok ? '✔' : part ? '◐' : '✘'} 第 ${i + 1} 题　${typeName(it.type)}　得分 ${fmtScore(it.score)}/${it.points}（${esc(it.herb)}）</div>
      <div class="ana-q">${esc(it.q)}</div>
      <div class="ana-line"><span class="lb">你答：</span>${esc(mine)}</div>
      <div class="ana-line"><span class="lb ok">正确：</span>${esc(std)}</div>
      ${ok ? '' : `<div class="ana-line"><span class="lb">解析：</span>${esc(it.ref)}</div>`}
    </div>`;
  }).join('');
  $('#resultBox').innerHTML = `
    <div class="scoreCard ${pct >= 0.6 ? 'pass' : 'fail'}">
      <div class="scoreBig">${score} 分</div>
      <div class="scoreMeta">满分 ${total} 分　${comment}</div>
      <div class="scoreStats">
        <span>正确 ${correct} / ${QUIZ.items.length} 题</span>
        <span>正确率 ${(pct * 100).toFixed(1)} %</span>
        <span>用时 ${Math.floor(QUIZ.elapsed / 60)} 分 ${QUIZ.elapsed % 60} 秒</span>
        <span>错题 ${wrongCount} 题</span>
      </div>
    </div>
    <div class="btnrow">
      <button class="btn primary" id="againBtn">再做一套</button>
      <button class="btn" id="redoWrongBtn" ${wrongCount ? '' : 'disabled'}>只重做错题</button>
      <button class="btn ghost" id="backBtn">返回首页</button>
    </div>
    <h3 class="anah">逐题解析</h3>${list}`;
  $('#quizPage').classList.add('hide');
  $('#resultPage').classList.remove('hide');
  $('#againBtn').onclick = () => { $('#resultPage').classList.add('hide'); $('#setupPage').classList.remove('hide'); updateTotal(); };
  $('#backBtn').onclick = () => { $('#resultPage').classList.add('hide'); $('#setupPage').classList.remove('hide'); switchTab('browse'); };
  $('#redoWrongBtn').onclick = () => redoWrong();
  window.scrollTo({ top: 0 });
}

function redoWrong() {
  const items = QUIZ.items.filter(it => it.score < it.points - 1e-6).map(it => {
    const c = Object.assign({}, it);
    c.pick = null; c.picks = []; c.input = ''; c.graded = false; c.score = 0;
    return c;
  });
  if (!items.length) { toast('没有错题'); return; }
  QUIZ = { items, index: 0, elapsed: 0, limit: 0, cfg: QUIZ.cfg, finished: false, modeName: '错题重做' };
  $('#resultPage').classList.add('hide');
  $('#quizPage').classList.remove('hide');
  renderQuestion(); startTimer();
}

/* ------------------------------------------------------------------ */
/* 错题本 / 成绩记录                                                    */
/* ------------------------------------------------------------------ */
function renderWrong() {
  const wrong = LS.get('wrong', {});
  const rows = Object.keys(wrong).map(n => ({ n, c: wrong[n], h: herbByName(n) }))
    .filter(r => r.h).sort((a, b) => b.c - a.c);
  $('#wrongSummary').textContent = rows.length
    ? `共 ${rows.length} 味药 · 累计错 ${rows.reduce((s, r) => s + r.c, 0)} 次` : '错题本为空';
  if (!rows.length) {
    $('#wrongList').innerHTML = '<div class="empty">错题本还是空的：做一次测试，答错的题会自动记到这里。</div>';
    $('#wrongDetail').innerHTML = '';
    return;
  }
  $('#wrongList').innerHTML = rows.map(r =>
    `<div class="row" data-name="${esc(r.n)}">
      <span class="row-name">${esc(r.n)}</span>
      <span class="row-cat">${esc(r.h.c.split('·')[0])}</span>
      <span class="row-cnt">${r.c} 次</span></div>`).join('');
  $('#wrongList').onclick = e => {
    const row = e.target.closest('.row');
    if (!row) return;
    const name = row.dataset.name;
    $$('#wrongList .row').forEach(x => x.classList.toggle('active', x === row));
    const h = herbByName(name);
    $('#wrongDetail').innerHTML = `
      <h2>${esc(h.n)}</h2>
      <div class="warnbox">做错 ${wrong[name]} 次</div>
      <button class="btn small" id="goBrowse">在速查中查看</button>
      <dl><dt>分类</dt><dd>${esc(h.c)}</dd><dt>性味</dt><dd>${esc(h.x)}</dd>
      <dt>归经</dt><dd>${esc(h.m)}</dd><dt>功效</dt><dd class="fx">${esc(h.f.join('；'))}</dd>
      <dt>用法</dt><dd>${esc(h.u)}</dd><dt>注意</dt><dd>${esc(h.k)}</dd></dl>`;
    $('#goBrowse').onclick = () => {
      switchTab('browse');
      $('#search').value = h.n;
      browseCat = '';
      renderCategoryChips();
      renderHerbList();
      window.scrollTo({ top: 0 });
    };
  };
  $('#wrongList').firstElementChild.click();
}

function renderScores() {
  const hist = LS.get('history', []);
  const best = hist.reduce((m, r) => Math.max(m, r.score), 0);
  const avg = hist.length ? hist.reduce((s, r) => s + (r.total ? r.score / r.total : 0), 0) / hist.length * 100 : 0;
  $('#scoresStat').innerHTML = `
    <div class="stat"><span>测试次数</span><b>${hist.length} 次</b></div>
    <div class="stat"><span>历史最高</span><b>${hist.length ? best + ' 分' : '-'}</b></div>
    <div class="stat"><span>百分制均值</span><b>${hist.length ? avg.toFixed(1) + ' 分' : '-'}</b></div>
    <div class="stat"><span>错题本</span><b>${Object.keys(LS.get('wrong', {})).length} 味</b></div>`;
  const last = hist.slice(-20);
  const chart = $('#chart');
  if (!last.length) { chart.innerHTML = '<div class="empty">暂无数据</div>'; }
  else {
    chart.innerHTML = last.map(r => {
      const pct = r.total ? r.score / r.total : 0;
      const cls = pct >= 0.9 ? 'g' : pct >= 0.6 ? 'm' : 'b';
      return `<div class="bar ${cls}" style="height:${Math.max(4, pct * 100)}%">
                <span>${r.score}</span><i>${(r.time || '').slice(5, 10)}</i></div>`;
    }).join('');
  }
  const rows = hist.slice().reverse();
  $('#histTable tbody').innerHTML = rows.length ? rows.map(r => `
    <tr><td>${esc(r.time)}</td><td>${esc(r.mode)}</td><td>${r.score} / ${r.total}</td>
    <td>${r.count ? (r.correct / r.count * 100).toFixed(1) : 0} %</td>
    <td>${r.correct} / ${r.count}</td>
    <td>${Math.floor(r.seconds / 60)}分${r.seconds % 60}秒</td><td>${r.wrong}</td></tr>`).join('')
    : '<tr><td colspan="7" class="empty">还没有测试记录</td></tr>';
}

/* ------------------------------------------------------------------ */
/* 版本更新检查                                                         */
/* ------------------------------------------------------------------ */
async function checkUpdate(manual) {
  try {
    const r = await fetch('version.json?_=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const v = await r.json();
    APP.remoteVersion = v.version;
    if (v.version !== APP.version) {
      $('#updateBar').classList.remove('hide');
      $('#updateBar').innerHTML = `发现新版本 <b>${esc(v.version)}</b>（当前 ${esc(APP.version)}）：
        ${esc(v.notes || '')} <button class="btn small" id="reloadBtn">刷新更新</button>`;
      $('#reloadBtn').onclick = () => location.reload(true);
      if (manual) toast('有新版本，点击「刷新更新」');
    } else if (manual) {
      toast('已是最新版本 ' + APP.version);
    }
  } catch (e) {
    if (manual) toast('检查更新失败（可能未联网或本地打开）');
  }
}

/* ------------------------------------------------------------------ */
/* 启动                                                                */
/* ------------------------------------------------------------------ */
/* 数据来源：优先用页面内嵌数据（单文件离线版），否则从 data/ 目录读取（网页版） */
async function loadData() {
  const embedded = window.__TCM_DATA__;
  if (embedded && embedded.herbs) return embedded;
  const [herbs, syn, imgs] = await Promise.all([
    fetch('data/herbs.json').then(r => r.json()),
    fetch('data/synonyms.json').then(r => r.json()).catch(() => []),
    fetch('data/images_manifest.json').then(r => r.json()).catch(() => ({}))
  ]);
  return { herbs, synonyms: syn, images: imgs };
}

async function boot() {
  try {
    const d = await loadData();
    const herbs = d.herbs, syn = d.synonyms, imgs = d.images;
    APP.herbs = herbs.herbs;
    APP.categories = herbs.meta.categories;
    APP.synonyms = syn || [];
    APP.imgMap = imgs || {};
    APP.version = herbs.meta.version || APP.version;
    buildIndex();
    restoreBrowse();          /* 恢复上次的筛选状态，避免错位/丢失 */
    renderCategoryChips();
    renderHerbList();
    applyCfgToUI();
    bindEvents();
    $('#loading').classList.add('hide');
    $('#app').classList.remove('hide');
    $('#verLabel').textContent = 'v' + APP.version;
    const sub = $('#subLine');
    if (sub) {
      sub.textContent = `题库 ${APP.herbs.length} 味 · ${APP.categories.length} 个分类 · 图片 ` +
        Object.values(APP.imgMap).reduce((s, a) => s + a.length, 0) + ' 张';
    }
    try { startClock(); } catch (e) { }
    try { renderRandomHerb(); } catch (e) { }
    try { sprinkleMotto(); bindGuessKeys(); } catch (e) { }
    try {
      const { tab: t0, arg: a0 } = tabFromHash();
      if (t0 !== 'browse' || a0) applyHash();
      window.addEventListener('hashchange', applyHash);
    } catch (e) { }
    if (location.protocol !== 'file:') checkUpdate(false);
  } catch (e) {
    $('#loading').innerHTML = '<div class="empty">数据加载失败：' + esc(e.message) +
      '<br>若你是直接双击打开本地文件，请改用「单文件离线版」（数据已内嵌），' +
      '或把本目录部署到静态托管后再访问。</div>';
  }
}

function bindEvents() {
  $$('.tab').forEach(b => b.onclick = () => switchTab(b.dataset.tab));
  /* 搜索框：输入即筛；有内容时显示 ✕ 清空按钮 */
  const search = $('#search'), clearBtn = $('#clearSearch');
  const syncClear = () => { if (clearBtn) clearBtn.classList.toggle('hide', !search.value); };
  search.oninput = () => { syncClear(); renderHerbList(); };
  search.onkeydown = e => { if (e.key === 'Escape') { search.value = ''; syncClear(); renderHerbList(); } };
  if (clearBtn) {
    clearBtn.onclick = () => {
      search.value = '';
      syncClear();
      renderHerbList();
      search.focus();
    };
  }
  syncClear();
  /* 分类区收起/展开（减少杂乱） */
  const catToggle = $('#catToggle'), catWrap = $('#catWrap');
  if (catToggle && catWrap) {
    let closed = LS.get('catClosed', false);
    const applyClosed = () => {
      catWrap.classList.toggle('hide', !!closed);
      catToggle.textContent = closed ? '展开' : '收起';
    };
    applyClosed();
    catToggle.onclick = () => {
      closed = !closed;
      LS.set('catClosed', closed);
      applyClosed();
    };
  }
  $('#onlyWrong').onchange = renderHerbList;
  ['n1', 'n2', 'n3', 'n4', 'minutes', 'immediate', 'mode'].forEach(id => {
    $('#' + id).oninput = updateTotal;
    $('#' + id).onchange = updateTotal;
  });
  $('#cats').onchange = updateTotal;
  $('#startBtn').onclick = startQuiz;
  $('#randomBtn').onclick = () => {
    const presets = [
      { n1: 10, n2: 4, n3: 10, n4: 10 },
      { n1: 12, n2: 4, n3: 11, n4: 10 },
      { n1: 8, n2: 5, n3: 10, n4: 10 },
      { n1: 14, n2: 4, n3: 7, n4: 10 },
      { n1: 10, n2: 6, n3: 10, n4: 6 }
    ];
    let p = pick(presets);
    for (let i = 0; i < 60; i++) {
      if (p.n1 * 3 + p.n2 * 5 + p.n3 * 2 + p.n4 * 3 === 100) break;
      p = pick(presets);
    }
    $('#n1').value = p.n1; $('#n2').value = p.n2;
    $('#n3').value = p.n3; $('#n4').value = p.n4;
    updateTotal();
    startQuiz();
  };
  $('#resetQty').onclick = () => {
    $('#n1').value = 10; $('#n2').value = 4; $('#n3').value = 10; $('#n4').value = 10;
    $('#minutes').value = 30; updateTotal();
  };
  $('#confirmBtn').onclick = confirmCurrent;
  $('#prevBtn').onclick = () => go(-1);
  $('#nextBtn').onclick = () => go(1);
  $('#submitBtn').onclick = () => {
    const un = QUIZ.items.filter(it => !isAnswered(it)).length;
    let msg = `确定交卷评分吗？共 ${QUIZ.items.length} 题`;
    if (un) msg += `，其中 ${un} 题未作答（按 0 分计）`;
    if (confirm(msg + '。')) finishQuiz();
  };
  $('#quitBtn').onclick = () => {
    if (confirm('确定退出测试吗？本次成绩不会保存。')) {
      stopTimer();
      $('#quizPage').classList.add('hide');
      $('#setupPage').classList.remove('hide');
    }
  };
  $('#checkUpdateBtn').onclick = () => checkUpdate(true);
  /* 更新日志 */
  const clBtn = $('#changelogBtn'), clBox = $('#clModal'), clClose = $('#clClose');
  if (clBtn) clBtn.onclick = () => openChangelog();
  if (clClose) clClose.onclick = () => closeChangelog();
  if (clBox) clBox.onclick = e => { if (e.target === clBox) closeChangelog(); };
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && clBox && clBox.classList.contains('show')) closeChangelog();
  });
  $('#clearWrong').onclick = () => {
    if (confirm('确定清空错题本吗？')) { LS.set('wrong', {}); renderWrong(); toast('已清空'); }
  };
  $('#startWrong').onclick = () => {
    if (!Object.keys(LS.get('wrong', {})).length) { toast('错题本为空'); return; }
    $('#mode').value = 'wrong';
    $('#n1').value = 10; $('#n2').value = 4; $('#n3').value = 10; $('#n4').value = 10;
    $('#minutes').value = 20;
    updateTotal();
    switchTab('exam');
    startQuiz();
  };
  $('#exportWrong').onclick = exportWrong;
  $('#clearHist').onclick = () => {
    if (confirm('确定清空成绩记录吗？')) { LS.set('history', []); renderScores(); toast('已清空'); }
  };
  // 图片查看器
  $('#imgBox').onclick = e => {
    const fig = e.target.closest('.ph');
    if (!fig) return;
    openViewer(fig.dataset.name, fig.dataset.file);
  };
  $('#viewerClose').onclick = closeViewer;
  $('#viewerPrev').onclick = () => stepViewer(-1);
  $('#viewerNext').onclick = () => stepViewer(1);
  $('#viewerHide').onclick = hideViewerImage;
  $('#viewerRestore').onclick = restoreViewerImage;
  $('#viewer').onclick = e => { if (e.target.id === 'viewer') closeViewer(); };
  document.addEventListener('keydown', e => {
    if ($('#viewer').classList.contains('show')) {
      if (e.key === 'Escape') closeViewer();
      if (e.key === 'ArrowLeft') stepViewer(-1);
      if (e.key === 'ArrowRight') stepViewer(1);
      return;
    }
    if (QUIZ && !QUIZ.finished && !$('#quizPage').classList.contains('hide')) {
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'Enter' && QUIZ.cfg.immediate) confirmCurrent();
    }
  });
}

function exportWrong() {
  const wrong = LS.get('wrong', {});
  const names = Object.keys(wrong).sort((a, b) => wrong[b] - wrong[a]);
  if (!names.length) { toast('错题本为空'); return; }
  let txt = '中药学复习系统 · 错题本导出\n' + new Date().toLocaleString('zh-CN') + '\n' + '='.repeat(40) + '\n';
  names.forEach((n, i) => {
    const h = herbByName(n);
    if (!h) return;
    txt += `\n${i + 1}. ${h.n}（错 ${wrong[n]} 次）\n   分类：${h.c}\n   性味：${h.x}　归经：${h.m}\n` +
      `   功效：${h.f.join('；')}\n   用法：${h.u}\n   注意：${h.k}\n`;
  });
  const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '错题本_' + new Date().toISOString().slice(0, 10) + '.txt';
  a.click();
  URL.revokeObjectURL(a.href);
}

boot();
