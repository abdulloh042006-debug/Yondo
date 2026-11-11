// Render reel 1: node render.mjs <page.html> <out.mp4|stillsDir> [stills t1 t2 ...]
import { spawn } from 'node:child_process';
import { chromium } from '/home/claude/fonttools/node_modules/playwright-core/index.mjs';
const [pagePath, out, mode, ...ts] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox', '--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
await page.goto('file://' + pagePath); await page.evaluate(() => window.ready);
const total = await page.evaluate(() => window.TOTAL);
if (mode === 'stills') {
  for (const t of ts.map(Number)) { await page.evaluate((x) => window.render(x), t); await page.screenshot({ path: `${out}/s-${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 80 }); }
} else {
  const n = Math.round(total * 30);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', out]);
  const t0 = Date.now();
  for (let f = 0; f < n; f++) {
    await page.evaluate((x) => window.render(x), f / 30);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 200 === 0) console.log(f, '/', n, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r)); console.log('DONE', n, ((Date.now() - t0) / 1000).toFixed(0) + 's');
}
if (errs.length) console.log('ERRORS', errs.slice(0, 5));
await browser.close();
