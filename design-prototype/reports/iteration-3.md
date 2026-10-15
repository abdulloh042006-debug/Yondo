# Iteration 3 — Product UX (prototype)
**Critique (defects found by code review + test):**
1. Dead end: after booking creation and closing the success sheet there was no way back to the booking.
2. Sheet did not take focus, did not trap Tab, lost focus after every chip re-render.
3. If every slot today was taken (late evening) the user saw only disabled chips, no explanation.
4. Success sheet had no explicit close button (found by the test failing).
**Changes:** "Mening bronim" entry on Discover until review is sent; focus moves into sheet, Tab wraps, focus restored on close and preserved across chip re-render; message "Bu kunda boʻsh vaqt qolmadi"; "Keyinroq" button added.
**Re-test (jsdom, run):** 37 → 43 passing assertions, no runtime errors. Includes late-clock simulation (21:00). One earlier FAIL was a wrong expected value in my test (gift total is 368 000), corrected.
**Not tested:** real browsers/devices, screen readers, search quality with real data, Uzbek copy by a native speaker.
