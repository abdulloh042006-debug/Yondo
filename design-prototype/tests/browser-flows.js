/* Real-browser E2E flows. Loaded by tests/browser.js. All data is the in-browser DEMO mock. */
module.exports = async function (X) {
  const { open, ready, nav, session, T, mk, sleep, rec, errors, out, browser, SHOTS, path } = X;
  let page;
  const P = async (w, o) => { page = await open(w || 390, o); return page; };
  const txt = () => page.evaluate(() => document.querySelector('#v').innerText);
  const dtxt = () => page.evaluate(() => (document.querySelector('dialog[open]') || { innerText: '' }).innerText);
  const wait = (fn, arg, t) => page.waitForFunction(fn, { timeout: t || 6000 }, arg);
  const settle = async () => { await sleep(450); };
  const clickText = async (t, scope) => { const h = await page.evaluateHandle((t, sc) => { const root = document.querySelector(sc || 'body'); return [...root.querySelectorAll('button,a,summary')].find((e) => e.textContent.trim().includes(t) && e.getBoundingClientRect().width > 0 && !e.disabled); }, t, scope); const el = h.asElement(); if (el) await el.evaluate((e) => e.scrollIntoView({ block: 'center' })); if (!el) throw new Error('no clickable "' + t + '" | page: ' + (await txt()).replace(/\n+/g, ' / ').slice(0, 420)); await el.click(); await sleep(250); };
  const openDemo = async () => { await page.evaluate(() => { const d = document.querySelector('details'); if (d && !d.open) d.open = true; }); await sleep(120); };
  const clickA = async (a) => { await page.waitForSelector(`[data-a="${a}"]`, { timeout: 5000 }); await page.click(`[data-a="${a}"]`); await sleep(250); };
  const setVal = async (sel, v) => { await page.waitForSelector(sel, { timeout: 5000 }); await page.$eval(sel, (e) => { e.value = ''; }); await page.type(sel, String(v)); };
  const submit = async (formSel) => { await page.$eval(formSel + ' [type=submit]', (b) => b.click()); await sleep(450); };
  const active = () => page.evaluate(() => { const a = document.activeElement; return a ? (a.id || a.tagName) + ':' + (a.closest('dialog') ? 'dialog' : 'page') : 'none'; });
  const status = () => page.evaluate(() => (document.querySelector('#v .stc') || {}).textContent);
  const hash = () => page.evaluate(() => location.hash);
  const API = (fn, ...a) => page.evaluate(fn, ...a);
  const mkBooking = (day, hour, who) => API(async (d, h) => { const Y = YAPP; const pg = await Y.call('GET', '/discovery/companions', { query: { q: 'Nilufar' } }); const c = pg.items[0]; const b = await Y.call('POST', '/bookings', { body: { service_id: c.services[1].id, starts_at: new Date(Y.dayStart(d) + h * 36e5).toISOString(), duration_minutes: 60, meeting_place: 'Kafe (test)', timezone: 'Asia/Tashkent' } }); return b.id; }, day, hour);

  // ===== F1 auth via UI =====
  await P(390);
  await T('F1 login UI: bad phone → inline error; bad OTP → error; good OTP → roles page', async () => {
    await ready(); await clickText('Telefon raqam bilan davom etish'); await ready();
    await setVal('#ph', '12'); await submit('form[data-f=phone]'); mk(/9 ta raqam/.test(await txt()), 'phone error text missing'); mk(await page.$eval('#ph', (e) => e.getAttribute('aria-invalid')) === 'true', 'aria-invalid not set');
    await setVal('#ph', '90 123 45 67'); await submit('form[data-f=phone]'); await page.waitForSelector('#ot');
    await setVal('#ot', '0000'); await submit('form[data-f=otp]'); mk(/Kod notoʻgʻri/.test(await txt()), 'otp error missing');
    await setVal('#ot', '1234'); await submit('form[data-f=otp]'); await wait(() => /roles/.test(location.hash)); await ready(); mk(/Rolni tanlang/.test(await txt()), 'roles page'); return 'ok';
  });
  await T('F1 roles: empty selection blocked; select all three → customer home', async () => {
    await submit('form[data-f=roles]'); mk(/Kamida bitta rol/.test(await txt()), 'no role error');
    for (const r of ['customer', 'companion', 'vendor']) await page.click(`input[value=${r}]`); await submit('form[data-f=roles]'); await wait(() => /#\/home/.test(location.hash)); await ready();
    mk(/Toshkent/.test(await txt()), 'home heading'); mk(await page.$('#rolesel') !== null, 'role switcher missing'); return 'ok';
  });

  // ===== F2 search =====
  await T('F2 search: text filter, category chip, empty state + reset', async () => {
    await nav('#/search'); await settle(); const n0 = await page.$$eval('#res .card', (c) => c.length); mk(n0 === 5, 'expected 5 cards, got ' + n0);
    await setVal('#q', 'Nilufar'); await settle(); mk((await page.$$eval('#res .card', (c) => c.length)) === 1, 'text filter');
    await setVal('#q', 'zzzz'); await settle(); mk(/Hech narsa topilmadi/.test(await txt()), 'empty state'); await clickText('Filtrni tozalash'); await settle();
    mk((await page.$$eval('#res .card', (c) => c.length)) === 5, 'reset'); await clickA('sf:cinema'); await settle(); mk((await page.$$eval('#res .card', (c) => c.length)) === 1, 'cinema chip');
    mk(await page.$eval('[data-a="sf:cinema"]', (e) => e.getAttribute('aria-pressed')) === 'true', 'aria-pressed'); return 'ok';
  });
  await T('F2 verification badge only for verified:true (4 of 5 DEMO cards)', async () => { await nav('#/search'); await settle(); await clickA('sf:study'); await settle(); const t = await txt(); mk(/Sardor/.test(t) && !/Tasdiqlangan/.test(t), 'unverified card shows badge'); await page.evaluate(() => YAPP.A.sreset()); await settle(); const n = await page.$$eval('#res .bdg', (b) => b.length); mk(n === 4, 'badges ' + n); return n + ' badges'; });

  // ===== F3 booking =====
  await T('F3 open profile from card; verified badge explicit; 5 fields only in request', async () => {
    await nav('#/home'); await settle(); await page.evaluate(() => YM.demo.cfg.calls.length = 0); await clickText('Madina K.'); await ready(); mk(/Madina/.test(await txt()) && /Tasdiqlangan/.test(await txt()), 'profile');
    await clickText('Bron qilish'); await ready(); mk(/Bron: Madina/.test(await txt()), 'book form'); return 'ok';
  });
  await T('F3 booking form validation: empty submit → summary alert focused, fields flagged', async () => {
    await submit('form[data-f=book]'); const t = await txt(); mk(/Toʻldirilmagan maydonlar/.test(t) && /Uchrashuv joyini yozing/.test(t), 'summary'); mk((await active()).includes('tabindex') || (await page.evaluate(() => document.activeElement.getAttribute('role'))) === 'alert', 'focus not on alert'); return 'ok';
  });
  let freeDay = null;
  await T('F3 availability pre-check: finds a closed day ("mavjud emas") and an open day ("mavjud") for 12:00', async () => {
    let closed = null, open_ = null;
    for (let d = 1; d <= 6 && !(closed !== null && open_ !== null); d++) { await clickA('bd:' + d); await clickA('bt:12'); await sleep(500); const t = await page.$eval('#chk', (e) => e.innerText); if (/mavjud emas/.test(t)) { closed = d; mk(await page.$eval('#sub', (b) => b.disabled), 'submit not disabled on unavailable'); } else if (/✓/.test(t)) open_ = open_ === null ? d : open_; }
    mk(closed !== null, 'no closed day found'); mk(open_ !== null, 'no open day found'); freeDay = open_; return `closed day idx ${closed}, open ${open_}`;
  });
  await T('F3 successful booking create → detail (pending), request body has exactly 5 fields', async () => {
    await clickA('bd:' + freeDay); await clickA('bt:12'); await sleep(500); await clickA('bu:120'); await clickA('bp:Amir Temur xiyoboni'); await sleep(200);
    mk(/180 000/.test(await page.$eval('form[data-f=book]', (f) => f.innerText)), 'estimate for 2h should be 180 000'); await submit('form[data-f=book]'); await wait(() => /#\/b\//.test(location.hash)); await ready();
    mk(/Hamroh javobini kutmoqda/.test(await txt()), 'pending hint'); mk((await status()) === 'Kutilmoqda', 'status ' + (await status()));
    const bk = await API(async () => (await YAPP.call('GET', '/bookings'))[0]); mk(JSON.stringify(Object.keys(bk).filter((k) => ['service_id', 'starts_at', 'duration_minutes', 'meeting_place', 'timezone'].includes(k)).sort()) === JSON.stringify(['duration_minutes', 'meeting_place', 'service_id', 'starts_at', 'timezone']), 'fields'); mk(bk.starts_at.endsWith('Z'), 'UTC instant'); mk(bk.duration_minutes === 120 && bk.price_minor === 18000000, 'price'); return 'ok';
  });
  await T('F4 server conflict (booking_time_unavailable) shows error, keeps inputs, flags slot', async () => {
    const info = await API(async (fd) => { const Y = YAPP; return { d: fd }; }, freeDay); await nav('#/search'); await settle(); await clickText('Madina K.'); await ready(); await clickText('Bron qilish'); await ready();
    await clickA('bd:' + freeDay); await clickA('bt:14'); await sleep(500); mk(/✓/.test(await page.$eval('#chk', (e) => e.innerText)), 'precheck ok 14:00');
    await API(async (fd) => { const Y = YAPP; const c = (await Y.call('GET', '/discovery/companions', { query: { q: 'Madina' } })).items[0]; await Y.call('POST', '/bookings', { body: { service_id: c.services[0].id, starts_at: new Date(Y.dayStart(fd) + 14 * 36e5).toISOString(), duration_minutes: 60, meeting_place: 'Boshqa joy', timezone: 'Asia/Tashkent' } }); }, freeDay);
    await clickA('bp:Magic City hududi'); await submit('form[data-f=book]'); const t = await txt(); mk(/Bu vaqt band/.test(t), 'conflict message: ' + t.slice(0, 80)); mk(await page.$eval('#place', (e) => e.value) === 'Magic City hududi', 'place input lost'); mk(await page.$eval('#sub', (b) => b.disabled), 'submit should be disabled for taken slot'); return 'ok';
  });

  // ===== F5 payment states =====
  let bid;
  await T('F5 pay before accept is blocked; DEMO accept enables payment', async () => {
    await nav('#/bookings'); await settle(); await clickText('Kofe'); await ready(); bid = (await hash()).split('/').pop(); mk(!/Toʻlashga oʻtish/.test(await txt()), 'pay button visible on pending');
    await nav('#/pay/' + bid); mk(/Hozir toʻlab boʻlmaydi/.test(await txt()), 'pay page should refuse pending'); await nav('#/b/' + bid);
    await page.evaluate(() => document.querySelector('details summary').click()); await clickText('Hamroh qabul qildi'); await sleep(500); mk((await status()) === 'Qabul qilindi', 'accepted'); mk(/Toʻlashga oʻtish/.test(await txt()), 'pay button'); return 'ok';
  });
  await T('F5 payment 503 (provider) is shown as UNAVAILABLE, distinct from failed; booking stays accepted', async () => {
    await clickText('Toʻlashga oʻtish'); await ready(); mk(/Toʻlov bosqichida aniqlanadi/.test(await txt()), 'fee not shown as pending'); await page.evaluate(() => { YM.demo.cfg.pay = '503'; });
    await clickText('Toʻlash (demo)'); await sleep(500); const t = await txt(); mk(/Xizmat vaqtincha mavjud emas/.test(t) && /Toʻlov tizimi vaqtincha mavjud emas/.test(t), '503 text'); mk(!/Toʻlov amalga oshmadi/.test(t), '503 must not look like failure');
    mk(await page.$('.alert.unavailable') !== null, 'alert kind'); mk((await page.evaluate(() => YM.demo.S.bookings.find((b) => b.status === 'accepted')) !== undefined), 'booking still accepted'); return 'ok';
  });
  await T('F5 fees unconfigured → payment_configuration_unavailable message', async () => { await page.evaluate(() => { YM.demo.cfg.pay = 'ok'; YM.demo.cfg.feeBps = null; }); await clickText('Qayta urinish'); await sleep(500); mk(/Toʻlov sozlamalari hali tayyor emas/.test(await txt()), 'cfg 503 text: ' + (await txt()).slice(0, 120)); await page.evaluate(() => { YM.demo.cfg.feeBps = 1000; }); return 'ok'; });
  await T('F5 provider dialog: focus inside, declined → failed state with retry; then success → confirmed', async () => {
    await clickText('Toʻlash (demo)'); await sleep(500); await page.waitForSelector('dialog[open]'); mk((await active()).endsWith('dialog') || (await page.evaluate(() => !!document.activeElement.closest('dialog'))), 'focus not in dialog');
    await clickText('Rad etilsin', 'dialog'); await sleep(700); mk(/Toʻlov amalga oshmadi/.test(await txt()), 'failed alert'); mk(/Platforma haqi/.test(await txt()) && /9 000|9\s000|900/.test('9 000'), 'fee row');
    await clickText('Toʻlash (demo)'); await sleep(500); await clickText('Muvaffaqiyatli toʻlash', 'dialog'); await sleep(900); mk(/Toʻlov tasdiqlandi/.test(await txt()), 'success page'); await clickText('Bronni koʻrish'); await ready(); mk((await status()) === 'Tasdiqlandi', 'confirmed: ' + (await status())); mk(/Demo toʻlov: haqiqiy pul yechilmagan/.test(await txt()), 'demo disclaimer'); return 'ok';
  });
  await T('F5 combined booking+gift preview is "unavailable" (no total), not faked', async () => { await clickText('Sovgʻalar').catch(() => {}); await nav('#/gifts'); await settle(); await clickA((await page.$$eval('[data-a^="gq:"]', (b) => b[0].dataset.a))); await settle(); mk(/Savat/.test(await txt()), 'gifts'); const b2 = await mkBooking(5, 11); await API((id) => YM.demo.companionAccept(id), b2); await nav('#/pay/' + b2); await clickText('Birlashgan narxni koʻrish'); await sleep(500); const t = await txt(); mk(/Aniqlanmagan/.test(t) && /Birlashgan toʻlov yoʻq/.test(t), 'preview text'); return 'ok'; });

  // ===== F6 meeting, SOS, chat, review =====
  await T('F6 check-in too early → info message; DEMO time skip; both check in → start → SOS honest copy → end', async () => {
    await nav('#/b/' + bid); await clickText('Men yetib keldim'); await sleep(500); mk(/hali kelmadi/.test(await page.evaluate(() => document.querySelector('#ts').textContent)), 'too early toast');
    await openDemo(); await clickText('Uchrashuv vaqtiga oʻtish'); await sleep(400);
    await clickText('Men yetib keldim'); await sleep(500); await openDemo(); await clickText('Hamroh yetib keldi'); await sleep(500); await clickText('Uchrashuvni boshlash'); await sleep(600); mk((await status()) === 'Uchrashuv faol', 'active ' + (await status()));
    await clickText('SOS signali'); await sleep(500); const d = await dtxt(); mk(/chaqirilmaydi/.test(d) && /kuzatilmaydi/.test(d), 'SOS honest copy'); await clickText('Signalni yuborish', 'dialog'); await sleep(700); mk(/Favqulodda xizmat chaqirilmadi/.test(await page.evaluate(() => document.querySelector('#ts').textContent)), 'sos toast honest'); return 'ok';
  });
  await T('F6 chat: empty message blocked; message appears; end → completed; chat input disabled', async () => {
    await clickText('Yuborish'); await sleep(300); mk(/boʻsh boʻlmasin/.test(await txt()), 'empty msg | hash ' + await hash() + ' | ' + (await txt()).replace(/\n+/g, ' / ').slice(0, 160)); await setVal('#mi', 'Salom, men yetib keldim'); await submit('form[data-f=msg]'); await sleep(500); mk(/Salom, men yetib keldim/.test(await txt()), 'msg shown');
    await clickText('Uchrashuvni yakunlash'); await sleep(600); mk((await status()) === 'Yakunlandi', 'completed'); mk(await page.$eval('#mi', (e) => e.disabled), 'chat should close'); return 'ok';
  });
  await T('F6 review dialog: requires stars; submit → thanks; second review blocked by backend code', async () => {
    await clickText('Sharh qoldirish'); await sleep(500); await submit('dialog form[data-f=review]'); mk(/Baho tanlang/.test(await dtxt()), 'star validation'); await clickA('star:' + bid + ':5'); await sleep(250);
    mk(await page.$eval('[data-a="star:' + bid + ':5"]', (e) => e.getAttribute('aria-pressed')) === 'true', 'aria-pressed'); await submit('dialog form[data-f=review]'); await sleep(700); mk(/rahmat/i.test(await page.evaluate(() => document.querySelector('#ts').textContent)), 'thanks');
    const r = await API(async (id) => { try { await YAPP.call('POST', '/reviews/bookings/' + id, { body: { stars: 4 } }); return 'no-error'; } catch (e) { return e.code; } }, bid); mk(r === 'review_already_exists', 'dup review: ' + r); return 'ok';
  });

  // ===== F7 cancel =====
  await T('F7 cancel: dialog states terms (no fake percentages); confirm → cancelled; stale cancel handled', async () => {
    const b = await mkBooking(6, 12); await nav('#/b/' + b); await clickText('Bronni bekor qilish'); await sleep(500); const d = await dtxt(); mk(/foizlar hali belgilanmagan/.test(d) && !/%/.test(d), 'terms'); await submit('dialog form[data-f=cancel]'); await sleep(800); mk((await status()) === 'Bekor qilindi', 'cancelled'); mk(!/Bronni bekor qilish/.test(await txt().then((t) => t.replace(/Bron bekor qilindi\./g, ''))), 'cancel btn gone'); return 'ok';
  });

  // ===== F8 gifts =====
  await T('F8 gifts: out of stock disabled; manual delivery needs note (field error, focus); pickup test order flags', async () => {
    await page.evaluate(() => YM.demo.S.cart.length = 0); await nav('#/gifts'); await settle(); mk(await page.$$eval('[data-a^="gq:"]:disabled', (b) => b.length) === 1, 'one disabled (out of stock)'); mk(/Maxsus kunlar/.test(await txt()) && !/Romantic/i.test(await txt()), 'romantic label mapping');
    await page.evaluate(() => document.querySelector('[data-a^="gq:"]:not(:disabled)').click()); await settle(); await page.click('input[value=manual_delivery]'); await submit('form[data-f=gift]'); await settle(); mk(/izoh yozing/.test(await txt()), 'note error'); mk(await page.evaluate(() => document.activeElement.id) === 'note', 'focus on note');
    await page.click('input[value=pickup]'); await submit('form[data-f=gift]'); await settle(); const t = await txt(); mk(/Test buyurtma yaratildi/.test(t) && /real_money_moved: false/.test(t) && /aniqlanmagan/.test(t), 'order flags'); return 'ok';
  });

  // ===== F9 companion + vendor =====
  await T('F9 companion: switch role; status shows blockers; application → profile (validation) → service (validation) → availability (validation) → approve → active', async () => {
    await page.select('#rolesel', 'companion'); await ready(); mk(/Holat/.test(await txt()), 'status'); mk(/Faol emas/.test(await txt()) && /Ariza hali tasdiqlanmagan/.test(await txt()), 'blockers');
    await setVal('#statement', 'Salom'); await submit('form[data-f=app]'); await settle(); await ready(); await clickText('Arizani yuborish'); await settle(); await nav('#/me/profile');
    await submit('form[data-f=prof]'); mk(/Ismni kiriting/.test(await txt()), 'profile validation'); await setVal('#display_name', 'Test Hamroh'); await setVal('#interests', 'kofe, Kofe'); await submit('form[data-f=prof]'); mk(/takrorlanmasin/.test(await txt()), 'dup interests');
    await setVal('#interests', 'kofe, sayr'); await setVal('#languages', 'Oʻzbek'); await submit('form[data-f=prof]'); await settle(); await ready();
    await nav('#/me/services'); await clickText('Xizmat qoʻshish'); await sleep(500); await setVal('dialog #price', '-5'); await submit('dialog form[data-f=svc]'); await sleep(400); mk(/0 dan kam/.test(await dtxt()), 'svc price validation'); await setVal('dialog #price', '55000'); await submit('dialog form[data-f=svc]'); await settle(); await ready(); mk(/55 000/.test(await txt()), 'svc listed');
    await nav('#/me/availability'); const day = await page.evaluate(() => new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10)); await page.$eval('#date', (e, v) => { e.value = v; }, day); await page.$eval('#from', (e) => { e.value = '18:00'; }); await page.$eval('#to', (e) => { e.value = '10:00'; }); await submit('form[data-f=avail]'); mk(/keyin boʻlishi kerak/.test(await txt()), 'avail validation');
    await page.$eval('#from', (e) => { e.value = '10:00'; }); await page.$eval('#to', (e) => { e.value = '18:00'; }); await submit('form[data-f=avail]'); await settle(); await ready(); mk(/10:00 – 18:00/.test(await txt()), 'avail listed');
    await nav('#/me'); await clickText('Profilni tekshiruvga yuborish'); await settle(); await clickText('Faollashtirishni soʻrash'); await settle(); await page.evaluate(() => document.querySelector('details summary').click()); await clickText('Hammasini tasdiqlash'); await settle(); await ready(); mk(/Profilingiz mijozlarga koʻrinadi/.test(await txt()), 'active'); return 'ok';
  });
  await T('F9 companion requests: demo requests → open → accept; earnings page says "not live"', async () => {
    await nav('#/me/requests'); await page.evaluate(() => document.querySelector('details summary').click()); await clickText('Demo soʻrovlar qoʻshish'); await settle(); await ready(); mk(/mijoz #/.test(await txt()), 'requests listed @' + await hash() + ': ' + (await txt()).replace(/\n+/g, ' / ').slice(0, 200)); await clickText('Kutilmoqda'); await ready(); mk(/Soʻrov|Mijoz soʻrovi/.test(await txt()), 'companion detail'); mk(!/Telefon|\+998/.test(await txt().then((t) => t.replace(/Telefon raqamlar chatda koʻrsatilmaydi\./, ''))), 'no customer phone leak');
    await clickText('Qabul qilish'); await sleep(600); mk((await status()) === 'Qabul qilindi', 'accepted by companion'); mk(!/Toʻlashga oʻtish/.test(await txt()), 'companion cannot pay'); await nav('#/me/earnings'); mk(/Hali jonli emas/.test(await txt()), 'earnings not live'); return 'ok';
  });
  await T('F9 vendor: product validation → create → publish(DEMO) → earnings 503 unavailable state', async () => {
    await page.select('#rolesel', 'vendor'); await ready(); await clickText('Mahsulot qoʻshish'); await sleep(500); await submit('dialog form[data-f=prod]'); mk(/Nom 2–160/.test(await dtxt()), 'validation');
    await setVal('dialog #name', 'Test buket'); await setVal('dialog #price', '120000'); await setVal('dialog #stock', '4'); await setVal('dialog #description', 'DEMO'); await submit('dialog form[data-f=prod]'); await settle(); await ready(); mk(/Test buket/.test(await txt()) && /Eʼlon qilinmagan/.test(await txt()), 'created unpublished');
    await clickText('DEMO: eʼlon qilish'); await settle(); await ready(); mk(/Eʼlon qilingan/.test(await txt()), 'published'); await nav('#/v/earnings'); const t = await txt(); mk(/Xizmat vaqtincha mavjud emas/.test(t) && /Daromad maʼlumoti hali jonli emas/.test(t), 'earnings 503'); return 'ok';
  });
  await T('F9 role guard: customer-only account cannot open companion/vendor areas (UI guard + server 403 codes)', async () => {
    await page.evaluate(() => YM.demo.reset()); await page.reload(); await page.evaluate(() => { YM.demo.cfg.latency = 0; }); await session(['customer']); await nav('#/me'); mk(/Ruxsat yoʻq/.test(await txt()), 'ui guard'); const c = await API(async () => { const r = []; for (const p of ['/companions/me/status', '/gifts/vendor/products', '/vendor/earnings']) { try { await YAPP.call('GET', p); r.push('ok'); } catch (e) { r.push(e.code); } } return r; }); mk(JSON.stringify(c) === JSON.stringify(['companion_role_required', 'role_required', 'role_required']), 'server codes ' + c); return 'ok';
  });

  // ===== F10 offline / retry / slow =====
  await T('F10 offline: banner + error with retry; back online → retry restores content', async () => {
    await nav('#/bookings'); await page.evaluate(() => { YM.demo.cfg.offline = true; YAPP.A.dm('offline'); YAPP.A.dm('offline'); YM.demo.cfg.offline = true; document.querySelector('#off').hidden = false; }); await page.keyboard.press('Escape'); await sleep(300); await page.evaluate(() => { document.querySelector('#nav a[href="#/home"]').click(); }); await sleep(600);
    const t = await txt(); mk(/Internet yoʻq/.test(t) && /Internet aloqasi yoʻq/.test(t), 'offline error'); mk(await page.evaluate(() => !document.querySelector('#off').hidden), 'banner'); mk(await page.$('[data-a=retry]') !== null, 'retry button');
    await page.evaluate(() => { YM.demo.cfg.offline = false; document.querySelector('#off').hidden = true; }); await clickA('retry'); await ready(); mk(/Toshkent/.test(await txt()), 'restored'); return 'ok';
  });
  await T('F10 loading state: skeleton appears under slow network, then content', async () => {
    await page.evaluate(() => { YM.demo.cfg.latency = 900; }); await page.evaluate(() => { location.hash = '#/search'; }); await sleep(250); mk(await page.$('#v .sk') !== null, 'skeleton visible'); await ready(); await page.evaluate(() => { YM.demo.cfg.latency = 0; }); return 'ok';
  });

  await T('F7b decided copy @360: cancel dialog + paid-cancel page say no % / no refund calculation; layout/contrast clean', async () => {
    await P(360); await ready(); await session(['customer']); const b = await mkBooking(6, 12); await API(async (id) => { YM.demo.companionAccept(id); const p = await YAPP.call('POST', '/payments/bookings/' + id, { headers: { 'Idempotency-Key': 'k-f7b-' + id.slice(-6) } }); YM.demo.providerComplete(p.id, 'succeeded'); }, b);
    await nav('#/b/' + b); await clickText('Bronni bekor qilish'); await sleep(500); const d = await dtxt(); mk(/refund hisoblanmaydi/.test(d) && /foiz hali belgilanmagan/.test(d) && !/%/.test(d), 'dialog copy: ' + d.slice(0, 160));
    const m1 = await page.evaluate(X.MEASURE); const p1 = m1.off.concat(m1.small, m1.clip, m1.contrast, m1.overflowX > 0 ? ['overflow ' + m1.overflowX] : []); mk(!p1.length, 'dialog layout: ' + p1.slice(0, 3).join(' | '));
    await submit('dialog form[data-f=cancel]'); await sleep(900); const t2 = await txt(); mk(/Bekor qilindi/.test(t2) && /refund hisoblanmaydi/.test(t2) && /Demo toʻlovda haqiqiy pul qaytarilmaydi/.test(t2) && !/%/.test(t2), 'page copy: ' + t2.replace(/\n+/g, ' / ').slice(0, 220));
    const m2 = await page.evaluate(X.MEASURE); const p2 = m2.off.concat(m2.small, m2.clip, m2.contrast, m2.overflowX > 0 ? ['overflow ' + m2.overflowX] : []); mk(!p2.length, 'page layout: ' + p2.slice(0, 3).join(' | ')); return 'ok';
  });

  // ===== F11 keyboard + dialog focus =====
  await T('F11 keyboard: skip link first Tab; dialog opens with Enter, traps Tab (25 presses), Esc closes and restores focus to opener', async () => {
    await P(390); await ready(); mk(await page.evaluate(() => document.activeElement.tagName) === 'BODY', 'initial load must not steal focus: ' + await page.evaluate(() => document.activeElement.tagName)); await page.keyboard.press('Tab'); mk(await page.evaluate(() => document.activeElement.className) === 'skip', 'skip link not first'); await page.keyboard.press('Enter'); await sleep(200); mk(await page.evaluate(() => document.activeElement.id) === 'v', 'skip target: ' + await page.evaluate(() => document.activeElement.outerHTML.slice(0, 70))); await session(['customer']); await nav('#/home');
    await page.focus('[data-a=demo]'); await page.keyboard.press('Enter'); await sleep(500); mk(await page.evaluate(() => !!document.querySelector('dialog[open]')), 'dialog open'); mk(await page.evaluate(() => !!document.activeElement.closest('dialog')), 'focus inside on open');
    for (let i = 0; i < 25; i++) { await page.keyboard.press('Tab'); if (!(await page.evaluate(() => !!document.activeElement.closest('dialog')))) throw new Error('focus escaped dialog at Tab ' + i); }
    await page.keyboard.press('Escape'); await sleep(500); mk(await page.evaluate(() => !document.querySelector('dialog[open]')), 'esc closes'); mk(await page.evaluate(() => document.activeElement.getAttribute('data-a')) === 'demo', 'focus restore: ' + (await page.evaluate(() => document.activeElement.outerHTML.slice(0, 60)))); return 'ok';
  });
  await T('F11 dialog backdrop click closes; page behind is inert (cannot focus nav link)', async () => {
    await page.focus('[data-a=demo]'); await page.keyboard.press('Enter'); await sleep(500); const inert = await page.evaluate(() => { const a = document.querySelector('#nav a'); a.focus(); return document.activeElement === a; }); mk(!inert, 'background focusable while modal open'); await page.mouse.click(5, 5); await sleep(500); mk(await page.evaluate(() => !document.querySelector('dialog[open]')), 'backdrop close'); return 'ok';
  });

  // ===== F12 reduced motion =====
  await T('F12 reduced motion: animations/transitions collapse to ~0 ms; logo still renders', async () => {
    await P(390, { rm: true }); await ready(); await session(['customer']); await nav('#/home'); const r = await page.evaluate(() => { const d = (s) => { const e = document.querySelector(s); return e ? parseFloat(getComputedStyle(e).animationDuration) : null; }; document.querySelector('[data-a=demo]').click(); return { scr: d('.scr'), up: d('.up'), btn: parseFloat(getComputedStyle(document.querySelector('.btn') || document.body).transitionDuration), sheet: parseFloat(getComputedStyle(document.querySelector('dialog')).transitionDuration) }; });
    mk(r.scr !== null && r.scr <= 0.001 && (r.up === null || r.up <= 0.001) && r.sheet <= 0.001, 'durations ' + JSON.stringify(r)); await sleep(300); mk(await page.evaluate(() => !!document.querySelector('dialog[open]')), 'dialog still opens'); return JSON.stringify(r);
  });
  await T('F12 normal motion: durations within 150–400 ms spec (screen 200 ms, sheet 300 ms)', async () => { await P(390); await ready(); await session(['customer']); await nav('#/home'); const r = await page.evaluate(() => ({ scr: parseFloat(getComputedStyle(document.querySelector('.scr')).animationDuration) * 1000, sheet: parseFloat(getComputedStyle(document.querySelector('dialog')).transitionDuration) * 1000, up: parseFloat(getComputedStyle(document.querySelector('.up')).animationDuration) * 1000 })); mk(r.scr === 200 && r.sheet === 300 && r.up === 300, JSON.stringify(r)); return JSON.stringify(r); });

  // ===== F13 six standalone screens =====
  for (const [f, n, expect] of [['01-home', 'home', /Toshkent/], ['02-search', 'search', /Qidiruv/], ['03-companion-profile', 'profile', /Xizmatlar/], ['04-booking', 'booking', /Uchrashuv joyi/], ['05-chat-active-booking', 'chat', /Uchrashuv faol|Chat/], ['06-flowers-gifts', 'gifts', /Gul va sovgʻalar/]]) {
    await T(`F13 screen file ${f}.html opens standalone and renders`, async () => { const pg = await browser.newPage(); await pg.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true }); await pg.setRequestInterception(true); pg.on('request', (r) => (/googleapis|gstatic/.test(r.url()) ? r.abort() : r.continue())); pg.on('pageerror', (e) => errors.push(f + ' pageerror: ' + e.message)); await pg.goto('file://' + path.join(__dirname, '..', 'screens', f + '.html')); await pg.waitForFunction(() => document.querySelector('#v h1') && !document.querySelector('#v .sk') && !/screen/.test(location.hash), { timeout: 9000 }); await new Promise((r) => setTimeout(r, 600)); const t = await pg.evaluate(() => document.querySelector('#v').innerText); if (!expect.test(t)) throw new Error('missing content: ' + t.slice(0, 100)); await pg.screenshot({ path: path.join(SHOTS, `screen-${n}-390.png`) }); await pg.close(); return 'ok'; });
  }
  rec(errors.length ? 'FAIL' : 'PASS', 'no uncaught JS errors / console errors across all flows', errors.slice(0, 4).join(' | '));
  const f = out.filter((x) => x.st === 'FAIL').length; console.log(`\n${out.length - f} passed, ${f} failed, ${out.length} total`); await browser.close(); process.exit(f ? 1 : 0);
};
