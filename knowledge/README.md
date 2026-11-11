# Knowledge base for the Yondo AI assistant

Source documents the assistant may answer from. Plan and decisions: `docs/ai-assistant/phase-a-audit.md`.

| Folder | Who can get answers from it |
|---|---|
| `public/` | Everyone in Public mode: customers, companions and anonymous visitors (decision Q3). |
| `internal/` | Internal mode only. The server gates it with the admin role (`companions/dependencies.py`, decision Q4). |
| `shared/` | Both modes. |

## Document format

One Markdown file per document. Subfolders are allowed, e.g. `public/faq/`. Files named `README.md` are not documents.
Each document starts with TOML front-matter between `+++` lines, followed by one `## <language>` section for each declared language:

```
+++
id = "faq.pay"                      # unique lowercase slug: a-z, 0-9, "-" or "."
title = "How does payment work?"
audience = "public"                 # public | internal | shared; must equal the top folder
languages = ["uz", "ru", "en"]      # one "## uz" / "## ru" / "## en" section each, none empty
category = "faq"                    # lowercase slug
status = "review"                   # draft | review | approved | deprecated
version = 1                         # integer >= 1; bump when the text changes
source = "apps/web/src/i18n/{uz,ru,en}.ts: help.faq.pay.*"   # where the text comes from
updated_at = 2026-11-10             # date, YYYY-MM-DD
+++

## uz
...
```

- Uzbek text is written in the **2026 alphabet**, the same as `apps/web/src/i18n/uz.ts`. Answers follow the user's chosen alphabet (decision Q8).
- **Only `status = "approved"` documents are indexable.** Draft, review and deprecated documents are validated but are never used for answers.
- **Approval:** the CEO approves a document after an independent verifier review (decision Q5), by changing `status` in a reviewed PR.
- **Allowed content:** product help and policy text that is already approved elsewhere. Never put in personal data, user content, secrets or invented business rules (fees, refunds, cancellation terms, payouts). Unset rules stay "Aniqlanmagan".

- Text before the first `## <language>` heading is ignored: it is never indexed or shown.
- In each language section, a first line `### <question>` becomes the answer title; the rest is returned **verbatim** as the answer.

## Index and answers (AI assistant, retrieval only)

```
cd apps/api
python -m yondo_api.assistant.index            # or --root /path/to/knowledge
```

- **What gets indexed:** only `approved` documents go into the `assistant_sections` table, one row per document and language.
- **Updates:** a row is rewritten only when its content changes (content hash). Rows of documents that are no longer approved, or no longer exist, are removed.
- **Refuses on errors:** while `kb --check` reports any error, the indexer refuses to run and changes nothing.
- **Where it looks:** the folder comes from `YONDO_ASSISTANT_KB_ROOT`. It defaults to this repository's `knowledge/`; set it where the code runs without a checkout, e.g. the Docker image.
- **Answers:** `yondo_api.assistant.retrieval.answer()` returns the best-matching section **verbatim**, with its source. If no section scores at least `YONDO_ASSISTANT_MIN_SCORE` (default 0.55), it returns "not found" (the client points to Help). Nothing is generated and nothing leaves the server.
- **Who sees what:** public mode sees `public` and `shared` documents only.

## Check

```
cd apps/api
python -m yondo_api.assistant.kb --check
```

The check prints a summary and exits 1 on any invalid document. Tests: `apps/api/tests/test_assistant_kb.py`. These tests also check that every `public/faq/*` document matches the Help FAQ strings in `apps/web/src/i18n` exactly.
