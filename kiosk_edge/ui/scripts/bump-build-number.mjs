import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function formatTodayYYMMDD(date = new Date()) {
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yy}${mm}${dd}`;
}

function parseBuildNumber(value) {
  const text = String(value || '').trim();
  const m = /^(\d{6})\.(\d+)$/.exec(text);
  if (!m) return null;
  return { day: m[1], seq: Number.parseInt(m[2], 10) || 0 };
}

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgPath = path.resolve(here, '../package.json');
const raw = fs.readFileSync(pkgPath, 'utf8');
const pkg = JSON.parse(raw);

const today = formatTodayYYMMDD();
const current = parseBuildNumber(pkg.buildNumber);

let nextSeq = 1;
if (current && current.day === today) {
  nextSeq = current.seq + 1;
}

pkg.buildNumber = `${today}.${nextSeq}`;

fs.writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`, 'utf8');
console.log(`[build-number] ${pkg.buildNumber}`);
