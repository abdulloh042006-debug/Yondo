/**
 * Before/after evidence for the owner's 2026-11-15 fixes, 360×800 phone, web and mobile:
 * header (logo only), sign-in with the language choice, Settings with the two account buttons, the delete dialog.
 * Servers as in e2e/parity.mjs; BEFORE = builds from origin/main, AFTER = this branch.
 *
 *   WEB_BEFORE=… WEB_AFTER=… MOB_BEFORE=… MOB_AFTER=… OUT=<dir> node apps/mobile/e2e/header-and-delete.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const env = (k, d) => process.env[k] ?? d;
const SITES = {
  'web-before': env('WEB_BEFORE', 'http://127.0.0.1:8787'),
  'web-after': env('WEB_AFTER', 'http://127.0.0.1:8777'),
  'mobile-before': env('MOB_BEFORE', 'http://127.0.0.1:8786'),
  'mobile-after': env('MOB_AFTER', 'http://127.0.0.1:8776'),
};
const OUT = env('OUT', 'shots');
mkdirSync(OUT, { recursive: true });
const VERSIONS = { terms: '2026-10-23-draft', privacy: '2026-10-23-draft' };
const API = SITES['web-after'];
async function post(path, body, token) {
  const r = await fetch(`${API}/api/v1${path}`, { method: 'POST', headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json().catch(() => null);
}
const otp = await post('/auth/otp/request', { phone_number: '+998901110003' });
const pair = await post('/auth/otp/verify', { phone_number: '+998901110003', code: otp.development_otp });
for (const [document, version] of Object.entries(VERSIONS)) await post('/account/consents', { document, version }, pair.access_token);

const browser = await chromium.launch();
async function page(site, signedIn) {
  const ctx = await browser.newContext({ viewport: { width: 360, height: 800 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  await ctx.addInitScript(([p, signed]) => {
    localStorage.setItem('yondo.theme', 'yondo');
    if (signed) {
      sessionStorage.setItem('yondo.access', p.access_token);
      sessionStorage.setItem('yondo.refresh', p.refresh_token);
    }
  }, [pair, signedIn]);
  const p = await ctx.newPage();
  return { p, ctx };
}
const shots = [];
async function shot(name, site, signedIn, act) {
  const { p, ctx } = await page(site, signedIn);
  try {
    await act(p, SITES[site], site.startsWith('web'));
    await p.waitForTimeout(900);
    const f = `${OUT}/${name}-${site}.jpg`;
    await p.screenshot({ path: f, type: 'jpeg', quality: 82 });
    shots.push([name, site, f]);
  } catch (e) {
    console.log(`skip ${name} ${site}: ${String(e.message).split('\n')[0]}`);
  } finally {
    await ctx.close();
  }
}
const home = async (p, b) => { await p.goto(b); await p.getByText(/Madina/).first().waitFor({ timeout: 20000 }); };
// BEFORE (main): sign out and deletion lived on Profil (/account); AFTER: in Sozlamalar.
const toSettings = async (p, b, isWeb, before) => {
  if (isWeb) { await p.goto(`${b}${before ? '/account' : '/settings'}`); await p.getByRole('heading', { level: 1 }).first().waitFor(); }
  else { await home(p, b); await p.getByRole('tab', { name: 'Profil', exact: true }).click(); if (!before) await p.getByRole('button', { name: /^Sozlamalar\./ }).click(); }
  const target = p.getByRole('button', { name: /Chiqish/ }).first();
  await target.scrollIntoViewIfNeeded();
  await p.evaluate(() => window.scrollBy(0, -120));
};
for (const site of Object.keys(SITES)) {
  const isWeb = site.startsWith('web');
  await shot('1-header', site, true, async (p, b) => { if (isWeb) { await p.goto(`${b}/help`); await p.getByRole('heading', { level: 1 }).first().waitFor(); } else { await home(p, b); } });
  await shot('2-login', site, false, async (p, b) => {
    if (isWeb) { await p.goto(`${b}/login`); await p.getByRole('heading', { level: 1 }).first().waitFor(); }
    else { await home(p, b); await p.getByRole('tab', { name: 'Kirish', exact: true }).click(); await p.getByRole('heading', { level: 1 }).first().waitFor(); }
  });
  const before = site.endsWith('before');
  await shot('3-settings-buttons', site, true, (p, b) => toSettings(p, b, isWeb, before));
  await shot('4-delete-dialog', site, true, async (p, b) => {
    if (before && !isWeb) throw new Error('mobile on main had no native deletion (a web row)');
    await toSettings(p, b, isWeb, before);
    const btn = p.getByRole('button', { name: /^Hisobni o‘chirish(ni so‘rash)?$/ }).first();
    await btn.scrollIntoViewIfNeeded();
    await btn.click();
    await p.getByRole('dialog').first().waitFor();
  });
}
// Composite per scene: before | after for web and mobile.
const pg = await browser.newPage({ viewport: { width: 1520, height: 900 } });
const img = (f) => `data:image/jpeg;base64,${readFileSync(f).toString('base64')}`;
for (const scene of [...new Set(shots.map((s) => s[0]))]) {
  const cells = ['web-before', 'web-after', 'mobile-before', 'mobile-after'].map((site) => {
    const s = shots.find((x) => x[0] === scene && x[1] === site);
    return `<figure style="margin:0"><figcaption style="padding:4px 0 6px">${site}</figcaption>${s ? `<img src="${img(s[2])}" width="360" height="800">` : '<div style="width:360px;height:800px;background:#555"></div>'}</figure>`;
  });
  await pg.setContent(`<body style="margin:0;background:#888;font:600 15px system-ui;color:#fff"><div style="display:flex;gap:16px;padding:12px">${cells.join('')}</div></body>`);
  await pg.screenshot({ path: `${OUT}/before-after-${scene}.jpg`, type: 'jpeg', quality: 78, fullPage: true });
}
await browser.close();
console.log(`${shots.length} shots -> ${OUT}`);
