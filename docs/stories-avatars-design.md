# Stories and avatars: design spec (S39 draft)

Status: design only. Nothing here is built in `apps/web`. The **story endpoints exist** (`apps/api/src/yondo_api/stories/`, openapi-v1.json); the **avatar API does not exist** (`users.avatar_code` is PLANNED). Live preview: `design-prototype/brand/avatar/preview.html` (day/night, 390 px to desktop, contrast table computed live). The preview also holds the reference generator (plain JS) to port to TS.

Rules kept: ink `#111111`, paper `#F5F2EC`, carrot `#E8501A` only; carrot is a graphic fill, never text. Meaning is carried by words, not colour. No faces, no people, no romantic imagery (not a dating or escort product). All UI text through `t('key')` (uz, ru, en). Sample data marked DEMO. `prefers-reduced-motion` respected.

## 1. Customer avatars (no photos)

Customers have no photo. Each account gets a geometric ornament (Uzbek pattern vocabulary: star, almond/bodom, zigzag/adras, pomegranate/anor), drawn on a circle.

- **12 patterns x 3 grounds (ink, paper, carrot) x 2 folds = 72 combinations, 69 distinct looks** (the pomegranate is mirror-symmetric, so its fold changes nothing). ids: `star8 star10 bodom8 rhomb4 chain strap8 lattice bodom quatrefoil hex7 adras anor` (this order is the index).
- **Default pick** (deterministic, same on every device, no server state):
  `h = FNV-1a32(accountId)`; `pattern = h % 12`; `ground = floor(h/12) % 3` (0 ink, 1 paper, 2 carrot); `fold = floor(h/36) % 2`. FNV-1a: `h = 2166136261; for each UTF-16 unit c: h = imul(h ^ c, 16777619) >>> 0`.
  Fold 1 = the motif rotated by `STEP[pattern]` degrees (22.5, 18, 22.5, 45, 45, 22.5, 45, -, 45, 30, 90, -); `bodom` is mirrored instead (`translate(48 0) scale(-1 1)`), `anor` has no fold. So two accounts with the same pattern and ground mostly still differ.
- **Test vectors** (must match in TS and in any server copy): `7c1d6f0e-5b6a-4d0e-9b53-1a2f3c4d5e61` -> bodom8, paper, fold 1; `c0ffee00-0000-4000-8000-00000000a001` -> lattice, paper, fold 1; `demo-customer-1` -> anor, carrot, fold 0; `b2a9e8d4-77aa-4c10-8f3e-0f9d5c2a1b77` -> anor, ink, fold 1 (drawn like fold 0). Over 60 000 random UUIDs each pattern landed 4886 to 5075 times (expected 5000), grounds 19.9k/20.1k/20.0k, folds 30.1k/29.9k.
- **Sizes**: 32 (rows, chat, top bar), 44 (cards, touch size), 64 (profile header, story ring inner), 96 (Settings picker). Drawing grid 48 units; every shape is at least 3 units (2 px at 32). Under 44 px the *fine* layer is not drawn (CSS `--fine:none`); at 44 px and up it is.
- **Contrast**: ink/paper 16.9, carrot/ink 5.03, carrot/paper 3.36 (graphic only, passes 3:1 for non-text). Text on a carrot ground is ink only (5.03, AA); paper on carrot (3.36) is never used for text. A 1 px ring of 30 % ink/paper separates the circle from its background.
- **Accessibility**: decorative next to a name (`aria-hidden`); standalone (Settings picker, profile header) `role="img"` with `t('avatar.label', {pattern})`.
- **Companions** keep their photo. When `photo` is null (profile has none, or a story ring has none) the same art is the fallback, seeded by the **profile id**.

### Planned avatar field (NOT BUILT)

- `users.avatar_code` `VARCHAR(24) NULL`, default null = "automatic". Format `<pattern>.<ground>.<fold>`, e.g. `anor.ink.1`; allowed values are the 72 combinations, validated server-side (422 otherwise). A client that meets an unknown code falls back to the derived look.
- Exposed on the current-user response and written through the same account-settings write that already stores `users.ui_locale`; the backend agent picks the exact route. Adding it needs a migration, tests and `python export_openapi.py` (CI contract).
- Settings (later): "Avatar" group, radiogroup of 36 tiles + a fold toggle + "Automatic" (sets null). Not part of the first slice.
- **Privacy**: the client may derive from the *viewer's own* account id. For another person (a companion looking at a booking request) the API must send the effective code (explicit, else server-derived with the same algorithm), never the customer's user id (CLAUDE.md section 4: user ids are not shared).

## 2. Stories (companion cards, 24 h)

Server facts this design follows (`stories/schemas.py`, `router.py`, `service.py`):

