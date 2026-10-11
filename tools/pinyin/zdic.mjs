// 批量抓取汉典词条，用于核对中药名读音。
// 用法: node tools/pinyin/zdic.mjs 射干 枳壳 罂粟壳 海蛤壳 大黄 白术
import fs from 'node:fs';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';
const out = [];
for (const w of process.argv.slice(2)) {
  const url = 'https://www.zdic.net/hans/' + encodeURIComponent(w);
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 20000);
    const r = await fetch(url, { headers: { 'user-agent': UA }, signal: ac.signal });
    clearTimeout(t);
    let txt = await r.text();
    txt = txt.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/[ \t\u00a0]+/g, ' ');
    const i = txt.indexOf('拼音');
    out.push('### ' + w + '  [' + r.status + ']\n' + txt.slice(i, i + 400).replace(/\s+/g, ' ').trim());
  } catch (e) {
    out.push('### ' + w + '  FAIL ' + e.message);
  }
}
fs.writeFileSync(process.argv[1].replace(/zdic\.mjs$/, 'zdic_words.txt'), out.join('\n\n'), 'utf8');
console.log('done ->', out.length, 'entries');
