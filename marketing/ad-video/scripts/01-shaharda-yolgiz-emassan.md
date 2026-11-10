# Reel 1 — «Shaharda yolg‘iz emassan» (production breakdown)

Owner script 1 of 3, 2026-11-10. Concept: transitional hook + conceptual motion design + UI motion design.
Emotion: loneliness → possibility. **34.0 s, 9:16, 1080×1920, 30 fps, H.264 + AAC 48 kHz, -13.8 LUFS.**
Sources (all in `marketing/ad-video/reel1/`): `page.tpl.html` (every frame = deterministic `render(t)`),
`build_reel.py`, `render.mjs`, `audio.py`, `mux.sh`, `capture_list.mjs`. No video/audio is committed.

## Deviations from the owner text (and why)
| Item | Decision |
| --- | --- |
| Scene 3 "til mashqi" (language practice) | Replaced by **exploring the city together** (route on a map, skyline, one points the way). Owner decision 2026-10-29. The profile field "Tillar" still appears (which languages a companion speaks). |
| VO | **No voice-over.** No human actor this time; a synthetic Uzbek voice was not used (quality risk, extra credits). The VO lines are carried as kinetic typography (secondary lines) + sound design. A VO track can be added later: the timings below are the slots. |
| "3D digits" | CSS 3D (perspective + translateZ + rotateY) on real Space Grotesk glyphs, not a 3D model. |
| "Realistic phone" | Flat ink device with depth shadow and a continuous 3D tilt (rotateX/Y); screens are real `apps/web` captures. |
| Verified badge | Hidden in captures (it comes from a test double). The search hero copy that says "Tasdiqlangan profillar" is never shown. |
| Prices | Real seed values from the app's own screens (150 000 so‘m / 60 daq). No payment is shown: the booking screen itself says the payment provider is not connected; the flow ends at "Bron so‘rovi yuborildi". |

## Palette, type, assets
- Colours: ink `#111111`, paper `#F5F2EC`, carrot `#E8501A` (graphics, dots, lines, glow at ≤18 % opacity). Greys only as ink↔paper mixes (S5 sunrise). Carrot is never used for text.
- Type: Manrope 600/700/800 (kinetic copy), Space Grotesk 700 (clock digits). Fonts from `@fontsource` (Google Fonts blocked in the sandbox).
- Logo: Y-fork geometry copied from `design-prototype/brand/logo/yondo-symbol-light.svg`; wordmark = the outlined path in `wordmark.svgfrag` (never retyped), lockup proportions from `yondo-horizontal-light.svg`.
- 2D line-art (drawn in code, 6–8 px strokes, round caps): people, cafe table/cups, bench, lamp, trees, Tashkent-like skyline (TV tower, dome, minarets), map route + pin, chat window, speech bubbles. No photos of real people; profile pictures are the repo's illustrated portraits (`photos/`).
- App screens: `apps/web` production build + real FastAPI on SQLite (`server_video.py` test doubles), mobile 390×844 @2.5×, theme `yondo` (day). Files used: `m-list-1`, `m-list-2` (new `capture_list.mjs`), `m-profile`, `m-profile-services`, `m-booking-dialog`, `m-bookings` (`capture.mjs`).
- Public places only: cafe table, park, city streets. People keep a normal distance; no touching, no romantic gestures or wording.

