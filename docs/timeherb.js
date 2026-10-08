/* =====================================================================
   中药学复习系统 · 网页版 · 时辰养生模块
   —— 北京时间 + 天干地支 + 十二时辰 + 脏腑当令 + 养生建议 + 中药材推荐
   ===================================================================== */
'use strict';

const GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
const ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
const SHENGXIAO = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪'];
const WUXING_ZHI = ['水', '土', '木', '木', '土', '火', '火', '土', '金', '金', '土', '水'];
const JIJIE = ['春', '春', '春', '春', '春', '夏', '夏', '夏', '秋', '秋', '秋', '冬'];

/* 十二时辰（序号 0 = 子时 23:00~01:00） */
const SHICHEN = [
  { n: '子时', t: '23:00–01:00', z: '胆', herb: ['酸枣仁', '龙胆', '柴胡'], tip: '胆经当令，宜入睡养胆。此时不睡最耗气，忌熬夜与夜宵。' },
  { n: '丑时', t: '01:00–03:00', z: '肝', herb: ['当归', '白芍', '菊花'], tip: '肝经当令，肝主藏血。熟睡才利于肝血归藏，忌生气、忌饮酒。' },
  { n: '寅时', t: '03:00–05:00', z: '肺', herb: ['黄芪', '百合', '川贝母'], tip: '肺经当令，气血由静转动。此时咳喘易发，睡好可润养肺气。' },
  { n: '卯时', t: '05:00–07:00', z: '大肠', herb: ['火麻仁', '决明子', '大黄'], tip: '大肠经当令，宜排浊。起床后喝杯温水、按时如厕，最利通便排毒。' },
  { n: '辰时', t: '07:00–09:00', z: '胃', herb: ['山楂', '麦芽', '陈皮'], tip: '胃经当令，是吃早饭的黄金时间。早餐宜温宜软，忌生冷空腹。' },
  { n: '巳时', t: '09:00–11:00', z: '脾', herb: ['白术', '茯苓', '党参'], tip: '脾经当令，脾主运化。此时精力最好，适合工作学习，忌久坐不动。' },
  { n: '午时', t: '11:00–13:00', z: '心', herb: ['酸枣仁', '龙眼肉', '柏子仁'], tip: '心经当令，阳气最盛。午饭七八分饱，小睡 20 分钟最养心神。' },
  { n: '未时', t: '13:00–15:00', z: '小肠', herb: ['木通', '车前子', '淡竹叶'], tip: '小肠经当令，主分清泌浊。多喝水助吸收，有利于营养输布。' },
  { n: '申时', t: '15:00–17:00', z: '膀胱', herb: ['茯苓', '泽泻', '滑石'], tip: '膀胱经当令，宜多喝水勤排尿。此时头脑清醒，适合背书与复习。' },
  { n: '酉时', t: '17:00–19:00', z: '肾', herb: ['熟地黄', '枸杞子', '山药'], tip: '肾经当令，肾藏精。晚餐宜清淡少盐，忌过劳与剧烈运动。' },
  { n: '戌时', t: '19:00–21:00', z: '心包', herb: ['丹参', '川芎', '郁金'], tip: '心包经当令，主护心。适合散步、听音乐、与家人聊天以畅情志。' },
  { n: '亥时', t: '21:00–23:00', z: '三焦', herb: ['柴胡', '栀子', '香附'], tip: '三焦经当令，宜静心安神。泡脚、放下手机，为入睡做准备。' }
];

