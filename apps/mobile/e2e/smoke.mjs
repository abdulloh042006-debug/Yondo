/**
 * Smoke test of the mobile app's web build against the REAL API (the demo harness: throw-away SQLite, DEMO seed,
 * development OTP shown on screen, no payment provider => payment answers 503).
 *
 *   cd apps/mobile && npx expo export --platform web --output-dir <dist>
 *   cd apps/web && YONDO_WEB_DIST=<dist> PYTHONPATH=../api/src python e2e/server.py 8765 <tmp.db>
 *   MOBILE_URL=http://127.0.0.1:8765 node apps/mobile/e2e/smoke.mjs
 *
 * Phone viewport, English UI (the dictionaries are shared with apps/web, whose e2e covers the Uzbek texts).
 */
import { createRequire } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const URL = process.env.MOBILE_URL ?? 'http://127.0.0.1:8765';
const AXE_PATH = ['../../web/node_modules/axe-core/axe.min.js', '../node_modules/axe-core/axe.min.js']
  .map((p) => new globalThis.URL(p, import.meta.url).pathname)
  .find((p) => existsSync(p));
const CUSTOMER = '901110003';
const MADINA = '901110011';

let failed = 0;
const results = [];
async function step(name, fn) {
  try {
    await fn();
    results.push(`PASS ${name}`);
  } catch (e) {
    failed++;
    const seen = await page.locator('body').innerText().catch(() => '');
    results.push(`FAIL ${name}: ${String(e.message).split('\n').slice(0, 3).join(' | ').slice(0, 400)}\n  screen: ${seen.replace(/\s+/g, ' ').slice(0, 600)}`);
  }
}
const assert = (ok, msg) => {
  if (!ok) throw new Error(msg);
};

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const problems = [];
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, hasTouch: true });
await ctx.addInitScript(() => localStorage.setItem('yondo.locale', 'en'));
const page = await ctx.newPage();
page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
page.on('console', (m) => m.type() === 'error' && !/Failed to load resource/.test(m.text()) && problems.push(`console: ${m.text()}`));

const tab = (name) => page.getByRole('tab', { name, exact: true }).click();
const button = (name) => page.getByRole('button', { name, exact: true });
async function axe(label) {
  assert(AXE_PATH, 'axe-core not found: run npm ci in apps/web (or apps/mobile) first');
  await page.waitForTimeout(450); // let the 320 ms screen enter fade finish (a half-faded frame reads as low contrast)
  await page.addScriptTag({ content: readFileSync(AXE_PATH, 'utf8') });
  const v = await page.evaluate(async () => {
    const r = await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'], resultTypes: ['violations'] });
    return r.violations.filter((x) => ['serious', 'critical'].includes(x.impact)).map((x) => `${x.id}(${x.nodes.length})`);
  });
  assert(v.length === 0, `axe ${label}: ${v.join(', ')}`);
}
async function noSideScroll(label) {
  const w = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert(w <= 1, `${label}: horizontal overflow ${w}px`);
}
/** Sign out lives in Settings, which opens from Profile (owner, 2026-11-14). */
async function signOut() {
  await tab('Profile');
  await page.getByRole('button', { name: /^Settings\./ }).click();
  await button('Sign out').click();
}

/** Kirish opens on username/phone + password (owner, 2026-11-15); the code path is one tap away. */
const pw = (phone) => `smoke pass ${phone.slice(-4)}`;
const uname = (phone) => `smoke${phone.slice(-4)}`;
async function login(phone, p = page) {
  await p.getByRole('button', { name: 'Sign in with a code via Telegram', exact: true }).click();
  await p.getByLabel('Phone number').fill(`+998${phone}`);
  await button('Send code').click();
  const banner = page.getByText(/\b\d{6}\b/).first();
  await banner.waitFor({ timeout: 10000 });
  const code = (await banner.innerText()).match(/\b(\d{6})\b/)[1];
  await page.getByLabel('Verification code').fill(code);
  await page.getByRole('checkbox').click();
  await button('Sign in').click();
  // Every DEMO account starts without a password: the setup screen comes first, as for a real new account.
  const setup = page.getByRole('heading', { name: 'Create a username and password' });
  await Promise.race([setup.waitFor({ timeout: 15000 }), page.getByRole('tab', { name: 'Profile', exact: true }).waitFor({ timeout: 15000 })]);
  if (await setup.count()) {
    await page.waitForTimeout(400);
    await page.getByLabel('Username', { exact: true }).fill(uname(phone));
    await page.getByLabel('New password', { exact: true }).fill(pw(phone));
    await page.getByLabel('Repeat the password', { exact: true }).fill(pw(phone));
    await button('Save and continue').click();
    await setup.waitFor({ state: 'detached', timeout: 15000 });
  }
}