## Storyboard (exact timings; t in seconds)
### S1 HOOK 0.00–3.00 (ink ground)
| t | Picture / camera | Text | Sound |
| --- | --- | --- | --- |
| 0.00–0.45 | Paper-outline phone scales 0.92→1 in the centre. "19:42" (paper digits), "Seshanba, kech", a seconds dial with a carrot hand ticking every 1/6 s. | — | clock ticks every 1/6 s (start at 0.00: no silent first second), low A drone |
| 0.50–1.30 | The five glyphs jump off the screen one by one (60 ms stagger): translateZ 0→420 px, rotateY 360°, scatter; the phone recedes to 0.82 and fades. | — | 5 "digit pop" clicks, rising pitch, panned L→R |
| 1.25–1.95 | **Camera dives into the second hand**: the dial zooms ×26 onto the hand's tip; at 1.70 the carrot tip floods the frame. Digits fall away. | — | riser 0.90→1.88 |
| 1.95–2.35 | **Stitch**: the carrot flood closes as an iris onto one carrot figure → busy night city (paper skyline, 16 paper figures crossing both ways at different speeds/depths). One carrot person stands still in the centre. Slow push-in 1.00→1.08. | 2.15 «Shahar to‘la odam...» (104 px, word stagger, blur-in) · 2.40 «Har kuni minglab insonlar / yonimizdan o‘tadi...» (50 px, VO line 1) | **bass hit 1.95**, filtered city murmur |

### S2 PROBLEM 3.00–8.00 (paper ground, ink line-art; each cut = 0.22 s whip from the right)
| t | Picture | Text | Sound |
| --- | --- | --- | --- |
| 3.00–4.00 | Cafe: one person seated, one cup with carrot steam, the opposite chair only a dashed outline. | 3.15→ «...ammo ba’zan birga vaqt o‘tkazadigan / inson topish qiyin.» (VO line 2, word by word through 5.95, top) | whoosh on cut 3.00; lonely piano (A minor) |
| 4.00–5.00 | Empty park bench, unlit lamp, tree, carrot leaves falling; push-in 1.06. | (continues) | whoosh 4.00 |
| 5.00–6.00 | Phone: the clock flips 19:42→20:17→…→23:18, "Yangi xabar yo‘q", carrot dial hand spinning. | (continues) | whoosh 5.00, ticks every 1/6 s |
| 6.00–6.60 | Big words «Suhbatlashadigan / odam yo‘q» (112 px). | the words are the object | soft impact 6.00 |
| 6.60–7.40 | **Words become the chat**: every letter drifts out, rotates, shrinks and fades while the empty chat window (dashed avatar, empty body, "Xabar yozing...") draws in where the letters were. | — | sparkle (letters dissolve) |
| 7.35–8.00 | An ink typing bubble pops in; three paper dots bounce. | — | pop 7.35, soft typing 7.45–7.85 |

### S3 TRANSITIONAL HOOK 8.00–13.00
| t | Picture | Text | Sound |
| --- | --- | --- | --- |
| 8.00–8.75 | Zoom into the bubble: ink floods from the centre; the dots grow ×4 and turn carrot with a soft glow. | — | whoosh 8.00 |
| 8.75–9.25 | The three dots fly apart on curved paths with fading trails. | — | 3 pings 8.75 (panned L/C/R); groove starts at 9.00 (C–G–Am–F, kick on 1/3) |
| 9.25–10.50 | Dot 1 opens as an iris → **two people talking** at a cafe table; speech bubbles pop alternately; the second bubble holds a carrot dot. | — | pop + swell + chime 9.25 |
| 10.50–11.75 | That carrot dot opens the next iris → **walking side by side in a park** (trees scroll, carrot sun). | — | pop + swell + chime 10.50 |
| 11.75–13.00 | The sun opens the last iris → **exploring the city together**: skyline windows light up, a carrot route draws to a map pin, one figure points the way. (Replaces "language practice".) | 12.00 «Endi buning uchun / yechim bor.» (scale-in, VO line 3) | pop + swell + chime 11.75; riser 12.40 |

