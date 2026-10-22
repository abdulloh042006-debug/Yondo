import { spawn } from 'node:child_process';
import { chromium } from '/home/claude/Yondo3/apps/web/node_modules/playwright-core/index.mjs';
const AD = '/tmp/claude-0/-home-claude/80ed5239-9a87-5b7a-bb32-cb2c8e001f18/scratchpad/ad';
const [fmt, lang, mode, ...rest] = process.argv.slice(2);
const W = fmt === 'v' ? 1080 : 1920, H = fmt === 'v' ? 1920 : 1080;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox', '--allow-file-access-from-files', '--disable-web-security'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
const errs = []; page.on('pageerror', (e) => errs.push(e.message)); page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`file://${AD}/page.html?fmt=${fmt}&lang=${lang}`);
await page.evaluate(() => window.ready);
const total = await page.evaluate(() => window.TOTAL);
if (mode === 'stills') {
  for (const t of rest.map(Number)) { await page.evaluate((x) => window.render(x), t); await page.screenshot({ path: `${AD}/${process.env.STILLS || 'stills'}/${fmt}-${lang}-${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 80 }); }
} else {
  const n = Math.ceil(total * 30);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', `${AD}/out/video-${fmt}-${lang}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = 0; f < n; f++) {
    await page.evaluate((x) => window.render(x), f / 30);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 150 === 0) console.log(fmt, lang, f, '/', n, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r));
  console.log('DONE', fmt, lang, n, 'frames', ((Date.now() - t0) / 1000).toFixed(0) + 's');
}
if (errs.length) console.log('ERRORS', errs.slice(0, 5));
await browser.close();
