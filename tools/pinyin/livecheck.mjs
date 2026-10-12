// 发布后校验：把线上文件与本地文件做（行尾归一化后的）逐字节比对，并抽查关键内容。
// 用法: node tools/pinyin/livecheck.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(HERE));
const BASE = (process.argv[2] || 'https://wangji330330-ops.github.io/111/').replace(/\/?$/, '/');

const files = [
  'index.html', 'app.js', 'style2.css', 'changelog.js', 'encourage.js',
  'timeherb.js', 'version.json', 'data/herbs.json'
];

const norm = b => Buffer.from(b.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
const md5 = b => crypto.createHash('md5').update(b).digest('hex');

let bad = 0;
for (const f of files) {
  const local = norm(fs.readFileSync(path.join(ROOT, 'docs', f)));
  let remote = null;
  try {
    const r = await fetch(BASE + f + '?_=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) { console.log(`  ✗ ${f}: HTTP ${r.status}`); bad++; continue; }
    remote = norm(Buffer.from(await r.arrayBuffer()));
  } catch (e) { console.log(`  ✗ ${f}: ${e.message}`); bad++; continue; }
  const same = md5(local) === md5(remote) ? '一致' : '不一致';
  if (same !== '一致') bad++;
  console.log(`  ${same === '一致' ? '✓' : '✗'} ${f.padEnd(18)} 本地 ${local.length} B / 线上 ${remote.length} B  ${same}`);
}

// 关键内容抽查（线上）
const checks = [
  ['data/herbs.json', '"p": "Má Huáng"'],
  ['app.js', 'pyKey'],
  ['style2.css', '.row-py'],
  ['index.html', '搜索药名 / 别名 / 拼音'],
  ['data/herbs.json', '"a": "川军、川锦纹"']
];
for (const [f, needle] of checks) {
  const r = await fetch(BASE + f + '?_=' + Date.now(), { cache: 'no-store' });
  const t = await r.text();
  const okk = t.includes(needle);
  if (!okk) bad++;
  console.log(`  ${okk ? '✓' : '✗'} ${f} 含 ${JSON.stringify(needle)}`);
}
const v = await (await fetch(BASE + 'version.json?_=' + Date.now(), { cache: 'no-store' })).json();
const CUR = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs', 'version.json'), 'utf8')).version;
const vok = v.version === CUR;
if (!vok) bad++;
console.log(`  ${vok ? '✓' : '✗'} 线上版本 = ${v.version}`);

console.log('');
console.log(bad ? `LIVE CHECK FAIL - ${bad} 项不一致` : 'LIVE CHECK PASS');
process.exit(bad ? 1 : 0);
