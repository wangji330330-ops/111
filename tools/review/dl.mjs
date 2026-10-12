// 二进制下载（PDF 等），fetch.mjs 会把内容当 HTML 洗掉，不能用来下 PDF
// 用法: node tools/review/dl.mjs <url> <out-path>
import fs from 'node:fs';

const [, , url, out] = process.argv;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';
const ac = new AbortController();
const t = setTimeout(() => ac.abort(), 60000);
try {
  const r = await fetch(url, { headers: { 'user-agent': UA, referer: 'https://www.cmro.gov.hk/' }, signal: ac.signal });
  const buf = Buffer.from(await r.arrayBuffer());
  fs.writeFileSync(out, buf);
  console.log(r.status, (r.headers.get('content-type') || ''), buf.length, '->', out);
} catch (e) {
  console.error('DL FAIL', url, e.message);
  process.exitCode = 1;
} finally { clearTimeout(t); }
