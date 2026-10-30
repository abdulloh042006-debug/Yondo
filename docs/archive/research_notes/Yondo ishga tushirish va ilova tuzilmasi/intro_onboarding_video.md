# Yondo: app-opening intro, first-run onboarding, tutorial and video guide (research + build spec)

Research date: 2026-10-28. Scope: evidence for an intro animation (2-5 s, optional sound), first-run onboarding, step-by-step tour and a video guide, plus a concrete, buildable proposal for Yondo (`apps/web`, React 19 + Vite + `motion`, uz/ru/en, themes `yondo` / `yondo-tun`, palette ink #111111 / paper #F5F2EC / carrot #E8501A only).
Source-quality legend used below: **[P]** primary (standards body, platform vendor docs), **[V]** vendor/marketing blog or analytics vendor (self-interested, B2B SaaS data), **[S]** secondary/news/community. "Unverified" = I could not open or confirm the primary page in this session.
Two limits to know: (1) the web-search quota ran out near the end, so a few planned lookups (Spotify/Headspace/Yandex Go launch behaviour, YouTube hosting facts, WCAG 1.2.2 / 2.3.1 pages) were not done and are listed under Gaps; (2) the Apple HIG page is JavaScript-rendered and the fetch returned only the title, so Apple statements below are marked unverified.

---

## 1. Intro / splash animation: how long, how often, skippable, non-blocking

### Takeaway
Platform guidance converges on "get the user into content fast": Android caps the splash icon animation at about 1 s, dismisses it at the app's first drawn frame and says to loop only if startup is slow; Nielsen's 0.1 s / 1 s / 10 s limits say anything over about 1 s breaks flow. A 3-4 s branded intro is therefore defensible only as a one-time (first-run) moment that is skippable and never gates content; repeat launches should get at most a sub-second "settle".

### Cited Findings
- Android's splash-screen guidance: the icon animation should not exceed 1,000 ms on phones; a deliberate start delay may be at most 166 ms; if startup takes longer than 1 s, "consider a looping animation"; the splash "is dismissed as soon as your app draws its first frame"; the attribute `windowSplashScreenAnimationDuration` does not change how long the splash stays on screen. Page last updated 2026-10-23. [P] — [Android Developers: Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen)
- Same page: design guidelines "recommend against using a branding image" on the splash, and the splash should be dismissed only when the app is visually stable so that no extra spinners are needed. [P] — [Android Developers: Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen)
- Nielsen's response-time limits: 0.1 s feels instantaneous; 1 s keeps the user's flow of thought uninterrupted (slower feels sluggish); 10 s is the limit for holding attention. Originally 1993 (book Usability Engineering), page carries a 2014 web-app update. [P/classic] — [NN/g: Response Times: The 3 Important Limits](https://www.nngroup.com/articles/response-times-3-important-limits/)
- A third-party UX blog (UXPin, titled 2026) suggests a splash should ideally be under about 2 s with no artificial delay. [V/S, not a platform rule] — [UXPin: Splash Screen Design best practices](https://www.uxpin.com/studio/blog/splash-screen/)
- Apple's HIG "Launching" page (from memory, page could not be rendered): launch screen should look like a static placeholder of the first screen, not a branding/"about" screen; avoid text on it; keep onboarding brief and skippable. **Unverified in this session; read the HIG pages before citing.** — [Apple HIG: Launching](https://developer.apple.com/design/human-interface-guidelines/launching)
- Duolingo (benchmark app): third-party teardown describes a plain solid-green splash with the centred owl and the name at the bottom, separate from the onboarding welcome screen. [S] — [ScreensDesign: Duolingo](https://screensdesign.com/apps/duolingo-language-lessons/?via=growthgems)
- Duolingo recently added a launch ("startup") sound; it plays only at app launch (so keeping the app open avoids it) and can be muted via Settings > Preferences > Sound Effects or by muting the device. Article dated 2026-07-29; third-party how-to, treat as unverified for exact release timing. [S] — [Lingoly: Turn off the Duolingo startup sound](https://lingoly.io/turn-off-duolingo-startup-sound/)
- Chameleon 2025 benchmark (B2B SaaS tours, not splashes, but relevant to "forced vs user-triggered"): user-triggered or smart-timed tours outperform delayed/blanket-triggered ones by 2-3x; self-triggered tours double engagement vs automated ones. [V] — [Chameleon Benchmark Report 2025](https://www.chameleon.io/benchmark-report)

### Inferences
- The only widely documented rule of thumb is "about 1 s for repeat launches, content-first". A 3-4 s animation should be framed as a **first-run brand moment**, not a per-launch tax. Frequency policy that follows: first ever launch = full intro (~3.4 s) and interruptible; later cold starts of the installed app = <= 0.9 s "settle" that ends as soon as the app is ready; warm resumes and route changes = none.
- Because Yondo's `main.tsx` does `await applySavedLang()` before `createRoot(...).render`, the page is blank until the language chunk loads; the intro must live in static `index.html` (inline CSS + SVG, zero JS) so it paints before the bundle, otherwise the animation itself becomes part of the delay.
- "Skippable" should mean: any tap, Esc, Enter or Space ends it immediately; the app is rendering underneath in parallel, so skipping costs nothing.
- Spotify, Headspace and Yandex Go behaviour could not be sourced (see Gaps); do not cite them as precedent.

### Gaps
- No sourced launch-screen behaviour for Spotify, Headspace or Yandex Go (search returned nothing usable).
- No independent data on user drop-off versus splash length for web apps/PWAs; the 1 s / 2 s figures are platform guidance and a vendor blog, not experiments.
- Apple HIG wording unverified (page not rendered by the fetch tool).

---

## 2. Can sound play at launch on web / PWA? (browser autoplay rules, as of 2026)

### Takeaway
On a normal web visit no browser will play sound at launch without a user gesture; the only documented exception is an installed/home-screen app in Chrome. So Yondo's intro must be designed **silent-first**: play the sting only if the audio context is already allowed (installed Chrome PWA, or after any earlier tap), otherwise tie sound to the first tap (language choice / "Boshlash") and never play late or out of sync.

### Cited Findings
- Chrome: muted autoplay is always allowed; unmuted autoplay is allowed if (a) the user has clicked/tapped on the domain, (b) on desktop the Media Engagement Index is high enough, or (c) the site is added to the home screen on mobile / the PWA is installed on desktop. [P] — [Chrome for Developers: Autoplay policy](https://developer.chrome.com/blog/autoplay)
- Chrome Web Audio: since Chrome 71 an `AudioContext` created before a user gesture starts `suspended`; call `resume()` after a gesture; check `AudioContext.state` / `statechange`. Don't assume playback; check the `play()` Promise and show a control if rejected. (The page's footer says "Last updated 2017-09-13" yet describes April 2018 changes, so the date is unreliable.) [P] — [Chrome for Developers: Autoplay policy](https://developer.chrome.com/blog/autoplay)
- Chromium page: "Any click on the document itself (this excludes scrolling) will count as user interaction"; on mobile, autoplay with sound is allowed if the user added the site to the Home Screen; Web Audio policy launched in M71 (Nov 22, 2018 update). [P] — [Chromium: Autoplay](https://www.chromium.org/audio-video/autoplay)
- MDN: autoplay blocking is not applied to `<video>` with no audio track or a muted track; autoplay is generally allowed only if audio is muted/volume 0, the user has interacted, the site is allowlisted, or an iframe is delegated via Permissions Policy. `navigator.getAutoplayPolicy()` returns `allowed` / `allowed-muted` / `disallowed`; a blocked `play()` rejects with `NotAllowedError`. [P] — [MDN: Autoplay guide](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)
- Firefox (per MDN): `media.autoplay.default` = 0 (per-domain), `media.autoplay.allow-muted` = true, `media.autoplay.block-webaudio` = true (audio contexts need sticky activation), autoplay waits until the tab is in the foreground. [P] — [MDN: Autoplay guide](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)
- Safari/macOS (June 8, 2017, WebKit blog): inference engine blocks sound-producing media by default on most sites; user can allow/deny per site; "Websites should assume any use of `<video>` or `<audio>` requires a user gesture click to play." [P] — [WebKit: Auto-Play Policy Changes for macOS](https://webkit.org/blog/7734/auto-play-policy-changes-for-macos/)
- iOS Safari history: iOS 10 (2016) allowed silent video autoplay but paused/blocked video with audio without a gesture (secondary report); MDN notes `playsinline` is required for inline autoplay in Safari. [S] — [AppleInsider forum on WebKit iOS 10 policy](https://forums.appleinsider.com/discussion/194134); [P] — [MDN: Autoplay guide](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)
- iOS Web Audio is silenced by the ringer/silent switch by default (audio session type `ambient`); workaround `navigator.audioSession.type = 'playback'`; reports conflict on other modes. Community WebKit bug threads, not official docs. [S] — [WebKit Bugzilla 264473](https://bugs.webkit.org/show_bug.cgi?id=264473); [Adactio: Web Audio API update on iOS](https://adactio.com/journal/19929)
- iOS 26 / iPadOS 26: every site added to the Home Screen now opens as a web app by default (user can switch this off in the Add dialog); manifest support unchanged. Reported via heise and mjtsai quoting WebKit; WebKit's own post was not opened. [S] — [heise: iOS 26 web app behaviour](https://heise.de/-10749652); [mjtsai.com](https://mjtsai.com/blog/wp-json/wp/v2/posts/49472)
- Reference behaviour: Duolingo's launch sound is mutable through a Sound Effects toggle (see section 1). [S] — [Lingoly](https://lingoly.io/turn-off-duolingo-startup-sound/)

### Inferences
- Answer to "can sound be played at all?": yes, but only (1) in an installed Chrome/Android PWA (documented exception), (2) after any prior tap/click in the session, or (3) on the first tap of the first-run flow. A plain-browser first visit is always silent. Whether the home-screen exception also unlocks `AudioContext` on iOS standalone web apps is not documented in what I found: **unverified**; feature-test with `ctx.state === 'running'` and fall back to silence.
- Implementation rule: create `AudioContext` lazily; at launch try `resume()`; if state is not `running` within ~100 ms, play nothing (do not queue a late sound). Pre-gesture feature detection via `navigator.getAutoplayPolicy('audiocontext')` may not exist in all engines (MDN snippet did not state support): treat as optional.
- On iOS leave the default `ambient` session: a launch sting should obey the silent switch (people open apps in public places); only a user-initiated media control should use `playback`.
- Sound identity therefore = two tiny assets: a ~1.2 s **sting** (only when audio is already allowed) and a ~0.15 s **tap/confirm** sound (on first gesture and key UI moments), both behind a Settings toggle.

### Gaps
- Current (2026) Safari desktop/iOS autoplay policy beyond the 2017 post: no primary source found.
- Whether Chrome's "home screen" exception applies to Web Audio (not only `<video>`/`<audio>`) is not stated explicitly in the pages fetched.
- No primary source for Firefox on Android or Samsung Internet behaviour.
- No data on what share of Uzbek users run installed PWAs vs browser tabs.

---

## 3. Accessibility and performance of the intro (WCAG 2.2, reduced motion, low-end Android, battery)

### Takeaway
A ~3.4 s, full-screen, standalone intro that is skippable, has no flashing and offers a non-motion variant satisfies WCAG 2.2.2 and 1.4.2 by construction (under 5 s / under 3 s, not in parallel with other content). Use `prefers-reduced-motion` (CSS for the boot intro, `MotionConfig reducedMotion="user"` already in the app for React parts) and animate only cheap properties on a tiny SVG.

### Cited Findings
- WCAG 2.2.2 Pause, Stop, Hide (Level A): moving content needs a pause/stop/hide mechanism only if it starts automatically, lasts more than five seconds, and is presented in parallel with other content; content not presented in parallel (e.g. a standalone loading animation) is exempt; a pause mechanism must not tie up focus. [P] — [W3C: Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)
- WCAG 2.3.3 Animation from Interactions (Level AAA): motion animation triggered by interaction can be disabled unless essential; "motion animation" excludes changes of colour, blur and opacity; techniques C39 / SCR40 use `prefers-reduced-motion`, and a user setting is also an accepted technique; vestibular disorders are the main concern. [P] — [W3C: Understanding 2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)
- WCAG 1.4.2 Audio Control (Level A): audio that plays automatically for more than 3 seconds needs a mechanism to pause/stop or a volume control independent of system volume; muting the system volume does not count; audio started by a deliberate user action is not "automatic". [P] — [W3C: Understanding 1.4.2](https://www.w3.org/WAI/WCAG22/Understanding/audio-control.html)
- Motion for React: `MotionConfig reducedMotion="user"` disables transform and layout animations automatically while keeping opacity/background-colour animation; override with `"always"` / `"never"` (e.g. from a saved profile setting); `useReducedMotion()` returns a boolean. [P] — [Motion: Accessibility](https://motion.dev/docs/react-accessibility)
- web.dev animations guide: `transform` and `opacity` stay on the compositor; animating `top`/`left` dropped 50% of frames in the page's test versus about 1% with `transform`; blur and shadows are costlier to paint; use `will-change` sparingly. Page last updated 2020-10-06; does not address low-end devices specifically. [P] — [web.dev: Animations guide](https://web.dev/articles/animations-guide)
- Android: the 1,000 ms icon-animation guideline (section 1) is the platform's own budget for launch animation. [P] — [Android Developers](https://developer.android.com/develop/ui/views/launch/splash-screen)
- Repo state: the app already wraps everything in `<MotionConfig reducedMotion="user">` and has three `@media (prefers-reduced-motion: reduce)` blocks in `styles.css`. [repo] — [apps/web/src/main.tsx](file:///D:/Yondo/apps/web/src/main.tsx)

### Inferences
- Keep the first-run intro under 5 s (proposal: 3.4 s) and mark it as a standalone full-screen state; also make it interruptible. This avoids needing a persistent pause control while still handling keyboard/screen-reader users (overlay `aria-hidden`, app content not `inert`, any key/tap dismisses).
- Keep every sound <= 1.5 s (well under the 3 s threshold of 1.4.2) and still ship a Settings toggle; the toggle also covers people who dislike unexpected sound.
- Flashing: an ink<->paper full-screen swap is high contrast. WCAG 2.3.1 (three flashes) was **not fetched in this session** (standard knowledge: no more than three flashes in any 1-second period). Design rule: no full-screen luminance inversion repeated; the intro has one background colour throughout.
- Reduced-motion variant should use only opacity changes (explicitly not "motion animation" under 2.3.3 and kept by Motion's reduced-motion handling).
- Low-end Android and battery: tiny inline SVG (64x64 viewBox symbol), animate `transform`, `opacity` and `stroke-dashoffset` (the last repaints, but on a ~64 px glyph that is negligible), no `backdrop-filter`/blur in the intro (glass is for the app, not the boot screen), no JS animation loop, remove the overlay from the DOM when finished so nothing keeps running. Measure on a real mid/low Android device; no benchmark was found.

### Gaps
- WCAG 2.3.1 and 1.2.2 / 1.2.5 pages not fetched this session.
- No source for what proportion of Uzbek users enable reduced motion; no battery-cost measurement for short CSS/SVG animations was found.
- LCP interaction: whether a large splash overlay counts as the LCP element in Chrome should be measured in Lighthouse on the real build (not researched).

---

## 4. PWA splash screen vs in-app animation (manifest, iOS splash images)

### Takeaway
The OS-level splash is generated for you on Android Chrome from the manifest (name, background_color, icons) and cannot be animated; iOS needs per-device `apple-touch-startup-image` images. Treat it as a static "first frame" that must colour-match the in-app boot screen so the hand-over is seamless. Yondo currently has no web manifest, so this layer does not exist yet.

### Cited Findings
- Chrome shows a splash on mobile until first paint, built automatically from manifest `name`, `background_color` and `icons`; set `background_color` to match the page load colour; 192 px and 512 px icons are usually enough; `theme_color` should match `<meta name="theme-color">`, which can vary by colour scheme via the `media` attribute but **not** in the manifest. Page last updated 2024-09-18. [P] — [web.dev: Add a web app manifest](https://web.dev/articles/add-manifest)
- iOS does not generate a splash from the manifest; startup images are declared with `apple-touch-startup-image` link tags with device-specific media queries; community examples show older device sizes (current device list needs checking). [S] — [Discourse Meta: Generating splash screens for iOS PWA](https://meta.discourse.org/t/generating-splash-screens-for-ios-pwa/112733)
- iOS 26 treats Home Screen sites as web apps by default (section 2), which makes the standalone experience more common on iPhone. [S] — [heise](https://heise.de/-10749652)
- Repo state: `apps/web/public` contains only `app-icon.svg`, `apple-touch-icon.png`, `favicon.svg`, `icon-512.png`; `index.html` has no manifest link, `theme-color` is `#f3ebdf`, and `vite.config.ts` has no PWA plugin. [repo] — [apps/web/index.html](file:///D:/Yondo/apps/web/index.html), [apps/web/vite.config.ts](file:///D:/Yondo/apps/web/vite.config.ts)
- Android guidance on branding on the splash ("recommend against using a branding image") concerns native apps; roadmap says native apps come only if allowed. [P] — [Android Developers](https://developer.android.com/develop/ui/views/launch/splash-screen)

### Inferences
- Layering: (1) OS splash (static, from manifest) -> (2) inline boot screen in `index.html` with the same background colour and a static symbol -> (3) the animated intro continues from that symbol -> (4) app. Pick the colour to avoid a flash: manifest `background_color` cannot follow the day/night theme, so a night-theme user may see a paper-coloured OS splash before the ink boot screen. Options for the owner: accept it (default theme is day `yondo`), or choose ink for the manifest. Mitigate by an inline script in `<head>` that reads the saved theme key (see `ui/theme.tsx`) and sets the boot background before first paint.
- Installing as a PWA also unlocks the only documented autoplay exception (Chrome home screen), so the manifest + service worker + install prompt is a prerequisite for "intro with sound on every launch" and should be scheduled before any promise of launch sound.
- If native apps arrive later, the Android 12 splash API rules in section 1 apply (<= 1 s icon animation); the web intro design stays valid as the first-run-only moment.

### Gaps
- No current Apple documentation on exact `apple-touch-startup-image` sizes for 2026 devices.
- No source on how Android 12+ renders splash for installed PWAs beyond Chrome's description.
- Installability criteria for 2026 not listed by the fetched page.

---

## 5. Technology options for a 3-4 s logo animation

### Takeaway
Use inline CSS/SVG for the boot intro (no JS, no bundle cost) and the already-installed `motion` library for any in-app animated moments. Lottie/dotLottie and Rive each need a WebAssembly runtime of roughly 0.15-0.57 MB (figures conflict) plus an authoring tool; that is disproportionate for a three-circle-and-three-lines logo in three colours.

### Cited Findings
- Rive's own comparison claims .riv files are about 10-15x smaller than equivalent Lottie JSON (example: 240 KB Lottie vs 16 KB Rive). Vendor claim. [V] — [Rive: Rive as a Lottie alternative](https://rive.app/blog/rive-as-a-lottie-alternative); echoed in [LottieFiles: LottieFiles or Rive](https://lottiefiles.com/blog/lottie-animations/lottiefiles-or-rive)
- Rive web runtime sizes (docs updated January 2026): `canvas` runtime 1728 KB uncompressed / 567 KB compressed; `canvas-lite` 707 KB / 222 KB; most of this is the WASM library. A v2 migration guide separately says the WASM request is about 261 KB brotli. The two pages disagree; the WASM is fetched at runtime from a CDN unless a `-single` variant is used. [P] — [Rive: Runtime sizes](https://rive.app/docs/runtimes/runtime-sizes.md); [Rive: Migrating v1 to v2](https://rive.app/docs/runtimes/web/migrating-from-v1-to-v2)
- dotLottie: open (MIT) container format; renderer is ThorVG compiled to WASM. LottieFiles' marketing page says about 150 KB runtime; its v0.x JS docs say about 500 KB compressed WASM fetched from a CDN on first player construction; newer builds add WebGL/WebGPU renderers. Figures conflict and are for different versions. [V] — [LottieFiles dotLottie](https://lottiefiles.com/dotlottie); [LottieFiles docs: How the web player works](https://docs.lottiefiles.com/en/runtimes/distributions/js/v0.x/core-concepts)
- Rive runtimes are MIT-licensed and free for commercial use; the Editor is free to use but, per Rive's October 2025 pricing announcement (starting 2025-10-20), creating exports moved to paid plans (a $9/month annual "Cadet" plan was introduced), with no runtime fees. I could not open the announcement itself; relayed by a search summary. **Verify at rive.app/pricing.** [P/V, unverified] — [Rive: Getting started with runtimes](https://rive.app/docs/runtimes); [Rive blog: new 9 mo plan](https://rive.app/blog/rive-s-new-9-mo-plan)
- Callstack's mobile benchmark reports Rive playing at roughly 60 FPS on an older Android device (no Lottie baseline in the part I could see). [S] — [Callstack: Lottie vs Rive](https://callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation)
- Motion (already a dependency, `"motion": "^14.5.0"`) respects reduced motion via `MotionConfig` / `useReducedMotion`; `transform` and `opacity` are the compositor-friendly properties. [P] — [Motion: Accessibility](https://motion.dev/docs/react-accessibility); [web.dev: Animations guide](https://web.dev/articles/animations-guide); [repo package.json](file:///D:/Yondo/apps/web/package.json)
- Remotion (React video renderer): free for individuals, for-profit organisations of up to 3 employees, non-profits and evaluators; paid Company License at 4+ people; source-available, not OSI open source; the license "will slightly change" in Remotion 5.0 (details unconfirmed). [P] — [Remotion: Pricing](https://www.remotion.dev/docs/pricing); [Remotion: License FAQ](https://www.remotion.dev/docs/license/faq)
- Web animation performance rule (transform/opacity cheap, layout/paint costly): see [web.dev: Animations guide](https://web.dev/articles/animations-guide).

### Inferences
- Comparison for a 3-4 s ink/paper/carrot logo (my judgement, sources above for the facts):

| Option | Added weight | Tooling | Fit |
|---|---|---|---|
| Inline CSS keyframes + SVG (`stroke-dasharray/offset`, `transform`, `opacity`) | ~1-2 KB inline, 0 JS | any editor; the logo SVG already exists | **Best for boot intro** (paints before JS) |
| `motion` (WAAPI/JS) in React | already shipped | code | **Best for in-app moments** (logo docking into the header, card transitions, onboarding) |
| SVG SMIL | 0 | code | Supported in modern browsers (from memory, unverified); no clean `prefers-reduced-motion` hook; not recommended |
| dotLottie | 0.15-0.5 MB WASM + .lottie file | After Effects + Bodymovin or LottieFiles | Overkill; adds an async request in the critical path |
| Rive | 0.22-0.57 MB WASM + .riv | Rive editor (exports paid since Oct 2025, unverified) | Only worth it if interactive state machines are needed later |
| Video (WebM/MP4) | tens-hundreds of KB, plus autoplay-video rules | ffmpeg (already in repo) | Poor for crisp vector logo, theme switching and reduced-motion handling; no |
| Canvas/WebGL | JS code | code | Unneeded for three circles and three lines |

- The brand symbol is already a 64x64 SVG made of three round-cap strokes and three circles (ink, carrot top-right, ink bottom), which maps directly onto `stroke-dashoffset` draws and `scale` pops. See the shot list in section 10.
- Remotion is not needed: the repo already has a deterministic HTML/SVG -> headless browser -> ffmpeg pipeline (`marketing/ad-video`), and adding Remotion would introduce a licence consideration if the team grows past 3 people.

### Gaps
- No independent same-asset benchmark (file size, frame rate, CPU, battery) comparing CSS/SVG vs dotLottie vs Rive on a low-end Android.
- Exact current `dotlottie-web` and `@rive-app/canvas` transfer sizes must be measured from the package (Bundlephobia / network panel).
- Motion's own bundle-size figures were not fetched (not needed since it is already shipped).
- Rive export pricing unverified at the source.

---

## 6. First-run onboarding: patterns that work, and the evidence

### Takeaway
The strongest evidence says: keep onboarding short and skippable, personalise only where you must, teach by doing and by contextual hints, and avoid long forced carousels. NN/g found tutorials made no measurable success difference and made tasks feel harder; vendor benchmarks show completion collapses past about five steps and rises when users trigger the tour themselves. For Yondo: one setup screen (language/alphabet), a 3-card "how it works + safety" with Skip everywhere, then contextual hints at first use.

### Cited Findings
- NN/g (Alita Kendrick, March 8, 2020): quantitative remote unmoderated between-subjects test, 70 participants (35 per group), four iPhone apps with deck-of-cards tutorials. Task success 91% (tutorial) vs 94% (skipped), not significant; perceived ease lower for the tutorial group (4.92 vs 5.49 on a 1-7 scale, p=0.047); completion time slower (93.49 s vs 85.17 s), not significant, and reading time excluded. Tutorials are usually not worth building for simple apps; where needed prefer interactive/contextual help; limitation: only four iOS apps. [P] — [NN/g: Mobile-app onboarding tutorials](https://www.nngroup.com/articles/mobile-tutorials/)
- NN/g (summarised by secondary coverage): onboarding can make sense when an app needs information from the user to tailor the experience or has unusual interaction patterns; keep instruction brief and unobtrusive, highlight what's unfamiliar. [S] — [search summary of NN/g mobile tutorials article](https://www.nngroup.com/articles/mobile-tutorials/)
- NN/g help-and-documentation: "push revelations" (help unrelated to the current task, e.g. launch overlays) are often ignored; "pull revelations" (help triggered by a signal of need) are better; users should be able to re-access dismissed help. Secondary sources attribute a 2023 Laubheimer piece to similar conclusions (not confirmed). [P/S] — [NN/g: Help and documentation](https://www.nngroup.com/articles/help-and-documentation/)
- Chameleon Benchmark Report 2025 (550M+ interactions, B2B SaaS web tours): tours over five steps "lose attention from more than half of users"; four-step tours have the highest completion; launcher-driven tours complete at 67% vs 31% otherwise; user-triggered/smart-timed beat delayed tours 2-3x; progress indicators improve completion by 12%; modal dismiss rate 37.5%, CTA click 40%. [V] — [Chameleon Benchmark Report 2025](https://www.chameleon.io/benchmark-report)
- Earlier Chameleon reports (via search summary): 2019 average completion 61%, 4-step 46% vs 5-step 23%; 2020 three-step tours 66%; 2024 average 33.5%. Figures vary by year and method. [V] — [Chameleon 2019 PDF](https://www.chameleon.io/assets/chameleon-product-tour-benchmarks-report-2019.pdf); [Chameleon 2024 report](https://www.chameleon.io/benchmark-report-24)
- Userpilot 2025 benchmark (188 companies, B2B SaaS): average onboarding checklist completion 19.2%, median 10.1%; Appcues case: checklist completion rose from 2% to 25% after splitting into bite-sized lists (single anecdote). [V] — [Userpilot: SaaS product metrics](https://userpilot.com/saas-product-metrics/); [Appcues: bite-sized checklists](https://goodux.appcues.com/behind-the-experience/appcues-bite-sized-checklists)
- Claims like "30% fewer steps raises completion up to 50%" (attributed to Appcues) and "60% completion for persona-based paths" could not be traced to primary sources. [V, unverified] — [Monetizely](https://www.getmonetizely.com/articles/how-to-measure-onboarding-completion-rates-a-strategic-guide-for-saas-executives); [SaaSHero](https://www.saashero.net/customer-retention/appcues-style-saas-onboarding-frameworks/)
- Repo: Discovery is the index route and public (`<Route index element={<Discovery />} />`); bookings, favorites, account and notifications are behind `RequireAuth`; the Studio is companion-only. [repo] — [apps/web/src/App.tsx](file:///D:/Yondo/apps/web/src/App.tsx)

### Inferences
- Pattern choice for Yondo: **(1) one preference screen** (language, since it changes everything after) -> **(2) three "how it works" cards** that carry the trust/safety message (a marketplace for meeting strangers is the case where NN/g's exception "unusual or tailoring" plus trust framing justifies a short intro) -> **(3) straight into public Discovery** (no forced sign-up) -> **(4) contextual hints** at first encounter -> **(5) a replayable guide in Help** (video + the same three cards).
- Cap: 4 screens max including language, Skip visible on every card, a progress indicator (Chameleon: +12% completion, vendor figure) and explicit Back.
- Checklist only where there is a genuine multi-step setup with dependencies: the companion application in Studio (profile, photos, services, availability, submit). Customers need none.
- Targets should be Yondo's own: measure language-screen pass rate, onboarding skip rate, and "reached first booking request"; B2B SaaS benchmarks above do not transfer directly to a consumer booking marketplace.

### Gaps
- No peer-reviewed study of onboarding length vs retention for consumer marketplaces; most numbers are vendor-reported B2B SaaS tours/checklists.
- Retention-impact data (Mixpanel/Amplitude/Pendo) not found; a Duolingo delayed-sign-up case search failed due to the quota.
- Culturally specific onboarding data for Uzbekistan (Telegram-first habits, Russian/Uzbek mix) not found.

---

## 7. Language/alphabet choice, role choice, permission priming, safety explanation

### Takeaway
Ask only what changes the experience immediately (language, plus Uzbek alphabet when Uzbek is chosen); do not ask for role (the app already supports roles as an Account setting) or any browser permission at first launch; explain safety honestly using the app's existing wording and rules (public places, verified badge only from the server, SOS is a record for review and a helper to call 112, not a rescue service).

### Cited Findings
- Permission priming: no controlled study of grant-rate uplift was found; vendor pieces agree on being specific about value, offering "Not now", and tying the request to a moment the user has reason to want the feature rather than first launch. Observational counts (Lazyweb) say roughly 40-63% of sampled apps show a notification primer; that is prevalence, not effectiveness. [V] — [Dolfy: permission prompt problem](https://www.dolfy.ai/blog/permission-prompt-problem-push-notification-opt-in-timing); [TRTC: push opt-in guide](https://trtc.io/blog/details/push-notification-permission-opt-in-guide); [Lazyweb research](https://www.lazyweb.com/research/percent-apps-notification-primer-screen)
- Apple guidance (from memory, unverified): ask only when needed, explain in context, don't request several permissions at launch. [P, unverified] — [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/launching)
- Repo i18n: `LANGS` picker with own-language labels exists (`LanguagePicker`, `AlphabetPicker`), storage keys `yondo.lang` and `yondo.uzAlphabet`; owner rule (CLAUDE.md S21-S23): switcher only in Settings and the compact top-bar, **no browser auto-detect**, Uzbek alphabets 1995 (o' g' sh ch) and 2026 (ö ğ ş ç) both kept, **default 1995 until 2027-04-22 then 2026**, choice saved to the account (`users.ui_locale`). [repo] — [apps/web/src/i18n/LanguagePicker.tsx](file:///D:/Yondo/apps/web/src/i18n/LanguagePicker.tsx), [CLAUDE.md](file:///D:/Yondo/CLAUDE.md)
- Repo roles: `Account.tsx` lets a signed-in user toggle `customer` / `companion` roles ("Who I am"); the FAQ says to enable the Companion role and fill in the application in the Companion studio, which a moderator reviews. [repo] — [apps/web/src/pages/Account.tsx](file:///D:/Yondo/apps/web/src/pages/Account.tsx), [apps/web/src/i18n/en.ts](file:///D:/Yondo/apps/web/src/i18n/en.ts)
- Repo safety wording already approved: Help says call 112 for danger and that the Yondo app does not call emergency services or the police; the verified badge appears only when the server confirms identity and "is not a safety guarantee"; trusted contacts are "not messaged automatically yet". Product rules: SOS is a recorded alert for manual review; never claim emergency services, trusted contacts or tracking were notified; location only after a tap and only into the SMS text. [repo] — [apps/web/src/i18n/en.ts](file:///D:/Yondo/apps/web/src/i18n/en.ts), [CLAUDE.md](file:///D:/Yondo/CLAUDE.md)
- Consent: legal consent is already collected at login (`ConsentCheck`, `ConsentGate`), unticked by default with links to terms/privacy. [repo] — [apps/web/src/ui/Consent.tsx](file:///D:/Yondo/apps/web/src/ui/Consent.tsx)

### Inferences
- Language screen: show labels in each language's own name (the picker already does), no pre-selection from `navigator.language` (owner rule); after choosing Uzbek reveal two compact options with a live sample ("hamroh topish" 1995 vs "hamroh topiş" 2026, the second form is how `index.html` already spells it), pre-selected = 1995 until 2027-04-22 per the owner's rule; store in the same keys; promise "you can change this in Settings".
- Role: customer-first. Do not ask "customer or companion?" up front (it adds a fork to everyone's first minute and the app has no such first-run state); put a secondary link "I'm a companion" on the last card that goes to login -> Account -> role toggle. Fits the existing "Who I am" mechanism.
- Permissions at first run: none. Location only on SOS tap (existing rule). Notifications: ask only after the first booking request, with a soft in-app explanation first, and only if web push is built (not verified in the repo). Camera/photos: only inside the companion application when uploading.
- Safety card content (intent, final copy to be owner-approved): meetings in public places only; companion applications are reviewed; the Verified badge appears only when the server confirms identity and is not a guarantee; in danger call 112; SOS records an alert for review and helps you call/text from your own phone, Yondo does not itself dispatch help. Avoid any phrase implying emergency dispatch, tracking or guaranteed safety.
- No romantic imagery or wording anywhere in onboarding: use line-art of city, bench, café awning, two avatars as neutral companions (already established in the ad pipeline).

### Gaps
- No controlled evidence for pre-permission priming effect size.
- Apple HIG statements unverified.
- Whether web push exists in Yondo (affects the notification-priming step) not checked.
- Legal text of consent copy is out of scope here.

---

## 8. Step-by-step product tours: libraries vs a short illustrated "how it works"

### Takeaway
Do not add a tour library yet. A 3-card illustrated intro plus 2-3 lightweight, custom contextual hints covers the need with less weight and no licence risk. If a spotlight tour is wanted later: driver.js (MIT, ~5 KB gz, no dependencies) or react-joyride v3 (MIT, React 16.8-19); avoid Shepherd.js and Intro.js for a commercial product unless a paid license is bought.

### Cited Findings
- driver.js: MIT, "free for personal and commercial use", about 5 KB gzipped, zero dependencies, vanilla TypeScript, keyboard controllable; README gives no accessibility details and no React-specific API. [P] — [driver.js on GitHub](https://github.com/kamranahmedse/driver.js)
- Shepherd.js: dual-licensed AGPL-3.0 and a Commercial License; AGPL free for open-source/non-commercial use, commercial license required for commercial products and revenue-generating companies; has a React wrapper package in the repo; README does not mention accessibility. [P] — [Shepherd on GitHub](https://github.com/shipshapecode/shepherd)
- react-joyride v3: MIT; v3.1.0 `package.json`/README declare React 16.8 through 19 (peer range "16.8 - 19"); v3.2.0 listed as MIT by a directory; v2 to v3 requires migration; a third-party `react-joyride-react19-compat` package is a different project. [P/S] — [react-joyride v3.1.0 README (jsDelivr)](https://cdn.jsdelivr.net/npm/react-joyride@3.1.0/README.md); [package.json](https://cdn.jsdelivr.net/npm/react-joyride@3.1.0/package.json); [licenses.dev](https://licenses.dev/npm/react-joyride/2.5.5)
- Intro.js: AGPL, commercial use requires a commercial license; official site lists lifetime tiers $9.99 (1 project), $49.99 (5 projects), $299.99 (unlimited); free for non-commercial. [P] — [Intro.js license](https://introjs.com/docs/getting-started/license); [Intro.js checkout](https://introjs.com/checkout)
- Product-tour length evidence: see section 6 (<= 5 steps; user-triggered tours perform better; tours that auto-start are push revelations). [V/P] — [Chameleon 2025](https://www.chameleon.io/benchmark-report); [NN/g Help and documentation](https://www.nngroup.com/articles/help-and-documentation/)
- The app already has reveal/stagger components and a `ToastProvider` and `Sos`/`feedback` UI, so a small hint component fits the existing structure. [repo] — [apps/web/src/ui/motion.tsx](file:///D:/Yondo/apps/web/src/ui/motion.tsx)

### Inferences
- Comparison:

| Library | Licence for Yondo (commercial) | Size / deps | React 19 | A11y evidence | Verdict |
|---|---|---|---|---|---|
| driver.js | MIT | ~5 KB gz, none | wrapper not needed (vanilla) | keyboard control only documented | Good later option |
| react-joyride 3.x | MIT | not measured | declared 16.8-19 | not verified | Good later option; verify focus handling |
| Shepherd.js | AGPL-3.0 or paid commercial | not measured | React wrapper exists | not documented | Avoid without licence |
| Intro.js | AGPL or paid ($9.99-$299.99 lifetime) | not measured | vanilla | not documented | Avoid unless licence bought |

- Why custom first: three hints (first Discovery visit: filters; first profile: availability + request; first booking: status timeline) need only a dismissible card/popover anchored to an element, a `localStorage` flag per hint (`yondo.seen.<id>`) and a "Show hints again" action in Help. That is under 100 lines, uses `motion` and `t('key')`, and avoids trapping focus the way a modal tour can.
- A11y requirements for any hint/tour you build or adopt: operable by keyboard, focus not trapped, Esc dismisses, announced via polite live region, dismissals persisted, honours reduced motion, and a re-entry point (NN/g: allow re-access to dismissed help).
- The illustrated "How it works" cards double as the static fallback for the video (same artwork, no audio, no data cost).

### Gaps
- No verified accessibility audit of driver.js, react-joyride 3.x, Shepherd or Intro.js; must be tested with axe-core (already a devDependency) and keyboard/screen-reader before adoption.
- Bundle sizes of react-joyride/Shepherd/Intro.js not measured.
- Driver.js release date/version not found (Releases tab was empty in the fetch).

---

## 9. Video guide: length, structure, captions, languages, hosting, bandwidth, production

### Takeaway
A 60-90 s guide fits inside Wistia's "educate/explain" 1-5 min band at the short end, and under-one-minute videos average a 52% engagement rate. Make two language files (uz, ru) per aspect ratio, self-host an optimised MP4 (about 6-12 MB for 75 s) with `preload="none"` and a poster, offer captions as an optional track (not burned in), and produce it with the existing HTML/SVG + ffmpeg pipeline.

### Cited Findings
- Wistia (July 1, 2025): under 1 min averages a 52% engagement rate (viewers watch about half); 1-5 min is "the sweet spot" for how-tos/tutorials/explainers (viewers typically watch over 50%); engagement drops 11% once videos pass the 30-minute mark; the post cites its 2026 State of Video Report on 13M+ videos. [V] — [Wistia: Optimal video length](https://wistia.com/blog/optimal-video-length)
- Older Wistia study (2016 write-up of 564,710 videos / 1.3B plays): about 2 minutes is the sweet spot and engagement drops significantly after that; a 90-second video holds viewers well. [V, secondary] — [Wistia: Optimal video length (older edition cited by Maestro/ATD)](https://maestrolearning.com/blogs/how-long-should-your-video-be/)
- Uzbekistan connectivity: Ookla Speedtest Global Index mobile download April 2026 = 57.77 Mbps (76th), per local news published 19 May. Later reports in search snippets give 62.87 Mbps (June) and 65.27 Mbps (August 2026, 72nd) but those pages were not opened. Averages, not medians. [S] — [Anhor.uz: Uzbekistan rises in mobile speed ranking](https://anhor.uz/news/uzbekistan-mobile-internet/); August snippet sources: [Zamin.uz](https://zamin.uz/en/uzbekistan/221541-uzbekistans-rank-in-the-internet-speed-ranking-revealed.html) (unverified which month)
- Mobile data price: a May 14, 2026 Kun.uz item (snippet, not opened) cites an average 5 GB package at about $2.32/month; cable.co.uk 2023 put Uzbekistan's average at $0.30 per GB. [S] — [Kun.uz, 2026-05-14](https://kun.uz/en/news/2026/05/14/uzbekistan-ranks-as-cheapest-in-region-for-mobile-connectivity-report); [Daryo, 2023](https://daryo.uz/2023/09/27/global-mobile-data-prices-in-2023-central-asian-countries-in-focus/)
- Existing production pipeline in the repo (reusable): deterministic HTML/SVG page `render(t)` rendered frame-by-frame in headless Chromium to ffmpeg; 9:16 (1080x1920) and 16:9 (1920x1080) at 30 fps; H.264 + AAC 48 kHz; original synthesized music/SFX (`audio.py` has `s_pop`, `s_tap`, `s_ding`, `s_chime`, `s_whoosh`); voices supplied by the owner from voicelab.uz (A narrator woman, B customer young man, C companion young woman); loudnorm I=-14 / TP=-1.5; UZ + RU; line-art scene layer in ink/paper/carrot; `?subs=1` toggles subtitles (off by default per owner); app screens captured from `apps/web` in `yondo` / `yondo-tun` themes. [repo] — [marketing/ad-video/README.md](file:///D:/Yondo/marketing/ad-video/README.md)
- Owner rules for the ad: no subtitles, no DEMO labels, only ink/paper/carrot, no romantic gestures; the owner wrote "no subtitles" about the promo video. [repo] — [CLAUDE.md](file:///D:/Yondo/CLAUDE.md)
- Remotion is an alternative React-based renderer with licence limits (section 5); Rive/After Effects/Lottie need separate paid or heavy tooling. [P] — [Remotion pricing](https://www.remotion.dev/docs/pricing)
- Captions/hosting: WCAG 1.2.2 (captions for prerecorded video) and YouTube vs self-host facts were **not fetched** (see Gaps).

### Inferences
- Size arithmetic (mine, from bitrate x duration): 75 s at 0.6 Mbps (480p) = about 5.6 MB; at 1.2 Mbps video + 64 kbps audio (720p) = about 11.9 MB; at 3 Mbps (1080p) = about 28.7 MB. At the 2026 average mobile speed (~58-65 Mbps) 12 MB is a couple of seconds, but averages hide slow rural/congested connections, and at ~$0.46/GB (5 GB / $2.32 snippet) 12 MB costs roughly half a cent. Conclusion: ship 720p (9:16 for phones, 16:9 for desktop), poster image, `preload="none"`, `playsinline`, play only on tap; never autoplay with data cost.
- Hosting: self-hosting an MP4 in the app's origin matches the app's no-third-party posture (fonts are self-hosted "no request to Google"); YouTube would add adaptive bitrate and free bandwidth but third-party requests; decide after checking YouTube embed privacy mode and local availability (not researched). Keep the hosting decision tied to the owner's "server last" rule (S26): initially a static file in `public/` or the future storage adapter.
- Captions: the owner's "no subtitles" rule was stated for the promo. For the in-app guide propose an optional WebVTT `<track>` (off by default, not burned in) because people watch muted in public; needs explicit owner confirmation since it touches an owner preference. Design the visuals to be understandable silent-first via in-frame step titles ("1 Toping / 2 So'rov / 3 Xavfsizlik") which are UI callouts, not subtitles.
- Language handling: two audio-voiced files per ratio (uz, ru), uz in the user's chosen alphabet only for on-screen text (voices are language-only); English version can be silent or later.
- Storyboard method (cheap and uses repo tooling): script (7-9 lines) -> beat sheet (one idea per scene, 5-15 s) -> animatic of stills with durations in `timeline.json` -> voice recording by the owner -> render with `build_page.py` / `render.mjs` -> audio via `audio.py` -> mux. Use real UI captures from `apps/web` so the guide never contradicts the product; re-capture when UI changes.

### Gaps
- No sourced guidance on YouTube vs self-hosted video privacy/availability in Uzbekistan; not searched.
- No Uzbekistan-specific video engagement data; Wistia is a global B2B-weighted dataset.
- Data-plan/caps behaviour of Uzbek carriers for video not found; Ookla figures are averages; the August 2026 figure unverified.
- WCAG 1.2.2 / 1.2.5 pages not fetched; Facebook-style "85% watch muted" claim not verified and not used.

---

## 10. Concrete proposal for Yondo

### Takeaway
Build a three-layer experience: (a) a 3.4 s first-run intro (Y-fork draws itself: two nodes converge on the third; silent by default, sting only when audio is already allowed) and a <= 0.9 s settle for later cold starts; (b) reduced-motion = opacity-only fade of the static logo; (c) a 4-screen first-run flow (language/alphabet -> 3 cards incl. safety -> public Discovery -> contextual hints) with a replayable Help guide; (d) a 75 s tutorial video in uz and ru built with the existing pipeline. Do not write final code yet.

### Cited Findings
Repo facts the design relies on:
- Symbol: 64x64 viewBox; strokes `M14 12 28 33Q31 37 32 40 M50 12 36 33Q33 37 32 40 M32 40v12` width 5 round caps; circles at (14,12) r7 ink, (50,12) r7 carrot `#E8501A`, (32,55) r5.5 ink; wordmark = outlined paths (Space Grotesk Bold, do not retype); carrot is graphic-only, never text (3.36:1 on paper, 5.03:1 on ink); minimum sizes; no gradients/shadows/outlines on the logo. [repo] — [yondo-symbol.svg](file:///D:/Yondo/design-prototype/brand/logo/yondo-symbol.svg), [USAGE.md](file:///D:/Yondo/design-prototype/brand/logo/USAGE.md)
- Slogan "Yondo doim yoningda" (RU "Yondo. Всегда рядом."); "yoningda" has no letters that differ between the 1995 and 2026 alphabets. [repo] — [CLAUDE.md](file:///D:/Yondo/CLAUDE.md)
- Existing easing constant `[0.22, 1, 0.36, 1]` in `ui/motion.tsx`; `MotionConfig reducedMotion="user"`; glow = carrot at low opacity; themes `yondo` (paper ground, ink actions) and `yondo-tun` (ink ground, paper actions). [repo] — [apps/web/src/ui/motion.tsx](file:///D:/Yondo/apps/web/src/ui/motion.tsx), [CLAUDE.md](file:///D:/Yondo/CLAUDE.md)
- `main.tsx` awaits `applySavedLang()` before first render; no manifest/service worker yet. [repo] — [apps/web/src/main.tsx](file:///D:/Yondo/apps/web/src/main.tsx)
- Evidence behind each rule: sections 1-9 above.

### Inferences (the build spec)

**(a) Intro storyboard, first run (3.4 s total, ground = current theme: paper `#F5F2EC` day / ink `#111111` night; symbol colours invert ink<->paper per theme, carrot node always `#E8501A`)**

| Shot | Time (s) | What happens | Motion / easing | Sound (only if allowed) |
|---|---|---|---|---|
| 0 Hold | 0.00-0.25 | Flat ground; inline boot screen already painted, colour-matched to manifest `background_color` | none | none |
| 1 Two people | 0.25-0.85 | Ink node (14,12) pops, carrot node (50,12) pops 80 ms later; scale 0 -> 1 with slight overshoot (spring stiffness ~380, damping ~22, or `cubic-bezier(0.34,1.56,0.64,1)`) | transform + opacity | soft low "tap", then a fifth-up "tap" (about 60-90 ms each) |
| 2 Converge | 0.60-1.60 | Two stems draw from the nodes toward the fork point (32,40); after the join, the single stem draws down to (32,52) | `stroke-dashoffset` 1 -> 0, ease-in-out `cubic-bezier(0.65,0,0.35,1)`, 0.8 s + 0.35 s | gentle filtered-noise rise (-24 dB) tracking the draw |
| 3 Meeting | 1.55-1.95 | Third ink node (32,55) pops; a carrot ring (opacity 0.5 -> 0, radius 5.5 -> 14) pulses once | scale + opacity, ease-out `[0.22,1,0.36,1]` | two-note chime A4 + E5 (open fifth, matches the Am-F-C-G ad key), decays by ~1.2 s |
| 4 Wordmark | 1.95-2.55 | Outlined "Yondo" wordmark reveals left-to-right under a mask with a slight rise (8 px) | clip/mask or per-path stagger 40 ms if the letters are separate paths (check `yondo-horizontal-light.svg`), opacity 0 -> 1 | none |
| 5 Slogan | 2.40-2.90 | "Yondo doim yoningda" fades in under the wordmark (Uzbek, brand-invariant; identical in both alphabets) | opacity only | none |
| 6 Release | 2.90-3.40 | Hold 0.3 s, then overlay fades out (opacity 1 -> 0, 0.25 s) to the language screen; optional: the symbol docks into the top-bar logo (shared-element) | opacity; dock via `motion` layout only when motion is allowed | none |

- Frequency: first ever launch = this storyboard, interruptible by tap/Esc/Enter/Space at any time (skip hint appears at 0.6 s as small text "Skip" in the user's saved language or Uzbek by default); cold start of installed PWA afterwards = shots 3 + 6 only (about 0.6 s: static symbol, third-node pop + ring, fade), ends as soon as the app is ready and never later than 1.2 s; warm resume / route change = none. Optionally re-show the full intro after an app update or 90 days away (judgement, not sourced).
- Never gates content: render the app underneath at once; if the bundle is slower than the animation, hold on a static symbol with a subtle carrot ring loop (Android guidance: loop if startup is slow) instead of a spinner; overlay `aria-hidden="true"`; not `inert`.
- Build: inline `<style>` + `<svg>` in `index.html` (about 1-2 KB), keyframes on `transform`, `opacity`, `stroke-dashoffset`, no `backdrop-filter`; a tiny inline script reads the saved theme and first-run flag (`localStorage`, try/catch) before first paint and removes the node when finished; React takes over for docking and onboarding via `motion`. No Lottie/Rive.
- Sound design (original synthesis, reuse `audio.py` voices `s_pop`/`s_tap`/`s_chime`/`s_whoosh`): `sting` about 1.2-1.3 s total, peak <= -6 dBFS, soft attack; export AAC/M4A (about 10 KB at 64 kbps; arithmetic mine) plus an Ogg/Opus alternative if wanted, lazy-fetched only after audio is allowed, or generate the same notes live with Web Audio oscillators (0 KB, slightly thinner). `tap` about 0.15 s for primary buttons. Rules: never play before `ctx.state === 'running'`; never queue late; respect iOS silent switch (leave `ambient`); respect an in-app **Sound** setting in Settings (default on, low gain) and also stay silent when the tab is not visible; total sound per launch < 3 s (WCAG 1.4.2 threshold).
- Where sound can legitimately start: (1) installed Chrome PWA at launch (documented exception), (2) after any earlier tap in the session, (3) on the first tap in the first-run flow (language button / "Boshlash"), using `tap` + a shortened 0.6 s echo of the chime synced to the button's own micro-animation.

**(b) Reduced-motion and accessibility fallback**
- `@media (prefers-reduced-motion: reduce)` in the inline CSS: show the **final static logo** (symbol + wordmark) with a 200 ms opacity fade-in, hold 600 ms on first run (0 ms on later runs), 200 ms fade-out; no scale, no draw, no pulse, no dock. Opacity changes are explicitly not "motion animation" under WCAG 2.3.3.
- Add a Settings control "Animation: follow system / reduced" wired to `MotionConfig reducedMotion` (`"user"` vs `"always"`) so users without OS settings can opt out (WCAG 2.3.3 technique "user setting"), plus the **Sound** toggle.
- Skip: tap anywhere, Esc, Enter, Space; no focus trap; screen reader gets nothing from the overlay (the app title announces itself); no flashing; one background colour for the whole intro; contrast: carrot used only as a graphic accent.
- Test plan: Playwright (already a dev dependency) with `reducedMotion: 'reduce'` and with prefers-color-scheme dark; axe-core scan of onboarding screens; Lighthouse/Web Vitals check that the intro does not worsen LCP/CLS; manual test on a real low-end Android phone; unit test that the first-run flag suppresses the full intro on second launch.

**(c) First-run flow (screens, copy intent; final texts via `t('key')` in uz/ru/en, owner approves wording)**
1. *Language* (after intro): title in three languages; buttons "O'zbekcha / Русский / English" (own-language labels), no auto-detect, none pre-selected; if Uzbek: two chips with live sample "o' g' sh ch" vs "ö ğ ş ç" (hamroh topish / hamroh topiş), 1995 selected by default until 2027-04-22 (2026 afterwards); line "Change later in Settings". One tap + Continue. Plays `tap`.
2. *Card 1, Find*: "Profiles show languages, services and prices openly." Illustration: city skyline line-art with a carrot route/pin.
3. *Card 2, Ask*: "Choose a service, time and meeting place and send a request. Payment step opens only after the companion accepts." (no fee/cancellation/refund statements; follow the product rules). Illustration: calendar + two avatars.
4. *Card 3, Meet safely*: public places only; applications are reviewed; Verified badge appears only when confirmed by the server and is not a guarantee; in danger call 112; SOS records an alert for review and helps you call or message from your own phone; Yondo does not dispatch help. Buttons: **"Start"** (primary -> public Discovery), "Sign in" (secondary), link "I'm a companion" (-> login -> Account -> roles), link "Watch the 75 s guide" (opens video on tap, not autoplay).
5. *Contextual hints* (max three, pull-style, dismissible, persisted): first Discovery visit (filters and availability), first profile (service/time/place request), first booking (status timeline: pending -> accepted -> pay -> confirmed). Re-run from Help.
6. *Help -> Guide*: the three cards + the video + "Show hints again".
- Constraints: total first-run <= 4 screens and about 20 s; Skip on every card; progress dots; Back; each card stands alone; no permission prompts at all; consent stays at login (existing `ConsentCheck`).
- Companion path (Studio): a short setup checklist (profile, photos, services, availability, submit for review) with progress, because it is genuinely multi-step; separate from customer onboarding.
- Measurement (own events, privacy-respecting; analytics presence in the repo not verified): intro shown/skipped, language chosen, alphabet chosen, card reached/skip, "Start" vs "Sign in", hint dismissals, video play/finish.

**(d) Tutorial video outline (about 75 s; 9:16 and 16:9; uz and ru; owner voices from voicelab.uz; no romantic imagery; ink/paper/carrot; captions via optional track, not burned in)**

| # | Time | Scene | Visual (reuse `apps/web` captures + line-art layer) | Voice intent |
|---|---|---|---|---|
| 1 | 0-6 s | Hook | Y-fork draws itself (the intro), then Tashkent skyline line-art | A: "New city? Find a companion in three steps." |
| 2 | 6-22 s | Find | Discovery list, filters (language, service, availability), open a profile: services and prices visible | A (+ C short line: "My languages, services and prices are in my profile") |
| 3 | 22-42 s | Ask | Choose service, time (shown in Tashkent time), meeting place; send request; companion accepts; payment step opens only then | B: "I sent the request"; A explains the order |
| 4 | 42-62 s | Meet safely | Public square line-art; Verified badge (server-confirmed, not a guarantee); report via booking; SOS button and 112 | C: "Meetings are in public places only"; A: SOS records a signal, in danger call 112 |
| 5 | 62-75 s | Make it yours + end card | Settings: language/alphabet, day <-> night theme (ink/paper); end card logo + slogan "Yondo doim yoningda" | A: close line |
- Production: extend `marketing/ad-video` (`timeline.json`, `build_page.py`, `render.mjs`, `audio.py`, `mux.sh`); reuse the same cast (A narrator, optional B and C); voices are generated by the owner and uploaded (voicelab.uz unreachable from the sandbox); 30 fps, H.264 + AAC, loudnorm -14 LUFS; export 720p web versions (about 6-12 MB each) plus a poster JPG; keep in-frame step titles so the video works muted. RU cut shows the app in RU locale; UZ cut in the user-selected alphabet where possible (otherwise 1995).
- Delivery: self-hosted files under the app origin (or the future storage adapter), `<video controls playsinline preload="none" poster=...>`, optional `<track kind="captions">` in uz and ru WebVTT.

### Gaps
- Owner decisions needed: (1) manifest `background_color` paper vs ink; (2) whether the in-app guide may have an optional captions track despite the ad's "no subtitles" rule; (3) default for the Sound setting (proposal: on, low gain, silent when device is muted); (4) whether the full intro should re-run after updates/long absence; (5) final Uzbek/Russian copy (this spec gives intent only).
- Not verified: iOS standalone audio behaviour, wordmark path structure for per-letter reveal, presence of analytics, web push, and any measurement on real low-end Android devices.

---

## 11. Plain 10-line summary and recommendation

### Takeaway
Build first-run onboarding plus a silent-first, interruptible 3.4 s intro (first launch only), then add the sound layer, the PWA manifest and the 75 s guide video.

### Cited Findings
Ten-line summary (sources in the sections above):
1. Launch animation guidance is tiny: Android caps the splash animation at about 1 s and dismisses at first frame; a 3-4 s intro is OK only once, skippable, and never delaying content ([Android](https://developer.android.com/develop/ui/views/launch/splash-screen), [NN/g response times](https://www.nngroup.com/articles/response-times-3-important-limits/)).
2. Browsers do not allow sound at launch without a gesture; the documented exception is an installed/home-screen Chrome app, and iOS silences Web Audio with the ringer switch by default ([Chrome](https://developer.chrome.com/blog/autoplay), [MDN](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay), [WebKit](https://webkit.org/blog/7734/auto-play-policy-changes-for-macos/)).
3. WCAG: automatic motion over 5 s in parallel needs a pause control, audio over 3 s needs a stop/volume control, and `prefers-reduced-motion` (opacity-only fallback) is the standard technique ([2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html), [1.4.2](https://www.w3.org/WAI/WCAG22/Understanding/audio-control.html), [2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)).
4. Technology: inline CSS/SVG for the boot intro and `motion` (already shipped) for in-app moments; dotLottie/Rive add a 0.15-0.57 MB WASM runtime (figures conflict) for no benefit here ([Rive sizes](https://rive.app/docs/runtimes/runtime-sizes.md), [LottieFiles](https://lottiefiles.com/dotlottie)).
5. Onboarding evidence: NN/g found tutorials gave no success gain and felt harder; vendor benchmarks say keep tours to 5 steps or fewer and let users trigger them ([NN/g](https://www.nngroup.com/articles/mobile-tutorials/), [Chameleon](https://www.chameleon.io/benchmark-report)).
6. Yondo first-run: language (plus Uzbek alphabet) -> three cards (find, ask, meet safely) -> public Discovery -> contextual hints; Skip everywhere; no permission prompts; role choice stays in Account ([repo](file:///D:/Yondo/apps/web/src/pages/Account.tsx)).
7. Tour libraries: skip for now; if needed use driver.js (MIT, ~5 KB) or react-joyride 3 (MIT, React 19); Shepherd and Intro.js need paid licences for commercial use ([driver.js](https://github.com/kamranahmedse/driver.js), [Shepherd](https://github.com/shipshapecode/shepherd), [Intro.js](https://introjs.com/docs/getting-started/license)).
8. Video guide: about 75 s, uz and ru, 9:16 and 16:9, self-hosted 720p MP4 (about 6-12 MB), tap-to-play, optional captions track; produce with the repo's `marketing/ad-video` pipeline ([Wistia](https://wistia.com/blog/optimal-video-length), [ad-video README](file:///D:/Yondo/marketing/ad-video/README.md)).
9. PWA layer is missing (no manifest, no service worker); it is needed for the OS splash, installed-app sound and iOS standalone ([web.dev](https://web.dev/articles/add-manifest), [repo](file:///D:/Yondo/apps/web/index.html)).
10. Not verified: Spotify/Headspace/Yandex Go behaviour, Apple HIG wording, iOS standalone audio, real low-end device performance.

### Inferences
**Recommendation (build order):**
1. First: first-run flow (language/alphabet + 3 cards + Help replay) together with the silent CSS/SVG boot intro and its reduced-motion fallback (small-to-medium effort, no external dependencies, biggest trust/comprehension gain).
2. Second: Sound (sting + tap) behind a Settings toggle, plus the Animation setting.
3. Third: web manifest + service worker (also unlocks installed-app sound and a seamless OS splash).
4. Fourth: contextual hints and the companion setup checklist.
5. Fifth: the 75 s guide video in uz then ru (needs the owner's voice files), embedded in Help.
6. Defer: tour library, Rive/Lottie, native splash.

### Gaps
- Effort sizes above are judgement, not measured estimates.
- All acceptance numbers (3.4 s, 0.9 s, 4 screens, 75 s) are design proposals to be validated with real users, not research findings.
