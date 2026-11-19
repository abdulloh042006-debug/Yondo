# Yondo UI redesign, November 2026 (phase 1: design and specification)

**Status:** phase 1 deliverable (design + spec + prototype). No app code changes in this PR. Phase 2 (implementation in `apps/web` and `apps/mobile`) follows this document.
**Source brief:** `docs/tasks/2026-11-18-ui-redesign-brief.md`. **The owner's answers of 2026-11-18 override the brief** (CLAUDE.md §7, last line):

| Brief asked for | Decided (owner, 2026-11-18) | Used here |
|---|---|---|
| Warm dark palette `#110d0b` / `#1c1613` / `#302621`, oranges `#e86f38` `#ff7b3d` `#ff854d` | Keep the app's colours; new components use ink `#111111`, paper `#F5F2EC`, carrot `#E8501A` | Every brief hex is mapped in §5.2. No new hue except one red. |
| Red/crimson for destructive actions, red→orange gradient | Red **only** for dangerous/destructive actions | One red token, `--c-danger`, used only by the destructive zone and the hold button. Solid fill, no gradient. |
| Hold-to-Confirm for delete/block/cancel | Hold-to-Confirm (1.5 s) **replaces** the blurred confirmation dialog of 2026-11-15 | §4.4 |
| Biometric switch row | Not built: in-app Face ID was removed on 2026-11-16 | The Hisob screen has no biometric row; one line explains the phone's own password autofill. |
| Dark theme only | Both themes stay: `yondo` (day, default) and `yondo-tun` (night) | Every token, component and frame exists in both. |
| Motion everywhere | Every animation respects `prefers-reduced-motion` and stays cheap on low-end Android | Each component spec has a reduced-motion variant and a cost note. |

Product rules that shape the design (CLAUDE.md §4): Yondo is never a dating service (no romantic imagery or wording); `romantic` is shown as "Maxsus kunlar"; sample data carries a DEMO label; the verified badge only from the API's `verified: true`; carrot never carries small text (3.36:1 on paper).

**Contents:** 1 Screenshot analysis · 2 Screen-by-screen plan · 3 Navigation · 4 Component specs · 5 Design system · 6 Layout rules · 7 Prototype · 8 Phase 2 task list · 9 Open questions.

---

## 1. Screenshot analysis (current state)

