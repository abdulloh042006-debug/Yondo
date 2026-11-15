/**
 * Evidence for the web ↔ mobile parity work: side-by-side screenshots (web left, mobile right) at 390×844 in the
 * Yondo day and night themes, against the REAL API with the video seed (marketing/ad-video/server_video.py, which
 * uploads the illustrated DEMO portraits through the photo API).
 *
 *   python marketing/ad-video/server_video.py 8775 <tmp.db>                     # API + DEMO photos
 *   node <proxy> 8776 <mobile web export> http://127.0.0.1:8775                  # mobile build, /api proxied
 *   node <proxy> 8777 apps/web/dist http://127.0.0.1:8775                        # web build, /api proxied
 *   MOBILE=http://127.0.0.1:8776 WEB=http://127.0.0.1:8777 OUT=<dir> node apps/mobile/e2e/parity.mjs
 *
 * Signed in as the DEMO customer (tokens from the development OTP, consent recorded through the API).
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const MOBILE = process.env.MOBILE ?? 'http://127.0.0.1:8776';
const WEB = process.env.WEB ?? 'http://127.0.0.1:8777';
const OUT = process.env.OUT ?? 'parity-out';
mkdirSync(OUT, { recursive: true });
const VERSIONS = { terms: '2026-10-23-draft', privacy: '2026-10-23-draft' };

async function post(path, body, token) {
  const r = await fetch(`${WEB}/api/v1${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.status === 204 ? null : r.json();
}
async function signIn(phone) {
  const otp = await post('/auth/otp/request', { phone_number: phone });
  const pair = await post('/auth/otp/verify', { phone_number: phone, code: otp.development_otp });
  for (const [document, version] of Object.entries(VERSIONS)) await post('/account/consents', { document, version }, pair.access_token);
  return pair;
}

const browser = await chromium.launch();
async function shoot(base, theme, pair, act, file) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, hasTouch: true, isMobile: true, colorScheme: theme === 'yondo-tun' ? 'dark' : 'light' });
  await ctx.addInitScript(([th, p]) => {
    localStorage.setItem('yondo.theme', th);
    if (p) {
      sessionStorage.setItem('yondo.access', p.access_token);
      sessionStorage.setItem('yondo.refresh', p.refresh_token);
    }
  }, [theme, pair]);
  const page = await ctx.newPage();
  await act(page, base);
  await page.waitForTimeout(900);
  await page.screenshot({ path: file, type: 'jpeg', quality: 82 });
  await ctx.close();
}

const pair = await signIn('+998901110003');
const tabM = (name) => async (page) => page.getByRole('tab', { name, exact: true }).click();
const screens = [
  ['discover', async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); }],
  ['companion', async (p, b) => { await p.goto(b); await p.getByRole('link', { name: /Madina/ }).first().click(); await p.getByText(/Xizmatlar|Services/).first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByRole('button', { name: /Madina/ }).first().click(); await p.getByText(/Xizmatlar|Services/).first().waitFor(); }],
  ['bookings', async (p, b) => { await p.goto(`${b}/bookings`); await p.getByRole('heading').first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); await tabM('Bronlar')(p); }],
  ['profile', async (p, b) => { await p.goto(`${b}/account`); await p.getByRole('heading').first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); await tabM('Profil')(p); }],
  ['settings', async (p, b) => { await p.goto(`${b}/settings`); await p.getByRole('heading').first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); await tabM('Profil')(p); await p.getByRole('button', { name: /^Sozlamalar\./ }).click(); }],
  ['notifications', async (p, b) => { await p.goto(`${b}/notifications`); await p.getByRole('heading').first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); await tabM('Profil')(p); await p.getByRole('button', { name: /^Sozlamalar\./ }).click(); await p.getByRole('button', { name: /^Bildirishnomalar\./ }).click(); }],
  ['help', async (p, b) => { await p.goto(`${b}/help`); await p.getByRole('heading').first().waitFor(); }, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); await tabM('Profil')(p); await p.getByRole('button', { name: /^Sozlamalar\./ }).click(); await p.getByRole('button', { name: /^Yordam va xavfsizlik\./ }).click(); }],
];
const pairs = [];
for (const theme of ['yondo', 'yondo-tun']) {
  for (const [name, web, mob] of screens) {
    const w = `${OUT}/${name}-${theme}-web.jpg`;
    const m = `${OUT}/${name}-${theme}-mobile.jpg`;
    await shoot(WEB, theme, pair, web, w);
    await shoot(MOBILE, theme, pair, mob, m);
    pairs.push([`${name}-${theme}`, w, m]);
  }
}
// Signed out: the dock is Kashf · Kirish on both.
for (const theme of ['yondo']) {
  const w = `${OUT}/signed-out-${theme}-web.jpg`;
  const m = `${OUT}/signed-out-${theme}-mobile.jpg`;
  await shoot(WEB, theme, null, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); }, w);
  await shoot(MOBILE, theme, null, async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); }, m);
  pairs.push([`signed-out-${theme}`, w, m]);
}

// Side-by-side composites (web | mobile).
const page = await browser.newPage({ viewport: { width: 820, height: 900 } });
for (const [name, w, m] of pairs) {
  const img = (f) => `data:image/jpeg;base64,${readFileSync(f).toString('base64')}`;
  await page.setContent(`<body style="margin:0;background:#888;font:600 15px system-ui;color:#fff"><div style="display:flex;gap:16px;padding:12px 12px 0">
    <figure style="margin:0"><figcaption style="padding:4px 0 6px">web (apps/web)</figcaption><img src="${img(w)}" width="390" height="844"></figure>
    <figure style="margin:0"><figcaption style="padding:4px 0 6px">mobile (apps/mobile)</figcaption><img src="${img(m)}" width="390" height="844"></figure></div></body>`);
  await page.screenshot({ path: `${OUT}/side-by-side-${name}.jpg`, type: 'jpeg', quality: 80, fullPage: true });
}
writeFileSync(`${OUT}/index.txt`, pairs.map((p) => p[0]).join('\n'));
await browser.close();
console.log(`${pairs.length} pairs -> ${OUT}`);
