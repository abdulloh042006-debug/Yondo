# Yondo notification sound

`yondo_notify.py` synthesises the notification sound. **Original synthesis, no samples**: additive sine partials of a
struck metal bowl (inharmonic ratios 2.76 / 5.40 / 8.93), a short "droplet" sweep at the onset, a soft mallet tick,
and a small noise-based room reverb. It is deterministic (fixed seed 2026).

Owner decision 2026-11-11: **variant A "tomchi-rin"** (droplet, then a bright bowl ding, 2.4 s). B and C are kept in
the script as alternatives only; they are not shipped.

```
python tools/sounds/yondo_notify.py <out_dir>        # needs numpy; writes three 48 kHz stereo WAVs
ffmpeg -i <out_dir>/yondo-bildirishnoma-A-tomchi-rin.wav -c:a libmp3lame -b:a 128k yondo-notify.mp3
```

Only the A file, as mp3, is committed: `apps/web/public/sounds/yondo-notify.mp3` and
`apps/mobile/assets/sounds/yondo_notify.mp3` (underscore: Android resource names cannot contain "-"; it is also
the Android push channel sound). WAV files are not committed.