### S4 YONDO DEMO 13.00–22.00 (paper ground + carrot glow ≤16 %)
Phone flies in from below with a −12° roll, then floats with a slow 3D sway (rotateY −14°±7°, rotateX 5°±2°).
Real UI crops are lifted out of the screen (scale 1.12–1.3, back-ease overshoot, deep shadow); ink label pills name each step.
| t | Screen | Lifted element / motion | Label | Sound |
| --- | --- | --- | --- | --- |
| 13.00–14.15 | companion list (`m-list-1`) | 13.55 Madina's card info (name, city, interests, "dan 75 000 so‘m") pops forward-left | Hamrohlar | bass hit 13.00, click 13.55 |
| 14.00–15.00 | list scrolled (`m-list-2`) | screen slides up | — | swipe 14.00 |
| 14.90–16.40 | profile (`m-profile`) | 15.15 the profile photo lifts and tilts 3° | Profil rasmi | swipe 14.90, click 15.15 |
| 16.30–19.50 | profile details (`m-profile-services`) | 16.45 interests fly out as cards **Kitob**, **Sayr**; 17.35 the language codes become cards **UZ o‘zbek tili**, **RU rus tili** that line up in order on the left; 18.20 the service card "Kofe · 150 000 so‘m / 60 daq" lifts | Qiziqishlar → Tillar → Xizmatlar va narxlar | card flips 16.45/16.60/17.35/17.50, click 18.20 |
| 19.40–20.95 | booking request form (`m-booking-dialog`) | 20.35 carrot tap ripple on "So‘rov yuborish" | Bron so‘rovi | swipe 19.40, tap 20.35 |
| 20.85–22.00 | bookings (`m-bookings`) | 21.05 the toast "Bron so‘rovi yuborildi. Hamroh javobini kuting." lifts | So‘rov yuborildi | swipe 20.85, success chime 21.05 |
Headline (top, 62–70 px, word stagger): 13.20–17.30 «YONDO orqali o‘zingizga / mos hamrohni toping.» · 17.45–21.90 «Suhbatlashing, sayr qiling / yoki shaharni / birga kashf eting.» (VO line 4).

### S5 EMOTIONAL ENDING 22.00–29.00
| t | Picture / camera | Text | Sound |
| --- | --- | --- | --- |
| 21.70–23.40 | **Stitch**: the phone collapses into a carrot dot that rises to become the sun over a night park. | — | reverse whoosh 21.95, bass hit 22.00, drums stop |
| 22.00–29.00 | The carrot person from S1 now walks with a companion (side by side, normal distance), trees and lamps scroll. **Camera rises** (scene drops 520 px, zooms 1.15→0.86) to reveal the skyline; windows light up carrot one by one; the ground shifts ink → paper (night → bright day), line colour flips paper → ink, lamps switch off. | 23.30 «Ba’zan kuningizni / o‘zgartirish uchun / bir insonning o‘zi kifoya.» (72 px, 160 ms word stagger, colour follows the light) | warm pads Am–F–C–G, rising arpeggio, riser 28.40 |

### S6 BRANDING 29.00–34.00 (paper)
| t | Picture | Text | Sound |
| --- | --- | --- | --- |
| 29.00–30.20 | Pieces of earlier scenes fly in from the edges and shrink to the centre: clock digits 1-9-4-2, the typing "…", 10 chip outlines (UI chips), and the three dots that become the logo nodes (ink, carrot, ink). | — | long whoosh 29.00 |
| 29.90–30.90 | The Y-fork strokes draw between the nodes (stroke-dashoffset). | — | **bass hit 30.20** + C major chord |
| 31.10–32.20 | The symbol slides into the horizontal lockup; the outlined wordmark wipes in left→right. | — | whoosh 31.10, shimmer 31.40 |
| 32.10–34.00 | «Doim yoningda.» (92 px) · carrot underline draws 32.60 · «Tez kunda.» (58 px) | end card | soft hit + chime 32.10, chord rings, fade-out 32.8–34.0 |