/* 脏腑当令 → 一句“当令做什么” + 一味应季/应脏的药材（均取自题库） */
const ZANGFU_ADVICE = {
  '胆': { do: '按时入睡、别熬夜；保持决断，少纠结。', avoid: '忌夜宵、忌生闷气。' },
  '肝': { do: '熟睡养血；白天可伸筋、散步、远眺。', avoid: '忌动怒、忌过量饮酒。' },
  '肺': { do: '深长呼吸、开窗透气；注意颈背保暖。', avoid: '忌烟、忌干燥环境久留。' },
  '大肠': { do: '晨起温水利排便；多吃粗纤维。', avoid: '忌久忍便意、忌久坐。' },
  '胃': { do: '按时吃早餐，温软易消化。', avoid: '忌空腹生冷、忌暴饮暴食。' },
  '脾': { do: '专心用脑；饭后慢走助运化。', avoid: '忌思虑过度、忌甜腻过量。' },
  '心': { do: '午间小憩；心态平和。', avoid: '忌大喜大悲、忌过咸。' },
  '小肠': { do: '适量温水，助分清泌浊。', avoid: '忌冷饮急饮。' },
  '膀胱': { do: '多喝水、勤排尿；适合背书复习。', avoid: '忌憋尿。' },
  '肾': { do: '温水泡脚、早睡；腰腹保暖。', avoid: '忌熬夜、忌过劳、忌过咸。' },
  '心包': { do: '散步听乐，畅达情志。', avoid: '忌情绪激动、忌剧烈运动。' },
  '三焦': { do: '静心收神，泡脚助眠。', avoid: '忌睡前刷手机、忌浓茶咖啡。' }
};

/* ---------------- 干支 / 生肖 ---------------- */
function ganzhiYear(y) {
  const i = ((y - 4) % 60 + 60) % 60;
  return { gan: GAN[i % 10], zhi: ZHI[i % 12], sx: SHENGXIAO[i % 12], idx: i };
}
function ganzhiDay(date) {
  /* 以 1949-10-01 为甲子参考点（该日干支为甲子）的常用算法 */
  const base = Date.UTC(1949, 9, 1);
  const d = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
  const days = Math.floor((d - base) / 86400000);
  const i = ((days % 60) + 60) % 60;
  return { gan: GAN[i % 10], zhi: ZHI[i % 12], idx: i };
}
function ganzhiHour(zhiIdx, dayGanIdx) {
  const start = (dayGanIdx % 5) * 2;          // 甲己起甲子 …
  const i = (start + zhiIdx) % 10;
  return GAN[i];
}
function shichenIndex(date) {
  /* 23:00~00:59 = 子时(0)，01:00~02:59 = 丑时(1) … */
  const h = date.getHours();
  return Math.floor(((h + 1) % 24) / 2);
}

/* ---------------- 北京时间 ---------------- */
function beijingNow() {
  /* 用 UTC 偏移强制取北京时间（UTC+8），不受本机时区影响 */
  const now = new Date();
  const bj = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + 8 * 3600000);
  return bj;
}

/* ---------------- 渲染 ---------------- */
function renderClock() {
  const box = document.getElementById('clockBox');
  if (!box) return;
  const d = beijingNow();
  const y = d.getFullYear();
  const gz = ganzhiYear(y);
  const day = ganzhiDay(d);
  const si = shichenIndex(d);
  const sc = SHICHEN[si];
  const hourGan = ganzhiHour(si, day.idx % 10);
  const adv = ZANGFU_ADVICE[sc.z] || { do: '', avoid: '' };

  const pad = n => String(n).padStart(2, '0');
  const week = '日一二三四五六'[d.getDay()];

  const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  const dateStr = `${y}年${d.getMonth() + 1}月${d.getDate()}日 星期${week}`;

  /* 已过时辰的进度条：本时辰内的时间占比 */
  const mins = d.getHours() * 60 + d.getMinutes();
  const startMin = (si * 2 + 23) % 24 * 60;               // 该时辰起点（子时 = 23:00）
  let passed = ((mins - startMin) % 1440 + 1440) % 1440;
  if (passed > 120) passed = 120;                          // 兜底
  const pct = Math.round(passed / 120 * 100);

  box.innerHTML = `
    <div class="clock-main">
      <div class="clock-time">${timeStr}</div>
      <div class="clock-date">${dateStr}　北京时间</div>
      <div class="clock-gz">
        <span class="gz-item"><b>${gz.gan}${gz.zhi}</b>年 · ${gz.sx}</span>
        <span class="gz-item"><b>${day.gan}${day.zhi}</b>日</span>
        <span class="gz-item"><b>${hourGan}${sc.n.charAt(0)}</b>时 · ${sc.n}</span>
      </div>
    </div>
    <div class="clock-side">
      <div class="sc-head"><span class="sc-name">${sc.n}</span>
        <span class="sc-range">${sc.t}</span>
        <span class="sc-organ">${sc.z}当令</span></div>
      <div class="sc-bar"><i style="width:${pct}%"></i></div>
      <div class="sc-tip">${sc.tip}</div>
      <div class="sc-advice">
        <span class="adv-do">宜：${adv.do}</span>
        <span class="adv-avoid">忌：${adv.avoid}</span>
      </div>
      <div class="sc-herbs">推荐参考：${sc.herb.map(h =>
        `<button class="herb-chip" data-herb="${h}">${h}</button>`).join('')}</div>
      <div class="sc-note">※ 以上为中医时辰养生的科普内容，仅供学习参考，不作为诊疗依据；用药请遵医嘱。</div>
    </div>`;

  /* 点击药材名 → 跳到速查 */
  box.querySelectorAll('.herb-chip').forEach(b => {
    b.onclick = () => gotoHerb(b.dataset.herb);
  });
}

