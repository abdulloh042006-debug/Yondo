# Google Flow prompt pack — NAMUNA (C1 «Keyinroq» ro‘yxati)

**Bu Stage 1 namunasi.** CEO konseptni tasdiqlamaguncha hech narsa generatsiya qilmang. To‘liq paket Stage 2 da beriladi.
Format: 9:16, 1080×1920, 30 fps, ≈ 32 s. Til: o‘zbekcha (1995 lotin), keyin RU.

## 0. Qanday ishlatiladi (qadam-baqadam)
1. **Avval rasmlar (R01–R07), keyin videolar (s02–s05).** Har bir video o‘z referens rasmlaridan foydalanadi: shu tufayli qahramonlar
   va joylar har kadrda bir xil chiqadi.
2. Flow'da yangi loyiha oching: nomi `yondo-ad5-reja`. Sozlamalarda **Aspect ratio = 9:16** (portret). Agar sizning tarifingizda 9:16
   bo‘lmasa, 16:9 da qiling va menga ayting: markazdan kesamiz (sifat biroz tushadi).
3. Promptni **so‘zma-so‘z** nusxalang (inglizcha qismi). Qavs ichidagi o‘zbekcha izohlar promptga kirmaydi.
4. Har bir natijani shu nom bilan saqlang va **shu chatga** yuklang: masalan `R01_dilnoza.png`, `s04_museum_hall.mp4`.
5. Videolarda Flow ovoz ham yaratishi mumkin: uni o‘chiring yoki e'tibor bermang, ovozni o‘zimiz qo‘yamiz.
6. Kredit: har generatsiyadan oldin Flow ko‘rsatgan narxni ko‘ring. Qoralama uchun tezroq/arzonroq modelni (Fast) tanlang,
   yaxshi chiqqan kadrni keyin sifatli rejimda qaytaring. Men hech narsa sotib olmayman va generatsiya qilmayman.
7. Ilova ekranlari (a01–a04) **Flow'da qilinmaydi**: ular haqiqiy `apps/web` dan yozib olinadi. Motion qismlari (m01–m03) ham men tomonda.

## 1. Kadrlar ro‘yxati (kadrlar)
| # | Vaqt | Davomiylik | Fayl | Kim qiladi | Nima |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0–3.0 | 3.0 s | `m01_list_hook` | motion (men) | Ro‘yxat, 4 ta «KEYINROQ» muhri, oylar aylanadi |
| 2 | 3.0–7.0 | 4.0 s (5–6 s yarating) | `s02_poster_pass.mp4` | **Flow (siz)** | Dilnoza ko‘rgazma afishasi yonida sekinlaydi, o‘tib ketadi |
| 3 | 7.0–10.0 | 3.0 s (4–5 s yarating) | `s03_chess_shelf.mp4` | **Flow (siz)** | Javdondagi shaxmat, qo‘l otni olib, qaytarib qo‘yadi |
| 4 | 10.0–11.5 | 1.5 s | `m02_kim_bilan` | motion | Katta so‘z «Kim bilan?» |
| 5 | 11.5–13.3 | 1.8 s | `a01_list_interest` | ilova yozuvi | Hamrohlar ro‘yxati |
| 6 | 13.3–15.1 | 1.8 s | `a02_profile_interests` | ilova yozuvi | Profil: Qiziqishlar |
| 7 | 15.1–16.9 | 1.8 s | `a03_booking_form` | ilova yozuvi | Bron so‘rovi formasi (narx kadrga kirmaydi) |
| 8 | 16.9–18.5 | 1.6 s | `a04_request_sent` | ilova yozuvi | «Bron so‘rovi yuborildi» |
| 9 | 18.5–23.5 | 5.0 s (6 s yarating) | `s04_museum_hall.mp4` | **Flow (siz)** | Dilnoza va hamroh Kamola ko‘rgazmada |
| 10 | 23.5–27.5 | 4.0 s (6 s yarating) | `s05_park_chess.mp4` | **Flow (siz)** | Javlon va Rustam aka bog‘da shaxmat, qo‘l berib ko‘rishadi |
| 11 | 27.5–29.5 | 2.0 s | `m03_list_ticks` | motion | Ro‘yxatdagi bandlarga belgi (✓) qo‘yiladi |
| 12 | 29.5–32.0 | 2.5 s | `m04_end_card` | motion | Logo, «Yondo — doim yoningda.», «18+ · Tez kunda» |

Subtitrlar (yoqilgan): 0.3 «Bu ro‘yxat hammada bor.» · 3.2 «Yangi ko‘rgazma — keyinroq.» · 7.2 «Shaxmat — keyinroq.» ·
11.5 «Yondoda qiziqishingiz bo‘yicha hamroh toping.» · 13.3 «Profilda — qiziqishlari va xizmatlari.» ·
15.1 «Vaqt va joyni tanlab, so‘rov yuboring.» · 16.9 «Hamroh so‘rovni tasdiqlaydi.» · 18.5 «Ko‘rgazma — bugun.» ·
23.5 «Shaxmat — shanba kuni.» · 27.5 «Rejangiz bor. Hamroh — Yondoda.»

