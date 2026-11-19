# Ad 6 — «Yondo nima? (10 soniyada)» (C3, companion explainer): script

Stage 2, 2026-11-19. Approved by the CEO as the companion piece to ad 5. **9:16, 1080×1920, 30 fps, 12.0 s** (13.0 s if the final VO
needs it), captions ON, UZ first then RU. **Motion + real app only: no AI footage, so it costs nothing to make.** It can be rendered
as soon as the app captures exist (no Flow uploads needed).

## Idea
People cannot place a new category and guess "dating?". One clear, fast explainer: **activity + companion + public place**. One line
says what Yondo is not; everything else shows what it is.

## Storyboard
| # | t | Picture and motion | On-screen text (UZ) | VO (DRAFT timing) | Sound |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.00–1.40 | Paper ground. «YONDO» 220 px (Manrope 800) slams in (scale 1.3 → 1, back-ease), then splits into three vertical cards that slide apart (1.0–1.4). | «Yondo nima?» (caption) | — (title read on screen; VO starts at card 1) | bass hit 0.0; whoosh 1.0 |
| 2 | 1.40–4.20 | Card 1 «Faoliyat» fills the frame. Four line-art icons pop in on the beat (cup, walking shoes, film strip, ticket), each with its category name **as the app writes it**: Kofe, Sayr, Kino, Tadbir. | «Faoliyat: kofe, sayr, kino, tadbir.» | C3-V1 at 1.45 (2.66 s) | pop ×4 at 1.9 / 2.4 / 2.9 / 3.4 |
| 3 | 4.20–8.00 | Card 2 «Hamroh». The real companion card from the app's card feed (illustrated portrait, name, city, category chips Kofe · Tadbir · Sayr), cropped above the price line; a carrot frame lifts the chip row. | «Hamroh: profilida xizmatlari ko‘rinadi.» | C3-V2 at 4.25 | swipe 4.2; click ×2 |
| 4 | 8.00–10.30 | Card 3 «Uchrashuv». The real booking form's meeting-place field with the app's own hint «Jamoat joyi: kafe, park, savdo markazi. Uy manzilini yozmang.» lifts out; a line-art square with a bench and a cafe awning draws behind it. | «Uchrashuv: ochiq, jamoat joyida.» | C3-V3 at 8.05 (3.10 s) | whoosh 8.0 |
| 5 | 10.30–12.00 | The three cards slide back into «YONDO»; it shrinks into the kit end card (logo, «Yondo — doim yoningda.», small «18+», CTA placeholder). One line under the cards for 1 s: «Tanishuv ilovasi emas — faoliyat uchun hamroh.» | (on-screen line above) | V7 «Yondo — doim yoningda.» at 10.40 (2.74 s, runs to 13.1 with the DRAFT voice) | chime 10.3; bass hit 10.8 |

With the DRAFT voice the speech ends at ~13.1 s, so the DRAFT cut is **13.0 s**; a voicelab.uz narrator reading at a normal pace fits
12.0 s. "Tanishuv ilovasi emas" is on screen only (not spoken): saying denials out loud makes them stick (research §2, RentAFriend).

**Voice:** the owner accepted the synthesized voice on 2026-11-19 (no voicelab.uz take); `c3_preview_draft_voice.mp4` is the voiced cut.

## VO script (narrator A)
| # | UZ | RU |
| --- | --- | --- |
| C3-V1 | Faoliyat: kofe, sayr, kino, tadbir. | Занятие: кофе, прогулка, кино, мероприятие. |
| C3-V2 | Hamroh: profilida xizmatlari ko‘rinadi. | Компаньон: в профиле видно, чем заняться вместе. |
| C3-V3 | Uchrashuv: ochiq, jamoat joyida. | Встреча: открыто, в общественном месте. |
| V7 | Yondo — doim yoningda. | Yondo. Всегда рядом. |

RU category names must match the app's RU locale (`apps/web/src/i18n/ru.ts`, `service.*`) at capture time.

## RU cut (done 2026-11-19)
- Captures: `APP_LANG=ru` in `ad5/capture_c3.mjs` = the whole run in the app's own ru locale (sign-in included); seed data
  (Madina, Toshkent, service descriptions) translated from `ru-dict.json`; the RU verified badge («✓ … подтверждена») is removed too.
- Page: `REEL_LANG=ru kit/build.py ad5/c3.tpl.html` (texts from the RU column; category names = ru.ts `service.*`; on-screen line
  «Не приложение для знакомств — компаньон для занятий.»; end card «Yondo. Всегда рядом.»). The RU voice is longer, so scenes are
  stretched piecewise-linearly (boundaries 1.4/5.0/8.5/11.35/12.25/14.6 s): **14.6 s**.
- Voice: `ad5/tts_ru.py` (Meta MMS Russian, CPU), played 1.1× by `REEL_LANG=ru ad5/audio_c3.py`.

## App captures (done 2026-11-19, `ad5/capture_c3.mjs`)
Real `apps/web` build against `server_video.py` (`AD5_SERVICES=1`), 1995 alphabet, theme `yondo`, 390×844 @2.5:
- `card.png` = the card feed with the Tadbir filter (`/?service_code=event&view=cards`); edited from `card-crop.png` = the card from
  its top to just under the category chips (the stats row and the price line are below the crop).
- `place.png` = the booking dialog scrolled to «Uchrashuv joyi»; edited from `place-crop.png` = label + field + the app's hint
  (the service select and the price estimate are outside the crop).
Crops are made from the recorded boxes (`card.json`, `place-field.json`), so no file used in the edit contains a price.

## Preview build (2026-11-19)
`kit/build.py ad5/c3.tpl.html` → `kit/render.mjs` (13.3 s, 399 frames) → `ad5/audio_c3.py` (music + SFX, optional voice dir) →
`ad5/mux.sh` (static gain to −14 LUFS + limiter). Two previews: no voice, and the MMS DRAFT voice (named `…_draft_voice.mp4`;
nothing in the frame says DRAFT). Media are not committed.

## Claims check
- "ochiq, jamoat joyida" describes the app's own hint and the recommendation; it does not say the app enforces it.
- No safety-absolute words, no "tasdiqlangan" unless the API badge itself is shown (it is not).
- No loneliness, health or romance wording.