function gotoHerb(name) {
  switchTab('browse');
  const s = document.getElementById('search');
  if (s) s.value = name;
  browseCat = '';
  document.querySelectorAll('#catChips .chip').forEach(c =>
    c.classList.toggle('active', c.dataset.cat === ''));
  renderHerbList();
  showHerb(name);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

let clockTimer = null;
function startClock() {
  if (clockTimer) return;
  renderClock();
  clockTimer = setInterval(renderClock, 1000);
}

/* =====================================================================
   随机中药：每次点“换一味”随机抽一味，可加入/查看详情
   ===================================================================== */
let RANDOM_CURRENT = null;

function randomHerb() {
  const list = APP.herbs;
  if (!list || !list.length) return null;
  let h = list[Math.floor(Math.random() * list.length)];
  let guard = 0;
  while (RANDOM_CURRENT && h.n === RANDOM_CURRENT.n && guard++ < 20) {
    h = list[Math.floor(Math.random() * list.length)];
  }
  RANDOM_CURRENT = h;
  return h;
}

function renderRandomHerb() {
  const box = document.getElementById('randBox');
  if (!box) return;
  const h = randomHerb();
  if (!h) { box.innerHTML = '<div class="empty">题库未加载</div>'; return; }

  const files = (APP.imgMap[h.n] || []).filter(f => !LS.get('hidden', []).includes(h.n + '|' + f));
  const img = files.length
    ? `<img src="images/${encodeURIComponent(files[0])}" alt="${esc(h.n)}" loading="lazy"
         data-name="${esc(h.n)}" data-file="${esc(files[0])}" class="rand-img">`
    : '<div class="rand-noimg">暂无图片</div>';

  box.innerHTML = `
    <div class="rand-card">
      <div class="rand-left">
        ${img}
        <div class="rand-tag">${esc(h.c.split('·')[0])}</div>
      </div>
      <div class="rand-right">
        <h2 class="rand-name">${esc(h.n)}</h2>
        <dl>
          <dt>分类</dt><dd>${esc(h.c)}</dd>
          <dt>性味</dt><dd>${esc(h.x)}</dd>
          <dt>归经</dt><dd>${esc(h.m)}</dd>
          <dt>功效</dt><dd class="fx">${esc(h.f.join('；'))}</dd>
          <dt>用法</dt><dd>${esc(h.u)}</dd>
          <dt>注意</dt><dd>${esc(h.k)}</dd>
        </dl>
      </div>
    </div>
    <div class="rand-actions">
      <button class="btn primary" id="randAgain">🔁 换一味</button>
      <button class="btn" id="randBrowse">在速查中查看</button>
      <span class="rand-hint">题库共 ${APP.herbs.length} 味，已随机抽取 ${(RANDOM_CURRENT && RANDOM_CURRENT._count) || ''}</span>
    </div>`;

  const imgEl = box.querySelector('.rand-img');
  if (imgEl) imgEl.onclick = () => openViewer(imgEl.dataset.name, imgEl.dataset.file);
  const again = box.querySelector('#randAgain');
  if (again) again.onclick = () => renderRandomHerb();
  const br = box.querySelector('#randBrowse');
  if (br) br.onclick = () => gotoHerb(h.n);
}
