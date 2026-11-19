# Ad video 5 — research (Stage 1, 2026-11-19)

Worker: Videochi 2. Scope: assess existing Yondo video work, competitor and creative research, tools, ad policy.
No rendering and no paid generation was done in this stage. Every source below was opened or returned by a web search on
2026-11-19. **Verified** = what the source itself says. **Interpretation** = my reading, to be challenged.

## 1. Existing Yondo work: what to keep, improve, never repeat

Basis: the production breakdowns `scripts/01–03`, `reel1–3/` sources, WORKLOG S62 (Higgsfield ad), `marketing/social/caption.md`,
`apps/web/src/ui/Intro.tsx`. **I did not watch the MP4s** (no media is committed), so this is an assessment of the plans, not of the
finished picture.

| Asset | Keep | Improve | Never repeat |
| --- | --- | --- | --- |
| Pipeline (`page.tpl.html` → deterministic `render(t)` → Puppeteer → ffmpeg; `audio.py` synthesis; `mux.sh` loudnorm) | Frame-exact, free, reproducible, RU switch by table | Turn the repeated parts into a shared kit (§5 of the concepts doc) instead of copying `reelN/` folders | — |
| Real `apps/web` captures (`capture.mjs`, `capture_list.mjs`, seed without "DEMO") | Real UI, illustrated portraits, `yondo` theme | Show more of what shipped since: the "Kartochkalar" feed (Saqlash / Keyingisi), likes, Help/SOS, interests filter | Showing a **price** (reel 1 lifts "dan 75 000 so‘m" / "150 000 so‘m"; new rule = no prices). Showing the verified badge from a test double |
| Reels 1–3 story arc | Hook in the first second, strong motion craft, brand palette discipline, friendly-distance rule (reel 3) | All three use the same arc (problem → metaphor → phone → logo) and the same four screens (list → profile → booking form → toast). The next ad needs a different structure and a human scene | Loneliness as the viewer's condition: "Suhbatlashadigan odam yo‘q", "Shaharda yolg‘iz emassan" (risk: "cures loneliness" reading and Meta personal-attribute review, §4) |
| No VO + no captions (S20 owner rule) | — | **Captions ON** from now on (CEO directive 2026-11-19, overrides the 2026-10-23 "no subtitles"); a VO slot in every timeline | Long kinetic-type sentences that carry the whole message (reel 3 has 3-line, 54 px lines) |
| Higgsfield ad (S62: 23 s, 3 Seedance shots: alone at a cafe window, two people walking, hands and tea; opens on the happy walk, then "one hour earlier") | Hook-first structure; the owner-generates / agent-edits route; 5 s shots | Its scripts are **not in the repo**: write every generated shot into the prompt pack so it can be repeated | "Hands and tea" close-ups and a sad solo window shot: closeness + melancholy reads romantic/therapeutic |
| `caption.md` | One caption for all posts, no dating hashtags | Opening question "…topish qiyinmi?" addresses the viewer's situation (borderline personal-attribute style). "Uchrashuvlar faqat jamoat joylarida" is a promise the app cannot enforce: say "jamoat joylarida uchrashish tavsiya etiladi" or what the app really does | — |
| Opening animation (`Intro.tsx`, official symbol + outlined wordmark) | Reuse its motion as the **animated logo** of the kit, so the ad and the app open the same way | — | The girih-strap Y (not approved) |

## 2. Competitors and comparable products

