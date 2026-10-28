// Generator for the "warm" proposal pages. Hand-authored SVG/CSS, no network. Run: node build.cjs [render]
// Reads the approved girih symbol + outlined wordmark from ../ornament/symbols (read-only), writes r.html / e.html.
const fs = require('fs'), path = require('path');
const D = __dirname, SYM = path.join(D, '../ornament/symbols');
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, p) => '#' + hex(a).map((v, i) => Math.round(v * p + hex(b)[i] * (1 - p)).toString(16).padStart(2, '0')).join('');
const INK = '#111111', PAPER = '#F5F2EC', CARROT = '#E8501A';
// heritage palette for direction E (<= 6 colours: ink, paper, indigo, turquoise, pomegranate, saffron)
const E = { indigo: '#26397F', turq: '#0B7478', pom: '#B3262E', saf: '#E5A12B' };
const NIGHT = mix(E.indigo, INK, 0.16);

const S = {
  'R-day': { bg: PAPER, sf: '#FFFFFF', fg: INK, mut: mix(INK, PAPER, .7), ln: mix(INK, PAPER, .14), pr: INK, onpr: PAPER, sym: INK, acc: CARROT, word: INK, a1: CARROT, a2: INK, a3: INK,
    ml: mix(INK, PAPER, .5), m1: mix(CARROT, PAPER, .2), m2: mix(INK, PAPER, .07), m3: CARROT, chip: mix(INK, PAPER, .06), solid: false,
    glow: `radial-gradient(70% 40% at 0% 100%,rgba(232,80,26,.15),transparent 70%),radial-gradient(60% 35% at 100% 0%,#fff,transparent 75%),${PAPER}` },
  'R-night': { bg: INK, sf: mix(PAPER, INK, .07), fg: PAPER, mut: mix(PAPER, INK, .72), ln: mix(PAPER, INK, .16), pr: PAPER, onpr: INK, sym: PAPER, acc: CARROT, word: PAPER, a1: CARROT, a2: PAPER, a3: PAPER,
    ml: mix(PAPER, INK, .5), m1: mix(CARROT, INK, .3), m2: mix(PAPER, INK, .09), m3: CARROT, chip: mix(PAPER, INK, .1), solid: false,
    glow: `radial-gradient(70% 40% at 0% 100%,rgba(232,80,26,.2),transparent 70%),radial-gradient(60% 35% at 100% 0%,rgba(245,242,236,.07),transparent 75%),${INK}` },
  'E-day': { bg: PAPER, sf: '#FFFFFF', fg: INK, mut: mix(INK, PAPER, .72), ln: mix(E.indigo, PAPER, .16), pr: E.indigo, onpr: PAPER, sym: E.indigo, acc: E.pom, word: E.indigo, a1: E.turq, a2: E.pom, a3: E.saf,
    ml: E.indigo, m1: E.turq, m2: E.pom, m3: E.saf, chip: mix(E.indigo, PAPER, .08), solid: true,
    glow: `radial-gradient(60% 38% at 100% 0%,rgba(229,161,43,.3),transparent 72%),radial-gradient(70% 42% at 0% 100%,rgba(38,57,127,.15),transparent 72%),radial-gradient(45% 28% at 100% 100%,rgba(179,38,46,.08),transparent 70%),${PAPER}` },
  'E-night': { bg: NIGHT, sf: mix(PAPER, NIGHT, .07), fg: PAPER, mut: mix(PAPER, NIGHT, .74), ln: mix(PAPER, NIGHT, .17), pr: PAPER, onpr: INK, sym: PAPER, acc: E.saf, word: PAPER, a1: mix(E.turq, PAPER, .55), a2: mix(E.pom, PAPER, .5), a3: E.saf,
    ml: mix(PAPER, NIGHT, .55), m1: mix(E.turq, NIGHT, .7), m2: mix(E.pom, NIGHT, .6), m3: E.saf, chip: mix(PAPER, NIGHT, .1), solid: true,
    glow: `radial-gradient(60% 40% at 0% 0%,rgba(70,92,190,.38),transparent 72%),radial-gradient(60% 36% at 100% 100%,rgba(229,161,43,.14),transparent 72%),radial-gradient(40% 25% at 100% 20%,rgba(11,116,120,.22),transparent 70%),${NIGHT}` },
};
const schemeCss = (cls, s) => `.${cls}{--bg:${s.bg};--sf:${s.sf};--fg:${s.fg};--mut:${s.mut};--ln:${s.ln};--pr:${s.pr};--onpr:${s.onpr};--a1:${s.a1};--a2:${s.a2};--a3:${s.a3};--ml:${s.ml};--m1:${s.m1};--m2:${s.m2};--m3:${s.m3};--chip:${s.chip};--glow:${s.glow};background:var(--bg);color:var(--fg)}`;

