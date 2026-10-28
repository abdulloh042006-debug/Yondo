# Yondo — qaror xulosasi (2026-10-28)

Egasi uchun, qisqa. Har bir da'vo yonida manba belgisi bor: **[R]** repo fayli, **[W]** bugungi veb-qidiruv, **[M]** mening umumiy bilimim (bugun tekshirilmagan). **[Y]** mening mahalliy tadqiqot yozuvlarim (`research_notes/`, git'da emas; 2026-10-28; qidiruv xulosalari, rasmiy matn o‘qilmagan) — bulut sessiyasidan keyin shu yerga qo‘shildi.

> **Halol eslatma.** 7 ta tadqiqot yozuvi (`research_notes/`) git'da emas, faqat sizning kompyuteringizda; bu sessiyada ular yo‘q edi. Shu sabab quyidagi da'volar yozuvlarga emas, repo va ochiq manbalarga bog‘langan. Yozuvlaringizdagi "Gaps" ro‘yxati bilan solishtirib chiqing — farq bo‘lsa, yozuv emas, shu xulosa tekshiriladi.

## 1. Server (hosting) — tavsiya

| Variant | Hukm | Sabab |
|---|---|---|
| **Hozirgi Render (bepul) + Neon** | Demo uchun **qoladi** | Ishlayapti, push'da o‘zi yangilanadi; 15 daqiqa bo‘sh tursa ~1 daq. "uyg‘onadi"; haqiqiy shaxsiy ma'lumot kiritilmaydi [R `infra/deploy/README.md`] |
| **O‘zbekistondagi VPS (Toshkent) + Docker** | **Yopiq beta (20–50 mijoz) uchun tavsiya** | Foydalanuvchilar va ma'lumot bir joyda, qonun savoli eng sodda. Toshkentda VPS beruvchilar bor (Serverspace, Pro-Data — ularning o‘z sahifalari; narx/SLA tekshirilmagan) [W] |
| **Oracle Always Free + Docker** | Faqat **staging/zaxira** sifatida | (a) 7 kun ichida CPU/tarmoq/xotira <20% bo‘lsa, Oracle bo‘sh nusxani **olib qo‘yishi mumkin** [W, Oracle hujjati]; (b) bepul ARM kvotasi 4 OCPU/24 GB dan 2/12 ga kamaygani haqida xabar bor — **tasdiqlanmagan** [W]; (c) ro‘yxatdan o‘tishda xalqaro karta kerak, Uzcard/Humo qabul qilinishi **tasdiqlanmagan** [W]; (d) O‘zbekistonda Oracle regioni yo‘q (tekshiring) [M] |
| **Universitet laboratoriya PC'lari** | **Tavsiya etilmaydi** (hatto beta uchun) | 24/7 kafolat yo‘q, elektr/tarmoq/statik IP/zaxira nusxa noaniq, universitet siyosati xavfi, to‘lov va chat ma'lumotlari uchun mos emas [M] — faqat o‘quv-test uchun |

**[Y] Server tanlovi — sizning qaroringiz (ikki yozuv farq qiladi).** Qonun tomoni Toshkent VPS’ni xavfsiz deydi (telefon raqami masalasi hal bo‘lmaguncha). Narx tomoni esa Yevropa VPS’ni birinchi qo‘yadi. Taqqoslash:

| | Toshkent VPS | Yevropa VPS |
|---|---|---|
| Narx | ~125–320 ming so‘m/oy (aHOST dan 125 ming, UzCloud/Uztelecom ~256–284 ming) | ~6–12 EUR/oy (Hetzner hozir "mavjud emas", DigitalOcean Frankfurt 12–24 USD, Contabo ~5,5 EUR) |
| To‘lov | so‘mda | xalqaro karta kerak (Uzcard/Humo qabul qilinishi tasdiqlanmagan) |
| Qonun | eng sodda | 49 davlat ro‘yxati va telefon raqami masalasi aniqlanishi kerak |
| Kechikish | eng kam | kattaroq (o‘lchanmagan) |

**Tavsiya:** beta uchun Toshkent VPS; Yevropa VPS — huquqshunos telefon raqami masalasini "chet elda mumkin" deb tasdiqlasa. Narxlar qidiruv xulosalaridan, tasdiqlanmagan.

**Docker** sizning noutbukingizda **kerak emas**: image'ni serverda yoki GitHub Actions'da quramiz. Image bugungacha **hech qachon qurilmagan** [R WORKLOG S28] — keyingi kichik qadam: CI'da build tekshiruvi.

