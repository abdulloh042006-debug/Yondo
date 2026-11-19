# Ad 5 — «Keyinroq» ro‘yxati (C1, hero ad): script and storyboard

Stage 2, 2026-11-19. Approved by the CEO (concept C1, `concepts-2026-11.md`). **9:16, 1080×1920, 30 fps, 32.0 s**, H.264 + AAC 48 kHz,
master −14 LUFS / TP −1.5. Uzbek first (1995 Latin), RU cut after. Audience: city residents 20–35 (Toshkent first).
Sources: `kit/` (shared pieces) + `ad5/` (this ad, Stage 2b). AI shots: the owner generates them in Google Flow with
`flow-pack-c1-keyinroq.md` and uploads them with its file names. **Final render waits for those uploads.**

## Product accuracy (CEO review, 2026-11-19)
- The app has **no interests filter**. What ships: Kashf (discovery) with the **category** filter (`service_code`: Kofe, Sayr, Kino,
  Tadbir, Suhbat, …) shown as chips, the companion profile with its services (categories) and languages, the booking request
  (5 fields) and the toast "Bron so‘rovi yuborildi". The list items in this ad are mapped to those categories.
- Interests appear only if that feature has merged before capture (the CEO will say).
- **Prices never in frame.** Crops are chosen so no price line shows; the UI is not edited, with one exception: the
  «✓ … tasdiqlangan» badge is removed before each shot, because in the capture server it comes from an always-verified test double.
- The companion **reviews** a request (accepts or declines); the ad never says a meeting is guaranteed.

## The plan list (motion design; each item = a real category)
| Item on the list | Category chip in the app | AI payoff |
| --- | --- | --- |
| Yangi ko‘rgazmaga borish | Tadbir | s04 exhibition hall |
| Eski shahar bo‘ylab sayr | Sayr | s05 old-town walk |
| Yangi filmni ko‘rish | Kino | (tick only) |
| Yangi kafeni sinab ko‘rish | Kofe | (tick only) |

