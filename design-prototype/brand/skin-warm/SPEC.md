# Yondo skin "iliq" (warm, direction R): spec + assets (design agent, proposal; nothing applied to apps/web)
Direction R chosen by the owner, E rejected. Only ink #111111 / paper #F5F2EC / carrot #E8501A (+ ink/paper mixes). Carrot = graphic only, never small text.

## 1. Tokens (variable names exactly as styles.css/theme.tsx; same keys as `yondo`/`yondo-tun`)
Ids: `yondo-warm` ("Yondo · iliq"), `yondo-warm-tun` ("Yondo · iliq tun"); `chrome` = #f5f2ec / #111111 (= `--c-bg`, theme.test.tsx rule). Swatch day `linear-gradient(135deg,#fff 50%,#f5f2ec 50%)`.
```css
[data-theme='yondo-warm'], [data-theme='yondo-warm-tun'] {
  --c-glow: #e8501a; --ok: var(--c-fg); --warn: var(--c-fg); --bad: var(--c-fg);
  --f-display: 'Manrope Variable', 'Manrope', system-ui, sans-serif;   /* Manrope is already bundled */
  --f-sans: 'Manrope Variable', 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --r-sm: 16px; --r-md: 22px; --r-lg: 30px;                           /* softer than 14/20/28 */
}
[data-theme='yondo-warm'] {
  --c-bg: #f5f2ec; --c-fg: #111111; --c-muted: color-mix(in oklab, #111111 70%, #f5f2ec);
  --c-surface: #ffffff; --c-primary: #111111; --c-on-primary: #f5f2ec;
  --c-line: color-mix(in oklab, #111111 14%, #f5f2ec); --c-chip: color-mix(in oklab, #111111 6%, #f5f2ec);
  --c-scrim: #111111; --c-on-media: #f5f2ec; color-scheme: light;
}
[data-theme='yondo-warm-tun'] {
  --c-bg: #111111; --c-fg: #f5f2ec; --c-muted: color-mix(in oklab, #f5f2ec 70%, #111111);
  --c-surface: color-mix(in oklab, #f5f2ec 7%, #111111); --c-primary: #f5f2ec; --c-on-primary: #111111;
  --c-line: color-mix(in oklab, #f5f2ec 16%, #111111); --c-chip: color-mix(in oklab, #f5f2ec 10%, #111111);
  --c-scrim: #000000; --c-on-media: #f5f2ec; color-scheme: dark;
}
/* proposed for the new skin only: field border >= 3:1 (see table) */
[data-theme^='yondo-warm'] .input, [data-theme^='yondo-warm'] select.input, [data-theme^='yondo-warm'] textarea.input {
  border-color: color-mix(in oklab, var(--c-fg) 55%, var(--c-surface)); }
```
Differences from `yondo`: Manrope instead of Space Grotesk, rounder radii, white surface + warm tile logo, rhombus-accent icons, field border fix. Colours are otherwise the same, by owner rule.

