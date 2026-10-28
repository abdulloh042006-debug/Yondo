// Renders the PNG previews in ./png (needs Playwright's Chromium: `require('playwright')`). Usage: node render.cjs
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const here = __dirname, out = path.join(here, 'png');
const url = (p, q = '') => 'file://' + path.join(here, p) + q;
const MAX = 390000; // bytes (keeps each PNG under 400 kB, decimal)
fs.mkdirSync(out, { recursive: true });

async function shot(browser, p, w, h, q = '', full = false) {
  const pg = await browser.newPage({ viewport: { width: w, height: h } });
  await pg.goto(url(p, q)); await pg.waitForTimeout(500);
  const buf = await pg.screenshot({ fullPage: full }); await pg.close(); return buf;
}
const b64 = (b) => 'data:image/png;base64,' + b.toString('base64');

async function board(browser, name, page) {
  const desk = await shot(browser, `mockups/${page}.html`, 1440, 900, '?theme=yondo');
  const phone = await shot(browser, `mockups/${page}.html`, 360, 740, '?theme=yondo-tun');
  for (const scale of [1, 0.85, 0.72, 0.62, 0.52]) {
    const pg = await browser.newPage({ viewport: { width: Math.round(1440 * scale + 360 + 90), height: Math.max(Math.round(900 * scale), 740) + 70 } });
    await pg.setContent(`<body style="margin:0;background:#E4DFD4;font:600 12px system-ui;color:#111;display:flex;gap:30px;padding:30px 30px 0;align-items:flex-start">
      <div><div style="margin-bottom:6px;opacity:.7">1440 px · yondo</div><img src="${b64(desk)}" width="${Math.round(1440 * scale)}" style="display:block;border-radius:10px;box-shadow:0 8px 24px #0002"></div>
      <div><div style="margin-bottom:6px;opacity:.7">360 px · yondo-tun</div><img src="${b64(phone)}" width="360" style="display:block;border-radius:18px;box-shadow:0 8px 24px #0004"></div></body>`);
    const buf = await pg.screenshot(); await pg.close();
    if (buf.length <= MAX || scale === 0.52) { fs.writeFileSync(path.join(out, `mockup-${name}.png`), buf); return [name, scale, buf.length]; }
  }
}
(async () => {
  const browser = await chromium.launch();
  const report = [];
  for (const [n, p] of [['home', 'home'], ['profile', 'profile'], ['gifts', 'gifts'], ['checkout', 'checkout'], ['safety', 'safety']]) report.push(await board(browser, n, p));
  fs.writeFileSync(path.join(out, 'legibility.png'), await shot(browser, 'legibility.html', 1210, 560));
  fs.writeFileSync(path.join(out, 'onboarding-cards.png'), await shot(browser, 'onboarding/cards.html', 1100, 880, '', true));
  // opening storyboard: six frozen frames of preview.html (?t=ms), 360x640 each, shown at 50 %
  const times = [200, 600, 1000, 1400, 1900, 2400]; const frames = [];
  for (const t of times) frames.push(await shot(browser, 'preview.html', 360, 640, `?t=${t}`));
  const pg = await browser.newPage({ viewport: { width: 6 * 190 + 20, height: 380 } });
  await pg.setContent(`<body style="margin:0;background:#E4DFD4;font:600 12px system-ui;color:#111;display:flex;gap:10px;padding:10px">${frames.map((f, i) => `<div><img src="${b64(f)}" width="180" style="display:block;border-radius:8px"><div style="margin-top:4px">${times[i]} ms</div></div>`).join('')}</body>`);
  fs.writeFileSync(path.join(out, 'opening-storyboard.png'), await pg.screenshot());
  await browser.close();
  for (const f of fs.readdirSync(out)) console.log(f, Math.round(fs.statSync(path.join(out, f)).size / 1024) + ' KB');
  console.log(JSON.stringify(report));
})();