**How captured.** `origin/main` at `b8cccd4` (includes #45: photos, likes, filters, card feed). The real FastAPI app on SQLite with the DEMO seed (`apps/web/e2e/server.py`); `apps/web` production build through `vite preview`; `apps/mobile` through `expo export --platform web`, served with an `/api` proxy. Viewport 360 × 780, device scale 2, signed in as the DEMO customer after the mandatory login + password setup. Images: `docs/design/redesign-2026-11/before/` (web: `NN-*.jpg`, mobile: `m-NN-*.jpg`, night theme: `yondo-tun-*.jpg`). Full-page web captures show the sticky header and dock where the viewport was at capture time; that overlap is a capture artefact, not a bug.

**Not reproduced:** the brief's "floating Telegram icon covering the Support title". No floating Telegram button exists on `main` at 360 px (web or mobile). The rule in §6 (floating buttons never overlap the App Bar) covers it if one is added later.

| Screen | File(s) | Problems |
|---|---|---|
| **Kashf** (Discover) | `before/03-kashf.jpg`, `04-kashf-filtrlar.jpg`, `05-kashf-kartochkalar.jpg`, `m-03-kashf.jpg` | The hero card (eyebrow, 3-line title, 3-line paragraph, search, separate "Qidirish" button) fills the first ~420 px. A second glass card holds "Filtrlar", a full Select for sort and the list/cards toggle. **No companion is visible above the fold at 360 × 780**: the first card starts at ~700 px. The category choice lives only inside the filter sheet, where 11 identical grey chips sit in rows. Cards: grey placeholder with a giant letter "D"; five small chips for rating, meetings, likes and services compete with the name; price is the last line. |
| **Sevimlilar** (empty) | `06-sevimlilar-bosh.jpg`, `m-04-sevimlilar.jpg` | Empty state is a card hugging the top, with a decorative orb; mobile is left-aligned text plus a wide black button. The page footer (Yordam, Sozlamalar, Terms, Privacy links) repeats on every page and pulls attention. |
| **Bronlar** | `07-bronlar.jpg`, `m-05-bronlar.jpg` | A 4-line notice in a carrot-bordered box starts the page. Every booking card carries 4–5 equal pills (Bekor qilish, Batafsil, Muammo haqida xabar berish, Bloklash, SOS) that wrap onto three lines; destructive actions sit next to "Batafsil" with the same weight. Mobile shows a stray "Qayta urinish" pill above the list. |
| **Bron tafsilotlari** | `08-bron-tafsilotlari.jpg`, `yondo-tun-08-…` | "← Bronlar" is a small text link under the header, separate from the title. Key-value rows are left-aligned labels with wrapped values; the time wraps to 3 lines. The To‘lov card says the same rule twice. Chat, Uchrashuv and Sharh are full cards, mostly explaining that they are not available yet. Safety actions are mixed with ordinary ones. |
| **Profil** (page title "Hisobim") | `09-profil-hisobim.jpg`, `m-07-profil.jpg` | Tab says "Profil", page says "Hisobim". The phone number is the page's name. Roles are a grey "Mijoz" line. The photos block has two paragraphs of rules before any photo. Missing gender shows "—". "Tahrirlash" is a large black primary button. Sozlamalar is a card at the bottom. |
| **Sozlamalar** | `10-sozlamalar.jpg` (5 900 px tall), `m-08*-sozlamalar*.jpg` | Language = 3 large cards, alphabet = 2 large cards, theme = 5 large cards: ~1 700 px of identical grey boxes before anything else. Hisob, Maxfiylik va xavfsizlik and Ilova haqida are folded into the same page; role chips, "Parolni almashtirish", "Chiqish" and "Hisobni o‘chirish" are identical outline pills, so deletion looks as harmless as sign-out. Mobile shows a developer message to users: "Veb-ilova manzili sozlanmagan (EXPO_PUBLIC_WEB_URL)". |
| **Hisob** (role, login) | inside `10-sozlamalar.jpg`, `m-08b-…` | "Men kimman" is two small chips with a long paragraph. The login is plain text. No visual link between the chosen role and what changes. |
| **Maxfiylik va xavfsizlik / Ilova haqida** | inside `10-sozlamalar.jpg`, `m-08c-…` | Normal links (Terms, Privacy, Yordam) and the destructive "Hisobni o‘chirish" share one style and one area. Version and legal notice are long text cards. |
| **Yordam / Qo‘llab-quvvatlash** | `11-yordam.jpg` (6 000 px), `m-09*-yordam*.jpg` | Six stacked cards, each with a paragraph. Trusted contacts show a full add form inline. Support: topic is a `<select>` (web) or same-looking chips (mobile); the textarea blends into the card; "Murojaat yuborish" is a small left-aligned button. |
| **Hamroh profili** | `12-hamroh-profili.jpg` | "← Orqaga" is a pill under the header; big grey photo placeholder; sticky "Bron qilish" bar overlaps the dock area. |
| **Bottom nav** | all | Works and is consistent (Kashf · Sevimlilar · Bronlar · Profil), but the active state is a pale carrot pill that reads weakly in the day theme; there is no motion tying tab and page together. |
| **Kirish** (not in brief) | `02-kirish.jpg`, `02b-parol-yaratish.jpg` | Out of scope here; listed for completeness. Same input contrast issue as Support. |

---

## 2. Screen-by-screen redesign plan

Frames: `docs/design/redesign-2026-11/prototype/kun-*.jpg` (day) and `tun-*.jpg` (night). The interactive version is `design-prototype/redesign/index.html` (§7).

### 2.1 Profil (`prototype/kun-profil.jpg`)
- **App Bar:** title "Profil"; actions: pencil (Tahrirlash) and gear (→ Sozlamalar). Remove the Sozlamalar card.
- **Header row:** 72 px avatar (photo, or initial on ink) with a 2 px carrot ring; name (for customers without a public name: the masked phone `+998 90 ••• •• 03`, the full number stays visible in Hisob); roles as badges ("Mijoz" solid, "Administrator" carrot-outline). Badge text is ink/paper, never carrot.
- **Rasmlarim:** a 3-slot grid (add tile + empty dashed slots), count "0 / 6", one support line; the long rules move behind the ⓘ icon (sheet).
- **Shaxsiy ma’lumotlar:** one grouped list, key left / value right (`justify-between`). A missing value is an outline "Ko‘rsatilmagan" badge, never "—".
- **Tezkor:** Bildirishnomalar (with unread count) and Yordam va xavfsizlik as list rows.
- Remove: the page footer links (they move to Sozlamalar → Ilova haqida / Maxfiylik).

### 2.2 Sozlamalar (`prototype/kun-sozlamalar.jpg`)
- Reached from the gear on Profil (and from Kirish when signed out, as today). App Bar with back.
- Three grouped lists instead of 13 cards:
  - **Ilova:** Til → row with the current value, opens a **bottom-sheet radio list** (O‘zbekcha / Русский / English). O‘zbek alifbosi → **segmented control** "o‘ g‘ sh ch · 1995 | ö ğ ş ç · 2026" inline (two options, always visible). Ko‘rinish → row, opens a **bottom sheet with swatches** (Yondo kunduzgi, Yondo tungi, Qurilma bo‘yicha; Gul / Jurnal / Stone in a "Boshqa mavzular" disclosure so they stay available). Bildirishnomalar → row.
  - **Hisob:** Hisob va rol → screen 2.3; Maxfiylik va xavfsizlik → screen 2.4.
  - **Yordam:** Yordam va qo‘llab-quvvatlash → 2.5; Ilova haqida (shows version) → screen.
- "Chiqish" as a ghost button at the end. Sign-out is not destructive (no red, no hold).
- The help text under Til ("Hisobingizga kirgan bo‘lsangiz…") moves into the language sheet.

### 2.3 Hisob va rol (`prototype/kun-hisob-hamroh.jpg`)
- **3D Aura Role Switcher** card (§4.2) for Mijoz / Hamroh with a one-line description per role. Behaviour is unchanged from today's "Men kimman" control: it switches between the roles the account already has, and the existing path to become a companion stays as it is. Only the visuals change.
- **Kirish** group: Login (value, read-only) and Parolni almashtirish (row → existing page).
- One support line: "Telefoningizning parol menejeri (Face ID / barmoq izi) kirish formasida o‘zi taklif qiladi." No biometric switch (removed 2026-11-16).
- "Chiqish" secondary button.

### 2.4 Maxfiylik va xavfsizlik + Ilova haqida (`prototype/kun-maxfiylik.jpg`, `kun-haqida.jpg`)
- Top: grouped rows (Shikoyatlar va ishonchli kontaktlar → Yordam; Bloklanganlar).
- **Hujjatlar:** Foydalanish shartlari, Maxfiylik siyosati as rows with an external-link icon.
- **Destructive zone at the bottom**, separated by 28 px and a red-tinted container: title "Hisobni o‘chirish", the consequence in one sentence (30 days, data erased or de-identified, can be cancelled meanwhile), then the **Hold-to-Confirm button** (§4.4). It replaces the blurred confirmation dialog. The pending state with "cancel deletion" after a request stays as today.
- Ilova haqida: symbol, slogan "Yondo doim yoningda", version, the two documents, the draft notice. Never show configuration messages (e.g. `EXPO_PUBLIC_WEB_URL`) to users: hide the row instead.

### 2.5 Yordam / Qo‘llab-quvvatlash (`prototype/kun-yordam.jpg`)
- App Bar "Yordam" with back.
- **Emergency card** (carrot border): "Hayot yoki sog‘liqqa xavf bo‘lsa", one line ("112 ga qo‘ng‘iroq qiling. Yondo favqulodda xizmat emas."), buttons "112 ga qo‘ng‘iroq" (primary) and SOS (carrot fill, ink bold label). Wording keeps the SOS rule: it never claims help was sent.
- **Rows:** Shikoyat yuborish (subtitle "Bron orqali", → Bronlar), Mening shikoyatlarim (count), Ishonchli kontaktlar (count; the add form moves to its own screen/sheet).
- **FAQ:** accordion rows (`<details>`), answers hidden until opened.
- **Support form card:** topic as **choice chips** (single-select radio group with a check mark; a different look from filter chips), a textarea with inner contrast, focus ring and a counter, then a **full-width primary** "Murojaat yuborish". One meta line under it: "Javob ilova ichida keladi." Remove the "response time not defined" paragraph from the form (keep it in the FAQ if needed).

### 2.6 Kashf (`prototype/kun-kashf.jpg`, `kun-kashf-chip-kino.jpg`, `kun-kashf-filtrlar.jpg`)
- App Bar: brand mark left, bell (with unread dot) right.
- **Compact header:** "Hamroh toping" (22 px) + one support line. The slogan eyebrow and the 3-line paragraph go.
- **Unified search:** pill input with a leading search icon; search runs on submit/debounce, so the separate "Qidirish" button goes. A square **filter button** (ink) opens the Filtrlar sheet (sort, minimum stars, city).
- **Bouncy Magnetic Category Chips** (§4.3) in one horizontal scroller directly under search: Hammasi, Kofe, Sayr, Kino, Shopping, Tadbir, Shahar do‘sti, Suhbat, O‘qish / Coworking (+ Onlayn suhbat, Maxsus tajriba; `romantic` = "Maxsus kunlar" if it is ever listed). Each has a line icon. The category leaves the filter sheet.
- **Results line:** "3 ta hamroh · Tavsiya" + an icon toggle for List / Cards (the #45 card feed keeps "Saqlash" / "Keyingisi"; no dislike, no match).
- **Companion card:** 4:3 photo (illustrated fallback, never a grey letter), heart (44 px target) top-right, verified badge on the photo **only when `verified: true`**; below: "DEMO Madina, 26" + price right-aligned ("45 000 so‘m / 30 daq"); one meta line with icons (city · ★ 4.9 · 12 uchrashuv · 👍 31); services as one text line. **Measured: the first card starts at 286 px** in the prototype (it was ~700 px).

### 2.7 Sevimlilar empty state (`prototype/kun-sevimlilar.jpg`)
- Centred, vertically balanced in the free space: a 112 px carrot-tinted circle with a dashed ring and a carrot line heart (graphic only), title "Hali sevimlilar yo‘q", one line, primary "Kashf qilish" (min 200 px wide, centred). Same pattern for every empty list (§5.8).

### 2.8 Bron tafsilotlari (`prototype/kun-bron.jpg`)
- App Bar: back (→ Bronlar) + title "Bron tafsilotlari" + "⋯" (secondary actions such as "Muammo haqida xabar" can also live here).
- **Summary card:** service icon tile, "Kofe", "DEMO Madina bilan", status badge (ink text, carrot dot/border; status meaning in words). Key-value rows with leading icons: Vaqt (one line, "20-noyabr, 21:18–22:18"), Joy, Narx, Rolingiz; values right-aligned and bold.
- **To‘lov info banner:** one line ("To‘lov hamroh bronni qabul qilgandan keyin ochiladi."), a carrot left rule (graphic), details behind "Batafsil" if needed. Pay button appears only for `accepted` (rule unchanged).
- **Uchrashuv group:** Chat, Uchrashuv bosqichi, Sharh as rows with their state on the right; unavailable rows are dimmed instead of explained in paragraphs.
- **Xavfsizlik:** "Muammo haqida xabar" (secondary) + SOS.
- **Xavfli amallar** zone at the bottom: "Bronni bekor qilish" and "Bloklash" as Hold-to-Confirm buttons (§4.4). Block goes through `booking_id` as today.

### 2.9 Bronlar list (`prototype/kun-bronlar.jpg`)
- Segmented control "Faol | Tarix" (if the API's status filter is used; otherwise a single list).
- Each booking is **one tappable card** → detail: service + status, time · duration, DEMO place, price right-aligned. **No action buttons on list cards**: cancel, report, block and SOS live on the detail screen (SOS stays reachable in one tap from the detail and from Yordam).
- The provider notice becomes a one-line banner at the end of the list.

### 2.10 Bottom navigation
- **Quantum Shockwave** dock (§4.1) on Kashf, Sevimlilar, Bronlar, Profil. Hidden on full-task screens (booking detail, payment, chat) where the App Bar back is the way out, so the hold zone and sticky actions are never covered.

---

## 3. Navigation

### 3.1 Hierarchy
```
Dock (top level)        Kashf ─────────── Sevimlilar ─── Bronlar ─────────── Profil
Level 2 (App Bar back)  Hamroh profili                   Bron tafsilotlari   Sozlamalar (gear) · Bildirishnomalar · Yordam
Level 3                 Bron yaratish                    To‘lov · Chat       Hisob va rol · Maxfiylik va xavfsizlik · Ilova haqida · Parol
Sheets (no route)       Filtrlar                                             Til · Ko‘rinish · Rasmlar haqida
```
- A **tab keeps its own stack**: Profil → Sozlamalar → Hisob keeps "Profil" active in the dock.
- Sheets are for picking a value; screens are for content with their own state.

### 3.2 Compact App Bar (replaces "← Orqaga", "← Bronlar" pills/links)
- Height 56 px, sticky, background = page colour at 86 % with a 14 px blur; a hairline appears only after the content scrolls under it.
- Left: back button 44 × 44 (chevron, `aria-label="Orqaga"`), only on level 2+. On a top-level tab the left side shows the brand mark (Kashf) or nothing.
- Title: 17 px Space Grotesk 600, one line, ellipsis. The page has **one** `<h1>`: the App Bar title (the large in-page heading goes, except Kashf's "Hamroh toping").
- Right: up to two 44 px icon actions (bell, pencil, gear, ⋯).
- Web: `history.back()` when the previous entry is in the app, else the parent route. Mobile: the stack in `nav.tsx`; Android hardware back does the same.

### 3.3 Names (one word per place)

| Place | Name everywhere (dock, App Bar, links) | Replaces |
|---|---|---|
| Profile tab | **Profil** | "Hisobim" page title |
| Account sub-screen | **Hisob va rol** | "Hisob" card in Settings, "Hisobim va shaxsiy ma’lumotlar" link |
| Settings | **Sozlamalar** | unchanged |
| Help | **Yordam** (App Bar), "Yordam va qo‘llab-quvvatlash" (row) | "Yordam va xavfsizlik" page title |
| Booking detail | **Bron tafsilotlari** | unchanged; "← Bronlar" link goes |

New i18n keys are listed in §8; existing keys are reused where the text stays.

### 3.4 Quantum Shockwave interaction in the brand palette
See §4.1. Summary: ink pill (day) / paper pill (night) with the opposite text; it shrinks into a **carrot** orb, flies to the target tab, expands with a spring; on arrival a carrot ripple, 8 carrot particles, a small 3D tilt of the dock and an icon bounce. Total 520 ms + 460 ms settle; navigation itself is immediate (the screen changes on tap, the animation runs on top).

---

## 4. Component specifications

Shared rules: animate only `transform`, `opacity` and (for the hold fill) `clip-path`; no animated `box-shadow`/`filter`/layout on low-end Android; reuse elements instead of creating them per tap; every component works with keyboard and screen readers; every component has a reduced-motion variant read from `prefers-reduced-motion` (web) and `AccessibilityInfo.isReduceMotionEnabled()` (mobile, already used in `apps/mobile/src/brand.tsx`).

### 4.1 Quantum Shockwave bottom navigation

| Property | Day (`yondo`) | Night (`yondo-tun`) |
|---|---|---|
| Container | floating, 12 px from the edges and bottom (plus safe area), height 64, radius full, `rgba(255,255,255,.86)`, 1 px `--c-line`, blur 18 px | `rgba(24,24,24,.90)`, 1 px `--c-line`, blur 18 px |
| Active pill | ink `#111111`, label + icon paper | paper `#F5F2EC`, label + icon ink |
| Inactive | ink icon + label 11/14 600 | paper icon + label |
| Orb / ripple / particles | carrot `#E8501A` (graphic) | carrot |
| Badge (unread) | carrot pill, ink 10 px bold digits (≥ 4.5:1) | same |

Brief → brand mapping: `rgba(24,19,16,.92)` → `--c-dock`; pill `#f5f2f0` → `--c-primary`; pill text `#110d0b` → `--c-on-primary`; orb `#ff854d` → carrot `#E8501A`.

**Timeline** (one Web Animations API group on web; `Animated`/Reanimated on mobile), T = 520 ms:

| Time | Pill | Orb (18 px carrot circle, glow is a static pre-blurred shadow) | Effects |
|---|---|---|---|
| 0–120 ms (0–23 %) | `scale(1,1)` → `scale(.22,.15)`, opacity → 0 at the source tab | appears at source centre, `scale(.3)` → `1` | – |
| 120–322 ms (23–62 %) | hidden, jumps to target x | travels to target centre, `cubic-bezier(.65,0,.35,1)` | – |
| 322–447 ms (62–86 %) | at target, `scale(.22,.15)` → `scale(1.06,1.04)`, opacity 1, spring `cubic-bezier(.34,1.56,.64,1)` | `scale(1)` → `1.6`, opacity → 0 | **arrival at 322 ms:** ripple, particles, tilt, bounce start together |
| 447–520 ms | settles to `scale(1)` | – | – |
| ripple 322–842 ms | – | – | one 40 px ring centred on the target, `scale(.2)` → `scale(dockWidth/40 × 1.1)`, opacity .9 → 0, clipped by the dock's rounded shape |
| particles 322–742 ms | – | – | 8 dots (5 px), angles `i·45° + 17°`, radius 22–32 px, `scale(1)` → `.2`, opacity → 0 |
| tilt 322–782 ms | – | – | dock `perspective(600px) rotateY(±4°) rotateX(5°)` → `rotateY(∓1.5°) rotateX(-1.5°)` → 0, sign = direction of travel |
| bounce 322–782 ms | – | – | active icon `translateY(-5px) scale(1.22)` → `(1px, .94)` → `(-1px, 1.04)` → rest |

- **State:** the page switches on tap, before the animation; the label colour of the target switches after 300 ms so it is never invisible on the old background. A second tap mid-flight cancels the running group and starts from the current tab.
- **Accessibility:** `<nav aria-label="Asosiy bo‘limlar">` with real links/buttons; active = `aria-current="page"`; focus ring 2 px `--c-fg`; tab targets ≥ 44 px. Unread count is in the accessible name ("Bildirishnomalar, 2 ta yangi").
- **Reduced motion:** no orb, ripple, particles, tilt or bounce. The pill is placed on the target at once and fades in over 120 ms. Label colours switch at once.
- **Cost:** 1 pill + 1 orb + 1 ripple + 8 particles exist once (11 compositor layers only during the 1 s burst; `will-change` set on them only). No layout per frame; geometry is read once per tap. Low-end Android (mobile): run on the native driver (`useNativeDriver: true`) or Reanimated worklets; if the device reports low RAM or the frame drops, skip particles and tilt (keep orb + pill).

### 4.2 3D Aura Role Switcher (Mijoz / Hamroh)

- **Structure:** card (radius 28, padding 16, 1.5 px border) → overline "Men kimman" → segmented control (`role="radiogroup"`, two `role="radio"` buttons) → description (`aria-live="polite"`, one line per role).
- **Thumb:** absolutely positioned pill under the selected option, moved with `transform: translateX()` and width, **spring `cubic-bezier(0.34, 1.56, 0.64, 1)` 320 ms**, soft inner highlight + 6/16 shadow (static).
  - Mijoz: thumb `--c-primary` (ink in day, paper at night), label `--c-on-primary`.
  - Hamroh: thumb **carrot `#E8501A`**, label **ink `#111111`** (5.0:1; the brief's white text on orange is 3.3:1 and is not used).
- **Card aura:** Mijoz: border `--c-line`, normal shadow. Hamroh: border `rgba(232,80,26,.5)`, extra glow `0 0 30px rgba(232,80,26,.15)`; 450 ms `--ease`. The glow change happens once per switch (not continuous), so animating the shadow is acceptable here; on low-end Android use a pre-rendered glow layer with opacity.
- **3D:** on switch the card does `perspective(700px) rotateX(4deg) translateY(-2px)` for 220 ms and springs back.
- **Description:** two stacked lines cross-fade (opacity + 6 px rise, 300 ms). Mijoz: "Hamroh topasiz, bron qilasiz va uchrashuvlarni kuzatasiz." Hamroh: "Profilingiz, xizmatlar va narxlaringizni boshqarasiz."
- **Keyboard:** Tab focuses the selected option; ←/→ (and ↑/↓) move the selection (roving tabindex).
- **Reduced motion:** thumb, border and text change instantly; no tilt.
- **Rule:** the switcher changes what the user sees, never what the server allows. Roles are enforced in the backend (owner, 2026-11-06); a role the account does not have keeps today's behaviour.

### 4.3 Bouncy Magnetic Category Chips

| State | Day | Night |
|---|---|---|
| Default | surface `#FFFFFF`, 1.5 px `--c-line`, ink 14/18 600, icon 18 px line | surface (paper 7 % on ink), 1.5 px `--c-line`, paper |
| Pressed (`:active`) | `scale(0.92)`, 80 ms | same |
| Selected (`aria-pressed="true"`) | **ink** fill, **paper** text, **carrot border**, `translateY(-2px) scale(1.04)`, glow `0 0 20px rgba(232,80,26,.35)` | **paper** fill, **ink** text, carrot border, same lift and glow (.40) |

Brief → brand: selected `#f5f2f0` bg / `#110d0b` text → `--c-primary` / `--c-on-primary` (so the selected chip is the high-contrast one in both themes); border `#ff7b3d` → carrot; glow `rgba(232,111,56,.35)` → `rgba(232,80,26,.35)`.

- **Spring:** transform transition 350 ms `cubic-bezier(0.34, 1.56, 0.64, 1)`; colours 200 ms.
- **Magnetic:** only for a fine pointer that can hover (`(hover: hover) and (pointer: fine)`): the chip follows the pointer by up to ±3 px x / ±2 px y (CSS variables `--mx/--my` in the same `transform`), and returns on leave. Touch gets the press bounce only (no per-frame JS on phones).
- **Behaviour:** single-select (Hammasi clears the rest); selecting scrolls the chip into view (`inline: center`); the list filters immediately. Height 40 px (touch target 44 with row padding). Icons: line SVGs from one set (coffee cup, walking person, film, bag, star, city, speech bubble, graduation cap, grid); no emoji (they render differently per phone).
- **Accessibility:** `role="group" aria-label="Xizmat turi"`; each chip a `<button aria-pressed>`; the label is the text, the icon is `aria-hidden`.
- **Reduced motion:** no lift, no bounce, no magnet; selected state = colours + border only.
- **Cost:** CSS transitions only; one `pointermove` listener on the row for desktop.

### 4.4 Hold-to-Confirm Destructive Button

Used for **Hisobni o‘chirish**, **Bloklash** and **Bronni bekor qilish**. Nowhere else.

- **Look (idle):** full width, height 52, radius full, 1.5 px border `--c-danger`, surface fill, label `--c-danger` 15/20 700. Sits inside a **destructive zone**: red-tinted container (`--c-danger-soft`, 1.5 px border at 40 % red) with a title and one consequence line, placed last on the screen and ≥ 20 px from other actions.
- **Red:** day `#B42318` (5.9:1 on paper; paper text on it 5.9:1), night `#FF6B5B` (6.7:1 on ink; ink text on it 6.7:1). The brief's red→orange gradient is **not** used: one solid red keeps "red = danger" unambiguous and carrot keeps its brand meaning.
- **Hold:** press (pointer down, or Space/Enter key down) starts the fill: a red layer revealed **left → right, 0 % → 100 %, 1.5 s, linear** (`clip-path: inset(0 100% 0 0)` → `inset(0 0 0 0)`; the brief's `width` animation is visually identical but triggers layout every frame, so `clip-path` is used). The label changes to **"Tasdiqlanmoqda…"**; the part of the label over the fill is drawn in `--c-on-danger` (a second label inside the fill layer), so it reads at every moment.
- **Complete:** at exactly 1 500 ms of continuous hold the action runs once; button shows "Bajarildi" (or the screen moves on); haptic tick on mobile where available (`navigator.vibrate` on web; mobile: optional `expo-haptics`, not a dependency today).
- **Early release** (pointer up/cancel/leave, key up, blur, app backgrounded): the fill retracts to 0 % in **0.25 s ease-out**, label returns, **nothing is executed**. Key auto-repeat is ignored.
- **Screen readers and other non-hold activation** (TalkBack/VoiceOver double-tap, switch control, voice; detected as a `click` that was not preceded by our own press): an inline **two-step confirmation** appears under the button ("Yo‘q" / "Ha, hisobni o‘chirish"), focus moves to "Ha…". It is never a one-tap action, and it is an equivalent path, not a weaker one.
- **Announcements** (`aria-live`): hint via `aria-describedby` ("Bosib turing yoki ikki marta tasdiqlang"); on start "Tasdiqlanmoqda. 1,5 soniya bosib turing."; on early release "Bekor qilindi. Amal bajarilmadi."; on completion the result text ("O‘chirish so‘rovi qabul qilindi").
- **Mobile (React Native):** `Pressable` with `onPressIn`/`onPressOut`, `delayLongPress` not used (own timer so release before 1.5 s is exact); `accessibilityRole="button"`, `accessibilityHint`, and `accessibilityActions=[{name:'activate'}]` → the same two-step confirm via `onAccessibilityAction`.
- **Reduced motion:** the fill advances in three steps (0.5 s each) instead of a smooth sweep, and retracts instantly; timing and rules are unchanged.
- **Errors:** if the API call fails, the button returns to idle and the error (chosen by the error `code`) shows under it; a 503 reads "unavailable", never "declined".

---

## 5. Design system

### 5.1 Typography (Space Grotesk for display, Manrope for text; both already bundled)

| Token | Use | Size / line | Weight | Font |
|---|---|---|---|---|
| `t-page` | Page heading (only Kashf's "Hamroh toping", empty-state titles may use `t-section`) | 22 / 28, −0.01 em | 600 | Space Grotesk |
| `t-section` | App Bar title, section and card titles | 17 / 24 | 600 | Space Grotesk |
| `t-title` | Row titles, form labels, card subtitles | 15 / 22 | 600 | Manrope |
| `t-body` | Body text, inputs, buttons (buttons 600) | 15 / 22 | 400 | Manrope |
| `t-support` | Supporting text | 13 / 18 | 400, `--c-muted` | Manrope |
| `t-meta` | Metadata, counters, hints | 12 / 16, +0.01 em | 500, `--c-muted` | Manrope |
| `t-overline` | Group labels | 11 / 16, +0.08 em, uppercase | 600, `--c-muted` | Manrope |

Rule: one page heading per screen, max two text sizes per card, no paragraph longer than two lines on a list screen (move detail behind ⓘ, a row or the FAQ).

### 5.2 Colour tokens

Existing web tokens (`apps/web/src/styles.css` `[data-theme='yondo' | 'yondo-tun']`) and mobile palettes (`apps/mobile/src/theme.tsx` `PALETTES`) stay; new tokens are **added**:

| Token | Day `yondo` | Night `yondo-tun` | Existing equivalent / note |
|---|---|---|---|
| `--c-bg` | `#F5F2EC` | `#111111` | existing |
| `--c-fg` | `#111111` | `#F5F2EC` | existing |
| `--c-muted` | ink 66 % on paper | paper 68 % on ink | existing (70 %); 66/68 % to keep ≥ 4.5:1 for 12 px meta |
| `--c-surface` | `#FFFFFF` | paper 7 % on ink | existing |
| `--c-surface-2` *(new)* | ink 5 % on paper | paper 11 % on ink | = existing `--c-chip` (alias) |
| `--c-line` | ink 14 % | paper 16 % | existing |
| `--c-line-strong` *(new)* | ink 34 % | paper 36 % | dashed slots, secondary button border |
| `--c-primary` / `--c-on-primary` | ink / paper | paper / ink | existing |
| `--c-accent` *(new)* | `#E8501A` | `#E8501A` | carrot, graphic only (dots, borders, orb, glow, SOS fill with ink label) |
| `--c-on-accent` *(new)* | `#111111` | `#111111` | text on carrot fills (5.0:1) |
| `--c-accent-soft` *(new)* | carrot 12 % | carrot 18 % | icon tiles, focus halo, empty-state art |
| `--c-glow` | carrot 35 % | carrot 40 % | existing `--c-glow: #e8501a` used with opacity |
| `--c-danger` *(new)* | `#B42318` | `#FF6B5B` | **only** destructive zone + hold button (owner, 2026-11-18). Replaces nothing: today `--bad` is collapsed to ink in Yondo themes |
| `--c-on-danger` *(new)* | `#F5F2EC` | `#111111` | text on the red fill |
| `--c-danger-soft` *(new)* | red 8 % | red 10 % | destructive zone background |
| `--c-dock` *(new)* | `rgba(255,255,255,.86)` | `rgba(24,24,24,.90)` | dock glass |
| `--c-scrim` | ink 44 % | black 60 % | existing (colour), opacity added |

Brief hex mapping: `#110d0b` → `--c-bg` (night) / `--c-fg` (day) = ink; `#1c1613` → `--c-surface` (night); `#302621` → `--c-line-strong`/`--c-surface-2` (night); `#f5f2f0` → paper `#F5F2EC`; `#e86f38`, `#ff7b3d`, `#ff854d` → carrot `#E8501A`; "red-600 → orange-600" → `--c-danger` solid.

**Status colours** (brief: pending / confirmed / destructive): pending = ink text + carrot border + carrot dot ("Javob kutilmoqda"); confirmed = ink text + strong grey border + ink dot ("Tasdiqlangan"); cancelled/expired = muted text, no border; destructive actions = `--c-danger`. Meaning is always in the words (owner rule 2026-10-22). Gul / Jurnal / Stone keep their own palettes; the new tokens get fallbacks there (`--c-accent: var(--c-primary)`, `--c-danger: var(--bad)`).

### 5.3 Spacing, radius, elevation
- 4-pt scale: 4, 8, 12, 16, 20, 24, 32. Page gutter 16. Between groups 24 (overline label 24 above, 8 below). Inside cards 16. Between rows 0 (hairline divider).
- Radius: 10 (icon tiles), 14 (inputs, small cards, choice chips), 20 (cards, groups), 28 (hero cards, aura card), full (buttons, chips, dock, search).
- Elevation: one shadow (`--shadow-1`) for cards; dock and sheets have their own. No nested cards: a card never contains a card; use a group with rows.
- Touch targets ≥ 44 × 44.

### 5.4 Buttons

| Variant | Use | Style |
|---|---|---|
| **Primary** | the one main action of a screen (Murojaat yuborish, Kashf qilish, Natijalarni ko‘rsatish, To‘lovga o‘tish) | `--c-primary` fill, `--c-on-primary` label, 48 px, full width in forms and sheets |
| **Secondary** | alternatives (Muammo haqida xabar, Keyingisi, Chiqish in Hisob) | surface fill, 1.5 px `--c-line-strong` border |
| **Ghost** | low-emphasis (Tozalash, Hammasini o‘qildi, Chiqish in Sozlamalar) | no fill; hover `--c-surface-2` |
| **Icon** | App Bar and card actions | 44 × 44 round, no fill |
| **SOS** | safety only | carrot fill, ink 700 label (not destructive, not red) |
| **Destructive hold** | delete account, block, cancel booking | §4.4 |

Press feedback: `scale(.97)` 120 ms (none under reduced motion). Disabled: 45 % opacity + `aria-disabled`, with the reason in text nearby.

### 5.5 Inputs
- **Text input / search:** fill `--c-surface-2`, 1.5 px `--c-line`, radius 14 (search: full, 48 px, leading icon at 14 px). Focus: border `--c-fg`, fill `--c-surface`, 4 px halo `--c-accent-soft`. Error: message below in text (code-based), border `--c-fg` 2 px + "!" icon (red is not used for form errors; red = destructive only).
- **Textarea:** same, min height 120, counter right-aligned under it (`t-meta`).
- **Segmented control:** 2–4 options that are always visible (alphabet, star minimum, Faol/Tarix, role). Track `--c-surface-2`, thumb `--c-primary`, spring 320 ms; `radiogroup` + arrow keys.
- **Bottom-sheet selector:** for 3+ options or options that need explanation (language, theme). Radio rows 52 px, grabber, scrim, Escape/back closes, focus returns to the row.
- **Switch:** 52 × 32, track `--c-line-strong` → `--c-primary`, knob springs; `<input type="checkbox" role="switch">`. For on/off settings only (e.g. a notification channel); not for actions.
- **Choice chips:** single/multi choice inside forms (support topic): radius 14, check mark when selected, `--c-fg` border. Visually different from category chips (pill + icon) and from filter tags.

### 5.6 Cards and components
- **Companion card** (§2.6), **booking card** (§2.9), **summary card** (§2.8).
- **Grouped list:** surface, radius 20, rows 52 px min with a 32 px icon tile, title, value right, chevron. Replaces the "card per setting" pattern.
- **Key-value row:** label left (muted, optional icon), value right (600). Long values wrap right-aligned.
- **Badges:** solid (role), carrot-outline (attention, count), outline-dashed (optional/missing), DEMO (outline 10 px bold).
- **Info banner:** surface-2, carrot left rule 3 px, ⓘ icon, one line.

### 5.7 Motion
- Page change: 280 ms fade + 6 px rise. Sheets: 320 ms slide up. Everything else: §4.
- Under reduced motion all of these become ≤ 10 ms; state changes still happen.

### 5.8 Empty states
Centred block in the free height: 112 px icon art (carrot-soft circle + dashed ring + line icon), `t-section` title, one `t-support` line, one primary button. Used for Sevimlilar, Bronlar (no bookings), Bildirishnomalar, Kashf with no results ("Bu turda hozircha hamroh yo‘q" + "Hammasini ko‘rsatish").

---

## 6. Layout rules (remove · simplify · group · move behind icons)

**Remove**
- The Kashf hero paragraph and slogan eyebrow; the separate "Qidirish" button.
- "← Orqaga" / "← Bronlar" pills and links (App Bar back instead).
- Action buttons on Bronlar list cards.
- The repeated page footer links on every screen (they live in Sozlamalar → Ilova haqida and Maxfiylik).
- "—" placeholders (use "Ko‘rsatilmagan" badge or hide the row).
- Configuration/developer text shown to users (`EXPO_PUBLIC_WEB_URL` message): hide the row.
- Repeated explanations (To‘lov said twice; the "Chat opens after…" paragraphs).

**Simplify**
- One heading per screen (App Bar title). Max two lines of supporting text per section.
- Settings choices: 10 cards → 1 segmented control + 2 rows with sheets.
- Booking time on one line ("20-noyabr, 21:18–22:18").
- Companion card meta in one icon line.

**Group**
- Settings into Ilova / Hisob / Yordam groups.
- Booking detail into Summary → To‘lov banner → Uchrashuv rows → Xavfsizlik → Xavfli amallar.
- All destructive actions of a screen into one destructive zone at the bottom, never next to primary actions.
- Help into emergency card → rows → FAQ → support form.

**Move behind icons**
- Sozlamalar → gear on Profil. Tahrirlash → pencil on Profil.
- Photo rules → ⓘ on Rasmlarim.
- Sort, stars and city → filter button next to search.
- List/Cards view → two-icon toggle.
- Secondary booking actions → "⋯" in the App Bar if the screen gets long.

**Floating elements:** nothing floats over the App Bar or the dock; floating buttons sit above the dock with 12 px gap and respect safe areas; full-task screens hide the dock.

---

## 7. Interactive prototype

- **File:** `design-prototype/redesign/index.html`, one self-contained file (189 KB; Space Grotesk and Manrope latin + latin-ext inlined from the repo's `@fontsource-variable` packages; no network, no external scripts). Source `design-prototype/redesign/src/prototype.html`; rebuild with `node design-prototype/redesign/build.mjs` after `npm ci` in `apps/web` (do not hand-edit `index.html`).
- **Open:** in any browser; on a desktop it shows a 360 × 760 phone; on a phone it fills the width. Controls above the phone: theme (Yondo kunduzgi / tungi), screen jump, "Kam harakat" (reduced-motion preview). URL parameters `?theme=yondo-tun&screen=bron&rm=1` work too.
- **Screens:** Kashf (list and card view, filter sheet), Sevimlilar (empty), Bronlar, Bron tafsilotlari, Profil, Sozlamalar (language and theme sheets), Hisob va rol, Maxfiylik va xavfsizlik, Ilova haqida, Yordam, Bildirishnomalar. All data is DEMO.
- **Components working:** dock shockwave (click or keyboard), aura role switcher (click or arrows), magnetic chips (filtering the DEMO list), hold-to-confirm on Bron tafsilotlari (cancel, block) and Maxfiylik (delete account), including Space/Enter hold and the two-step path.
- **Frames:** `docs/design/redesign-2026-11/prototype/` — `kun-*.jpg` (day), `tun-*.jpg` (night), `dock-1-orb.jpg` / `dock-2-arrive.jpg` / `dock-3-wave.jpg` (shockwave mid-flight), `kun-maxfiylik-hold.jpg` (fill at ~45 %), `kun-hisob-hamroh.jpg` (companion aura), `kun-kashf-chip-kino.jpg`, `kun-kashf-filtrlar.jpg`.

**Checks run on the prototype** (Playwright/Chromium, 360 px, both themes; script outside the repo): 23 / 23 PASS — fonts inlined and used; no horizontal scroll at 360; first companion card at 286 px (above the fold); chip `aria-pressed` and `translateY(-2px) scale(1.04)`; dock `aria-current` moves and the pill settles on the target; dock works with Enter; gear opens Sozlamalar; aura border `rgba(232,80,26,.5)` + glow in Hamroh mode and arrow keys switch back; hold shows "Tasdiqlanmoqda…", early release cancels, 1.5 s completes, Space hold works and early Space release cancels, aria-live announces, non-hold activation opens the two-step confirm; red appears only inside destructive zones; reduced motion: no orb and pill already on target; **0 network requests; 0 page errors**. Not run: real iOS/Android devices, screen readers (VoiceOver/TalkBack), a low-end Android frame-time measurement — these are phase 2 checks.

---

## 8. Phase 2 implementation guidance (task list)

Order matters: tokens first, then shared components, then screens. One PR or a few small sequential PRs; each with a verifier APPROVE, tests, 360 px screenshots and an APK link (CEO). Merge `origin/main` first (includes #44).

**A. Tokens and primitives**
1. `apps/web/src/styles.css`: add the new tokens of §5.2 to `[data-theme='yondo']` / `[data-theme='yondo-tun']` (and fallbacks in `:root` for Gul/Jurnal/Stone); add type classes `t-page … t-overline`; button variants (`.btn.secondary`, `.btn.ghost`, `.btn.sos`); `.group/.list-row/.kv`; inputs focus halo. Keep existing class names working.
2. `apps/mobile/src/theme.tsx`: add `accent, onAccent, accentSoft, danger, onDanger, dangerSoft, surface2, lineStrong, dock` to both `PALETTES`; `FONT` sizes from §5.1.
3. i18n (`apps/web/src/i18n/{uz,ru,en}.ts`, uz in 2026 spelling): new keys, e.g. `nav.back`, `profile.title` ("Profil"), `settings.group.app|account|help`, `account.screenTitle` ("Hisob va rol"), `role.desc.customer|companion`, `hold.hint`, `hold.confirming` ("Tasdiqlanmoqda…"), `hold.cancelled`, `hold.yes`, `hold.no`, `danger.zone`, `discovery.title` ("Hamroh toping"), `discovery.subtitle`, `discovery.count`, `empty.favorites.*`, `help.emergency.*` (reuse existing texts where they exist). Remove the user-facing `mobile.webMissing` row (hide instead).

**B. Shared components (web `apps/web/src/ui/`, mobile `apps/mobile/src/`)**
4. `AppBar` — web: new `ui/AppBar.tsx` used by pages; `ui/Layout.tsx` header becomes the App Bar host (brand on top-level, back on nested). Mobile: `ui.tsx` `Screen` gets `title`, `back`, `actions` props; `nav.tsx` stack drives back.
5. `ShockwaveDock` — web: replace the dock in `ui/Layout.tsx` (`.dock`, `nav-pill` layoutId) with the §4.1 component (Web Animations API, reduced-motion branch via `ui/motion.tsx`). Mobile: dock in `nav.tsx`/`App.tsx` with `Animated` native driver; reduced motion via `AccessibilityInfo` (pattern in `brand.tsx`). Unit test: `aria-current` + reduced-motion path places the pill without animation.
6. `RoleSwitcher` (aura) — web `ui/RoleSwitcher.tsx`, mobile `ui.tsx`; wraps the existing "Men kimman" logic from `pages/Settings.tsx` / `screens/Settings.tsx` unchanged.
7. `CategoryChips` — web `ui/CategoryChips.tsx`, mobile replaces `Chip`/`ChipGroup` use in `screens/Discover.tsx`; categories from `lib/labels.ts` (`SERVICE_LABELS`), icons in one `ui/icons.tsx`.
8. `HoldToConfirm` — web `ui/HoldToConfirm.tsx`, mobile `ui.tsx`; tests: early release does not call `onConfirm`; 1.5 s hold (fake timers) calls it once; key hold; non-hold click opens the two-step confirm; aria-live text.
9. `Segmented`, `Switch`, `SheetSelect`, `ChoiceChips`, `GroupedList/ListRow`, `KeyValue`, `EmptyState`, `InfoBanner` — web `ui/form.tsx` + new files; mobile `ui.tsx` (`Sheet`, `MenuRow`, `Banner` already exist: restyle, don't duplicate).

**C. Screens**
10. Kashf — web `pages/Discovery.tsx` (+ `CardDeck.tsx`, `companionParts.tsx`), mobile `screens/Discover.tsx`, `CardDeck.tsx`, `companion.tsx`: compact header, unified search, chips, filter sheet without category, new card.
11. Sevimlilar — `pages/Favorites.tsx`, `screens/Favorites.tsx`: EmptyState.
12. Bronlar — `pages/Bookings.tsx`, `screens/Bookings.tsx`: tappable cards, no inline actions, one-line banner.
13. Bron tafsilotlari — `pages/BookingDetail.tsx`, `screens/BookingDetail.tsx`, `ui/ReportDialog.tsx`: App Bar, summary + KV rows, banner, rows, destructive zone with HoldToConfirm for cancel and block (same API calls; block via `booking_id`).
14. Profil — `pages/Account.tsx` (route `/account`, title "Profil"), `screens/Profile.tsx`/`Account.tsx`, `MyPhotos.tsx`: header with badges, photo grid, KV, gear/pencil.
15. Sozlamalar / Hisob va rol / Maxfiylik / Ilova haqida — split `pages/Settings.tsx` into the grouped list + sub-routes (`/settings/account`, `/settings/privacy`, `/settings/about`) on web; mobile `screens/Settings.tsx` into stack screens. Language/theme sheets reuse `i18n/LanguagePicker.tsx` and `ui/theme.tsx`.
16. Hisobni o‘chirish — `pages/DeleteAccount.tsx`, mobile deletion in `screens/Settings.tsx`: HoldToConfirm replaces the blur dialog (owner); keep the pending/cancel state; update `DeleteAccount.test.tsx`.
17. Yordam — `pages/Help.tsx`, `screens/Help.tsx`, `ui/Sos.tsx`: emergency card, rows, FAQ accordion, support form with ChoiceChips + full-width primary.

**D. Checks per PR**
- web: `npm run typecheck`, `lint`, `vitest` (update tests that look for old texts/roles), `build`; e2e `node e2e/run.mjs` (selectors for "← Orqaga", "Hisobim" change); axe on changed pages.
- mobile: `npx tsc --noEmit`, smoke, `expo export --platform web` and android; APK via the existing build route.
- 360 px screenshots of every changed screen in both themes; reduced-motion run; low-end Android check (dock and hold at 60 fps or degrade).

---

## 9. Open questions for the owner

None blocking. Two small points are decided here by default and can be changed later without rework:
- Customers without a public name are shown by a **masked phone** on Profil (the full number stays in Hisob). Default: masked.
- The Bronlar "Faol | Tarix" split is used only if the API's status filter gives it; otherwise one list.
