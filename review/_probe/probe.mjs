// 探针：看看各来源能不能拿到「高清 + 无文字」的药材图
// 用法: node review/_probe/probe.mjs 黄芪
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';
const q = process.argv[2] || '黄芪';
const enc = encodeURIComponent(q);

async function get(url, headers = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), 20000);
  try {
    const r = await fetch(url, { headers: { 'user-agent': UA, ...headers }, signal: ac.signal });
    const buf = Buffer.from(await r.arrayBuffer());
    return { status: r.status, text: buf.toString('utf8'), len: buf.length };
  } catch (e) { return { status: -1, text: '', err: e.message }; }
  finally { clearTimeout(t); }
}

// 1) 360 图片 API：看是否带宽高
const so = await get(`https://image.so.com/j?q=${enc}%20%E9%A5%AE%E7%89%87&src=srp&sn=0&pn=10`,
  { referer: 'https://image.so.com/' });
console.log('=== 360 API status', so.status, 'len', so.len);
try {
  const j = JSON.parse(so.text);
  const l = j.list || [];
  console.log('items:', l.length);
  for (const it of l.slice(0, 6)) {
    console.log('  keys:', Object.keys(it).join(','));
    console.log(`   w=${it.width} h=${it.height} img=${String(it.img).slice(0, 70)}`);
    break;
  }
  console.log('  全部尺寸:', l.map(i => `${i.width}x${i.height}`).join(' '));
} catch (e) { console.log('  parse fail', e.message, so.text.slice(0, 200)); }

// 2) 抖音 / 快手 / 小红书 搜索结果页里有多少图片 URL
for (const [name, url] of [
  ['抖音', `https://www.douyin.com/search/${enc}`],
  ['快手', `https://www.kuaishou.com/search/video?searchKey=${enc}`],
  ['小红书', `https://www.xiaohongshu.com/search_result?keyword=${enc}`],
]) {
  const r = await get(url, { referer: 'https://www.baidu.com/' });
  const imgs = (r.text.match(/https?:\/\/[^"'\s\\]+?\.(?:jpe?g|png|webp)/gi) || []);
  console.log(`=== ${name} status=${r.status} len=${r.len} 图片URL=${imgs.length}`);
  imgs.slice(0, 4).forEach(u => console.log('   ', u.slice(0, 110)));
}
