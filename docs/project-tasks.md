# Yondo — ishlar ro'yxati (bajarilgan va qolgan)

Bu hujjat loyihaning `ROADMAP.md` bo'yicha holatini ko'rsatadi. Belgilar:

- ✅ — bajarilgan va test qilingan
- 🟡 — kod tayyor, lekin real provayder/kalit yoki biznes qarori kerak (test rejimida ishlaydi)
- ⬜ — hali bajarilmagan

Oxirgi yangilanish: 2026-11-04.

## Boshlang'ich holat (topshirilganda)

| Bosqich | Holat | Izoh |
| --- | --- | --- |
| Phase 0 — Product Foundation | ✅ | `README.md`, `TZ.md`, `ROADMAP.md` |
| Phase 1–3 — UX, Wireframe, UI Design | ⬜ | Figma dizayn yo'q (dizayner ishi) |
| Phase 4 — Backend Foundation | ✅ | FastAPI, PostgreSQL, Redis, Alembic, rollar |
| Phase 5 — Authentication | ✅ | Telefon + OTP, sessiya/token, rollar, logout |
| Phase 6 — Companion System | ✅ | Ariza, profil, xizmatlar, narx, rasmlar, bo'sh vaqt, tasdiqlash |
| Phase 7–18 | ⬜ | Boshlanmagan |
| Admin panel (web), Mobile ilova | ⬜ | Faqat bo'sh papkalar |

## Ish rejasi (ushbu topshiriqda)

1. Platforma asoslari: umumiy yordamchilar, akkaunt faollashuvi, S3 storage adapteri,
   realtime broker, bildirishnomalar yadrosi.
2. Phase 7 — Discovery: qidiruv, filtrlar, home bo'limlari, public profil, favorites.
3. Phase 8 — Booking: bron, shartnoma, accept/decline, bekor qilish, double booking himoyasi.
4. Phase 9 — Payment: checkout, provayder abstraksiyasi, sandbox provayder, webhook,
   idempotentlik, refund, payout.
5. Phase 10 — Chat: booking chat, WebSocket, tizim xabarlari, o'qilmaganlar.
6. Phase 11 — Meeting: I'm here, Start/End Meeting, no-show.
7. Phase 12 — Rating & Review: ikki tomonlama baho, mezonlar, quick tags, o'rtacha reyting.
8. Phase 13 — Trust & Safety: ID/selfie verification, report, block, dispute, trusted contact,
   SOS, safety center, moderatsiya.
9. Phase 14 — Admin API: foydalanuvchilar, bronlar, to'lovlar, payoutlar, reportlar,
   disputelar, analytics.
10. Phase 15–17 — Gifts marketplace, Booking + Gift bitta checkout, Vendor panel API.
11. Phase 18 — Notifications: in-app, push (FCM), eslatmalar, fon worker.
12. Phase 19 — Testlar: double booking, duplicate payment, timezone, concurrency.
13. Admin + Vendor web panel (`apps/admin`).
14. Mobile ilova (`apps/mobile`).
15. Infra: Dockerfile, compose, CI (PostgreSQL bilan), deploy hujjatlari.

Har bir bosqich tugagach, bu jadval yangilanadi.
