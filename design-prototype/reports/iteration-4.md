# Iteration 4 — Visual precision (STATIC checks only)
**Method:** scripted scan of CSS/inline styles + WCAG contrast computed from token values. No rendering was possible (no browser in this environment), so overflow/clipping at 360–1440 px is **unchecked**.
**Findings → fixes:** "Gul va sovgʻalar" button was 40 px tall → 44 px. Interest tags looked like tappable chips but were not → restyled as non-interactive tags (`.tg`).
**Contrast:** 26 pairs (13 per theme) computed; 0 failures (e.g. muted text on page 6.45:1, error text 5.85:1, accent graphics ≥3.36:1).
**Not done:** rendered spacing/radius/icon-size review, motion on budget Android, overflow tests, dark-theme visual check.
