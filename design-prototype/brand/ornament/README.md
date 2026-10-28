# Yondo — Uzbek-ornament "Y" identity layer (PROPOSAL, 2026-10-28, design agent)

Status: **proposal for the owner's approval. Nothing here is applied to the app.** The official logo in `../logo/` is untouched and stays the master until approved.
Everything in this folder is hand-authored SVG/HTML/CSS (no raster sources, no external fonts, no scripts except the animation preview). PNGs in `png/` are renders of those files.

## 1. The concept in three sentences
The mark keeps the approved skeleton (two converging arms, a stem, three nodes; same coordinates as `../logo/yondo-symbol*.svg`) and turns it into a **girih strap**: the arms and stem become a double-line ribbon that passes *over* one arm and *under* the other at the fork, the two top nodes become **8-pointed girih stars** (left ink, right carrot, as in the current mark), and the stem ends in a **72° rhombus** (the basic girih tile). The Y stays the dominant silhouette; the ornament is a *layer* (pattern strip, divider, corner, double rule) that reuses the same three shapes (star, rhombus, strap) and never becomes a background.

## 2. What is authentic-inspired and what is my abstraction (please read)
- **Inspired by real Central-Asian craft:** girih/strapwork (interlaced double lines), the 8-pointed star-and-cross lattice found in Samarkand/Bukhara/Khiva tilework, 72°/108° rhombus tiles, and (concepts B and C) the *bodom* (almond) and the rhombus chain of *adras/ikat* textiles and *suzani/doppi* embroidery.
- **My own abstraction:** the exact drawing. It does not reproduce any specific monument, tile or textile. The over/under fork, star-as-node, pencil-tip foot and the reduction to ink/paper/carrot are design decisions. Real Uzbek tilework is polychrome (turquoise, blue); the palette rule removes that on purpose, so it reads as *inspired by*, not as a replica.
- **Risk to name honestly:** the 8-pointed star and girih are shared by the wider Islamic world. A viewer may read "Islamic/Central Asian" rather than "Uzbek". The more specific Uzbek markers are the textile ones (bodom, adras rhombus chain), which is why B and C exist. **Not reviewed by a native designer, a cultural expert or a trademark search.** I recommend both reviews before public launch (the owner's "avoid generic Islamic motifs" rule is a judgement call that needs a human who knows the craft).

## 3. Concepts and recommendation
| | Concept | Files | Reads as Y? | Verdict |
|---|---|---|---|---|
| **A** | **Girih strap Y** (double-line ribbon, over/under fork, star nodes, rhombus foot) | `concepts/concept-a-girih.svg`, `symbols/*` | Yes, strongest silhouette; survives to 16 px via the micro form | **Recommended** (closest evolution of the approved mark, best at small sizes) |
| B | **Bodom Y** (three almond petals, seed nodes, hairline veins) | `concepts/concept-b-bodom.svg` | Yes, but softer; can read as a sprout | Not recommended as the mark; keep the almond as a secondary motif (flower glyph in the gift mockup) |
| C | **Adras Y** (each limb a chain of 72° rhombi, star nodes) | `concepts/concept-c-adras.svg` | Yes at ≥ 48 px; dotted at small size | Not recommended as the mark; its rhombus chain became `pattern/strip-rhombus-chain.svg` |
The concept sheets show each on paper and on ink at 240/64/32/24/16 px (no text, no fonts).

## 4. Symbol variants (`symbols/`) and sizes
| File | Use | Size |
|---|---|---|
| `y-ornament.svg`, `-on-ink.svg` | full: double-line strap + star eyes | **≥ 48 px** (hero, intro, onboarding, covers) |
| `y-ornament-simple.svg`, `-simple-on-ink.svg` | solid strap, no eyes | **24–47 px** (top bar, cards, empty states) |
| `y-ornament-mono-ink.svg`, `-mono-paper.svg` | one colour, accent star hollow (same idea as the existing mono logo) | stamps, emboss, 1-colour print |
| `lockup-horizontal.svg`, `-on-ink.svg` | simple symbol + the **official outlined wordmark path, copied unchanged** | ≥ 96 px wide |
| micro (no new file) | the **existing** `../logo/yondo-symbol-small*.svg` | **16–23 px**, favicon, dock |
`legibility.html` / `png/legibility.png` show 16/24/32/64 px at 1x on paper and ink for every variant. Verdict from that sheet: full is mush below 32 px (so the ≥ 48 rule), simplified still reads as Y at 24 px, micro is the right form at 16 px. Real devices, print and embroidery are **not tested**.

## 5. Usage rules
- **Colour:** ink #111111 / paper #F5F2EC / carrot #E8501A only. Ink version on paper or white, paper version on ink. Carrot is a graphic (star, ring, dot): never text, never a background for the mark. No gradients, shadows, outlines, recolouring, rotation, skew, stretch.
- **Clear space:** at least one star radius (≈ 16 % of the symbol height) on every side; one star diameter in heroes.
- **Where it may appear:** brand lockup in the top bar; opening animation; onboarding cards; empty and success states; one star bullet per section header; **one** card corner per screen (featured card only); a divider between major sections (≤ 2 per screen); a pattern field inside **one** bounded banner (hero or catalog header, ≤ 140 px tall); rhombus-chain strip under a header; double rule above totals; video-guide covers; app icon.
- **Where it must NOT appear:** as a full-screen, page, section or list background; behind body text, form fields or buttons; repeated per list item; over photos of people; as an icon for a control; as the only carrier of meaning (status stays in words); animated in a loop; any romantic, heart or couple imagery.
- **Pattern tile rules:** `pattern/tile-star-lattice.svg` is a 48 px tile, stroke 1.2, applied only as a `currentColor` mask (`ornament.css .orn-field`), **opacity ≤ 7 %**, inside a bounded container with `overflow:hidden; border-radius:inherit`, anchored at the container origin, never rotated or scaled to non-integer sizes, never over a photo. Text over it stays at 14.9:1 (measured below).
- **Both themes:** everything is `currentColor` + the literal carrot, so it works unchanged in `yondo` and `yondo-tun` and would in any ink/paper theme. No new colour theme is introduced.

## 6. Contrast and accessibility findings (computed, WCAG 2.x)
| Pair | Ratio | Note |
|---|---|---|
| ink on paper / paper on ink | 16.90 | mark, text |
| carrot on paper | **3.36** | graphic only (passes the 3:1 non-text rule, fails text) |
| carrot on ink | 5.03 | graphic; ink text on a carrot fill is also 5.03 |
| paper on carrot | 3.36 | do not put paper text on carrot |
| ink text over paper + 6 % pattern | 14.89 | pattern does not hurt readability |
| paper text over ink + 6 % pattern | 14.88 | same on night |
| divider hairline 34 % / strip 30 % on paper | 2.20 / 1.98 | **decorative only**, never carries meaning |
| card corner 45 % ink on paper / paper on ink | 2.97 / 4.17 | decorative |
- All ornament is `aria-hidden`; meaning always lives in text (status words, headings). Controls in the mockups are real links/buttons with the app's existing 44 px targets and focus ring.
- Strap rails are 2.45 viewBox units: ≥ 1.8 px at 48 px, hence the ≥ 48 px rule for the full form.
- Motion: transform/opacity (and one `stroke-dashoffset` draw) only, one-shot, never looping; `prefers-reduced-motion` gives a static final frame.
- Checked in Chromium: all HTML pages load with 0 console errors; the five mockups have no horizontal scroll at 360 px.
- Observations about the *existing* app seen while mocking (not changed): at 360 px the top bar with SOS + brand + language switch overflows by ~25 px (the mocks tighten the gap); the day/night glow renders peach/brown at 20–22 % opacity, which the "never brown/peach" note in CLAUDE.md §7 wants to avoid; the nav/favourites heart icon conflicts with the "no hearts" direction (bookmark glyph suggested).

## 7. Opening animation (`preview.html`, storyboard `png/opening-storyboard.png`)
Open `preview.html` in a browser: tap/click/Enter/Space/Esc skips instantly (visible "Ötkazib yuboriş" button, focused first); buttons replay, force the reduced-motion variant and switch UZ/RU/EN. **No audio element exists.** `?t=1400` freezes a frame; `?rm=1` forces reduced motion.
| ms | What happens |
|---|---|
| 0–150 | ink field (brand literals, so even the Gul default theme shows only ink/paper/carrot) |
| 150–410 | rhombus foot pops (scaleY .2→1) |
| 250–1050 | strap draws from the foot up the stem and into the left arm (`stroke-dashoffset`, ease-out) |
| 600–1050 | right arm draws from the fork and tucks under the left strap |
| 900–1420 | stars bloom: left (paper) 900, right (carrot) 1000; scale .2→1 and −45° → 0 (8-fold symmetry, so the turn is subtle) |
| 1250–1900 | one soft carrot ring leaves the right star (r 10→24, opacity .55→0) |
| 1400–1900 | official outlined wordmark rises 8 px + fades in; 1500–1950 double rule with a carrot star grows from the centre |
| 2000–2450 | slogan fades in (uz "Yondo doim yoningda" / ru "Yondo. Всегда рядом." / en "Yondo, always by your side") |
| 2450–2800 | overlay fades out over the already-mounted app (350 ms); total 2.8 s |
Skip = 150 ms fade. **Reduced motion:** final frame shown immediately, held 1.2 s, opacity-only 150 ms exit, still skippable. Product rules proposed in the design plan (`docs/design-plan-s37.md` C1): key `yondo.intro.v1` written at start, not shown on deep links, `inert` app while it runs. Performance: ≈ 10 animated SVG elements, GPU-friendly transforms; not measured on low-end phones.

## 8. Onboarding cards (`onboarding/`)
`card-1-top.svg`, `card-2-bron-qil.svg`, `card-3-xavfsiz-uchrash.svg` (320×200, `currentColor` + carrot, work in both themes) and `onboarding/cards.html` / `png/onboarding-cards.png` (cards with dots and the approved Uzbek copy). Card 1: stacked abstract profile cards (star placeholder, no faces) under a magnifier. Card 2: calendar with a carrot star on the chosen day and a clock. Card 3: meeting place in an octagon (public square) with a rhombus route, a booking-details card and three small tool marks (report, block, signal to moderator). **No shield, lock, heart or couple, and the copy says Yondo does not guarantee safety or act as emergency service.**

## 9. Components and mockups
- `ornament.css`: the identity layer (`.orn-field`, `.orn-strip`, `.orn-corner`, `.orn-divider`, `.orn-rule2`, `.orn-head`, `.orn-price`, one-shot motion). `ornament-fonts.css`: optional local app fonts (falls back to system-ui).
- `components.html`: nav brand lockup, corner + divider + double rule, empty and success signature (the Y draws, the carrot star pops once), price-breakdown header in **both** fee models (A: fee added to the customer total, B: fee held back from the companion), gift catalog header — each in `yondo` and `yondo-tun`.
- `mockups/{home,profile,gifts,checkout,safety}.html` (responsive, real `apps/web/src/styles.css` tokens; add `?theme=yondo-tun`). `png/mockup-*.png` show 1440 px (day) beside 360 px (night). The pages link `../../../../apps/web/src/styles.css` and local fonts, so they need this repo checkout; sample data is marked DEMO; the safety map is labelled "Kelajak bosqichi" (future).
- Checkout shows the owner's latest model (fee held back from the companion, customer pays the service price) plus the companion earnings view; the same component takes the other model (`components.html`). The base is still pending TZ §26.

## 10. Regenerate / adopt
`node render.cjs` re-renders `png/` (needs Playwright's Chromium; each PNG stays under 400 kB). To adopt after approval (not done): add `ornament.css`, swap `BrandMark` in `ui/Layout.tsx` for the simplified symbol (micro ≤ 24 px), build the intro and onboarding per `docs/design-plan-s37.md`, then apply corner/divider/header per screen. Product code, i18n and tests are untouched.

## 11. Open questions for the owner
1. Approve **A** as the Y signature (or choose B/C, or a hybrid with C's rhombus chain)?
2. OK to use the simplified A in the top bar and keep the existing small symbol for ≤ 24 px, with `../logo/` as master until you sign off?
3. Wordmark: the logo files use outlined **caps "YONDO"**, the app top bar writes "Yondo" in Space Grotesk. Which one is the brand (the intro uses the official caps)?
4. Allow the faint pattern field in the home hero and the gift header, or keep ornament to opening, onboarding, headers and dividers only?
5. Who does the cultural/native-designer review, and is "before public launch" acceptable?
6. Replace the favourites heart with a bookmark glyph to follow "no hearts"?
