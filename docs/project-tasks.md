# Yondo — ishlar ro'yxati (bajarilgan va qolgan)

Belgilar:

- ✅ — bajarilgan va test qilingan
- 🟡 — kod tayyor va test rejimida ishlaydi, lekin real provayder/kalit yoki biznes qarori kerak
- ⬜ — bajarilmagan (dizayner, huquqshunos yoki egasining ishi / keyingi bosqich)

Oxirgi yangilanish: 2026-11-04.

## Umumiy holat

| Bosqich (ROADMAP) | Holat | Natija / izoh |
| --- | --- | --- |
| Phase 0 — Product Foundation | ✅ | `README.md`, `TZ.md`, `ROADMAP.md` (avvaldan) |
| Phase 1–3 — UX, Wireframe, Figma UI | ⬜ | Dizayner ishi. Ilova va panel o'z soddalashtirilgan dizayni bilan ishlaydi |
| Phase 4 — Backend Foundation | ✅ | Avvaldan + S3 adapter, realtime broker, bildirishnoma yadrosi |
| Phase 5 — Authentication | ✅ / 🟡 | OTP, sessiya, rollar; profil to'ldirilganda akkaunt faollashadi. **Real SMS provayder kerak** |
| Phase 6 — Companion System | ✅ | Avvaldan; + taxminiy hudud (location) |
| Phase 7 — Discovery | ✅ | Qidiruv, 9 filtr, saralash, home bo'limlari, public profil, bo'sh vaqtlar, favorites |
| Phase 8 — Booking Engine | ✅ | So'rov, narx/quote, shartnoma, accept/decline, bekor qilish siyosati, muddati o'tishi, double booking himoyasi (DB constraint + lock) |
| Phase 9 — Payment | ✅ / 🟡 | Checkout, sandbox provayder, imzolangan webhook, idempotentlik, refund, payout. **Real provayder (Payme/Click/Uzum) kerak** |
| Phase 10 — Chat | ✅ | Booking chat, matn/rasm/joy/tizim xabarlari, o'qilmaganlar, WebSocket |
| Phase 11 — Meeting | ✅ | I'm here, Start/End, no-show (avtomatik nizo), avtomatik yakunlash |
| Phase 12 — Rating & Review | ✅ | Ikki tomonlama, TZ mezonlari, quick tags, o'rtacha reyting, badge'lar |
| Phase 13 — Trust & Safety | ✅ | ID+selfie verification, report, block, dispute, trusted contact, ulashish havolasi, SOS, Safety Center |
| Phase 14 — Admin Panel | ✅ | Admin API + web panel: foydalanuvchilar, moderatsiya, navbatlar, bronlar, moliya, nizolar, SOS, analytics, audit |
| Phase 15 — Gifts Marketplace | ✅ | Vendorlar, kategoriyalar, mahsulotlar, savat, checkout, buyurtmalar |
| Phase 16 — Booking + Gift | ✅ | Bitta checkout: bron + gul/sovg'a, uchrashuv joyiga yetkazish |
| Phase 17 — Vendor Panel | ✅ | Web panel: do'kon, mahsulot/rasm/stock, buyurtma statuslari, daromad, reyting |
| Phase 18 — Notifications | ✅ / 🟡 | In-app, eslatmalar, push outbox, worker. **Firebase (FCM) kaliti kerak** |
| Phase 19 — Testing | ✅ | 210+ avtomatik test (SQLite + PostgreSQL), concurrency, duplicate payment, timezone; brauzerda uchdan-uchga sinov |
| Phase 20 — Closed Beta | ⬜ | Real provayderlar ulangach, 20–50 mijoz, 10–20 companion bilan |
| Phase 21 — MVP Launch (Toshkent) | ⬜ | Beta natijalaridan keyin |
| Phase 22 — Metrics | ✅ (asos) | TZ §47 metrikalari admin dashboard'da |
| Phase 23–25 — V2/V3/Expansion | ⬜ | Roadmap bo'yicha keyinroq (AI matching, surprise builder, va h.k.) |

## Ushbu topshiriqda bajarilgan ishlar

1. **Platforma asoslari** — umumiy yordamchilar, pul (integer minor units), S3 SigV4 adapter
   (AWS test vektori bilan tekshirilgan), dev-only lokal storage, realtime broker (Redis/memory),
   bildirishnomalar va qurilma tokenlari, CORS.
2. **Backend Phase 7–18** — yuqoridagi jadvaldagi barcha modullar, 8 ta yangi migratsiya
   (upgrade/downgrade/check tekshirilgan), 171 ta API operatsiya (`docs/api-overview.md`).
3. **Admin + vendor web panel** (`apps/admin`, React/TypeScript) — brauzerda sinab ko'rilgan.
4. **Mobil ilova** (`apps/mobile`, Expo React Native) — mijoz va companion oqimlari; web
   eksportda to'liq oqim (login → bron → qabul → to'lov → chat) avtomatik sinovdan o'tgan.
5. **Infra** — API/panel Dockerfile, to'liq dev stack (`docker compose --profile app`),
   CI (lint, SQLite + PostgreSQL testlar, migratsiya aylanmasi, panel va ilova tekshiruvi).
6. **Hujjatlar** — `development.md`, `deployment.md`, `business-policies.md`,
   `api-overview.md`, ADR 0002.
7. **Demo ma'lumotlar** — `python -m yondo_api.cli seed-demo` (admin, mijoz, 3 companion,
   vendor va mahsulotlar).

## Qolgan ishlar va sizdan kerak bo'ladiganlar

### Sizdan (egasidan) kerak — kalitlar va akkauntlar

| # | Nima | Nega |
| --- | --- | --- |
| 1 | SMS provayder (masalan Eskiz.uz yoki Play Mobile) akkaunt va API kaliti | Productionda OTP yuborish |
| 2 | To'lov provayderi tanlovi (Payme / Click / Uzum) va merchant kalitlari | Real to'lov va refund |
| 3 | Payout usuli (bank o'tkazmasi qo'lda yoki API) | Companion/vendorlarga pul o'tkazish |
| 4 | Firebase loyiha: service account JSON + `google-services.json`, Apple developer akkaunt | Push bildirishnomalar, iOS build |
| 5 | Hosting (server/bulut), domen, S3 bucket | Deploy |
| 6 | Logo, ranglar, ilova ikonkasi (yoki Figma dizayn) | Store va brend |

### Sizdan kerak — biznes qarorlari (`docs/business-policies.md`)

Platforma komissiyasi (hozir 10%), bekor qilish qoidalari (24 soat / 50%), minimal yosh (18),
companion va vendor komissiyasi (0%), payout ushlab turish (24 soat), trust badge chegaralari,
review quick tag'lari, valyuta va narx chegaralari.

### Huquqiy hujjatlar (TZ §20)

Terms of Service, Privacy Policy, Community Guidelines, Booking/Cancellation/Refund/No-show
Policy, Payment Terms, Safety Rules — matnlar huquqshunos tomonidan tayyorlanishi kerak.

### Texnik keyingi qadamlar (credentials bilan)

- Tanlangan SMS va to'lov provayderi adapterlarini yozish (interfeyslar tayyor).
- So'rovlar uchun rate limiting (chat, report, SOS), chatda telefon raqam aniqlash (TZ §15).
- Companion intro video (TZ §8), Google/Apple login (TZ §42), xarita SDK.
- Rasm saqlash muddati va tozalash (Phase 6 dan qolgan), monitoring/alerting.
- Figma dizayn tayyor bo'lgach UI'ni moslashtirish; store'larga chiqarish (EAS build).
