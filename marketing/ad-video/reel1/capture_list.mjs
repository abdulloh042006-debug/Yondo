// Extra shots for reel 1: the companion list cards (mobile, yondo theme). Run from apps/web after capture.mjs setup:
//   OUT=<dir> YONDO_PY=<venv python> PHOTOS_DIR=<repo>/marketing/ad-video/photos node e2e/.tmp/capture_list.mjs
import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { chromium } from 'playwright-core';
const OUT = process.env.OUT; const WEB = 'http://127.0.0.1:4173';
// APP_LANG=ru: the app's own Russian locale (top-bar switch) + ru-dict.json for seed data (names, cities, interests)
const RU = process.env.APP_LANG === 'ru';
const DICT_PATH = process.env.RU_DICT || new URL('./ru-dict.json', import.meta.url).pathname;
const DICT = RU && existsSync(DICT_PATH) ? JSON.parse(readFileSync(DICT_PATH, 'utf8')) : { exact: {}, sub: [] };
const FS = '/home/claude/fonttools/node_modules/@fontsource';
const FONT_CSS = [['manrope', [400, 500, 600, 700]], ['fraunces', [500, 600]], ['outfit', [400, 500, 600]]]
  .flatMap(([p, ws]) => ws.map((w) => readFileSync(`${FS}/${p}/${w}.css`, 'utf8').replace(/url\(\.\/files\//g, `url(https://fonts.gstatic.com/fs/${p}/`))).join('\n');
const kids = [];
const start = (cmd, args, ready) => new Promise((res, rej) => {
  const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }); kids.push(p); let b = '';
  const on = (d) => { b += d; if (b.includes(ready)) res(p); }; p.stdout.on('data', on); p.stderr.on('data', on);
  setTimeout(() => rej(new Error('timeout ' + b.slice(-300))), 60000);
});
try {
  await start(process.env.YONDO_PY, ['e2e/.tmp/server_video.py', '8000', `e2e/.tmp/cl-${Date.now()}.db`], 'SEED_DONE');
  await start('npx', ['vite', 'preview', '--port', '4173', '--host', '127.0.0.1'], '4173');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const c = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true, locale: RU ? 'ru-RU' : 'uz-UZ' });
  await c.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ contentType: 'text/css', body: FONT_CSS }));
  await c.route('https://fonts.gstatic.com/fs/**', (r) => { const [p, f] = new URL(r.request().url()).pathname.split('/').slice(2); r.fulfill({ contentType: 'font/woff2', body: readFileSync(`${FS}/${p}/files/${f}`) }); });
  await c.addInitScript(() => { try { localStorage.setItem('yondo.theme', 'yondo'); } catch { /* */ } });
  const pg = await c.newPage(); await pg.goto(WEB); await pg.getByText('Madina').first().waitFor();
  await pg.waitForTimeout(1500);
  if (RU) { await pg.evaluate(() => { const b = [...document.querySelectorAll('.lang-switch button')].find((e) => (e.getAttribute('aria-label') || e.textContent || '').toUpperCase().startsWith('RU')); if (b) b.click(); }); await pg.waitForTimeout(900); }
  const toRu = () => pg.evaluate((D) => { const subs = [...D.sub].sort((a, b) => b[0].length - a[0].length); const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) { const k = n.nodeValue.trim(); if (!k) continue; let o = D.exact[k]; if (o === undefined) { o = k; for (const [a, b] of subs) o = o.split(a).join(b); } if (o !== k) n.nodeValue = n.nodeValue.replace(k, o); } }, DICT);
  const hide = () => pg.evaluate(() => { for (const el of document.querySelectorAll('span, small, p, .tag')) if (!el.children.length && /tasdiqlangan|подтвержд/i.test(el.textContent)) el.style.visibility = 'hidden'; });
  for (const [i, name] of [[0, 'm-list-1'], [1, 'm-list-2'], [2, 'm-list-3']]) {
    await pg.evaluate((k) => { document.documentElement.style.scrollBehavior = 'auto';
      const a = [...document.querySelectorAll('a')].filter((x) => /profilini ochish|профил/i.test(x.getAttribute('aria-label') || x.textContent));
      const el = a[k] || a[a.length - 1]; const card = el.closest('article, li') || el;
      window.scrollTo({ top: card.getBoundingClientRect().top + scrollY - 90, behavior: 'instant' }); }, i);
    if (RU) await toRu(); await hide(); await pg.waitForTimeout(400); await pg.screenshot({ path: `${OUT}/${name}.png` }); console.log('shot', name);
  }
  await b.close();
} catch (e) { console.error('ERR', e); process.exitCode = 1; } finally { for (const k of kids) k.kill(); setTimeout(() => process.exit(), 500); }
