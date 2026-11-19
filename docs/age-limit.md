# 18+ age limit

The owner decided on 2026-11-19 ("roziman 18+ cheklov qoying"). The CEO decided the details the same day.

## Rules

- **Everyone is 18+.** The age is computed on the UTC date: `apps/api/src/yondo_api/auth/age.py`.
- **Registration.** The username + password step (`POST /auth/registration`) takes `date_of_birth`.
  - When `YONDO_AUTH_REQUIRE_DATE_OF_BIRTH=true`, the date is required (`date_of_birth_required`).
  - A date that is given is always checked:
    - `invalid_date_of_birth` for a future date or one more than 120 years ago;
    - `age_restricted` (403) for anyone under 18.
- **A new sign-up under 18 leaves no account.**
  - The row created by the code sign-in is erased at once, the same way as an account deletion.
  - Only a **salted hash of the phone number** (`age_blocks`) is kept, with a **30-day cooldown**. Any new account for that number is refused with `age_restricted` during that time: code, password reset, Telegram, Google. This stops an instant retry with another date.
  - The hourly job (`python -m yondo_api.jobs`) prunes ended cooldowns.
- **Existing accounts** (made before the limit) give their date of birth once, at the next sign-in (`PUT /auth/date-of-birth`).
  - While the gate is on, everything except `/auth/` and `/legal/` answers `date_of_birth_required` until they do.
  - If the date given is under 18:
    - the date is **not stored**;
    - the account gets `age_restricted_at` and stays **locked**. A second try with another date is refused, and everything except `/auth/`, `/legal/`, the support form and account deletion answers `age_restricted`;
    - the screen explains this and offers support (an admin checks the ID) and self-service account deletion.
  - An admin clears the flag after the ID check with `POST /admin/users/{id}/age-restriction/clear {reason}`. Who cleared it, when and why is written to the admin audit log. The user then enters the date again.
- **The date of birth is private.** Only its owner sees it (`/auth/me`). Other users see only the age, where the age was already shown (discovery). Once a date exists, the age follows it and can no longer be edited in the profile.
- **Companions: ID review.** Approving an ID verification needs `adult_confirmed: true` ("18+ confirmed from the ID"); otherwise the API answers `adult_confirmation_required`.
- **Terms and Privacy** contain the 18+ clause. Both versions are now `2026-11-19-draft`, so every user is asked to accept them again.

## Be honest about what this checks

A date of birth typed at registration is a **declaration**: the app cannot know whether it is true. The cooldown and the lock only stop the easiest retries. The strong check is the **ID review for companions**, where an admin sees the document. Customers are not ID-checked today.

## Owner step

Set `YONDO_AUTH_REQUIRE_DATE_OF_BIRTH=true` in Render, next to `YONDO_AUTH_REQUIRE_PASSWORD_SETUP=true`.
- The seeded DEMO accounts (and the well-known test admin) have a fixed adult date.
- The owner's own admin number (`YONDO_DEMO_ADMIN_PHONE`) has none: he enters his real date once.
