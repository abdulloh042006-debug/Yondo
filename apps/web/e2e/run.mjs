// End-to-end browser tests against the REAL FastAPI backend (see server.py for the test doubles).
// Runs the production build through `vite preview`, whose /api proxy forwards to the backend.
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { chromium } from 'playwright-core';

const require = createRequire(import.meta.url);
const AXE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const API = 'http://127.0.0.1:8000';
const WEB = 'http://127.0.0.1:4173';
const PY = process.env.YONDO_PY ?? 'python';
const reuse = process.env.E2E_REUSE === '1';
mkdirSync('e2e/.tmp', { recursive: true });
mkdirSync('e2e/shots', { recursive: true });

const children = [];
function start(cmd, args, readyText) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    children.push(p);
    let buf = '';
    const onData = (d) => {
      buf += d.toString();
      if (buf.includes(readyText)) resolve(p);
    };
    p.stdout.on('data', onData);
    p.stderr.on('data', onData);
    p.on('exit', (c) => reject(new Error(`${cmd} exited ${c}: ${buf.slice(-400)}`)));
    setTimeout(() => reject(new Error(`timeout starting ${cmd}: ${buf.slice(-400)}`)), 60000);
  });
}

const results = [];
async function step(name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`PASS  ${name}`);
  } catch (e) {
    results.push({ name, ok: false, error: String(e.message ?? e).split('\n')[0] });
    console.log(`FAIL  ${name}\n      ${String(e.message ?? e).split('\n').slice(0, 3).join('\n      ')}`);
  }
}
const assert = (cond, msg) => {
  if (!cond) throw new Error(msg);
};

