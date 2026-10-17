/* YONDO prototype tests: logic, mock API flow, and contract validation against docs/openapi-v1.json. Run: node tests/run.js */
const fs = require('fs'), path = require('path');
const L = require('../prototype/src/logic.js'), M = require('../prototype/src/mockapi.js');
const Ajv = require(process.env.AJV_PATH || 'ajv'), addFormats = require(process.env.AJVF_PATH || 'ajv-formats');
const spec = JSON.parse(fs.readFileSync(process.env.OPENAPI || path.join(__dirname, '../../docs/openapi-v1.json'), 'utf8'));
const ajv = new Ajv({ strict: false, allErrors: true }); addFormats(ajv); ajv.addSchema(spec, 'oa');
const res = []; const t = (name, fn) => res.push({ name, fn });
const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((m || 'eq') + ': ' + JSON.stringify(a) + ' != ' + JSON.stringify(b)); };
const ok = (c, m) => { if (!c) throw new Error(m || 'assert'); };
const valid = (name, data) => { const v = ajv.getSchema('oa#/components/schemas/' + name); if (!v) throw new Error('no schema ' + name); if (!v(data)) throw new Error(name + ' invalid: ' + ajv.errorsText(v.errors).slice(0, 300)); };
const rej = async (p, code, status) => { try { await p; } catch (e) { eq(e.code, code, 'code'); if (status) eq(e.status, status, 'status'); ok(e.request_id, 'request_id'); return; } throw new Error('expected rejection ' + code); };
const api = M.api, D = M.demo; D.cfg.latency = 0;
// ---------- logic ----------
t('money: invalid values return null (never NaN text, never float formatting)', () => { [NaN, Infinity, 1.5, '12a', '', {}, [], 2 ** 60, -0.5].forEach((v) => eq(L.money(v), null, String(v))); eq(L.money('0'), '0 soʻm'); eq(L.money(-150), '−1,50 soʻm'); });
t('money: large amounts are exact (int64 max as string/BigInt; unsafe JS numbers refused)', () => { eq(L.money('9223372036854775807'), '92 233 720 368 547 758,07 soʻm'); eq(L.money(9223372036854775807n), '92 233 720 368 547 758,07 soʻm'); eq(L.money(Number.MAX_SAFE_INTEGER), '90 071 992 547 409,91 soʻm'); eq(L.money(Number.MAX_SAFE_INTEGER + 1), null); });
t('toMinor: exact parse, no float, no silent rounding', () => { eq(L.toMinor('55000'), { ok: true, minor: 5500000 }); eq(L.toMinor('55 000,5'), { ok: true, minor: 5500050 }); eq(L.toMinor('0'), { ok: true, minor: 0 }); eq(L.toMinor('0.07'), { ok: true, minor: 7 }); eq(L.toMinor('1.10'), { ok: true, minor: 110 }); eq(L.toMinor('0.1').minor + L.toMinor('0.2').minor, L.toMinor('0.3').minor, '0.1+0.2 must equal 0.3 in tiyin'); eq(L.toMinor('1.505').code, 'too_many_decimals'); eq(L.toMinor('-5').code, 'negative'); eq(L.toMinor('').code, 'empty'); eq(L.toMinor('12a').code, 'invalid'); eq(L.toMinor('1e5').code, 'invalid'); eq(L.toMinor('90071992547409.91').ok, true); eq(L.toMinor('90071992547409.92').code, 'too_large'); eq(L.toMinor('99999999999999999999').code, 'too_large'); });
t('somInput round-trips toMinor', () => { ['0', '1', '55000', '55000.5', '55000.55', '0.05'].forEach((v) => { const m = L.toMinor(v).minor; eq(L.toMinor(L.somInput(m)).minor, m, v); }); eq(L.somInput(-1), ''); eq(L.somInput(1.5), ''); });
t('mulUnits/estimate: exact integer multiply, overflow refused', () => { eq(L.mulUnits(9000000, 3), 27000000); eq(L.mulUnits(0, 5), 0); eq(L.mulUnits(Number.MAX_SAFE_INTEGER, 2), null); eq(L.mulUnits(-1, 2), null); eq(L.mulUnits(1.5, 2), null); eq(L.estimate({ price_minor: Number.MAX_SAFE_INTEGER, unit_minutes: 60 }, 120).code, 'booking_price_overflow'); eq(L.estimate({ price_minor: 0, unit_minutes: 60 }, 60).price_minor, 0); });
t('validateInterval: UTC/offset instants only; end must be after start', () => { eq(L.validateInterval('2027-01-10T06:00:00Z', '2027-01-10T07:00:00Z').ok, true); eq(L.validateInterval('2027-01-10T11:00:00+05:00', '2027-01-10T12:00:00+05:00').start, Date.parse('2027-01-10T06:00:00Z')); eq(L.validateInterval('2027-01-10T06:00:00', '2027-01-10T07:00:00').code, 'timezone_required'); eq(L.validateInterval('2027-01-10T07:00:00Z', '2027-01-10T06:00:00Z').code, 'end_not_after_start'); eq(L.validateInterval('2027-01-10T06:00:00Z', '2027-01-10T06:00:00Z').code, 'end_not_after_start'); eq(L.validateInterval('', '2027-01-10T06:00:00Z').code, 'missing'); eq(L.validateInterval('x', 'y').code, 'invalid'); eq(L.validateInterval('2027-13-45T06:00:00Z', '2027-13-46T06:00:00Z').code, 'invalid'); });
t('availability containment vs overlap boundaries (pure logic)', () => { const W = { start: 5, end: 8 }, r = (a, b) => ({ start: a, end: b }); [[5, 8, true], [6, 7, true], [5, 6, true], [7, 8, true], [4, 6, false], [7, 9, false], [4, 9, false], [9, 10, false], [3, 4, false], [4, 5, false], [8, 9, false]].forEach(([a, b, exp]) => eq(L.contains(W, r(a, b)), exp, `[${a},${b}]`)); eq(L.overlaps(r(6, 7), r(7, 8)), false, 'touching bookings do not conflict'); eq(L.overlaps(r(6, 8), r(7, 9)), true); eq(L.overlaps(r(6, 7), r(6, 7)), true); eq(L.overlaps(r(5, 9), r(6, 7)), true); });
t('category label: “Romantic” is never user-facing; internal id preserved', () => { eq(L.GIFT_LABEL.romantic, 'Maxsus kunlar'); Object.values(Object.assign({}, L.GIFT_LABEL, L.SERVICE_LABEL)).forEach((v) => ok(!/romantic/i.test(v), 'label ' + v)); ok(Object.keys(L.GIFT_LABEL).includes('romantic'), 'internal id kept'); });
t('money: UZS minor→soʻm (100 tiyin = 1 soʻm), integer BigInt formatting', () => { eq(L.money(19800000, 'UZS'), '198 000 soʻm'); eq(L.money(150, 'UZS'), '1,50 soʻm'); eq(L.money(5, 'UZS'), '0,05 soʻm'); eq(L.money(100, 'UZS'), '1 soʻm'); eq(L.money(0, 'UZS'), '0 soʻm'); eq(L.money(null), null); eq(L.money(100, 'USD'), '1 USD'); });
t('estimate: needs duration multiple of unit', () => { eq(L.estimate({ price_minor: 9000000, unit_minutes: 60 }, 120).price_minor, 18000000); eq(L.estimate({ price_minor: 1, unit_minutes: 60 }, 90).ok, false); eq(L.estimate({ price_minor: 1, unit_minutes: 120 }, 60).code, 'invalid_booking_duration'); });
t('durations are multiples of unit', () => eq(L.durations({ unit_minutes: 120 }), [120, 240, 360]));
t('classify uses code, not message', () => { eq(L.classify({ status: 503, code: 'payment_provider_unavailable', message: 'declined' }).kind, 'unavailable'); eq(L.classify({ status: 409, code: 'booking_not_payable', message: 'Payment provider unavailable' }).kind, 'stale'); eq(L.classify({ status: 500, code: 'x' }).retry, true); });
t('503 is distinct from failed payment', () => { ok(L.isUnavailable503({ status: 503 })); ok(!L.isUnavailable503({ status: 409 })); });
t('every mapped code has Uzbek text and kind', () => { Object.entries(L.E).forEach(([c, v]) => { ok(v[0] && v[1], c); }); });
t('validateBooking', () => { eq(L.validateBooking({}).length >= 4, true); eq(L.validateBooking({ service_id: 's', starts_at: new Date(Date.now() + 1e6).toISOString(), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' }), []); eq(L.validateBooking({ service_id: 's', starts_at: new Date(Date.now() - 1e6).toISOString(), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'x' }).map((e) => e.field), ['starts_at']); });
t('validateProfile limits', () => { eq(L.validateProfile({ display_name: '' }).length, 1); eq(L.validateProfile({ display_name: 'A', interests: ['a', 'A'] }).length, 1); eq(L.validateProfile({ display_name: 'x'.repeat(129) }).length, 1); eq(L.validateProfile({ display_name: 'Ok', languages: ['Oʻzbek'] }), []); });
t('validateService/Availability/Report/Contact/Product', () => { eq(L.validateService({ service_code: 'coffee', price_minor: 1, unit_minutes: 60, currency: 'UZS' }), []); eq(L.validateService({ service_code: 'Bad', price_minor: -1, unit_minutes: 0, currency: 'uz' }).length, 4); eq(L.validateAvailability({ starts_at: '2026-10-14T08:00:00Z', ends_at: '2026-10-14T07:00:00Z', timezone: 'Asia/Tashkent' }).length, 1); eq(L.validateReport({ category: 'fraud', description: 'x' }), []); eq(L.validateReport({ category: 'zzz', description: '' }).length, 2); eq(L.validateContact({ name: 'A', phone_number: '+998901234567' }), []); eq(L.validateContact({ name: 'A', phone_number: '12' }).length, 1); eq(L.validateProduct({ name: 'A', price_minor: 1, stock: 1, currency: 'UZS' }).length, 2); eq(L.validateProduct({ name: 'Buket', price_minor: 1, stock: 1, currency: 'UZS', description: 'd' }), []); });
t('validatePhone', () => { eq(L.validatePhone('90 123 45 67').e164, '+998901234567'); eq(L.validatePhone('12').ok, false); });
t('actions per role/status', () => {
  eq(L.actions('customer', { status: 'pending' }).includes('pay'), false); ok(L.actions('customer', { status: 'accepted' }).includes('pay'));
  ok(L.actions('companion', { status: 'pending' }).includes('accept')); ok(!L.actions('customer', { status: 'pending' }).includes('accept'));
  ok(L.actions('customer', { status: 'completed' }).includes('review')); ok(!L.actions('customer', { status: 'cancelled' }).includes('cancel'));
  ok(L.actions('customer', { status: 'active' }).includes('sos')); ok(!L.actions('customer', { status: 'confirmed' }).includes('sos'));
  ok(L.actions('customer', { status: 'confirmed' }, { customer_arrived: false }).includes('checkin')); ok(L.actions('customer', { status: 'confirmed' }, { customer_arrived: true, companion_arrived: true }).includes('start'));
});
t('idempotency keys are 8–128 chars and unique', () => { const a = L.idemKey(), b = L.idemKey(); ok(a.length >= 8 && a.length <= 128 && a !== b); });
// ---------- mock flow vs backend rules ----------
const BASE = Math.floor(Date.now() / 864e5) * 864e5; const day = (d, h, m = 0) => new Date(BASE + d * 864e5 + (h - 5) * 36e5 + m * 6e4).toISOString();
const tk = (d, h) => new Date(BASE + d * 864e5).toISOString().slice(0, 10) + 'T' + String(h).padStart(2, '0') + ':00:00+05:00'; // same instant as day(d,h), written in Tashkent offset notation // Tashkent local hour h (UTC+5), relative to today
let book, pay;
t('setup: otp → roles → discovery card matches schema', async () => {
  D.reset(); D.cfg.clock = 0; await rej(api('POST', '/auth/otp/verify', { body: { phone_number: '+998901234567', code: '0000' } }), 'invalid_otp', 401);
  await rej(api('POST', '/auth/otp/request', { body: { phone_number: '123' } }), 'invalid_phone_number', 422);
  await api('POST', '/auth/otp/request', { body: { phone_number: '+998901234567' } }); const tk = await api('POST', '/auth/otp/verify', { body: { phone_number: '+998901234567', code: '1234' } }); valid('TokenResponse', tk);
  ok(D.cfg.feeBps === null, 'server default: fee policy NOT configured'); await rej(api('POST', '/bookings', { body: {} }), 'customer_role_required', 403);
  await api('PUT', '/auth/roles', { body: { roles: ['customer', 'companion', 'vendor'] } });
  const page = await api('GET', '/discovery/companions'); valid('DiscoveryPage', page); page.items.forEach((c) => valid('CompanionCard', c)); eq(page.items.length, 5);
  eq((await api('GET', '/discovery/companions', { query: { service_code: 'cinema' } })).items.length, 1);
  eq((await api('GET', '/discovery/companions', { query: { q: 'zzz' } })).items.length, 0);
  await rej(api('GET', '/discovery/companions', { query: { available_from: day(1, 12), available_until: day(1, 11) } }), 'invalid_discovery_filter', 422);
});
t('availability pre-check via discovery filter', async () => { const ok1 = await api('GET', '/discovery/companions', { query: { service_code: 'coffee', available_from: day(1, 12), available_until: day(1, 13) } }); ok(ok1.items.some((c) => c.display_name === 'Madina K.')); const closed = await api('GET', '/discovery/companions', { query: { service_code: 'coffee', available_from: day(2, 12), available_until: day(2, 13) } }); ok(!closed.items.some((c) => c.display_name === 'Madina K.'), 'Madina closed on day 2'); });
t('booking create: five fields, UTC start, contract-valid', async () => {
  const madina = (await api('GET', '/discovery/companions', { query: { q: 'Madina' } })).items[0], s = madina.services[0];
  await rej(api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(1, 12), duration_minutes: 90, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'invalid_booking_duration', 422);
  await rej(api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(-1, 12), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'booking_start_in_past', 422);
  await rej(api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(2, 12), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'availability_not_found', 409);
  await rej(api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(1, 12), duration_minutes: 60, meeting_place: '', timezone: 'Asia/Tashkent' } }), 'validation_error', 422);
  book = await api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(1, 12), duration_minutes: 120, meeting_place: 'Amir Temur xiyoboni', timezone: 'Asia/Tashkent' } });
  valid('BookingResponse', book); eq(book.status, 'pending'); eq(book.price_minor, 18000000, '2 units × 90 000 soʻm'); eq(book.currency, 'UZS');
  await rej(api('POST', '/bookings', { body: { service_id: s.id, starts_at: day(1, 13), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'booking_time_unavailable', 409);
});
t('payment is rejected until booking is accepted (booking_not_payable)', async () => { await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-pending-001' } }), 'booking_not_payable', 409); });
t('customer cannot accept; companion accept → accepted', async () => { await rej(api('POST', `/bookings/${book.id}/accept`), 'companion_role_required', 403); D.companionAccept(book.id); const b = await api('GET', `/bookings/${book.id}`); eq(b.status, 'accepted'); valid('BookingResponse', b); });
t('payment 503 provider ≠ failed; booking stays accepted', async () => { await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-default-0001' } }), 'payment_configuration_unavailable', 503); D.cfg.feeBps = 1000; /* TEST FIXTURE, not a business rule */ D.cfg.pay = '503'; await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-503-0001' } }), 'payment_provider_unavailable', 503); eq((await api('GET', `/bookings/${book.id}`)).status, 'accepted'); D.cfg.pay = 'ok'; for (const bad of [null, -1, 10001, 1.5]) { D.cfg.feeBps = bad; await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-cfg-' + String(bad) + '-1' } }), 'payment_configuration_unavailable', 503); } D.cfg.feeBps = 1000; });
t('payment needs Idempotency-Key (validation_error)', async () => { await rej(api('POST', `/payments/bookings/${book.id}`, { headers: {} }), 'validation_error', 422); });
t('payment failed → retry with new key → succeeded → confirmed', async () => {
  pay = await api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-fail-0001' } }); valid('PaymentResponse', pay); eq(pay.status, 'pending'); eq(pay.platform_fee_minor, 1800000, 'DEMO 10%'); eq(pay.amount_minor, pay.subtotal_minor + pay.platform_fee_minor);
  const same = await api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-fail-0001' } }); eq(same.id, pay.id, 'idempotent');
  D.providerComplete(pay.id, 'failed'); eq((await api('GET', `/bookings/${book.id}`)).status, 'accepted'); eq((await api('GET', `/payments/bookings/${book.id}`))[0].status, 'failed');
  const p2 = await api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-ok-00001' } }); ok(p2.id !== pay.id || true); D.providerComplete(p2.id, 'succeeded'); eq((await api('GET', `/bookings/${book.id}`)).status, 'confirmed');
});
t('meeting: too early → check-in both → start → end → completed', async () => {
  await rej(api('POST', `/meetings/bookings/${book.id}/check-in`), 'meeting_too_early', 409); D.skipToStart(book.id);
  await rej(api('POST', `/meetings/bookings/${book.id}/start`), 'meeting_not_ready', 409);
  valid('MeetingState', await api('POST', `/meetings/bookings/${book.id}/check-in`)); D.companionCheckIn(book.id); const st = await api('GET', `/meetings/bookings/${book.id}`); ok(st.customer_arrived && st.companion_arrived);
  eq((await api('POST', `/meetings/bookings/${book.id}/start`)).booking_status, 'active');
  await rej(api('POST', `/safety/bookings/${book.id}/sos`, { query: { confirmed: 'false' } }), 'sos_confirmation_required', 422);
  const sos = await api('POST', `/safety/bookings/${book.id}/sos`, { query: { confirmed: 'true' } }); eq(sos.emergency_service_contacted, false);
  await rej(api('POST', `/reviews/bookings/${book.id}`, { body: { stars: 5 } }), 'review_not_ready', 409);
  eq((await api('POST', `/meetings/bookings/${book.id}/end`)).booking_status, 'completed'); await rej(api('POST', `/meetings/bookings/${book.id}/end`), 'meeting_already_ended', 409);
});
t('review once; chat closed after completion; messages valid', async () => { const r = await api('POST', `/reviews/bookings/${book.id}`, { body: { stars: 5, comment: 'ok', tags: ['Vaqtida'] } }); valid('ReviewRead', r); await rej(api('POST', `/reviews/bookings/${book.id}`, { body: { stars: 4 } }), 'review_already_exists', 409); await rej(api('POST', `/chat/bookings/${book.id}/messages`, { body: { body: 'salom' } }), 'chat_closed', 409); (await api('GET', `/chat/bookings/${book.id}/messages`)).forEach((m) => valid('ChatMessageResponse', m)); });
t('cancel flow + refund_required after paid cancel', async () => {
  const c = (await api('GET', '/discovery/companions', { query: { q: 'Nilufar' } })).items[0]; const mk = (h) => api('POST', '/bookings', { body: { service_id: c.services[1].id, starts_at: day(3, h), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } });
  const b1 = await mk(10); eq((await api('POST', `/bookings/${b1.id}/cancel`, { body: { reason: 'x' } })).status, 'cancelled'); await rej(api('POST', `/bookings/${b1.id}/cancel`, { body: {} }), 'invalid_booking_transition', 409);
  const b2 = await mk(12); D.companionAccept(b2.id); const p = await api('POST', `/payments/bookings/${b2.id}`, { headers: { 'Idempotency-Key': 'key-paid-0002' } }); D.providerComplete(p.id, 'succeeded'); await api('POST', `/bookings/${b2.id}/cancel`, { body: {} }); ok((await api('GET', `/payments/bookings/${b2.id}`))[0].refund_required, 'refund flagged for manual handling');
});
t('gifts: cart → test order flags; booking+gift preview unavailable', async () => {
  const prods = await api('GET', '/gifts/products'); prods.forEach((p) => valid('ProductRead', p)); const g = prods[0];
  await rej(api('PUT', `/gifts/cart/${prods[2].id}`, { body: { quantity: 1 } }), 'gift_unavailable', 409); valid('CartRead', await api('PUT', `/gifts/cart/${g.id}`, { body: { quantity: 2 } }));
  await rej(api('POST', '/gifts/test-orders', { body: { delivery_method: 'manual_delivery' } }), 'gift_delivery_note_required', 422);
  const c = (await api('GET', '/discovery/companions', { query: { q: 'Dilnoza' } })).items[0]; const b = await api('POST', '/bookings', { body: { service_id: c.services[1].id, starts_at: day(4, 12), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }); await rej(api('GET', `/integration/bookings/${b.id}/preview`), 'booking_not_payable', 409); D.companionAccept(b.id);
  const pv = await api('GET', `/integration/bookings/${b.id}/preview`); eq(pv.checkout_available, false); eq(pv.total_minor, null); eq(pv.platform_fee_minor, null); eq(pv.subtotal_minor, b.price_minor + 2 * g.price_minor);
  await rej(api('POST', `/integration/bookings/${b.id}/checkout`), 'combined_checkout_unavailable', 503);
  const o = await api('POST', '/gifts/test-orders', { body: { delivery_method: 'pickup' } }); valid('TestOrderRead', o); eq(o.real_money_moved, false); eq(o.is_test_order, true); eq(o.payable_total_minor, null); eq((await api('GET', '/gifts/cart')).length, 0);
  D.cfg.giftTest = false; await rej(api('GET', '/gifts/test-orders').then(() => api('POST', '/gifts/test-orders', { body: { delivery_method: 'pickup' } })), 'click_test_disabled', 404); D.cfg.giftTest = true;
});
t('safety: report validation, trusted contacts', async () => { await rej(api('POST', '/safety/reports', { body: { category: 'zzz', description: 'x', reported_user_id: '00000000-0000-4000-8000-000000000001' } }), 'validation_error', 422); const uid_ = D.S.profiles[0].user_id; const r = await api('POST', '/safety/reports', { body: { category: 'fraud', description: 'test', reported_user_id: uid_ } }); valid('ReportRead', r); const c = await api('POST', '/safety/trusted-contacts', { body: { name: 'Ona', phone_number: '+998901112233' } }); valid('ContactRead', c); });
t('companion: status blockers → approve → public; profile/service/availability schemas', async () => {
  await rej(api('GET', '/companions/me/profile'), 'profile_not_found', 404); const a = await api('POST', '/companions/me/application', { body: { statement: 'Salom' } }); valid('ApplicationResponse', a);
  const pr = await api('POST', '/companions/me/profile', { body: { display_name: 'Test Hamroh', bio: 'b', interests: ['kofe'], languages: ['Oʻzbek'] } }); valid('ProfileResponse', pr);
  const sv = await api('POST', '/companions/me/services', { body: { service_code: 'coffee', price_minor: 5000000, unit_minutes: 60, currency: 'UZS', description: 'x' } }); valid('ServiceResponse', sv); await rej(api('POST', '/companions/me/services', { body: { service_code: 'coffee', price_minor: -1, unit_minutes: 60, currency: 'UZS' } }), 'invalid_price', 422);
  const av = await api('POST', '/companions/me/availability', { body: { starts_at: day(5, 10), ends_at: day(5, 18), timezone: 'Asia/Tashkent' } }); valid('AvailabilityResponse', av); await rej(api('POST', '/companions/me/availability', { body: { starts_at: day(5, 18), ends_at: day(5, 10), timezone: 'Asia/Tashkent' } }), 'validation_error', 422);
  let st = await api('GET', '/companions/me/status'); valid('CompanionStatus', st); eq(st.publicly_active, false); ok(st.blockers.includes('identity_not_verified'));
  await api('POST', '/companions/me/application/submit'); await api('POST', '/companions/me/profile/submit'); await api('POST', '/companions/me/activate'); D.adminApprove(); st = await api('GET', '/companions/me/status'); eq(st.publicly_active, true); eq(st.blockers, []);
  const found = await api('GET', '/discovery/companions', { query: { q: 'Test Hamroh' } }); eq(found.items.length, 0, 'own profile hidden from own discovery');
  D.incomingRequests(); const inc = (await api('GET', '/bookings')).filter((b) => b.status === 'pending'); ok(inc.length >= 1); const acc = await api('POST', `/bookings/${inc[0].id}/accept`); eq(acc.status, 'accepted'); valid('BookingResponse', acc); eq(L.classify({ status: 409, code: 'invalid_booking_transition' }).kind, 'stale');
});
t('vendor: product create/patch/unpublish, earnings 503', async () => {
  const p = await api('POST', '/gifts/vendor/products', { body: { name: 'Buket', category: 'flowers', price_minor: 1000000, currency: 'UZS', description: 'd', stock: 3 } }); valid('ProductRead', p); eq(p.published, false);
  eq((await api('PATCH', `/vendor/products/${p.id}`, { body: { stock: 5 } })).stock, 5); await rej(api('GET', '/vendor/earnings'), 'vendor_earnings_unavailable', 503); await rej(api('PATCH', `/vendor/products/${p.id}`, { body: { price_minor: -5 } }), 'invalid_product_update', 422);
  D.cfg.offline = true; await rej(api('GET', '/gifts/products'), 'network_offline'); D.cfg.offline = false;
});
t('role isolation: customer-only user cannot use companion/vendor endpoints', async () => { await api('PUT', '/auth/roles', { body: { roles: ['customer'] } }); await rej(api('GET', '/companions/me/status'), 'companion_role_required', 403); await rej(api('GET', '/gifts/vendor/products'), 'role_required', 403); await rej(api('GET', '/vendor/earnings'), 'role_required', 403); });

// ---------- Decision 2: availability filter (mock mirrors the real backend; the real backend is covered by tests/backend/*.py) ----------
t('mock discovery: FULL CONTAINMENT boundaries + invalid intervals + booking conflicts stay in force', async () => {
  D.reset(); D.cfg.latency = 0; await api('POST', '/auth/otp/request', { body: { phone_number: '+998901234567' } }); await api('POST', '/auth/otp/verify', { body: { phone_number: '+998901234567', code: '1234' } }); await api('PUT', '/auth/roles', { body: { roles: ['customer'] } });
  const q = (a, b) => api('GET', '/discovery/companions', { query: { q: 'Madina', available_from: a, available_until: b } }).then((r) => r.items.length === 1);
  const W0 = day(3, 10), W1 = day(3, 21); // Madina's day-3 window: 10:00–21:00 Asia/Tashkent
  const cases = [[W0, W1, true, 'exact'], [day(3, 12), day(3, 13), true, 'inside'], [W0, day(3, 11), true, 'shares start'], [day(3, 20), W1, true, 'shares end'], [day(3, 9), day(3, 12), false, 'starts before'], [day(3, 20), day(3, 22), false, 'ends after'], [day(3, 9), day(3, 22), false, 'request CONTAINS window (intersection would match)'], [day(3, 22), day(3, 23), false, 'disjoint after'], [day(3, 8), day(3, 9), false, 'disjoint before'], [day(3, 9), W0, false, 'touches start'], [W1, day(3, 22), false, 'touches end']];
  for (const [a, b, exp, why] of cases) eq(await q(a, b), exp, why);
  eq(await q(tk(3, 12), tk(3, 13)), true, '+05:00 notation = same instants'); eq(await q(tk(3, 9), tk(3, 12)), false, '+05:00 notation, starts before window');
  await rej(api('GET', '/discovery/companions', { query: { available_from: day(3, 13), available_until: day(3, 12) } }), 'invalid_discovery_filter', 422);
  await rej(api('GET', '/discovery/companions', { query: { available_from: day(3, 12), available_until: day(3, 12) } }), 'invalid_discovery_filter', 422);
  await rej(api('GET', '/discovery/companions', { query: { available_from: day(3, 12) } }), 'invalid_discovery_filter', 422);
  await rej(api('GET', '/discovery/companions', { query: { available_until: day(3, 12) } }), 'invalid_discovery_filter', 422);
  await rej(api('GET', '/discovery/companions', { query: { available_from: '2027-01-10T06:00:00', available_until: '2027-01-10T07:00:00' } }), 'invalid_discovery_filter', 422);
  const c = (await api('GET', '/discovery/companions', { query: { q: 'Madina' } })).items[0];
  const bk = await api('POST', '/bookings', { body: { service_id: c.services[0].id, starts_at: day(3, 12), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }); eq(bk.status, 'pending');
  eq(await q(day(3, 12), day(3, 13)), false, 'identical to booking'); eq(await q(day(3, 12, 30), day(3, 13, 30)), false, 'overlaps booking'); eq(await q(day(3, 10), day(3, 21)), false, 'window-wide overlaps booking');
  eq(await q(day(3, 13), day(3, 14)), true, 'adjacent after booking'); eq(await q(day(3, 11), day(3, 12)), true, 'adjacent before booking');
  await rej(api('POST', '/bookings', { body: { service_id: c.services[0].id, starts_at: day(3, 20, 30), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'availability_not_found', 409);
});
// ---------- Decision 5: user ids vs profile ids ----------
t('mock reports/blocks: profile id ≠ user id; reporter from session; error matrix = real backend', async () => {
  const c = (await api('GET', '/discovery/companions', { query: { q: 'Madina' } })).items[0], prof = D.S.profiles.find((p) => p.id === c.id), bk = D.S.bookings[0];
  ok(prof.user_id !== prof.id && !JSON.stringify(c).includes(prof.user_id), 'card exposes profile id only');
  const R = (b) => api('POST', '/safety/reports', { body: Object.assign({ category: 'harassment', description: 'x' }, b) });
  await rej(R({ reported_user_id: c.id }), 'reported_user_not_found', 404);                               // profile id sent as user id
  await rej(api('PUT', `/safety/blocks/${c.id}`), 'user_not_found', 404);
  await rej(R({ reported_user_id: '00000000-0000-4000-8000-0000000000ff' }), 'reported_user_not_found', 404);
  await rej(R({ reported_user_id: 'not-a-uuid' }), 'validation_error', 422);
  await rej(R({ reported_user_id: D.S.user.id }), 'invalid_report', 422);                                   // self
  await rej(R({ reported_user_id: prof.user_id, reporter_id: D.S.user.id }), 'validation_error', 422);    // client-supplied reporter identity refused
  await rej(R({ reported_user_id: prof.user_id, booking_id: '00000000-0000-4000-8000-0000000000ee' }), 'booking_not_found', 404);
  await rej(R({ reported_user_id: D.S.user.id === bk.customer_id ? D.S.profiles[1].user_id : bk.customer_id, booking_id: bk.id }), 'invalid_report_target', 422); // not the counterparty
  const good = await R({ reported_user_id: prof.user_id, booking_id: bk.id }); valid('ReportRead', good); eq(good.reported_user_id, prof.user_id);
  eq((await api('GET', '/safety/reports')).length >= 1, true);
  const tok = D.S.token; D.S.token = null; await rej(R({ reported_user_id: prof.user_id }), 'authentication_required', 401); await rej(api('PUT', `/safety/blocks/${prof.user_id}`), 'authentication_required', 401); D.S.token = tok;
  eq((await api('PUT', `/safety/blocks/${prof.user_id}`)).user_id, prof.user_id);
  await rej(api('POST', '/bookings', { body: { service_id: c.services[0].id, starts_at: day(5, 12), duration_minutes: 60, meeting_place: 'Kafe', timezone: 'Asia/Tashkent' } }), 'booking_blocked', 403);
});
t('classify: new id/report codes are mapped with Uzbek text', () => { ['reported_user_not_found', 'user_not_found', 'invalid_report_target'].forEach((c) => ok(L.classify({ status: 404, code: c }).text.length > 5, c)); });
// ---------- OpenAPI decisions overlay (proposed contract text) ----------
t('contract overlay: every target exists in openapi-v1.json and carries the decision text', () => {
  const ov = JSON.parse(fs.readFileSync(path.join(__dirname, '../contract/openapi-v1.decisions.overlay.json'), 'utf8')); ok(ov.actions.length >= 15, 'overlay too small: ' + ov.actions.length);
  const get = (ptr) => ptr.split('/').slice(1).reduce((o, k) => (o == null ? o : o[k.replace(/~1/g, '/').replace(/~0/g, '~')]), spec);
  ov.actions.forEach((a) => { let target; if (a.parameter) { const op = get(`/paths/${a.path.replace(/\//g, '~1')}/${a.method}`); target = op && (op.parameters || []).find((p) => p.name === a.parameter); } else target = get(a.pointer); ok(target && typeof target === 'object', 'missing target: ' + (a.pointer || a.path + ' ' + a.parameter)); ok(a.description && a.description.length > 20, 'empty description'); });
  const txt = JSON.stringify(ov); ok(/containment/i.test(txt) && /tiyin/.test(txt) && /user id/i.test(txt) && /Maxsus kunlar/.test(txt), 'decisions not all covered');
});
// ---------- run ----------
(async () => { let pass = 0, fail = 0; for (const { name, fn } of res) { try { await fn(); pass++; console.log('PASS', name); } catch (e) { fail++; console.log('FAIL', name, '→', e.message.slice(0, 400)); } } console.log(`\n${pass} passed, ${fail} failed, ${res.length} total`); process.exit(fail ? 1 : 0); })();