await step('discovery lists the DEMO companions (anonymous, API data)', async () => {
  await page.goto(URL);
  await page.getByText('DEMO Madina').first().waitFor({ timeout: 20000 });
  assert(await page.getByText('DEMO Jasur').count(), 'Jasur missing');
  assert(!(await page.getByText('DEMO Sevara').count()), 'unapproved Sevara must not be listed');
  await noSideScroll('discovery');
  await axe('discovery');
});

await step('signed out: the dock is Discover · Sign in (as on the web); Settings opens from Sign in', async () => {
  const names = await page.getByRole('tab').allInnerTexts();
  assert(names.join('|') === 'Discover|Sign in', `signed-out tabs: ${names.join('|')}`);
  await tab('Sign in');
  await page.getByLabel('Username or phone number').waitFor();
  // Owner, 2026-11-15: the language is chosen here (and in Settings), not in the header.
  const langs = page.getByRole('radiogroup', { name: 'App language' }).getByRole('radio');
  assert((await langs.count()) === 3, 'UZ | RU | EN on the sign-in screen');
  await page.getByRole('radio', { name: /^RU/ }).click();
  await page.getByLabel('Логин или номер телефона').waitFor();
  await page.getByRole('radio', { name: /^EN/ }).click();
  await page.getByLabel('Username or phone number').waitFor();
  const pwField = page.getByLabel('Password', { exact: true });
  assert((await pwField.getAttribute('autocomplete')) === 'current-password', 'current-password autocomplete');
  assert((await page.getByLabel('Username or phone number').getAttribute('autocomplete')) === 'username', 'username autocomplete');
  await page.getByRole('button', { name: /^Settings/ }).click();
  await page.getByRole('heading', { name: 'Settings' }).waitFor();
  await button('← Back').click();
  await page.getByLabel('Username or phone number').waitFor();
  await axe('sign in');
  await tab('Discover');
  await page.getByText('DEMO Madina').first().waitFor();
});

await step('profile -> book -> login with the development code -> back on the profile', async () => {
  await page.getByRole('button', { name: /DEMO Madina/ }).first().click();
  await page.getByText('Services and prices').waitFor();
  await button('Book').click();
  await page.getByLabel('Username or phone number').waitFor();
  await login(CUSTOMER);
  await page.getByText('Services and prices').waitFor({ timeout: 15000 });
});

await step('signed in: the dock is Discover · Favourites · Bookings · Profile, Settings is not a tab', async () => {
  const names = await page.getByRole('tab').allInnerTexts();
  assert(names.join('|') === 'Discover|Favourites|Bookings|Profile', `signed-in tabs: ${names.join('|')}`);
  // Header = logo only (owner, 2026-11-15): no SOS button, no language switch; nothing overflows at this width.
  assert((await page.getByRole('button', { name: /SOS/ }).count()) === 0, 'no SOS in the header');
  assert((await page.getByRole('radiogroup', { name: 'App language' }).count()) === 0, 'no language switch in the header');
  await noSideScroll('header');
});