## Storyboard (t in seconds)
| # | t | Shot | Picture and motion | Caption (UZ) | VO (A, narrator) | Sound |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.00–3.00 | `m01_list_hook` (motion) | Paper ground. Heading «Shu oy:» (Manrope 800, 88 px) and 4 list lines draw in (ink, 64 px, 80 ms stagger, 0.0–0.6). Carrot stamp «KEYINROQ» (rotated −8°, scale 2.2 → 1 with a 6 % overshoot) hits each line at 0.75 / 1.25 / 1.75 / 2.25. Month in the top-right corner flips «Sentabr → Oktabr → Noyabr» (0.9 / 1.9). Slight camera shake 4 px on each hit. | 0.30 «Bu ro‘yxat hammada bor.» | V1 at 0.25 | paper rustle 0.0; stamp thud ×4 on the hits; low tick bed |
| 2 | 3.00–7.00 | `s02_poster_pass.mp4` (AI, 4.0 s of 6) | Dilnoza slows at the exhibition poster, smiles, walks on. Enters with a 0.25 s whip-pan from the right; the stamped line «Yangi ko‘rgazmaga borish» stays as a small top label (ink pill, 40 px). | 3.20 «Ko‘rgazma — keyinroq.» | V2 at 3.25 (covers shots 2–3) | whoosh 3.00; street ambience bed (synth noise, low) |
| 3 | 7.00–10.00 | `s03_map_board.mp4` (AI, 3.0 s of 5) | Close-up: a paper city map pinned on a cork board, an old-town area circled; a hand touches the circle, leaves. Label «Eski shahar bo‘ylab sayr». | 7.20 «Sayr — keyinroq.» | (V2 continues) | whoosh 7.00; soft clock ticks |
| 4 | 10.00–11.50 | `m02_kim_bilan` (motion) | Ink ground. «Kim bilan?» 150 px paper, letters drop in (back-ease, 50 ms stagger); the question mark tilts and becomes a carrot dot that slides down to 1450 px: the dot becomes the tap point of the next shot. | (the words are the caption) | V3 at 10.20 | bass hit 10.00; pop 11.20 |
| 5 | 11.50–13.50 | `a01_discover_tadbir` (app) | Kit phone flies up (0.35 s), screen = Kashf with the **Tadbir** chip active. The chip lifts out (scale 1.15, shadow) at 12.0. | 11.50 «Kerakli toifani tanlang.» | V4 at 11.60 (covers 5–8) | swipe 11.50; click 12.00 |
| 6 | 13.50–15.30 | `a02_profile_services` (app) | Push left. Companion profile: name, illustrated portrait, services (category chips) and languages. Crop stops above any price. | 13.50 «Profilda — xizmatlari va tillari.» | | swipe 13.50 |
| 7 | 15.30–17.10 | `a03_booking_form` (app) | Push left. Booking request: service, start time, duration, meeting place with the app's hint «Jamoat joyi … Uy manzilini yozmang.» Carrot tap ripple on «So‘rov yuborish» at 16.70. Crop excludes the price summary. | 15.30 «Vaqt va joyni tanlab, so‘rov yuboring.» | | swipe 15.30; tap 16.70 |
| 8 | 17.10–18.50 | `a04_request_sent` (app) | Bookings with the toast «Bron so‘rovi yuborildi. Hamroh javobini kuting.» Phone shrinks out 18.20–18.50. | 17.10 «Hamroh so‘rovni ko‘rib chiqadi.» | | chime 17.10; whoosh 18.20 |
| 9 | 18.50–23.50 | `s04_exhibition_hall.mp4` (AI, 5.0 s of 6–8) | Dilnoza and Kamola in the gallery, ~1 m apart; Kamola points out a detail, Dilnoza laughs. Iris-in from a carrot dot (0.3 s). Label pill «Tadbir». | 18.70 «Ko‘rgazma — bugun.» | V5 at 18.70 (covers 9–10) | music lifts (pad + light percussion) 18.50 |
| 10 | 23.50–27.50 | `s05_oldtown_walk.mp4` (AI, 4.0 s of 6–8) | Javlon and Rustam aka walk an old-town lane; Rustam aka points at a carved door; they stop and shake hands. Label pill «Sayr». | 23.70 «Sayr — shanba kuni.» | | whoosh 23.50; footsteps (synth) |
| 11 | 27.50–29.50 | `m03_list_ticks` (motion) | Paper ground, the same list; stamps fall away (rotate + drop), carrot ticks draw on each line (0.25 s apart). | 27.60 «Rejangiz bor. Hamroh — Yondoda.» | V6 at 27.60 | 4 rising chimes |
| 12 | 29.50–32.00 | `m04_end_card` (motion, kit) | Animated logo (kit, from the app's opening animation), «Yondo — doim yoningda.», small «18+», and the **CTA placeholder** (owner decides: «Tez kunda» or a link). | (end card text) | V7 at 29.70 | bass hit 29.50, sustain to the end |

VO timing above is the synthesized voice's. **Owner, 2026-11-19: this voice is accepted; no voicelab.uz recordings will come** (CLAUDE.md §7).

## VO script (narrator A: woman, 30–40, calm, warm)
| # | UZ (1995 Latin) | RU | DRAFT length |
| --- | --- | --- | --- |
| V1 | Bu ro‘yxat hammada bor. | Такой список есть у каждого. | 1.80 s |
| V2 | Ko‘rgazma — keyinroq. Sayr — keyinroq. | Выставка — потом. Прогулка — потом. | 4.46 s |
| V3 | Kim bilan? | С кем? | 0.86 s |
| V4 | Yondoda toifani tanlang, hamroh profilini ko‘ring va so‘rov yuboring. | В Yondo выберите категорию, посмотрите профиль компаньона и отправьте запрос. | 4.82 s |
| V5 | Ko‘rgazma — bugun. Sayr — shanba kuni. | Выставка — сегодня. Прогулка — в субботу. | 3.38 s |
| V6 | Rejangiz bor. Hamroh — Yondoda. | План есть. Компаньон — в Yondo. | 3.42 s |
| V7 | Yondo — doim yoningda. | Yondo. Всегда рядом. | 2.74 s |

**DRAFT voice:** Meta MMS (`facebook/mms-tts-uzb-script_cyrillic`, via the uzbek-tts skill, CPU). It is robotic, it has one voice that
is not the narrator, and it is for timing only: every draft file and preview is labelled **DRAFT VO**. edge-tts (`uz-UZ-MadinaNeural`)
was BLOCKED (the sandbox proxy does not pass WebSocket). Audio files are not committed. The final voice = the owner's voicelab.uz take.

## Captions
- ON (CEO directive 2026-11-19, owner confirmation pending). Kit caption style: Manrope 700, 54 px, paper on an ink box at 88 %,
  max 2 lines × 24 chars, word-by-word reveal (60 ms), lower third at y = 1380 (clear of the Reels/TikTok bottom UI and the right rail).
- Captions match the VO word for word where both exist (accessibility). Spelling: 1995 Latin, ‘ = U+2018, tutuq ʼ = U+02BC.

## Real app capture list (apps/web on current `main`, theme `yondo`, 390×844 @2.5, seed names without "DEMO")
Uzbek alphabet in the app = **1995** (the default until 2027-04-22), so screens match the captions.

| File | Route / state | Crop (in 975×2110 px) | Must show | Must not show |
| --- | --- | --- | --- | --- |
| `a01_discover_tadbir.png` | `/?service_code=event` (Kashf with the Tadbir chip) | full screen | chip «Tadbir ✕», first companion card | price line on the card (crop above it or pick a card scrolled so the price is under the phone edge), verified badge |
| `a01_chip_box.json` | bounding box of the Tadbir chip | — | for the lift effect | — |
| `a02_profile_services.png` | Madina's profile, scrolled to services + languages | top 0–1500 px | name, illustrated photo, service chips (Kofe, Sayr, Tadbir), languages | prices next to services: crop or capture the chip row only |
| `a03_booking_form.png` | booking request dialog filled: service «Tadbir», start 12:00, 60 daqiqa, meeting place «Markaziy kutubxona oldi» | dialog down to «So‘rov yuborish», the estimate line masked by framing (phone edge) or a separate crop above/below it | the fields + the app's own hint «Jamoat joyi: kafe, park, savdo markazi. Uy manzilini yozmang.» + «So‘rov yuborish» | «Taxminiy narx …» line |
| `a03_button_box.json` | bounding box of «So‘rov yuborish» | — | for the tap ripple | — |
| `a04_request_sent.png` | `/bookings` right after sending | full screen | toast «Bron so‘rovi yuborildi. Hamroh javobini kuting.» and the new booking with its pending status | price, payment buttons |

Seed change needed before capture (test double only, `server_video.py`): give Madina an **event** service
(`service_code: 'event'`, description «Ko‘rgazma va tadbirlarga birga borish»), so the Tadbir chip returns her. The price that the API
requires stays in the seed but never in frame. Capture with `capture.mjs` (+ the new routes above) after `npx vite build`; RU cut:
`APP_LANG=ru` as in reels 1–3.

## Motion specs (kit names)
- Easing: `eo` (cubic out) for entrances, `eio` for moves, `back(1.6)` for stamps and letter drops. No linear moves except tickers.
- Whip-pan cut: 0.25 s, 60 px motion blur (CSS filter blur on the outgoing layer), always right → left.
- Iris: carrot dot grows to a circle mask over 0.3 s, `eio`.
- Phone: kit `phone()` with sway rotateY −10° ± 5°, rotateX 4°; screen push 0.3 s; lift = scale 1.15 + 40 px shadow at 30 % ink.
- AI footage grade: kit neutral grade (blacks lifted to #111111, highlights warmed toward #F5F2EC, saturation 0.9).
- Reduced motion does not apply to video files; for the in-app use of the logo the app's own rules stay.

## Sound
Original synthesis (`audio.py` lineage): 100 BPM, D major pad (D–A–Bm–G), light percussion from 18.5 s, stamp thud (low sine
burst + paper noise), paper rustle, ticks, whoosh, chime, bass hit. Music ducks 8 dB under the VO. Master −14 LUFS, TP −1.5 dBTP.

## Adaptations
| Platform | Cut |
| --- | --- |
| Reels / TikTok / Shorts | the 32 s master, 9:16; captions inside the safe zone |
| Stories (15 s) | shots 1, 4, 5, 8, 9, 12 (0–3, 10–11.5, 11.5–13.5, 17.1–18.5, 18.5–21.5, end card 2.5 s) |
| 16:9 YouTube | Stage 3 if asked: AI shots generated 16:9 separately (do not crop 9:16 to 16:9) |
| RU | same timeline; captions/VO from the RU column; app captures with `APP_LANG=ru` |

## QC checklist (Stage 2b, after the render)
File exists; 1080×1920; 30 fps; 32.0 s ± 0.1; audio −14 ± 1 LUFS, TP ≤ −1.5 (audio-ears); no black frames (`ffmpeg blackdetect`);
captions readable on a phone (≥ 52 px, contrast ≥ 7:1); 1995 spelling; official logo geometry + outlined wordmark; app screens are
unedited captures with no price and no verified badge; non-romantic reading (pairs, distance, gestures); no "DEMO" on screen.
