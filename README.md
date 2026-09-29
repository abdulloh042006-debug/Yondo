# Companion Marketplace

O‘zbekiston bozori uchun ikki tomonlama **companion booking + gifts marketplace** platformasi.

Loyiha foydalanuvchiga ijtimoiy companion topish, vaqt bo‘yicha bron qilish, xavfsiz to‘lov qilish va uchrashuvga gul yoki sovg‘a qo‘shish imkonini beradi.

> Bu dating yoki escort platforma emas. Asosiy konsept — **ijtimoiy companion va experience booking**.

## Asosiy imkoniyatlar

- Companion qidirish va filtrlash
- Ikki tomonlama customer/companion tizimi
- ID va selfie verification
- Booking va calendar
- Payment va payout
- Booking bilan bog‘langan chat
- Check-in / Start Meeting / End Meeting
- Ikki tomonlama rating va review
- Report, block, dispute
- Safety Center, SOS, Trusted Contact
- Flowers & Gifts marketplace
- Vendor panel
- Admin panel

## Foydalanuvchi rollari

- **Customer** — companion yoki sovg‘a buyurtma qiladi
- **Companion** — xizmat va vaqtini taklif qiladi
- **Vendor** — gul, sovg‘a va boshqa mahsulotlarni sotadi
- **Admin** — platformani boshqaradi

## Asosiy user flow

```text
Signup
  ↓
Home / Search
  ↓
Companion Profile
  ↓
Booking
  ↓
Payment
  ↓
Chat
  ↓
Meeting
  ↓
Review
  ↓
Rebook
```

## MVP

Birinchi versiyada:

- Signup + OTP
- Customer profile
- Companion profile
- Verification
- Search va filters
- Booking
- Payment
- Chat
- Rating / Review
- Report / Block
- Basic Safety Center
- Flowers & Gifts marketplace
- Admin panel

MVPda hozircha bo‘lmaydi:

- AI matching
- Advanced Trust Score
- Loyalty va gamification
- Full courier network
- Restaurant integration
- Subscription
- Complex recommendation engine

## Companion xizmatlari

- Coffee Companion
- Walking Companion
- Cinema Companion
- Shopping Companion
- Event Companion
- City Friend
- Conversation Companion
- Study/Coworking Companion

## Safety

Platformada quyidagilar rejalashtirilgan:

- ID verification
- Selfie verification
- Booking contract
- Check-in
- Trusted Contact
- SOS
- Report / Block
- Dispute Center
- Admin moderation

## Marketplace

Companion bookingga quyidagilar qo‘shilishi mumkin:

- Flowers
- Chocolate
- Gift Box
- Toys
- Birthday Gifts
- Romantic Gifts
- Custom Gifts

Maqsad: **Booking + Gift + Delivery → One Checkout**.

## Tavsiya etilgan texnologiyalar

### Mobile
- Flutter yoki React Native

### Backend
- FastAPI yoki Node.js

### Database
- PostgreSQL

### Cache
- Redis

### Storage
- S3-compatible storage

### Realtime
- WebSocket

### Notifications
- Firebase Cloud Messaging

### Admin
- React / Next.js

## Repository hujjatlari

- [`TZ.md`](./TZ.md) — texnik topshiriq
- [`ROADMAP.md`](./ROADMAP.md) — ishlab chiqish bosqichlari

## Roadmap qisqacha

```text
Product Foundation
→ UX Architecture
→ Wireframe
→ UI Design
→ Backend
→ Authentication
→ Companion System
→ Search
→ Booking
→ Payment
→ Chat
→ Meeting
→ Rating
→ Safety
→ Admin
→ Gifts Marketplace
→ Testing
→ Closed Beta
→ MVP Launch
```

## Birinchi launch

Boshlang‘ich bozor: **Toshkent**.

Keyingi kengayish:

Toshkent → Samarqand → Andijon → Farg‘ona → Buxoro → boshqa shaharlar.

## Product yadrosi

**Discover → Trust → Book → Meet → Review → Rebook**

## Status

`Planning / Pre-MVP`

## Development status

Phase 4 backend foundation is located in [`apps/api`](./apps/api). Local PostgreSQL, Redis,
and S3-compatible storage are defined in [`compose.yaml`](./compose.yaml). See
[`docs/development.md`](./docs/development.md) for setup and verification commands.