await step('booking form sends exactly the 5 fields and the booking appears as pending', async () => {
  const sent = [];
  page.on('request', (r) => r.method() === 'POST' && r.url().endsWith('/api/v1/bookings') && sent.push(r.postDataJSON()));
  await button('Book').click();
  // The DEMO seed opens Madina's availability for [now+2d, now+2d+7h] and books now+2d+1h itself, so pick now+2d+4h
  // (Tashkent wall time, 5-minute steps): clear of the seed booking at any time of day.
  const slot = new Date(Math.floor((Date.now() + 2 * 864e5 + 4 * 36e5) / 3e5) * 3e5);
  const local = new Date(slot.getTime() + 5 * 36e5); // Asia/Tashkent = UTC+05:00
  const p2 = (n) => String(n).padStart(2, '0');
  await page.getByRole('radio', { name: `${p2(local.getUTCDate())}.${p2(local.getUTCMonth() + 1)}`, exact: true }).click();
  await page.getByLabel('Time (hh:mm)').fill(`${p2(local.getUTCHours())}:${p2(local.getUTCMinutes())}`);
  await page.getByLabel('Meeting place').fill('DEMO Amir Temur square');
  await button('Send request').click();
  await page.getByText('DEMO Amir Temur square').first().waitFor({ timeout: 15000 });
  assert((await page.getByRole('tab', { name: 'Bookings' }).getAttribute('aria-selected')) === 'true', 'Bookings tab not selected');
  assert(sent.length === 1, `POST /bookings count ${sent.length}`);
  const keys = Object.keys(sent[0]).sort().join(',');
  assert(keys === 'duration_minutes,meeting_place,service_id,starts_at,timezone', `fields: ${keys}`);
  assert(sent[0].starts_at === slot.toISOString(), `Tashkent ${p2(local.getUTCHours())}:${p2(local.getUTCMinutes())} must be ${slot.toISOString()}, got ${sent[0].starts_at}`);
  assert(sent[0].timezone === 'Asia/Tashkent', 'timezone');
  await noSideScroll('bookings');
  await axe('bookings');
});

await step('booking detail: report goes by booking_id only; payment not offered while pending', async () => {
  const bodies = [];
  page.on('request', (r) => r.method() === 'POST' && r.url().includes('/safety/reports') && bodies.push(r.postDataJSON()));
  await page.getByRole('button', { name: 'Details' }).filter({ hasText: 'DEMO Amir Temur square' }).first().click();
  await page.getByText('Booking details').waitFor();
  await page.getByText(/only for bookings in the .Accepted. state/i).first().waitFor();
  await button('Report a problem').click();
  await page.getByLabel('Describe what happened').fill('DEMO smoke-test report');
  await button('Send report').click();
  await page.getByText(/Report received/i).first().waitFor();
  assert(bodies.length === 1, 'one report');
  const keys = Object.keys(bodies[0]).sort().join(',');
  assert(keys === 'booking_id,category,description', `report fields: ${keys}`);
  await axe('booking detail');
});

await step('companion accepts the booking (role mode in the same app)', async () => {
  await signOut();
  await tab('Sign in');
  await login(MADINA);
  await tab('Bookings');
  await page.getByText('DEMO Amir Temur square').first().waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Details' }).filter({ hasText: 'DEMO Amir Temur square' }).first().click();
  await button('Accept').click();
  await page.getByRole('button', { name: 'Accept' }).last().click();
  await page.getByText('Accepted').first().waitFor();
});

await step('customer pays: no provider configured => shown as unavailable, never as declined', async () => {
  const keys = [];
  page.on('request', (r) => r.method() === 'POST' && r.url().includes('/payments/bookings/') && keys.push(r.headers()['idempotency-key']));
  await signOut();
  await tab('Sign in');
  await login(CUSTOMER);
  await tab('Bookings');
  await page.getByRole('button', { name: 'Details' }).filter({ hasText: 'DEMO Amir Temur square' }).first().click();
  await button('Go to payment').click();
  const status = await page.waitForResponse((r) => r.url().includes('/payments/bookings/') && r.request().method() === 'POST');
  assert(status.status() === 503, `payment status ${status.status()}`);
  await page.waitForTimeout(300);
  const text = await page.locator('body').innerText();
  assert(!/declined/i.test(text), 'a 503 must not read as declined');
  await button('Go to payment').click();
  await page.waitForResponse((r) => r.url().includes('/payments/bookings/') && r.request().method() === 'POST');
  assert(keys.length === 2 && keys[0] && keys[0] === keys[1], `idempotency keys ${keys.join(' / ')}`);
});

await step('favourites: the heart saves a companion (PUT) and Favourites lists it from the API', async () => {
  await tab('Discover');
  await page.getByRole('button', { name: /^Add DEMO Madina to favourites|DEMO Madina.*favourites/ }).first().click();
  await page.getByText(/Added to favourites/i).first().waitFor();
  await tab('Favourites');
  await page.getByText('DEMO Madina').first().waitFor();
  await noSideScroll('favourites');
  await axe('favourites');
});

