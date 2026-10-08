/* =====================================================================
   中药学复习系统 · 网页版 · 看图猜药 + 鼓励语
   —— 看图识药（四选一）、答对答错都显示答案、鼓励与勉励的话
   ===================================================================== */
'use strict';

/* ---------------- 鼓励 / 勉励语料 ---------------- */
const PRAISE = [
  '认得一味是一味，日积月累自成良医。',
  '妙！这一味你已经记住了。',
  '眼力不错，识药如识人，越看越准。',
  '对了！基础就是这样一味一味垒起来的。',
  '很好，舌耕不如目耕，你已经在进步了。',
  '这一分稳了 —— 继续下一味。',
  '熟能生巧，巧从熟来。',
  '记性靠重复，你已经重复得很好。',
  '答得漂亮！药性入眼，方能入心。',
  '不错的判断力，保持这个节奏。'
];

const ENCOURAGE = [
  '别急，认错一味不等于学不会。',
  '错了正好，说明这一味是今天最该记住的。',
  '温故而知新，看一眼答案就赚到了。',
  '记住形色，下次一定认得出。',
  '错题是宝，肯回头的人进步最快。',
  '不要灰心，张仲景也是一味一味背下来的。',
  '把这一味写下来，明天再来考它。',
  '这一味记住了，就少一个坑。',
  '慢就是快，认药最怕跳着学。',
  '再来一次，你离答对只差一点。'
];

const MOTTO = [
  '博极医源，精勤不倦。 —— 《备急千金要方》',
  '读方三年，便谓天下无病可治；治病三年，乃知天下无方可用。 —— 孙思邈',
  '勤求古训，博采众方。 —— 张仲景《伤寒杂病论·序》',
  '学医之道，不可不慎。 —— 《医学源流论》',
  '药有个性之专长，方有合群之妙用。 —— 徐大椿',
  '不明药性，焉能治病。 —— 本草名言',
  '凡欲为大医，必须谙《素问》《甲乙》《黄帝针经》…… —— 孙思邈',
  '纸上得来终觉浅，绝知此事要躬行。 —— 陆游',
  '积土成山，风雨兴焉；积水成渊，蛟龙生焉。 —— 《荀子·劝学》',
  '锲而不舍，金石可镂。 —— 《荀子·劝学》',
  '学而不思则罔，思而不学则殆。 —— 《论语》',
  '医者仁心，学无止境。',
  '温故而知新，可以为师矣。 —— 《论语》',
  '一日一钱，千日千钱；绳锯木断，水滴石穿。 —— 《汉书》',
  '不积跬步，无以至千里。 —— 《荀子·劝学》'
];

