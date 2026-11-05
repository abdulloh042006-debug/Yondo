# Egadan kerakli narsalar (2026-11-05 kechqurun holati)

Qisqa ro'yxat. Har bandda nima kerakligi va nima uchunligi yozilgan. Kod tomoni tayyor; bu yerdagilarni faqat siz qila olasiz.

## 1. PR'larni ko'rib chiqish va birlashtirish (sizning qaroringiz)

Tartib: **#10 → #11 → #12 → #13 → #14**. Har biri CI'da yashil va mustaqil verifier tomonidan tekshirilgan. Har birlashtirishdan keyin keyingi PR'dagi konfliktlarni (`WORKLOG.md`, `main.py`, `jobs.py`) men merge commit bilan hal qilaman.

| PR | Nima |
|---|---|
| #10 | S3 rasm saqlash |
| #11 | ID va selfi tasdiqlash (admin qo'lda) |
| #12 | Gifts/vendor: moderatsiya ro'yxati, mahsulotni o'chirish, audit |
| #13 | Mobil ilova (Expo) |
| #14 | Qo'lda tasdiqlanadigan karta to'lovi |

## 2. Qo'lda to'lovni yoqish (server sozlamasi; Render → Environment)

Karta raqamlarini **faqat o'zingiz**, server sozlamasiga kiriting. Repo public, ular hech qachon faylga yozilmaydi.

```
YONDO_PAYMENT_PROVIDER=manual
YONDO_PUBLIC_WEB_URL=https://<web manzilingiz>
YONDO_MANUAL_PAYMENT_CARDS=[{"label":"Uzcard","number":"...","holder":"<Ism F.>"},{"label":"Humo","number":"...","holder":"<Ism F.>"},{"label":"Visa (Uzum)","number":"...","holder":"<Ism F.>"}]
YONDO_PLATFORM_FEE_BPS=<qaror: 0 = beta'da komissiya yo'q>
```

Har kuni: **Admin → To'lovlar** bo'limini oching. Bankingizda aynan shu summa izohda shu kod (`YND-....-....`) bilan tushgan bo'lsa, **"Pul keldi"** ni bosing. Kod yoki summa mos kelmasa, bosmang.

Keyin TezCheck'ka o'tish uchun TezCheck kalitlarini qo'shasiz va `YONDO_PAYMENT_PROVIDER=tezcheck` qilasiz.

## 3. Qarorlar (javobingiz kerak)

1. **Komissiya (platform fee) beta'da:** 0% yoki necha foiz? Bu qiymat belgilanmaguncha to'lov ishlamaydi (503 qaytadi).
2. **Mobil ilova:** bitta ilova rollar bilan (hozir shunday) yoki ikkita alohida ilova?
3. **Muvaffaqiyatsiz to'lov:** hozir har bir bronga bitta to'lov yozuvi. To'lov "failed" bo'lsa, o'sha bronni qayta to'lab bo'lmaydi. Qayta to'lashga ruxsat beraylikmi? Bu backend o'zgarishi.
4. **Vendor:**
   - mahsulot e'lon qilishdan oldin vendorning o'zi admin tasdig'idan o'tsinmi?
   - vendor uchun do'kon profili kerakmi?
   - beta'da mahsulot rasmsiz bo'lishi mumkinmi?
5. **ID rasmlari:** admin qaror chiqargan zahoti o'chirilsinmi (hozir shunday, 0 kun)? Kodda bu "taklif" deb belgilangan.
6. **Qaytarish (refund) va hamrohga to'lash:**
   - Bekor qilingan bron uchun pul kelsa, ilova uni "qaytarish kerak" deb belgilaydi, lekin pulni qaytarishni siz qilasiz.
   - Hamrohlarga pulni qanday va qachon o'tkazasiz?
   
   Ilova bu qoidalarni o'zi to'qib chiqarmaydi.

## 4. Hisob va kalitlar (tayyor bo'lganda)

- **Domen** (TezCheck uchun kerak).
- **S3 bucket va kalitlar**, masalan DigitalOcean Spaces: `YONDO_STORAGE_*` sozlamalari, `infra/deploy/README.md`. Busiz rasm va ID yuklash ishlamaydi (503).
- **Telegram Gateway tokeni** (`YONDO_TELEGRAM_GATEWAY_TOKEN`): haqiqiy foydalanuvchilarga kirish kodi yuborish uchun.
- **TezCheck kalitlari:** foydalanuvchilar ko'payganda kerak bo'ladi.
- **Server va baza** (DigitalOcean).

## 5. Faqat siz qila oladigan tekshiruvlar

- **Bank va hisobchi:** shaxsiy kartaga biznes to'lovlarini qabul qilish vaqtinchalik yechim. Bank limiti yoki bloklanish xavfi, soliq masalasi bor. Bank va hisobchi bilan aniqlashtiring.
- **Telefonda sinash:** Expo Go'ni o'rnatib, mobil ilovani o'z telefoningizda sinab ko'ring. Buning uchun API telefon ochadigan manzilda turishi kerak.
- **Matnlar:** o'zbekcha matnlarni bir ko'rib chiqing. Agent yozgan, ona tili egasi tekshirmagan.
- **Eski tokenlar:** chatda yuborilgan eski GitHub tokenlarini bekor qiling (WORKLOG "Next steps" 1-band).
