# Yondo promo video — pipeline and script

For the owner's own viewing (not an official ad). Formats: 9:16 (1080×1920) and 16:9 (1920×1080), 30 fps,
H.264 + AAC 48 kHz, master ≈ -14 LUFS. Languages: Uzbek and Russian. Scripts use a hard-coded working folder
`AD=...` at the top of each file: change it to your folder before running.

## Cast (3 speakers, voices made by the owner on voicelab.uz)
| voice | role | lines |
| --- | --- | --- |
| A | narrator — woman, 30–40, calm, warm | 1, 3, 7 |
| B | customer — young man, 20–25, curious | 2, 5 |
| C | companion — young woman, 22–28, warm, confident | 4, 6 |

Files: `voice/uz-01.wav … uz-07.wav`, `voice/ru-01.wav … ru-07.wav` (not committed: owner's audio).

## Lines (voicelab tags in brackets)
| # | UZ | RU |
| --- | --- | --- |
| 1 A | Yangi shahar. Rejangiz bor. [short pause] Hamroh-chi? [neutral] | Новый город. План есть. [short pause] А компания? [neutral] |
| 2 B | Shaharni ko‘rmoqchiman… lekin kim bilan? [sad] | Хочу увидеть город… но с кем? [sad] |
| 3 A | Yondo — suhbat, sayr va til mashqi uchun hamroh topish platformasi. [neutral] | Yondo — платформа, где можно найти компаньона для беседы, прогулки и языковой практики. [neutral] |
| 4 C | Men hamrohman. Tillarim, qiziqishlarim, xizmatlarim va narxlarim — profilimda ochiq. [excited] | Я гид-компаньон. Мои языки, интересы, услуги и цены — открыто в профиле. [excited] |
| 5 B | Profilni ko‘rdim, narxni oldindan bildim va bron so‘rovini yubordim. [excited] | Посмотрел профиль, сразу узнал цену и отправил запрос на бронь. [excited] |
| 6 C | Uchrashuvlar — faqat jamoat joylarida. Har bir ariza ko‘rib chiqiladi. [neutral] | Встречи — только в общественных местах. Каждая заявка проходит проверку. [neutral] |
| 7 A | Yondo. [short pause] Doim yoningda. [short pause] Tez kunda! [excited] | Yondo. [short pause] Всегда рядом. [short pause] Скоро! [excited] |

## Visual rules
Only the logo colours: ink `#111111`, paper `#F5F2EC`/white, carrot `#E8501A`. App screens in the `yondo` (day) theme;
the theme beat shows day ↔ night (`yondo-tun`). No "DEMO" labels on screen (owner request); seed names have no DEMO prefix
(`server_video.py`). Verified badges are removed from captures (they come from a test double).

## Steps
1. Screens: from `apps/web` after `npx vite build`:
   `THEME=yondo OUT=<AD>/shots-yondo YONDO_PY=<venv python> node capture.mjs` and `capture_extra.mjs`; same with `THEME=yondo-tun`
   into `shots-yondo-tun`; then `ln -s ../shots-yondo-tun <AD>/shots-yondo/n`. (Copy the three capture files to `apps/web/e2e/.tmp/` first.)
   Fonts: `npm i @fontsource/{fraunces,outfit,newsreader,manrope,space-grotesk}` in `/home/claude/fonttools` (Google Fonts are blocked in the sandbox).
2. `python3 build_timeline.py` → `timeline.json` (voice placement from real durations, phrase times from pauses, SFX cue list).
3. `python3 build_page.py` → `page.html` (deterministic `render(t)` animation).
4. `node render.mjs v uz` (and `h uz`, `v ru`, `h ru`) → frame-by-frame screenshots piped to ffmpeg; `node render.mjs v uz stills 1 5 10` for checks.
5. `python3 audio.py uz ru` → original synthesized music (120 BPM, Am–F–C–G) + SFX + voices with ducking.
6. `./mux.sh v uz` … → `yondo-reklama-<lang>-<9x16|16x9>.mp4` (loudnorm I=-14, TP=-1.5).
7. `python3 mk_preview.py` → single-file HTML gallery of all screens.