## Sound design and music
- All original synthesis in `audio.py` (numpy; no samples, no copyrighted music). 120 BPM grid: the cuts at 3/8/13/22/29 s sit on beats.
- Music arc: A drone (0–3) → sparse piano in A minor (3–8) → C–G–Am–F groove with kick, clap, hats, bass, plucks (9–22) → warm pads + arpeggio, no drums (22–29) → C major logo chord (29–34).
- SFX palette: clock tick, digit pop, riser, bass hit (sub sweep + noise), whoosh (band-swept noise), sparkle, UI pop/click, typing, ping, iris swell + chime, swipe, tap, success chime, shimmer. 74 cues, written to `cues.json` at render time.
- Mix: soft tanh bus → two-pass `loudnorm` (I −13.6 target, TP −1.5, linear) → `alimiter` 0.68 → AAC 192 kbps.

### audio-ears report (final mix, measured, not heard)
- Integrated **−13.8 LUFS**, loudness range 3.3 LU, true peak **−1.8 dBTP**, **0 clipped samples**, no silences, no silent start (ticks from 0.00).
- First pass had 863 clipped samples (a mono fold-down of loud bass hits) and 85–99 % bass share; fixed by lighter kick/bass/impacts and a limiter; re-checked.
- Hits vs picture (analyser onset, ±2 frames resolution): flood→city 1.95 → 1.90 (riser peak just before the hit); cuts 3.00/4.00/5.00 → 3.04/4.02/5.02 (+1 f); typing bubble 7.35 → 7.38; iris pops 9.25/10.50/11.75 → 9.20/10.45/11.70 (−2 f, constant analyser offset); product 13.00 → 12.93; screen change 14.00 → 14.00; photo 15.15 → 15.19; tap 20.35 → 20.29; ending 22.00 → 21.94; logo 30.20 → 30.14; tagline 32.10 → 32.04. All within ±2 frames except the toast chime (+4 f, tonal attack).

## Optional VO (if added later)
| Slot | UZ line | Starts |
| --- | --- | --- |
| 1 | Har kuni minglab insonlar yonimizdan o‘tadi... | 2.0 |
| 2 | ...ammo ba’zan birga vaqt o‘tkazadigan inson topish qiyin. | 3.2 |
| 3 | Endi buning uchun yechim bor. | 11.9 |
| 4 | YONDO orqali o‘zingizga mos hamrohni toping. Suhbatlashing, sayr qiling yoki shaharni birga kashf eting. | 13.3 |
| 5 | Ba’zan kuningizni o‘zgartirish uchun bir insonning o‘zi kifoya. | 23.3 |
| 6 | Yondo. Doim yoningda. Tez kunda. | 32.0 |
Duck music −8 dB under VO. Voices only from the owner (voicelab.uz) or a reviewed TTS take.

## AI generation
None. Every picture is code-drawn line-art, real app captures or the repo's illustrated portraits.

## How to render
```sh
# 1. app screens (once): build apps/web, copy capture files, run both captures
cd apps/web && npm ci && npx vite build && mkdir -p e2e/.tmp
cp ../../marketing/ad-video/{capture.mjs,server_video.py} ../../marketing/ad-video/reel1/capture_list.mjs e2e/.tmp/
THEME=yondo OUT=$W/shots YONDO_PY=<api venv python> PHOTOS_DIR=$PWD/../../marketing/ad-video/photos node e2e/.tmp/capture.mjs
OUT=$W/shots YONDO_PY=<api venv python> PHOTOS_DIR=$PWD/../../marketing/ad-video/photos node e2e/.tmp/capture_list.mjs
# 2. page, frames, sound, mux (fonts + playwright-core in /home/claude/fonttools, see ../README.md)
cd ../../marketing/ad-video/reel1
SHOTS=$W/shots OUT=$W python3 build_reel.py
node render.mjs $W/page.html $W/video.mp4            # 1020 frames, ~3 min; stills: node render.mjs $W/page.html <dir> stills 1 9.8 16
OUT=$W python3 audio.py && ./mux.sh $W                # -> $W/yondo-reel1-shaharda-yolgiz-emassan.mp4
```
Export: H.264 high, CRF 17, yuv420p, 30 fps, 1080×1920; AAC-LC 192 kbps 48 kHz stereo; `+faststart`.
