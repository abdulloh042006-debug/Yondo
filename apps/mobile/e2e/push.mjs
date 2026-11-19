/**
 * Push notifications in the Expo app (owner, 2026-11-18), on the app's web build with a FAKE expo-notifications
 * (window.__YONDO_PUSH_FAKE__, same shape as the native module) and mocked /push/* answers: the web build has no FCM,
 * and the e2e harness has no Firebase project. What it proves: the one-time card, "Yoqish" asking only after a tap,
 * the device registration call, the denied state with "open phone settings", "Keyinroq", the Settings switch, and
 * that sign-out unregisters. What it cannot prove: a real Android permission prompt, a real FCM token or a delivered
 * notification (needs the owner's Firebase project and a phone).
 *
 *   cd apps/mobile && npx expo export --platform web --output-dir <dist>
 *   cd apps/web && YONDO_WEB_DIST=<dist> PYTHONPATH=../api/src python e2e/server.py 8765 <tmp.db>
 *   MOBILE_URL=http://127.0.0.1:8765 node apps/mobile/e2e/push.mjs
 */
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const URL = process.env.MOBILE_URL ?? 'http://127.0.0.1:8765';
const VERSIONS = { terms: '2026-11-19-draft', privacy: '2026-11-19-draft' };

let failed = 0;
const results = [];
const problems = [];
async function step(name, fn) {
  try {
    await fn();
    results.push(`PASS ${name}`);
  } catch (e) {
    failed++;
    results.push(`FAIL ${name}: ${String(e.message).split('\n').slice(0, 3).join(' | ').slice(0, 400)}`);
  }
}
const assert = (ok, msg) => {
  if (!ok) throw new Error(msg);
};

