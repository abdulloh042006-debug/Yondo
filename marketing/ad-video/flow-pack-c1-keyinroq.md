# Google Flow paketi — «Keyinroq» ro‘yxati (to‘liq, 1-versiya)

Reklama 5 (C1). Format 9:16, 1080×1920, 30 fps, 32 s. Ssenariy: `scripts/05-keyinroq.md`.
**Siz faqat 8 ta rasm va 4 ta video yaratasiz.** Ilova ekranlari, animatsiya, ovoz va montaj men tomonda.
Men hech narsa generatsiya qilmayman va hech narsa sotib olmayman. Kreditlarni siz boshqarasiz.

## 1-qadam. Tayyorgarlik
1. Google Flow'ni oching (labs.google saytidagi Flow), yangi loyiha yarating: `yondo-ad5-keyinroq`.
2. Sozlamalar: **Aspect ratio = 9:16**. Agar 9:16 bo‘lmasa, 16:9 da qiling va menga yozing (markazdan kesamiz, sifat tushadi).
3. Har generatsiyadan oldin Flow ko‘rsatgan kredit narxini ko‘ring. Avval tezkor (Fast) rejimda sinang; yoqqan variantni sifatli
   rejimda qaytaring.
4. Promptlarni **so‘zma-so‘z** nusxalang (inglizcha). Qavs ichidagi o‘zbekcha izohlar promptga kirmaydi.
5. Flow videoga ovoz qo‘shsa, e'tibor bermang: ovozni men qo‘yaman.

## 2-qadam. Nima va qaysi tartibda
| № | Fayl nomi | Turi | Qayerda ishlatiladi | Kerakli uzunlik |
| --- | --- | --- | --- | --- |
| 1 | `R01_dilnoza.png` | rasm | s02, s04 | — |
| 2 | `R02_kamola.png` | rasm | s04 | — |
| 3 | `R03_javlon.png` | rasm | s05 | — |
| 4 | `R04_rustam_aka.png` | rasm | s05 | — |
| 5 | `R05_gallery.png` | rasm | s04 | — |
| 6 | `R06_oldtown_lane.png` | rasm | s05 | — |
| 7 | `R07_street_poster.png` | rasm | s02 | — |
| 8 | `R08_cork_board.png` | rasm | s03 | — |
| 9 | `s02_poster_pass.mp4` | video | 3.0–7.0 s | 6 s yarating (4 s ishlatiladi) |
| 10 | `s03_map_board.mp4` | video | 7.0–10.0 s | 5 s (3 s) |
| 11 | `s04_exhibition_hall.mp4` | video | 18.5–23.5 s | 6–8 s (5 s) |
| 12 | `s05_oldtown_walk.mp4` | video | 23.5–27.5 s | 6–8 s (4 s) |

**Nega juftliklar shunday:** ayol + ayol, yosh erkak + katta yoshli erkak. Bu «uchrashuv/sevgi» deb o‘qilishini oldini oladi;
«tanishuv emas» deb aytishga hojat qolmaydi. Hamma qahramonlar **to‘qima va katta yoshli**. Haqiqiy odamga o‘xshatmang.

## 3-qadam. Referens rasmlar (avval shular)
Rejim: rasm yaratish (Image), 9:16, har biriga 2–4 variant. Eng yaxshisini nom bilan saqlang.

### 1. R01_dilnoza.png — mijoz, ayol, ~28 yosh
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian woman, about 28 years old, clearly adult, friendly calm face,
dark hair tied in a low ponytail, natural no-makeup look. Wearing a cream knit sweater, dark straight trousers, a rust-orange
scarf, a plain canvas tote bag with no print. Standing on a city sidewalk, soft overcast daylight, neutral natural colour grade,
35mm lens look, shallow depth of field. No text, no logos, no brand names, no visible jewellery.
```
Tekshiring: yuz aniq va katta yoshli; sharf to‘q sabzi (rust-orange); sumkada yozuv yo‘q.

### 2. R02_kamola.png — hamroh, ayol, ~35 yosh
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian woman, about 35 years old, clearly adult, warm confident
expression, short dark bob haircut, thin black-framed glasses. Wearing a charcoal blazer over a plain white t-shirt, black
trousers. Bright indoor gallery light, neutral natural colour grade, 50mm lens look, plain light wall behind her.
No text, no logos, no badges, no name tags, no lanyard.
```
Tekshiring: ko‘zoynak bor; R01 dan aniq farq qiladi (soch, yosh, kiyim).

