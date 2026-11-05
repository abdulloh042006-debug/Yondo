// Renders photos/*.svg to 1080x1350 JPEGs (used by server_video.py PHOTOS_DIR seed upload).
import { readdirSync } from 'node:fs';
import { chromium } from '/home/claude/fonttools/node_modules/playwright-core/index.mjs';
const dir = new URL('./photos/', import.meta.url).pathname;
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
for (const f of readdirSync(dir).filter((x) => x.endsWith('.svg'))) {
  await p.goto('file://' + dir + f);
  await p.screenshot({ path: dir + f.replace('.svg', '.jpg'), type: 'jpeg', quality: 90 });
  console.log('jpg', f);
}
await b.close();
