// Render a kit page: node kit/render.mjs <page.html> <out.mp4 | stillsDir> [stills t1 t2 ...]
// The page exposes window.render(t), window.TOTAL and window.ready. 1080x1920, 30 fps, H.264 (video only; audio is muxed later).
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
const [pagePath, out, mode, ...ts] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
await page.goto('file://' + pagePath); await page.evaluate(() => window.ready);
if (mode === 'stills') {
  for (const t of ts.map(Number)) { await page.evaluate((x) => window.render(x), t); await page.screenshot({ path: `${out}/s-${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 80 }); }
} else {
  const n = Math.round((await page.evaluate(() => window.TOTAL)) * 30);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < n; f++) {
    await page.evaluate((x) => window.render(x), f / 30);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r)); console.log('DONE', n, 'frames');
}
if (errs.length) { console.log('ERRORS', errs.slice(0, 5)); process.exitCode = 1; }
await browser.close();
