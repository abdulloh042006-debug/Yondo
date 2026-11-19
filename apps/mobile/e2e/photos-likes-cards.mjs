/**
 * Evidence for the photos / likes / filters / cards UI (owner, 2026-11-14): 360×800 screenshots, web | mobile side by
 * side, in the Yondo day and night themes, against the REAL API. Signed in as the sample
 * customer, who first uploads one photo and likes DEMO Madina through the API.
 *
 * The backend is the video seed (marketing/ad-video/server_video.py with PHOTOS_DIR=marketing/ad-video/photos): unlike
 * the e2e harness it serves the stored photos, so pictures really render. Its names carry no DEMO prefix (owner's video
 * rule); every account in it is still sample data. Both builds are served by a static proxy that forwards /api and
 * /__test_storage to it (one database, so web and mobile show the same state):
 *   PHOTOS_DIR=marketing/ad-video/photos PYTHONPATH=apps/api/src python marketing/ad-video/server_video.py 8775 <tmp.db>
 *   (static proxy) 8777 -> apps/web/dist, 8776 -> mobile web export, both forwarding to 8775
 *   WEB=http://127.0.0.1:8777 MOBILE=http://127.0.0.1:8776 OUT=<dir> PHOTO=<png> node apps/mobile/e2e/photos-likes-cards.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const WEB = process.env.WEB ?? 'http://127.0.0.1:8777';
const MOBILE = process.env.MOBILE ?? 'http://127.0.0.1:8776';
const OUT = process.env.OUT ?? 'photos-likes-cards-out';
const PHOTO = readFileSync(process.env.PHOTO);
mkdirSync(OUT, { recursive: true });
const VERSIONS = { terms: '2026-11-19-draft', privacy: '2026-11-19-draft' };

async function call(base, method, path, body, token, type = 'application/json') {
  const r = await fetch(`${base}/api/v1${path}`, {
    method,
    headers: { 'content-type': type, ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : type === 'application/json' ? JSON.stringify(body) : body,
  });
  if (!r.ok) throw new Error(`${method} ${path} ${r.status}`);
  return r.status === 204 ? null : r.json();
}
async function prepare(base) {
  const phone = '+998901110003';
  const otp = await call(base, 'POST', '/auth/otp/request', { phone_number: phone });
  const pair = await call(base, 'POST', '/auth/otp/verify', { phone_number: phone, code: otp.development_otp });
  for (const [document, version] of Object.entries(VERSIONS)) await call(base, 'POST', '/account/consents', { document, version }, pair.access_token);
  const me = await call(base, 'GET', '/auth/me', undefined, pair.access_token);
  if (me.password_setup_required) await call(base, 'POST', '/auth/registration', { username: 'demo.customer', password: 'demo shots 2026', date_of_birth: '1995-05-15' }, pair.access_token);
  if (!(await call(base, 'GET', '/user-photos/me', undefined, pair.access_token)).length) await call(base, 'POST', '/user-photos/me', PHOTO, pair.access_token, 'image/png');
  const madina = (await call(base, 'GET', '/discovery/companions?q=Madina')).items[0].id;
  await call(base, 'PUT', `/discovery/companions/${madina}/like`, undefined, pair.access_token);
  return { pair, madina };
}

const browser = await chromium.launch();
async function shoot(base, theme, pair, act, file) {
  const ctx = await browser.newContext({ viewport: { width: 360, height: 800 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true, colorScheme: theme === 'yondo-tun' ? 'dark' : 'light', reducedMotion: 'reduce' });
  await ctx.addInitScript(([th, p]) => {
    localStorage.setItem('yondo.theme', th);
    localStorage.setItem('yondo.intro.off', '1');
    sessionStorage.setItem('yondo.access', p.access_token);
    sessionStorage.setItem('yondo.refresh', p.refresh_token);
  }, [theme, pair]);
  const page = await ctx.newPage();
  await act(page, base);
  await page.waitForTimeout(1200);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 1) throw new Error(`${file}: horizontal scroll ${overflow}px`);
  await page.screenshot({ path: file, type: 'jpeg', quality: 82 });
  await ctx.close();
}

const web = await prepare(WEB);
const mob = await prepare(MOBILE);
const ready = async (p, b) => {
  await p.goto(b);
  await p.getByText(/Madina/).first().waitFor({ timeout: 20000 });
};
const tab = (p, name) => p.getByRole('tab', { name, exact: true }).click();
const screens = [
  [
    'profil-photos',
    async (p, b) => { await p.goto(`${b}/account`); const h = p.getByRole('heading', { name: /Rasmlarim/ }); await h.waitFor(); await p.getByAltText(/rasmim, 1/).waitFor(); await h.scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, -70)); },
    async (p, b) => { await ready(p, b); await tab(p, 'Profil'); const h = p.getByText(/^Rasmlarim/).first(); await h.waitFor(); await h.scrollIntoViewIfNeeded(); },
  ],
  [
    'kashf-filters',
    async (p, b) => { await ready(p, b); await p.getByRole('button', { name: /^Filtrlar/ }).click(); await p.getByRole('dialog').waitFor(); },
    async (p, b) => { await ready(p, b); await p.getByRole('button', { name: /^Filtrlar/ }).click(); await p.getByRole('dialog').waitFor(); },
  ],
  [
    'card-feed',
    async (p, b) => { await p.goto(`${b}/?view=cards`); await p.locator('.deck-card img').waitFor(); await p.locator('.deck-actions').scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, 110)); },
    async (p, b) => { await ready(p, b); await p.getByRole('radio', { name: /Karto/ }).click(); const h = p.getByText(/1-si/).first(); await h.waitFor(); await p.getByRole('button', { name: /Keyingisi/ }).scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, 110)); },
  ],
  [
    'companion-likes',
    async (p, b) => { await p.goto(`${b}/c/${web.madina}`); await p.getByRole('heading', { name: /Madina/, level: 1 }).waitFor(); await p.getByRole('button', { name: /Yoqdi/ }).scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, 160)); },
    async (p, b) => { await ready(p, b); await p.getByRole('button', { name: /Madina/ }).first().click(); const l = p.getByRole('button', { name: /Yoqdi/ }); await l.waitFor(); await l.scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, 160)); },
  ],
];
const pairs = [];
for (const theme of ['yondo', 'yondo-tun']) {
  for (const [name, w, m] of screens) {
    const wf = `${OUT}/${name}-${theme}-web.jpg`;
    const mf = `${OUT}/${name}-${theme}-mobile.jpg`;
    await shoot(WEB, theme, web.pair, w, wf);
    await shoot(MOBILE, theme, mob.pair, m, mf);
    pairs.push([`${name}-${theme}`, wf, mf]);
  }
}
const page = await browser.newPage({ viewport: { width: 760, height: 860 } });
for (const [name, w, m] of pairs) {
  const img = (f) => `data:image/jpeg;base64,${readFileSync(f).toString('base64')}`;
  await page.setContent(`<body style="margin:0;background:#888;font:600 14px system-ui;color:#fff"><div style="display:flex;gap:16px;padding:12px 12px 0">
    <figure style="margin:0"><figcaption style="padding:4px 0 6px">web (apps/web) · ${name}</figcaption><img src="${img(w)}" width="360" height="800"></figure>
    <figure style="margin:0"><figcaption style="padding:4px 0 6px">mobile (apps/mobile)</figcaption><img src="${img(m)}" width="360" height="800"></figure></div></body>`);
  await page.screenshot({ path: `${OUT}/side-by-side-${name}.jpg`, type: 'jpeg', quality: 80, fullPage: true });
}
await browser.close();
console.log(`${pairs.length} pairs -> ${OUT}`);