## 2. Qahramonlar va joylar (hammasi to‘qima, hammasi kattalar)
| Ref | Kim / nima | Qaysi kadrlarda |
| --- | --- | --- |
| R01 | Dilnoza — mijoz, ayol, ~28 yosh | s02, s04 |
| R02 | Kamola — hamroh, ayol, ~35 yosh | s04 |
| R03 | Javlon — mijoz, erkak, ~27 yosh | s03 (faqat qo‘l va yeng), s05 |
| R04 | Rustam aka — hamroh, erkak, ~58 yosh | s05 |
| R05 | Ko‘rgazma zali (haqiqiy muzey emas) | s04 |
| R06 | Bog‘dagi tosh shaxmat stoli | s05 |
| R07 | Ko‘cha, bekat yonidagi bo‘sh afisha ramkasi | s02 |

**Nega juftliklar shunday:** ayol + ayol, erkak + katta yoshli erkak. Bu «uchrashuv/sevgi» deb o‘qilishini oldini oladi, «tanishuv
emas» deb aytishga hojat qolmaydi.

## 3. Referens rasm promptlari (avval shular)
Har bir rasm uchun: **Image** rejimi, 9:16, 2–4 variant yarating, eng yaxshisini saqlang.

### R01_dilnoza.png
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian woman, about 28 years old, clearly adult, friendly calm face,
dark hair tied in a low ponytail, no makeup look. Wearing a cream knit sweater, dark straight trousers, a rust-orange scarf,
a plain canvas tote bag with no print. Standing on a city sidewalk, soft overcast daylight, neutral natural colour grade,
35mm lens look, shallow depth of field. Plain background, no text, no logos, no brand names, no jewellery that looks expensive.
```
(Tekshiring: yuz aniq, kattalar yoshida, sharf to‘q sabzi (rust-orange) rangda.)

### R02_kamola.png
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian woman, about 35 years old, clearly adult, warm confident
expression, short dark bob haircut, thin black-framed glasses. Wearing a charcoal blazer over a plain white t-shirt, black
trousers. Bright indoor gallery light, neutral natural colour grade, 50mm lens look. Plain light wall behind her.
No text, no logos, no badges, no name tags.
```

### R03_javlon.png
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian man, about 27 years old, clearly adult, short dark hair,
short neat beard, relaxed friendly face. Wearing a navy overshirt over a plain white t-shirt, dark jeans. Soft afternoon
window light, neutral natural colour grade, 50mm lens look. Plain background. No text, no logos.
```

### R04_rustam_aka.png
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian man, about 58 years old, short grey beard, kind smiling eyes,
grey flat cap, beige shirt with a brown knit vest. Dappled daylight under trees, neutral natural colour grade, 50mm lens look.
No text, no logos.
```

### R05_gallery.png
```
Photorealistic interior, 9:16. A bright modern art gallery hall with white walls and a light stone floor. One very large abstract
painting in deep blue and white geometric patterns inspired by Central Asian ceramics hangs on the main wall. Even soft
museum lighting, no people, neutral natural colour grade, 24mm lens look. No text, no signs, no labels, no logos.
```

### R06_park_chess.png
```
Photorealistic exterior, 9:16. A grey stone table with an inlaid chessboard and two stone stools in a public city park under
large plane trees, wooden chess pieces set up on the board. Dappled midday sunlight, a paved path behind, a few distant blurred
passers-by. Neutral natural colour grade, 35mm lens look. No text, no signs, no logos.
```

### R07_street_poster.png
```
Photorealistic street scene, 9:16. A quiet city sidewalk with low trees and a bus stop. Next to the bus stop, a tall poster frame
showing an abstract artwork in deep blue and white geometric patterns, with no text on it. Overcast soft morning light,
neutral natural colour grade, 35mm lens look. No people. No readable text anywhere, no logos, no shop names.
```

