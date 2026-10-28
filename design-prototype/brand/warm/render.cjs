// Renders r.html / e.html boards to PNG with Playwright Chromium (no network). Usage: node render.cjs
const { chromium } = require('playwright'); const path = require('path');
(async () => { const b = await chromium.launch(); const D = __dirname;
  for (const d of ['r', 'e']) { const p = await b.newPage({ viewport: { width: 1700, height: 1000 } });
    const errs = []; p.on('console', (m) => m.type() === 'error' && errs.push(m.text())); p.on('requestfailed', (r) => errs.push('fail ' + r.url().slice(0, 80)));
    await p.goto('file://' + path.join(D, d + '.html')); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
    for (const id of ['logo', 'login', 'home', 'gift']) await p.locator('#' + id).screenshot({ path: path.join(D, `${d}-${id}.png`) });
    const SC = process.env.SCRATCH; if (SC) { await p.locator('#login .fr').nth(0).screenshot({ path: SC + `/${d}-ld.png` }); await p.locator('#login .fr').nth(2).screenshot({ path: SC + `/${d}-ln.png` }); await p.locator('#logo .fr').nth(0).screenshot({ path: SC + `/${d}-lg.png` }); }
    console.log(d, 'errors', errs.length, errs.slice(0, 2)); await p.close(); }
  await b.close(); })();