/** Kirish opens on username/phone + password (2026-11-15); the code path is one tap away. */
async function toCodeLogin(page, label = 'Telegram orqali kod bilan kiriş') {
  await page.goto(`${WEB}/login`);
  await page.getByRole('button', { name: label }).click();
}
/** Every DEMO account starts without a password; the e2e user sets one the way a person would. */
const e2ePassword = (phone) => `e2e pass ${phone.slice(-4)}`;
const e2eUsername = (phone) => `e2e${phone.slice(-9)}`; // all 9 digits: two DEMO numbers share their last 4
async function finishSetup(page, phone) {
  const me = await page.evaluate(async () => (await fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}` } })).json());
  if (!me.password_setup_required) return;
  await page.getByRole('heading', { name: 'Login va parol yarating', level: 1 }).waitFor();
  await page.waitForTimeout(600); // the page transition after sign-in replaces the first copy of the form
  await page.getByLabel('Login', { exact: true }).fill(e2eUsername(phone));
  await page.getByLabel('Yangi parol').fill(e2ePassword(phone));
  await page.getByLabel('Parolni takrorlang').fill(e2ePassword(phone));
  await page.getByRole('button', { name: 'Saqlaş va davom etiş' }).click();
  await page.getByRole('heading', { name: 'Login va parol yarating' }).waitFor({ state: 'detached' });
}

async function otpLogin(page, phone, { setup = true } = {}) {
  await toCodeLogin(page);
  await page.getByLabel('Telefon raqami').fill(phone);
  await page.locator('.consent input').check(); // explicit consent to the terms + privacy policy
  await page.getByRole('button', { name: 'Kod yuboriş' }).click();
  const code = (await page.locator('b.mono').first().innerText()).trim();
  await page.getByLabel('Tasdiqlaş kodi').fill(code);
  await page.getByRole('button', { name: 'Kiriş', exact: true }).click();
  await page.waitForURL((u) => !u.pathname.startsWith('/login'));
  if (setup) await finishSetup(page, phone);
}

async function axeScan(page, label) {
  await page.evaluate(AXE);
  const out = await page.evaluate(async () => {
    const r = await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'], resultTypes: ['violations'] });
    return r.violations.filter((v) => ['serious', 'critical'].includes(v.impact)).map((v) => `${v.id}(${v.nodes.length}) e.g. ${v.nodes.slice(0, 3).map((n) => n.target.join(' ') + ' ' + (n.any[0]?.message ?? '').slice(0, 90)).join(' || ')}`);
  });
  assert(out.length === 0, `axe ${label}: ${out.join(', ')}`);
}

try {
  if (!reuse) {
    mkdirSync('e2e/.tmp', { recursive: true });
    await start(PY, ['e2e/server.py', '8000', `e2e/.tmp/run-${Date.now()}.db`], 'SEED_DONE');
    await new Promise((r) => setTimeout(r, 1500));
    // Run vite through node itself: spawning `npx` fails on Windows (npx.cmd needs a shell).
    await start(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', '4173', '--host', '127.0.0.1'], '4173');
  }

  const browser = await chromium.launch({ executablePath: process.env.CHROME ?? '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const problems = [];
  const watch = (page, tag) => {
    page.on('pageerror', (e) => problems.push(`${tag} pageerror: ${e.message}`));
    page.on('console', (m) => {
      if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|Failed to load resource/.test(m.text() + m.location().url)) problems.push(`${tag} console: ${m.text()}`);
    });
  };
  // The assertions below use the 2026 Uzbek alphabet (the source spelling of uz.ts). Until 2027-04-22 the app's
  // default is the 1995 alphabet, so every context starts on 2026 unless a step chose otherwise; the default
  // itself is covered by the "Uzbek alphabet" step, which uses a context without this script.
  const NEW_ALPHABET_DEFAULT = Date.now() >= Date.parse('2027-04-22T00:00:00+05:00');
  // The opening animation (index.html + ui/Intro.tsx) covers the home page until its first list has arrived. Every
  // context switches it off, except the "opening animation" steps, which ask for it with `intro: true`.
  const noIntro = () => {
    try {
      localStorage.setItem('yondo.intro.off', '1');
    } catch {
      /* storage unavailable */
    }
  };
  const ctx = async ({ intro = false, ...opts } = {}) => {
    const c = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'uz-UZ', ...opts });
    await c.addInitScript(() => {
      try {
        if (!localStorage.getItem('yondo.uzAlphabet')) localStorage.setItem('yondo.uzAlphabet', '2026');
      } catch {
        /* storage unavailable */
      }
    });
    if (!intro) await c.addInitScript(noIntro);
    return c;
  };

  /* ----------------------------------------------------- anonymous discovery */
  const anon = await ctx();
  const page = await anon.newPage();
  watch(page, 'anon');
  await step('discovery lists only publicly active DEMO companions', async () => {
    await page.goto(WEB);
    await page.getByText('DEMO Madina').first().waitFor();
    const text = await page.locator('main').innerText();
    assert(text.includes('DEMO Jasur'), 'Jasur missing');
    assert(!text.includes('DEMO Sevara'), 'unapproved Sevara must not be listed');
    assert(text.includes('Şaxsi tasdiqlangan'), 'verified badge expected from API verified=true');
  });
  await step('glass surfaces really use backdrop-filter', async () => {
    const bf = await page.evaluate(() => getComputedStyle(document.querySelector('.glass')).backdropFilter || getComputedStyle(document.querySelector('.glass')).webkitBackdropFilter);
    assert(bf && bf !== 'none', `backdrop-filter=${bf}`);
  });
  await step('search + service/price filters hit the real API', async () => {
    await page.getByLabel('Ism yoki tavsif böyiça qidiriş').fill('Jasur');
    await page.getByRole('button', { name: 'Qidiriş' }).first().click();
    await page.waitForFunction(() => { const t = document.body.innerText; return t.includes('DEMO Jasur') && !t.includes('DEMO Madina'); });
    assert((await page.locator('main').innerText()).includes('DEMO Jasur'), 'Jasur expected');
    await page.getByRole('button', { name: /Hammasini tozalaş/ }).click();
    await page.getByText('DEMO Madina').first().waitFor();
    await page.getByRole('button', { name: /^Filtrlar/ }).click();
    await page.getByLabel('Eng yuqori narx (söm)').fill('50000');
    await page.getByRole('button', { name: 'Natijalarni körsatiş' }).click();
    await page.waitForFunction(() => { const t = document.body.innerText; return t.includes('DEMO Jasur') && !t.includes('DEMO Madina'); });
    assert((await page.locator('main').innerText()).includes('DEMO Jasur'), 'cheaper Jasur expected');
  });
  await step('empty state with clear-filters action', async () => {
    await page.goto(`${WEB}/?q=zzzz-yoq`);
    await page.getByText('Mos hamroh topilmadi').waitFor();
    await page.getByRole('button', { name: 'Filtrlarni tozalaş' }).click();
    await page.getByText('DEMO Madina').first().waitFor();
  });
  await step('profile shows bio, services, prices, honest availability note', async () => {
    await page.goto(WEB);
    await page.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await page.getByRole('heading', { name: 'DEMO Madina', level: 1 }).waitFor();
    const t = await page.locator('main').innerText();
    assert(t.includes('150 000 söm'), 'price 150 000 söm');
    assert(t.includes('Kofe') && t.includes('Sayr'), 'service labels');
    assert(t.includes('Tillar') && t.includes('Qiziqişlar'), 'languages/interests');
    assert(t.includes('mavjudlikni bron paytida server tekşiradi'), 'availability honesty note');
    await page.waitForTimeout(1500); // let reveal animations finish (axe would sample half-faded text)
    await axeScan(page, 'profile');
  });
  await step('404 profile shows friendly state', async () => {
    await page.goto(`${WEB}/c/00000000-0000-0000-0000-000000000000`);
    await page.getByText('Profil topilmadi').waitFor();
  });
  await step('anonymous booking click goes to login; admin URL redirects to login', async () => {
    await page.goto(WEB);
    await page.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await page.getByRole('button', { name: 'Bron qiliş' }).click();
    await page.waitForURL(/\/login/);
    await page.goto(`${WEB}/admin`);
    await page.waitForURL(/\/login/);
  });
  await step('login validation: bad phone + wrong code are shown in Uzbek, from error codes', async () => {
    await toCodeLogin(page);
    await page.getByLabel('Telefon raqami').fill('+99');
    await page.getByRole('button', { name: 'Kod yuboriş' }).click();
    await page.getByText('Davom etiş uçun rozilik belgisini qöying.').waitFor(); // consent first, unticked by default
    await page.getByLabel(/Foydalaniş şartlari va maxfiylik siyosati bilan tanişdim/).check();
    await page.getByRole('button', { name: 'Kod yuboriş' }).click();
    await page.getByText('Telefon raqami notöğri').waitFor();
    await page.getByLabel('Telefon raqami').fill('+998901110099');
    await page.getByRole('button', { name: 'Kod yuboriş' }).click();
    await page.getByLabel('Tasdiqlaş kodi').fill('000000');
    await page.getByRole('button', { name: 'Kiriş', exact: true }).click();
    await page.getByText('Kod notöğri').waitFor();
  });
  await axeScan(page, 'login').then(() => results.push({ name: 'axe login', ok: true }), (e) => results.push({ name: 'axe login', ok: false, error: e.message }));

  /* Telegram delivery (stubbed: the e2e server only has the development provider, which shows the code on screen).
     The dev path above is unchanged; these steps cover what appears when the API reports delivery_channel. */
  const OTP_REQUEST = '**/api/v1/auth/otp/request';
  const reply = (status, body) => (r) => r.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  const submitPhone = async (p) => {
    await toCodeLogin(p);
    await p.getByLabel('Telefon raqami').fill('+998901110055');
    await p.locator('.consent input').check();
    await p.getByRole('button', { name: 'Kod yuboriş' }).click();
  };
  await step('login (Telegram channel): instructions instead of an on-screen code, digits only, no SMS promise', async () => {
    await page.route(OTP_REQUEST, reply(200, { message: 'sent', expires_in_seconds: 300, resend_after_seconds: 60, delivery_channel: 'telegram' }));
    try {
      await submitPhone(page);
      await page.getByRole('heading', { name: 'Kod Telegramʼga yuborildi' }).waitFor();
      assert((await page.locator('b.mono').count()) === 0, 'no dev code may be shown for the Telegram channel');
      const text = await page.locator('main').innerText();
      assert(text.includes('Verification Codes') && text.includes('Kod 5 daqiqa amal qiladi'), 'Telegram instructions + validity expected');
      assert(!/SMS/.test(text), 'the Telegram screen must not mention SMS');
      const code = page.getByLabel('Tasdiqlaş kodi');
      await code.waitFor();
      assert(await code.evaluate((el) => el === document.activeElement), 'code field should be focused');
      assert((await code.getAttribute('autocomplete')) === 'one-time-code' && (await code.getAttribute('inputmode')) === 'numeric', 'one-time-code + numeric');
      await code.fill('123 456');
      assert((await code.inputValue()) === '123456', 'a pasted "123 456" must keep all six digits');
      await code.fill('12a34b5678');
      assert((await code.inputValue()) === '123456', 'digits only, max 6');
      const toggle = page.getByRole('button', { name: 'Telegramim yöq' });
      assert((await toggle.getAttribute('aria-expanded')) === 'false', 'collapsed by default');
      await toggle.click();
      await page.getByText('Hozirça kod faqat Telegram orqali yuboriladi.').waitFor();
      assert((await toggle.getAttribute('aria-expanded')) === 'true', 'expanded after click');
      assert(!/SMS/.test(await page.locator('main').innerText()), 'the no-Telegram text must not promise SMS');
      await page.waitForTimeout(800); // let the entrance animation finish before axe samples colours
      await axeScan(page, 'login (telegram)');
    } finally {
      await page.unroute(OTP_REQUEST);
    }
  });
  await step('login (Telegram channel): delivery errors come from the error code, shown on the phone step', async () => {
    const cases = [
      [422, 'otp_channel_unavailable', 'Telegram hisobi topilmadi'],
      [502, 'otp_delivery_failed', 'Kodni yuborib bölmadi'],
      [503, 'otp_delivery_unavailable', 'Kod yuboriş xizmati hozirça ulanmagan'],
    ];
    for (const [status, code, text] of cases) {
      await page.route(OTP_REQUEST, reply(status, { code, message: 'x', request_id: 'req-otp' }));
      try {
        await submitPhone(page);
        await page.getByText(text).first().waitFor();
        assert(await page.getByRole('button', { name: 'Kod yuboriş' }).isEnabled(), `${code}: the form must stay usable`);
        assert((await page.getByLabel('Tasdiqlaş kodi').count()) === 0, `${code}: must stay on the phone step`);
        if (code === 'otp_channel_unavailable') {
          assert((await page.getByLabel('Telefon raqami').getAttribute('aria-invalid')) === 'true', 'channel error belongs to the phone field');
        }
      } finally {
        await page.unroute(OTP_REQUEST);
      }
    }
  });

  /* --------------------------------------------------------------- customer */
  const cust = await ctx();
  const cp = await cust.newPage();
  watch(cp, 'customer');
  await step('customer OTP login → redirected back, session persists across reload', async () => {
    await otpLogin(cp, '+998901110003');
    await cp.goto(`${WEB}/account`);
    await cp.getByText('Hisobim').first().waitFor();
    await cp.reload();
    await cp.getByText('+998 90 111 00 03').waitFor();
  });
  await step('password (owner, 2026-11-15): set up after a code, sign in by username and by phone, wrong password, lockout, change, reset', async () => {
    const PHONE = '+998907770066';
    const pw1 = 'e2e first pass';
    const pw2 = 'e2e second pass';
    const pw3 = 'e2e third pass';
    const contexts = [];
    const fresh = async (label) => {
      const c = await ctx();
      contexts.push(c);
      const p = await c.newPage();
      watch(p, label);
      return p;
    };
    const signIn = async (p, login, password) => {
      await p.goto(`${WEB}/login`);
      await p.getByLabel('Login yoki telefon raqami').fill(login);
      await p.getByLabel('Parol', { exact: true }).fill(password);
      await p.getByRole('button', { name: 'Kiriş', exact: true }).click();
    };
    const meStatus = (p) => p.evaluate(async () => (await fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}` } })).status);
    try {
      // 1. Registration: a code sign-in, then the forced setup screen with a live username check.
      const a = await fresh('pw-setup');
      await otpLogin(a, PHONE, { setup: false });
      await a.getByRole('heading', { name: 'Login va parol yarating', level: 1 }).waitFor();
      await a.waitForTimeout(600); // let the page transition after sign-in finish
      const name = a.getByLabel('Login', { exact: true });
      assert((await name.getAttribute('autocomplete')) === 'username', 'username autocomplete');
      assert((await a.getByLabel('Yangi parol').getAttribute('autocomplete')) === 'new-password', 'new-password autocomplete');
      await name.fill(e2eUsername('+998901110003')); // taken by the customer above
      await a.getByText('Bu login band.').waitFor();
      await name.fill('admin'); // reserved
      await a.getByText('Bu loginni tanlab bölmaydi.').waitFor();
      await name.fill('E2E.Pass');
      await a.getByText('Bu login böş.').waitFor();
      await a.getByLabel('Yangi parol').fill('998907770066');
      await a.getByLabel('Parolni takrorlang').fill('998907770066');
      await a.getByRole('button', { name: 'Saqlaş va davom etiş' }).click();
      await a.getByText('Parol telefon raqamingiz bölmasin.').waitFor();
      await a.getByLabel('Yangi parol').fill(pw1);
      await a.getByLabel('Parolni takrorlang').fill(pw1);
      await a.waitForTimeout(400);
      await axeScan(a, 'password setup');
      await a.getByRole('button', { name: 'Saqlaş va davom etiş' }).click();
      await a.getByRole('heading', { name: 'Login va parol yarating' }).waitFor({ state: 'detached' });
      const me = await a.evaluate(async () => (await fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}` } })).json());
      assert(me.username === 'e2e.pass' && me.has_password && !me.password_setup_required, `account complete: ${JSON.stringify(me).slice(0, 160)}`);

      // 2. Sign in with the username, then with the phone (any spelling).
      const b = await fresh('pw-username');
      await signIn(b, 'E2E.Pass', pw1);
      await b.waitForURL((u) => !u.pathname.startsWith('/login'));
      const c = await fresh('pw-phone');
      await signIn(c, '+998 90 777 00 66', pw1);
      await c.waitForURL((u) => !u.pathname.startsWith('/login'));

      // 3. A wrong password: one neutral answer, tied to the password field, the field is emptied.
      const d = await fresh('pw-wrong');
      await signIn(d, 'e2e.pass', 'not the password');
      await d.getByText('Login yoki parol notöğri.').waitFor();
      const pwField = d.getByLabel('Parol', { exact: true });
      assert((await pwField.getAttribute('aria-invalid')) === 'true' && (await pwField.inputValue()) === '', 'error on the password field, which is emptied');
      await axeScan(d, 'login (password error)');

      // 4. Lockout after 5 failures (an unknown login is locked the same way, so nothing leaks).
      for (let i = 0; i < 5; i += 1) {
        await signIn(d, 'nobody.e2e', `wrong ${i}`);
        await d.getByText('Login yoki parol notöğri.').waitFor();
      }
      await signIn(d, 'nobody.e2e', 'wrong again');
      await d.getByText(/parol bilan kiriş 15 daqiqaga yopildi/).waitFor();

      // 5. Change password in Settings → Hisob: other devices are signed out, this one stays.
      await a.goto(`${WEB}/settings`);
      await a.getByText('Login: e2e.pass').waitFor();
      await a.getByRole('button', { name: 'Parolni almaştiriş' }).click();
      await a.getByText(/boşqa qurilmalardagi seanslar yopiladi/).waitFor();
      await a.getByLabel('Hozirgi parol').fill('wrong current');
      await a.getByLabel('Yangi parol').fill(pw2);
      await a.getByLabel('Parolni takrorlang').fill(pw2);
      await a.getByRole('button', { name: 'Parolni saqlaş' }).click();
      await a.getByText('Hozirgi parol notöğri.').waitFor();
      await a.getByLabel('Hozirgi parol').fill(pw1);
      await a.getByRole('button', { name: 'Parolni saqlaş' }).click();
      await a.getByText('Parol almaştirildi. Boşqa qurilmalardagi seanslar yopildi.').waitFor();
      assert((await meStatus(a)) === 200, 'this device stays signed in');
      assert((await meStatus(b)) === 401, 'another device is signed out after the change');

      // 6. Forgotten password: phone → code → new password; every old session ends.
      const e = await fresh('pw-reset');
      await e.goto(`${WEB}/login`);
      await e.getByRole('button', { name: 'Parolni unutdingizmi?' }).click();
      await e.getByRole('heading', { name: 'Parolni tiklaş', level: 1 }).waitFor();
      await e.getByLabel('Telefon raqami').fill(PHONE);
      await e.getByRole('button', { name: 'Kod yuboriş' }).click();
      const code = (await e.locator('b.mono').first().innerText()).trim();
      await e.getByLabel('Tasdiqlaş kodi').fill(code);
      await e.getByLabel('Yangi parol').fill(pw3);
      await e.getByLabel('Parolni takrorlang').fill(pw3);
      await e.getByRole('button', { name: 'Parolni saqlaş va kiriş' }).click();
      await e.waitForURL((u) => !u.pathname.startsWith('/login'));
      assert((await meStatus(a)) === 401, 'a reset signs out every old session');
      const f = await fresh('pw-after-reset');
      await signIn(f, 'e2e.pass', pw3);
      await f.waitForURL((u) => !u.pathname.startsWith('/login'));
    } finally {
      for (const c of contexts) await c.close();
    }
  });
  await step('favorite toggles only after the server confirms', async () => {
    await cp.goto(WEB);
    await cp.getByText('DEMO Madina').first().waitFor();
    await cp.getByRole('button', { name: /DEMO Madinani sevimlilarga qöşiş|DEMO Madina.*sevimlilarga qöşiş/ }).first().click();
    await cp.getByText('Sevimlilarga qöşildi.').waitFor();
    await cp.goto(`${WEB}/favorites`);
    await cp.getByText('DEMO Madina').first().waitFor();
  });
  const authed = (pg, path, init = {}) =>
    pg.evaluate(async ([path, init]) => {
      const r = await fetch(`/api/v1${path}`, { ...init, headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}`, ...(init.headers ?? {}) } });
      return { status: r.status, body: r.status === 204 ? null : await r.json() };
    }, [path, init]);
  const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');
  await step('Profil photos (owner, 2026-11-14): upload PNG, privacy note, main photo, delete — on the real API', async () => {
    await cp.goto(`${WEB}/account`);
    await cp.getByRole('heading', { name: /Rasmlarim/ }).waitFor();
    assert(/bron sörovi yuborgan hamrohlar/.test(await cp.locator('main').innerText()), 'customer privacy note expected');
    for (const name of ['a.png', 'b.png']) {
      await cp.locator('[data-testid=photo-input]').setInputFiles({ name, mimeType: 'image/png', buffer: PNG });
      await cp.getByText('Rasm yuklandi.').last().waitFor();
      await cp.getByText('Rasm yuklandi.').last().waitFor({ state: 'detached', timeout: 8000 }).catch(() => {});
    }
    await cp.getByAltText('Mening rasmim, 2').waitFor();
    const before = (await authed(cp, '/user-photos/me')).body.map((p) => p.id);
    assert(before.length === 2, `2 photos expected, got ${before.length}`);
    await cp.getByRole('button', { name: 'Asosiy qiliş' }).click();
    await cp.getByText('Asosiy rasm tanlandi.').waitFor();
    const after = (await authed(cp, '/user-photos/me')).body.map((p) => p.id);
    assert(after[0] === before[1] && after[1] === before[0], 'the second photo must become the main one on the server');
    await cp.getByRole('button', { name: 'Öçiriş' }).first().click();
    await cp.getByRole('dialog').getByRole('button', { name: 'Öçiriş' }).click();
    await cp.getByText('Rasm öçirildi.').waitFor();
    const left = (await authed(cp, '/user-photos/me')).body.map((p) => p.id);
    assert(left.length === 1 && left[0] === before[0], 'the main photo was deleted on the server');
    const gif = await (async () => {
      await cp.locator('[data-testid=photo-input]').setInputFiles({ name: 'x.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') });
      return cp.getByRole('alert').filter({ hasText: 'Faqat JPEG, PNG yoki WebP' }).count();
    })();
    assert(gif === 1, 'a GIF is refused before it is sent');
  });
  let madinaId = '';
  await step('Yoqdi: like/unlike with an optimistic count, separate from favourites (real API)', async () => {
    const list = await (await fetch(`${API}/api/v1/discovery/companions?q=Madina`)).json();
    madinaId = list.items[0].id;
    const start = list.items[0].like_count;
    await cp.goto(`${WEB}/c/${madinaId}`);
    const btn = cp.getByRole('button', { name: /profiliga «Yoqdi» bosiş/ });
    await btn.click();
    await cp.getByRole('button', { name: /«Yoqdi»ni olib taşlaş/ }).waitFor();
    await cp.waitForFunction(async ([id, n]) => (await (await fetch(`/api/v1/discovery/companions/${id}`)).json()).like_count === n, [madinaId, start + 1]);
    const anonView = await (await fetch(`${API}/api/v1/discovery/companions/${madinaId}`)).json();
    assert(anonView.like_count === start + 1 && anonView.liked_by_me === null, 'public count +1, no viewer state when anonymous');
    await cp.reload();
    await cp.getByRole('button', { name: /«Yoqdi»ni olib taşlaş/ }).click();
    await cp.getByRole('button', { name: /profiliga «Yoqdi» bosiş/ }).waitFor();
    await cp.waitForFunction(async ([id, n]) => (await (await fetch(`/api/v1/discovery/companions/${id}`)).json()).like_count === n, [madinaId, start]);
    await cp.getByRole('button', { name: /profiliga «Yoqdi» bosiş/ }).click(); // leave one like for the sort step
    await cp.getByRole('button', { name: /«Yoqdi»ni olib taşlaş/ }).waitFor();
    await page.goto(`${WEB}/c/${madinaId}`);
    await page.getByRole('heading', { name: 'DEMO Madina', level: 1 }).waitFor();
    assert((await page.getByRole('button', { name: /Yoqdi/ }).count()) === 0, 'signed out: the count only, no button');
    assert((await page.getByText(/ta «Yoqdi»/).count()) >= 1, 'signed out: the like count is shown');
  });
  await step('filters sheet: stars, category, sort by likes; chips + clear all (real API)', async () => {
    await page.goto(WEB);
    await page.getByText('DEMO Madina').first().waitFor();
    await page.getByRole('button', { name: /^Filtrlar/ }).click();
    const sheet = page.getByRole('dialog', { name: 'Filtrlar' });
    await sheet.getByRole('button', { name: 'Köp «Yoqdi»' }).click();
    await sheet.getByRole('button', { name: 'Natijalarni körsatiş' }).click();
    await page.waitForURL(/sort=likes/);
    await page.waitForFunction(() => document.querySelector('.grid-cards h3')?.textContent?.includes('DEMO Madina'));
    await page.waitForFunction(() => document.querySelector('main select')?.value === 'likes'); // the sort select follows the URL
    await page.getByRole('button', { name: /^Filtrlar/ }).click();
    await sheet.getByRole('button', { name: '4+ ★' }).click();
    await sheet.getByRole('button', { name: 'Kofe' }).click();
    await sheet.getByRole('button', { name: 'Natijalarni körsatiş' }).click();
    await page.waitForURL((u) => u.searchParams.get('rating_min') === '4' && u.searchParams.get('service_code') === 'coffee');
    await page.getByRole('button', { name: '«4+ ★» filtrini olib taşlaş' }).waitFor();
    await page.getByRole('button', { name: /^Filtrlar \(2\)/ }).waitFor();
    await page.getByText(/Mos hamroh topilmadi|DEMO/).first().waitFor();
    await page.getByRole('button', { name: 'Hammasini tozalaş' }).first().click();
    await page.waitForURL((u) => !u.searchParams.get('rating_min') && !u.searchParams.get('service_code') && u.searchParams.get('sort') === 'likes');
    await page.getByLabel('Saralaş', { exact: true }).selectOption('meetings');
    await page.waitForURL(/sort=meetings/);
    await page.getByLabel('Saralaş', { exact: true }).selectOption('default');
    await page.waitForURL((u) => !u.searchParams.get('sort'));
    await page.waitForFunction(() => document.querySelector('main')?.innerText.includes('DEMO Madina'));
  });
  await step('Kartoçkalar: Saqlaş adds to favourites, Keyingisi skips; keyboard path; no dislike/match', async () => {
    await authed(cp, `/discovery/favorites/${madinaId}`, { method: 'DELETE' });
    await cp.goto(`${WEB}/?view=cards&q=DEMO`);
    const deck = cp.getByRole('region', { name: 'Hamroh kartoçkalari' });
    await deck.waitFor();
    const first = await deck.locator('h2').innerText();
    const text = await cp.locator('main').innerText();
    assert(!/dislike|match|yoqmadi/i.test(text), 'no dislike or match wording');
    await cp.getByRole('button', { name: /Keyingisi/ }).click();
    await cp.waitForFunction((f) => document.querySelector('.deck h2') && !document.querySelector('.deck h2').textContent.startsWith(f.split(',')[0]), first);
    const second = (await deck.locator('h2').innerText()).split(',')[0];
    await cp.getByRole('button', { name: /^Saqlaş$/ }).click();
    await cp.getByText('Sevimlilarga qöşildi.').last().waitFor();
    await cp.getByRole('button', { name: /^Saqlangan$/ }).waitFor();
    const favs = (await authed(cp, '/discovery/favorites')).body.map((c) => c.display_name);
    assert(favs.some((n) => second.startsWith(n)), `favourites on the server must hold ${second}: ${favs}`);
    await deck.focus();
    await cp.keyboard.press('ArrowRight');
    await cp.waitForFunction((s) => !document.querySelector('.deck h2')?.textContent?.startsWith(s), second);
    await cp.getByRole('button', { name: 'Röyxat' }).click();
    await cp.locator('.grid-cards').waitFor();
  });
  await step('booking dialog validates, then creates a pending booking on the server', async () => {
    await cp.goto(WEB);
    await cp.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await cp.getByRole('button', { name: 'Bron qiliş' }).click();
    await cp.getByRole('button', { name: 'Sörov yuboriş' }).click();
    await cp.getByText('Boşlaniş vaqtini tanlang.').waitFor();
    await cp.getByText('Uçraşuv joyini yozing').waitFor();
    const d = new Date(Date.now() + 2 * 86400000 + 4 * 3600000 + 5 * 3600000);
    const local = d.toISOString().slice(0, 16);
    await cp.getByLabel('Boşlaniş vaqti (Toşkent vaqti)').fill(local);
    await cp.getByLabel('Uçraşuv joyi').fill('DEMO: Amir Temur xiyoboni');
    await cp.getByRole('button', { name: 'Sörov yuboriş' }).click();
    await cp.waitForURL(/\/bookings/);
    await cp.getByText('Javob kutilmoqda').first().waitFor();
    assert((await cp.locator('main').innerText()).includes('DEMO: Amir Temur xiyoboni'), 'booking place');
  });
  await step('booking an already-reserved slot shows the server refusal (no fake success)', async () => {
    await cp.goto(WEB);
    await cp.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await cp.getByRole('button', { name: 'Bron qiliş' }).click();
    const d = new Date(Date.now() + 2 * 86400000 + 4 * 3600000 + 5 * 3600000);
    await cp.getByLabel('Boşlaniş vaqti (Toşkent vaqti)').fill(d.toISOString().slice(0, 16));
    await cp.getByLabel('Uçraşuv joyi').fill('DEMO: takroriy urinish');
    await cp.getByRole('button', { name: 'Sörov yuboriş' }).click();
    await cp.getByText('Tanlangan vaqt band yoki hamroh böş emas.').waitFor();
    assert(!/\/bookings/.test(cp.url()), 'must stay on profile');
  });
  await step('customer cannot reach admin UI nor admin API (server-side 403)', async () => {
    await cp.goto(`${WEB}/admin`);
    await cp.getByText('Bu bölim siz uçun emas').waitFor();
    const codes = await cp.evaluate(async () => {
      const token = sessionStorage.getItem('yondo.access');
      const h = { Authorization: `Bearer ${token}` };
      const paths = ['/admin/summary', '/admin/users', '/admin/audit-events', '/companions/admin/applications', '/admin/safety/reports'];
      return Promise.all(paths.map(async (p) => (await fetch(`/api/v1${p}`, { headers: h })).status));
    });
    assert(codes.every((c) => c === 403), `expected all 403, got ${codes}`);
  });
  await step('customer cannot self-assign admin role (server refuses)', async () => {
    const status = await cp.evaluate(async () => {
      const token = sessionStorage.getItem('yondo.access');
      const r = await fetch('/api/v1/auth/roles', { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ roles: ['customer', 'admin'] }) });
      return r.status;
    });
    assert(status === 403, `got ${status}`);
  });
  await step('account profile validates age and saves via server', async () => {
    await cp.goto(`${WEB}/account`);
    await cp.getByRole('button', { name: 'Tahrirlaş' }).click(); // Profil shows the data; the form opens on "Tahrirlash"
    await cp.getByLabel('Yoş').fill('12');
    await cp.getByText('Yoş 18 dan 120 gaça bölişi kerak.').waitFor();
    await cp.getByLabel('Yoş').fill('29');
    await cp.getByRole('button', { name: 'Saqlaş' }).click();
    await cp.getByText('Profil saqlandi.').waitFor();
  });
  await step('profile hub → help: trusted contact add/remove, report a booking (server derives the companion), my reports', async () => {
    await cp.goto(`${WEB}/account`);
    await cp.getByRole('link', { name: /Sozlamalar/ }).first().click(); // Profil → Sozlamalar → Yordam (owner, 2026-11-14)
    await cp.getByRole('heading', { name: 'Sozlamalar', level: 1 }).waitFor();
    await cp.getByRole('main').getByRole('link', { name: 'Yordam va xavfsizlik' }).first().click();
    await cp.getByRole('heading', { name: 'Yordam va xavfsizlik', level: 1 }).waitFor();
    assert((await cp.getByRole('link', { name: /112/ }).getAttribute('href')) === 'tel:112', 'emergency number link');
    await cp.getByLabel('Ism', { exact: true }).fill('E2E Ona');
    await cp.getByLabel('Kontakt telefoni').fill('+998 90 123 45 67');
    await cp.getByRole('button', { name: 'Qöşiş' }).click();
    await cp.getByText('Kontakt saqlandi.').waitFor();
    await cp.getByText('+998901234567').waitFor();
    await cp.getByRole('button', { name: 'E2E Ona kontaktini öçiriş' }).click();
    await cp.getByText('Kontakt öçirildi.').waitFor();
    await cp.goto(`${WEB}/bookings`);
    await cp.getByRole('button', { name: 'Muammo haqida xabar beriş' }).first().click();
    await cp.getByText('Şikoyat şu brondagi hamroh haqida yuboriladi.').waitFor();
    await cp.getByRole('button', { name: 'Şikoyatni yuboriş' }).click();
    await cp.getByText('Qisqaça tavsif yozing.').waitFor();
    await cp.getByLabel('Sabab').selectOption('no_show');
    await cp.getByLabel('Nima bölganini yozing').fill('E2E: hamroh kelmadi');
    await cp.getByRole('button', { name: 'Şikoyatni yuboriş' }).click();
    await cp.getByText(/Şikoyat qabul qilindi/).waitFor();
    await cp.goto(`${WEB}/help`);
    await cp.getByText('E2E: hamroh kelmadi').waitFor();
    await cp.getByText('Yuborildi, navbatda').first().waitFor();
  });
  await step('push (owner, 2026-11-18): Settings switch asks only on a tap, registers this browser on the server, off unregisters', async () => {
    // Headless Chromium has no push service, so only PushManager.subscribe is replaced: it returns a subscription with
    // a real P-256 key made by WebCrypto. The permission prompt, the service worker and the API calls are real.
    await cust.grantPermissions(['notifications'], { origin: WEB });
    await cust.addInitScript(() => {
      const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
      const KEY = 'e2e.push.sub';
      const make = (s) => s && { endpoint: s.endpoint, toJSON: () => s, unsubscribe: async () => (sessionStorage.removeItem(KEY), true) };
      PushManager.prototype.getSubscription = async function () {
        return make(JSON.parse(sessionStorage.getItem(KEY) || 'null'));
      };
      PushManager.prototype.subscribe = async function (opts) {
        if (!opts || !opts.userVisibleOnly || !opts.applicationServerKey) throw new Error('bad subscribe options');
        window.__pushAsked = (window.__pushAsked || 0) + 1;
        const pair = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
        const raw = await crypto.subtle.exportKey('raw', pair.publicKey);
        const s = { endpoint: `https://fcm.googleapis.com/fcm/send/e2e-${Date.now()}`, keys: { p256dh: b64u(raw), auth: b64u(crypto.getRandomValues(new Uint8Array(16))) } };
        sessionStorage.setItem(KEY, JSON.stringify(s));
        return make(s);
      };
    });
    await cp.goto(`${WEB}/settings`);
    const sw = cp.getByRole('switch', { name: /Push bildirişnomalar/ });
    await sw.waitFor();
    await cp.getByText(/Öçirilgan\. Yoqsangiz/).waitFor();
    assert(!(await sw.isChecked()), 'off before the tap');
    assert((await cp.evaluate(() => window.__pushAsked || 0)) === 0, 'nothing is subscribed on page load');
    const registered = cp.waitForResponse((r) => r.url().endsWith('/api/v1/push/devices') && r.request().method() === 'PUT');
    await sw.click();
    const reg = await registered;
    assert(reg.status() === 200, `PUT /push/devices should be 200, got ${reg.status()}`);
    await cp.getByText(/Yoqilgan: ilova yopiq/).waitFor();
    assert(await sw.isChecked(), 'on after the tap');
    assert(await cp.evaluate(async () => !!(await navigator.serviceWorker.getRegistration('/sw.js'))), 'the service worker is registered');
    await cp.reload();
    await cp.getByText(/Yoqilgan: ilova yopiq/).waitFor(); // the state survives a reload
    const removed = cp.waitForResponse((r) => /\/api\/v1\/push\/devices\/[0-9a-f-]+$/.test(r.url()) && r.request().method() === 'DELETE');
    await cp.getByRole('switch', { name: /Push bildirişnomalar/ }).click();
    assert((await removed).status() === 204, 'DELETE /push/devices/{id} should be 204');
    await cp.getByText(/Öçirilgan\. Yoqsangiz/).waitFor();
  });
  await step('interface language is saved to the account and follows the user to another device', async () => {
    const other = await ctx();
    const op = await other.newPage();
    watch(op, 'second-device');
    try {
      await cp.goto(`${WEB}/settings`); // the header has no language switch any more (owner, 2026-11-15)
      const saved = cp.waitForResponse((r) => r.url().endsWith('/api/v1/auth/profile') && r.request().method() === 'PUT');
      await cp.locator('.lang-picker').getByRole('button', { name: /Русский/ }).click();
      assert((await (await saved).json()).ui_locale === 'ru', 'PUT /auth/profile should store ru');
      await otpLogin(op, '+998901110003'); // fresh device, Uzbek by default
      await op.getByRole('link', { name: 'Профиль' }).first().waitFor();
      assert((await op.evaluate(() => document.documentElement.lang)) === 'ru', 'second device should switch to ru');
    } finally {
      await cp.locator('.lang-picker').getByRole('button', { name: /Özbekça|O‘zbekcha/ }).click();
      await cp.getByRole('heading', { name: 'Sozlamalar', level: 1 }).waitFor();
      await cp.waitForTimeout(500); // let the PUT back to uz-Latn-2026 land
      await other.close();
    }
  });

  /* ------------------------------------------------ new companion, full path */
  const comp = await ctx();
  const kp = await comp.newPage();
  watch(kp, 'companion');
  await step('new user becomes companion, applies, builds profile, submits for review', async () => {
    await otpLogin(kp, '+998907770001');
    await kp.goto(`${WEB}/settings`); // "Men kimman" moved from Profil to Sozlamalar → Hisob
    await kp.getByRole('button', { name: 'Hamroh', exact: true }).click();
    await kp.getByText('Rollar yangilandi.').waitFor();
    await kp.getByRole('link', { name: 'Hamroh studiyasi' }).first().click();
    await kp.getByRole('tab', { name: 'Ariza' }).click();
    await kp.getByLabel('Özingiz haqingizda qisqaça').fill('E2E: men yangi hamrohman.');
    await kp.getByRole('button', { name: 'Saqlaş' }).click();
    await kp.getByText('Ariza saqlandi.').waitFor();
    await kp.getByRole('button', { name: 'Körib çiqişga yuboriş' }).click();
    await kp.getByText('Ariza körib çiqişga yuborildi.').waitFor();
    await kp.getByText('Körib çiqilmoqda').first().waitFor();
    await kp.getByRole('tab', { name: 'Profil' }).click();
    await kp.getByLabel('Körsatiladigan ism').fill('E2E Dilnoza');
    await kp.getByLabel('Tavsif').fill('E2E profil tavsifi.');
    await kp.getByLabel('Tillar').fill('uz, en');
    await kp.getByRole('button', { name: 'Saqlaş' }).click();
    await kp.getByText('Profil saqlandi.').waitFor();
    await kp.getByRole('tab', { name: 'Xizmatlar' }).click();
    await kp.getByRole('button', { name: 'Xizmat qöşiş' }).click();
    await kp.getByLabel('Narx (söm)').fill('0');
    await kp.getByRole('button', { name: 'Saqlaş' }).click();
    await kp.getByText('Narxni sömda kiriting').waitFor();
    await kp.getByLabel('Narx (söm)').fill('120 000');
    await kp.getByRole('button', { name: 'Saqlaş' }).click();
    await kp.getByText('Xizmat saqlandi.').waitFor();
    await kp.getByRole('tab', { name: 'Profil' }).click();
    await kp.getByRole('button', { name: 'Körib çiqişga yuboriş' }).click();
    await kp.getByText('Profil kontenti körib çiqişga yuborildi.').waitFor();
  });
  await step('status tab explains blockers (content ≠ identity), activation gated', async () => {
    await kp.getByRole('tab', { name: 'Holat' }).click();
    await kp.getByText('Ommaga körinmaydi').waitFor();
    assert((await kp.locator('main').innerText()).includes('Kontent tasdiği şaxs tasdiği emas'), 'distinction note');
  });
  await step('photo upload works against the (in-memory) storage double', async () => {
    await kp.getByRole('tab', { name: 'Rasmlar' }).click();
    const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');
    await kp.locator('input[type=file]').setInputFiles({ name: 'a.png', mimeType: 'image/png', buffer: png });
    await kp.getByText('Rasm yuklandi.').waitFor();
  });

  /* ------------------------------------------------------------------ admin */
  const adm = await ctx();
  const ap = await adm.newPage();
  watch(ap, 'admin');
  await step('admin logs in; dashboard shows real counters', async () => {
    await otpLogin(ap, '+998901110001');
    await ap.goto(`${WEB}/admin`);
    await ap.getByRole('heading', { name: 'Administrator paneli' }).waitFor();
    await ap.getByText('Körib çiqilişi kutilayotgan arizalar').waitFor();
    await ap.waitForTimeout(1500); // counters animate
    const t = await ap.locator('main').innerText();
    assert(/Oçiq şikoyatlar/.test(t) && /Foydalanuvçilar/.test(t), 'tiles');
    await axeScan(ap, 'admin dashboard');
  });
  await step('applications queue shows pending applicants; detail has content + photo + history', async () => {
    await ap.goto(`${WEB}/admin/applications`);
    await ap.getByText('DEMO Sevara').waitFor();
    await ap.getByText('E2E Dilnoza').waitFor();
    await ap.getByRole('link', { name: /E2E Dilnoza/ }).click();
    await ap.getByRole('heading', { name: 'Profil kontenti' }).waitFor();
    await ap.getByText('E2E profil tavsifi.').waitFor();
    const t = await ap.locator('main').innerText();
    assert(t.includes('E2E profil tavsifi.') && t.includes('120 000 söm'), 'content shown');
    assert(t.includes('şaxs tasdiği emas'), 'distinction banner');
  });
  await step('rejecting requires a reason (≥8) and a confirmation; result persists after refresh', async () => {
    await ap.getByRole('button', { name: 'Arizani rad etiş' }).click();
    const confirm = ap.getByRole('button', { name: 'Rad etiş', exact: true });
    assert(await confirm.isDisabled(), 'confirm must be disabled without reason');
    await ap.getByLabel('Rad etiş sababi').fill('qisqa');
    assert(await confirm.isDisabled(), 'still disabled for short reason');
    await ap.getByLabel('Rad etiş sababi').fill('E2E: bayon yetarli emas');
    await confirm.click();
    await ap.getByText('Qaror saqlandi: rad etildi.').waitFor();
    await ap.getByText('Rad etilgan').first().waitFor();
    await ap.reload();
    await ap.getByText('Rad etilgan').first().waitFor();
  });
  await step('applicant sees the rejection reason and can re-submit', async () => {
    await kp.goto(`${WEB}/studio`);
    await kp.getByRole('tab', { name: 'Ariza' }).click();
    await kp.getByText('E2E: bayon yetarli emas').waitFor();
  });
  await step('approve application + approve content: approval ≠ public (activation/identity gates)', async () => {
    await ap.goto(`${WEB}/admin/applications`);
    await ap.getByRole('link', { name: /DEMO Sevara/ }).click();
    await ap.getByRole('button', { name: 'Arizani tasdiqlaş' }).click();
    await ap.getByLabel('Izoh').fill('E2E ok');
    await ap.getByRole('button', { name: 'Tasdiqlaş', exact: true }).click();
    await ap.getByText('Qaror saqlandi: tasdiqlandi.').waitFor();
    await ap.getByRole('button', { name: 'Kontentni tasdiqlaş' }).click();
    await ap.getByLabel('Izoh').fill('E2E kontent ok');
    await ap.getByRole('button', { name: 'Tasdiqlaş', exact: true }).click();
    await ap.waitForFunction(() => document.body.innerText.includes('Faqat “Körib çiqilmoqda” kontentga'));
    const list = await (await fetch(`${API}/api/v1/discovery/companions`)).json();
    assert(!list.items.some((c) => c.display_name === 'DEMO Sevara'), 'Sevara must stay hidden until she requests activation');
  });
  await step('stale decision is refused (409) and UI explains', async () => {
    const msg = await ap.evaluate(async () => {
      const h = { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}`, 'Content-Type': 'application/json' };
      const rows = await (await fetch('/api/v1/companions/admin/applications?status=approved&limit=5', { headers: h })).json();
      const r = await fetch(`/api/v1/companions/admin/applications/${rows[0].id}/decision`, { method: 'POST', headers: h, body: JSON.stringify({ decision: 'approve', expected_revision: 1, note: 'x' }) });
      return r.status;
    });
    assert(msg === 409, `expected 409 got ${msg}`);
  });
  await step('users: filter, masked phones, status change needs reason + typed id, audit recorded', async () => {
    await ap.goto(`${WEB}/admin/users`);
    await ap.getByLabel('Hisob holati').selectOption('verification_pending');
    await ap.waitForFunction(() => document.querySelectorAll('table.data tbody tr').length >= 1);
    const t = await ap.locator('main').innerText();
    assert(!t.includes('901110004') && !t.includes('+998901110004'), 'raw phone leaked');
    await ap.getByRole('button', { name: 'Holatni özgartiriş' }).first().click();
    const dlg = ap.getByRole('dialog');
    const save = dlg.getByRole('button', { name: 'Holatni saqlaş' });
    assert(await save.isDisabled(), 'save disabled initially');
    const shortId = (await dlg.locator('b.mono').first().innerText()).trim();
    await dlg.getByLabel(/Sabab/).fill('E2E: hisob tekshirildi');
    await dlg.getByLabel(/Tasdiqlaş uçun ID/).fill('wrong');
    assert(await save.isDisabled(), 'wrong typed id keeps disabled');
    await dlg.getByLabel(/Tasdiqlaş uçun ID/).fill(shortId);
    await save.click();
    await ap.getByText(/Hisob holati özgartirildi/).waitFor();
  });
  await step('admin rows protect admin accounts and self', async () => {
    await ap.goto(`${WEB}/admin/users`);
    await ap.getByText('Siz', { exact: true }).waitFor();
  });
  await step('audit log shows all consequential actions from the server', async () => {
    await ap.goto(`${WEB}/admin/audit`);
    await ap.getByText('companion_application:reject').first().waitFor();
    const t = await ap.locator('main').innerText();
    for (const a of ['companion_application:approve', 'companion_content:approve', 'account_status:active']) assert(t.includes(a), `missing ${a}`);
  });
  await step('safety: report queue, SOS honesty banner, acknowledge with note', async () => {
    await ap.goto(`${WEB}/admin/safety`);
    await ap.getByText('avtomatik xabar yubormaydi').waitFor();
    await ap.getByText('DEMO shikoyat').waitFor();
    await ap.getByRole('button', { name: 'Körib çiqildi deb belgilaş' }).first().click();
    await ap.getByLabel('Operator izohi').fill('E2E: operator ko‘rib chiqdi');
    await ap.getByRole('button', { name: 'Belgilaş', exact: true }).click();
    await ap.getByText('Körib çiqildi deb qayd etildi.').waitFor();
    await ap.getByRole('button', { name: 'SOS signallari' }).click();
    await ap.getByText('SOS signallari yöq').waitFor();
  });
  await step('admin bookings is read-only and honest about missing admin actions', async () => {
    await ap.goto(`${WEB}/admin/bookings`);
    await ap.getByText('Faqat köriş').waitFor();
    await ap.waitForFunction(() => document.querySelectorAll('table.data tbody tr').length >= 1);
  });

  /* ------------------------------------------------------- 503 / network UX */
  await step('503 is shown as "service unavailable", never as a refusal', async () => {
    const p = await anon.newPage();
    watch(p, 'mock503');
    await p.route('**/api/v1/discovery/companions**', (r) => r.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'identity_status_unavailable', message: 'x', request_id: 'req-123' }) }));
    await p.goto(WEB);
    await p.getByRole('heading', { name: 'Xizmat hozirça mavjud emas' }).waitFor();
    await p.getByText('req-123').waitFor();
    await p.getByRole('button', { name: 'Qayta uriniş' }).waitFor();
    await p.close();
  });

  /* ------------------------------------------------------ responsive/themes */
  await step('legal pages: terms + privacy render as separate pages with version and draft notice', async () => {
    await page.goto(`${WEB}/terms`);
    await page.getByRole('heading', { name: 'Yondo — Foydalanish shartlari', level: 1, exact: true }).waitFor();
    assert((await page.locator('.legal-doc h2').count()) >= 5, 'sections must render as headings (CRLF sources once collapsed into the title)');
    await page.getByText(/Versiya: 2026-10-23-draft/).waitFor();
    await page.getByText(/Loyiha: hujjat hali kuçga kirmagan/).waitFor();
    await page.locator('.site-foot').getByRole('link', { name: 'Maxfiylik siyosati' }).click();
    await page.getByRole('heading', { name: 'Yondo — Maxfiylik siyosati', level: 1 }).waitFor();
    assert((await page.locator('.legal-doc').innerText()).includes('30 kun ichida'), '30-day deletion window stated');
  });
  await step('consent gate: an account without the current consent must accept before using the app', async () => {
    const g = await ctx();
    const gp = await g.newPage();
    watch(gp, 'consent-gate');
    try {
      await gp.route('**/api/v1/account/consents', (route) => (route.request().method() === 'POST' ? route.abort() : route.continue()));
      await otpLogin(gp, '+998907770077', { setup: false }); // the consent POST is lost on purpose
      await gp.getByRole('heading', { name: 'Hujjatlarni qabul qiling', level: 1 }).waitFor();
      await gp.unroute('**/api/v1/account/consents');
      await gp.getByRole('button', { name: 'Qabul qilaman' }).click();
      await gp.getByText('Davom etiş uçun rozilik belgisini qöying.').waitFor();
      await gp.locator('.consent input').check();
      await gp.getByRole('button', { name: 'Qabul qilaman' }).click();
      await gp.getByRole('heading', { name: 'Hujjatlarni qabul qiling' }).waitFor({ state: 'detached' });
      const state = await gp.evaluate(async () => (await fetch('/api/v1/account/consents', { headers: { Authorization: `Bearer ${sessionStorage.getItem('yondo.access')}` } })).json());
      assert(state.required.length === 0 && state.accepted.length === 2, `consents recorded: ${JSON.stringify(state).slice(0, 120)}`);
      await finishSetup(gp, '+998907770077'); // consent first, then the username + password (both gates in order)
    } finally {
      await g.close();
    }
  });
  await step('support: customer sends a request in Help, admin replies, customer sees the reply', async () => {
    await cp.goto(`${WEB}/help`);
    await cp.getByLabel('Mavzu').selectOption('account');
    await cp.getByLabel('Murojaat matni').fill('E2E: shahar maydoni saqlanmayapti');
    await cp.getByRole('button', { name: 'Murojaat yuboriş' }).click();
    await cp.getByText('Murojaat yuborildi. Javob şu yerda körinadi.').waitFor();
    await ap.goto(`${WEB}/admin/support`);
    const card = ap.locator('article', { hasText: 'E2E: shahar maydoni saqlanmayapti' });
    await card.getByLabel('Javob matni').fill('E2E: tuzatildi, qayta urinib köring.');
    await card.getByRole('button', { name: 'Javob yuboriş' }).click();
    await ap.getByText('Javob yuborildi.').waitFor();
    await cp.reload();
    await cp.getByText('E2E: tuzatildi, qayta urinib köring.').waitFor();
    await cp.getByText('Javob berildi').first().waitFor();
  });
  await step('SOS: the Help page button opens a confirmation window; 112 + trusted contact via own phone; location only on tap', async () => {
    await cp.goto(`${WEB}/help`);
    await cp.getByLabel('Ism', { exact: true }).fill('E2E Opa');
    await cp.getByLabel('Kontakt telefoni').fill('+998901234500');
    await cp.getByRole('button', { name: 'Qöşiş' }).click();
    await cp.getByText('Kontakt saqlandi.').waitFor();
    await cust.grantPermissions(['geolocation'], { origin: WEB });
    await cust.setGeolocation({ latitude: 41.31108, longitude: 69.24056, accuracy: 20 });
    // Owner, 2026-11-15: no SOS in the header; it stays on Help (here) and on confirmed/active bookings (S25).
    assert((await cp.locator('header').getByRole('button', { name: /SOS/ }).count()) === 0, 'no SOS in the header');
    await cp.getByRole('main').getByRole('button', { name: /SOS: favqulodda/ }).click();
    const dlg = cp.getByRole('dialog', { name: 'SOS — favqulodda holat' });
    await dlg.waitFor();
    assert((await dlg.getByRole('link', { name: '112 ga qönğiroq qiliş' }).getAttribute('href')) === 'tel:112', 'tel:112');
    await dlg.getByText('Hozir davom etayotgan uçraşuv yöq.').waitFor(); // no fake moderator signal
    await dlg.getByRole('button', { name: 'Joylaşuvimni xabarga qöşiş' }).click();
    await dlg.getByText(/Joylaşuv qöşildi: 41\.31108, 69\.24056/).waitFor();
    const href = await dlg.getByRole('link', { name: 'E2E Opa: SMS yoziş' }).getAttribute('href');
    assert(href.startsWith('sms:+998901234500?&body=') && decodeURIComponent(href).includes('41.31108, 69.24056'), `sms link ${href}`);
    await dlg.getByRole('button', { name: 'Yopiş' }).click();
    await cp.getByRole('button', { name: 'E2E Opa kontaktini öçiriş' }).click();
    await cp.getByText('Kontakt öçirildi.').waitFor();
  });
  await step('block the other participant via a booking, then unblock (no user id in the UI)', async () => {
    await cp.goto(`${WEB}/bookings`);
    await cp.getByRole('button', { name: 'Bloklaş', exact: true }).first().click();
    await cp.getByText(/Mavjud bronlar özgarmaydi/).waitFor();
    await cp.getByRole('dialog').getByRole('button', { name: 'Bloklaş', exact: true }).click();
    await cp.getByText('Foydalanuvçi bloklandi.').waitFor();
    await cp.getByText('Bloklangan', { exact: true }).first().waitFor();
    await cp.getByRole('button', { name: 'Blokdan çiqariş' }).first().click();
    await cp.getByText('Blokdan çiqarildi.').waitFor();
  });
  await step('booking detail: accept → payment shown honestly as unavailable (503) → notification', async () => {
    const m = await ctx();
    const mp2 = await m.newPage();
    watch(mp2, 'madina');
    try {
      await otpLogin(mp2, '+998901110011');
      await mp2.goto(`${WEB}/bookings`);
      const card = mp2.locator('article', { hasText: 'DEMO: Magic City kafesi' });
      await card.getByRole('button', { name: 'Qabul qiliş' }).click();
      await mp2.getByRole('dialog').getByRole('button', { name: 'Qabul qiliş' }).click();
      await mp2.getByText('Bron qabul qilindi.').waitFor();
    } finally {
      await m.close();
    }
    await cp.goto(`${WEB}/settings`);
    await cp.getByRole('link', { name: /Bildirişnomalar/ }).click();
    await cp.getByText('Bron qabul qilindi').first().waitFor();
    await cp.goto(`${WEB}/bookings`);
    await cp.locator('article', { hasText: 'DEMO: Magic City kafesi' }).getByRole('link', { name: 'Batafsil' }).click();
    await cp.getByRole('heading', { name: 'Tölov', level: 2 }).waitFor();
    await cp.getByRole('button', { name: 'Tölovga ötiş' }).click();
    await cp.getByText('Xizmat haqi sozlanmagan: tölov hozirça mumkin emas.').waitFor(); // 503 config, not "declined"
    assert(!(await cp.locator('main').innerText()).includes('Tölangan'), 'never shown as paid');
  });
  await step('meeting flow: chat, both check in, start, SOS moderator signal, both finish, review', async () => {
    await cp.goto(`${WEB}/bookings`);
    await cp.locator('article', { hasText: 'DEMO: Yunusobod bog‘i (tasdiqlangan)' }).getByRole('link', { name: 'Batafsil' }).click();
    await cp.getByRole('heading', { name: 'Uçraşuv', level: 2 }).waitFor();
    const url = cp.url();
    await cp.getByLabel('Xabar', { exact: true }).fill('E2E: men yöldaman');
    await cp.getByRole('button', { name: 'Yuboriş', exact: true }).click();
    await cp.locator('.chat-msg.me', { hasText: 'E2E: men yöldaman' }).waitFor();
    await cp.getByRole('button', { name: 'Keldim' }).click();
    await cp.getByText('Kelganlar: 1 / 2').waitFor();
    const m = await ctx();
    const mp2 = await m.newPage();
    watch(mp2, 'madina-meeting');
    try {
      await otpLogin(mp2, '+998901110011');
      await mp2.goto(url);
      await mp2.locator('.chat-msg.them', { hasText: 'E2E: men yöldaman' }).waitFor();
      await mp2.getByRole('button', { name: 'Keldim' }).click();
      await mp2.getByText('Kelganlar: 2 / 2').waitFor();
      await mp2.getByRole('button', { name: 'Uçraşuvni boşlaş' }).click();
      await mp2.getByText('Davom etmoqda').first().waitFor();
      await cp.reload();
      await cp.getByText('Davom etmoqda').first().waitFor();
      await cp.getByRole('main').getByRole('button', { name: /SOS: favqulodda/ }).first().click(); // the active booking's own SOS
      const dlg = cp.getByRole('dialog', { name: 'SOS — favqulodda holat' });
      await dlg.getByRole('button', { name: /«Sayr» uçraşuvi böyiça signal yuboriş/ }).click();
      await dlg.getByText(/Signal qayd etildi\. Moderator uni qölda körib çiqadi/).waitFor();
      await dlg.getByRole('button', { name: 'Yopiş' }).click();
      await cp.getByRole('button', { name: 'Tugatdim' }).click();
      await cp.getByText('Siz tugaganini tasdiqladingiz; ikkinçi tomon kutilmoqda.').waitFor();
      await mp2.reload();
      await mp2.getByRole('button', { name: 'Tugatdim' }).click();
      await mp2.getByText('Yakunlangan').first().waitFor();
    } finally {
      await m.close();
    }
    await cp.reload();
    await cp.getByRole('heading', { name: 'Şarh', level: 2 }).waitFor();
    await cp.getByRole('button', { name: 'Şarhni yuboriş' }).click();
    await cp.getByText('Bahoni tanlang.').waitFor();
    await cp.getByRole('radio', { name: '5 / 5' }).click();
    await cp.getByLabel('Izoh (ixtiyoriy)').fill('E2E: vaqtida keldi, yoqimli suhbat.');
    await cp.getByRole('button', { name: 'Şarhni yuboriş' }).click();
    await cp.getByText('Sizning bahoyingiz: 5/5').waitFor();
    await cp.getByText('Bron yopilgan: çat faqat öqiş uçun.').waitFor();
  });
  await step('account deletion: refused with open bookings; request → pending (profile hidden) → cancel; admin queue', async () => {
    await cp.goto(`${WEB}/settings#delete`);
    // Owner, 2026-11-18: a 1.5 s hold-to-confirm button replaces the dialog; red only here; early release does nothing.
    const hold = async (page, ms) => {
      const btn = page.getByRole('button', { name: 'Hisobni öçiriş', exact: true });
      await btn.scrollIntoViewIfNeeded();
      const box = await btn.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.waitForTimeout(ms);
      await page.mouse.up();
    };
    const trigger = cp.getByRole('button', { name: 'Hisobni öçiriş', exact: true });
    await trigger.waitFor();
    assert((await trigger.getAttribute('class')).includes('hold'), 'deletion is the hold button');
    assert((await cp.getByRole('button', { name: 'Çiqiş', exact: true }).getAttribute('class')).includes('hold') === false, 'sign-out is a normal button');
    assert((await cp.locator('.overlay').count()) === 0, 'no dialog');
    let sent = 0;
    const count = (r) => r.method() === 'POST' && r.url().endsWith('/account/deletion') && sent++;
    cp.on('request', count);
    await hold(cp, 700); // early release
    await cp.waitForTimeout(1200);
    assert(sent === 0, 'an early release sends nothing');
    await hold(cp, 1700);
    await cp.getByText('Avval oçiq bronlarni yakunlang yoki bekor qiling.').waitFor(); // cp has a pending booking
    assert(sent === 1, 'a full hold sends once');
    cp.off('request', count);
    const d = await ctx();
    const dp = await d.newPage();
    watch(dp, 'deletion');
    try {
      await otpLogin(dp, '+998907770088');
      await dp.goto(`${WEB}/settings`); // account deletion sits in Sozlamalar → Hisob, next to Çiqiş
      // the screen-reader path: activation without a hold opens the explicit two-step confirmation
      await dp.getByRole('button', { name: 'Hisobni öçiriş', exact: true }).evaluate((el) => el.click());
      await dp.getByRole('button', { name: 'Ha, öçiriş' }).click();
      await dp.getByText('Öçiriş sörovi qabul qilindi.').waitFor();
      await dp.getByText(/Öçiriş söralgan: hisob .* dan keyin öçiriladi\./).waitFor();
      await ap.goto(`${WEB}/admin/deletions`);
      await ap.getByText('Kutilmoqda').first().waitFor();
      await dp.getByRole('button', { name: 'Sörovni bekor qiliş' }).click();
      await dp.getByText('Öçiriş sörovi bekor qilindi.').waitFor();
      await dp.getByRole('button', { name: 'Hisobni öçiriş', exact: true }).waitFor();
    } finally {
      await d.close();
    }
  });
  await step('360 px header: logo and navigation only, no SOS/language in it, no overflow, steady while scrolling', async () => {
    const phone = await ctx({ viewport: { width: 360, height: 800 }, isMobile: true, hasTouch: true });
    const pp = await phone.newPage();
    try {
      for (const path of ['/login', '/help']) {
        await pp.goto(`${WEB}${path}`);
        await pp.locator('header.topbar').waitFor();
        await pp.waitForTimeout(1500); // opening animation
        const hdr = pp.locator('header.topbar');
        assert((await hdr.locator('.lang-switch, .sos-btn').count()) === 0, `${path}: header still holds SOS/language`);
        const over = await pp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        assert(over <= 1, `${path}: horizontal overflow ${over}px`);
        // Root cause of the reported shake: the scrolled state shrank the sticky header, scroll anchoring moved the
        // page back under the threshold, the class flipped back... Rest a "finger" at 20 px for 120 frames.
        const flips = await pp.evaluate(async () => {
          const h = document.querySelector('header.topbar');
          const raf = () => new Promise((r) => requestAnimationFrame(r));
          for (let y = 0; y <= 20; y++) { window.scrollTo(0, y); await raf(); }
          let n = 0; let last = h.className; const ys = new Set();
          for (let i = 0; i < 120; i++) { await raf(); ys.add(Math.round(window.scrollY)); if (h.className !== last) { n++; last = h.className; } }
          return { n, ys: [...ys] };
        });
        assert(flips.n === 0 && flips.ys.length === 1, `${path}: header oscillates (${flips.n} flips, scrollY ${flips.ys.join(',')})`);
      }
      await pp.goto(`${WEB}/login`);
      assert((await pp.locator('.login-lang .lang-switch button').count()) === 3, 'UZ | RU | EN on the sign-in page');
    } finally {
      await phone.close();
    }
  });
  const mobile = await ctx({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const mp = await mobile.newPage();
  watch(mp, 'mobile');
  await step('mobile: no horizontal scroll, floating dock visible, booking bar sits above dock', async () => {
    await mp.goto(WEB);
    await mp.getByText('DEMO Madina').first().waitFor();
    const overflow = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert(overflow <= 1, `horizontal overflow ${overflow}px`);
    assert(await mp.locator('.dock').isVisible(), 'dock');
    await mp.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await mp.getByRole('heading', { name: 'DEMO Madina', level: 1 }).waitFor();
    const [bar, dock] = await Promise.all([mp.locator('.book-bar').boundingBox(), mp.locator('.dock').boundingBox()]);
    assert(bar.y + bar.height <= dock.y + 1, `booking bar overlaps dock (${bar.y + bar.height} > ${dock.y})`);
    const small = await mp.evaluate(() => [...document.querySelectorAll('button, a.btn, .dock a, input, select')].filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.height && (r.height < 43.5 || r.width < 43.5) && getComputedStyle(e).visibility !== 'hidden' && !e.classList.contains('sr-only'); }).map((e) => `${e.tagName}.${e.className}:${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`));
    assert(small.length === 0, `targets < 44px: ${small.slice(0, 5).join(', ')}`);
  });
  for (const theme of ['gul', 'rausch', 'stone', 'yondo', 'yondo-tun']) {
    await step(`theme ${theme}: switch persists and screenshots captured`, async () => {
      await mp.goto(`${WEB}/settings`);
      await mp.getByRole('heading', { name: 'Sozlamalar', level: 1 }).waitFor();
      await mp.getByRole('button', { name: new RegExp(`${theme === 'rausch' ? 'Jurnal' : theme === 'gul' ? 'Gul' : theme === 'yondo' ? 'Yondo kunduzgi' : theme === 'yondo-tun' ? 'Yondo tungi' : 'Stone'} mavzusi`) }).click();
      assert((await mp.evaluate(() => document.documentElement.dataset.theme)) === theme, 'data-theme');
      await mp.reload();
      assert((await mp.evaluate(() => document.documentElement.dataset.theme)) === theme, 'theme must persist across reload');
      await mp.goto(WEB);
      assert((await mp.evaluate(() => document.documentElement.dataset.theme)) === theme, 'theme active on other pages');
      assert((await mp.locator('.topbar [aria-label="Mavzu"]').count()) === 0, 'no theme switch in the top bar');
      await mp.getByText('DEMO Madina').first().waitFor();
      await mp.waitForTimeout(900);
      await mp.screenshot({ path: `e2e/shots/mobile-discovery-${theme}.png` });
    });
  }
  await step('desktop screenshots: discovery, profile, admin pages', async () => {
    await page.goto(WEB);
    await page.getByText('DEMO Madina').first().waitFor();
    await page.waitForTimeout(900);
    await page.screenshot({ path: 'e2e/shots/desktop-discovery.png' });
    await page.getByRole('link', { name: /DEMO Madina profilini oçiş/ }).click();
    await page.getByRole('heading', { name: 'DEMO Madina', level: 1 }).waitFor();
    await page.waitForTimeout(900);
    await page.screenshot({ path: 'e2e/shots/desktop-profile.png' });
    for (const [path, name] of [['/admin', 'dashboard'], ['/admin/applications', 'applications'], ['/admin/safety', 'safety'], ['/admin/audit', 'audit']]) {
      await ap.goto(`${WEB}${path}`);
      await ap.waitForTimeout(1600);
      await ap.screenshot({ path: `e2e/shots/admin-${name}.png` });
    }
    await mp.goto(WEB);
    await mp.waitForTimeout(600);
    await mp.screenshot({ path: 'e2e/shots/mobile-discovery.png' });
  });
  const reduced = await ctx({ reducedMotion: 'reduce' });
  const rp = await reduced.newPage();
  watch(rp, 'reduced');
  await step('prefers-reduced-motion: content visible immediately, animations neutralised', async () => {
    await rp.goto(WEB);
    await rp.getByText('DEMO Madina').first().waitFor();
    const dur = await rp.evaluate(() => getComputedStyle(document.querySelector('.aurora i')).animationDuration);
    assert(parseFloat(dur) < 0.01, `aurora animation ${dur}`);
  });

  await step('language: Settings switches uz → ru → en → uz, persists on reload, sets <html lang>, translates API-backed pages', async () => {
    try {
      await page.goto(`${WEB}/settings`);
      await page.locator('.lang-picker').getByRole('button', { name: /Русский/ }).click();
      await page.getByRole('heading', { name: 'Настройки', level: 1 }).waitFor();
      assert((await page.evaluate(() => document.documentElement.lang)) === 'ru', '<html lang> should be ru');
      assert((await page.evaluate(() => document.activeElement?.textContent ?? '')).includes('Русский'), 'focus should stay on the chosen language button');
      await page.goto(WEB); // full reload: the choice must come back from storage
      await page.getByText('DEMO Madina').first().waitFor();
      const ru = await page.locator('main').innerText();
      assert(ru.includes('Найдите компаньона'), 'Russian hero expected');
      assert(ru.includes('Личность подтверждена'), 'verified badge (from API verified=true) should be Russian');
      assert(/сум/.test(ru), 'prices should use the Russian currency word');
      assert(!ru.includes('Şaxsi tasdiqlangan') && !ru.includes('Hammasi'), 'no Uzbek leftovers in Russian UI');
      await toCodeLogin(page, 'Войти по коду через Telegram');
      await page.getByLabel('Номер телефона').fill('+998');
      await page.locator('.consent input').check();
      await page.getByRole('button', { name: 'Отправить код' }).click();
      await page.getByText('Неверный номер телефона').first().waitFor(); // chosen from the error code, in Russian
      await page.goto(`${WEB}/settings`);
      await page.locator('.lang-picker').getByRole('button', { name: /English/ }).click();
      await page.getByRole('heading', { name: 'Settings', level: 1 }).waitFor();
      await page.goto(WEB);
      await page.getByText('DEMO Madina').first().waitFor();
      const en = await page.locator('main').innerText();
      assert(en.includes('Find a companion'), 'English hero expected');
      assert(en.includes('Identity verified'), 'verified badge should be English');
      await page.goto(`${WEB}/settings`);
      await page.locator('.lang-picker').getByRole('button', { name: /Özbekça/ }).click();
      await page.getByRole('heading', { name: 'Sozlamalar', level: 1 }).waitFor();
      assert((await page.evaluate(() => document.documentElement.lang)) === 'uz', '<html lang> should be uz again');
      // Header switch: changing language must not wipe what the user is typing (no remount).
      await page.goto(`${WEB}/login`);
      await page.getByLabel('Login yoki telefon raqami').fill('+998901234567');
      await page.locator('.lang-switch').getByRole('button', { name: /^RU/ }).click();
      await page.getByLabel('Логин или номер телефона').waitFor();
      assert((await page.getByLabel('Логин или номер телефона').inputValue()) === '+998901234567', 'typed login must survive a language switch');
      await page.locator('.lang-switch').getByRole('button', { name: /^UZ/ }).click();
      await page.getByLabel('Login yoki telefon raqami').waitFor();
    } finally {
      await page.evaluate(() => localStorage.removeItem('yondo.lang'));
    }
  });
  await step('Uzbek alphabet: date-based default, Settings switch, and search matches both spellings', async () => {
    const fresh = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'uz-UZ' });
    await fresh.addInitScript(noIntro);
    const fp = await fresh.newPage();
    watch(fp, 'alphabet');
    try {
      await fp.goto(WEB);
      await fp.getByText('DEMO Madina').first().waitFor();
      const first = await fp.locator('main').innerText();
      const want = NEW_ALPHABET_DEFAULT ? 'Şaxsi tasdiqlangan' : 'Shaxsi tasdiqlangan';
      assert(first.includes(want), `default alphabet should show “${want}”`);
      await fp.goto(`${WEB}/settings`);
      await fp.locator('.alphabet-picker').getByRole('button', { name: /Özbekça/ }).click();
      await fp.getByRole('heading', { name: 'Köriniş', level: 2 }).waitFor();
      await fp.goto(WEB);
      await fp.getByText('DEMO Madina').first().waitFor();
      assert((await fp.locator('main').innerText()).includes('Şaxsi tasdiqlangan'), '2026 spelling after the switch');
      // Seed bio is written in the 1995 alphabet ("shahar bo‘ylab"); a 2026-spelled query must still find it.
      await fp.getByLabel('Ism yoki tavsif böyiça qidiriş').fill('ŞAHAR BÖYLAB');
      await fp.getByRole('button', { name: 'Qidiriş' }).first().click();
      await fp.waitForFunction(() => { const t = document.body.innerText; return t.includes('DEMO Madina') && !t.includes('DEMO Jasur'); });
      await fp.goto(`${WEB}/settings`);
      await fp.locator('.alphabet-picker').getByRole('button', { name: /O‘zbekcha/ }).click();
      await fp.getByRole('heading', { name: 'Ko‘rinish', level: 2 }).waitFor();
    } finally {
      await fresh.close();
    }
  });
  for (const lang of ['ru', 'en']) {
    await step(`axe (WCAG2 A/AA serious+critical) with the UI in ${lang}: public pages`, async () => {
      try {
        await page.goto(`${WEB}/settings`);
        await page.evaluate((l) => localStorage.setItem('yondo.lang', l), lang);
        for (const path of ['/', '/login', '/settings', '/help']) {
          await page.goto(`${WEB}${path}`);
          await page.waitForTimeout(1700);
          assert((await page.evaluate(() => document.documentElement.lang)) === lang, `<html lang> on ${path}`);
          await axeScan(page, `${path} [${lang}]`);
        }
      } finally {
        await page.evaluate(() => localStorage.removeItem('yondo.lang'));
      }
    });
  }
  /* ------------------------------------------------------- opening animation */
  // The animation is part of index.html and leaves when the first screen is ready (src/ui/Intro.tsx). To look at it
  // at a known moment these steps hold the home page's first list request and let it go when they are done.
  const LIST = '**/api/v1/discovery/companions**';
  const holdList = async (p) => {
    const held = [];
    await p.route(LIST, (route) => void held.push(route));
    return async () => {
      await p.unroute(LIST);
      await Promise.all(held.map((route) => route.continue().catch(() => {})));
    };
  };
  const useTheme = (id) => {
    try {
      localStorage.setItem('yondo.theme', id);
    } catch {
      /* storage unavailable */
    }
  };
  // how long the overlay stayed, measured in the page from the moment index.html chose the mode
  const stopwatch = () => {
    let seen = false;
    new MutationObserver(() => {
      const on = !!document.getElementById('yi');
      if (window.__yondoIntro?.app && window.__introApp === undefined) window.__introApp = performance.now() - window.__yondoIntro.t0;
      if (on) seen = true;
      else if (seen && window.__introGone === undefined) window.__introGone = performance.now() - window.__yondoIntro.t0;
    }).observe(document, { childList: true, subtree: true });
  };
  // Where the visible mark is just before and at the moment the exit starts (an early exit must not jump), and where
  // the flight ends. Timers and a MutationObserver, not animation frames: a headless page may draw very few of them.
  const markTrack = () => {
    const centre = (sel) => {
      const r = document.querySelector(sel).getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2, r.width];
    };
    let before = null;
    const iv = setInterval(() => {
      const el = document.getElementById('yi');
      if (el && !el.classList.contains('yi-land') && el.querySelector('.yi-sym')) before = centre('.yi-sym');
    }, 20);
    new MutationObserver(() => {
      const el = document.getElementById('yi');
      if (!el || !el.classList.contains('yi-land') || window.__exit) return;
      clearInterval(iv);
      const at = centre('.yi-sym'); // the flight is at its first instant
      for (const a of document.getAnimations()) if (a.effect?.target?.closest?.('#yi')) a.finish(); // ... and now at its end
      window.__exit = { before, at, end: centre('.yi-sym'), logo: centre('.brand .brand-mark') };
    }).observe(document, { attributes: true, attributeFilter: ['class'], subtree: true });
  };
  const yi = (p, mode) => p.locator(`html[data-intro=${mode}] #yi`);
  for (const [theme, viewport] of [['yondo', { width: 390, height: 844 }], ['yondo-tun', { width: 1280, height: 900 }]]) {
    await step(`opening animation [${theme}, ${viewport.width}px]: on screen while the first list loads, axe clean, lands on the header logo when it arrives`, async () => {
      const c = await ctx({ intro: true, viewport });
      await c.addInitScript(useTheme, theme);
      const ip = await c.newPage();
      watch(ip, `intro ${theme}`);
      try {
        await ip.bringToFront(); // a page in the background draws no frames, and these steps look at animated state
        const release = await holdList(ip);
        await ip.goto(WEB, { waitUntil: 'commit' });
        await yi(ip, 'full').waitFor();
        await ip.waitForFunction(() => window.__yondoIntro?.app === true); // the app has mounted underneath and taken over
        const at = await ip.evaluate(() => ({
          inert: document.getElementById('root').inert,
          seen: localStorage.getItem('yondo.intro.v1'),
          theme: document.documentElement.dataset.theme,
          ground: getComputedStyle(document.querySelector('.yi-ground')).backgroundColor,
          buttons: document.querySelectorAll('#yi button:not(#yi-retry)').length,
          message: document.getElementById('yi-msg').hidden,
        }));
        assert(at.inert, 'the app under the overlay must be inert');
        assert(at.seen === '1', 'the first-run flag is written when the app takes over');
        assert(at.theme === theme, `theme ${at.theme}`);
        assert(at.ground === (theme === 'yondo-tun' ? 'rgb(17, 17, 17)' : 'rgb(245, 242, 236)'), `ground colour ${at.ground}`);
        assert(at.buttons === 0 && at.message, 'no skip button and no fallback message');
        await ip.waitForTimeout(3300); // the 2.5 s piece is over and the list has still not arrived
        await ip.waitForFunction(() => getComputedStyle(document.querySelector('.yi-slogan')).opacity === '1', null, { timeout: 3000 }).catch(() => {});
        const mid = await ip.evaluate(() => ({
          up: !!document.getElementById('yi') && !document.getElementById('yi').classList.contains('yi-land'),
          slogan: document.querySelector('.yi-slogan').textContent,
          said: getComputedStyle(document.querySelector('.yi-slogan')).opacity,
          pulse: document.getAnimations().some((a) => a.effect?.target?.classList?.contains('yi-ring1') && a.playState === 'running'),
          logo: getComputedStyle(document.querySelector('.brand .brand-mark')).opacity,
        }));
        assert(mid.up, 'it must stay while the first screen is not ready');
        assert(mid.slogan === 'doim yoningda' && mid.said === '1', `slogan "${mid.slogan}" opacity ${mid.said}`);
        assert(mid.pulse, 'the slow pulse must run while it waits');
        assert(mid.logo === '0', 'the header logo waits while the flying mark is on its way');
        await axeScan(ip, `opening animation [${theme}]`);
        await release();
        await ip.locator('#yi.yi-land').waitFor({ state: 'attached' });
        const off = await ip.evaluate(() => {
          for (const a of document.getAnimations()) if (a.effect?.target?.closest?.('#yi')) a.finish(); // jump to the end of the flight
          const a = document.querySelector('.yi-sym').getBoundingClientRect();
          const b = document.querySelector('.brand .brand-mark').getBoundingClientRect();
          return [a.left - b.left, a.top - b.top, a.width - b.width, a.height - b.height].map((v) => Math.round(Math.abs(v) * 10) / 10);
        });
        assert(Math.max(...off) <= 1, `the mark must land exactly on the header logo, off by ${off.join('/')} px`);
        await ip.locator('#yi').waitFor({ state: 'detached', timeout: 3000 });
        await ip.waitForFunction(() => getComputedStyle(document.querySelector('.brand .brand-mark')).opacity === '1');
        const after = await ip.evaluate(() => ({ inert: document.getElementById('root').inert, on: document.documentElement.classList.contains('yi-on'), mode: document.documentElement.dataset.intro }));
        assert(!after.inert && !after.on && after.mode === 'done', 'the app must be usable once it has left');
        await ip.getByText('DEMO Madina').first().click({ trial: true }); // and clickable
      } finally {
        await c.close();
      }
    });
  }
  await step('opening animation: a quick start is not held back (no 2.5 s wait), a start that never finishes is let go at the 6 s cap', async () => {
    const c = await ctx({ intro: true });
    await c.addInitScript(stopwatch);
    await c.addInitScript(markTrack);
    const ip = await c.newPage();
    watch(ip, 'intro timing');
    try {
      await ip.bringToFront();
      await ip.goto(WEB, { waitUntil: 'commit' });
      await ip.waitForFunction(() => window.__introGone !== undefined, null, { timeout: 5000 });
      // It may leave once the mark has formed (0.7 s) and the first list has arrived, whichever is later; the flight takes 0.62 s.
      const q = await ip.evaluate(() => {
        const list = performance.getEntriesByType('resource').find((r) => r.name.includes('/discovery/companions'));
        return { gone: Math.round(window.__introGone), app: Math.round(window.__introApp), list: list ? Math.round(list.responseEnd - window.__yondoIntro.t0) : null };
      });
      const due = Math.max(700, q.list ?? 0) + 620;
      assert(q.list !== null && q.gone >= due - 100 && q.gone < due + 400, `quick start: gone after ${q.gone} ms, expected about ${due} ms (app took over at ${q.app} ms, list arrived at ${q.list} ms)`);
      assert(q.gone < 2400, `quick start: ${q.gone} ms is not quick (list at ${q.list} ms)`);
      // At this early exit the mark is still in the middle of the frame: the flight must start from there, not jump,
      // and still end exactly on the header logo.
      const x = await ip.evaluate(() => window.__exit);
      assert(x?.before, 'the exit was not observed');
      const jump = Math.hypot(x.at[0] - x.before[0], x.at[1] - x.before[1]);
      assert(Math.abs(x.before[0] - 640) < 12, `before the exit the mark should be in the middle of the 1280 px frame, was at x ${Math.round(x.before[0])}`);
      assert(jump <= 6, `the mark jumped ${Math.round(jump)} px at the moment the exit started (x ${Math.round(x.before[0])} -> ${Math.round(x.at[0])})`);
      const miss = Math.max(Math.abs(x.end[0] - x.logo[0]), Math.abs(x.end[1] - x.logo[1]), Math.abs(x.end[2] - x.logo[2]));
      assert(miss <= 1.5, `an early exit must land on the header logo too, off by ${miss.toFixed(1)} px`);
      await ip.getByText('DEMO Madina').first().click({ trial: true });

      await ip.evaluate(() => localStorage.removeItem('yondo.intro.v1')); // a first visit again, this time the list never answers
      const release = await holdList(ip);
      await ip.goto(WEB, { waitUntil: 'commit' });
      await yi(ip, 'full').waitFor();
      await ip.waitForFunction(() => window.__introGone !== undefined, null, { timeout: 9000 });
      const slow = await ip.evaluate(() => window.__introGone);
      assert(slow >= 6000 && slow < 7600, `no answer: gone after ${Math.round(slow)} ms (cap 6 s + flight)`);
      await ip.locator('.skeleton').first().waitFor(); // the page shows its own loading state
      assert(!(await ip.evaluate(() => document.getElementById('root').inert)), 'the app must be usable after the cap');
      await release();
      await ip.getByText('DEMO Madina').first().waitFor();
    } finally {
      await c.close();
    }
  });
  for (const theme of ['yondo', 'yondo-tun']) {
    await step(`opening animation [${theme}]: when the app's code cannot be loaded it says "no connection" with a retry button instead of animating for ever`, async () => {
      const c = await ctx({ intro: true });
      await c.addInitScript(useTheme, theme);
      const ip = await c.newPage(); // not watched: the failed script load is the point of this step
      try {
        await ip.bringToFront();
        await ip.route('**/assets/*.js', (route) => route.abort());
        await ip.goto(WEB, { waitUntil: 'commit' });
        await ip.getByRole('alert').getByText('Aloqa yöq. Internetni tekşirib, qayta urinib köring.').waitFor();
        const retry = ip.getByRole('button', { name: 'Qayta uriniş' });
        await retry.waitFor();
        assert(!(await ip.evaluate(() => document.getAnimations().some((a) => a.effect?.target?.classList?.contains('yi-ring') && a.playState === 'running'))), 'the pulse must stop');
        assert((await ip.evaluate(() => localStorage.getItem('yondo.intro.v1'))) === null, 'a failed start must not spend the first run');
        await axeScan(ip, `opening animation, no connection [${theme}]`);
        await ip.unroute('**/assets/*.js');
        await retry.click(); // reloads the page
        await ip.getByText('DEMO Madina').first().waitFor();
        await ip.locator('#yi').waitFor({ state: 'detached', timeout: 5000 });
      } finally {
        await c.close();
      }
    });
  }
  await step('opening animation: deep links show nothing, Escape dismisses, later visits get the short form, reduced motion gets one still frame, the switch-off key silences it', async () => {
    const c = await ctx({ intro: true });
    const ip = await c.newPage();
    watch(ip, 'intro later');
    const r = await ctx({ intro: true, reducedMotion: 'reduce' });
    const rp = await r.newPage();
    watch(rp, 'intro reduced');
    try {
      await ip.bringToFront();
      await ip.goto(`${WEB}/login`);
      await ip.getByLabel('Login yoki telefon raqami').waitFor();
      assert((await ip.evaluate(() => document.documentElement.dataset.intro)) === 'off' && (await ip.locator('#yi').count()) === 0, 'no opening animation on a deep link');
      assert((await ip.evaluate(() => localStorage.getItem('yondo.intro.v1'))) === null, 'a deep link must not spend the first run');
      await ip.locator('.brand').first().click(); // in-app navigation home: same page load, still nothing
      await ip.getByText('DEMO Madina').first().waitFor();
      assert((await ip.locator('#yi').count()) === 0, 'in-app navigation must not start it');

      let release = await holdList(ip); // the first cold open at /
      await ip.goto(WEB, { waitUntil: 'commit' });
      await yi(ip, 'full').waitFor();
      await ip.waitForFunction(() => window.__yondoIntro?.app === true);
      await ip.keyboard.press('Escape');
      await ip.locator('#yi').waitFor({ state: 'detached', timeout: 1500 });
      assert(!(await ip.evaluate(() => document.getElementById('root').inert)), 'the app must be usable after Escape');
      await release();

      release = await holdList(ip); // a later cold open: the finished mark, no build
      await ip.reload({ waitUntil: 'commit' });
      await yi(ip, 'short').waitFor();
      await ip.waitForFunction(() => window.__yondoIntro?.app === true);
      assert((await ip.evaluate(() => getComputedStyle(document.querySelector('.yi-wmclip')).display)) === 'none', 'the short form has no wordmark');
      await release();
      await ip.locator('#yi').waitFor({ state: 'detached', timeout: 2500 });
      await ip.getByText('DEMO Madina').first().click({ trial: true });

      await rp.bringToFront();
      release = await holdList(rp);
      await rp.goto(WEB, { waitUntil: 'commit' });
      await yi(rp, 'reduced').waitFor();
      await rp.waitForFunction(() => window.__yondoIntro?.app === true);
      assert((await rp.evaluate(() => document.getAnimations().filter((a) => a.effect?.target?.closest?.('#yi')).length)) === 0, 'reduced motion: nothing may move');
      await release();
      await rp.locator('#yi').waitFor({ state: 'detached', timeout: 2500 });
      await rp.reload();
      await rp.getByText('DEMO Madina').first().waitFor();
      assert((await rp.evaluate(() => document.documentElement.dataset.intro)) === 'off' && (await rp.locator('#yi').count()) === 0, 'reduced motion: nothing on later visits');

      await page.goto(WEB); // every other context of this run carries the switch-off key
      await page.getByText('DEMO Madina').first().waitFor();
      assert((await page.evaluate(() => document.documentElement.dataset.intro)) === 'off' && (await page.locator('#yi').count()) === 0, 'the switch-off key must silence it');
      assert((await page.evaluate(() => localStorage.getItem('yondo.intro.v1'))) === null, 'the switch-off key must not spend the first run');
    } finally {
      await c.close();
      await r.close();
    }
  });
  for (const theme of ['gul', 'rausch', 'stone', 'yondo', 'yondo-tun']) {
    await step(`axe (WCAG2 A/AA serious+critical) in theme ${theme}: public + admin pages`, async () => {
      for (const [pg, path] of [[page, '/'], [page, '/login'], [page, '/settings'], [page, '/help'], [page, '/privacy'], [cp, '/account'], [cp, '/help'], [page, '/?view=cards'], [cp, '/notifications'], [ap, '/admin'], [ap, '/admin/support'], [ap, '/admin/deletions'], [ap, '/admin/applications'], [ap, '/admin/users'], [ap, '/admin/safety'], [ap, '/admin/audit']]) {
        await pg.goto(`${WEB}${path}`);
        await pg.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);
        await pg.waitForTimeout(1700);
        await axeScan(pg, `${path} [${theme}]`);
      }
    });
  }
  await step('no uncaught page errors or console errors during the run', async () => {
    assert(problems.length === 0, problems.slice(0, 4).join(' | '));
  });
  await browser.close();
} catch (e) {
  console.error('HARNESS ERROR', e);
  results.push({ name: 'harness', ok: false, error: String(e) });
} finally {
  for (const c of children) c.kill();
}
const failed = results.filter((r) => !r.ok);
writeFileSync('e2e/.tmp/results.json', JSON.stringify(results, null, 1));
console.log(`\nE2E: ${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