**Ma'lumotni O‘zbekistonda saqlash (huquqiy)** — huquqshunos tasdiqlashi kerak:
- 2019 yilgi "Shaxsiy ma'lumotlar to‘g‘risida" qonun (ZRU‑547) fuqarolar ma'lumotini mamlakat ichidagi serverlarda saqlashni talab qilgan [W].
- 2026‑yil 26‑martda qonunga o‘zgartirish imzolangan: ko‘p ma'lumotni chet elda saqlash mumkin (3 shartdan biri bilan), lekin **biometrik/genetik** ma'lumot va telekom abonentlari ma'lumoti hamon faqat mahalliy [W — to‘liq matn o‘qilmagan, jarima miqdori topilmadi].
- **[Y]** Chet elda saqlash uchun shartlardan biri: davlat 2026‑yil 29‑iyuldagi ro‘yxatda bo‘lishi (49 davlat va hudud, AQSH, Germaniya, Yaponiya, Singapur kabilar), yoki tasdiqlangan standart shartnoma bandlari, yoki xalqaro standart. Ro‘yxat va qaror matni **o‘qilmagan** — huquqshunos aniqlaydi.
- **[Y] Ochiq savol:** oddiy foydalanuvchining **telefon raqami** "telekom xizmati foydalanuvchisi ma’lumoti" hisoblanadimi? Yondo telefon raqamini saqlaydi, shuning uchun bu javob server joyini hal qiladi. Javobsiz: telefon raqamlari va zaxira nusxalar O‘zbekistonda tursin.
- Yondo uchun xulosa: telefon, chat, buyurtma — shaxsiy ma'lumot; kelajakdagi shaxs tasdiqlash (MyID/yuz) biometrik bo‘lishi mumkin → uni **provayder tomonida qoldiring**, biz saqlamaymiz. Shu sabab ham birinchi tanlov — Toshkent VPS.

## 2. Bitta ilovami, ikkitami?
**Tavsiya: bitta veb-ilova, ikki rejim (Mijoz | Hamroh) + alohida admin konsol.** `apps/web` shunday: mijoz sahifalari, `/studio` (hamroh), `/admin` [R `App.tsx`]. Sabab: yopiq betada jamoa kichik, ikkita ilova = ikki barobar test va yangilash. Yandex Go uslubidagi ikkita alohida ilova katta hajmda mantiqli [M]; backend rolga asoslangan, shuning uchun keyin `apps/mobile`'da ajratish mumkin. **Hozir ajratmaymiz.**

## 3. Ekranlar: beta uchun kerakmi, ortiqchami

| Ekran | Beta uchun | Eslatma |
|---|---|---|
| Kirish (OTP), Qidiruv, Hamroh profili | **Shart** | asosiy oqim |
| Bronlar + bron tafsiloti (to‘lov, uchrashuv, chat, sharh) | **Shart** | to‘lov faqat `accepted` dan keyin |
| Studio (hamroh: vaqt, so‘rovlar) | **Shart** | hamrohsiz bron yo‘q |
| Admin (tasdiqlash, shikoyat, to‘lov) | **Shart** | server-authorized |
| Yordam + SOS, Shartlar/Maxfiylik, Akkauntni o‘chirish | **Shart** | o‘z siyosatingiz va xavfsizlik [R CLAUDE.md §7 S24–S25] |
| Bildirishnomalar | Shart | |
| Sevimlilar | Ixtiyoriy | arzon, qoldiramiz, kengaytirmaymiz |
| Sozlamalar (mavzu, alifbo, til) | Bor, **kengaytirmang** | |
| **Sovg‘alar / vendor** | Veb'da **yo‘q** | ⚠ ROADMAP Phase 20 "bir nechta vendor" deydi — bu **qarama-qarshilik**: vendorsiz beta o‘tkazish ROADMAP'ni o‘zgartirishni talab qiladi. **Qaror sizniki.** |

## 4. Sizdan kerak bo‘lgan 11 ta qaror (yopiq savollar)
1. **Domen nomi** va qaysi registrator (TezCheck kassasi shuni so‘raydi). 2. **SMS provayder** (Eskiz / PlayMobile / boshqa). 3. **Shaxs tasdig‘i**: provayder (MyID…) yoki beta uchun admin qo‘lda tasdiqlaydi? *(Tavsiya: beta'da qo‘lda.)* 4. **Platforma komissiyasi**. 5. **Bekor qilish foizlari**. 6. **Qaytarish (refund) qoidasi**. 7. **Hamrohga to‘lov (payout) usuli va muddati**. 8. **Operator nomi** (Shartlar/Maxfiylikda hozir "ko‘rsatilmagan"). 9. **SOS signalini kim va qachon o‘qiydi** (jonli odam kerak; bo‘lmasa SOS va'dasi yolg‘on bo‘lib qoladi). 10. **Beta'da vendor/sovg‘a bormi?** (3‑bo‘limdagi qarama-qarshilik).
11. **[Y] Yuridik shakl:** yakka tartibdagi tadbirkor (IP) yoki MChJ va bank hisobi. Payme Business faqat ro‘yxatdan o‘tgan yuridik shaxsga ishlaydi; shu shaxs Shartlar va Maxfiylikdagi **operator** (8‑band) bo‘ladi. TezCheck yakka shaxsni qabul qiladimi — hujjatda yozilmagan, TezCheck’dan so‘rang (`docs/payments-tezcheck.md`).
(4–7 ni men o‘ylab topmayman: sozlanmaguncha API 503 "sozlanmagan" qaytaradi [R CLAUDE.md §4].)

