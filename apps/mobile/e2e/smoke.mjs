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

const authed = (path, init = {}) =>
  page.evaluate(async ([path, init]) => {
    const r = await fetch(`/api/v1${path}`, { ...init, headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}`, ...(init.headers ?? {}) } });
    return { status: r.status, body: r.status === 204 ? null : await r.json() };
  }, [path, init]);
const deckName = async () => (await page.getByRole('heading').filter({ hasText: /^DEMO/ }).first().innerText()).split(',')[0];
async function nextCard(from) {
  await button('Next').click();
  for (let i = 0; i < 50 && (await deckName()) === from; i++) await page.waitForTimeout(100);
  assert((await deckName()) !== from, 'Next must show another card');
}
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');
await step('Profile photos (owner, 2026-11-14): upload a PNG through the picker, main photo, delete (real API)', async () => {
  await tab('Profile');
  await page.getByText(/^My photos/).first().waitFor();
  await page.getByText(/companions you sent a booking request to/).first().waitFor();
  for (const name of ['a.png', 'b.png']) {
    const chooser = page.waitForEvent('filechooser');
    await button('Add a photo').click();
    await (await chooser).setFiles({ name, mimeType: 'image/png', buffer: PNG });
    await page.getByText('Photo uploaded.').first().waitFor();
    await page.waitForFunction((n) => document.body.innerText.includes(`My photos · ${n} of 6`), name === 'a.png' ? 1 : 2);
  }
  const before = (await authed('/user-photos/me')).body.map((p) => p.id);
  assert(before.length === 2, `2 photos expected, got ${before.length}`);
  await button('Make main').click();
  await page.getByText('Main photo set.').first().waitFor();
  const after = (await authed('/user-photos/me')).body.map((p) => p.id);
  assert(after[0] === before[1], 'the second photo must become the main one on the server');
  await button('Delete').first().click();
  await page.getByRole('dialog', { name: 'Delete this photo?' }).getByRole('button', { name: 'Delete', exact: true }).click();
  await page.getByText('Photo deleted.').first().waitFor();
  const left = (await authed('/user-photos/me')).body.map((p) => p.id);
  assert(left.length === 1 && left[0] === before[0], 'the main photo was deleted on the server');
  await noSideScroll('profile photos');
  await axe('profile photos');
});

await step('Like: optimistic toggle with the count from the API, separate from favourites', async () => {
  await tab('Discover');
  await page.getByRole('button', { name: 'Open the profile of DEMO Jasur' }).first().click();
  const like = page.getByRole('button', { name: /^Like DEMO Jasur/ });
  await like.waitFor();
  const id = (await (await page.evaluate(async () => (await fetch('/api/v1/discovery/companions?q=Jasur')).json())).items[0].id);
  const count = async () => (await page.evaluate(async (id) => (await fetch(`/api/v1/discovery/companions/${id}`)).json(), id)).like_count;
  const start = await count();
  await like.click();
  await page.getByRole('button', { name: /^Remove your like from DEMO Jasur/ }).waitFor();
  await page.waitForFunction(async ([id, n]) => (await (await fetch(`/api/v1/discovery/companions/${id}`)).json()).like_count === n, [id, start + 1]);
  await page.getByRole('button', { name: /^Remove your like from DEMO Jasur/ }).click();
  await page.waitForFunction(async ([id, n]) => (await (await fetch(`/api/v1/discovery/companions/${id}`)).json()).like_count === n, [id, start]);
  await page.getByText(/No ratings yet|★/).first().waitFor();
  await axe('profile with likes');
});

await step('filters sheet: category, minimum stars, sort; chips + clear all (real API)', async () => {
  await tab('Discover');
  await page.getByText('DEMO Madina').first().waitFor();
  await page.getByRole('button', { name: 'Filters', exact: true }).click();
  const sheet = page.getByRole('dialog', { name: 'Filters' });
  await sheet.getByRole('radio', { name: 'Coffee' }).click();
  await sheet.getByRole('radio', { name: '4+ ★' }).click();
  await sheet.getByRole('radio', { name: 'Most likes' }).click();
  const req = page.waitForRequest((r) => r.url().includes('/discovery/companions?') && r.url().includes('sort=likes') && r.url().includes('rating_min=4') && r.url().includes('service_code=coffee'));
  await sheet.getByRole('button', { name: 'Show results' }).click();
  await req;
  await page.getByRole('button', { name: 'Filters (2)' }).waitFor();
  await page.getByRole('button', { name: 'Remove the “4+ ★” filter' }).waitFor();
  await axe('discover with filters');
  await button('Clear all').click();
  await page.getByRole('button', { name: 'Filters', exact: true }).waitFor();
  await page.getByRole('radio', { name: 'Recommended' }).click();
  await page.getByText('DEMO Madina').first().waitFor();
  await noSideScroll('discover filters');
});

await step('Cards: Save adds to favourites, Next skips; no dislike or match', async () => {
  await page.getByRole('radio', { name: 'Cards' }).click();
  // The deck always opens on its first card ("1 of N"), never on the end screen.
  await page.getByText(/^1 of \d+\+?$/).first().waitFor();
  const heading = page.getByRole('heading').filter({ hasText: /^DEMO/ }).first();
  await heading.waitFor();
  assert(!/dislike|match/i.test(await page.locator('body').innerText()), 'no dislike or match wording');
  // The seed has two visible companions and the favourites step already saved one of them. Their order under
  // "Recommended" ties on every stat, so the API breaks the tie by profile id (random per seed): either may come
  // first. Save the first card that is not saved yet, skipping with Next, and check Next once more after saving.
  let second = '';
  for (let i = 0; i < 5 && !second; i++) {
    const name = await deckName();
    if (await button('Save').isVisible()) {
      second = name;
      await button('Save').click();
    } else {
      await nextCard(name);
    }
  }
  assert(second, 'a card that is not yet saved');
  await page.getByText(/Added to favourites/i).first().waitFor();
  await button('Saved').waitFor();
  // Next is always exercised: before the save when the saved card came first, or here when cards remain after it.
  const [pos, total] = (await page.getByText(/^\d+ of \d+/).first().innerText()).match(/^(\d+) of (\d+)/).slice(1).map(Number);
  if (pos < total) await nextCard(second);
  const favs = (await authed('/discovery/favorites')).body.map((c) => c.display_name);
  assert(favs.includes(second), `favourites on the server must hold ${second}: ${favs}`);
  await noSideScroll('cards');
  await axe('cards');
  await page.getByRole('radio', { name: 'List' }).click();
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
  // Owner, 2026-11-18: deletion is a 1.5 s hold-to-confirm button (no dialog); an early release does nothing and a
  // non-hold activation (screen reader) opens an explicit two-step confirmation.
  const del = page.getByRole('button', { name: 'Delete account', exact: true });
  await del.scrollIntoViewIfNeeded();
  const box = await del.boundingBox();
  let posted = 0;
  const onReq = (r) => r.method() === 'POST' && r.url().endsWith('/account/deletion') && posted++;
  page.on('request', onReq);
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.getByText('Confirming…').first().waitFor();
  await page.waitForTimeout(600);
  await page.mouse.up();
  await page.waitForTimeout(1500);
  assert(posted === 0, 'an early release sends nothing');
  await del.evaluate((el) => el.click()); // activation without a hold, like a screen-reader double-tap
  await button('Yes, delete').waitFor();
  await axe('delete two-step');
  await button('No').click();
  await page.waitForTimeout(300);
  assert(posted === 0, '"No" sends nothing');
  page.off('request', onReq);
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

await step('settings: notification sound switch (default on, saved on the device) and the test button', async () => {
  const sw = page.getByRole('switch', { name: 'Notification sound', exact: true });
  await sw.waitFor();
  assert((await sw.getAttribute('aria-checked')) === 'true', 'sound switch should default to ON');
  await sw.click();
  assert((await sw.getAttribute('aria-checked')) === 'false', 'sound switch should turn OFF');
  assert((await page.evaluate(() => localStorage.getItem('yondo.notifySound'))) === 'off', 'switch not saved on the device');
  await button('Test the sound').click(); // a refused or silent play() must never raise an error
  await sw.click();
  assert((await sw.getAttribute('aria-checked')) === 'true', 'sound switch should turn ON again');
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