## 4. Video promptlari
Rejim: **Ingredients to Video** (yoki sizning Flow'dagi shu turdagi rejim): ko‘rsatilgan referens rasmlarni qo‘shing, keyin prompt.
Davomiyligi: Flow beradigan uzunlik (odatda 8 s gacha); jadvaldagi kerakli qismni o‘zim kesaman.
Barcha videolar uchun umumiy salbiy qism (prompt oxiriga qo‘shing):
```
Negative: no text, no subtitles, no logos, no brand names, no readable signs, no romance, no hugging, no kissing, no holding
hands, no flirting looks, no candles, no sunset couple shots, no alcohol, no minors or children, no real celebrities,
no distorted hands, no extra fingers, no morphing faces, no fast camera shake. No dialogue, no music.
```

### s02_poster_pass.mp4 — referenslar: R01 + R07
```
9:16 vertical video, 6 seconds. The woman from the reference image walks along the city sidewalk from left to right at a relaxed
pace. As she passes the poster frame with the blue abstract artwork, she slows down, looks at it for one second with a small
interested smile, glances at her phone, then keeps walking out of frame. Camera: slow lateral tracking shot at eye level,
moving with her, 35mm lens, shallow depth of field. Light: soft overcast morning. Mood: ordinary weekday, light and curious,
not sad. Neutral natural colour grade.
```
(Negative qismini qo‘shing.)
**Qabul qilishdan oldin tekshiring:** yuzi R01 ga o‘xshaydimi; sharf sabzi rangdami; afishada **hech qanday yozuv yo‘q**;
qadam tabiiy (sirpanmaydi); oyoqlar/qo‘llar buzilmagan; kamida 4 s toza bo‘lak bor; kayfiyat g‘amgin emas.

### s03_chess_shelf.mp4 — referens: R03 (yeng va qo‘l uchun)
```
9:16 vertical video, 5 seconds. Close-up of a wooden chess set resting on a bookshelf, a thin layer of dust on the board.
A man's hand in a navy overshirt sleeve enters the frame, picks up the white knight, holds it for a moment, then puts it back
in place and the hand leaves. Camera: static, macro-style close-up, 50mm lens, very shallow depth of field. Light: warm
afternoon side light from a window, dust visible in the light. Mood: quiet, a plan waiting. Neutral natural colour grade.
```
**Tekshiring:** 5 ta barmoq, qo‘l tabiiy; ot figurasi shaklini o‘zgartirmaydi; yeng to‘q ko‘k; javonda kitob nomlari o‘qilmaydi.

### s04_museum_hall.mp4 — referenslar: R01 + R02 + R05
```
9:16 vertical video, 6 seconds. In the bright gallery hall from the reference, the woman with the rust-orange scarf (first
reference) and the woman with glasses and a charcoal blazer (second reference) stand side by side about one metre apart in front
of the large blue abstract painting. The woman with glasses points to a detail of the painting and explains it with an open hand
gesture; the woman with the scarf laughs and nods, both looking mostly at the painting. Camera: slow push-in from a medium-wide
shot to a medium shot, smooth gimbal, 35mm lens. Light: even bright museum light. Mood: curious, friendly, relaxed.
Neutral natural colour grade.
```
**Tekshiring:** ikkalasining yuzi o‘z referensiga mos; orada ~1 metr masofa saqlangan, tegish yo‘q; rasm ustida yozuv/imzo yo‘q;
ko‘zlar asosan rasmga qaragan (bir-biriga uzoq tikilish yo‘q); qo‘l ishoralari tabiiy.

### s05_park_chess.mp4 — referenslar: R03 + R04 + R06
```
9:16 vertical video, 6 seconds. At the stone chess table in the park from the reference, the young man in the navy overshirt
(first reference) and the older man with the grey beard and flat cap (second reference) sit opposite each other. The older man
makes a move, the young man laughs and shakes his head, then they reach across the board and shake hands warmly. Camera: slow
30-degree arc around the table at seated eye level, 35mm lens. Light: dappled midday sun under plane trees. Mood: friendly
competition, respect. Neutral natural colour grade.
```
**Tekshiring:** qo‘l berib ko‘rishish aniq va tabiiy (barmoqlar qo‘shilib ketmagan); shaxmat figuralari taxtadan «uchib»
ketmaydi; ikkala yuz referensga mos; fonda bolalar ko‘rinmaydi.

## 5. Har bir natijani qabul qilish ro‘yxati (umumiy)
- [ ] 9:16, kamida 1080 px kenglik (yoki 16:9 bo‘lsa, menga aytildi)
- [ ] hamma odam aniq katta yoshli; voyaga yetmaganlar yo‘q
- [ ] hech qanday yozuv, logo, brend, o‘qiladigan belgi yo‘q
- [ ] romantika yo‘q: quchoqlash, qo‘l ushlash, uzoq tikilish, sham, quyosh botishidagi juftlik yo‘q
- [ ] qo‘l-oyoqlar, yuzlar buzilmagan; tasvir miltillamaydi
- [ ] yuz va kiyim referensga mos (R01–R04)
- [ ] kayfiyat do‘stona, g‘amgin emas
- [ ] fayl nomi jadvaldagidek; shu chatga yuklandi
Agar biror band bajarilmasa: o‘sha kadrni qayta yarating (kredit sarfini ko‘rib), keyingi kadrga o‘tmang.
