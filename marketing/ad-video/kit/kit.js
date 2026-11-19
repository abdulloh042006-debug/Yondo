// Yondo ad kit (2026-11-19). Deterministic helpers: every function draws the frame for time t, no timers, no randomness.
// Inlined into ad pages by kit/build.py; the page defines `const WORDMARK` (= marketing/ad-video/wordmark.svgfrag).
const K = (() => {
  const INK = '#111111', PAPER = '#F5F2EC', CAR = '#E8501A';
  const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const P = (t, a, b) => cl((t - a) / (b - a));                 // progress of t through [a, b]
  const eo = (k) => 1 - Math.pow(1 - k, 3);
  const eio = (k) => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
  const back = (k, s = 1.6) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

  // Official symbol (design-prototype/brand/logo/yondo-symbol-light.svg), 64-unit box; draw = 0..1 stroke reveal, dots = 0..1 pop.
  function symbol(draw = 1, dots = 1, ink = INK) {
    const d = (k) => cl(k);
    return `<g stroke="${ink}" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="5">`
      + `<path d="M14 12 28 33Q31 37 32 40M50 12 36 33Q33 37 32 40M32 40v12" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1 - draw}"/>`
      + `<circle cx="14" cy="12" r="${7 * back(d(dots * 3))}" fill="${ink}" opacity="${d(dots * 3)}"/>`
      + `<circle cx="50" cy="12" r="${7 * back(d(dots * 3 - 1))}" fill="${CAR}" opacity="${d(dots * 3 - 1)}"/>`
      + `<circle cx="32" cy="55" r="${5.5 * back(d(dots * 3 - 2))}" fill="${ink}" opacity="${d(dots * 3 - 2)}"/></g>`;
  }

  // Animated horizontal lockup (219 x 64 units) centred at (cx, cy), unit scale u. Timing follows the app's opening animation:
  // stroke draws, three nodes pop, the outlined wordmark wipes in. t0 = start; whole piece 1.2 s.
  function logo(t, t0, cx, cy, u, ink = INK) {
    const draw = eio(P(t, t0, t0 + .55)), dots = P(t, t0 + .3, t0 + .8), wm = eio(P(t, t0 + .6, t0 + 1.2));
    const x = cx - 219 * u / 2, y = cy - 32 * u;
    return `<g transform="translate(${x} ${y}) scale(${u})">${symbol(draw, dots, ink)}`
      + `<clipPath id="kwm"><rect x="66" y="0" width="${153 * wm}" height="64"/></clipPath>`
      + `<g clip-path="url(#kwm)" style="color:${ink}" opacity="${wm}">${WORDMARK}</g></g>`;
  }

  // End card on paper: logo, tagline, CTA placeholder, small 18+. Returns SVG markup for a 1080 x 1920 frame.
  function endCard(t, t0, o = {}) {
    const tag = o.tagline || 'Yondo — doim yoningda.', cta = o.cta || '{{CTA}}', age = o.age || '18+';
    const a = eo(P(t, t0 + .9, t0 + 1.4)), b = eo(P(t, t0 + 1.2, t0 + 1.7));
    const ul = eo(P(t, t0 + 1.0, t0 + 1.5));
    return `<rect width="1080" height="1920" fill="${PAPER}"/>${logo(t, t0, 540, 820, 3.9)}`
      + `<text x="540" y="${1080 + 30 * (1 - a)}" font-family="Manrope" font-weight="800" font-size="76" fill="${INK}" text-anchor="middle" opacity="${a}">${esc(tag)}</text>`
      + `<path d="M${540 - 160 * ul} 1135 H${540 + 160 * ul}" stroke="${CAR}" stroke-width="10" stroke-linecap="round"/>`
      + `<text x="540" y="${1270 + 20 * (1 - b)}" font-family="Manrope" font-weight="700" font-size="54" fill="${INK}" text-anchor="middle" opacity="${b}">${esc(cta)}</text>`
      + `<g opacity="${b}"><rect x="482" y="1560" width="116" height="64" rx="32" fill="none" stroke="${INK}" stroke-width="4"/>`
      + `<text x="540" y="1604" font-family="Space Grotesk" font-weight="700" font-size="34" fill="${INK}" text-anchor="middle">${age}</text></g>`;
  }

  // Captions: list of [t0, t1, text]. Ink box, paper Manrope 700 54 px, word-by-word reveal; max 2 lines (split on '\n').
  function caption(t, list, y = 1380) {
    const c = list.find(([a, b]) => t >= a && t < b);
    if (!c) return '';
    const [a, b, txt] = c, fade = Math.min(eo(P(t, a, a + .15)), 1 - P(t, b - .15, b));
    const lines = txt.split('\n'), lh = 70, w = Math.max(...lines.map((l) => l.length)) * 29 + 72;
    let words = 0, g = `<g opacity="${fade}"><rect x="${540 - w / 2}" y="${y - 58}" width="${w}" height="${lines.length * lh + 34}" rx="22" fill="${INK}" fill-opacity=".88"/>`;
    lines.forEach((l, i) => {
      const ws = l.split(' ').map((wd) => { const k = eo(P(t, a + words * .06, a + words * .06 + .18)); words++; return `<tspan opacity="${k}">${esc(wd)} </tspan>`; });
      g += `<text x="540" y="${y + i * lh}" font-family="Manrope" font-weight="700" font-size="54" fill="${PAPER}" text-anchor="middle">${ws.join('')}</text>`;
    });
    return g + '</g>';
  }

  // Carrot stamp (e.g. KEYINROQ) hitting at time th, rotated rot degrees; falls away from tOut.
  function stamp(t, th, x, y, label = 'KEYINROQ', rot = -8, tOut = 1e9) {
    if (t < th) return '';
    const k = P(t, th, th + .22), s = lerp(2.2, 1, back(k, 1.2)), f = eio(P(t, tOut, tOut + .5));
    const w = label.length * 30 + 60;
    return `<g transform="translate(${x} ${y + f * 600}) rotate(${rot + f * 40}) scale(${s})" opacity="${cl(k * 3) * (1 - f)}">`
      + `<rect x="${-w / 2}" y="-38" width="${w}" height="76" rx="10" fill="none" stroke="${CAR}" stroke-width="7"/>`
      + `<text x="0" y="16" font-family="Space Grotesk" font-weight="700" font-size="46" letter-spacing="4" fill="${CAR}" text-anchor="middle">${esc(label)}</text></g>`;
  }

  // Carrot tick drawn between t0 and t0 + .3 at (x, y), size s.
  function tick(t, t0, x, y, s = 60) {
    const k = eo(P(t, t0, t0 + .3));
    return `<path d="M${x - s * .5} ${y} l${s * .35} ${s * .38} l${s * .65} ${-s * .8}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1 - k}" stroke="${CAR}" stroke-width="12" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
  }

  // Camera shake offset (deterministic) after hit times.
  function shake(t, hits, px = 4) {
    let dx = 0, dy = 0;
    for (const h of hits) { const k = P(t, h, h + .18); if (k > 0 && k < 1) { const a = (1 - k) * px; dx += Math.sin(k * 40) * a; dy += Math.cos(k * 33) * a; } }
    return [dx, dy];
  }

  return { INK, PAPER, CAR, cl, lerp, P, eo, eio, back, esc, symbol, logo, endCard, caption, stamp, tick, shake };
})();
