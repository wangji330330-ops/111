// 用 pinyin-pro 生成第二份拼音，作为 pypinyin 的交叉校验（仅开发期使用，运行时不需要）。
// 用法: node tools/pinyin/node_gen.mjs <herbs.json> <out.json>
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let pinyin = null;
for (const spec of ['pinyin-pro', '../_pytmp/node_modules/pinyin-pro', '../../_pytmp/node_modules/pinyin-pro']) {
  try { ({ pinyin } = require(spec)); break; } catch (e) { /* 继续尝试下一个位置 */ }
}
if (!pinyin) {
  console.error('找不到 pinyin-pro，请先安装：pnpm add pinyin-pro（可在项目根 _pytmp 目录内）');
  process.exit(2);
}

const [, , src, dst] = process.argv;
const data = JSON.parse(fs.readFileSync(src, 'utf8'));

/** 保留声调符号，逐字返回 */
const py = name => pinyin(name, { toneType: 'symbol', type: 'array', nonZh: 'consecutive' });

const out = {};
for (const h of data.herbs) out[h.name] = py(h.name).join(' ');

/** 每个字的全部读音（用于人工裁定多音字） */
const alt = {};
for (const h of data.herbs) {
  for (const ch of h.name) {
    if (alt[ch]) continue;
    alt[ch] = pinyin(ch, { toneType: 'symbol', type: 'array', multiple: true });
  }
}

fs.writeFileSync(dst, JSON.stringify(out, null, 0), 'utf8');
fs.writeFileSync(dst.replace(/\.json$/, '_alt.json'), JSON.stringify(alt, null, 0), 'utf8');
console.log('pinyin-pro wrote', Object.keys(out).length, 'entries ->', dst);
