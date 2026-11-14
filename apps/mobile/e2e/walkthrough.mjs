/**
 * Screen recording for the owner: the mobile app (Expo web build, 390×844) tapping every tab and every Profil row,
 * signed out and signed in. A row that opens the web app really opens it (a new browser tab); the recording then
 * shows a 2-second preview of the page that opened, labelled with its address.
 *
 *   (servers as in e2e/parity.mjs)  MOBILE=http://127.0.0.1:8776 OUT=<dir> node apps/mobile/e2e/walkthrough.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const MOBILE = process.env.MOBILE ?? 'http://127.0.0.1:8776';
const OUT = process.env.OUT ?? 'walkthrough-out';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 1,
  hasTouch: true,
  recordVideo: { dir: OUT, size: { width: 390, height: 844 } },
});
await ctx.addInitScript(() => localStorage.setItem('yondo.theme', 'yondo'));
const page = await ctx.newPage();
const pause = (ms = 1200) => page.waitForTimeout(ms);
const tab = async (name) => {
  await page.getByRole('tab', { name, exact: true }).click();
  await pause();
};
const scroll = async (y) => {
  await page.mouse.move(195, 420);
  await page.mouse.wheel(0, y);
  await pause(900);
};
async function caption(text, ms = 1600) {
  await page.evaluate((t) => {
    const d = document.createElement('div');
    d.id = '__cap';
    d.textContent = t;
    Object.assign(d.style, { position: 'fixed', left: '12px', right: '12px', top: '96px', zIndex: 99999, padding: '10px 14px', borderRadius: '14px', background: '#111111', color: '#F5F2EC', font: '600 15px system-ui', textAlign: 'center', border: '2px solid #E8501A' });
    document.body.appendChild(d);
  }, text);
  await pause(ms);
  await page.evaluate(() => document.getElementById('__cap')?.remove());
}
/** Tap a "Veb-ilovada ochiladi" row: the web page opens in a new tab; show its screenshot for 2 s. */
async function webRow(name) {
  const [popup] = await Promise.all([page.waitForEvent('popup'), page.getByRole('link', { name }).click()]);
  await popup.waitForLoadState('load');
  await popup.waitForTimeout(1500);
  const shot = (await popup.screenshot({ type: 'jpeg', quality: 70 })).toString('base64');
  const url = new URL(popup.url()).pathname;
  await popup.close();
  await page.evaluate(([b64, u]) => {
    const d = document.createElement('div');
    d.id = '__web';
    Object.assign(d.style, { position: 'fixed', inset: '0', zIndex: 99998, background: '#111111' });
    d.innerHTML = `<div style="position:absolute;left:0;right:0;top:0;padding:8px;font:600 14px system-ui;color:#F5F2EC;text-align:center;background:#111">Veb-ilova ochildi: ${u}</div><img src="data:image/jpeg;base64,${b64}" style="position:absolute;top:34px;left:16px;width:358px;border-radius:12px">`;
    document.body.appendChild(d);
  }, [shot, url]);
  await pause(2200);
  await page.evaluate(() => document.getElementById('__web')?.remove());
  await pause(400);
}

await page.goto(MOBILE);
await page.getByText(/Madina/).first().waitFor({ timeout: 20000 });
await caption('Kirmagan foydalanuvchi: Kashf · Kirish');
await scroll(700);
await scroll(-700);
await tab('Kirish');
await page.getByRole('button', { name: /^Sozlamalar/ }).click();
await pause();
await page.getByRole('button', { name: '← Orqaga' }).click();
await pause(800);

// Sign in with the development code shown on screen (demo harness only).
await page.getByLabel('Telefon raqami').fill('+998901110003');
await page.getByRole('button', { name: 'Kod yuborish', exact: true }).click();
const banner = page.getByText(/\b\d{6}\b/).first();
await banner.waitFor({ timeout: 10000 });
const code = (await banner.innerText()).match(/\b(\d{6})\b/)[1];
await page.getByLabel('Tasdiqlash kodi').fill(code);
await page.getByRole('checkbox').click();
await pause(600);
await page.getByRole('button', { name: 'Kirish', exact: true }).click();
await page.getByRole('tab', { name: 'Profil', exact: true }).waitFor({ timeout: 15000 });
await pause(800);
await caption('Kirgan foydalanuvchi: Kashf · Sevimlilar · Bronlar · Profil');

await page.getByRole('button', { name: /Madina/ }).first().click();
await pause(1500);
await page.getByRole('button', { name: /sevimlilarga qo/ }).first().click();
await pause(1500);
await scroll(600);
await page.getByRole('button', { name: '← Orqaga' }).first().scrollIntoViewIfNeeded();
await page.getByRole('button', { name: '← Orqaga' }).first().click();
await pause();
await tab('Sevimlilar');
await tab('Bronlar');
await tab('Profil');
await caption('Profil = veb-ilovadagi “Hisobim” menyusi');
await page.getByRole('button', { name: /^Bronlar\./ }).click();
await pause();
await tab('Profil');
await webRow(/^Bildirishnomalar/);
await page.getByRole('button', { name: /^Sevimlilar\./ }).click();
await pause();
await tab('Profil');
await webRow(/^Yordam va xavfsizlik/);
await page.getByRole('button', { name: /^Sozlamalar\./ }).click();
await pause();
await page.getByRole('radio', { name: 'Yondo tungi', exact: true }).click();
await pause(1500);
await page.getByRole('radio', { name: 'Yondo kunduzgi', exact: true }).click();
await pause(900);
await page.getByRole('button', { name: '← Orqaga' }).click();
await pause();
await scroll(900);
await scroll(900);
await webRow(/^Hisobni o‘chirish/);
await webRow(/^Foydalanish shartlari/);
await webRow(/^Maxfiylik siyosati/);
await page.getByRole('button', { name: 'Chiqish', exact: true }).click();
await pause(1500);
await caption('Chiqildi: yana Kashf · Kirish');

await ctx.close();
await browser.close();
console.log('video in', OUT);