### Timeleft (dinner with five strangers, weekly)
**Verified**
- Ad library analysis lists 20 ads: Google-search opener "How to meet people in my city" → "This is the actual solution";
  red pill / blue pill countdown ("best night of your life" vs "microwave pasta alone"); notification mockups "5 Strangers" →
  "Accept"; meme "Eating Pret alone at your desk is not 'catching up with someone'"; infographic "WORK → SCROLL → EAT → SLEEP /
  Break the cycle"; "You're not strangers, you're just friends who haven't met"; CTA mostly "BOOK YOUR SEAT"
  ([Runneth/Motion ad library](https://runneth.com/library/timeleft)).
- Static ad: neon sign "Less scary when you're all there for the same reason." (same source).
- Meta ad copy "Tired of swiping? Try Dining!" ([Business Insider](https://WWW.BUSINESSINSIDER.IN/irl-social-startups-combat-loneliness-among-millennials-gen-z-2024-5)).
- Own blog: "the antidote to big city loneliness" ([timeleft.com](https://timeleft.com/post/timeleft-the-antidote-to-big-city-loneliness/)); press: [RTÉ](https://www.rte.ie/lifestyle/living/2024/0319/1438734-would-you-dine-with-5-strangers-this-new-app-will-set-you-up), [Axios](https://www.axios.com/local/columbus/2024/08/23/making-friends-app-columbus-ohio).

**Interpretation**
- Volume + variety: many cheap formats (UGC talking head, static meme, UI mockup) tested in parallel. The winning hooks name a
  **routine** (desk lunch, scroll loop, cancelled plans), not a feeling.
- "Less scary when you're all there for the same reason" = the shared-purpose insight. It fits Yondo exactly: a meeting with a reason
  (museum, walk) is easier than "meeting a person".
- What Yondo must not copy: "antidote to loneliness" (health-like claim), "best night of your life" (promise), anti-swipe digs that pull
  the dating frame into the ad.

### Bumble BFF (friend matching, standalone app since 2025)
**Verified**: relaunch framed as "The Great Friennaissance" / "Find your people"; Groups for shared interests and local events; Bumble
research "55% of 18–35s want more local friends" ([Fast Company SA](https://fastcompany.co.za/fast-company/business/2025-09-19-bumbles-new-bff-app-aims-to-spark-the-great-friennassance));
India "Find Real Friends" campaign normalising new friendships in adult life ([afaqs](https://afaqs.com/news/industry-news/bumble-bff-launches-campaign-championing-real-friendship)).
**Interpretation**: BFF still carries the dating parent's swipe/profile grammar. Yondo should avoid profile-swipe visuals in ads and
show **the activity** first, the app second.

### Showaround (locals show travellers around, paid by the hour)
**Verified**: "Find a local to show you around" / "Meet your local guide"; browse locals, filter by language/activity, chat, locals set
hourly prices; it says it does not offer professional guide services ([showaround.com/press](https://showaround.com/press),
[App Store](https://apps.apple.com/app/id1001885430)).
**Interpretation**: the closest business model to Yondo (a person + their time + a place). Its framing is **the city**, not the person.

### Withlocals (private tours with local hosts)
**Verified**: "Enchanting experiences, with incredible locals"; "Enjoy a city like a local"; "Travel deeper. Travel locally."; every
experience private, "just you and your local host" ([withlocals.com help](https://helpcenter.withlocals.com/en/articles/627960-what-is-withlocals),
[App Store](https://apps.apple.com/us/app/id655695313)).
**Interpretation**: paid one-to-one time with a person is presented as **an experience with a named activity**. That is the honest,
policy-safe vocabulary Yondo should use too.

### RentAFriend (paid platonic companionship)
**Verified**: "strictly a platonic Friendship website… NOT a dating website, and NOT an Escort agency"; physical contact prohibited;
press frames it as a curiosity ([Dayton Daily News](https://daytondailynews.com/news/national/rent-home-rent-car-rent-friend-online-service-offers-platonic-friendship-price/DhG8fBBbMnG9r0tEGb2z0M),
[Huck](https://huckmag.com/article/inside-the-moral-maze-of-friend-rental-services)).
**Interpretation**: the cautionary example. "Rent a friend" invites jokes and suspicion; leading with denials ("not dating, not escort")
makes viewers think of exactly that. Yondo should **never** say "do‘st ijarasi" and should show what it is rather than what it is not
(the "what Yondo is not" concept in the concepts doc keeps the denials to one line).

### Others: 222, Pie, Meetup
**Verified**: 222 groups strangers by a personality test for events; Pie groups RSVPs into tables of six; these apps "rely heavily on
Instagram and TikTok… with ads that target lonely people" ([Fast Company on 222](https://fastcompany.com/91356813/222-aims-to-end-loneliness-by-engineering-chance),
[TechCrunch on Pie](https://techcrunch.com/2025/03/04/andy-dunns-new-app-pie-uses-ai-to-help-you-make-friends), [CBC](https://www.cbc.ca/lite/story/1.7622111));
Meetup's own pages use "Find your people" ([meetup.com](https://www.meetup.com/start/organizing)).
**Interpretation**: the category is crowded with "loneliness" ads. Owning **"the plan / the activity"** instead of "the lonely person" is
both a differentiator and policy-safer.

## 3. What Yondo should learn, and do differently
| Learn | Do differently |
| --- | --- |
| Name a concrete routine or object in the hook (Timeleft desk lunch, scroll loop) | Our object = **an unused plan / a place**, never a sad person |
| Shared purpose lowers the fear ("same reason") | Every scene has a named activity: muzey, sayr, kino, shaxmat, kafe |
| Many cheap variants beat one expensive film | Kit-based production (one kit, many 15–30 s cuts) |
| Locals-as-hosts framing (Showaround, Withlocals) | Shown honestly: a companion's profile, interests, a booking request |
| UI mockups as social proof (notification ads) | Only **real** `apps/web` captures, no invented notifications |
| — | No anti-dating jokes, no "rent a friend", no loneliness cure, no "100% xavfsiz", no prices |

## 4. Ad-policy check (paid ads)

| Platform | Verified text | What it means for Yondo |
| --- | --- | --- |
| Meta (FB/IG) | Dating ads need prior written permission; allowed without it: "Social apps without matchmaking elements, such as meetup apps"; prohibited: "Dating based on monetary or other financial transactions" ([Dating ads](https://transparency.meta.com/policies/ad-standards/restricted-goods-services/dating-ads/)). Ads must not "assert or imply personal attributes"; "Are you 18 years old?" / "Do you have diabetes?" are not allowed ([Personal attributes](https://transparency.meta.com/policies/ad-standards/objectionable-content/privacy-violations-personal-attributes/)) | Yondo is not matchmaking, so the meetup-app route is plausible, but companions are **paid**, which a reviewer may read as "financial transaction" companionship. Copy must not ask "Yolg‘izmisiz?", "18 yoshdamisiz?". "18+" as a label is fine |
| TikTok | Prohibited: "Sugar dating, or any type of engagement in companionship or relationships in exchange for compensation or material benefit" ([Adult content](https://ads.tiktok.com/help/article/tiktok-ads-policy-adult-content?lang=en)); NA handbook also lists "transactional companionship" ([handbook](https://ads.tiktok.com/help/article/ad-policy-handbook-north-america?lang=en)); branded content globally prohibits services "focused on generating connections… interested in romance, casual sex, sexual favors, or friendship" ([branded content](https://ads.tiktok.com/help/article/branded-content-policy-country-specific-requirements)) | **High risk.** Yondo's model (a companion's time for a price) matches the wording "companionship… in exchange for compensation" literally. Paid TikTok ads and paid creator (branded) posts may be rejected. Not checked: TikTok rules for Uzbekistan specifically, and organic posts (community guidelines) |
| Google / YouTube | Since 2025-03-04 dating and companionship ads need Google certification; the policy prohibits ads that "Promote compensated companionship, dating, or sexual acts" ([Google Ads policy update](https://support.google.com/adspolicy/answer/15327789?hl=en), [Compensated sexual acts](https://support.google.com/adspolicy/answer/10212441?hl=en)) | **High risk** for YouTube ads for the same reason. Paid activity hosts (tours) advertise on Google; whether Yondo is classed as "tours/experiences" or "companionship" is the reviewer's call |

**Recommendation (for the CEO/owner, not decided by me):**
1. Start **organic** (own Instagram/TikTok/YouTube accounts); the ads are made so they are also ad-policy-clean.
2. Never disguise the model: no hiding that companions set a price, no "free friends", no fake "tour guide" label if the app says
   "hamroh". Describe it truthfully as **booking time with a companion for an activity in a public place**.
3. Before any paid spend: ask Meta (and Google certification support) in writing how they classify Yondo; skip TikTok paid ads until a
   TikTok rep confirms. Target 18+ only.
4. Copy rules used in all concepts: describe the service, never the viewer's condition; no romance, health, guarantee or safety-absolute
   claims; safety only as built (moderation, API verification badge, reports/blocks via booking, SOS = recorded alert for manual review).

## 5. Tools: what is really available here (checked 2026-11-19)
| Tool | Status | Use |
| --- | --- | --- |
| HTML/CSS → Puppeteer/Playwright → ffmpeg | **Available** (Chromium + Playwright preinstalled, `/usr/bin/ffmpeg`); used by reels 1–3 | Main motion engine, free |
| Remotion / HyperFrames (explainer-reel skill) | Not installed; npm install possible but not tried. Remotion's licence is free only for individuals/small companies (check before use) | Not needed: the existing deterministic pipeline already does the same |
| Blender | **Not installed** (`which blender` = none) | Out of scope; CSS 3D covers the 3D needs so far |
| Original synthesized sound (`audio.py`) | Available | Music bed + SFX kit |
| uzbek-tts skill | Needs a Colab GPU (owner's Google account) or a local model; edge-tts was blocked by the proxy in S54 | Draft VO only, labelled DRAFT |
| audio-ears skill | Available | QC: LUFS, true peak, silences, transcript |
| Google Flow (Veo, images) | Owner's account; owner generates and uploads | AI cinematic shots (≈25 %) |
| Higgsfield connector | Attached, read-only (cannot generate) | Optional second route, owner generates |

Sources not reachable: withlocals.com homepage (HTTP header overflow), the TechCrunch 2026-04-05 roundup (404). Not researched: local
Uzbek competitors (no source found in this pass).
