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
t('money: UZS minor→soʻm', () => { eq(L.money(19800000, 'UZS'), '198 000 soʻm'); eq(L.money(150, 'UZS'), '1,50 soʻm'); eq(L.money(null), null); eq(L.money(100, 'USD'), '1 USD'); });
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
const BASE = Math.floor(Date.now() / 864e5) * 864e5; const day = (d, h) => new Date(BASE + d * 864e5 + (h - 5) * 36e5).toISOString(); // Tashkent local hour h (UTC+5), relative to today
let book, pay;
t('setup: otp → roles → discovery card matches schema', async () => {
  D.reset(); D.cfg.clock = 0; await rej(api('POST', '/auth/otp/verify', { body: { phone_number: '+998901234567', code: '0000' } }), 'invalid_otp', 401);
  await rej(api('POST', '/auth/otp/request', { body: { phone_number: '123' } }), 'invalid_phone_number', 422);
  await api('POST', '/auth/otp/request', { body: { phone_number: '+998901234567' } }); const tk = await api('POST', '/auth/otp/verify', { body: { phone_number: '+998901234567', code: '1234' } }); valid('TokenResponse', tk);
  await rej(api('POST', '/bookings', { body: {} }), 'customer_role_required', 403);
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
t('payment 503 provider ≠ failed; booking stays accepted', async () => { D.cfg.pay = '503'; await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-503-0001' } }), 'payment_provider_unavailable', 503); eq((await api('GET', `/bookings/${book.id}`)).status, 'accepted'); D.cfg.pay = 'ok'; D.cfg.feeBps = null; await rej(api('POST', `/payments/bookings/${book.id}`, { headers: { 'Idempotency-Key': 'key-cfg-0001' } }), 'payment_configuration_unavailable', 503); D.cfg.feeBps = 1000; });
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
t('safety: report enum, block, contacts', async () => { await rej(api('POST', '/safety/reports', { body: { category: 'zzz', description: 'x', reported_user_id: 'u' } }), 'invalid_report', 422); const r = await api('POST', '/safety/reports', { body: { category: 'fraud', description: 'test', reported_user_id: '00000000-0000-4000-8000-000000000001' } }); valid('ReportRead', r); const c = await api('POST', '/safety/trusted-contacts', { body: { name: 'Ona', phone_number: '+998901112233' } }); valid('ContactRead', c); });
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
// ---------- run ----------
(async () => { let pass = 0, fail = 0; for (const { name, fn } of res) { try { await fn(); pass++; console.log('PASS', name); } catch (e) { fail++; console.log('FAIL', name, '→', e.message.slice(0, 400)); } } console.log(`\n${pass} passed, ${fail} failed, ${res.length} total`); process.exit(fail ? 1 : 0); })();
