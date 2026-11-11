# Reel 2 — «Bir harakat — bir nechta imkoniyat» (production breakdown)

Owner script 2 of 3, 2026-11-10. Concept: stitch hook + match cut + seamless transition + kinetic typography.
Emotion: motion, energy, many possibilities. **30.0 s, 9:16, 1080×1920, 30 fps, H.264 + AAC 48 kHz, −13.9 LUFS.**
Sources: `marketing/ad-video/reel2/` (`page.tpl.html` = deterministic `render(t)`, `build_reel.py`, `render.mjs`, `audio.py`, `mux.sh`).
App screens: the same `apps/web` captures as reel 1 (`capture.mjs` + `reel1/capture_list.mjs`, theme `yondo`). No media committed.

## Decisions
| Item | Decision |
| --- | --- |
| VO | **None.** Free TTS tried: edge-tts (`uz-UZ-MadinaNeural`) needs a WebSocket, which the sandbox proxy does not pass; Silero/MMS need a heavy torch install (not "cheap"); voicelab.uz is paid. The VO lines are on screen as kinetic type. VO slots are listed below. |
| Language practice | Not used (owner decision 2026-10-29). The 3 choices are conversation, walk, exploring the city. |
| Discover screen | The companion list (`m-list-1`). The search hero is not used because its copy mentions verified profiles. |
| Booking | Ends at "So‘rov yuborish" → "Bron so‘rovi yuborildi" toast. No payment is shown. |
| Colour | Ink `#111111`, paper `#F5F2EC`, carrot `#E8501A` only. Carrot only for graphics: sun, road line, dots, focus frame, clock hand, logo node. Never for text. |

## Storyboard
Each row lists the shot length, camera, object, text, transition / next-shot mechanism, sound and light.

### S1 HOOK 0.00–3.00
- **0.00–1.00 (1.0 s) — the ball comes at the camera.** Paper ground. An ink football with paper panels spins (540°/s) and accelerates at the camera (cubic ease-in): radius 60 → 1500 px. Ink speed lines appear and its floor shadow shrinks. Sound: long whoosh 0.00, kick from 0.00, so there is no silent start.
- **1.00–1.35 — stitch.** The ball covers the frame and the picture goes fully ink: "inside the ball". The ink then iris-wipes away (circle shrinking) as the ball passes the camera. Sound: **bass hit 1.00** and a reverse whoosh.
- **1.00–2.60 — night city, the sphere becomes the sun.** A paper sphere rises from below over a paper line-art skyline (ease-out). From 1.70 it turns carrot, with rays and a low-opacity carrot glow. Sound: chime 1.70.
- **Text:** 1.50 «Bir kun. / Minglab imkoniyat.» (104 px paper, word pop and blur-in). 2.10 «Bugun nima qilishni xohlaysiz?» (50 px, VO line 1).
- **Next shot:** a tilt down from the sun to a table.

### S2 STITCH CHAIN 3.00–7.00
All four objects turn about the same centre with the same radius (210 px) and the same angular speed (260°/s). That makes each cut land at the same point of the motion.
- **3.00–3.75 — cup.** Tilt down (the scene drops in from above over 0.3 s). A side-view cup falls onto the table with a back-ease bounce (lands at about 3.30). Over 3.45–3.75 the camera swings overhead: the cup squashes vertically and is replaced by the top view (saucer, cup, coffee, carrot sugar dot), which rotates. Sound: whoosh 3.00, knock + kick 3.30.
- **3.75–4.60 — match cut 1: cup → circular park path.** Seen from above, the turning cup crossfades into a turning ring path. It has trees around it and walkers on the path, one of them carrot. Sound: whoosh + pop 3.75.
- **4.60–5.75 — match cut 2: path rim → bicycle wheel.** The ring becomes a spoked wheel with a fork and chain-stay stub, rolling on a park path. Ground dashes stream left, and the wheel scales 0.86 → 1.25. Sound: whoosh + pop 4.60, spoke ticks 5.00.
- **5.75–7.00 — match cut 3: wheel → clock face.** The spokes fade, 12 ticks and two hands appear (the minute hand is carrot), and the hands spin and settle (ease-out). Sound: whoosh + pop 5.75, clock ticks.
- **Text** (top, 80–86 px, slides in from the right, VO line 2): 3.25 «Suhbatlashishmi?» · 4.45 «Sayr qilishmi?» · 5.65 «Yoki shaharni / birga kashf qilishmi?»

### S3 KINETIC TYPOGRAPHY 7.00–13.00
Each word has its own animation.
- **7.00–9.00 — SUHBAT (ink ground, paper letters, Space Grotesk 800).** The letters drop in with a back-ease. At 7.70–8.30 each letter shrinks to 42 % and slides into a chat column, and a paper speech bubble grows around it, alternating left and right. At 8.40 carrot typing dots appear. Sound: bass hit 7.00, 6 bubble pops 7.70–8.00, typing 8.45.
- **9.00–11.00 — SAYR (paper ground).** A perspective road draws in (vanishing point 540, 700), with a carrot centre line whose dashes stream toward the viewer. From 9.55 the letters lie down on the road (rotateX 0 → 68°). From 10.00 they slide away into the vanishing point. Sound: whoosh 9.00, falling whoosh 9.55.
- **11.00–13.00 — SHAHAR → KASHF (ink ground).** SHAHAR scales in. At 11.60 every letter is cut into a top and a bottom half, and the halves fly apart and rotate, with carrot shards. At 12.00–12.55 the halves of KASHF fly in from scattered positions and lock together. At 12.55 a carrot underline draws, then turns 90° into the road line and runs down the frame. Sound: bass hit 11.00, shatter 11.60, lock click + kick 12.50, riser 12.60.

