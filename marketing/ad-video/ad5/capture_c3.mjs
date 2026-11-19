// Ad 6 «Yondo nima?» (C3) captures from the REAL apps/web build against marketing/ad-video/server_video.py.
// Run the API first:  AD5_SERVICES=1 PHOTOS_DIR=<repo>/marketing/ad-video/photos python3 server_video.py 8000 /tmp/cap.db
// (needs redis on :6379), then from apps/web:  npx vite build && OUT=<dir> node <repo>/marketing/ad-video/ad5/capture_c3.mjs
// Default alphabet (1995), theme `yondo`, phone 390x844 @2.5. Verified badges are removed (they come from a test double).
// Writes: discover-tadbir.png (Kashf with the Tadbir chip), card.png (card feed), profile.png, services.png, place.png
// (meeting-place field + hint) and *.json boxes (fractions of the viewport). ad5/crop_c3.py then makes the price-free crops.
// The only DOM change: the «✓ … tasdiqlangan» / «✓ … подтверждена» badge is removed, because it comes from the always-verified test double.
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
const { chromium } = createRequire(import.meta.url)('playwright');
const OUT = process.env.OUT; mkdirSync(OUT, { recursive: true });
// APP_LANG=ru: the whole run uses the app's own ru locale (localStorage 'yondo.lang' before the first page load, so the
// account is created in Russian); seed data (names, city) are translated from ../ru-dict.json "exact" entries, as in the RU cuts of reels 1-3.
const RU = process.env.APP_LANG === 'ru';
const L = (uz, ru) => (RU ? ru : uz);
const RUD = RU ? JSON.parse(readFileSync(new URL('../ru-dict.json', import.meta.url), 'utf8')) : { exact: {}, sub: [] };
const DICT = { exact: RUD.exact, sub: [...RUD.sub].sort((x, y) => y[0].length - x[0].length) };
const WEB = 'http://127.0.0.1:4173';
const preview = spawn('npx', ['vite', 'preview', '--port', '4173', '--host', '127.0.0.1'], { stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 2500));
const browser = await chromium.launch();
try {
  const c = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true, locale: 'uz-UZ' });
  await c.addInitScript((ru) => { try { localStorage.setItem('yondo.theme', 'yondo'); localStorage.setItem('yondo.intro.off', '1'); if (ru) localStorage.setItem('yondo.lang', 'ru'); } catch { /* */ } }, RU);
  const pg = await c.newPage();
  const settle = async () => {
    if (RU) await pg.evaluate((D) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); for (let n = w.nextNode(); n; n = w.nextNode()) { const k = n.nodeValue.trim(); if (!k) continue; let v = D.exact[k]; if (v === undefined) { v = k; for (const [x, y] of D.sub) v = v.split(x).join(y); } if (v !== k) n.nodeValue = n.nodeValue.replace(k, v); } }, DICT);
    await pg.evaluate(() => Promise.all(document.getAnimations().filter((a) => a.effect?.getComputedTiming?.().iterations !== Infinity).map((a) => a.finished.catch(() => 0))));
    await pg.waitForTimeout(400);
    await pg.evaluate(() => { for (const el of document.querySelectorAll('span, small, p, .tag')) if (el.children.length === 0 && /tasdiqlangan|подтвержден|verified/i.test(el.textContent) && /✓/.test(el.textContent)) el.remove(); });
  };
  const box = (sel) => pg.evaluate((s) => { const r = document.querySelector(s)?.getBoundingClientRect(); return r && { x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight }; }, sel);
  // sign in as the seeded customer (phone + on-screen dev code; the demo harness shows it, production never does)
  await pg.goto(`${WEB}/login`);
  await pg.getByRole('button', { name: L('Telegram orqali kod bilan kirish', 'Войти по коду через Telegram') }).click();
  await pg.getByLabel(L('Telefon raqami', 'Номер телефона')).fill('+998901110003');
  await pg.locator('.consent input').check();
  await pg.getByRole('button', { name: L('Kod yuborish', 'Отправить код') }).click();
  await pg.getByLabel(L('Tasdiqlash kodi', 'Код подтверждения')).fill((await pg.locator('b.mono').first().innerText()).trim());
  await pg.getByRole('button', { name: L('Kirish', 'Войти'), exact: true }).click();
  await pg.waitForURL((u) => !u.pathname.startsWith('/login'));
  // first sign-in: the app asks for a login + password (+ date of birth when missing), as for every new account
  if (await pg.getByRole('heading', { name: L('Login va parol yarating', 'Создайте логин и пароль') }).count()) {
    await pg.waitForTimeout(600);
    await pg.getByLabel(L('Login', 'Логин'), { exact: true }).fill('video0003');
    await pg.getByLabel(L('Yangi parol', 'Новый пароль')).fill('video pass 0003');
    await pg.getByLabel(L('Parolni takrorlang', 'Повторите пароль')).fill('video pass 0003');
    if (await pg.getByLabel(L('Tug‘ilgan sana', 'Дата рождения')).count()) await pg.getByLabel(L('Tug‘ilgan sana', 'Дата рождения')).fill('1995-05-15');
    await pg.getByRole('button', { name: L('Saqlash va davom etish', 'Сохранить и продолжить') }).click();
    await pg.getByRole('heading', { name: L('Login va parol yarating', 'Создайте логин и пароль') }).waitFor({ state: 'detached' });
  }
  // Kashf with the Tadbir category chip (ad 5, a01) and the card feed (ad 6): the card shows the categories as chips
  await pg.goto(`${WEB}/?service_code=event`);
  await pg.locator('.card, article').first().waitFor();
  await settle(); await pg.screenshot({ path: `${OUT}/discover-tadbir.png` });
  await pg.goto(`${WEB}/?service_code=event&view=cards`);
  await pg.locator('.deck-card').first().waitFor();
  await pg.waitForFunction(() => [...document.querySelectorAll('.deck-card img')].every((i) => i.complete), null, { timeout: 15000 }).catch(() => 0);
  await pg.evaluate(() => { const c = document.querySelector('.deck-card'); window.scrollTo(0, c.getBoundingClientRect().top + window.scrollY - 110); });
  await settle(); await pg.screenshot({ path: `${OUT}/card.png` });
  writeFileSync(`${OUT}/card.json`, JSON.stringify({ card: await box('.deck-card'), price: await box('.deck-card .price'), tags: await pg.evaluate(() => { const row = document.querySelector('.deck-card .tag')?.parentElement; if (!row) return null; const rs = [...row.children].map((e) => e.getBoundingClientRect()); const l = Math.min(...rs.map((r) => r.left)), t = Math.min(...rs.map((r) => r.top)), rr = Math.max(...rs.map((r) => r.right)), b = Math.max(...rs.map((r) => r.bottom)); return { x: l / innerWidth, y: t / innerHeight, w: (rr - l) / innerWidth, h: (b - t) / innerHeight }; }) }, null, 1));
  // profile
  await pg.goto(`${WEB}/?service_code=event`);
  await pg.locator('a[href^="/c/"]').first().click();
  await pg.getByRole('heading', { level: 1 }).first().waitFor();
  await pg.waitForFunction(() => [...document.querySelectorAll('img')].every((i) => i.complete), null, { timeout: 15000 }).catch(() => 0);
  await settle(); await pg.screenshot({ path: `${OUT}/profile.png` });
  await pg.getByText(L('Xizmatlar va narxlar', 'Услуги и цены')).first().scrollIntoViewIfNeeded(); await pg.evaluate(() => window.scrollBy(0, -120));
  await settle(); await pg.screenshot({ path: `${OUT}/services.png` });
  // booking dialog: meeting place + the app's own hint
  await pg.evaluate(() => window.scrollTo(0, 0));
  await pg.getByRole('button', { name: L('Bron qilish', 'Забронировать') }).first().click();
  const day = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10);
  await pg.getByLabel(L('Boshlanish vaqti (Toshkent vaqti)', 'Время начала (по Ташкенту)')).fill(`${day}T12:00`);
  await pg.getByLabel(L('Uchrashuv joyi', 'Место встречи')).fill(L('Markaziy kutubxona oldi, kafe', 'У центральной библиотеки, кафе'));
  await pg.getByLabel(L('Uchrashuv joyi', 'Место встречи')).scrollIntoViewIfNeeded();
  await settle(); await pg.screenshot({ path: `${OUT}/place.png` });
  writeFileSync(`${OUT}/place-field.json`, JSON.stringify(await pg.evaluate(() => {
    const LAB = /Uchrashuv joyi|Место встречи/, HINT = /Uy manzilini yozmang|домашний адрес|адрес дома/i;
    const lab = [...document.querySelectorAll('label')].find((l) => LAB.test(l.textContent));
    const f = document.getElementById(lab?.htmlFor || 'x') || lab?.querySelector('input, textarea');
    const hint = [...document.querySelectorAll('body *')].find((e) => e.children.length === 0 && HINT.test(e.textContent));
    const R = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight }; };
    return { label: R(lab), field: R(f), hint: R(hint), hintText: hint?.textContent };
  }), null, 1));
  if (RU) writeFileSync(`${OUT}/untranslated.json`, JSON.stringify(await pg.evaluate(() => [...new Set([...document.querySelectorAll('body *')].filter((e) => e.children.length === 0 && e.offsetParent && /[A-Za-z]{3}/.test(e.textContent)).map((e) => e.textContent.trim()))]), null, 1));
  console.log('CAPTURED', OUT, JSON.stringify(await box('h1')));
} finally { await browser.close(); preview.kill(); }
