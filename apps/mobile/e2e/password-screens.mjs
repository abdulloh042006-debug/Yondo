/**
 * 360×800 screenshots of the password and username screens (owner, 2026-11-15), web and mobile side by side:
 * Kirish (username/phone + password), the setup after a code sign-in, the reset's new-password step,
 * and Settings → change password.
 *
 *   WEB=http://127.0.0.1:8777 MOB=http://127.0.0.1:8765 OUT=<dir> node apps/mobile/e2e/password-screens.mjs
 * Each server: apps/web/e2e/server.py with YONDO_WEB_DIST = the web or mobile build (fresh DEMO database).
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const SITES = { web: process.env.WEB ?? 'http://127.0.0.1:8777', mobile: process.env.MOB ?? 'http://127.0.0.1:8765' };
const OUT = process.env.OUT ?? 'shots';
mkdirSync(OUT, { recursive: true });

async function api(base, path, body, token, method = 'POST') {
  const r = await fetch(`${base}/api/v1${path}`, {
    method,
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.status === 204 ? null : r.json();
}
/** A fresh code sign-in (with consent), as the app does it. `register` also sets a username + password. */
async function codeSession(base, phone, register) {
  const otp = await api(base, '/auth/otp/request', { phone_number: phone });
  const pair = await api(base, '/auth/otp/verify', { phone_number: phone, code: otp.development_otp });
  for (const [document, version] of Object.entries({ terms: '2026-11-19-draft', privacy: '2026-11-19-draft' })) await api(base, '/account/consents', { document, version }, pair.access_token);
  if (register) await api(base, '/auth/registration', { date_of_birth: '1995-05-15', ...register }, pair.access_token);
  return pair;
}

const browser = await chromium.launch();
const shots = [];
async function shot(name, site, { pair, act }) {
  const ctx = await browser.newContext({ viewport: { width: 360, height: 800 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  await ctx.addInitScript(
    (p) => {
      localStorage.setItem('yondo.theme', 'yondo');
      localStorage.setItem('yondo.intro.off', '1');
      localStorage.setItem('yondo.uzAlphabet', '2026'); // web: Uzbek in the 2026 alphabet (uz.ts as written)
      localStorage.setItem('yondo.locale', 'uz-Latn-2026'); // mobile build: the same
      if (p) {
        sessionStorage.setItem('yondo.access', p.access_token);
        sessionStorage.setItem('yondo.refresh', p.refresh_token);
      }
    },
    pair ?? null,
  );
  const page = await ctx.newPage();
  try {
    await act(page, SITES[site]);
    await page.waitForTimeout(900);
    const f = `${OUT}/${name}-${site}.jpg`;
    await page.screenshot({ path: f, type: 'jpeg', quality: 82 });
    shots.push([name, site, f]);
  } catch (e) {
    console.log(`skip ${name} ${site}: ${String(e.message).split('\n')[0]}`);
  } finally {
    await ctx.close();
  }
}
const h1 = (p) => p.getByRole('heading', { level: 1 }).first().waitFor({ timeout: 20000 });
const openLogin = async (p, b, site) => {
  if (site === 'web') await p.goto(`${b}/login`);
  else {
    await p.goto(b);
    await p.getByRole('tab', { name: 'Kiriş', exact: true }).click();
  }
  await h1(p);
};
const openSettings = async (p, b, site) => {
  if (site === 'web') await p.goto(`${b}/settings`);
  else {
    await p.goto(b);
    await p.getByRole('tab', { name: 'Profil', exact: true }).click();
    await p.getByRole('button', { name: /^Sozlamalar\./ }).click();
  }
  await h1(p);
};

for (const site of ['web', 'mobile']) {
  const base = SITES[site];
  const ready = await codeSession(base, '+998901110003', { username: 'aziz.demo', password: 'demo pass 0003' });
  await shot('1-kirish', site, { act: (p, b) => openLogin(p, b, site) });
  await shot('2-setup', site, {
    pair: await codeSession(base, '+998907770055'),
    act: async (p, b) => {
      await p.goto(b);
      await p.getByRole('heading', { name: 'Login va parol yarating' }).waitFor({ timeout: 20000 });
      await p.waitForTimeout(600);
      await p.getByLabel('Login', { exact: true }).fill('nodira.t');
      await p.getByText('Bu login böş.').waitFor();
    },
  });
  await shot('3-reset', site, {
    act: async (p, b) => {
      await openLogin(p, b, site);
      await p.getByRole('button', { name: 'Parolni unutdingizmi?' }).click();
      await p.getByLabel('Telefon raqami').fill('+998901110003');
      await p.getByRole('button', { name: 'Kod yuboriş' }).click();
      await p.getByLabel('Yangi parol').waitFor();
      await p.getByLabel('Yangi parol').scrollIntoViewIfNeeded();
    },
  });
  await shot('4-change-password', site, {
    pair: ready,
    act: async (p, b) => {
      await openSettings(p, b, site);
      await p.getByRole('button', { name: 'Parolni almaştiriş' }).click();
      await p.getByLabel('Hozirgi parol').scrollIntoViewIfNeeded();
      await p.evaluate(() => window.scrollBy(0, -140));
    },
  });
}

// One composite per scene: web | mobile.
const pg = await browser.newPage({ viewport: { width: 780, height: 900 } });
const img = (f) => `data:image/jpeg;base64,${readFileSync(f).toString('base64')}`;
for (const scene of [...new Set(shots.map((s) => s[0]))]) {
  const cells = ['web', 'mobile'].map((site) => {
    const s = shots.find((x) => x[0] === scene && x[1] === site);
    return `<figure style="margin:0"><figcaption style="padding:4px 0 6px">${site}</figcaption>${s ? `<img src="${img(s[2])}" width="360" height="800">` : ''}</figure>`;
  });
  await pg.setContent(`<body style="margin:0;background:#888;font:600 15px system-ui;color:#fff"><div style="display:flex;gap:16px;padding:12px">${cells.join('')}</div></body>`);
  await pg.screenshot({ path: `${OUT}/${scene}.jpg`, type: 'jpeg', quality: 78, fullPage: true });
}
await browser.close();
console.log(`${shots.length} shots -> ${OUT}`);
