# REPLY — paste this into the other (cloud) chat that wrote the decision brief

Owner's answers (2026-10-28). I already recorded them on `design/prototype` (commit after `fcc3daf`: CLAUDE.md §7 "Interim decisions … S35", `docs/decision-brief-2026-10-28.md` decision #11, `docs/payments-tezcheck.md`, WORKLOG S35). Pull `origin/design/prototype` first; do not redo them.

## What the owner decided
1. **Hosting for now: DigitalOcean**, which he called "free". It is not free by itself: new/student **credits** only (GitHub Student Pack: official page says $100 for 1 year, forum posts say $200; a marketing line says $200 for the first 60 days — none verified for 2026), card or PayPal required, **acceptance of Uzbek cards unverified**. Fallback if the card fails: a Tashkent VPS paid in UZS. Keep Render + Neon as the public demo.
2. **TezCheck accepts individuals (yakka shaxs)** — the owner says this is why he chose it. So **no legal entity is needed for payments**; decision #11 is resolved for payments. Not written in TezCheck's public docs: ask TezCheck for written confirmation. The data **operator** name for Terms/Privacy (decision #8) is still open.
3. **Phone/SMS:** for now he uses **his own phone number** (admin and tests). Real OTP SMS for other testers comes later via a **short-code / service-SMS gateway** (Eskiz-like), **not advertising SMS**. Unconfirmed: whether OTP must use a service route, and whether an individual can sign an Eskiz contract (ask Eskiz: notify.eskiz.uz; community packages use sender "4546"; 85 UZS/SMS from a Bitrix24 listing).
4. Domain: later (no subdomain workaround). TezCheck stays implemented but unconnected until then; the DEMO payment page keeps working.

## Do now (small, no new accounts, no purchases, no secrets)
- Add a **CI check that builds the Docker image** (`infra/deploy/Dockerfile`) — the image has never been built; this was the brief's "next small step". Test it locally only if Docker is available (it is off on the owner's laptop; CI is enough). Do not change application code.
- Do **not** write a DigitalOcean deploy how-to yet: first ask the owner (one message, Uzbek) whether his card works on DigitalOcean and whether he accepts HTTP-only on an IP for internal tests until the domain exists (TezCheck webhooks and real users need HTTPS + a domain).
- Update `docs/WORKLOG.md` (entry + "Next steps"), commit, push `design/prototype`, verify the remote SHA.

## Owner decisions that are STILL OPEN (ask in this form, closed questions, one line each, with your recommended answer)
1. Domain name and registrar (later).
2. Does your card work on DigitalOcean, or do we use a Tashkent VPS paid in UZS? (recommendation for the closed beta: Tashkent VPS)
3. Platform commission — a number (never invent it).
4. Cancellation percentages.
5. Refund rule.
6. Payout to companions: method and timing (TezCheck sends funds straight to the merchant's bank; paying companions is then the owner's process).
7. Whose name goes into Terms/Privacy as the data operator (the owner personally, as an individual?).
8. Companion identity check in the beta: manual by an admin? (recommendation: yes)
9. Who reads SOS alerts, and when? (a live person is required, otherwise the SOS promise is false)
10. Gifts/vendors in the beta? (ROADMAP Phase 20 says "several vendors"; the web app has no vendor screens; recommendation: no, and update ROADMAP only if the owner agrees)
11. Real SMS for testers: which gateway, and can an individual sign (ask Eskiz/PlayMobile).
12. Approve the intro animation / onboarding / video plan in section 5 of the brief (then step D starts).

## Rules to remember
Answer the owner in Uzbek (Latin), short and plain. Never invent fee/cancellation/refund/payout rules. Never ask for secrets in chat. Do not type the owner's personal phone into the TezCheck cash-desk contact field (it is shown to payers; use a Telegram handle). Merge/PR/deploy only on explicit instruction; push `design/prototype` at the end of the session.