**Computed WCAG 2.x contrast** (oklab mixes resolved to sRGB, then ratio): 
| Pair | Day | Night | Use |
|---|---|---|---|
| fg / bg | 16.90 | 16.90 | text |
| fg / surface | 18.88 | 15.05 | text on cards |
| muted / bg (#4c4b4a / #a8a6a2) | 7.79 | 7.77 | hints |
| muted / surface | 8.70 | 6.92 | hints on cards |
| on-primary / primary | 16.90 | 16.90 | buttons |
| focus ring (primary 85 % + white) / bg | 12.15 | 17.18 | `:focus-visible`, needs 3 |
| line (#d1cec9 / #2f2e2e) / bg | 1.40 | 1.39 | decorative hairline only (not a UI boundary) |
| field border today (fg 22 %) / surface | 1.74 | 1.76 | FAILS 1.4.11 (3:1) |
| field border proposed (fg 55 % on surface) | 4.88 | 4.89 | PASS |
| carrot / bg, / surface | 3.36 / 3.75 | 5.03 / 4.48 | graphic only (>= 3 PASS); NEVER small text on day |
| ink on carrot fill | 5.03 | 5.03 | text on carrot chips PASS |

## 2. Skin mechanism
`skin` = `{ id, label, themes:{day,night}, iconSet, lockup, appIconDefault, chrome }`. Two skins: `warm` (themes yondo-warm/-tun, iconSet `yw-*`, lockup `warm`, default icon `kartochka`) and `classic` (= today's yondo/yondo-tun, current icons, current mark, default icon = current app-icon.svg). Day/night stays an independent switch inside a skin. Gul/Jurnal/Stone remain legacy themes (no skin).
Settings, group "Köriniş": (1) **Köriniş uslubi**: 2 preview tiles (mini login: lockup, 4 icons, button), selected = 2.5 px ink border + check, radio semantics; changing it swaps tokens, icon sprite, lockup and `theme-color` at once. (2) **Ilova belgisi** (optional, "Standart" = skin default): 4 tiles from `app-icons/*.svg`, label under each; helper text states the installed-app limit. Saved like `yondo.theme` (localStorage) and, once the account has a UI-prefs field, to the account. Nobody is forced: default = classic until the owner decides.
Mock: `png/skin-board.png`. Icon swap: one `<Icon name>` component reading `<use href="#yw-name">` or the classic path; today's code has 3 hand-copied paths, so this is a small refactor.

## 3. Honest platform limits
- Web: favicon, `apple-touch-icon`, `theme-color` follow the choice live (JS). Installed PWA / home-screen icon is fixed at install time (manifest read once; iOS caches the touch icon). See `app-icons/manifest-snippets.md`.
- Native later (apps/mobile is a stub): iOS alternate icons via `setAlternateIconName` (needs each PNG set in the asset catalog, user sees a system alert); Android = one `activity-alias` per variant (switching can restart/kill the app on some launchers) + adaptive icon (foreground inside the 66 dp safe zone; our masters keep art inside the 80 % circle) + monochrome layer for themed icons.

## 4. Accessibility
Icons are decorative (`aria-hidden`) next to a text label; icon-only buttons (heart, close) need `aria-label`/`aria-pressed`. Heart on/off must differ by fill AND `aria-pressed`, not hue. Picker tiles = radio group with visible label; do not rely on the check alone. Skin swap uses the existing `data-theme-switching` guard; animations respect `prefers-reduced-motion`. Sprite uses `currentColor`, so forced-colors/high contrast recolours it (untested). Min targets stay 44-48 px.

## 5. Implementation impact (apps/web, no edits made)
`ui/theme.tsx` (THEMES + skin bundles, chrome, saved id, test list); `ui/theme.test.tsx` (chrome == `--c-bg`); `styles.css` (add the blocks above; the existing `[data-theme^='yondo']` rules WILL also match `yondo-warm*` (danger, tags, toast, banner, media: wanted), but the aurora/glass rules use the exact `[data-theme='yondo']`/`'yondo-tun'` selectors and will NOT apply: add the new ids or switch to `^=`+night modifier); `ui/Layout.tsx` (ICONS paths -> `<Icon name>`, BrandMark -> lockup per skin), `pages/companionParts.tsx:113` heart, `pages/Account.tsx:95` user, `ui/feedback.tsx:53` check; `public/` (copy icons + 4 manifests); `index.html` (head tags become dynamic); i18n keys in uz/ru/en (`skin.*`, `appicon.*`); Settings page. Pre-existing, non-blocking: field border ~1.7:1 in every theme (fix proposed here for the new skin only).

## 6. Open questions (recommended answer first)
1. Default skin for new users? Rec: classic until warm passes owner review, then warm.
2. Save the icon choice on the account? Rec: local only now, account later with `ui_locale`-style field.
3. Replace text glyphs (star, close, arrow) with the extra icons? Rec: yes, same PR.
4. Keep `Naqsh` pattern (<= 11 % ink)? Rec: yes; pattern field rule is limited to hero/gift, but app icons are not UI.
5. Install-time wording of the limit? Rec: "Ilova o'rnatilgan bo'lsa, belgi qayta o'rnatganda yangilanadi."

## 7. Icon language, variants, files
Icons: stroke 1.75 (was 1.8), larger radii, arched door on home, rounder heart, one filled rhombus (girih tip) on cal/shield/gift only; heart stays a heart. App icons: Oq kartochka (paper + white tile), Siyoh (ink), Karrot (carrot ground, ink Y, paper node 3.36), Naqsh (paper + faint star lattice <= 11 %, faded away from the Y). 16/32 px legibility (rendered, Playwright inline SVG): stem vs ground at 32 px 19.0 / 16.9 / 5.1 / 17.0, at 16 px 12.1 / 12.0 / 4.3 / 11.2 (the stem is under 1 px at 16 px, so 16 px reads as a blob: use symbol only, tab icons use the simple strap). Mono variants of siyoh/karrot/naqsh are the same silhouette (kartochka adds a tile outline).
Files: `icons/{warm-icons.svg,names.json,preview.html}`, `app-icons/*`, `lockups/lockup-{horizontal,stacked}-{light,dark}.svg` (min: horizontal 96 px wide, stacked 72 px wide, symbol alone 16 px; wordmark path copied unchanged), `png/{icons-day,icons-night,skin-board}.png`. App-icon PNGs (512/192/180/32) sit in `app-icons/` and are not counted in the 10-PNG limit of `png/`.

## 8. Honesty
Craft-inspired: girih star nodes (approved concept A), arched door (Registan-style portal), lattice. Own abstraction: rhombus accent, tile, all icon geometry. Not tested: real devices/home screens, forced-colors, screen readers, iOS/Android masks (only the 80 % safe-zone geometry). A native-designer review and a trademark-similarity check precede public launch.
