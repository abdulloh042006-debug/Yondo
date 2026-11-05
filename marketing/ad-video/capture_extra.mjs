// Ad screen capture: real app (production build) + real FastAPI on SQLite with the e2e test doubles.
// Verified badges are removed before every shot (they come from the "always verified" double).
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { chromium } from 'playwright-core';

const OUT = process.env.OUT;
mkdirSync(OUT, { recursive: true });
const WEB = 'http://127.0.0.1:4173';
const FS = '/home/claude/fonttools/node_modules/@fontsource';
const FONT_CSS = [['fraunces', [500, 600]], ['outfit', [400, 500, 600]], ['newsreader', [500, 600]], ['manrope', [400, 500, 600, 700]]]
  .flatMap(([pkg, ws]) => ws.map((w) => readFileSync(`${FS}/${pkg}/${w}.css`, 'utf8').replace(/url\(\.\/files\//g, `url(https://fonts.gstatic.com/fs/${pkg}/`)))
  .join('\n');
async function fonts(ctx) {
  await ctx.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ contentType: 'text/css', body: FONT_CSS }));
  await ctx.route('https://fonts.gstatic.com/fs/**', (r) => {
    const [pkg, file] = new URL(r.request().url()).pathname.split('/').slice(2);
    r.fulfill({ contentType: 'font/woff2', body: readFileSync(`${FS}/${pkg}/files/${file}`) });
  });
}
const kids = [];
const start = (cmd, args, ready) => new Promise((res, rej) => {
  const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }); kids.push(p); let b = '';
  const on = (d) => { b += d; if (b.includes(ready)) res(p); };
  p.stdout.on('data', on); p.stderr.on('data', on);
  setTimeout(() => rej(new Error('timeout ' + cmd + b.slice(-300))), 60000);
});
const hideVerified = (page) => page.evaluate(() => {
  for (const el of document.querySelectorAll('.tag, span, small, p')) {
    if (el.children.length === 0 && /Shaxsi tasdiqlangan/.test(el.textContent)) el.remove();
  }
});
async function shot(page, name, opts = {}) {
  await page.waitForTimeout(1600);
  await hideVerified(page);
  await page.screenshot({ path: `${OUT}/${name}.png`, ...opts });
  console.log('shot', name);
}
async function login(page, phone) {
  await page.goto(`${WEB}/login`);
  await page.getByLabel('Telefon raqami').fill(phone);
  await page.getByRole('button', { name: 'Kod yuborish' }).click();
  const code = (await page.locator('b.mono').first().innerText()).trim();
  await page.getByLabel('Tasdiqlash kodi').fill(code);
  return code;
}
try {
  await start(process.env.YONDO_PY, ['e2e/.tmp/server_video.py', '8000', `e2e/.tmp/cap-${Date.now()}.db`], 'SEED_DONE');
  await new Promise((r) => setTimeout(r, 1500));
  await start('npx', ['vite', 'preview', '--port', '4173', '--host', '127.0.0.1'], '4173');
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const mk = (mobile, theme = process.env.THEME || 'yondo') => browser.newContext(mobile
    ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true, locale: 'uz-UZ' }
    : { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.5, locale: 'uz-UZ' }).then(async (c) => {
    await fonts(c);
    await c.addInitScript((t) => { try { localStorage.setItem('yondo.theme', t); } catch { /* */ } }, theme);
    return c;
  });

  for (const mobile of [true, false]) {
    const p = mobile ? 'm' : 'd';
    const c = await mk(mobile); const pg = await c.newPage();
    await pg.goto(`${WEB}/settings`); await pg.getByRole('heading', { name: 'Sozlamalar', level: 1 }).waitFor();
    await shot(pg, `${p}-settings`);
    await login(pg, '+998901110001');
    await pg.getByRole('button', { name: 'Kirish', exact: true }).click();
    await pg.waitForURL((u) => !u.pathname.startsWith('/login'));
    await pg.goto(`${WEB}/account`); await pg.getByRole('heading', { name: 'Hisobim' }).waitFor();
    await shot(pg, `${p}-account`);
    for (const [path, name] of [['/admin', 'admin-dashboard'], ['/admin/users', 'admin-users'], ['/admin/safety', 'admin-safety'], ['/admin/audit', 'admin-audit']]) {
      await pg.goto(`${WEB}${path}`); await pg.waitForTimeout(800); await shot(pg, `${p}-${name}`);
    }
    await c.close();
    const c2 = await mk(mobile); const p2 = await c2.newPage();
    await login(p2, '+998901110011');
    await p2.getByRole('button', { name: 'Kirish', exact: true }).click();
    await p2.waitForURL((u) => !u.pathname.startsWith('/login'));
    await p2.goto(`${WEB}/studio`); await p2.waitForTimeout(800); await shot(p2, `${p}-studio`);
    await c2.close();
  }
  await browser.close();
} catch (e) { console.error('ERR', e); process.exitCode = 1; } finally { for (const k of kids) k.kill(); setTimeout(() => process.exit(), 500); }
