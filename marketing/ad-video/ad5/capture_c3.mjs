// Ad 6 «Yondo nima?» (C3) captures from the REAL apps/web build against marketing/ad-video/server_video.py.
// Run the API first:  AD5_SERVICES=1 PHOTOS_DIR=<repo>/marketing/ad-video/photos python3 server_video.py 8000 /tmp/cap.db
// (needs redis on :6379), then from apps/web:  npx vite build && OUT=<dir> node <repo>/marketing/ad-video/ad5/capture_c3.mjs
// Default alphabet (1995), theme `yondo`, phone 390x844 @2.5. Verified badges are removed (they come from a test double).
// Writes: profile.png (top of the profile), services.png (service chips + languages), place.png (meeting-place field + hint),
// and *.json boxes (fractions of the viewport) of the elements the video lifts or crops. Prices are never in a saved crop.
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
const { chromium } = createRequire(import.meta.url)('playwright');
const OUT = process.env.OUT; mkdirSync(OUT, { recursive: true });
const WEB = 'http://127.0.0.1:4173';
const preview = spawn('npx', ['vite', 'preview', '--port', '4173', '--host', '127.0.0.1'], { stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 2500));
const browser = await chromium.launch();
try {
  const c = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true, locale: 'uz-UZ' });
  await c.addInitScript(() => { try { localStorage.setItem('yondo.theme', 'yondo'); localStorage.setItem('yondo.intro.off', '1'); } catch { /* */ } });
  const pg = await c.newPage();
  const settle = async () => {
    await pg.evaluate(() => Promise.all(document.getAnimations().filter((a) => a.effect?.getComputedTiming?.().iterations !== Infinity).map((a) => a.finished.catch(() => 0))));
    await pg.waitForTimeout(400);
    await pg.evaluate(() => { for (const el of document.querySelectorAll('span, small, p, .tag')) if (el.children.length === 0 && /tasdiqlangan/i.test(el.textContent) && /✓/.test(el.textContent)) el.remove(); });
  };
  const box = (sel) => pg.evaluate((s) => { const r = document.querySelector(s)?.getBoundingClientRect(); return r && { x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight }; }, sel);
  // sign in as the seeded customer (phone + on-screen dev code; the demo harness shows it, production never does)
  await pg.goto(`${WEB}/login`);
  await pg.getByRole('button', { name: 'Telegram orqali kod bilan kirish' }).click();
  await pg.getByLabel('Telefon raqami').fill('+998901110003');
  await pg.locator('.consent input').check();
  await pg.getByRole('button', { name: 'Kod yuborish' }).click();
  await pg.getByLabel('Tasdiqlash kodi').fill((await pg.locator('b.mono').first().innerText()).trim());
  await pg.getByRole('button', { name: 'Kirish', exact: true }).click();
  await pg.waitForURL((u) => !u.pathname.startsWith('/login'));
  // first sign-in: the app asks for a login + password (+ date of birth when missing), as for every new account
  if (await pg.getByRole('heading', { name: 'Login va parol yarating' }).count()) {
    await pg.waitForTimeout(600);
    await pg.getByLabel('Login', { exact: true }).fill('video0003');
    await pg.getByLabel('Yangi parol').fill('video pass 0003');
    await pg.getByLabel('Parolni takrorlang').fill('video pass 0003');
    if (await pg.getByLabel('Tug‘ilgan sana').count()) await pg.getByLabel('Tug‘ilgan sana').fill('1995-05-15');
    await pg.getByRole('button', { name: 'Saqlash va davom etish' }).click();
    await pg.getByRole('heading', { name: 'Login va parol yarating' }).waitFor({ state: 'detached' });
  }
  // Kashf with the Tadbir category chip (ad 5, a01) and the card feed (ad 6): the card shows the categories as chips
  await pg.goto(`${WEB}/?service_code=event`);
  await pg.getByRole('link', { name: /Madina profilini ochish/ }).first().waitFor();
  await settle(); await pg.screenshot({ path: `${OUT}/discover-tadbir.png` });
  await pg.goto(`${WEB}/?service_code=event&view=cards`);
  await pg.locator('.deck-card').first().waitFor();
  await pg.waitForFunction(() => [...document.querySelectorAll('.deck-card img')].every((i) => i.complete), null, { timeout: 15000 }).catch(() => 0);
  await pg.evaluate(() => { const c = document.querySelector('.deck-card'); window.scrollTo(0, c.getBoundingClientRect().top + window.scrollY - 110); });
  await settle(); await pg.screenshot({ path: `${OUT}/card.png` });
  writeFileSync(`${OUT}/card.json`, JSON.stringify({ card: await box('.deck-card'), price: await box('.deck-card .price'), tags: await box('.deck-card .tag') }, null, 1));
  // profile
  await pg.goto(`${WEB}/?service_code=event`);
  await pg.getByRole('link', { name: /Madina profilini ochish/ }).click();
  await pg.getByRole('heading', { name: 'Madina', level: 1 }).waitFor();
  await pg.waitForFunction(() => [...document.querySelectorAll('img')].every((i) => i.complete), null, { timeout: 15000 }).catch(() => 0);
  await settle(); await pg.screenshot({ path: `${OUT}/profile.png` });
  await pg.getByText('Xizmatlar va narxlar').first().scrollIntoViewIfNeeded(); await pg.evaluate(() => window.scrollBy(0, -120));
  await settle(); await pg.screenshot({ path: `${OUT}/services.png` });
  // booking dialog: meeting place + the app's own hint
  await pg.evaluate(() => window.scrollTo(0, 0));
  await pg.getByRole('button', { name: 'Bron qilish' }).first().click();
  const day = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10);
  await pg.getByLabel('Boshlanish vaqti (Toshkent vaqti)').fill(`${day}T12:00`);
  await pg.getByLabel('Uchrashuv joyi').fill('Markaziy kutubxona oldi, kafe');
  await pg.getByLabel('Uchrashuv joyi').scrollIntoViewIfNeeded();
  await settle(); await pg.screenshot({ path: `${OUT}/place.png` });
  writeFileSync(`${OUT}/place-field.json`, JSON.stringify(await pg.evaluate(() => {
    const f = document.querySelector('[aria-label="Uchrashuv joyi"], #' + CSS.escape([...document.querySelectorAll('label')].find((l) => /Uchrashuv joyi/.test(l.textContent))?.htmlFor || 'x'));
    const lab = [...document.querySelectorAll('label')].find((l) => /Uchrashuv joyi/.test(l.textContent));
    const hint = [...document.querySelectorAll('body *')].find((e) => e.children.length === 0 && /Uy manzilini yozmang/.test(e.textContent));
    const R = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight }; };
    return { label: R(lab), field: R(f), hint: R(hint), hintText: hint?.textContent };
  }), null, 1));
  console.log('CAPTURED', OUT, JSON.stringify(await box('h1')));
} finally { await browser.close(); preview.kill(); }
