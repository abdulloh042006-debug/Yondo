/* DEMO mock of the Yondo API. Mirrors docs/openapi-v1.json shapes and the backend's real error codes. NOT the real backend. */
(function (root, factory) { if (typeof module === 'object' && module.exports) module.exports = factory(); else root.YM = factory(); })(typeof self !== 'undefined' ? self : this, function () {
  const cfg = { offline: false, latency: 180, pay: 'ok', feeBps: 1000, clock: 0, giftTest: true, calls: [] };
  const now = () => Date.now() + cfg.clock;
  let n = 0; const uid = () => { n++; const h = (n + 0x1000000).toString(16); return `00000000-0000-4000-8000-${h.padStart(12, '0')}`; };
  const iso = (t) => new Date(t).toISOString();
  const err = (status, code, message, extra) => Object.assign(new Error(code), { status, code, message: message || code, request_id: 'req-demo-' + (++n) }, extra || {});
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const T0 = Math.floor(Date.now() / 864e5) * 864e5; // start of today (UTC); availability seeded relative to it
  const svc = (code, p, u, d) => ({ id: uid(), service_code: code, price_minor: p, unit_minutes: u, currency: 'UZS', description: d });
  const mkProf = (name, age, langs, ints, bio, services, o) => Object.assign({ id: uid(), user_id: uid(), display_name: name, age, city: 'Toshkent', gender: null, bio, languages: langs, interests: ints, services, photos: [], rating: null, review_count: 0, verified: false, hue: 0 }, o || {});
  const S = {
    user: null, roles: [], token: null, otp: false,
    profiles: [], bookings: [], payments: [], messages: {}, meetings: {}, reviews: [], reports: [], blocks: [], contacts: [], cart: [], testOrders: [], products: [], notifs: [], sos: [],
    me: { app: null, prof: null, status: null, services: [], avail: [] }
  };
  function seed() {
    S.profiles = [
      mkProf('Madina K.', 26, ['Oʻzbek', 'Rus', 'Ingliz'], ['kitoblar', 'kofe'], 'Sokin suhbat va yaxshi kofe sevaman.', [svc('coffee', 9000000, 60, 'Kofe ustida suhbat'), svc('walking', 8000000, 60, 'Xiyobonda sayr')], { rating: 4.8, review_count: 23, verified: true, hue: 160 }),
      mkProf('Jasur A.', 29, ['Oʻzbek', 'Rus'], ['kino', 'sport'], 'Kino va shahar tadbirlariga hamroh.', [svc('cinema', 12000000, 120, 'Kinoga hamroh'), svc('event', 10000000, 60, 'Tadbirga hamroh')], { rating: 4.6, review_count: 12, verified: true, hue: 30 }),
      mkProf('Nilufar R.', 24, ['Oʻzbek', 'Ingliz'], ['tillar', 'sayohat'], 'Shaharga yangi kelganlarga yoʻl koʻrsataman.', [svc('city_friend', 11000000, 120, 'Shahar doʻsti'), svc('conversation', 7000000, 60, 'Ingliz tilida suhbat')], { rating: 4.9, review_count: 31, verified: true, hue: 200 }),
      mkProf('Sardor T.', 31, ['Oʻzbek', 'Rus'], ['biznes', 'kitoblar'], 'Yangi profil. Coworking uchun hamroh.', [svc('study', 6000000, 60, 'Birga oʻqish'), svc('conversation', 6500000, 60, 'Suhbat')], { hue: 80 }),
      mkProf('Dilnoza M.', 27, ['Oʻzbek', 'Rus', 'Ingliz'], ['moda', 'shopping'], 'Xaridda maslahat va hamrohlik.', [svc('shopping', 9500000, 120, 'Xaridda hamroh'), svc('coffee', 9000000, 60, 'Kofe')], { rating: 4.7, review_count: 18, verified: true, hue: 340 })
    ];
    S.profiles.forEach((p) => { p.avail = []; for (let d = 0; d < 14; d++) { const day = Math.floor(T0 / 864e5) * 864e5 + d * 864e5; p.avail.push({ id: uid(), profile_id: p.id, starts_at: iso(day + 5 * 36e5), ends_at: iso(day + 16 * 36e5), timezone: 'Asia/Tashkent' }); } });
    // Madina closed on day 2 → exercises availability_not_found
    S.profiles[0].avail = S.profiles[0].avail.filter((a, i) => i !== 2);
    S.products = [
      { id: uid(), vendor_id: '00000000-0000-4000-8000-0000000000aa', name: 'Mavsumiy gul buketi', category: 'flowers', price_minor: 15000000, currency: 'UZS', description: 'DEMO', stock: 12, published: true },
      { id: uid(), vendor_id: '00000000-0000-4000-8000-0000000000aa', name: 'Shokolad toʻplami', category: 'chocolate', price_minor: 8000000, currency: 'UZS', description: 'DEMO', stock: 30, published: true },
      { id: uid(), vendor_id: '00000000-0000-4000-8000-0000000000aa', name: 'Maxsus kun buketi', category: 'romantic', price_minor: 18000000, currency: 'UZS', description: 'DEMO', stock: 0, published: true }
    ];
  }
  seed();
  const card = (p) => ({ id: p.id, display_name: p.display_name, age: p.age, bio: p.bio, city: p.city, gender: p.gender, interests: p.interests, languages: p.languages, photos: p.photos, rating: p.rating, review_count: p.review_count, services: p.services.map(({ id, service_code, price_minor, unit_minutes, currency, description }) => ({ id, service_code, price_minor, unit_minutes, currency, description })), verified: p.verified });
  const myProfile = () => S.profiles.find((p) => p.user_id === S.user.id);
  const need = (role) => { if (!S.token) throw err(401, 'authentication_required'); if (!S.roles.includes(role)) throw err(403, role === 'customer' ? 'customer_role_required' : role === 'companion' ? 'companion_role_required' : 'role_required'); };
  const bk = (id) => { const b = S.bookings.find((x) => x.id === id); if (!b) throw err(404, 'booking_not_found'); return b; };
  const isCust = (b) => b.customer_id === S.user.id;
  const isComp = (b) => { const p = myProfile(); return !!p && p.id === b.profile_id; };
  function part(b) { if (!isCust(b) && !isComp(b)) throw err(404, 'booking_not_found'); return isCust(b) ? 'customer' : 'companion'; }
  const sysmsg = (b, code, text) => { (S.messages[b.id] = S.messages[b.id] || []).push({ id: uid(), booking_id: b.id, sender_id: null, kind: 'system', body: text, payload: { status: b.status }, system_code: code, created_at: iso(now()) }); };
  const notify = (b, kind) => S.notifs.unshift({ id: uid(), booking_id: b.id, gift_order_id: null, kind, details: { status: b.status }, created_at: iso(now()), read_at: null });
  function profileStatus() {
    const m = S.me, bl = [];
    if (!m.app || m.app.status !== 'approved') bl.push('application_not_approved');
    if (!m.prof || m.prof.content_status !== 'approved') bl.push('content_not_approved');
    if (m.identity !== 'verified') bl.push('identity_not_verified');
    return { account_status: 'active', activation_requested: !!(m.prof && m.prof.activation_requested), application_status: m.app ? m.app.status : 'draft', blockers: bl, content_status: m.prof ? m.prof.content_status : 'draft', identity_status: m.identity || 'unknown', publicly_active: !bl.length && !!(m.prof && m.prof.activation_requested) };
  }
  function syncPublic() { const m = S.me; let p = S.profiles.find((x) => x.user_id === S.user.id); const st = profileStatus(); if (st.publicly_active && !p) { p = mkProf(m.prof.display_name, null, m.prof.languages, m.prof.interests, m.prof.bio, m.services, { user_id: S.user.id, verified: true, id: m.prof.id }); p.avail = m.avail; S.profiles.push(p); } if (p) { p.display_name = m.prof ? m.prof.display_name : p.display_name; p.bio = m.prof ? m.prof.bio : p.bio; p.interests = m.prof ? m.prof.interests : p.interests; p.languages = m.prof ? m.prof.languages : p.languages; p.services = m.services; p.avail = m.avail; if (!st.publicly_active) S.profiles = S.profiles.filter((x) => x !== p); } }
  const need422 = (cond, loc, msg) => { if (cond) throw err(422, 'validation_error', 'Request validation failed', { errors: [{ type: 'value_error', loc: ['body', loc], msg }] }); };
  const avail = (p, s, e) => p.avail.some((a) => Date.parse(a.starts_at) <= s && Date.parse(a.ends_at) >= e);
  const overlap = (p, s, e) => S.bookings.some((b) => b.profile_id === p.id && ['pending', 'accepted', 'confirmed', 'active'].includes(b.status) && Date.parse(b.starts_at) < e && Date.parse(b.ends_at) > s);

  const R = [];
  const on = (m, re, fn) => R.push([m, re, fn]);
  // ---- auth ----
  on('POST', /^\/auth\/otp\/request$/, ({ body }) => { if (!/^\+998\d{9}$/.test(body.phone_number || '')) throw err(422, 'invalid_phone_number'); S.otp = true; return { development_otp: '1234', expires_in_seconds: 300, message: 'DEMO', resend_after_seconds: 30 }; });
  on('POST', /^\/auth\/otp\/verify$/, ({ body }) => { if (body.code !== '1234') throw err(401, 'invalid_otp'); if (!S.user) S.user = { id: uid(), phone_number: body.phone_number }; S.token = 'demo-' + uid(); return { access_token: S.token, refresh_token: 'demo-r', expires_in: 900, token_type: 'bearer' }; });
  on('GET', /^\/auth\/me$/, () => { if (!S.token) throw err(401, 'authentication_required'); return { id: S.user.id, roles: S.roles, account_status: 'active' }; });
  on('PUT', /^\/auth\/roles$/, ({ body }) => { if (!S.token) throw err(401, 'authentication_required'); const r = body.roles || []; if (new Set(r).size !== r.length) throw err(422, 'duplicate_role'); S.roles = r; return { roles: r }; });
  // ---- discovery ----
  on('GET', /^\/discovery\/companions$/, ({ query: q }) => {
    let l = S.profiles.filter((p) => !(S.user && p.user_id === S.user.id));
    if (q.q) { const k = q.q.toLowerCase(); l = l.filter((p) => (p.display_name + ' ' + p.city + ' ' + p.interests.join(' ')).toLowerCase().includes(k)); }
    if (q.service_code) l = l.filter((p) => p.services.some((s) => s.service_code === q.service_code));
    if (q.rating_min) l = l.filter((p) => p.rating !== null && p.rating >= +q.rating_min);
    if (q.language) l = l.filter((p) => p.languages.includes(q.language));
    const pr = (p) => Math.min(...p.services.map((s) => s.price_minor * 60 / s.unit_minutes));
    if (q.price_min_minor) l = l.filter((p) => pr(p) >= +q.price_min_minor);
    if (q.price_max_minor) l = l.filter((p) => pr(p) <= +q.price_max_minor);
    if (q.available_from && q.available_until) { const a = Date.parse(q.available_from), b = Date.parse(q.available_until); if (isNaN(a) || isNaN(b) || b <= a) throw err(422, 'invalid_discovery_filter'); l = l.filter((p) => avail(p, a, b) && !overlap(p, a, b)); }
    const lim = +q.limit || 30, off = +q.offset || 0;
    return { items: l.slice(off, off + lim).map(card), has_more: off + lim < l.length, limit: lim, offset: off };
  });
  on('GET', /^\/discovery\/companions\/([^/]+)$/, ({ m }) => { const p = S.profiles.find((x) => x.id === m[1]); if (!p) throw err(404, 'companion_not_found'); return card(p); });
  // ---- bookings ----
  on('GET', /^\/bookings$/, () => { if (!S.token) throw err(401, 'authentication_required'); const p = S.roles.includes('companion') ? myProfile() : null; return S.bookings.filter((b) => isCust(b) || (p && b.profile_id === p.id)).map(clone).sort((a, b) => (a.starts_at < b.starts_at ? 1 : -1)); });
  on('POST', /^\/bookings$/, ({ body }) => {
    need('customer'); const p = S.profiles.find((x) => x.services.some((s) => s.id === body.service_id)); if (!p) throw err(404, 'companion_service_not_found');
    if (p.user_id === S.user.id) throw err(403, 'self_booking_forbidden');
    if (S.blocks.includes(p.user_id) || S.blocks.includes(p.id)) throw err(403, 'booking_blocked');
    const s = p.services.find((x) => x.id === body.service_id); const st = Date.parse(body.starts_at);
    need422(!body.meeting_place || !body.meeting_place.trim(), 'meeting_place', 'required'); need422(!body.timezone, 'timezone', 'required'); need422(isNaN(st), 'starts_at', 'invalid');
    if (!Number.isInteger(body.duration_minutes) || body.duration_minutes <= 0 || body.duration_minutes % s.unit_minutes) throw err(422, 'invalid_booking_duration');
    if (st <= now()) throw err(422, 'booking_start_in_past'); const en = st + body.duration_minutes * 6e4;
    if (!avail(p, st, en)) throw err(409, 'availability_not_found'); if (overlap(p, st, en)) throw err(409, 'booking_time_unavailable');
    const b = { id: uid(), customer_id: S.user.id, profile_id: p.id, service_id: s.id, service_code: s.service_code, service_description: s.description, starts_at: iso(st), ends_at: iso(en), duration_minutes: body.duration_minutes, meeting_place: body.meeting_place.trim(), timezone: body.timezone, price_minor: s.price_minor * (body.duration_minutes / s.unit_minutes), currency: s.currency, status: 'pending', created_at: iso(now()), customer_contract_accepted_at: iso(now()), companion_contract_accepted_at: null };
    S.bookings.push(b); sysmsg(b, 'booking_requested', 'Bron soʻrovi yuborildi.'); notify(b, 'booking_requested'); return clone(b);
  });
  on('GET', /^\/bookings\/([^/]+)$/, ({ m }) => { const b = bk(m[1]); part(b); return clone(b); });
  on('POST', /^\/bookings\/([^/]+)\/(accept|decline|cancel)$/, ({ m, body }) => {
    const b = bk(m[1]); const who = part(b), act = m[2];
    if (act === 'cancel') { if (!['pending', 'accepted', 'confirmed'].includes(b.status)) throw err(409, 'invalid_booking_transition'); const paid = S.payments.some((x) => x.booking_id === b.id && x.status === 'succeeded'); b.status = 'cancelled'; if (paid) S.payments.filter((x) => x.booking_id === b.id).forEach((x) => (x.refund_required = true)); sysmsg(b, 'booking_cancelled', 'Bron bekor qilindi.'); notify(b, 'booking_cancelled'); return clone(b); }
    if (who !== 'companion') throw err(403, 'companion_role_required'); if (b.status !== 'pending') throw err(409, 'invalid_booking_transition');
    if (act === 'accept') { b.status = 'accepted'; b.companion_contract_accepted_at = iso(now()); sysmsg(b, 'booking_accepted', 'Hamroh bronni qabul qildi. Endi toʻlash mumkin.'); notify(b, 'booking_accepted'); } else { b.status = 'cancelled'; sysmsg(b, 'booking_declined', 'Hamroh bronni rad etdi.'); notify(b, 'booking_declined'); }
    return clone(b);
  });
  // ---- payments (only for ACCEPTED bookings; Idempotency-Key required) ----
  const payResp = (p) => clone(p);
  on('POST', /^\/payments\/bookings\/([^/]+)$/, ({ m, headers }) => {
    const b = bk(m[1]); if (!isCust(b)) throw err(404, 'booking_not_found'); const key = headers['Idempotency-Key'];
    if (!key || key.length < 8 || key.length > 128) throw err(422, 'validation_error', 'Request validation failed', { errors: [{ type: 'string_too_short', loc: ['header', 'idempotency-key'], msg: 'invalid' }] });
    const ex = S.payments.find((x) => x.key === key); if (ex) { if (ex.booking_id !== b.id) throw err(409, 'idempotency_key_conflict'); return payResp(ex); }
    if (b.status !== 'accepted') throw err(409, 'booking_not_payable');
    if (cfg.feeBps === null) throw err(503, 'payment_configuration_unavailable');
    if (cfg.pay === '503') throw err(503, 'payment_provider_unavailable');
    const fee = Math.round(b.price_minor * cfg.feeBps / 10000); const p = { id: uid(), key, booking_id: b.id, subtotal_minor: b.price_minor, platform_fee_minor: fee, amount_minor: b.price_minor + fee, currency: b.currency, status: 'pending', checkout_url: 'demo://provider/' + b.id, refund_required: false, created_at: iso(now()) };
    S.payments.push(p); return payResp(p);
  });
  on('GET', /^\/payments\/bookings\/([^/]+)$/, ({ m }) => { const b = bk(m[1]); part(b); return S.payments.filter((p) => p.booking_id === b.id).map(payResp); });
  // ---- integration (gift + booking): preview works, checkout is unavailable in the real backend ----
  on('GET', /^\/integration\/bookings\/([^/]+)\/preview$/, ({ m }) => { need('customer'); const b = bk(m[1]); if (!isCust(b)) throw err(404, 'booking_not_found'); if (b.status !== 'accepted') throw err(409, 'booking_not_payable'); const items = S.cart.map((c) => { const pr = S.products.find((x) => x.id === c.product_id); return { product_id: pr.id, name: pr.name, quantity: c.quantity, unit_price_minor: pr.price_minor, line_total_minor: pr.price_minor * c.quantity }; }); const g = items.reduce((a, i) => a + i.line_total_minor, 0); return { booking_id: b.id, booking_service_minor: b.price_minor, gift_items: items, gift_subtotal_minor: g, subtotal_minor: b.price_minor + g, currency: b.currency, platform_fee_minor: null, delivery_fee_minor: null, total_minor: null, checkout_available: false, reason: 'combined_payment_and_delivery_policy_unconfigured' }; });
  on('POST', /^\/integration\/bookings\/([^/]+)\/checkout$/, ({ m }) => { need('customer'); const b = bk(m[1]); if (!isCust(b)) throw err(404, 'booking_not_found'); if (b.status !== 'accepted') throw err(409, 'booking_not_payable'); throw err(503, 'combined_checkout_unavailable'); });
  // ---- gifts ----
  on('GET', /^\/gifts\/products$/, () => S.products.filter((p) => p.published).map(clone));
  on('GET', /^\/gifts\/cart$/, () => { need('customer'); return clone(S.cart); });
  on('PUT', /^\/gifts\/cart\/([^/]+)$/, ({ m, body }) => { need('customer'); const p = S.products.find((x) => x.id === m[1]); if (!p) throw err(404, 'gift_not_found'); if (!p.published || p.stock < body.quantity) throw err(409, 'gift_unavailable'); need422(!(body.quantity >= 1 && body.quantity <= 100), 'quantity', 'range'); const c = S.cart.find((x) => x.product_id === p.id); if (c) c.quantity = body.quantity; else S.cart.push({ product_id: p.id, quantity: body.quantity }); return clone(S.cart.find((x) => x.product_id === p.id)); });
  on('DELETE', /^\/gifts\/cart\/([^/]+)$/, ({ m }) => { need('customer'); S.cart = S.cart.filter((c) => c.product_id !== m[1]); return null; });
  on('POST', /^\/gifts\/test-orders$/, ({ body }) => { need('customer'); if (!cfg.giftTest) throw err(404, 'click_test_disabled'); if (!S.cart.length) throw err(409, 'cart_empty'); if (body.delivery_method === 'manual_delivery' && !(body.delivery_note || '').trim()) throw err(422, 'gift_delivery_note_required'); const items = S.cart.map((c) => { const p = S.products.find((x) => x.id === c.product_id); return { product_id: p.id, name_snapshot: p.name, quantity: c.quantity, unit_price_minor: p.price_minor, line_total_minor: p.price_minor * c.quantity }; }); const o = { id: uid(), customer_id: S.user.id, items, subtotal_minor: items.reduce((a, i) => a + i.line_total_minor, 0), currency: 'UZS', status: 'awaiting_test_payment', delivery_method: body.delivery_method, delivery_note: body.delivery_note || null, delivery_fee_minor: null, payable_total_minor: null, is_test_order: true, real_money_moved: false, operator_fulfillment: true, click_test_trans_id: null, created_at: iso(now()) }; S.testOrders.push(o); S.cart = []; return clone(o); });
  on('GET', /^\/gifts\/test-orders$/, () => { need('customer'); return clone(S.testOrders); });
  // ---- meetings / chat / reviews / safety ----
  const meet = (b) => { const m = (S.meetings[b.id] = S.meetings[b.id] || { c: false, p: false, ec: false, ep: false }); return m; };
  const mstate = (b) => { const m = meet(b); return { arrived_count: +m.c + +m.p, booking_id: b.id, booking_status: b.status, companion_arrived: m.p, customer_arrived: m.c, ended_count: +m.ec + +m.ep }; };
  on('GET', /^\/meetings\/bookings\/([^/]+)$/, ({ m }) => { const b = bk(m[1]); part(b); return mstate(b); });
  on('POST', /^\/meetings\/bookings\/([^/]+)\/(check-in|start|end)$/, ({ m }) => {
    const b = bk(m[1]), who = part(b), s = meet(b), a = m[2];
    if (a === 'check-in') { if (b.status !== 'confirmed') throw err(409, 'meeting_state_conflict'); if (now() < Date.parse(b.starts_at)) throw err(409, 'meeting_too_early'); if (who === 'customer') s.c = true; else s.p = true; sysmsg(b, 'checked_in', (who === 'customer' ? 'Mijoz' : 'Hamroh') + ' yetib keldi.'); }
    if (a === 'start') { if (b.status !== 'confirmed') throw err(409, 'meeting_state_conflict'); if (!(s.c && s.p)) throw err(409, 'meeting_not_ready'); b.status = 'active'; sysmsg(b, 'meeting_started', 'Uchrashuv boshlandi.'); }
    if (a === 'end') { if (b.status === 'completed') throw err(409, 'meeting_already_ended'); if (b.status !== 'active') throw err(409, 'meeting_not_active'); if (who === 'customer') s.ec = true; else s.ep = true; if (s.ec || s.ep) { b.status = 'completed'; sysmsg(b, 'meeting_ended', 'Uchrashuv yakunlandi.'); notify(b, 'review_reminder'); } }
    return mstate(b);
  });
  on('GET', /^\/chat\/bookings\/([^/]+)\/messages$/, ({ m }) => { const b = bk(m[1]); part(b); return clone(S.messages[b.id] || []); });
  on('POST', /^\/chat\/bookings\/([^/]+)\/messages$/, ({ m, body }) => { const b = bk(m[1]); part(b); if (b.status === 'cancelled' || b.status === 'completed') throw err(409, 'chat_closed'); need422(!body.body || !body.body.trim() || body.body.length > 4000, 'body', 'length'); const x = { id: uid(), booking_id: b.id, sender_id: S.user.id, kind: body.kind || 'text', body: body.body, payload: null, system_code: null, created_at: iso(now()) }; (S.messages[b.id] = S.messages[b.id] || []).push(x); return clone(x); });
  on('POST', /^\/reviews\/bookings\/([^/]+)$/, ({ m, body }) => { const b = bk(m[1]); const who = part(b); if (b.status !== 'completed') throw err(409, 'review_not_ready'); if (S.reviews.some((r) => r.booking_id === b.id && r.reviewer_id === S.user.id)) throw err(409, 'review_already_exists'); need422(!(body.stars >= 1 && body.stars <= 5), 'stars', 'range'); const r = { id: uid(), booking_id: b.id, reviewer_id: S.user.id, reviewee_id: who === 'customer' ? b.profile_id : b.customer_id, stars: body.stars, comment: body.comment || '', tags: body.tags || [] }; S.reviews.push(r); return clone(r); });
  on('POST', /^\/safety\/reports$/, ({ body }) => { if (!S.token) throw err(401, 'authentication_required'); const c = ['harassment', 'inappropriate_request', 'fake_profile', 'fraud', 'unsafe_behavior', 'no_show', 'payment_issue', 'other']; if (!c.includes(body.category) || !(body.description || '').trim()) throw err(422, 'invalid_report'); const r = Object.assign({ id: uid(), status: 'open' }, body); S.reports.push(r); return clone(r); });
  on('PUT', /^\/safety\/blocks\/([^/]+)$/, ({ m }) => { if (!S.token) throw err(401, 'authentication_required'); if (!S.blocks.includes(m[1])) S.blocks.push(m[1]); return { user_id: m[1] }; });
  on('POST', /^\/safety\/bookings\/([^/]+)\/sos$/, ({ m, query }) => { const b = bk(m[1]); part(b); if (query.confirmed !== 'true') throw err(422, 'sos_confirmation_required'); if (b.status !== 'active') throw err(409, 'sos_requires_active_booking'); const a = { id: uid(), emergency_service_contacted: false }; S.sos.push(a); return a; });
  on('GET', /^\/safety\/trusted-contacts$/, () => { if (!S.token) throw err(401, 'authentication_required'); return clone(S.contacts); });
  on('POST', /^\/safety\/trusted-contacts$/, ({ body }) => { if (!S.token) throw err(401, 'authentication_required'); const c = { id: uid(), name: body.name, phone_number: body.phone_number }; S.contacts.push(c); return clone(c); });
  on('DELETE', /^\/safety\/trusted-contacts\/([^/]+)$/, ({ m }) => { S.contacts = S.contacts.filter((c) => c.id !== m[1]); return null; });
  on('GET', /^\/notifications$/, () => clone(S.notifs));
  // ---- companion self-service ----
  const cm = () => { need('companion'); return S.me; };
  on('GET', /^\/companions\/me\/status$/, () => { cm(); return profileStatus(); });
  on('GET', /^\/companions\/me\/application$/, () => { const m = cm(); if (!m.app) throw err(404, 'application_not_found'); return clone(m.app); });
  on('POST', /^\/companions\/me\/application$/, ({ body }) => { const m = cm(); if (!m.app) m.app = { id: uid(), user_id: S.user.id, statement: body.statement || '', status: 'draft', revision: 1, review_note: null }; return clone(m.app); });
  on('PUT', /^\/companions\/me\/application$/, ({ body }) => { const m = cm(); if (!m.app) throw err(404, 'application_not_found'); need422((body.statement || '').length > 4000, 'statement', 'max'); m.app.statement = body.statement || ''; m.app.revision++; return clone(m.app); });
  on('POST', /^\/companions\/me\/application\/(submit|withdraw)$/, ({ m: x }) => { const m = cm(); if (!m.app) throw err(404, 'application_not_found'); m.app.status = x[1] === 'submit' ? 'submitted' : 'withdrawn'; return clone(m.app); });
  on('GET', /^\/companions\/me\/profile$/, () => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); return clone(m.prof); });
  on('POST', /^\/companions\/me\/profile$/, ({ body }) => { const m = cm(); if (!m.app) throw err(404, 'application_not_found'); need422(!(body.display_name || '').trim() || body.display_name.length > 128, 'display_name', 'length'); m.prof = { id: uid(), application_id: m.app.id, display_name: body.display_name, bio: body.bio || '', interests: body.interests || [], languages: body.languages || [], content_status: 'draft', activation_requested: false, review_note: null, revision: 1 }; return clone(m.prof); });
  on('PUT', /^\/companions\/me\/profile$/, ({ body }) => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); need422(!(body.display_name || '').trim() || body.display_name.length > 128, 'display_name', 'length'); Object.assign(m.prof, { display_name: body.display_name, bio: body.bio || '', interests: body.interests || [], languages: body.languages || [] }); m.prof.revision++; m.prof.content_status = 'draft'; syncPublic(); return clone(m.prof); });
  on('POST', /^\/companions\/me\/profile\/submit$/, () => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); m.prof.content_status = 'pending'; return clone(m.prof); });
  on('POST', /^\/companions\/me\/(activate|deactivate)$/, ({ m: x }) => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); m.prof.activation_requested = x[1] === 'activate'; syncPublic(); return profileStatus(); });
  on('GET', /^\/companions\/me\/services$/, () => clone(cm().services));
  on('POST', /^\/companions\/me\/services$/, ({ body }) => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); if (body.price_minor < 0) throw err(422, 'invalid_price'); const s = Object.assign({ id: uid(), profile_id: m.prof.id }, body); m.services.push(s); syncPublic(); return clone(s); });
  on('PUT', /^\/companions\/me\/services\/([^/]+)$/, ({ m: x, body }) => { const m = cm(); const s = m.services.find((v) => v.id === x[1]); if (!s) throw err(404, 'companion_service_not_found'); if (body.price_minor < 0) throw err(422, 'invalid_price'); Object.assign(s, body); syncPublic(); return clone(s); });
  on('DELETE', /^\/companions\/me\/services\/([^/]+)$/, ({ m: x }) => { const m = cm(); m.services = m.services.filter((v) => v.id !== x[1]); syncPublic(); return null; });
  on('GET', /^\/companions\/me\/availability$/, () => clone(cm().avail));
  on('POST', /^\/companions\/me\/availability$/, ({ body }) => { const m = cm(); if (!m.prof) throw err(404, 'profile_not_found'); if (Date.parse(body.ends_at) <= Date.parse(body.starts_at)) throw err(422, 'validation_error', 'Request validation failed', { errors: [{ type: 'value_error', loc: ['body', 'ends_at'], msg: 'ends_at must be after starts_at' }] }); const a = Object.assign({ id: uid(), profile_id: m.prof.id }, body); m.avail.push(a); syncPublic(); return clone(a); });
  on('DELETE', /^\/companions\/me\/availability\/([^/]+)$/, ({ m: x }) => { const m = cm(); m.avail = m.avail.filter((a) => a.id !== x[1]); syncPublic(); return null; });
  on('GET', /^\/companions\/me\/photos$/, () => { cm(); return []; });
  // ---- vendor (gift vendor) ----
  const vn = () => need('vendor');
  on('GET', /^\/gifts\/vendor\/products$/, () => { vn(); return clone(S.products.filter((p) => p.vendor_id === S.user.id)); });
  on('POST', /^\/gifts\/vendor\/products$/, ({ body }) => { vn(); if (body.price_minor < 0) throw err(422, 'invalid_product_update'); const p = Object.assign({ id: uid(), vendor_id: S.user.id, published: false }, body); S.products.push(p); return clone(p); });
  on('PATCH', /^\/vendor\/products\/([^/]+)$/, ({ m, body }) => { vn(); const p = S.products.find((x) => x.id === m[1] && x.vendor_id === S.user.id); if (!p) throw err(404, 'gift_not_found'); if (body.price_minor !== undefined && body.price_minor < 0) throw err(422, 'invalid_product_update'); Object.assign(p, body); return clone(p); });
  on('POST', /^\/vendor\/products\/([^/]+)\/unpublish$/, ({ m }) => { vn(); const p = S.products.find((x) => x.id === m[1] && x.vendor_id === S.user.id); if (!p) throw err(404, 'gift_not_found'); p.published = false; return clone(p); });
  on('GET', /^\/vendor\/summary$/, () => { vn(); const mine = S.products.filter((p) => p.vendor_id === S.user.id); return { products_total: mine.length, products_published: mine.filter((p) => p.published).length }; });
  on('GET', /^\/vendor\/orders$/, () => { vn(); return []; });
  on('GET', /^\/vendor\/earnings$/, () => { vn(); throw err(503, 'vendor_earnings_unavailable'); });

  async function api(method, path, opt) {
    opt = opt || {}; const q = opt.query || {}; cfg.calls.push(method + ' ' + path);
    if (cfg.offline) throw err(0, 'network_offline');
    await new Promise((r) => setTimeout(r, cfg.latency));
    for (const [mm, re, fn] of R) { if (mm !== method) continue; const m = path.match(re); if (m) return clone(await fn({ m, body: opt.body || {}, query: q, headers: opt.headers || {} })); }
    throw err(404, 'http_error', 'Not found');
  }
  // ---- DEMO-only controls (simulate provider / admin / other party; NOT API endpoints) ----
  const demo = {
    cfg, S,
    providerComplete(paymentId, result) { const p = S.payments.find((x) => x.id === paymentId); if (!p || p.status !== 'pending') return null; p.status = result; if (result === 'succeeded') { const b = S.bookings.find((x) => x.id === p.booking_id); if (b.status === 'accepted') { b.status = 'confirmed'; sysmsg(b, 'payment_confirmed', 'Toʻlov tasdiqlandi (DEMO).'); notify(b, 'payment_confirmed'); } } return p; },
    companionAccept(id) { const b = S.bookings.find((x) => x.id === id); if (b && b.status === 'pending') { b.status = 'accepted'; b.companion_contract_accepted_at = iso(now()); sysmsg(b, 'booking_accepted', 'Hamroh bronni qabul qildi. Endi toʻlash mumkin.'); notify(b, 'booking_accepted'); } return b; },
    companionCheckIn(id) { const b = S.bookings.find((x) => x.id === id); if (b && b.status === 'confirmed' && now() >= Date.parse(b.starts_at)) { meet(b).p = true; sysmsg(b, 'checked_in', 'Hamroh yetib keldi.'); } return b; },
    skipToStart(id) { const b = S.bookings.find((x) => x.id === id); if (b) cfg.clock = Math.max(cfg.clock, Date.parse(b.starts_at) - Date.now() + 1000); },
    adminApprove() { const m = S.me; if (m.app) m.app.status = 'approved'; if (m.prof) m.prof.content_status = 'approved'; m.identity = 'verified'; syncPublic(); },
    adminPublish(id) { const p = S.products.find((x) => x.id === id); if (p) p.published = true; },
    incomingRequests() { const p = myProfile(); if (!p || S.bookings.some((b) => b.profile_id === p.id)) return; const s = p.services[0]; if (!s) return; [26, 52].forEach((h, i) => { const st = Date.parse(p.avail[0] ? p.avail[Math.min(i + 1, p.avail.length - 1)].starts_at : iso(now() + 864e5)) + 3 * 36e5; S.bookings.push({ id: uid(), customer_id: uid(), profile_id: p.id, service_id: s.id, service_code: s.service_code, service_description: s.description, starts_at: iso(st), ends_at: iso(st + s.unit_minutes * 6e4), duration_minutes: s.unit_minutes, meeting_place: 'Amir Temur xiyoboni (DEMO)', timezone: 'Asia/Tashkent', price_minor: s.price_minor, currency: s.currency, status: 'pending', created_at: iso(now()), customer_contract_accepted_at: iso(now()), companion_contract_accepted_at: null }); }); },
    reset() { Object.assign(S, { user: null, roles: [], token: null, bookings: [], payments: [], messages: {}, meetings: {}, reviews: [], reports: [], blocks: [], contacts: [], cart: [], testOrders: [], notifs: [], sos: [], me: { app: null, prof: null, status: null, services: [], avail: [] } }); cfg.clock = 0; cfg.offline = false; cfg.pay = 'ok'; cfg.feeBps = 1000; seed(); }
  };
  return { api, demo, card };
});