await step('profile = only the person (data + Edit); Settings holds app and account; every row works', async () => {
  await tab('Profile');
  await page.getByRole('heading', { name: 'My account' }).waitFor();
  assert(!(await page.getByText(/Member since/).count()), 'the registration date is no longer shown');
  assert(!(await page.getByRole('button', { name: /^Bookings\./ }).count()), 'Bookings is a tab, not repeated in Profile');
  await axe('profile');
  await button('Edit').click();
  await page.getByLabel('Age', { exact: true }).waitFor();
  await button('Cancel').click();
  await page.getByRole('button', { name: /^Settings\./ }).click();
  await page.getByRole('heading', { name: 'Settings' }).waitFor();
  await axe('settings');
  // Notifications: native screen on the API
  await page.getByRole('button', { name: /^Notifications\./ }).click();
  await page.getByRole('heading', { name: 'Notifications' }).waitFor();
  await axe('notifications');
  await button('← Back').click();
  // Help & safety: native screen (112, SOS, reports via booking, trusted contacts, FAQ, support)
  await page.getByRole('button', { name: /^Help and safety\./ }).click();
  await page.getByRole('heading', { name: 'Help and safety' }).waitFor();
  await axe('help');
  await button('← Back').click();
  await page.getByRole('heading', { name: 'Settings' }).waitFor();
  // Owner, 2026-11-15: "Delete account" looks like "Sign out"; the question opens in a blurred, modal dialog.
  const del = page.getByRole('button', { name: 'Delete account', exact: true });
  const out = page.getByRole('button', { name: 'Sign out', exact: true });
  const look = (l) => l.evaluate((el) => { const c = getComputedStyle(el); return [c.backgroundColor, c.borderColor, c.borderRadius, c.minHeight].join(' '); });
  assert((await look(del)) === (await look(out)), `same look: ${await look(del)} vs ${await look(out)}`);
  await del.click();
  const dlg = page.getByRole('dialog', { name: 'Delete your account?' });
  await dlg.waitFor();
  assert((await dlg.getAttribute('aria-modal')) === 'true', 'aria-modal');
  assert(await page.getByRole('button', { name: 'Yes, delete' }).isDisabled(), 'confirm waits for the "I understand" box');
  await axe('delete dialog');
  await page.keyboard.press('Escape');
  await dlg.waitFor({ state: 'detached' });
  await del.click();
  await button('No').click();
  await dlg.waitFor({ state: 'detached' });
  const web = process.env.WEB_URL;
  if (web) {
    for (const [name, path] of [[/^Terms of use/, '/terms'], [/^Privacy policy/, '/privacy']]) {
      const [popup] = await Promise.all([page.waitForEvent('popup'), page.getByRole('link', { name }).click()]);
      assert(popup.url().startsWith(web + path), `${name} opened ${popup.url()}`);
      await popup.close();
    }
  }
});

await step('help: trusted contact add/remove and a support request go to the API', async () => {
  await page.getByRole('button', { name: /^Help and safety\./ }).click();
  await page.getByRole('heading', { name: 'Help and safety' }).waitFor();
  const posts = [];
  page.on('request', (r) => r.method() === 'POST' && /trusted-contacts|support\/requests/.test(r.url()) && posts.push(r.url()));
  await page.getByRole('button', { name: 'What is Yondo?' }).click(); // FAQ opens in place
  await page.getByLabel('Name', { exact: true }).fill('DEMO Ona');
  await page.getByLabel('Contact phone').fill('+998 90 123 45 67');
  await button('Add').click();
  await page.getByText('+998901234567').waitFor();
  await page.getByRole('button', { name: 'Remove contact DEMO Ona' }).click();
  await page.getByText('Contact removed.').waitFor();
  await page.getByLabel('Your message').fill('DEMO smoke-test support request');
  await button('Send request').click();
  await page.getByText('DEMO smoke-test support request').waitFor();
  assert(posts.length === 2, `POSTs: ${posts.join(', ')}`);
  await button('← Back').click();
  await page.getByRole('heading', { name: 'Settings' }).waitFor();
});

