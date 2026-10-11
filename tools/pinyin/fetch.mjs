// 开发期小工具：抓取网页正文（用于核对中药读音的权威来源）。
// 用法: node tools/pinyin/fetch.mjs <url> [outfile]
import fs from 'node:fs';

const [, , url, out] = process.argv;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

const ac = new AbortController();
const t = setTimeout(() => ac.abort(), 25000);
try {
  const r = await fetch(url, { headers: { 'user-agent': UA, accept: '*/*' }, signal: ac.signal, redirect: 'follow' });
  const buf = Buffer.from(await r.arrayBuffer());
  let txt;
  const ct = r.headers.get('content-type') || '';
  if (/gb2312|gbk|gb18030/i.test(ct)) {
    txt = new TextDecoder('gb18030').decode(buf);
  } else {
    txt = buf.toString('utf8');
  }
  const text = txt.replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/[ \t\u00a0]+/g, ' ')
    .replace(/\n{2,}/g, '\n');
  if (out) { fs.writeFileSync(out, text, 'utf8'); console.log(r.status, ct, '->', out, text.length); }
  else console.log(r.status, ct, '\n---\n' + text.slice(0, 3000));
} catch (e) {
  console.error('FETCH FAIL', url, e.message);
  process.exitCode = 1;
} finally { clearTimeout(t); }
