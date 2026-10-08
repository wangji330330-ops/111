/* 网页版功能自测：模拟浏览器环境，验证出题与判分（站点目录：docs/）
   用法： node tools/webtest.js   （在项目根目录执行） */
const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'docs');

const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};
global.document = {
  querySelector: () => null, querySelectorAll: () => [],
  addEventListener: () => { },
  createElement: () => ({ style: {}, classList: { add() { }, remove() { } }, appendChild() { } })
};
global.window = { scrollTo() { } };
global.location = { protocol: 'https:', reload() { } };
global.fetch = () => Promise.reject(new Error('offline'));
global.setInterval = () => 0; global.clearInterval = () => { };
global.setTimeout = () => 0; global.clearTimeout = () => { };
global.alert = () => { }; global.confirm = () => true;

let src = fs.readFileSync(path.join(web, 'app.js'), 'utf8').replace(/\nboot\(\);\s*$/, '\n');
src += '\nmodule.exports = { APP, Engine, scoreOf, isCorrect, norm, typeName, POINTS, buildIndex };';
const m = { exports: {} };
new Function('module', 'exports', src)(m, m.exports || {});
const L = m.exports;

const herbs = JSON.parse(fs.readFileSync(path.join(web, 'data/herbs.json'), 'utf8'));
L.APP.herbs = herbs.herbs;
L.APP.categories = herbs.meta.categories;
L.APP.synonyms = JSON.parse(fs.readFileSync(path.join(web, 'data/synonyms.json'), 'utf8'));
L.buildIndex();

const cfgs = [];
for (const v of [[10, 4, 10], [20, 8, 0], [0, 0, 20], [12, 4, 5], [14, 4, 9]]) {
  const rest = 100 - (v[0] * 3 + v[1] * 5 + v[2] * 2);
  if (rest >= 0 && rest % 3 === 0) cfgs.push({ n1: v[0], n2: v[1], n3: v[2], n4: rest / 3 });
}

let problems = 0, totalItems = 0;
const typeCount = {}, badDetail = [];
const mark = msg => { problems++; if (badDetail.length < 8) badDetail.push(msg); };