await step('settings: Russian, Uzbek alphabets and the night theme apply in place', async () => {
  await page.getByRole('radio', { name: 'Русский' }).last().click();
  await page.getByRole('tab', { name: 'Брони' }).waitFor();
  await page.getByRole('radio', { name: /^O‘zbekcha$/ }).last().click();
  await page.getByRole('radio', { name: /^Özbekça \(ö ğ ş ç\)/ }).click();
  await page.getByRole('tab', { name: 'Kaşf' }).waitFor();
  await page.getByRole('radio', { name: /^O‘zbekcha \(o‘ g‘ sh ch\)/ }).click();
  await page.getByRole('tab', { name: 'Kashf' }).waitFor();
  await page.getByRole('radio', { name: 'Yondo tungi', exact: true }).click();
  const bg = await page.evaluate(() => getComputedStyle(document.querySelector('[role="tablist"]')).backgroundColor);
  assert(/^rgba?\(17, 17, 17/.test(bg), `night theme tab bar ${bg}`);
  await noSideScroll('settings');
  await axe('settings (night)');
});

await step('password (owner, 2026-11-15): username and phone sign-in, wrong password, change, reset', async () => {
  const PHONE = CUSTOMER;
  // The previous step left Settings in Uzbek, and the language is saved to the account: back to English.
  await page.getByRole('radio', { name: 'English', exact: true }).click();
  await page.getByRole('heading', { name: 'Settings' }).waitFor();
  await page.waitForTimeout(600); // the PUT /auth/profile (ui_locale = en) lands before signing out
  const passwordSignIn = async (login, password) => {
    await page.getByLabel('Username or phone number').fill(login);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await button('Sign in').click();
  };
  await signOut();
  await tab('Sign in');
  await passwordSignIn(uname(PHONE), 'not the password');
  await page.getByText('The username or password is incorrect.').waitFor();
  assert((await page.getByLabel('Password', { exact: true }).inputValue()) === '', 'the password field is emptied');
  await axe('sign in (password error)');
  await passwordSignIn(uname(PHONE).toUpperCase(), pw(PHONE)); // usernames are case-insensitive
  await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor({ timeout: 15000 });
  await signOut();
  await tab('Sign in');
  await passwordSignIn(`+998 ${PHONE}`, pw(PHONE));
  await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor({ timeout: 15000 });
  // Change in Settings → Account: the note says other devices are signed out.
  await tab('Profile');
  await page.getByRole('button', { name: /^Settings\./ }).click();
  await page.getByText(`Username: ${uname(PHONE)}`).waitFor();
  await button('Change password').click();
  await page.getByText(/other devices are signed out/).first().waitFor();
  await page.getByLabel('Current password', { exact: true }).fill('wrong current');
  await page.getByLabel('New password', { exact: true }).fill('smoke changed pass');
  await page.getByLabel('Repeat the password', { exact: true }).fill('smoke changed pass');
  await button('Save the password').click();
  await page.getByText('The current password is incorrect.').waitFor();
  await page.getByLabel('Current password', { exact: true }).fill(pw(PHONE));
  await button('Save the password').click();
  await page.getByText('Password changed. Other devices were signed out.').waitFor();
  // Forgotten password: phone → code → new password → signed in.
  await button('Sign out').click();
  await tab('Sign in');
  await button('Forgot your password?').click();
  await page.getByRole('heading', { name: 'Reset your password' }).waitFor();
  await page.getByLabel('Phone number').fill(`+998${PHONE}`);
  await button('Send code').click();
  const banner = page.getByText(/\b\d{6}\b/).first();
  await banner.waitFor({ timeout: 10000 });
  await page.getByLabel('Verification code').fill((await banner.innerText()).match(/\b(\d{6})\b/)[1]);
  await page.getByLabel('New password', { exact: true }).fill(`+998${PHONE}`);
  await page.getByLabel('Repeat the password', { exact: true }).fill(`+998${PHONE}`);
  await button('Save the password and sign in').click();
  await page.getByText('The password must not be your phone number.').waitFor();
  await page.getByLabel('New password', { exact: true }).fill(pw(PHONE));
  await page.getByLabel('Repeat the password', { exact: true }).fill(pw(PHONE));
  await button('Save the password and sign in').click();
  await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor({ timeout: 15000 });
});

await step('no page errors or console errors', async () => {
  assert(problems.length === 0, problems.slice(0, 5).join(' | '));
});

await browser.close();
console.log(results.join('\n'));
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
