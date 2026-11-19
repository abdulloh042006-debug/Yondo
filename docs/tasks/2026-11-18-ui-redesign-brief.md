# Queued task: premium UI/UX redesign (owner brief, 2026-11-18)

**Status: QUEUED, not started.** The owner sent this brief on 2026-11-18 and said: "Yangi vazifa bor keyin. Boshlash uchun saqlab qo'y" ("a new task for later; save it to start"). Start it only after the two tasks running now (photos/likes/filters/cards UI; the notification sound) and only on the owner's word.

**Owner answers (2026-11-18), these override the brief:**
- **Colours:** keep the whole app's colours. Map the new components onto the Yondo brand palette: ink, paper and carrot `#E8501A`. **Red is allowed only for dangerous (destructive) actions.** The brief's `#110d0b`/`#e86f38`/`#ff7b3d`/`#ff854d` values are therefore NOT adopted.
- **Account deletion:** the **1.5 s Hold-to-Confirm button REPLACES** the blurred confirmation dialog of 2026-11-15 (#35).
- **Biometric toggle:** not built (in-app Face ID was removed on 2026-11-16, #43).

**CEO notes: points to settle with the owner before starting** (1–3 are answered above). These are conflicts with earlier owner decisions recorded in CLAUDE.md §7:
1. **Colours.** The brief uses a warm dark palette: `#110d0b`, `#1c1613` and `#302621`, orange `#e86f38` / `#ff7b3d` / `#ff854d`, red for destructive actions, and a red-to-orange gradient. The brand rule of 2026-10-22 allows only ink `#111111`, paper `#F5F2EC` and carrot `#E8501A`, with no other hue. Status colours collapse to ink plus a carrot border. There are two themes, `yondo` (day, the default) and `yondo-tun` (night). Ask: adopt the brief's palette as a new dark theme, or map it onto ink/paper/carrot?
2. **Destructive actions.** The brief asks for Hold-to-Confirm (1.5 s). On 2026-11-15 the owner asked for equal buttons plus a blurred confirmation dialog for account deletion (#35). Ask: replace the dialog, or use both (hold inside the dialog)?
3. **Biometric toggle (brief §5, screen 3).** This is obsolete: the owner removed in-app Face ID on 2026-11-16 (#43). The phone's own autofill handles it.
4. **Motion.** The Quantum Shockwave nav, particles, 3D tilt and bounce must respect `prefers-reduced-motion` (CLAUDE.md §7, motion rule). They must also stay cheap on low-end Android.
5. **Product rules (§4) still apply:** never dating wording; `romantic` shows as "Maxsus kunlar"; DEMO labels; carrot is never small text.
6. **Scope.** This covers web and mobile together (owner rule: the mobile app matches the web). Deliverables 1–6 can be a design doc. Deliverable 7 (prototype) fits `design-prototype/`, or is built directly in `apps/web` + `apps/mobile` behind the usual tests.

---

# YONDO — COMPLETE PREMIUM UI/UX REDESIGN

## Role

Act as an Expert UI/UX Designer and Mobile Product Design Specialist.

I am developing a companion/networking mobile app called **Yondo** for the Uzbek market. I have attached screenshots of the current UI.

The current design is functional but feels too basic, cluttered, and amateurish. It lacks a premium, modern feel.

My goal is to completely revamp the UI/UX based on modern mobile design principles (Material Design 3 / Apple Human Interface Guidelines).

The app uses a dark theme (`#110d0b` base background, `#1c1613` elevated surfaces, `#f5f2f0` warm white contrast, and `#e86f38` / `#ff7b3d` warm orange accents).

Your task is to provide a comprehensive, screen-by-screen UX/UI redesign strategy based on the attached screenshots and the exact requirements below.

---

## PART 1 — CORE UI/UX REDESIGN

### 1. Navigation & Hierarchy

The "Settings" section currently takes up a massive block on the Profile page.

- Move **Settings** to a simple gear icon (`⚙️`) in the top-right corner of the Profile screen to save space.
- The gear icon should open the Settings screen.
- Remove unnecessary space occupied by the current Settings section.
- Similarly, the `<- Back` buttons (`<- Orqaga`, `<- Bronlar`) are rendered as full cards/pills below the header, wasting vertical space.
- Integrate back navigation into a proper, compact top App Bar alongside the screen title.
- Unify naming mismatches (e.g., bottom tab says "Profil" while page heading says "Hisobim").
- Establish a consistent navigation hierarchy across all screens.

### 2. Overuse of Cards & Chips

Everything (languages, alphabets, themes, user roles, support topics, categories) is displayed as identical grey chips/buttons inside grey cards.

This creates visual monotony and bad contrast.

- Redesign these elements using appropriate component types (segmented controls, bottom-sheet selectors, compact list rows, interactive chips) and clear visual hierarchy.
- Do not represent every selectable element using the same grey card or chip style.

### 3. Cluttered Elements & Text-Heaviness

Pages like "Profile", "Support", "Booking Details", and the main "Discover" (Search) screen have too much explanatory text.

For example, the "Discover" screen has a huge title and paragraph that pushes the actual content (user cards) down below the fold.

- Reduce unnecessary explanatory text.
- Make headings compact and properly sized.
- Prioritize the actual content (companion cards, key booking metadata, quick actions).
- Improve spacing, key-value alignment (`justify-between`), and visual hierarchy.
- Ensure important information is visible without excessive scrolling.

### 4. Poor Action Button Differentiation

Primary actions (like "Search" or "Submit Request"), secondary actions, and destructive actions (like "Cancel Booking", "Delete Account", "Block") all look identical or inconsistently left-aligned.

Redesign the button hierarchy:

**Primary actions:**
- Prominent.
- Full-width where appropriate.
- High-contrast warm white (`#f5f2f0`) or brand orange (`#e86f38`) with clear visual weight.

**Secondary actions:**
- Visually quieter (subtle surface fill or clean border).
- Clearly differentiated from primary actions.

**Destructive actions:**
- Isolated from ordinary actions.
- Color-coded (red/crimson accents).
- Visually communicate the consequences of the action and use the required Hold-to-Confirm interaction.

### 5. Form & Input UI

Input fields (like the search bar and support message text area) blend into the background.

- Redesign input fields to be visually distinguishable with inner contrast, subtle borders, leading icons, and clear focus states.
- Replace raw placeholder dashes (`—` for missing Gender) with cleaner empty states or optional badges.
- Toggles for biometric login (`Face ID / barmoq izi bilan kirish`) are currently implemented as large buttons instead of simple switch toggles. Replace these with proper iOS/Material switch controls.

---

## PART 2 — ADVANCED INTERACTIVE UI COMPONENTS

Implement the following **four specific interactive components** as mandatory parts of the Yondo redesign:

### 6. 3-in-1 "Quantum Shockwave Contrast" Bottom Navigation Bar

Implement a 3-in-1 **"Quantum Shockwave Contrast"** bottom navigation bar for the 4 main tabs (*Kashf, Sevimlilar, Bronlar, Profil*).

**Visual Design:**
- Floating glassmorphic dark container (`rgba(24, 19, 16, 0.92)`, rounded-full).
- High-contrast warm white active pill: `#f5f2f0`
- Dark active text and icon: `#110d0b`
- Glowing orange quantum orb (`#ff854d`) during transitions.

**Tab Change Animation:**
On tab change:
1. Shrink the white active pill into a glowing orange quantum orb.
2. The orb must scale down to `0.22` (`scale(0.22, 0.15)`).
3. Shoot the orb across toward the target tab.
4. Expand it back to its full pill size upon arrival.

**Shockwave Arrival Effect:**
Upon arrival, simultaneously trigger:
- A container-wide radial **Shockwave Ripple** expanding from the active tab.
- A burst of **8 glowing orange micro-particles** around the active icon.
- A **3D physics tilt** on the navbar container and a springy keyframe **bounce animation** on the active icon.

The transition must combine all three effects into one coordinated navigation interaction.

### 7. 3D Aura Role Switcher

Implement a **"3D Aura Role Switcher"** card for switching between:
- **Mijoz** (Client)
- **Hamroh** (Companion)

**Segmented Control:**
Use a segmented control pill. The sliding background must morph between:
- **Client mode:** Warm white (`#f5f2f0`) with dark text (`#110d0b`).
- **Companion mode:** Vibrant orange (`#e86f38`) with white text (`#ffffff`).
- Use spring physics with the following easing: `cubic-bezier(0.34, 1.56, 0.64, 1)`

**Parent Card Animation:**
When switching roles:
- Dynamically update the parent card's border.
- Dynamically update its ambient `box-shadow` glow.
- When Companion mode is active, apply a warm orange border (`rgba(232, 111, 56, 0.5)`) and ambient orange glow (`0 0 30px rgba(232, 111, 56, 0.15)`).
- Smoothly transition the helper description text to explain the active role concisely.

The role switcher must feel dimensional, fluid, and premium.

### 8. Bouncy Magnetic Category Chips

Implement **"Bouncy Magnetic Category Chips"** for the Discover (*Kashf*) screen (*Hammasi, Kofe, Sayr, Kino, Shopping, Tadbir, Shahar do'sti, Suhbat, O'qish / Coworking*).

**Default State:**
Replace flat grey chips with interactive pill buttons containing:
- A relevant emoji or vector icon.
- A category label.

**Press Interaction:**
- On press (`:active`): `scale(0.92)`

**Selected State:**
When selected (`.active`), apply:
- Spring transition using `cubic-bezier(0.34, 1.56, 0.64, 1)`.
- Warm white background: `#f5f2f0`
- Dark text: `#110d0b`
- Orange border: `#ff7b3d`
- Upward lift: `translateY(-2px) scale(1.04)`
- Warm orange glow shadow: `0 0 20px rgba(232, 111, 56, 0.35)`

Category chips should feel responsive, magnetic, and satisfyingly bouncy.

### 9. Hold-to-Confirm Destructive Button

Implement a **"Hold-to-Confirm Destructive Button"** for dangerous actions:
- **Hisobni o'chirish** (Delete Account)
- **Bloklash** (Block User)
- **Bekor qilish** (Cancel Booking)

**Interaction Requirements:**
Require the user to press and hold the button for **exactly 1.5 seconds** to prevent accidental taps.

**Holding Animation:**
While holding:
- Fill the button background from left to right.
- Animate width from `0%` to `100%`.
- Duration: `1.5s`, Timing: `linear`.
- Use a red-to-orange gradient (`from-red-600 to-orange-600`).
- Change the button label to `"Tasdiqlanmoqda..."` (`Confirming...`).

**Early Release:**
If the user releases the button before completing the 1.5-second hold:
- Cancel the confirmation.
- Smoothly retract the fill bar back to `0%` (`0.25s ease-out`).
- Do not execute the destructive action.

Only execute the action after the full hold duration has completed.

---

## PART 3 — SCREEN-BY-SCREEN REDESIGN STRATEGY

Based on the attached screenshots, provide specific redesign recommendations for each screen. For every screen, explain what to remove, redesign, group differently, or hide behind icons, and how the layout hierarchy and interactive components should work:

1. **Profile (`Hisobim` / `Profil`):** Move Settings behind the top-right gear icon (`⚙️`), convert roles (`Administrator, Mijoz`) into styled badges, align personal info key-values (`Yosh`, `Jins`, `Shahar`) properly, and move "Edit" (`Tahrirlash`) to a compact icon or header action.
2. **Settings (`Sozlamalar`):** Reduce excessive chips for Language, Uzbek Alphabet, and Theme; use clean segmented controls or bottom-sheet selectors with leading icons.
3. **Account (`Hisob`):** Integrate the **3D Aura Role Switcher** for *Mijoz / Hamroh*, clean up Login/Password actions, and replace the giant Biometric button with a standard Switch toggle row.
4. **Privacy & Security (`Maxfiylik va xavfsizlik` & `Ilova haqida`):** Separate normal settings and external legal links from destructive account actions; apply the **Hold-to-Confirm Destructive Button** for account deletion.
5. **Support (`Qo'llab-quvvatlash`):** Fix the overlapping floating Telegram icon bug covering the title, reduce text-heavy disclaimers, style topic chips cleanly, improve the message textarea contrast, and make `"Murojaat yuborish"` a full-width primary button.
6. **Discover (`Kashf`):** Compress the oversized hero card (`"Suhbat, sayr yoki shahar bo'ylab hamroh toping"`) into a compact header + unified search bar with filter button, integrate horizontal **Bouncy Magnetic Category Chips**, and bring Companion Cards (`DEMO Madina, 26`) above the fold with rich photo/avatar hierarchy, verified badge, and clear hourly pricing.
7. **Favorites (`Sevimlilar` Empty State):** Redesign the plain left-aligned empty state into a centered, visually engaging empty state with an illustration/icon and a balanced CTA button.
8. **Booking Details (`Bron tafsilotlari`):** Move `<- Bronlar` into the top App Bar, structure booking metadata (*Kofe, Vaqt, Joy, Narx, Rol*) with icons and clear key-value rows, condense the long payment disclaimer (`To'lov`) into a clean info banner, and differentiate `"Bekor qilish"`, `"Muammo haqida xabar berish"`, and `"Bloklash"` using the **Hold-to-Confirm Destructive Button** for cancellation/blocking.
9. **Bottom Navigation:** Replace the current basic bottom navigation interaction with the **3-in-1 Quantum Shockwave Contrast** animation across all main screens.

---

## PART 4 — DESIGN SYSTEM

Provide concrete specifications for:
- **Typography:** Consistent scale and weights for Page Headings, Section Headings, Body Text, Supporting Text, and Metadata.
- **Colors:** Dark theme tokens (`#110d0b`, `#1c1613`, `#302621`), high-contrast warm white (`#f5f2f0`), warm orange accents (`#e86f38`, `#ff7b3d`), semantic status colors (Pending, Confirmed, Destructive Red).
- **Buttons:** Primary, Secondary, Ghost/Icon, and Hold-to-Confirm Destructive states.
- **Inputs:** Search fields, text inputs, message text areas, segmented controls, and switch toggles.
- **Cards & Components:** Reduce unnecessary card nesting and establish a unified visual language.

---

## PART 5 — FINAL DELIVERABLES

Provide the following:
1. **Screenshot Analysis:** Review each supplied screenshot and identify its UI/UX problems.
2. **Redesign Strategy:** Provide a screen-by-screen redesign plan covering all 8 screens + navigation.
3. **Navigation Redesign:** Explain the new navigation hierarchy and the 3-in-1 Quantum Shockwave Contrast animation.
4. **Component Specifications:** Explain the implementation and visual behavior of all four required interactive components.
5. **Design System:** Provide typography, color tokens, buttons, inputs, cards, and spacing rules.
6. **Layout Improvements:** Specify what to remove, what to simplify, what to group differently, and what to move behind icons.
7. **Visual Concepts / Interactive Prototype:** Provide redesigned visual concepts (or a complete interactive HTML/Tailwind/JS mobile prototype) demonstrating all redesigned screens and the 4 custom animations in action.
8. **Implementation Guidance:** Provide clear specifications that can be followed by the development team.

---

## FINAL OBJECTIVE

Transform **Yondo** from its current basic interface into a premium, modern, visually balanced mobile application.

The redesign must preserve the existing dark theme while significantly improving its visual quality, navigation, hierarchy, and interactive experience.

The four specified interactive components — **3-in-1 Quantum Shockwave Contrast Bottom Navigation**, **3D Aura Role Switcher**, **Bouncy Magnetic Category Chips**, and **Hold-to-Confirm Destructive Button** — must be treated as explicit design requirements, not optional inspiration.

Base your recommendations on the supplied screenshots and the exact specifications in this brief.