for (let round = 1; round <= 40; round++) {
  const cfg = Object.assign({ minutes: 30, immediate: false, mode: 'random', cats: [] },
    cfgs[round % cfgs.length]);
  if (round % 5 === 0) {
    cfg.cats = [L.APP.categories[round % L.APP.categories.length],
    L.APP.categories[(round + 7) % L.APP.categories.length]];
  }
  if (cfg.n1 * 3 + cfg.n2 * 5 + cfg.n3 * 2 + cfg.n4 * 3 !== 100) mark('方案分错');
  const items = new L.Engine(cfg).build(cfg);
  totalItems += items.length;
  const seen = new Set();
  for (const it of items) {
    const key = it.type + '|' + it.q;
    if (seen.has(key)) mark('重复题干'); else seen.add(key);
    typeCount[L.typeName(it.type)] = (typeCount[L.typeName(it.type)] || 0) + 1;
    if (it.points <= 0) mark('分值0');
    if (it.type === 'single' || it.type === 'judge') {
      if (!it.options || it.options.length < 2) mark('选项过少');
      else if (it.answer < 0 || it.answer >= it.options.length) mark('答案越界');
    }
    if (it.type === 'single') {
      let mm = it.q.match(/^具有「(.+?)」功效的药物是：$/);
      if (mm) {
        const fx = mm[1];
        const own = L.APP.herbs.filter(h => h.f.some(f => L.norm(f) === L.norm(fx)));
        if (own.length !== 1) mark('功效非唯一 ' + fx);
        it.options.forEach((o, i) => {
          const h = L.APP.herbs.find(x => x.n === o);
          if (!h) { mark('选项非药名'); return; }
          const has = h.f.some(f => L.norm(f) === L.norm(fx));
          if (i === it.answer && !has) mark('正确项无此功效');
          if (i !== it.answer && has) mark('干扰项也有此功效');
        });
      }
      mm = it.q.match(/^「(.+?)」的功效是：$/);
      if (mm) {
        const h = L.APP.herbs.find(x => x.n === mm[1]);
        if (!h) mark('找不到药');
        else {
          if (!h.f.some(f => L.norm(f) === L.norm(it.options[it.answer]))) mark('答案非其功效');
          it.options.forEach((o, i) => {
            if (i !== it.answer && h.f.some(f => L.norm(f) === L.norm(o))) mark('干扰项是其功效');
          });
        }
      }
      mm = it.q.match(/^下列哪一项不是「(.+?)」的功效？$/);
      if (mm) {
        const h = L.APP.herbs.find(x => x.n === mm[1]);
        if (!h) mark('找不到药');
        else {
          let fake = 0;
          it.options.forEach((o, i) => {
            const has = h.f.some(f => L.norm(f) === L.norm(o));
            if (i === it.answer) { if (has) mark('正确项其实是它的功效'); else fake++; }
            else if (!has) mark('干扰项不是它的功效');
          });
          if (fake !== 1) mark('假功效个数' + fake);
        }
      }
      mm = it.q.match(/^「(.+?)」的性味是：$/);
      if (mm) {
        const h = L.APP.herbs.find(x => x.n === mm[1]);
        if (!h || L.norm(h.x) !== L.norm(it.options[it.answer])) mark('性味答案错');
      }
      mm = it.q.match(/^「(.+?)」的归经是：$/);
      if (mm) {
        const h = L.APP.herbs.find(x => x.n === mm[1]);
        if (!h || L.norm(h.m) !== L.norm(it.options[it.answer])) mark('归经答案错');
      }
    } else if (it.type === 'multi') {
      if (it.answers.length < 2) mark('多选答案不足2');
      const mm = it.q.match(/^「(.+?)」的功效包括（多选）：$/);
      if (mm) {
        const h = L.APP.herbs.find(x => x.n === mm[1]);
        if (!h) mark('多选找不到药');
        else it.options.forEach((o, i) => {
          const has = h.f.some(f => L.norm(f) === L.norm(o));
          if (has !== it.answers.includes(i)) mark('多选答案不符');
        });
      }
    } else if (it.type === 'fill') {
      if (!it.answer || !String(it.answer).trim()) mark('填空答案空');
      if (!/＿|请填写/.test(it.q)) mark('填空题干缺空');
      const mm = it.q.match(/^具有「(.+?)」功效的药物是：/);
      if (mm) {
        const own = L.APP.herbs.filter(h => h.f.some(f => L.norm(f) === L.norm(mm[1])));
        if (own.length !== 1 || it.answer !== own[0].n) mark('填空答案错');
      }
    }
  }
}

let sp = 0;
for (const c of [['辛，温', '辛，温', true], ['辛温', '辛，温', true],
['发散风寒', '发汗解表', true], ['解表散风', '解表散风；透疹消疮', true],
['完全不同的答案XYZ', '利水渗湿', false]]) {
  if (L.isCorrect(c[0], c[1]) !== c[2]) { sp++; console.log('判分失败', c[0], c[1]); }
}
const fk = { type: 'multi', points: 5, answers: [0, 1, 2], options: ['a', 'b', 'c', 'd'] };
fk.picks = [0, 1, 2]; if (L.scoreOf(fk) !== 5) sp++;
fk.picks = [0, 1]; if (L.scoreOf(fk) !== 2.5) sp++;
fk.picks = [0, 3]; if (L.scoreOf(fk) !== 0) sp++;
const f1 = { type: 'fill', points: 3, answer: '辛，温' };
f1.input = '辛温'; if (L.scoreOf(f1) !== 3) sp++;
f1.input = '错误答案'; if (L.scoreOf(f1) !== 0) sp++;

console.log('药材:', L.APP.herbs.length, '分类:', L.APP.categories.length);
if (badDetail.length) console.log('问题样例:', badDetail.slice(0, 5));
console.log('出题总量:', totalItems, JSON.stringify(typeCount));
console.log('题目自洽问题:', problems, '判分用例问题:', sp);
console.log((problems === 0 && sp === 0) ? 'WEB SELFTEST PASS' : 'WEB SELFTEST FAIL');
process.exit(problems === 0 && sp === 0 ? 0 : 1);
