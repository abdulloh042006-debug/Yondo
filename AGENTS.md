# Repository instructions for AI coding agents

## Product context and scope

- Before making product-related changes, read `README.md`, `TZ.md`, and `ROADMAP.md`.
- `TZ.md` is the source of truth for functional requirements.
- `ROADMAP.md` defines implementation order. Do not skip ahead unless explicitly requested.
- If documentation is unclear, do not invent business rules. Clearly mark the ambiguity and ask for clarification.
- If a task conflicts with `TZ.md` or `ROADMAP.md`, stop and report the conflict instead of silently choosing different behavior.
- Do not modify UX/UI or business-policy documents unless explicitly asked.
- Keep changes scoped to the requested task. Do not rewrite large parts of the project unnecessarily.
- Preserve existing working functionality and avoid duplicated business logic or unnecessarily large files.

## Working approach

Work incrementally:

1. Inspect the relevant repository structure and existing implementation.
2. Plan a small, scoped change.
3. Implement the change.
4. Run relevant tests and checks.
5. Report the outcome, decisions, and any remaining issues.

Do not mass-format unrelated existing files. Before completing an implementation task, run relevant tests, lint, and build or type checks where applicable.

## Security and sensitive data

Treat authentication, permissions, verification, payments, payouts, booking state transitions, chat and privacy, and safety/reporting as security-sensitive areas requiring extra care.

Never commit secrets, API keys, passwords, tokens, real credentials, or local `.env` files. Use `.env.example` only for placeholder configuration.

## Data, API, and implementation practices

- Database changes must use migrations. Never manually modify production data. Avoid destructive migrations unless explicitly approved.
- API changes must preserve versioning, validate inputs, use typed schemas, and return consistent errors.
- Keep implementation maintainable: avoid giant files and duplicated business logic.

## Developer environment

The primary local development environment is Windows. Keep developer instructions and commands compatible with Windows PowerShell; call out shell-specific alternatives when commands differ.

## Completion report

At the end of every implementation task, report:

- Completed
- Files changed
- Tests/checks
- Important decisions
- Remaining issues
- Recommended next roadmap phase

Determine the recommended next phase from `ROADMAP.md` and the repository's current implementation state; do not skip ahead or infer unapproved product scope.
