/* YONDO prototype logic. Pure functions, no DOM. Contract: docs/openapi-v1.json (branch codex/notification-integration). */
(function (root, factory) { if (typeof module === 'object' && module.exports) module.exports = factory(); else root.YL = factory(); })(typeof self !== 'undefined' ? self : this, function () {
  // ---- money: integer tiyin ("minor units"). 100 tiyin = 1 UZS. No floating-point arithmetic anywhere. ----
  const EXP = { UZS: 2 };
  const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);
  function toBig(x) { if (typeof x === 'bigint') return x; if (typeof x === 'number') return Number.isSafeInteger(x) ? BigInt(x) : null; if (typeof x === 'string' && /^-?\d+$/.test(x)) return BigInt(x); return null; }
  // Format an integer minor amount. Returns null for null/undefined/invalid (unsafe numbers, floats, NaN, junk) so callers show "not determined".
  function money(minor, cur) {
    cur = cur || 'UZS';
    if (minor === null || minor === undefined) return null;
    const v = toBig(minor); if (v === null) return null;
    const e = EXP[cur] === undefined ? 2 : EXP[cur], d = 10n ** BigInt(e), neg = v < 0n, a = neg ? -v : v, whole = a / d, frac = a % d;
    let s = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    if (frac) s += ',' + String(frac).padStart(e, '0');
    return (neg ? '−' : '') + s + (cur === 'UZS' ? ' soʻm' : ' ' + cur);
  }
  // Parse a user-typed soʻm amount into integer tiyin WITHOUT floats and WITHOUT silent rounding (max 2 decimals).
  function toMinor(text) {
    let t = String(text == null ? '' : text).trim().replace(/[\s\u00a0]/g, '');
    if (!t) return { ok: false, code: 'empty' };
    if (t[0] === '-') return { ok: false, code: 'negative' };
    t = t.replace(',', '.');
    if (!/^\d+(\.\d+)?$/.test(t)) return { ok: false, code: 'invalid' };
    const [w, f = ''] = t.split('.');
    if (f.length > 2) return { ok: false, code: 'too_many_decimals' };
    const big = BigInt(w) * 100n + BigInt((f + '00').slice(0, 2));
    if (big > MAX_SAFE) return { ok: false, code: 'too_large' };
    return { ok: true, minor: Number(big) };
  }
  const AMOUNT_ERR = { empty: 'Narxni kiriting.', negative: 'Narx 0 dan kam boʻlmasin.', invalid: 'Narxni raqamlarda kiriting.', too_many_decimals: 'Tiyin 2 xonadan oshmasin.', too_large: 'Narx juda katta.' };
  // minor → text for an input box ("55000" or "55000.5"); exact, no floats.
  function somInput(minor) { const v = toBig(minor); if (v === null || v < 0n) return ''; const w = v / 100n, f = v % 100n; return String(w) + (f ? '.' + String(f).padStart(2, '0').replace(/0$/, '') : ''); }
  // Exact integer multiply (price × whole units). null when the result is not a safe integer (overflow).
  function mulUnits(price, units) { const a = toBig(price), b = toBig(units); if (a === null || b === null || a < 0n || b < 0n) return null; const r = a * b; return r <= MAX_SAFE ? Number(r) : null; }
  // ---- booking estimate: backend requires duration % unit_minutes === 0; price = price_minor * units ----
  function estimate(svc, duration) {
    if (!svc || !(svc.unit_minutes > 0)) return { ok: false, code: 'invalid_booking_duration' };
    if (!Number.isInteger(duration) || duration <= 0 || duration % svc.unit_minutes) return { ok: false, code: 'invalid_booking_duration' };
    const units = duration / svc.unit_minutes, p = mulUnits(svc.price_minor, units);
    if (p === null) return { ok: false, code: 'booking_price_overflow' };
    return { ok: true, units, price_minor: p };
  }
  // ---- time intervals: ISO-8601 instants WITH an explicit offset/Z (UTC convention); until must be after from ----
  const INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;
  const NAIVE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/;
  function parseInstant(v) { if (typeof v !== 'string' || !INSTANT.test(v)) return NaN; return Date.parse(v); }
  // { ok:true, start, end } or { ok:false, code } with code: missing | timezone_required | invalid | end_not_after_start
  function validateInterval(from, until) {
    if (!from || !until) return { ok: false, code: 'missing' };
    if (NAIVE.test(from) || NAIVE.test(until)) return { ok: false, code: 'timezone_required' };
    const a = parseInstant(from), b = parseInstant(until);
    if (isNaN(a) || isNaN(b)) return { ok: false, code: 'invalid' };
    if (b <= a) return { ok: false, code: 'end_not_after_start' };
    return { ok: true, start: a, end: b };
  }
  // DECISION: eligibility is FULL CONTAINMENT: available_from <= requested_from AND available_until >= requested_until.
  const contains = (av, rq) => av.start <= rq.start && av.end >= rq.end;
  // Booking conflict (kept in force, independent of availability): half-open overlap; touching boundaries do not conflict.
  const overlaps = (a, b) => a.start < b.end && a.end > b.start;
  const durations = (svc) => [1, 2, 3].map((n) => n * svc.unit_minutes);
  // ---- booking status machine (documented actions only) ----
  const STATUSES = ['pending', 'accepted', 'confirmed', 'active', 'completed', 'cancelled', 'no-show', 'disputed'];
  const LABEL = { pending: 'Kutilmoqda', accepted: 'Qabul qilindi', confirmed: 'Tasdiqlandi', active: 'Uchrashuv faol', completed: 'Yakunlandi', cancelled: 'Bekor qilindi', 'no-show': 'Kelmadi', disputed: 'Nizo' };
  // role: 'customer' | 'companion'. Returns UI actions allowed by documented endpoints; backend still decides.
  function actions(role, b, meeting) {
    const s = b.status, a = [];
    if (role === 'companion') {
      if (s === 'pending') a.push('accept', 'decline');
      if (['accepted', 'confirmed'].includes(s)) a.push('cancel');
      if (s === 'pending') { /* decline covers cancel */ }
    } else {
      if (s === 'accepted') a.push('pay');
      if (['pending', 'accepted', 'confirmed'].includes(s)) a.push('cancel');
    }
    if (s === 'confirmed') { const mine = role === 'companion' ? meeting && meeting.companion_arrived : meeting && meeting.customer_arrived; if (!mine) a.push('checkin'); else if (meeting && meeting.companion_arrived && meeting.customer_arrived) a.push('start'); }
    if (s === 'active') a.push('end', role === 'customer' ? 'sos' : 'sos');
    if (s === 'completed' && role === 'customer') a.push('review');
    if (['confirmed', 'active', 'completed', 'accepted', 'pending'].includes(s)) a.push('chat');
    return a;
  }
  // ---- structured errors: logic keyed ONLY on `code` (never on message text) ----
  const E = {
    booking_time_unavailable: ['Bu vaqt band. Boshqa vaqtni tanlang.', 'form'],
    availability_not_found: ['Hamroh tanlangan vaqtda ishlamaydi. Boshqa vaqtni tanlang.', 'form'],
    booking_start_in_past: ['Tanlangan vaqt oʻtib ketgan.', 'form'],
    invalid_booking_duration: ['Davomiylik xizmat birligiga karrali boʻlishi kerak.', 'form'],
    invalid_booking_interval: ['Vaqt oraligʻi notoʻgʻri.', 'form'],
    booking_price_overflow: ['Narx juda katta.', 'form'],
    self_booking_forbidden: ['Oʻzingizga bron qila olmaysiz.', 'blocked'],
    booking_blocked: ['Bu foydalanuvchi bilan bron qilib boʻlmaydi.', 'blocked'],
    companion_not_found: ['Profil topilmadi yoki faol emas.', 'notfound'],
    companion_service_not_found: ['Xizmat topilmadi. Sahifani yangilang.', 'stale'],
    booking_not_found: ['Bron topilmadi.', 'notfound'],
    invalid_booking_transition: ['Bron holati oʻzgargan. Yangilang.', 'stale'],
    booking_not_payable: ['Toʻlov faqat hamroh bronni qabul qilgach mumkin.', 'stale'],
    idempotency_key_conflict: ['Bu soʻrov allaqachon yuborilgan. Yangilang.', 'stale'],
    payment_provider_unavailable: ['Toʻlov tizimi vaqtincha mavjud emas. Keyinroq urinib koʻring. Bron saqlangan.', 'unavailable'],
    payment_configuration_unavailable: ['Toʻlov sozlamalari hali tayyor emas. Bron saqlangan.', 'unavailable'],
    combined_checkout_unavailable: ['Bron va sovgʻa uchun yagona toʻlov hali mavjud emas.', 'unavailable'],
    gift_checkout_unavailable: ['Sovgʻa toʻlovi hali mavjud emas.', 'unavailable'],
    gift_orders_unavailable: ['Sovgʻa buyurtmalari hali mavjud emas.', 'unavailable'],
    vendor_earnings_unavailable: ['Daromad maʼlumoti hali jonli emas.', 'unavailable'],
    otp_delivery_unavailable: ['SMS yuborish hozircha mavjud emas.', 'unavailable'],
    customer_role_required: ['Bu amal uchun “Mijoz” roli kerak.', 'role'],
    companion_role_required: ['Bu amal uchun “Hamroh” roli kerak.', 'role'],
    account_role_required: ['Bu amal uchun mos rol kerak.', 'role'],
    role_required: ['Bu amal uchun mos rol kerak.', 'role'],
    account_unavailable: ['Hisobingiz cheklangan. Qoʻllab-quvvatlashga murojaat qiling.', 'blocked'],
    authentication_required: ['Qayta kiring.', 'auth'], invalid_access_token: ['Seans tugadi. Qayta kiring.', 'auth'],
    invalid_phone_number: ['Telefon raqam notoʻgʻri.', 'form'], invalid_otp: ['Kod notoʻgʻri.', 'form'], otp_expired: ['Kod muddati tugadi. Yangisini soʻrang.', 'form'],
    otp_rate_limited: ['Juda koʻp urinish. Keyinroq urinib koʻring.', 'wait'], otp_resend_cooldown: ['Kodni qayta yuborish uchun biroz kuting.', 'wait'], otp_temporarily_blocked: ['Vaqtincha bloklandi. Keyinroq urinib koʻring.', 'wait'],
    meeting_too_early: ['Uchrashuv vaqti hali kelmadi.', 'info'], meeting_check_in_required: ['Avval ikkala tomon yetib kelganini belgilashi kerak.', 'info'],
    meeting_not_ready: ['Uchrashuvni boshlash uchun ikkala tomon yetib kelishi kerak.', 'info'], meeting_not_active: ['Uchrashuv faol emas.', 'stale'], meeting_already_ended: ['Uchrashuv allaqachon yakunlangan.', 'stale'], meeting_state_conflict: ['Uchrashuv holati oʻzgargan. Yangilang.', 'stale'],
    review_already_exists: ['Siz allaqachon sharh qoldirgansiz.', 'info'], review_not_ready: ['Sharh uchrashuv yakunlangach mumkin.', 'info'], review_not_allowed: ['Sharh qoldirish mumkin emas.', 'blocked'], invalid_review_tag: ['Teg notoʻgʻri.', 'form'],
    chat_closed: ['Chat yopilgan.', 'info'], chat_blocked: ['Chat bloklangan.', 'blocked'],
    sos_requires_active_booking: ['SOS faqat faol uchrashuvda ishlaydi.', 'info'], sos_confirmation_required: ['SOS ni tasdiqlang.', 'form'],
    invalid_report: ['Shikoyat maʼlumoti notoʻgʻri.', 'form'], invalid_block: ['Bloklash mumkin emas.', 'form'], reported_user_not_found: ['Foydalanuvchi topilmadi. Identifikator foydalanuvchi (user id) boʻlishi kerak.', 'notfound'], user_not_found: ['Foydalanuvchi topilmadi.', 'notfound'], invalid_report_target: ['Shikoyat manzili bronning ikkinchi ishtirokchisi boʻlishi kerak.', 'form'],
    gift_unavailable: ['Sovgʻa hozir mavjud emas yoki tugagan.', 'stale'], cart_conflict: ['Savat oʻzgargan. Yangilang.', 'stale'], cart_empty: ['Savat boʻsh.', 'form'],
    gift_delivery_note_required: ['Yetkazib berish uchun izoh yozing.', 'form'], click_test_disabled: ['Test rejimi oʻchirilgan.', 'unavailable'], gift_not_found: ['Sovgʻa topilmadi.', 'notfound'], gift_currency_mismatch: ['Valyuta mos kelmaydi.', 'blocked'],
    stale_companion_revision: ['Profil boshqa joyda oʻzgargan. Yangilang.', 'stale'], invalid_price: ['Narx notoʻgʻri.', 'form'], validation_error: ['Maʼlumotlarni tekshiring.', 'form'],
    invalid_discovery_filter: ['Filtr notoʻgʻri.', 'form'], network_offline: ['Internet aloqasi yoʻq.', 'offline']
  };
  const BYSTATUS = { 401: 'auth', 403: 'role', 404: 'notfound', 409: 'stale', 422: 'form', 429: 'wait', 503: 'unavailable' };
  function classify(err) {
    const code = err && err.code, st = err && err.status, hit = E[code];
    if (hit) return { code, text: hit[0], kind: hit[1], retry: ['unavailable', 'offline', 'wait'].includes(hit[1]) || st >= 500, rid: err.request_id || null };
    const kind = BYSTATUS[st] || (st >= 500 ? 'unavailable' : 'error');
    const text = st === 503
      ? 'Server vaqtincha xizmat koʻrsata olmayapti (503). Iltimos, birozdan soʻng qayta urinib koʻring.'
      : 'Xatolik yuz berdi. Qayta urinib koʻring.';
    return { code: code || 'unknown', text, kind, retry: kind === 'unavailable' || kind === 'error', rid: (err && err.request_id) || null };
  }
  const isUnavailable503 = (err) => !!err && err.status === 503; // distinct from a declined/failed payment
  // ---- validators (limits from OpenAPI schemas) ----
  const bad = (f, m) => ({ field: f, text: m });
  function validateProfile(p) {
    const e = [], n = (p.display_name || '').trim();
    if (!n) e.push(bad('display_name', 'Ismni kiriting.')); else if (n.length > 128) e.push(bad('display_name', 'Ism 128 belgidan oshmasligi kerak.'));
    if ((p.bio || '').length > 8000) e.push(bad('bio', 'Tavsif 8000 belgidan oshmasligi kerak.'));
    const list = (k, nm) => { const a = p[k] || [], low = a.map((x) => x.trim().toLowerCase()); if (a.some((x) => !x.trim() || x.length > 64)) e.push(bad(k, nm + ': har biri 1–64 belgi.')); else if (new Set(low).size !== low.length) e.push(bad(k, nm + ': takrorlanmasin.')); };
    list('interests', 'Qiziqishlar'); list('languages', 'Tillar'); return e;
  }
  function validateService(s) {
    const e = [];
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(s.service_code || '')) e.push(bad('service_code', 'Xizmat turini tanlang.'));
    if (!Number.isSafeInteger(s.price_minor) || s.price_minor < 0) e.push(bad('price_minor', 'Narx 0 dan kam boʻlmasligi kerak.'));
    if (!Number.isInteger(s.unit_minutes) || s.unit_minutes <= 0) e.push(bad('unit_minutes', 'Birlik musbat daqiqa boʻlishi kerak.'));
    if (!/^[A-Z]{3}$/.test(s.currency || '')) e.push(bad('currency', 'Valyuta kodi 3 ta bosh harf.'));
    if ((s.description || '').length > 4000) e.push(bad('description', 'Tavsif 4000 belgidan oshmasligi kerak.')); return e;
  }
  function validateAvailability(a) {
    const e = [], s = Date.parse(a.starts_at), t = Date.parse(a.ends_at);
    if (!a.starts_at || isNaN(s)) e.push(bad('starts_at', 'Boshlanish vaqtini kiriting.'));
    if (!a.ends_at || isNaN(t)) e.push(bad('ends_at', 'Tugash vaqtini kiriting.'));
    if (!isNaN(s) && !isNaN(t) && t <= s) e.push(bad('ends_at', 'Tugash vaqti boshlanishdan keyin boʻlishi kerak.'));
    if (!a.timezone || a.timezone.length > 64) e.push(bad('timezone', 'Vaqt zonasi (IANA) kerak.')); return e;
  }
  function validateBooking(b) {
    const e = [];
    if (!b.service_id) e.push(bad('service_id', 'Xizmatni tanlang.'));
    if (!b.starts_at) e.push(bad('starts_at', 'Sana va vaqtni tanlang.')); else if (Date.parse(b.starts_at) <= (b.now || Date.now())) e.push(bad('starts_at', 'Vaqt kelajakda boʻlishi kerak.'));
    if (!b.duration_minutes) e.push(bad('duration_minutes', 'Davomiylikni tanlang.'));
    if (!b.meeting_place || b.meeting_place.trim().length < 3) e.push(bad('meeting_place', 'Uchrashuv joyini yozing (kamida 3 belgi).'));
    if (!b.timezone) e.push(bad('timezone', 'Vaqt zonasi kerak.')); return e;
  }
  const REPORT_CATS = { harassment: 'Bezovta qilish', inappropriate_request: 'Nomaqbul soʻrov', fake_profile: 'Soxta profil', fraud: 'Firibgarlik', unsafe_behavior: 'Xavfli xatti-harakat', no_show: 'Kelmadi', payment_issue: 'Toʻlov muammosi', other: 'Boshqa' };
  function validateReport(r) { const e = []; if (!REPORT_CATS[r.category]) e.push(bad('category', 'Sababni tanlang.')); const d = (r.description || '').trim(); if (!d) e.push(bad('description', 'Qisqacha izoh yozing.')); else if (d.length > 4000) e.push(bad('description', 'Izoh 4000 belgidan oshmasligi kerak.')); return e; }
  function validateContact(c) { const e = []; if (!(c.name || '').trim() || c.name.length > 128) e.push(bad('name', 'Ism 1–128 belgi.')); if (!/^\+?[0-9]{7,15}$/.test(c.phone_number || '')) e.push(bad('phone_number', 'Raqam 7–15 raqamdan iborat boʻlsin.')); return e; }
  function validateProduct(p) { const e = []; const nm = (p.name || '').trim(); if (nm.length < 2 || nm.length > 160) e.push(bad('name', 'Nom 2–160 belgi boʻlsin.')); if (!Number.isSafeInteger(p.price_minor) || p.price_minor < 0) e.push(bad('price_minor', 'Narx 0 dan kam boʻlmasin.')); if (!Number.isInteger(p.stock) || p.stock < 0) e.push(bad('stock', 'Zaxira 0 dan kam boʻlmasin.')); if (!(p.description || '').trim()) e.push(bad('description', 'Qisqacha tavsif yozing.')); if (!/^[A-Z]{3}$/.test(p.currency || '')) e.push(bad('currency', 'Valyuta kodi.')); return e; }
  function validatePhone(raw) { const d = String(raw || '').replace(/\D/g, ''); return d.length === 9 ? { ok: true, e164: '+998' + d } : { ok: false }; }
  const idemKey = () => 'ui-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  const GIFT_LABEL = { flowers: 'Gullar', chocolate: 'Shokolad', gift_box: 'Sovgʻa qutisi', toys: 'Oʻyinchoqlar', birthday: 'Tugʻilgan kun', romantic: 'Maxsus kunlar', custom: 'Maxsus buyurtma' };
  const SERVICE_LABEL = { coffee: 'Kofe', walking: 'Sayr', cinema: 'Kino', shopping: 'Shopping', event: 'Tadbir', city_friend: 'Shahar doʻsti', conversation: 'Suhbat', study: 'Oʻqish / Coworking' };
  const BLOCKER = { application_not_approved: 'Ariza hali tasdiqlanmagan', content_not_approved: 'Profil kontenti tasdiqlanmagan', account_not_active: 'Hisob faol emas', companion_role_required: 'Hamroh roli kerak', identity_not_verified: 'Shaxs tasdiqlanmagan' };
  return { money, toMinor, somInput, mulUnits, AMOUNT_ERR, estimate, validateInterval, parseInstant, contains, overlaps, durations, STATUSES, LABEL, actions, E, classify, isUnavailable503, validateProfile, validateService, validateAvailability, validateBooking, validateReport, validateContact, validateProduct, validatePhone, REPORT_CATS, idemKey, GIFT_LABEL, SERVICE_LABEL, BLOCKER };
});
