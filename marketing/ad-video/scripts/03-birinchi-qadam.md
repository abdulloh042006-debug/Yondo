# Reel 3 — «Birinchi qadam» (production breakdown)

Owner script 3 of 3, 2026-11-11. Concept: conceptual motion design + 3D motion graphics + kinetic typography + emotional storytelling.
Emotion: a small decision can start a big change. Calmer, cinematic, philosophical.
**34.0 s, 9:16, 1080×1920, 30 fps, H.264 + AAC 48 kHz.**
Sources: `marketing/ad-video/reel3/` (`page.tpl.html` = deterministic `render(t)`, `build_reel.py`, `render.mjs`, `audio.py`, `mux.sh`).
App screens: the reel 1 `apps/web` captures in the `yondo` (day) theme (`capture.mjs` + `reel1/capture_list.mjs`). No media committed.

## Decisions
| Item | Decision |
| --- | --- |
| VO | **None.** The same blocker as reel 2: edge-tts needs a WebSocket the sandbox proxy does not pass, other free TTS needs torch, and voicelab.uz is paid. The lines are on screen as slow kinetic type. VO slots are listed below. |
| Places | Cafe, park, street, square with a public building (museum-like). There is no study or learning place. |
| Meeting | Two silhouettes walk towards each other and stop at a friendly distance (about 240 px apart at 1.3× scale). One waves hello. No hand-holding, no hearts, no romantic gesture. |
| "1 + 1 = YANGI TAJRIBA" | "?" flips away (rotateX 90°) and «YANGI / TAJRIBA» rises below the formula. The phrase is too long for one line at 3D size. |
| 180° camera move | The camera orbits the phone, not the UI. It starts behind the phone (back face: ink with the paper Y-symbol, carrot node) and swings 180° to the front. After that only a slow ±10° drift. The UI stays flat on the screen: no floating UI. |
| Theme | The video ground is ink (night, cinematic); the app is in the `yondo` day theme, which stands out as the light source. |
| Colour | Ink `#111111`, paper `#F5F2EC` and carrot `#E8501A` only. Carrot is used only for light: glows (radial gradient, ≤55 % at the core), light waves, roads, lamp heads, the logo node and the underline. Never for text. Greys are ink↔paper mixes (S5 background, extruded digit shadows). |

## Storyboard
### S1 HOOK 0.00–4.00 · 4.0 s
- **Light:** ink void with twinkling paper dust; a carrot halo grows behind the figure.
- **Camera:** pushes in from scale 0.06 to 1 (ease-in-out, 0.6–3.6). A single paper point of light resolves into a tiny paper human silhouette standing on a faint horizon.
- **Text:** «Ba’zan hammasi / bitta qarordan boshlanadi.» (76 px paper, slow word fade with blur, 140 ms stagger, 1.0–4.6).
- **Sound:** air ambience and a long, quiet riser.

### S2 VISUAL METAPHOR 4.00–10.00 · 6.0 s
- **4.20–4.80:** the figure takes one step (leg lift, forward).
- **4.75:** the foot lands and three carrot light rings spread across the ground in perspective (0.35 s apart). A perspective ground grid fades in.
- **5.30–7.60:** four carrot roads grow from the foot to four places on the horizon: Kafe, Park, Ko‘cha, Maydon (paper line-art). Each place lights up with its own halo and label (38 px paper).
- **Camera:** locked, so the step stays the centre of the world.
- **Text:** «Yangi kun, yangi tajriba yoki / yangi suhbat uchun faqat / birinchi qadam kerak.» (64 px, 6.6–9.95).
- **Sound:**
  - **bass hit 4.75** on the step
  - 3 light-wave whooshes
  - 4 rising chimes as the places light up: 6.10, 6.55, 7.00, 7.45
  - felt-piano bell notes over a D major pad

### S3 CONCEPT 10.00–17.00 · 7.0 s
- **10.0–11.0:** "1 + 1 = ?" in Space Grotesk 240–300 px with a 14-layer extruded shadow (paper → ink). Each glyph sways slowly in 3D (rotateY ±22°, rotateX ±8°) and arrives from translateZ −600.
- **11.3–12.4:** a light (carrot halo plus a paper core) appears between the two "1"s.
- **12.6–13.2:** a thin carrot beam runs down; "?" flips away and «YANGI / TAJRIBA» rises below (150 px).
- **14.3–15.0:** the formula lifts and fades.
- **14.8–16.4:** two silhouettes walk in from the left and right on a ground line and stop at a friendly distance. A halo grows between them. At 16.2 one raises a hand and waves hello.
- **Sound:** whoosh 10.0, shimmer 11.3, **bass hit 12.85** (YANGI TAJRIBA), soft footsteps 14.8–16.2, a chime on the wave at 16.2. Bm → G harmony.

### S4 YONDO 17.00–25.00 · 8.0 s
- **17.0–17.8:** the light between the two people flows up into the phone. The phone arrives from translateZ −900, back first.
- **17.2–18.8:** a **180° orbit** around the phone (ease-in-out). The back shows the paper Y-symbol and the carrot node; then the front turns to the camera with the screen on. After that: rotateY drift ±10°, rotateX 3±2°.
- **Screens** (calm crossfade 0.4 s with a slow upward drift; nothing pops out):