### S4 YONDO UI 13.00–21.00
Paper ground with a carrot glow at 14 % opacity. The phone sways ±5° in Y and is tilted 4° in X.
- **13.00–13.80 — the road enters the phone.** The camera follows the carrot road line up the frame. The phone rises in from below (0.45 s). The screen opens as a circle iris from its bottom edge, where the line enters. Sound: whoosh 13.00, click 13.35.
- **Screens** (fast horizontal push, 0.3 s in and out):

| Time | Screen | Label pill | Detail | Sound |
| --- | --- | --- | --- | --- |
| 13.35–15.25 | Companion list (Madina's card) | Hamrohlar | — | — |
| 15.20–16.85 | Profile | Profil | — | swipe + click 15.20 |
| 16.80–18.55 | Profile details | Qiziqishlar | carrot focus frame scales onto "Qiziqishlar" at 17.20 | swipe + click 16.80, focus click 17.20 |
| 18.50–20.25 | Booking request form | Bron so‘rovi | carrot tap ripple on "So‘rov yuborish" at 19.70 | swipe + click 18.50, tap 19.70 |
| 20.20–21.20 | Bookings with the "Bron so‘rovi yuborildi" toast | — | — | swipe + click 20.20, success chime 20.20 |

- **Headline** (62 px, top): 13.50 «YONDO — o‘zingizga mos / hamrohni topishning yangi usuli.» (VO line 3).
- **20.90–21.20 — exit.** The phone shrinks and lifts out. Sound: whoosh.

### S5 FINAL STITCH + BRANDING 21.00–30.00
- **21.00–23.20 — objects return.** On paper, the ball, clock, chat bubble, cup and road line fly in from 1400 px and orbit the centre (40°/s). The drums break down. Sound: whoosh 21.00.
- **23.20–24.50 — objects join.** Each object flies to its role in the logo:
  - ball → top-left ink node
  - clock → top-right carrot node
  - chat bubble → bottom ink node
  - cup and road line shrink into the fork joint

  Sound: riser 23.20 → **bass hit 24.50**.
- **24.30–25.30 — logo strokes.** The Y-fork strokes draw (stroke-dashoffset). The geometry is exactly `yondo-symbol-light.svg`.
- **26.00–27.10 — lockup.** The symbol slides into the horizontal lockup, and the outlined wordmark (`wordmark.svgfrag`, never retyped) wipes in. Sound: whoosh 26.00, shimmer 26.30.
- **27.20–30.00 — end card.** «Doim yoningda.» (92 px) · a carrot underline · «Tez kunda.» (58 px). It holds, and the audio fades over the last 1.2 s. Sound: soft hit + chime 27.20, C major chord.

## Music
- Original numpy synthesis, 120 BPM in C major (C–Am–F–G). Kick from 0 s, clap from 3 s, hats and plucks from 7 s, a brighter arpeggio from 13 s, a breakdown at 21–23 s, and the final chord at 27 s.
- All cuts sit on the 0.5 s beat grid: 1, 3, 7, 9, 11, 13 and 21 s.

## Mix and audio-ears report
The mix uses a soft tanh bus, two-pass `loudnorm` (TP −1.5) and `alimiter` 0.68 (see `mux.sh`). Measured on the final mp4 (measured, not heard):
- **Loudness:** −13.9 LUFS integrated, loudness range 2.1 LU, true peak −2.5 dBTP.
- **Clean signal:** 0 clipped samples, no silences, sound from 0.00.
- **Hits vs cuts** (the analyser places onsets about −2 frames early):

| Cue | Cut (s) | Hit (s) |
| --- | --- | --- |
| Ball hit | 1.00 | 0.95 |
| Match cuts | 3.75 / 5.75 | 3.69 / 5.80 |
| SUHBAT | 7.00 | 6.94 |
| SAYR | 9.00 | 9.06 |
| SHAHAR | 11.00 | 10.94 |
| KASHF lock | 12.50 | 12.45 |
| Screen pushes | 15.20 / 16.80 / 18.50 | 15.21 / 16.81 / 18.53 |
| Tap | 19.70 | 19.64 |
| Toast | 20.20 | 20.22 |
| Logo | 24.50 | 24.45 |
| Tagline | 27.20 | 27.14 |

- **Looser matches:**
  - Cup knock 3.30 → 3.46 (+5 f): the beat kick at 3.50 is the stronger onset there.
  - Match cut 4.60 → 4.46 (−4 f): the kick at 4.50.
  - Screen open 13.35 → 13.47 (+4 f).

## VO slots (if a voice is added later)
| Slot | Line | Starts |
| --- | --- | --- |
| 1 | Bugun nima qilishni xohlaysiz? | 1.6 |
| 2 | Suhbatlashishmi? Sayr qilishmi? Yoki shaharni birga kashf qilishmi? | 3.2 |
| 3 | Yondo — o‘zingizga mos hamrohni topishning yangi usuli. | 13.5 |
| 4 | Yondo. Doim yoningda. Tez kunda. | 27.2 |

Duck the music by 8 dB under the voice.

## AI generation
None: everything is code-drawn line art or a real app capture.

## Render
```sh
# screens: see scripts/01-shaharda-yolgiz-emassan.md "How to render" step 1 (same $W/shots)
cd marketing/ad-video/reel2
SHOTS=$W/shots OUT=$W python3 build_reel.py && node render.mjs $W/page.html $W/video.mp4     # 900 frames, about 1 min
OUT=$W python3 audio.py && ./mux.sh $W                                                     # -> $W/yondo-reel2-bir-harakat.mp4
```

**Export:** H.264, CRF 17, yuv420p, 30 fps, 1080×1920. AAC-LC 192 kbps, 48 kHz stereo. `+faststart`.