// ---- brand marks (symbol + wordmark come from the approved ornament files; geometry untouched, only colours/ids change)
let uid = 0;
const symSvg = (s, size, full) => {
  const dark = s.fg === PAPER;
  let f = fs.readFileSync(path.join(SYM, full ? (dark ? 'y-ornament-on-ink.svg' : 'y-ornament.svg') : (dark ? 'y-ornament-simple-on-ink.svg' : 'y-ornament-simple.svg')), 'utf8');
  const n = ++uid;
  f = f.replace(/id="(a[rl])"/g, `id="$1${n}"`).replace(/url\(#(a[rl])\)/g, `url(#$1${n})`);
  f = f.replace(/#E8501A/g, '@ACC@').replace(/#111111|#F5F2EC/g, '@SYM@').replace(/@ACC@/g, s.acc).replace(/@SYM@/g, s.sym);
  return f.replace('<svg ', `<svg width="${size}" height="${size}" aria-hidden="true" `).replace(/role="img" aria-label="Yondo"><title>Yondo<\/title>/, '>');
};
const WM = fs.readFileSync(path.join(SYM, 'lockup-horizontal.svg'), 'utf8').match(/<path fill="#111111" d="(M90[^"]+)"/)[1];
const wmSvg = (color, h) => `<svg viewBox="78 14 142 38" height="${h}" width="${(h * 142 / 38).toFixed(1)}" aria-hidden="true"><path fill="${color}" d="${WM}"/></svg>`;
// lockup: R = symbol sits on a soft rounded tile, wordmark smaller (lighter); E = same structure, indigo wordmark
const lockup = (s, h, o = {}) => {
  const tile = Math.round(h * 1.0), sy = Math.round(h * 0.72), wh = Math.round(h * 0.50);
  return `<span class="lock" style="gap:${Math.round(h * .26)}px"><span class="tile" style="width:${tile}px;height:${tile}px;border-radius:${Math.round(h * .32)}px">${symSvg(s, sy, sy >= 48)}</span>${wmSvg(s.word, wh)}</span>`;
};
// ---- motifs: own drawings (line + tint), classes pick colours from the scheme
const ln = 'class="ln"';
const bodom = (x, y, k, r = 0) => `<g transform="translate(${x} ${y}) rotate(${r}) scale(${k})"><path class="f1" d="M0-22C14-13 19 7 7 18C1 23-9 21-11 13C-13 4-5-6 0-22Z"/><path ${ln} d="M0-22C14-13 19 7 7 18C1 23-9 21-11 13C-13 4-5-6 0-22Z"/><path class="f2" d="M0-11C7-6 9 5 3 10C0 12-4 11-5 7C-6 3-3-2 0-11Z"/><circle class="f3" cx="-1" cy="2" r="1.9"/><circle class="f3" cx="1.5" cy="-5" r="1.2"/></g>`;
const stair = (r, n) => { const st = r / n; let p = [`${0},${-r}`]; for (let i = 0; i < n; i++) p.push(`${(i + 1) * st},${-r + i * st}`, `${(i + 1) * st},${-r + (i + 1) * st}`);
  for (let i = 0; i < n; i++) p.push(`${r - (i + 1) * st},${(i) * st}`, `${r - (i + 1) * st},${(i + 1) * st}`);
  for (let i = 0; i < n; i++) p.push(`${-(i + 1) * st},${r - i * st}`, `${-(i + 1) * st},${r - (i + 1) * st}`);
  for (let i = 0; i < n; i++) p.push(`${-r + (i + 1) * st},${-(i) * st}`, `${-r + (i + 1) * st},${-(i + 1) * st}`);
  return p.join(' '); };
const ikat = (x, y, r) => `<g class="ik" transform="translate(${x} ${y})"><polygon class="f2" points="${stair(r, 9)}"/><polygon ${ln} points="${stair(r, 9)}"/><polygon class="f1" points="${stair(r * .64, 6)}"/><polygon class="f3" points="${stair(r * .28, 3)}"/><path class="ln fine" d="M${-r * 1.28} 0h${r * .22}M${-r * 1.38} ${-r * .09}h${r * .12}M${-r * 1.38} ${r * .09}h${r * .12}M${r * 1.06} 0h${r * .22}M${r * 1.26} ${-r * .09}h${r * .12}M${r * 1.26} ${r * .09}h${r * .12}"/></g>`;
const tileMotif = (x, y, k) => { let p = ''; for (let i = 0; i < 8; i++) p += `<ellipse class="${i % 2 ? 'f2' : 'f1'}" cx="0" cy="-11" rx="4.6" ry="9" transform="rotate(${i * 45})"/>`;
  return `<g transform="translate(${x} ${y}) scale(${k})"><rect class="f2 soft" x="-28" y="-28" width="56" height="56" rx="9"/><rect ${ln} x="-28" y="-28" width="56" height="56" rx="9"/>${p}<circle class="f3" r="4"/><path ${ln} d="M-28-16a12 12 0 0 0 12-12M28-16a12 12 0 0 1-12-12M-28 16a12 12 0 0 1 12 12M28 16a12 12 0 0 0-12 12"/></g>`; };
const pomegranate = (x, y, r) => `<g transform="translate(${x} ${y})"><path class="f3" d="M${-r * .15} ${-r * .95}q${r * .5} ${-r * .55} ${r * .95} ${-r * .3}q${-r * .25} ${r * .45} ${-r * .8} ${r * .4}z"/><circle class="f2" r="${r}"/><path class="f3 pale" d="M${-r * .38} ${-r * .98}l${r * .1} ${-r * .3}l${r * .28} ${r * .18}l${r * .28} ${-r * .18}l${r * .1} ${r * .3}z"/><circle ${ln} r="${r}"/><path ${ln} d="M${-r * .5} ${-r * .2}a${r * .6} ${r * .6} 0 0 0 ${r * .35} ${r * .65}"/><g class="seed"><circle cx="${r * .2}" cy="${r * .1}" r="${r * .09}"/><circle cx="${r * .45}" cy="${r * .3}" r="${r * .09}"/><circle cx="${r * .05}" cy="${r * .38}" r="${r * .09}"/><circle cx="${r * .38}" cy="${-r * .15}" r="${r * .09}"/></g></g>`;
const lotus = (x, y, k) => { let p = ''; [-62, 62, -31, 31, 0].forEach((a, i) => { p += `<path class="${i < 2 ? 'f2' : i < 4 ? 'f1' : 'f3 pale'}" d="M0 0C-9-8-8-22 0-30C8-22 9-8 0 0Z" transform="rotate(${a})"/><path ${ln} d="M0 0C-9-8-8-22 0-30C8-22 9-8 0 0Z" transform="rotate(${a})"/>`; });
  return `<g transform="translate(${x} ${y}) scale(${k})">${p}<path ${ln} d="M-24 4Q0 12 24 4"/></g>`; };
const pishtaq = (x, y, k) => `<g transform="translate(${x} ${y}) scale(${k})"><circle class="f3 pale" cx="0" cy="-62" r="40"/><path class="f1" d="M-30 0V-52Q-30-70 0-90Q30-70 30-52V0Z"/><path ${ln} d="M-30 0V-52Q-30-70 0-90Q30-70 30-52V0Z"/><path class="f2" d="M-17 0V-44Q-17-58 0-72Q17-58 17-44V0Z"/><path ${ln} d="M-17 0V-44Q-17-58 0-72Q17-58 17-44V0Z"/><path ${ln} d="M-30-40H30"/><circle class="f3" cx="0" cy="-48" r="3.4"/>${[-1, 1].map((s) => `<g transform="translate(${s * 50} 0)"><rect class="f2" x="-8" y="-84" width="16" height="84"/><rect ${ln} x="-8" y="-84" width="16" height="84"/><path class="f3" d="M-9-84a9 9 0 0 1 18 0z"/><path ${ln} d="M-8-60h16M-8-36h16M-8-12h16"/></g>`).join('')}<path ${ln} d="M-70 0H70"/></g>`;
const band = (w, k = 1) => { let p = ''; for (let x = 8; x < w; x += 16 * k) p += `<path class="${(x / 16 | 0) % 2 ? 'f1' : 'f2'}" d="M${x} 6l${6 * k} ${6 * k}l${-6 * k} ${6 * k}l${-6 * k} ${-6 * k}z"/><circle class="f3" cx="${x + 8 * k}" cy="${12 * k}" r="${1.4 * k}"/>`; return `<svg class="band" viewBox="0 0 ${w} ${24 * k}" width="${w}" height="${24 * k}" aria-hidden="true"><path ${ln} d="M0 ${12 * k}H${w}"/>${p}</svg>`; };
const svgw = (w, h, inner, cls = '') => `<svg class="mot ${cls}" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">${inner}</svg>`;

// ---- shared CSS
const css = (dir) => `
@font-face{font-family:'Manrope';src:url(fonts/manrope-latin-wght-normal.woff2) format('woff2');font-weight:200 800;unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Manrope';src:url(fonts/manrope-latin-ext-wght-normal.woff2) format('woff2');font-weight:200 800;unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
*{box-sizing:border-box}html{background:#cfcac0}body{margin:0;padding:28px;font:500 15px/1.45 Manrope,system-ui,sans-serif;color:#111;width:max-content}
h1,h2,h3,p{margin:0}.board{padding:20px;background:#d9d4ca;border-radius:20px;margin-bottom:24px}.board>h6{font:700 12px Manrope;letter-spacing:.08em;text-transform:uppercase;color:#4a463f;margin:0 0 12px}
${Object.entries(S).filter(([k]) => k.startsWith(dir)).map(([k, s]) => schemeCss(k.endsWith('day') ? 'day' : 'night', s)).join('\n')}
.row{display:flex;gap:24px;align-items:flex-start}.fr{position:relative;overflow:hidden;border-radius:26px;flex:none;box-shadow:0 10px 30px -14px rgba(0,0,0,.35)}
.atmos{position:absolute;inset:0;background:var(--glow);z-index:0}.fr>*:not(.atmos){position:relative;z-index:1}
.mot{display:block;overflow:visible}.mot .ln,.band .ln,.ln{fill:none;stroke:var(--ml);stroke-width:1.15;vector-effect:non-scaling-stroke;stroke-linejoin:round;stroke-linecap:round}.ln.fine{stroke-width:1;opacity:.7}
.f1{fill:var(--m1)}.f2{fill:var(--m2)}.f3{fill:var(--m3)}.pale{opacity:.45}.soft{opacity:.7}.seed circle{fill:var(--bg)}
.absm{position:absolute!important;pointer-events:none}.ik{filter:url(#ikf)}
.lock{display:inline-flex;align-items:center}.tile{display:grid;place-items:center;background:var(--sf);box-shadow:0 0 0 1px var(--ln),0 6px 14px -8px rgba(17,17,17,.35);flex:none}
.top{display:flex;align-items:center;justify-content:space-between;padding:16px 18px 6px}
.lang{display:flex;gap:2px;padding:3px;border-radius:999px;background:var(--chip);font:700 12px Manrope}.lang span{padding:6px 10px;border-radius:999px;color:var(--mut)}.lang .on{background:var(--pr);color:var(--onpr)}
h1{font:800 32px/1.08 Manrope;letter-spacing:-.02em}h2{font:800 22px/1.15 Manrope;letter-spacing:-.01em}.lead{color:var(--mut);font-size:15px}.hint{color:var(--mut);font-size:13px}
.gcard{background:color-mix(in oklab,var(--sf) 88%,transparent);backdrop-filter:blur(14px);border:1px solid var(--ln);border-radius:30px;padding:20px;display:flex;flex-direction:column;gap:14px;box-shadow:0 18px 40px -22px rgba(17,17,17,.45)}
label.lb{font:700 13px Manrope}.inp{height:54px;border-radius:18px;border:1.5px solid color-mix(in oklab,var(--fg) 38%,var(--bg));background:var(--sf);color:var(--fg);padding:0 16px;font:600 17px Manrope;width:100%}
.inp.code{letter-spacing:.5em;text-align:center;font-size:22px}
.chk{display:flex;gap:12px;align-items:flex-start;font-size:14px}.chk i{flex:none;width:24px;height:24px;border-radius:8px;border:1.5px solid color-mix(in oklab,var(--fg) 45%,var(--bg));background:var(--sf);margin-top:1px}
a.lnk,.lnk{color:var(--fg);text-decoration:underline;text-underline-offset:3px;font-weight:600}
.btn{height:54px;border-radius:999px;border:0;background:var(--pr);color:var(--onpr);font:800 16px Manrope;display:flex;align-items:center;justify-content:center;gap:10px;width:100%;box-shadow:0 10px 20px -12px var(--pr)}
.btn.ghost{background:transparent;color:var(--fg);box-shadow:inset 0 0 0 1.5px color-mix(in oklab,var(--fg) 40%,var(--bg))}.btn.ghost[disabled]{opacity:.75}
.chip{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:7px 13px;background:var(--chip);font:700 13px Manrope;color:var(--fg);border:1px solid var(--ln);white-space:nowrap}.chip.on{background:var(--pr);color:var(--onpr);border-color:transparent}
details{border-radius:18px;border:1px solid var(--ln);padding:12px 14px;font-size:14px}details summary{font-weight:700;cursor:pointer}
.stack{display:flex;flex-direction:column;gap:14px}.tag{font:800 10px Manrope;letter-spacing:.06em;padding:3px 7px;border-radius:999px;border:1.5px dashed var(--ml);color:var(--fg)}
.nav{position:absolute!important;left:12px;right:12px;bottom:12px;display:flex;justify-content:space-around;padding:8px;border-radius:26px;background:color-mix(in oklab,var(--sf) 86%,transparent);backdrop-filter:blur(14px);border:1px solid var(--ln);box-shadow:0 14px 30px -16px rgba(17,17,17,.5)}
.nav a{display:flex;flex-direction:column;align-items:center;gap:3px;font:700 11px Manrope;color:var(--mut);padding:7px 12px;border-radius:20px;min-width:62px}.nav a.on{background:var(--pr);color:var(--onpr)}.nav svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.cstrip{display:flex;gap:14px;overflow:hidden;padding:2px 20px 4px}.cc{flex:none;width:184px;border-radius:26px;background:var(--sf);border:1px solid var(--ln);overflow:hidden;box-shadow:0 14px 30px -20px rgba(17,17,17,.5)}
.cc .ph{height:132px;position:relative;background:var(--chip)}.cc .bd{padding:11px 13px 13px;display:flex;flex-direction:column;gap:4px}.cc b{font:800 16px Manrope}.cc small{color:var(--mut);font-weight:600;font-size:12.5px}
.ok{display:inline-flex;gap:5px;align-items:center;font:700 12px Manrope}.ok svg{width:15px;height:15px}
.sec{padding:0 20px;display:flex;justify-content:space-between;align-items:baseline}.sec h3{font:800 18px Manrope}
.gi{border-radius:24px;background:var(--sf);border:1px solid var(--ln);overflow:hidden;width:156px;flex:none}.gi .ph{height:110px;position:relative;background:var(--chip)}.gi .bd{padding:10px 12px 12px;display:flex;flex-direction:column;gap:3px}
.legend{display:flex;gap:28px;align-items:flex-end;flex-wrap:wrap}.lg{display:flex;flex-direction:column;gap:8px;align-items:flex-start}.lg small{font:700 11px Manrope;color:var(--mut)}
`;

const navIcons = { k: '<path d="M3 11l9-8 9 8v10H3z"/><path d="M9 21v-7h6v7"/>', b: '<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>', g: '<rect x="3" y="9" width="18" height="12" rx="2"/><path d="M12 9v12M3 13h18M12 9C9 9 8 4 11 4s1 5 1 5zM12 9c3 0 4-5 1-5s-1 5-1 5z"/>', p: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-5 5-7 8-7s7 2 8 7"/>' };
const nav = (on) => `<nav class="nav"><a class="${on === 0 ? 'on' : ''}"><svg viewBox="0 0 24 24">${navIcons.k}</svg>Kaşf</a><a class="${on === 1 ? 'on' : ''}"><svg viewBox="0 0 24 24">${navIcons.b}</svg>Bronlar</a><a class="${on === 2 ? 'on' : ''}"><svg viewBox="0 0 24 24">${navIcons.g}</svg>Sovğalar</a><a class="${on === 3 ? 'on' : ''}"><svg viewBox="0 0 24 24">${navIcons.p}</svg>Profil</a></nav>`;
const tick = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" fill="var(--a1)" stroke="none" opacity=".2"/><path d="M7.5 12.5l3 3 6-7"/></svg>';
const topbar = (s, h = 34) => `<div class="top">${lockup(s, h)}<div class="lang"><span class="on">UZ</span><span>RU</span><span>EN</span></div></div>`;

// ---- screens
const mobileAtmos = (dir) => `<div class="atmos"></div>` + `<div class="absm" style="right:-40px;bottom:100px;opacity:${dir === 'E' ? .9 : .75}">${svgw(150, 150, ikat(75, 75, 46))}</div>`;
const loginPhone = (dir, cls, s) => `<div class="fr ${cls}" style="width:360px;height:800px">${mobileAtmos(dir)}${topbar(s)}<div class="stack" style="padding:14px 20px 0;gap:16px"><div class="stack" style="gap:8px"><h1>Yondoʼga kiriş</h1><p class="lead">Telefon raqamingizni kiriting — bir martalik tasdiqlaş kodini yuboramiz.</p></div>
<div class="gcard"><div class="stack" style="gap:8px"><label class="lb">Telefon raqami</label><div class="inp" style="display:flex;align-items:center">+998 90 123 45 67</div><span class="hint">Namuna: +998 90 123 45 67</span></div>
<div class="chk"><i></i><span>Foydalaniş şartlari va maxfiylik siyosati bilan tanişdim va ularga roziman. <a class="lnk">Şartlar</a> · <a class="lnk">Maxfiylik</a></span></div><div class="btn">Kod yuboriş</div></div>
<div class="absm" style="left:-6px;bottom:96px;opacity:.9">${svgw(120, 60, bodom(24, 30, 1.2, -20) + bodom(60, 34, .8, 12))}</div>
${band(320, 1).replace('<svg ', '<svg style="margin-top:6px" ')}<p class="hint" style="padding-top:8px">Yondo — hamroh topiş platformasi. Tanişuv yoki eskort xizmati emas.</p></div>${nav(3)}</div>`;
const loginCode = (dir, cls, s) => `<div class="fr ${cls}" style="width:360px;height:800px">${mobileAtmos(dir)}${topbar(s)}<div class="stack" style="padding:14px 20px 0;gap:16px"><h1>Yondoʼga kiriş</h1>
<div class="gcard"><h2>Kod Telegramʼga yuborildi</h2><p class="lead" style="font-size:14px">Raqam: +998 90 123 45 67 <span class="chip" style="margin-left:6px;padding:5px 10px">Raqamni özgartiriş</span></p><p class="hint">Kod 5 daqiqa amal qiladi.</p>
<div class="stack" style="gap:8px"><label class="lb">Tasdiqlaş kodi</label><div class="inp code">• • • • • •</div><span class="hint">Telegram ilovasini oçib, «Verification Codes» çatidagi 6 xonali kodni kiriting.</span></div>
<div class="btn">Kiriş</div><div class="btn ghost" disabled>Kodni qayta yuboriş (28)</div><details><summary>Kod kelmadimi?</summary><p class="hint" style="margin-top:8px">«Verification Codes» çatini tekşiring, keyin kodni qayta yuboring.</p></details></div></div>${nav(3)}</div>`;
const loginDesk = (dir, cls, s, step) => `<div class="fr ${cls}" style="width:1440px;height:720px;border-radius:0"><div class="atmos"></div>
<div class="absm" style="left:70px;bottom:40px">${svgw(420, 300, pishtaq(210, 270, 2.6))}</div><div class="absm" style="right:60px;top:40px;opacity:.85">${svgw(260, 260, ikat(130, 130, 90))}</div>
<div style="position:absolute;inset:0;padding:34px 70px;display:flex;flex-direction:column"><div style="display:flex;justify-content:space-between;align-items:center">${lockup(s, 46)}<div class="lang" style="font-size:14px"><span class="on">UZ</span><span>RU</span><span>EN</span></div></div>
<div style="display:flex;flex:1;align-items:center;gap:90px"><div style="flex:1;display:flex;flex-direction:column;gap:18px;margin-top:-170px"><h1 style="font-size:68px;line-height:1.02">Yondo<br>doim yoningda</h1><p class="lead" style="font-size:19px;max-width:420px">Şahar böylab hamroh toping: sayr, tadbir va maxsus kunlar.</p></div>
<div style="width:480px">${step === 'phone' ? `<div class="gcard" style="padding:28px"><h2>Yondoʼga kiriş</h2><div class="stack" style="gap:8px"><label class="lb">Telefon raqami</label><div class="inp">+998 90 123 45 67</div><span class="hint">Namuna: +998 90 123 45 67</span></div><div class="chk"><i></i><span>Foydalaniş şartlari va maxfiylik siyosati bilan tanişdim va ularga roziman.</span></div><div class="btn">Kod yuboriş</div></div>` :
`<div class="gcard" style="padding:28px"><h2>Kod Telegramʼga yuborildi</h2><p class="lead" style="font-size:14px">Raqam: +998 90 123 45 67 <span class="chip" style="margin-left:6px;padding:5px 10px">Raqamni özgartiriş</span></p><div class="stack" style="gap:8px"><label class="lb">Tasdiqlaş kodi</label><div class="inp code">• • • • • •</div><span class="hint">Telegram ilovasini oçib, «Verification Codes» çatidagi 6 xonali kodni kiriting.</span></div><div class="btn">Kiriş</div><div class="btn ghost">Kodni qayta yuboriş (28)</div></div>`}</div></div></div></div>`;

const avatar = (n, dir) => { const m = [bodom(92, 66, 2.3, 8), tileMotif(92, 64, 1.5), lotus(92, 96, 1.7)][n]; return `<div class="ph">${svgw(184, 132, m)}</div>`; };
const comp = (n, name, age, rate, dir) => `<div class="cc">${avatar(n, dir)}<div class="bd"><div style="display:flex;justify-content:space-between;align-items:center"><b>${name}, ${age}</b><span class="tag">DEMO</span></div><span class="ok">${tick}Tasdiqlangan</span><small>★ ${rate} · Samarqand</small><small style="color:var(--fg);font-weight:800">120 000 soʼm/soat</small></div></div>`;
const home = (dir, cls, s) => `<div class="fr ${cls}" style="width:360px;height:980px"><div class="atmos"></div>${topbar(s)}
<div class="stack" style="padding:10px 20px 0;gap:14px"><div class="stack" style="gap:8px"><h1 style="font-size:38px">Yondo<br>doim yoningda</h1><p class="lead">Şahar böylab hamroh toping: sayr, tadbir va maxsus kunlar.</p></div>
<div class="inp" style="display:flex;align-items:center;gap:10px;color:var(--mut);font-size:15px;height:52px"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>Şahar yoki xizmat izlang</div>
<div style="display:flex;gap:8px;flex-wrap:nowrap;overflow:hidden"><span class="chip on">Hammasi</span><span class="chip">Sayr</span><span class="chip">Tadbir</span><span class="chip">Maxsus kunlar</span></div></div>
<div style="margin:14px 20px 0;height:150px;border-radius:30px;border:1px solid var(--ln);background:color-mix(in oklab,var(--sf) 70%,transparent);position:relative;overflow:hidden">${svgw(320, 150, pishtaq(160, 138, 1.25).replace('</g></g>', '</g></g>'), '')}<div style="position:absolute;left:14px;top:12px"><span class="chip" style="background:var(--sf)">Yangi şahar · Samarqand</span></div></div>
${band(320, 1).replace('<svg ', '<svg style="margin:10px 20px 0" ')}
<div class="sec" style="margin-top:6px"><h3>Mashhur hamrohlar</h3><span class="lnk" style="font-size:13px">Hammasi</span></div>
<div class="cstrip" style="margin-top:12px">${comp(0, 'Dilnoza', 27, '4,9', dir)}${comp(1, 'Madina', 25, '4,8', dir)}${comp(2, 'Aziza', 29, '5,0', dir)}</div>
<p class="hint" style="padding:12px 20px 0">Namunaviy ma’lumotlar DEMO deb belgilangan. Yondo — hamroh topiş platformasi.</p>${nav(0)}</div>`;
const gift = (dir, cls, s) => `<div class="fr ${cls}" style="width:360px;height:440px"><div class="atmos"></div>${topbar(s, 30)}
<div style="padding:10px 20px 0;position:relative"><div class="absm" style="right:-8px;top:-8px;opacity:1">${svgw(150, 120, pomegranate(98, 64, 30) + bodom(38, 62, 1.6, -18) + lotus(60, 108, .6))}</div>
<h1 style="font-size:36px;max-width:200px">Sovğalar</h1><p class="lead" style="max-width:210px;margin-top:6px">Yaqinlaringiz uçun sovğa tanlang — yetkazib berişni birga belgilaymiz.</p></div>
<div style="display:flex;gap:8px;padding:16px 20px 0;overflow:hidden"><span class="chip on">Hammasi</span><span class="chip">Gullar</span><span class="chip">Şirinliklar</span><span class="chip">Dasturxon</span></div>
<div class="cstrip" style="margin-top:14px"><div class="gi"><div class="ph">${svgw(156, 110, lotus(78, 88, 1.5))}</div><div class="bd"><b style="font:800 14px Manrope">Gul savati</b><small style="color:var(--mut);font-weight:600;font-size:12px">180 000 soʼm</small><span class="tag" style="align-self:flex-start">DEMO</span></div></div><div class="gi"><div class="ph">${svgw(156, 110, pomegranate(78, 58, 34))}</div><div class="bd"><b style="font:800 14px Manrope">Anor to‘plami</b><small style="color:var(--mut);font-weight:600;font-size:12px">95 000 soʼm</small><span class="tag" style="align-self:flex-start">DEMO</span></div></div><div class="gi"><div class="ph">${svgw(156, 110, bodom(78, 56, 2.2, 10))}</div></div></div></div>`;

// logo board
const logoBoard = (dir) => {
  const strip = (cls, s) => `<div class="fr ${cls}" style="padding:22px 24px;border-radius:22px;width:520px;display:flex;flex-direction:column;gap:20px"><div class="atmos"></div>
  <div style="display:flex;gap:26px;align-items:flex-end">${[16, 32, 64, 160].map((n) => `<div class="lg">${symSvg(s, n, n >= 48)}<small>${n} px</small></div>`).join('')}</div>
  <div style="display:flex;gap:26px;align-items:flex-end">${[24, 32, 48].map((n) => `<div class="lg">${lockup(s, n)}<small>${n} px</small></div>`).join('')}</div></div>`;
  const big = (cls, s) => `<div class="fr ${cls}" style="width:520px;height:230px;display:grid;place-items:center"><div class="atmos"></div>${lockup(s, 104)}</div>`;
  return `<div class="board" id="logo"><h6>Logo lockup — girih Y + outlined wordmark (paths unchanged) — light and night</h6><div class="row"><div class="stack" style="gap:24px">${big('day', S[dir + '-day'])}${strip('day', S[dir + '-day'])}</div><div class="stack" style="gap:24px">${big('night', S[dir + '-night'])}${strip('night', S[dir + '-night'])}</div></div>
  <p style="font:600 12px Manrope;color:#4a463f;margin-top:10px">Below 48 px the simplified solid strap is used (as in ornament/README). 16 px is shown to be honest: the wordmark is not meant to be read below ~24 px height; use the symbol only.</p></div>`;
};
const page = (dir) => {
  const d = S[dir + '-day'], n = S[dir + '-night'];
  const title = dir === 'R' ? 'Direction R — restrained (ink / paper / carrot)' : 'Direction E — extended heritage palette';
  return `<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>${css(dir)}</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="ikf" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.09 0.5" numOctaves="2" seed="4" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="5"/></filter></svg>
${logoBoard(dir)}
<div class="board" id="login"><h6>Login — 360 px: phone step and Telegram code step, day and night</h6><div class="row">${loginPhone(dir, 'day', d)}${loginCode(dir, 'day', d)}${loginPhone(dir, 'night', n)}${loginCode(dir, 'night', n)}</div>
<h6 style="margin-top:22px">Login — 1440 px (shown at 50 %): day phone step, night code step</h6><div class="row"><div style="zoom:.5">${loginDesk(dir, 'day', d, 'phone')}</div><div style="zoom:.5">${loginDesk(dir, 'night', n, 'code')}</div></div></div>
<div class="board" id="home"><h6>Home / discovery hero — 360 px, day and night</h6><div class="row">${home(dir, 'day', d)}${home(dir, 'night', n)}</div></div>
<div class="board" id="gift"><h6>Gift catalogue header — 360 px</h6><div class="row">${gift(dir, 'day', d)}${gift(dir, 'night', n)}</div></div>
</body></html>`;
};
fs.writeFileSync(path.join(D, 'r.html'), page('R'));
fs.writeFileSync(path.join(D, 'e.html'), page('E'));
console.log('written r.html e.html');