| Item | Value |
|---|---|
| Kinds | `availability`, `note` (`StoryKindName`) |
| Write | `POST /api/v1/companions/me/stories` `StoryWrite {kind, caption<=80, photo_id?, service_id?}`; owner's own photo and service only |
| Own list / delete | `GET /companions/me/stories` (last 3 days, `state` active, expired, removed, `removal_note`), `DELETE /{id}` 204 |
| Rings | `GET /api/v1/discovery/stories?limit=1..50 (30)` -> `StoryRing {profile_id, display_name, verified, photo?, count, latest_at, has_availability}` |
| Slides | `GET /api/v1/discovery/companions/{profile_id}/stories` -> `StorySlide {id, kind, caption, created_at, expires_at, photo?, service?, windows[{starts_at, ends_at}]}` |
| Report | `POST /api/v1/discovery/stories/{id}/report` (sign-in needed) `{category: inappropriate_request, fake_profile, fraud, other; description<=500}` -> 201 |
| Admin | `GET /stories/admin`, `POST /stories/admin/{id}/remove {note 3..500}` (admin console, out of scope here) |
| Limits | life 24 h (`stories_ttl_hours`, max 72), 5 active, 10 per day; windows: at most 3, each at least 30 min, next 24 h, recomputed on every read |
| Public reading | no sign-in, **no viewer is ever recorded** |

Error codes to branch on (never on message text): `story_profile_not_active` 409, `story_caption_required` 422, `story_caption_contact_info` 422, `story_limit_reached`, `story_rate_limited` 429, `story_no_free_windows` 409, `story_not_found` 404, `story_already_reported` 409, `invalid_report` 422 (own story), `companion_not_found` 404.

### Ring (home strip, profile header)
- One arc per active card (`count`, 1 to 5), 14 degree gaps. **Unseen**: 3 px carrot arcs. **Seen**: 1.5 px arcs, ink or paper at 60 % (4.76:1 on paper, 6.56:1 on ink). Seen state lives in `localStorage` per `profile_id` + `latest_at` only; never sent to the server (no viewer tracking).
- `has_availability` adds a small carrot dot at the lower right **and** the text chip `t('stories.hasFreeTime')` under the name (the dot alone carries no meaning). The verified badge is drawn only from `verified: true` (API), never assumed.
- Ring is a button (44 px minimum), label `t('stories.open', {name, count})`. Order = server order (newest first). Draw-in 500 ms ease-out, off under reduced motion.

### Viewer (9:16 on phones, 360 px card centred on desktop)
- Top: one progress segment per slide (`role="img"`, "card 2 of 3"), header = avatar 32, name, verified badge, age from `created_at`, Pause and Close (44 px each).
- `availability` card: optional photo under a **78 % ink scrim** (paper text 8.58:1 even over a white photo), `service` name as title, caption, up to 3 windows as rows (local time from the UTC instants, `Bugun`/`Ertaga` labels via i18n), button `t('stories.book')` -> opens the companion profile/booking flow with `service_id` preselected. A story never creates a booking; the 5-field booking create and conflict checks stay as they are, windows are hints only. If `windows` comes back empty the card shows the caption only (window list hidden).
- `note` card: carrot ground, ink text 26 px, caption only (at most 80 chars). Photo optional with the same scrim rule on an ink ground.
- Controls: tap right/left or Arrow keys = next/previous, Esc or swipe down = close, press-and-hold or the Pause button = pause. Auto-advance 6 s (note) / 8 s (availability); **under reduced motion no auto-advance**, progress is static, manual next only. Focus trap in the dialog, focus returns to the ring.
- Footer: `Report this card` (flag + text, 44 px) -> sheet with the 4 categories and an optional description; success text "sent for review", `story_already_reported` shown as "already sent". Reports go to manual review: never claim anything was removed or the author was told.
- Guests can read; the report action asks to sign in first.

### Companion screen "My cards"
- List from `GET /companions/me/stories`: state chip in words (Active, Expired, Removed) with ink fill / ink outline at 55 % / **2 px carrot outline**; removed rows show `removal_note` as "Reason: ..." (no colour-only status). Delete button only on active rows, with a confirm.
- Composer: kind switch, caption with a live counter `n/80`, own photo picker (existing photos), own service picker (availability). There is **no preview endpoint**: show caption/photo preview, and say "free times are worked out when you post" (`t('stories.windowsHint')`). Map errors above to inline text; `story_caption_contact_info` says links, handles and long numbers are not allowed (the server rule: links, `@handles`, domains, more than 6 digits). Quota: show "x of 5 active" from the list.
- Needs an active public profile; otherwise show the `story_profile_not_active` explanation and no composer.

## 3. Build plan for apps/web (not started)

New files only, small: `src/components/avatar/avatarArt.ts` (pure `pick`, `symbols`, from the preview script), `Avatar.tsx` (inline `<svg><use/>`, sprite injected once), `StoryRing.tsx`, `StoryViewer.tsx`, `OwnStories.tsx`; hook `useStories()` on the generated API types. i18n keys under `avatar.*` and `stories.*` in uz.ts (2026 spelling), ru.ts, en.ts.

Acceptance (all must be run, not assumed): unit test with the four vectors above and the 12/3/2 range; `axe` clean on ring, viewer, own list at 360 and 1440 in both Yondo themes; keyboard-only pass of the viewer; reduced-motion pass (no auto-advance); 390 px has no horizontal scroll; no text smaller than 12 px; no carrot text.

## 4. Open points for the owner
1. Auto-advance timings (6 s / 8 s) and whether notes may carry a photo.
2. Avatar picker in Settings now or later (default stays automatic).
3. Whether companions may see a customer avatar at all before a booking exists (affects only the privacy line in section 1).
