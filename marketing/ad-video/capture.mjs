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
    for (const theme of [process.env.THEME || 'yondo']) {
      const c = await mk(mobile, theme); const pg = await c.newPage();
      await pg.goto(WEB); await pg.getByText('Madina').first().waitFor();
      await shot(pg, `${p}-discovery`);
      { await pg.evaluate(() => window.scrollTo(0, 520)); await shot(pg, `${p}-discovery-scrolled`); }
      await c.close();
    }
    const c = await mk(mobile); const pg = await c.newPage();
    // login (code step)
    await login(pg, '+998901110003');
    await shot(pg, `${p}-login-code`);
    await pg.getByRole('button', { name: 'Kirish', exact: true }).click();
    await pg.waitForURL((u) => !u.pathname.startsWith('/login'));
    // profile
    await pg.goto(WEB); await pg.getByRole('link', { name: /Madina profilini ochish/ }).click();
    await pg.getByRole('heading', { name: 'Madina', level: 1 }).waitFor();
    await shot(pg, `${p}-profile`);
    await pg.getByText('Xizmatlar va narxlar').first().scrollIntoViewIfNeeded(); await pg.evaluate(() => window.scrollBy(0, -90));
    await shot(pg, `${p}-profile-services`);
    await pg.evaluate(() => window.scrollTo(0, 0));
    // booking dialog filled
    await pg.getByRole('button', { name: 'Bron qilish' }).first().click();
    // server_video.py seeds Madina's availability on day+2 (UTC date) 09:00-16:00 Tashkent, with a booking at 10:00
    const day = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10);
    await pg.getByLabel('Boshlanish vaqti (Toshkent vaqti)').fill(`${day}T${mobile ? '12' : '14'}:00`);
    await pg.getByLabel('Uchrashuv joyi').fill('Amir Temur xiyoboni, kafe');
    await shot(pg, `${p}-booking-dialog`);
    await pg.getByRole('button', { name: 'So‘rov yuborish' }).click();
    await pg.waitForURL(/\/bookings/); await pg.getByText('Javob kutilmoqda').first().waitFor();
    await shot(pg, `${p}-bookings`);
    await c.close();
  }
  // admin (desktop + mobile)
  for (const mobile of [false, true]) {
    const p = mobile ? 'm' : 'd';
    const c = await mk(mobile); const pg = await c.newPage();
    await login(pg, '+998901110001');
    await pg.getByRole('button', { name: 'Kirish', exact: true }).click();
    await pg.waitForURL((u) => !u.pathname.startsWith('/login'));
    await pg.goto(`${WEB}/admin/applications`); await pg.getByText('Sevara').first().waitFor();
    await shot(pg, `${p}-admin-queue`);
    await pg.getByText('Sevara').first().click();
    await pg.getByRole('button', { name: 'Arizani tasdiqlash' }).waitFor();
    await shot(pg, `${p}-admin-detail`);
    await pg.getByRole('button', { name: 'Arizani tasdiqlash' }).click();
    await shot(pg, `${p}-admin-confirm`);
    await c.close();
  }
  await browser.close();
} catch (e) { console.error('ERR', e); process.exitCode = 1; } finally { for (const k of kids) k.kill(); setTimeout(() => process.exit(), 500); }