### 3. R03_javlon.png — mijoz, erkak, ~27 yosh
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian man, about 27 years old, clearly adult, short dark hair,
short neat beard, relaxed friendly face. Wearing a navy overshirt over a plain white t-shirt, dark jeans, white sneakers.
Soft daylight, neutral natural colour grade, 50mm lens look, plain background. No text, no logos.
```

### 4. R04_rustam_aka.png — hamroh, erkak, ~58 yosh
```
Photorealistic portrait, 9:16, waist-up. A fictional Central Asian man, about 58 years old, short grey beard, kind smiling eyes,
grey flat cap, beige shirt with a brown knit vest. Dappled daylight, neutral natural colour grade, 50mm lens look.
No text, no logos.
```

### 5. R05_gallery.png — ko‘rgazma zali (haqiqiy muzey emas)
```
Photorealistic interior, 9:16. A bright modern art gallery hall with white walls and a light stone floor. One very large abstract
painting in deep blue and white geometric patterns inspired by Central Asian ceramics hangs on the main wall; two smaller
ceramic plates on plinths. Even soft museum lighting, no people, neutral natural colour grade, 24mm lens look.
No text, no signs, no labels, no logos.
```

### 6. R06_oldtown_lane.png — eski shahar ko‘chasi (aniq bino emas)
```
Photorealistic exterior, 9:16. A quiet pedestrian lane in an old Central Asian town quarter: warm yellow brick and clay walls,
a tall carved wooden door with geometric patterns, a small tree, a few potted plants, a teahouse bench in the distance.
Soft late-morning sunlight, neutral natural colour grade, 35mm lens look. No people. No text, no signs, no shop names,
no famous landmark, no domes of a recognisable monument.
```

### 7. R07_street_poster.png — bekat yonidagi afisha
```
Photorealistic street scene, 9:16. A quiet city sidewalk with young trees and a bus stop. Next to the bus stop a tall
poster frame shows an abstract artwork in deep blue and white geometric patterns, with no text on it. Overcast soft morning
light, neutral natural colour grade, 35mm lens look. No people. No readable text anywhere, no logos, no shop names.
```

### 8. R08_cork_board.png — devordagi xarita
```
Photorealistic close-up, 9:16. A cork board on a light wall at home. Pinned on it: a paper city map with no readable names,
one old-town area circled with a dark marker, a few blank paper notes and two pushpins. Warm afternoon side light from a
window, neutral natural colour grade, 50mm lens look, shallow depth of field. No readable text, no logos, no photos of people.
```

## 4-qadam. Videolar
Rejim: **Ingredients to Video** (sizdagi nomi boshqacha bo‘lishi mumkin: «referens rasmlardan video»). Ko‘rsatilgan rasmlarni
qo‘shing, keyin promptni qo‘ying. Har bir promptning oxiriga o‘sha kadrning **Negative** qismini qo‘shing.

### 9. s02_poster_pass.mp4 — ingredientlar: R01 + R07
```
9:16 vertical video, 6 seconds. The woman from the reference image walks along the city sidewalk from left to right at a relaxed
pace. As she passes the poster frame with the blue abstract artwork she slows down, looks at it for one second with a small
interested smile, glances at her phone, then keeps walking out of frame. Camera: slow lateral tracking shot at eye level,
moving with her, 35mm lens, shallow depth of field. Light: soft overcast morning. Mood: an ordinary weekday, light and curious,
not sad. Neutral natural colour grade.
Negative: no text on the poster, no subtitles, no logos, no brand names, no readable signs, no other people in focus, no minors,
no sad or crying expression, no distorted hands or feet, no sliding feet, no morphing face, no camera shake, no dialogue, no music.
```
Qabul qilish: yuz R01 ga mos; sharf sabzi rangda; afishada **yozuv yo‘q**; qadamlar tabiiy (sirpanmaydi); kayfiyat g‘amgin emas;
kamida 4 s toza bo‘lak.

### 10. s03_map_board.mp4 — ingredient: R08
```
9:16 vertical video, 5 seconds. Close-up of the cork board from the reference. A hand enters from the right, a finger touches the
circled old-town area on the paper map for a moment, then the hand slowly leaves the frame. Camera: static, slight slow push-in,
50mm lens, shallow depth of field. Light: warm afternoon side light, soft dust in the light. Mood: quiet, a plan waiting.
Neutral natural colour grade.
Negative: no readable text on the map or notes, no logos, no photos of people, no extra fingers, no distorted hand, no pins
flying, no flicker, no dialogue, no music.
```
Qabul qilish: qo‘lda 5 barmoq; xaritada o‘qiladigan nom yo‘q; doira o‘z joyida qoladi.

### 11. s04_exhibition_hall.mp4 — ingredientlar: R01 + R02 + R05
```
9:16 vertical video, 8 seconds. In the bright gallery hall from the reference, the woman with the rust-orange scarf (first
reference) and the woman with glasses and a charcoal blazer (second reference) stand side by side about one metre apart in
front of the large blue abstract painting. The woman with glasses points to a detail of the painting and explains with an open
hand gesture; the woman with the scarf laughs and nods; both look mostly at the painting. Camera: slow push-in from a
medium-wide shot to a medium shot, smooth gimbal, 35mm lens. Light: even bright museum light. Mood: curious, friendly, relaxed.
Neutral natural colour grade.
Negative: no text, no signs or labels on the wall, no logos, no touching, no hugging, no holding hands, no long eye contact,
no romantic mood, no other visitors in focus, no minors, no distorted hands, no morphing faces, no dialogue, no music.
```
Qabul qilish: ikkala yuz o‘z referensiga mos; orada ~1 m; tegish yo‘q; ko‘zlar asosan rasmga qaragan; devorda yozuv yo‘q.

### 12. s05_oldtown_walk.mp4 — ingredientlar: R03 + R04 + R06
```
9:16 vertical video, 8 seconds. In the old-town lane from the reference, the young man in the navy overshirt (first reference)
and the older man with the grey beard and flat cap (second reference) walk side by side towards the camera at a relaxed pace.
The older man stops by the carved wooden door and points at its pattern, explaining; the young man looks, smiles and nods.
At the end they turn to each other and shake hands warmly. Camera: slow walking backwards in front of them (gimbal), then holds,
35mm lens. Light: soft late-morning sun. Mood: friendly, respectful, curious about the city.
Neutral natural colour grade.
Negative: no text, no signs, no shop names, no logos, no famous landmark, no crowds, no minors or children, no hugging,
no distorted hands, no fused fingers in the handshake, no morphing faces, no sliding feet, no dialogue, no music.
```
Qabul qilish: qo‘l berib ko‘rishish aniq (barmoqlar qo‘shilib ketmagan); eshik naqshi o‘zgarmaydi; bolalar ko‘rinmaydi;
ikkala yuz referensga mos.

## 5-qadam. Yuklash
Har bir tayyor faylni **jadvaldagi nom bilan** shu chatga yuklang (CEO orqali menga keladi). Bitta faylda bir nechta variant
bo‘lsa: `s04_exhibition_hall_v2.mp4` kabi nomlang. Agar kadr chiqmasa, nima chiqmaganini bir jumlada yozing, promptni men tuzataman.

## 6-qadam. Har bir natija uchun umumiy tekshiruv
- [ ] 9:16, kengligi kamida 1080 px (yoki 16:9 ekani menga aytildi)
- [ ] hamma odam aniq katta yoshli; bola yo‘q
- [ ] yozuv, logo, brend, o‘qiladigan belgi yo‘q
- [ ] romantika yo‘q: quchoqlash, qo‘l ushlash, uzoq tikilish, sham, quyosh botishidagi juftlik yo‘q
- [ ] qo‘l-oyoq va yuzlar buzilmagan; tasvir miltillamaydi
- [ ] yuz va kiyim referensga mos
- [ ] kayfiyat do‘stona, g‘amgin emas
- [ ] fayl nomi jadvaldagidek

## Kreditni tejash
- Rasmlar arzon: avval hamma 8 rasmni qiling, menga yuboring, men tasdiqlayman, keyin videoga o‘ting.
- Har video uchun avval tezkor rejimda 1–2 urinish; yaxshisini sifatli rejimda bir marta.
- Bitta kadr 3 urinishda chiqmasa, to‘xtang va menga yozing: kadrni soddalashtiraman.
