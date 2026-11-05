// Ad screen capture from the design-prototype (mock-backed) instead of apps/web.
// Usage: OUT=<dir> THEME=light|dark ONLY=discovery node capture_proto.mjs
// Produces m-*.png (390x844 @2.5 = 975x2110) and d-*.png (1280x800 @1.5).
// Owner rule for the video: no DEMO labels, no verified badges on screen.
import { mkdirSync } from 'node:fs';
import { chromium } from '/home/claude/fonttools/node_modules/playwright-core/index.mjs';

const OUT = process.env.OUT; mkdirSync(OUT, { recursive: true });
const THEME = process.env.THEME || 'light';
const ONLY = process.env.ONLY || '';
const PROTO = process.env.PROTO || '/home/claude/yondo/design-prototype/prototype/index.html';
const FS = 'file:///home/claude/fonttools/node_modules/@fontsource';
const FONT_CSS = [['inter', 400], ['inter', 500], ['inter', 600], ['inter', 700], ['space-grotesk', 700]]
  .map(([p, w]) => `@font-face{font-family:'${p === 'inter' ? 'Inter' : 'Space Grotesk'}';font-weight:${w};font-style:normal;src:url(${FS}/${p}/files/${p}-latin-${w}-normal.woff2) format('woff2')}
@font-face{font-family:'${p === 'inter' ? 'Inter' : 'Space Grotesk'}';font-weight:${w};font-style:normal;src:url(${FS}/${p}/files/${p}-latin-ext-${w}-normal.woff2) format('woff2');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1EFF}`).join('\n');
const HIDE_CSS = `.ban,.demo,.bdg,details,.toast,#off,.skip{display:none!important}*{caret-color:transparent!important}
.av{background:rgba(232,80,26,.14)!important;color:#B53A0C!important}[data-theme=dark] .av{background:rgba(232,80,26,.22)!important;color:#F5F2EC!important}
.stc{align-self:flex-start;flex:none}#v{--ok:var(--tx)}`; // video: only ink/paper/carrot (owner rule)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox', '--allow-file-access-from-files'] });

async function clean(page) {
  await page.evaluate(([css, theme]) => {
    document.documentElement.dataset.theme = theme;
    if (!document.getElementById('adcss')) { const s = document.createElement('style'); s.id = 'adcss'; s.textContent = css; document.head.appendChild(s); }
    // leaf texts that mention DEMO / demo (owner: no DEMO labels in the video)
    for (const el of document.querySelectorAll('#v p, #v span, #v div, #v b')) {
      if (el.children.length === 0 && /\bdemo\b/i.test(el.textContent)) el.style.display = 'none';
    }
  }, [HIDE_CSS, THEME === 'dark' ? 'dark' : 'light']);
}
async function shot(page, name, scrollY) {
  await sleep(900);
  await clean(page);
  if (scrollY != null) { await page.evaluate((y) => window.scrollTo(0, y), scrollY); }
  await sleep(700);
  await clean(page);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('shot', name);
}
const hash = async (page, h) => { await page.evaluate((x) => { location.hash = x; }, h); await page.waitForFunction(() => document.querySelector('#v h1, #v h2') && !document.querySelector('#v .sk'), null, { timeout: 15000 }); };
const click = async (page, a) => { await page.click(`[data-a="${a}"]`); await sleep(250); };

async function login(page) {
  await page.goto('file://' + PROTO + '#/login');
  await page.waitForSelector('#ph');
  await page.fill('#ph', '901234567'); await page.click('button[type=submit]');
  await page.waitForSelector('#ot'); await page.fill('#ot', '1234'); await page.click('button[type=submit]');
  await page.waitForFunction(() => /home|roles/.test(location.hash), null, { timeout: 15000 });
  if (/roles/.test(await page.evaluate(() => location.hash))) {
    await page.check('input[value=customer]'); await page.click('button[type=submit]');
    await page.waitForFunction(() => /home/.test(location.hash), null, { timeout: 15000 });
  }
  await page.waitForFunction(() => document.querySelector('#v .card'), null, { timeout: 15000 });
}
async function book(page, cid, days) {
  await hash(page, '#/book/' + cid);
  for (const day of days) {
  await click(page, 'bd:' + day);
  for (const h of [14, 15, 16, 13, 12, 17, 11]) {
    await click(page, 'bt:' + h);
    await page.waitForFunction(() => { const c = document.querySelector('#chk'); return c && !/tekshirilmoqda/.test(c.textContent) && c.textContent.trim(); }, null, { timeout: 15000 }).catch(() => {});
    const txt = await page.evaluate(() => document.querySelector('#chk').textContent.trim());
    if (process.env.DBG) console.log('chk', cid.slice(-3), day, h, txt);
    if (/mavjud\./.test(txt) && !/emas/.test(txt)) return h;
  }
  }
  return null;
}

for (const [p, vp, dsf] of [['m', { width: 390, height: 844 }, 2.5], ['d', { width: 1280, height: 800 }, 1.5]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: dsf, isMobile: p === 'm', hasTouch: p === 'm', colorScheme: THEME === 'dark' ? 'dark' : 'light', reducedMotion: 'reduce', locale: 'uz-UZ' });
  await ctx.route(/googleapis|gstatic/, (r) => r.abort());
  await ctx.addInitScript((css) => { document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); }); }, FONT_CSS);
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
  await login(page); await clean(page); await hash(page, '#/home');
  await shot(page, `${p}-discovery`, 0);
  if (ONLY === 'discovery') { await ctx.close(); continue; }
  await shot(page, `${p}-discovery-scrolled`, p === 'm' ? 760 : 560);
  const ids = await page.evaluate(() => [...new Set([...document.querySelectorAll('#v [data-a^="open:"]')].map((e) => e.dataset.a.slice(5)))]);
  const c1 = ids[0];
  await hash(page, '#/c/' + c1);
  await shot(page, `${p}-profile`, 0);
  const sy = await page.evaluate(() => { const h = [...document.querySelectorAll('#v h2')].find((x) => /Xizmatlar/.test(x.textContent)); return h ? h.getBoundingClientRect().top + scrollY - 90 : 400; });
  await shot(page, `${p}-profile-services`, sy);
  // extra bookings so the list is not empty
  let extra = 0;
  for (const c of ids.slice(1)) { if (extra >= 2) break; if ((await book(page, c, [2, 3, 4])) == null) continue; extra++; await page.fill('#place', ''); await click(page, 'bp:Magic City hududi'); await page.click('#sub'); await page.waitForFunction(() => /#\/b\//.test(location.hash), null, { timeout: 15000 }); }
  if ((await book(page, c1, [1, 2, 3, 4])) == null) throw new Error('no slot for main companion');
  await click(page, 'bp:Amir Temur xiyoboni');
  await shot(page, `${p}-booking-dialog`, 0);
  await page.click('#sub'); await page.waitForFunction(() => /#\/b\//.test(location.hash) && document.querySelector('.tl'), null, { timeout: 15000 });
  await shot(page, `${p}-admin-detail`, 0);
  const bid = await page.evaluate(() => location.hash.split('/').pop());
  await page.evaluate((id) => { YM.demo.companionAccept(id); YAPP.route(); }, bid);
  await page.waitForFunction(() => /qabul qildi/i.test(document.querySelector('#v').textContent), null, { timeout: 15000 });
  await shot(page, `${p}-admin-confirm`, 0);
  await hash(page, '#/bookings');
  await shot(page, `${p}-bookings`, 0);
  await ctx.close();
}
await browser.close();