function pickOne(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function praiseText() { return pickOne(PRAISE); }
function encourageText() { return pickOne(ENCOURAGE); }
function mottoText() { return pickOne(MOTTO); }

/* 把鼓励语撒在“细微处” */
function sprinkleMotto() {
  const el = document.getElementById('mottoLine');
  if (el) el.textContent = '「' + mottoText() + '」';
  const ft = document.getElementById('footMotto');
  if (ft) ft.textContent = mottoText();
}

/* ---------------- 看图猜药 ---------------- */
const GUESS_KEY = 'guessStats';
let GUESS = null;

function guessStats() {
  return LS.get(GUESS_KEY, { total: 0, right: 0, streak: 0, best: 0, masked: false });
}

function availableGuessImages() {
  const hidden = LS.get('hidden', []);
  const out = [];
  APP.herbs.forEach(h => {
    const files = (APP.imgMap[h.n] || []).filter(f => !hidden.includes(h.n + '|' + f));
    if (files.length) out.push({ herb: h, file: files[Math.floor(Math.random() * files.length)] });
  });
  return out;
}

function newGuessQuestion() {
  const pool = availableGuessImages();
  if (pool.length < 4) { GUESS = null; return; }
  const pick = pool[Math.floor(Math.random() * pool.length)];
  /* 干扰项：同分类优先（更难更贴切），不足则全库补 */
  const sameCat = pool.filter(p => p.herb.n !== pick.herb.n &&
    p.herb.c.split('·')[0] === pick.herb.c.split('·')[0]);
  const others = pool.filter(p => p.herb.n !== pick.herb.n);
  const distract = [];
  const src = sameCat.length >= 3 ? sameCat : others;
  const used = new Set([pick.herb.n]);
  while (distract.length < 3 && src.length) {
    const c = src[Math.floor(Math.random() * src.length)];
    if (used.has(c.herb.n)) continue;
    used.add(c.herb.n);
    distract.push(c.herb.n);
  }
  const options = [pick.herb.n, ...distract].sort(() => Math.random() - 0.5);
  GUESS = {
    answer: pick.herb.n,
    file: pick.file,
    options,
    picked: null,
    masked: guessStats().masked
  };
}

function renderGuess() {
  const box = document.getElementById('guessBox');
  if (!box) return;
  if (!APP.herbs.length) { box.innerHTML = '<div class="empty">题库未加载</div>'; return; }
  if (!GUESS) newGuessQuestion();
  if (!GUESS) { box.innerHTML = '<div class="empty">可用图片不足，无法出题</div>'; return; }

  const st = guessStats();
  const h = herbByName(GUESS.answer);
  const answered = GUESS.picked !== null;
  const right = answered && GUESS.picked === GUESS.answer;
  const rate = st.total ? Math.round(st.right / st.total * 100) : 0;
  const hideImg = GUESS.masked && !answered;

  box.innerHTML = `
    <div class="g-stat">
      <span class="g-chip">已答 <b>${st.total}</b></span>
      <span class="g-chip">答对 <b>${st.right}</b></span>
      <span class="g-chip">正确率 <b>${rate}%</b></span>
      <span class="g-chip">连对 <b>${st.streak}</b></span>
      <span class="g-chip">最高连对 <b>${st.best}</b></span>
      <button class="btn small" id="guessMask">${GUESS.masked ? '👁 显示图片' : '🙈 先遮住图片'}</button>
      <button class="btn small" id="guessReset">重置统计</button>
    </div>
    <div class="g-main">
      <div class="g-pic">
        ${hideImg
          ? `<div class="g-mask" id="guessUnmask">图片已遮住<br><span>点这里揭示图片</span></div>`
          : `<img src="images/${encodeURIComponent(GUESS.file)}" alt="看图猜药" id="guessImg"
                 class="${answered ? 'zoomable' : ''}">`}
      </div>
      <div class="g-side">
        <div class="g-q">这张图是哪一味中药？</div>
        <div class="g-options">
          ${GUESS.options.map(n => {
            let cls = 'g-opt';
            if (answered) {
              if (n === GUESS.answer) cls += ' right';
              else if (n === GUESS.picked) cls += ' wrong';
            }
            return `<button class="${cls}" data-n="${esc(n)}"${answered ? ' disabled' : ''}>${esc(n)}</button>`;
          }).join('')}
        </div>
        ${answered ? `
          <div class="g-fb ${right ? 'ok' : 'no'}">
            <div class="g-fb-head">${right ? '✅ 答对了！' : '❌ 答错了'}</div>
            <div class="g-fb-line">${right ? praiseText() : encourageText()}</div>
          </div>
          <div class="g-answer">
            <div class="g-ans-name">正确答案：<b>${esc(h.n)}</b>
              <span class="g-ans-cat">${esc(h.c)}</span></div>
            <dl class="g-dl">
              <dt>性味</dt><dd>${esc(h.x)}</dd>
              <dt>归经</dt><dd>${esc(h.m)}</dd>
              <dt>功效</dt><dd class="fx">${esc(h.f.join('；'))}</dd>
              <dt>用法</dt><dd>${esc(h.u)}</dd>
              <dt>注意</dt><dd>${esc(h.k)}</dd>
            </dl>
          </div>
          <div class="g-actions">
            <button class="btn primary" id="guessNext">下一味 →</button>
            <button class="btn" id="guessBrowse">在速查中查看</button>
          </div>` : `
          <div class="g-hint">看清形状、颜色、切面与质地 —— 先想一想，再选。</div>
        `}
      </div>
    </div>`;

  /* 交互 */
  box.querySelectorAll('.g-opt').forEach(b => {
    b.onclick = () => {
      if (GUESS.picked !== null) return;
      GUESS.picked = b.dataset.n;
      const st2 = guessStats();
      st2.total++;
      if (GUESS.picked === GUESS.answer) {
        st2.right++; st2.streak++;
        if (st2.streak > st2.best) st2.best = st2.streak;
        toast('✅ ' + praiseText());
      } else {
        st2.streak = 0;
        toast('💪 ' + encourageText());
      }
      LS.set(GUESS_KEY, st2);
      renderGuess();
    };
  });
  const nx = box.querySelector('#guessNext');
  if (nx) nx.onclick = () => { newGuessQuestion(); renderGuess(); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const bs = box.querySelector('#guessBrowse');
  if (bs) bs.onclick = () => gotoHerb(GUESS.answer);
  const mk = box.querySelector('#guessMask');
  if (mk) mk.onclick = () => {
    const st3 = guessStats(); st3.masked = !st3.masked; LS.set(GUESS_KEY, st3);
    if (GUESS) GUESS.masked = st3.masked;
    renderGuess();
  };
  const um = box.querySelector('#guessUnmask');
  if (um) um.onclick = () => {
    const st4 = guessStats(); st4.masked = false; LS.set(GUESS_KEY, st4);
    if (GUESS) GUESS.masked = false;
    renderGuess();
  };
  const rs = box.querySelector('#guessReset');
  if (rs) rs.onclick = () => {
    if (confirm('确定重置看图猜药的统计吗？')) {
      LS.set(GUESS_KEY, { total: 0, right: 0, streak: 0, best: 0, masked: false });
      renderGuess();
    }
  };
  const gi = box.querySelector('#guessImg');
  if (gi && answered) gi.onclick = () => openViewer(GUESS.answer, GUESS.file);
  const mp = box.querySelector('#mottoLine');
  if (mp) mp.textContent = '「' + mottoText() + '」';
}

/* 键盘快捷：1-4 选答案，回车下一味 */
function bindGuessKeys() {
  document.addEventListener('keydown', e => {
    const page = document.getElementById('page-guess');
    if (!page || !page.classList.contains('active') || !GUESS) return;
    if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
    if (/^[1-4]$/.test(e.key)) {
      const i = +e.key - 1;
      const btns = page.querySelectorAll('.g-opt');
      if (btns[i] && !btns[i].disabled) btns[i].click();
    } else if (e.key === 'Enter' && GUESS.picked !== null) {
      const nx = page.querySelector('#guessNext');
      if (nx) nx.click();
    }
  });
}
