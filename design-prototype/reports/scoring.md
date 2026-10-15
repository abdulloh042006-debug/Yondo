# Scoring (0–10), evidence-based, updated after Iteration 5
Polish ≠ validated UX. Scores <8 are known limitations; none were inflated.
| Dimension | Score | Evidence | Defect / limitation |
|---|---|---|---|
| Originality | 5 | Y-and-nodes mark, accent node | Generic structure; no similarity search |
| Logo craft | 5 | Outlined wordmark, 4 themes, small variant | Symbol still strokes; no kerning; no print/embroidery test |
| Visual quality | 6 | 180 browser measurements, screenshots reviewed | Never seen on a real device; fonts only checked locally |
| Merch consistency | 0 | — | Not started |
| Typography | 6 | Real Inter/Space Grotesk loaded; oʻ gʻ ʼ glyphs verified | No native-speaker review |
| System coherence | 7 | tokens → components.css/js → gallery; app uses them | No Figma; only Chromium verified |
| Usability | 6 | 36 browser flows incl. error recovery | No human testing |
| Search | 6 | Filters map to real discovery params; empty/error/retry | Mock data; server ranking unknown |
| Profile conversion | 5 | Price, badge from `verified`, services, CTA | No photos; no real reviews |
| Checkout | 7 | Contract-faithful order (accept → pay), idempotency, 503 vs failed, config-missing state, test-order flags | Fees/cancellation % undefined by backend; real provider absent |
| Trust & safety | 6 | Honest SOS copy, report/block, contacts, role guard + server codes | Report target id open question; no live tracking exists |
| Responsiveness | 7 | 7 widths + dark, 0 findings | Chromium emulation only |
| Accessibility | 6 | axe 0 violations, keyboard/dialog/focus tests, measured contrast | No screen-reader testing |
| Motion | 6 | Spec durations asserted, reduced-motion verified | No frame-rate/budget-Android test |
| Dev-readiness | 7 | Build script, tests, contract validation, handoff, backend 200/200 on PostgreSQL | Mock not real API; real integration untested |
