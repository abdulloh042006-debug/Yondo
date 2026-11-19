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
| 3 | 4.20–8.00 | Card 2 «Hamroh». The kit phone shows the real companion profile (illustrated portrait, service chips, languages; no price, no badge). The service chips lift one after another. | «Hamroh: profilida xizmatlari va tillari.» | C3-V2 at 4.25 (3.82 s) | swipe 4.2; click ×2 |
| 4 | 8.00–10.30 | Card 3 «Uchrashuv». The real booking form's meeting-place field with the app's own hint «Jamoat joyi: kafe, park, savdo markazi. Uy manzilini yozmang.» lifts out; a line-art square with a bench and a cafe awning draws behind it. | «Uchrashuv: ochiq, jamoat joyida.» | C3-V3 at 8.05 (3.10 s) | whoosh 8.0 |
| 5 | 10.30–12.00 | The three cards slide back into «YONDO»; it shrinks into the kit end card (logo, «Yondo — doim yoningda.», small «18+», CTA placeholder). One line under the cards for 1 s: «Tanishuv ilovasi emas — faoliyat uchun hamroh.» | (on-screen line above) | V7 «Yondo — doim yoningda.» at 10.40 (2.74 s, runs to 13.1 with the DRAFT voice) | chime 10.3; bass hit 10.8 |

With the DRAFT voice the speech ends at ~13.1 s, so the DRAFT cut is **13.0 s**; a voicelab.uz narrator reading at a normal pace fits
12.0 s. "Tanishuv ilovasi emas" is on screen only (not spoken): saying denials out loud makes them stick (research §2, RentAFriend).

## VO script (narrator A)
| # | UZ | RU |
| --- | --- | --- |
| C3-V1 | Faoliyat: kofe, sayr, kino, tadbir. | Занятие: кофе, прогулка, кино, событие. |
| C3-V2 | Hamroh: profilida xizmatlari va tillari. | Компаньон: в профиле его услуги и языки. |
| C3-V3 | Uchrashuv: ochiq, jamoat joyida. | Встреча: открыто, в общественном месте. |
| V7 | Yondo — doim yoningda. | Yondo. Всегда рядом. |

RU category names must match the app's RU locale (`apps/web/src/i18n/ru.ts`, `service.*`) at capture time.

## App captures needed (subset of ad 5's list)
`a02_profile_services.png` (+ chip boxes) and a close crop of the booking form's meeting-place field with its hint
(`a05_place_hint.png`). Same rules: real UI, no prices, no verified badge, 1995 alphabet, seed names without "DEMO".

## Claims check
- "ochiq, jamoat joyida" describes the app's own hint and the recommendation; it does not say the app enforces it.
- No safety-absolute words, no "tasdiqlangan" unless the API badge itself is shown (it is not).
- No loneliness, health or romance wording.
