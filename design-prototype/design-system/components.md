# YONDO component library

Source of truth: `tokens.json` / `tokens.css` (design tokens) → `components.css` (classes) → `prototype/src/components.js` (HTML-string helpers, `YC.*`). Live reference with all states: open `design-system/gallery.html` (regenerate with `node prototype/build.js`). The prototype is built from these same files, so every screen uses the library.

## Rules for every component
- Min touch target 44×44 px (buttons 48). Focus ring: 3 px `--c-focus` via `:focus-visible`. Programmatic-focus targets (`tabindex=-1`) show no ring.
- Colours only from tokens. Accent `#E8501A` is for graphics (≥3:1), never text; text accent is `--c-accent-text`.
- Motion: transform/opacity (path-draw for logo/check), 150–400 ms, `cubic-bezier(.22,1,.36,1)`, collapses to ~0 ms under `prefers-reduced-motion`.
- Motion map (S16): welcome logo draw + text stagger · login field shake on error, OTP field slides in · roles/role-screen lists stagger (`.list.st`) · buttons hover-lift (pointer only) / press-scale, auto spinner on `[aria-busy]` · icon buttons, chips, nav press · active nav tab top bar + icon bump · sheet slide + backdrop fade · alerts/empty/offline banner enter · timeline current-step pulse ring · payment check spring-pop then text · rating star pop. Spring easing `--ease-spring` only for success/star moments. Loops (`ring`, `sh`, `rot`) stop under reduced motion (`animation-iteration-count:1`).
- Uzbek copy uses ʻ (U+02BB) for oʻ/gʻ and ʼ (U+02BC) for tutuq.

| Component | Helper | Classes | States | A11y contract |
|---|---|---|---|---|
| Button | `Button(label,{a,variant,full,disabled,loading})` | `.btn` `.sec` `.danger` `.full` | default, :active, :focus-visible, disabled, loading | `aria-busy` while loading; `type=button` default; async actions auto-disable (no double submit) |
| Chip | `Chip(label,{on,a,disabled})` | `.chip` `.on` | off, on, disabled | `aria-pressed`; group wrapped in `role=group` + label |
| Tag / DEMO | `Tag()` `Demo()` | `.tg` `.demo` | static | non-interactive, no chip styling |
| Avatar | `Avatar(name,hue,'lg')` | `.av` `.big` | static | decorative (`aria-hidden`); no fake photos |
| Verified | `Verified(bool,{explicit})` | `.bdg` `.bdg.off` | verified / unverified | Rendered ONLY when backend `verified===true`. Unverified renders nothing in lists, neutral text in detail |
| Field | `Field(id,label,{value,err,hint,area,options,type…})` | `.fld` `.bad` `.err` | default, error, disabled | `<label for>`, `aria-invalid`, `aria-describedby` → hint/error |
| Alert | `Alert(kind,text,{title,rid,actions})` | `.alert` `.info/.success/.error/.unavailable` | 4 kinds | error/unavailable `role=alert`; info/success `role=status`; shows request id when present |
| Card | `Card(html,{a,up,col})` | `.card` | static / button | whole card is the hit area when `a` given |
| Status / Timeline | `Status()` `Timeline(steps,idx)` | `.stc` `.tl` | per booking status | `<ol>`, `aria-current=step` |
| Empty / Skeleton / Spinner | `Empty()` `Skeleton(n,h)` `Spinner()` | `.empty` `.sk` `.spin` | loading, empty | skeleton has sr-only “Yuklanmoqda”; Empty title is an `h2` |
| Navigation | `NavBar(items,activeId)` | `.nav` `.navi` | active | `<nav aria-label>`, `aria-current=page`, ≥56 px |
| Dialog / sheet | native `<dialog class="sheet">` + `dlg()` in app | `.sheet` `.in` `.gh` | open/closed | `showModal()`: inert background, Esc closes, Tab wraps, focus returns to opener; `aria-labelledby=dt` |
| Toast | `toast()` | `.toast` | on/off | `role=status` live region |
| Check / Logo | `Check()` `Logo(size,animate)` | `.ck` `.lg` | animated path-draw | `role=img` + label (logo) |

## Responsive variants
Container 480 px (<768), 640 px (≥768), 880 px (≥1024); lists become 2 columns at ≥768 (`.list.g2`). Dialog is a bottom sheet <768 px and centred ≥768 px. Verified at 360, 375, 390, 430, 768, 1024, 1440 px in headless Chromium (see `reports/test-report.md`).

## Using the library
```js
html = C.Card(C.Avatar('Madina',160) + '<b>Madina</b>' + C.Verified(card.verified), { a: 'open:' + card.id });
```
Wire behaviour through `data-a="action:arg"` (click) and `form[data-f="name"]` (submit); see `prototype/src/app.js`.