async function call(method, path, body, token) {
  const r = await fetch(`${URL}/api/v1${path}`, {
    method,
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${method} ${path} ${r.status}`);
  return r.status === 204 ? null : r.json();
}
async function signIn(phone, username) {
  const otp = await call('POST', '/auth/otp/request', { phone_number: phone });
  const pair = await call('POST', '/auth/otp/verify', { phone_number: phone, code: otp.development_otp });
  for (const [document, version] of Object.entries(VERSIONS)) await call('POST', '/account/consents', { document, version }, pair.access_token);
  const me = await call('GET', '/auth/me', undefined, pair.access_token);
  if (me.password_setup_required) await call('POST', '/auth/registration', { username, password: `push smoke ${phone.slice(-4)}`, date_of_birth: '1995-05-15' }, pair.access_token);
  return pair;
}

const browser = await chromium.launch({ args: ['--no-sandbox'] });

/** One phone: a fresh context with the fake native module; `perm` is what the OS prompt answers. */
async function phone({ pair, perm = 'granted', android = true, token = 'fcm-token-'.padEnd(64, 'x') }) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  await ctx.addInitScript(
    ([p, answer, tok]) => {
      localStorage.setItem('yondo.locale', 'en');
      localStorage.setItem('yondo.intro.off', '1');
      if (!sessionStorage.getItem('yondo.access')) {
        sessionStorage.setItem('yondo.access', p.access_token);
        sessionStorage.setItem('yondo.refresh', p.refresh_token);
      }
      const log = (window.__pushLog = []);
      let status = sessionStorage.getItem('fake.perm') || 'undetermined';
      window.__YONDO_PUSH_FAKE__ = {
        getPermissionsAsync: async () => ({ status, canAskAgain: status !== 'denied' }),
        requestPermissionsAsync: async () => {
          log.push('ask');
          status = answer;
          sessionStorage.setItem('fake.perm', status);
          return { status, canAskAgain: status !== 'denied' };
        },
        getDevicePushTokenAsync: async () => (log.push('token'), { type: 'android', data: tok }),
        setNotificationChannelAsync: async (id, ch) => (log.push(`channel:${id}:${ch.name}`), null),
      };
    },
    [pair, perm, token],
  );
  const page = await ctx.newPage();
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  const calls = [];
  await page.route('**/api/v1/push/**', async (route) => {
    const req = route.request();
    const path = new globalThis.URL(req.url()).pathname;
    calls.push(`${req.method()} ${path} ${req.postData() ?? ''}`);
    if (path.endsWith('/push/config')) return route.fulfill({ json: { web: { enabled: true, vapid_public_key: null }, android: { enabled: android } } });
    if (req.method() === 'PUT') return route.fulfill({ json: { id: '11111111-2222-4333-8444-555555555555', platform: 'android', created_at: '2026-11-18T10:00:00Z', last_seen_at: '2026-11-18T10:00:00Z' } });
    if (req.method() === 'DELETE') return route.fulfill({ status: 204, body: '' });
    return route.fulfill({ status: 404, json: { code: 'not_found' } });
  });
  await page.goto(URL);
  return { ctx, page, calls, log: () => page.evaluate(() => window.__pushLog) };
}
const openSettings = async (page) => {
  await page.getByRole('tab', { name: 'Profile', exact: true }).click();
  await page.getByRole('button', { name: /^Settings\./ }).click();
};
const pushSwitch = (page) => page.getByRole('switch', { name: 'Push notifications' });

const customer = await signIn('+998901110003', 'push.customer');

await step('after sign-in a one-time card explains push; nothing is asked before "Turn on"', async () => {
  const { ctx, page, calls, log } = await phone({ pair: customer });
  try {
    await page.getByRole('dialog', { name: 'Turn on notifications?' }).waitFor({ timeout: 15000 });
    await page.getByText(/even when the app is closed/).first().waitFor();
    assert(!(await log()).includes('ask'), 'the OS prompt must not open before the tap');
    await page.getByRole('button', { name: 'Turn on', exact: true }).click();
    await page.getByRole('dialog', { name: 'Turn on notifications?' }).waitFor({ state: 'detached' });
    const l = await log();
    assert(l.join(',') === 'channel:yondo:Yondo,ask,token', `channel → ask → token, got ${l}`);
    const put = calls.find((c) => c.startsWith('PUT /api/v1/push/devices'));
    assert(put && JSON.parse(put.split(' ').slice(2).join(' ')).platform === 'android', `PUT /push/devices android, got ${calls}`);
    assert(put.includes('fcm-token-'), 'the FCM token is registered');
    // The card is never shown again.
    await page.reload();
    await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor();
    await page.waitForTimeout(1200);
    assert((await page.getByRole('dialog', { name: 'Turn on notifications?' }).count()) === 0, 'card shown only once');
    // Settings: the switch is on; turning it off unregisters this phone.
    await openSettings(page);
    await page.getByText(/Notifications arrive even when the app is closed|On: notifications arrive/).waitFor();
    assert(await pushSwitch(page).isChecked(), 'switch on');
    await pushSwitch(page).click();
    await page.getByText(/Off\. When you turn it on, the phone asks/).waitFor();
    assert(calls.some((c) => c.startsWith('DELETE /api/v1/push/devices/11111111-')), 'DELETE /push/devices/{id}');
    // On again from Settings, then sign out: the device is unregistered first.
    await pushSwitch(page).click();
    await page.getByText(/On: notifications arrive/).waitFor();
    const before = calls.filter((c) => c.startsWith('DELETE')).length;
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await page.getByRole('tab', { name: 'Sign in', exact: true }).waitFor();
    assert(calls.filter((c) => c.startsWith('DELETE')).length === before + 1, 'sign-out unregisters the device');
  } finally {
    await ctx.close();
  }
});

await step('denied: explained, with a button to the phone settings; the switch shows it too', async () => {
  const pair = await signIn('+998901110003', 'push.customer');
  const { ctx, page, calls } = await phone({ pair, perm: 'denied' });
  try {
    await page.getByRole('dialog', { name: 'Turn on notifications?' }).waitFor({ timeout: 15000 });
    await page.getByRole('button', { name: 'Turn on', exact: true }).click();
    await page.getByText(/turned off in the phone settings/).first().waitFor();
    await page.getByRole('button', { name: 'Open phone settings' }).first().waitFor();
    assert(!calls.some((c) => c.startsWith('PUT')), 'nothing registered after a refusal');
    await page.getByRole('button', { name: 'Later', exact: true }).click();
    await openSettings(page);
    await page.getByText(/turned off in the phone settings/).first().waitFor();
    await page.getByRole('button', { name: 'Open phone settings' }).waitFor();
    assert(!(await pushSwitch(page).isChecked()), 'switch off when denied');
  } finally {
    await ctx.close();
  }
});

await step('"Later" closes the card for good; nothing is asked', async () => {
  const pair = await signIn('+998901110003', 'push.customer');
  const { ctx, page, log } = await phone({ pair });
  try {
    await page.getByRole('dialog', { name: 'Turn on notifications?' }).waitFor({ timeout: 15000 });
    await page.getByRole('button', { name: 'Later', exact: true }).click();
    await page.reload();
    await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor();
    await page.waitForTimeout(1200);
    assert((await page.getByRole('dialog').count()) === 0, 'no card after Later');
    assert(!(await log()).includes('ask'), 'no OS prompt');
  } finally {
    await ctx.close();
  }
});

await step('server without Android push: no card, the switch says it is not set up and is disabled', async () => {
  const pair = await signIn('+998901110003', 'push.customer');
  const { ctx, page } = await phone({ pair, android: false });
  try {
    await page.getByRole('tab', { name: 'Profile', exact: true }).waitFor({ timeout: 15000 });
    await page.waitForTimeout(1200);
    assert((await page.getByRole('dialog').count()) === 0, 'no card when push is not configured');
    await openSettings(page);
    await page.getByText('Push notifications are not set up on the server yet.').waitFor();
    assert(await pushSwitch(page).isDisabled(), 'switch disabled');
  } finally {
    await ctx.close();
  }
});

await step('no page errors', async () => {
  assert(problems.length === 0, problems.slice(0, 5).join(' | '));
});

await browser.close();
console.log(results.join('\n'));
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
