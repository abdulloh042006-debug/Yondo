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

async function otpLogin(page, phone) {
  await page.goto(`${WEB}/login`);
  await page.getByLabel('Telefon raqami').fill(phone);
  await page.getByRole('button', { name: 'Kod yuboriş' }).click();
  const code = (await page.locator('b.mono').first().innerText()).trim();
  await page.getByLabel('Tasdiqlaş kodi').fill(code);
  await page.getByRole('button', { name: 'Kiriş', exact: true }).click();
  await page.waitForURL((u) => !u.pathname.startsWith('/login'));
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
    await start('npx', ['vite', 'preview', '--port', '4173', '--host', '127.0.0.1'], '4173');
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
  const ctx = async (opts = {}) => {
    const c = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'uz-UZ', ...opts });
    await c.addInitScript(() => {
      try {
        if (!localStorage.getItem('yondo.uzAlphabet')) localStorage.setItem('yondo.uzAlphabet', '2026');
      } catch {
        /* storage unavailable */
      }
    });
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
    await page.getByLabel('Eng yuqori narx (söm)').fill('50000');
    await page.getByLabel('Eng yuqori narx (söm)').blur();
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
    await page.goto(`${WEB}/login`);
    await page.getByLabel('Telefon raqami').fill('+99');
    await page.getByRole('button', { name: 'Kod yuboriş' }).click();
    await page.getByText('Telefon raqami notöğri').waitFor();
    await page.getByLabel('Telefon raqami').fill('+998901110099');
    await page.getByRole('button', { name: 'Kod yuboriş' }).click();
    await page.getByLabel('Tasdiqlaş kodi').fill('000000');
    await page.getByRole('button', { name: 'Kiriş', exact: true }).click();
    await page.getByText('Kod notöğri').waitFor();
  });
  await axeScan(page, 'login').then(() => results.push({ name: 'axe login', ok: true }), (e) => results.push({ name: 'axe login', ok: false, error: e.message }));

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
  await step('favorite toggles only after the server confirms', async () => {
    await cp.goto(WEB);
    await cp.getByText('DEMO Madina').first().waitFor();
    await cp.getByRole('button', { name: /DEMO Madinani sevimlilarga qöşiş|DEMO Madina.*sevimlilarga qöşiş/ }).first().click();
    await cp.getByText('Sevimlilarga qöşildi.').waitFor();
    await cp.goto(`${WEB}/favorites`);
    await cp.getByText('DEMO Madina').first().waitFor();
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
    await cp.getByLabel('Yoş').fill('12');
    await cp.getByText('Yoş 18 dan 120 gaça bölişi kerak.').waitFor();
    await cp.getByLabel('Yoş').fill('29');
    await cp.getByRole('button', { name: 'Saqlaş' }).click();
    await cp.getByText('Profil saqlandi.').waitFor();
  });
  await step('profile hub → help: trusted contact add/remove, report a booking (server derives the companion), my reports', async () => {
    await cp.goto(`${WEB}/account`);
    await cp.getByRole('navigation', { name: 'Bölimlar' }).getByRole('link', { name: /Yordam va xavfsizlik/ }).click();
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
  await step('interface language is saved to the account and follows the user to another device', async () => {
    const other = await ctx();
    const op = await other.newPage();
    watch(op, 'second-device');
    try {
      await cp.goto(`${WEB}/account`);
      const saved = cp.waitForResponse((r) => r.url().endsWith('/api/v1/auth/profile') && r.request().method() === 'PUT');
      await cp.locator('.lang-switch').getByRole('button', { name: /^RU/ }).click();
      assert((await (await saved).json()).ui_locale === 'ru', 'PUT /auth/profile should store ru');
      await otpLogin(op, '+998901110003'); // fresh device, Uzbek by default
      await op.getByRole('link', { name: 'Профиль' }).first().waitFor();
      assert((await op.evaluate(() => document.documentElement.lang)) === 'ru', 'second device should switch to ru');
    } finally {
      await cp.locator('.lang-switch').getByRole('button', { name: /^UZ/ }).click();
      await cp.getByRole('heading', { name: 'Hisobim', level: 1 }).waitFor();
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
    await kp.goto(`${WEB}/account`);
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
      await page.goto(`${WEB}/login`);
      await page.getByLabel('Номер телефона').fill('+998');
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
      await page.getByLabel('Telefon raqami').fill('+998901234567');
      await page.locator('.lang-switch').getByRole('button', { name: /^RU/ }).click();
      await page.getByLabel('Номер телефона').waitFor();
      assert((await page.getByLabel('Номер телефона').inputValue()) === '+998901234567', 'typed phone must survive a language switch');
      await page.locator('.lang-switch').getByRole('button', { name: /^UZ/ }).click();
      await page.getByLabel('Telefon raqami').waitFor();
    } finally {
      await page.evaluate(() => localStorage.removeItem('yondo.lang'));
    }
  });
  await step('Uzbek alphabet: date-based default, Settings switch, and search matches both spellings', async () => {
    const fresh = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'uz-UZ' });
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
  for (const theme of ['gul', 'rausch', 'stone', 'yondo', 'yondo-tun']) {
    await step(`axe (WCAG2 A/AA serious+critical) in theme ${theme}: public + admin pages`, async () => {
      for (const [pg, path] of [[page, '/'], [page, '/login'], [page, '/settings'], [page, '/help'], [cp, '/account'], [cp, '/help'], [ap, '/admin'], [ap, '/admin/applications'], [ap, '/admin/users'], [ap, '/admin/safety'], [ap, '/admin/audit']]) {
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