## 5. Ochilish animatsiyasi, onboarding, video qo‘llanma (tavsiya)
- **Animatsiya 2,5–3 s**: ink→paper ustida Y logotip chiziladi, carrot tugun bir marta "uriladi", shior paydo bo‘ladi. Ilova yuklanishini **kutdirmaydi**; teginish bilan o‘tkazib yuboriladi; faqat o‘rnatishdagi birinchi ochilishda. `prefers-reduced-motion` bo‘lsa — statik 0,6 s. Ovoz ixtiyoriy va **o‘chiq**; brauzerlar foydalanuvchi bosmaguncha ovozni bloklaydi [M].
- **Onboarding**: 3 karta (Top → Bron qil → Xavfsiz uchrash), ikki rol uchun alohida, o‘tkazib yuborish mumkin, Yordam'dan qayta ochiladi.
- **Video qo‘llanma**: har rol uchun 45–60 s, `marketing/ad-video` va `motion` bilan [R]; faqat ink/paper/carrot, romantik tasvir yo‘q, **"DEMO" yozuvi yo‘q**, UZ+RU (ovozni siz berasiz).
- Boshlash sharti: siz shu bo‘limni tasdiqlaganingizdan **keyin**.

## 6. "Demo" so‘zini qachon olib tashlash
**Qoida: hozirgi ochiq sayt "demo" bo‘lib qoladi.** U yerda OTP ekranda ko‘rinadi — URL'ni bilgan har kim istalgan raqam (admin ham) bilan kira oladi [R README "Risks"]; "demo" belgisini olib tashlash foydalanuvchini chalg‘itadi. Production alohida quriladi va uning build'ida demo vositalari **bo‘lmasligi** kerak (ular `infra/deploy/demo/`da, `apps/api`da emas [R S31]). Ilova matnida "DEMO" hozir faqat `/demo-pay` sahifasida [R grep]. Yopiq beta davrida production'da **"Beta"** belgisi turadi; demo sayt staging/sandbox bo‘lib qoladi. "Demo" so‘zi faqat haqiqiy SMS + to‘lov + shaxs tasdig‘i ulangach, production'dan to‘liq yo‘qoladi.

**[Y] Muddat.** Production’da "Yopiq beta" belgisi taxminan **6–8 hafta** turadi (odatda 4–8) va oldindan belgilangan chiqish mezonlariga yetgach, Toshkentda ommaviy ishga tushirishda olinadi. Tartib: avval muhitlarni ajratish va production himoyasi, keyin SMS, to‘lov, shaxs tasdig‘i, saqlash; so‘ng huquqiy sahifalar va SOS tartibi; so‘ng 10–15 hamroh, keyin mijozlar.

## 7. Yopiq beta'dan oldingi darvoza (blokerlar birinchi)
**Bloker:** domen · yuridik shaxs va bank hisobi · haqiqiy SMS (sender‑ID ni oldindan ro‘yxatdan o‘tkazing: Ucell ro‘yxatdan o‘tmaganini 2026‑yil 3‑avgustdan bloklaydi; Eskiz ~85 so‘m/SMS, yuridik shaxs shartnomasi bilan) · TezCheck kassasi + komissiya/bekor/refund/payout qoidalari · operator nomi · production PostgreSQL + zaxira nusxa + kunlik `jobs` taymeri [R `infra/jobs/`] · rasm saqlash (S3/MinIO adapteri — hozir **NOT IMPLEMENTED**) · shaxs tasdig‘i usuli · SOS'ni o‘qiydigan odam · production'da demo vositalari yo‘qligi va admin raqami maxfiyligi.
**Bloker emas:** Redis‑chat (beta uchun 8 s polling yetadi), ona tilida matn tekshiruvi, haqiqiy qurilma/ekran o‘quvchi testi, Docker build tekshiruvi, `ruff format`, `apps/mobile`.

## Tasdiqlanmagan (tekshirish kerak)
Oracle kvota o‘zgarishi · Uzcard/Humo bilan Oracle ro‘yxati · Toshkent VPS narxlari/SLA · 2026‑yil qonun o‘zgarishining aniq matni va jarimalar (huquqshunos) · TezCheck komissiyasi, refund API (TezCheck qo‘llab-quvvatlashidan so‘rang, `docs/payments-tezcheck.md`).

**Manbalar [W]:** [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm) · [Kun.uz: 2026 o‘zgartirish](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems) · [Legal500: Personal data compliance in Uzbekistan](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/) · [Serverspace Toshkent](https://serverspace.io/services/vps-server/vps-in-uzbekistnan/) · [Pro-Data](https://pro-data.tech/en/dedicated-server). (Oracle va Kun.uz sahifalari bu muhitdan ochilmadi — ma'lumot qidiruv xulosasidan olingan.)
