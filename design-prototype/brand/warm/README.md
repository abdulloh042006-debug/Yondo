# Yondo "warm" proposal — removing the workshop feel (design agent, 2026-10-29)
Status: PROPOSAL for the owner. Nothing is applied to `apps/web`; `../logo` stays the master; the approved girih-Y (`../ornament`) is reused unchanged (symbol + outlined wordmark paths copied, only colours/ids change).
Open `r.html` (Direction R) and `e.html` (Direction E) in a browser (no network). PNGs: `{r,e}-{logo,login,home,gift}.png`, `compare.png` (current app vs R vs E; the "current" column is a real Vite render of `apps/web` /login). `build.cjs` regenerates both pages, `render.cjs` the PNGs.

## 1. Diagnosis (cues that read "car workshop / auto service")
1. Logo: heavy, tight, all-caps YONDO + a *mechanical fork with ball nodes* + one orange dot = tool/part signage. 2. Black pill/block + orange as the only two loud things (hazard/garage palette). 3. Flat, empty white card; no craft, no story, no softness. 4. Peach haze (carrot at 20 %) looks like a tinted wall, not an atmosphere. 5. No cultural surface at all, so nothing says "Uzbekistan, people, hospitality".
Honest note: in the real render the login page is calmer than the logo; the logo + black button + peach haze are the main offenders.

## 2. What the two directions change
| Cue | R (restrained) | E (extended) |
|---|---|---|
| Logo | girih Y on a soft white tile, wordmark smaller (path unchanged), no orange block | same structure, strap/wordmark indigo, nodes pomegranate + saffron |
| Black block | ink only for type, hairlines and one small pill button; paper/white dominate | primary button indigo (not black); ink only for type |
| Orange | carrot only as small graphic accent (node, dots, tint 15-20 %), never text | carrot retired; accent = pomegranate / saffron / turquoise |
| Atmosphere | paper + white + carrot 15 % blob bottom-left (night: carrot 20 %) | cream + saffron glow top-right, indigo tint bottom-left; night = indigo-ink ground |
| Culture | line + tint motifs: stepped ikat diamond, bodom, majolica-style tile, pomegranate, lotus, abstract pishtaq portal, diamond border band; bounded, never full-bleed | same motifs with solid craft colours |
| Shapes | cards 30 px, pills 999, tile 32 % radius | same |
| Type | Manrope 800 headlines (already in the app), sentence case; Space Grotesk dropped from headings | same |
Not changed: copy, controls (phone, consent, send code, code step, resend, Telegram disclosure), 44+ px targets, uz/ru/en, day/night, DEMO tags, no romantic imagery.