| Time | Screen | Detail |
| --- | --- | --- |
| 18.0–20.4 | Browse companions (Madina's card) | — |
| 20.3–22.6 | Profile: languages (Tillar), interests (Qiziqishlar), services and prices | — |
| 22.5–24.0 | Booking request form | carrot tap ripple on "So‘rov yuborish" at 23.4 |
| 23.9–25.0 | Bookings: "Bron so‘rovi yuborildi" | ends at the request; no payment |

- **24.7–25.2:** the screen light fades to ink.
- **Text:** «YONDO sizga o‘zingizga mos insonni / topish va vaqtingizni mazmunli / o‘tkazish imkonini beradi.» (54 px, 18.6–24.9).
- **Sound:**
  - whoosh 17.0 and an orbit whoosh 17.2
  - UI clicks: screen on at 18.0, screen changes at 20.3, 22.5 and 23.9
  - tap 23.4, success chime 23.9
  - a soft 80 BPM pulse (D–A–Bm–G) from 17 to 25 s

### S5 EMOTIONAL ENDING 25.00–31.00 · 6.0 s
- **Camera:** behind two people walking away down a lit path towards a public square with a cafe and park. Lamps with carrot heads stream past in perspective. The two keep a friendly distance and walk side by side.
- **Light:** the halo at the vanishing point grows (300 → 1100 px). The ground lifts from ink to a warm dark grey (an ink/paper mix). The dust fades.
- **Text:** «Ba’zi uchrashuvlar / oddiy kunni / unutilmas qiladi.» (70 px, 26.0–30.9).
- **Sound:** bass hit 25.0, quiet footsteps, a warm D major swell with bell notes.

### S6 BRANDING 31.00–34.00 · 3.0 s (ink)
- **31.0–31.8:** the point of light from the very first frame returns and flies to the logo's top-right position. It turns carrot and becomes that node.
- **31.6–32.4:** the paper strokes and nodes draw. This is the dark logo variant (`yondo-horizontal-dark.svg` colours).
- **32.1–32.9:** the outlined wordmark (`wordmark.svgfrag`, never retyped) wipes in, in paper.
- **End card:** «Doim yoningda.» (88 px) · carrot underline · «Tez kunda.» (56 px).
- **Sound:** whoosh 31.0, **bass hit 31.8**, shimmer 32.1, soft hit 32.5, an open D chord, and a fade over the last 1.2 s.

## Music
- Original numpy synthesis, no samples.
- **0–10 s:** void drone (D–A).
- **3–17 s:** felt-piano bells in D major / B minor colour.
- **17–25 s:** a soft pulse only under the app scene.
- **25 s on:** a warm swell, then an open chord on the logo.

## Mix and audio-ears report
The mix uses the same chain as reels 1–2 (`mux.sh`: two-pass loudnorm, limiter). Measured on the final mp4 (measured, not heard):
- −13.8 LUFS integrated, LRA 5.8 LU (calmer dynamics on purpose), true peak −2.4 dBTP, 0 clipped samples, no silences.
- Hits vs picture (the analyser places onsets ≈ −2 f early): step 4.75 → 4.69 · YANGI TAJRIBA 12.85 → 12.75 · light into phone 17.00 → 16.95 ·
  screen on 18.00 → 17.95 · screen changes 20.30/22.50 → 20.25/22.45 · tap 23.40 → 23.34 · toast 23.90 → 23.85 · ending 25.00 → 24.94 · logo node 31.80 → 31.74.
- Fix pass: the 18.0 and 25.0 hits were first masked by long whooshes (not detected); whooshes lowered, hits strengthened, re-checked.
  Tonal chimes (places 6.1–7.45) are not onsets by design.

## Transitions (summary)
S1→S2 continuous shot (the push-in ends on the figure, the step starts) · S2→S3 dissolve through the void (roads fade, the formula arrives from depth) ·
S3→S4 the light between the two people travels into the phone (light-path stitch) · S4→S5 the screen light blooms to ink, the path opens from the same glow ·
S5→S6 the glow contracts to the original point of light, which becomes the logo's carrot node.

## VO slots (if a voice is added later)
| Slot | Line | Starts |
| --- | --- | --- |
| 1 | Ba’zan... | 1.2 |
| 2 | ...yangi kun, yangi tajriba yoki yangi suhbat uchun faqat birinchi qadam kerak. | 6.6 |
| 3 | Yondo sizga o‘zingizga mos insonni topish va vaqtingizni mazmunli o‘tkazish imkonini beradi. | 18.6 |
| 4 | Ba’zi uchrashuvlar oddiy kunni unutilmas qiladi. | 26.0 |

Duck the music by 8 dB under the voice.

## AI generation
None: everything is code-drawn (SVG line art, CSS 3D glyphs) or a real app capture.

## Render
```sh
cd marketing/ad-video/reel3
SHOTS=$W/shots OUT=$W python3 build_reel.py && node render.mjs $W/page.html $W/video.mp4     # 1020 frames
OUT=$W python3 audio.py && ./mux.sh $W                                                     # -> $W/yondo-reel3-birinchi-qadam.mp4
```

**Export:** H.264, CRF 17, yuv420p, 30 fps, 1080×1920. AAC-LC 192 kbps, 48 kHz stereo. `+faststart`.
