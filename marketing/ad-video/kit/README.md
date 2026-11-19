# Yondo ad kit (2026-11-19)

Shared pieces for ads 5+ so each new ad is a template, not a copied folder. Deterministic: every frame is `render(t)`.

| File | What |
| --- | --- |
| `kit.js` | `K.logo` (official symbol + outlined wordmark, timing of the app's opening animation), `K.endCard` (logo, tagline, CTA, 18+), `K.caption` (ink box, Manrope 700 54 px, word reveal, y = 1380 safe zone), `K.stamp` («KEYINROQ»), `K.tick`, `K.shake`, easing helpers |
| `build.py` | template → page: fills `{{FONTS}} {{SHOTS}} {{KIT_JS}} {{WORDMARK_INLINE}} {{CTA}}`; `CTA` defaults to a visible `[ CTA ]` placeholder |
| `render.mjs` | page → 1080×1920 30 fps H.264 (or stills); uses the preinstalled Playwright |
| `demo.tpl.html` | the «Keyinroq» list hook + end card, for checking the kit |

Try it:
```
npm i @fontsource/manrope@5.1.0 @fontsource/space-grotesk@5.1.0   # in a tools folder
FONTS=<tools>/node_modules/@fontsource python3 kit/build.py kit/demo.tpl.html /tmp/kit/page.html
node kit/render.mjs /tmp/kit/page.html /tmp/kit stills 1 2.4 5.4      # or: node kit/render.mjs /tmp/kit/page.html demo.mp4
```
Colours: ink #111111, paper #F5F2EC, carrot #E8501A (graphics only, never small text). Uzbek text in 1995 Latin with ‘ (U+2018).
Not yet in the kit (built with ad 5 in Stage 2b, when the AI clips exist): phone mockup with real captures, whip-pan, iris,
AI-footage grade, sound set. They come from the reel 1–3 code (`reel1/page.tpl.html`, `reel1/audio.py`).