## 3. Palettes and contrast (WCAG 2.x, computed from the hex values)
**R (no new colour):** ink #111111, paper #F5F2EC, white, carrot #E8501A.
| Pair | Ratio | Use |
|---|---|---|
| ink / paper | 16.90 | text |
| muted text (ink 70 % on paper / white) | 6.69 / 7.47 | hints |
| night: muted paper 72 % on ink / on card | 9.02 / 7.70 | hints |
| carrot / paper, / white, / ink | 3.36, 3.75, 5.03 | graphic only, never text |
**E (needs the owner to lift the rule; 6 colours):**
| Name | Hex | On paper | On white | On night #141723 | Role |
|---|---|---|---|---|---|
| Ink | #111111 | 16.90 | 18.88 | — | text |
| Paper | #F5F2EC | — | — | 15.97 | ground/text on dark |
| Indigo (lojuvard) | #26397F | 9.52 | 10.64 | 1.68 (tint 50 %: 6.11) | primary action, wordmark |
| Turquoise (feruza) | #0B7478 | 4.97 | 5.55 | tint 55 %: 7.07 | accent, text allowed >= 14 px bold |
| Pomegranate (anor) | #B3262E | 5.81 | 6.49 | tint 50 %: 6.74 | accent node, text allowed |
| Saffron (za'faron) | #E5A12B | 1.99 | 2.22 | 8.04 | graphic/fill only; ink on saffron 8.51 |
Night ground = ink mixed 16 % with indigo (#141723): paper text 15.97, muted 9.13, card 7.69. Primary button day: paper on indigo 9.52; night: ink on paper 16.90. First pick of turquoise #0F7C80 gave 4.46 on paper (fail), so it was darkened. Saffron never carries text. Pomegranate and turquoise have similar lightness (L 0.112 / 0.139): never use them as the only difference between two states; words/icons carry meaning (as today).

## 4. Tez: what we do not copy and why this will not look like Tez
Not used: lion mascot, stickers/memes, "skin/card-collection" concept, purple + mint gradient, hanger/frame/metro-line layouts, their typeface, any card illustration, caption wording ("Har bir skinning o'z hikoyasi bor"). Taken: the *principles* (soft atmosphere, big friendly type, rounded cards, craft motifs, storytelling). Colour world differs (warm cream + indigo/saffron vs lilac + mint); all motifs are drawn here from generic shared Uzbek craft vocabulary (ikat diamond, almond/bodom, tile rosette, pomegranate, lotus, arched portal), not traced from monuments, tiles or photos. A trademark/trade-dress similarity check is still required.

## 5. Recommendation
**R first, E as the next step if the owner wants more colour.** R fixes the workshop cues with zero change to the approved palette and keeps the brand recognisable; E is clearly richer and warmer (Tez-like richness) but it retires carrot, changes the approved logo colours and needs a palette decision. Honest limit: R is calm, not lavish; if the goal is "Tez-level colour richness", only E delivers it. Possible hybrid: R now, E tokens kept ready behind a new theme id `yondo-meros` (heritage) so the owner can compare in Settings.

## 6. Implementation impact (list only, nothing edited)
`apps/web/src/styles.css` (yondo/yondo-tun blocks ~L1270-1370: glow, `.aurora`, `.btn` radius/shadow, `.glass`, `--r-*`, heading font), `src/ui/theme.tsx` (swatches; new theme id for E), a lockup component + `public/` icons/favicon (tile lockup), new small `Ornament` SVG components (ikat/bodom/band) plus `ornament.css` (already proposed), Login.tsx/Home/Gifts markup only for decorative wrappers, i18n unchanged. E adds tokens `--c-indigo/-turq/-pom/-saffron` and a night ground; `.btn.danger`, `.tag.*`, `.banner` rules that collapse status to carrot must be redefined. Rough size: R about 1 day front-end, E 2-3 days plus a visual-regression sweep.

## 7. Accessibility
All ornament `aria-hidden`; meaning in text; decorative contrast intentionally low (<3:1) and never behind text; patterns bounded (hero strip, card corner, band), not a field; ikat displacement filter is static (no motion); `prefers-reduced-motion` unaffected; focus ring indigo (E, 9.52) / ink (R). Checked: both pages load with 0 console errors in Chromium. Not tested: real devices, forced-colors mode, screen readers, glass blur on low-end phones, uz/ru/en text length beyond the uz copy shown.

## 8. Honesty
Craft-inspired (shared vocabulary): ikat stepped diamond, bodom, tile rosette, pomegranate, lotus, portal+minarets, border band. My own abstraction: every drawing, the colour pairings, the stair/displacement ikat look. A native Uzbek designer/cultural review and a trademark check are needed before public launch. The pishtaq illustration is generic, not a named monument.

## 9. Open questions for the owner (recommended answer first)
1. Which direction: R now (recommended), E, or R now + E as an optional theme?
2. May the carrot node in the logo stay in R and be retired in E (recommended: yes)?
3. Keep the approved girih Y, shown on a soft tile (recommended: yes), or show it tile-less?
4. Should DEMO illustrated avatars stay until real photos arrive (recommended: yes)?
5. Allow the Space Grotesk to Manrope headline change in all themes (recommended: yes)?
6. Is a native-designer review before launch acceptable as a gate (recommended: yes)?
