// Builds design-prototype/redesign/index.html: src/prototype.html with the repo's own fonts inlined
// (Space Grotesk + Manrope variable, latin + latin-ext, SIL OFL, from apps/web's @fontsource-variable packages),
// so the prototype is one self-contained file that needs no network.
// Usage (after `npm ci` in apps/web): node design-prototype/redesign/build.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const fsrc = process.env.FONTS_DIR || join(here, '../../apps/web/node_modules/@fontsource-variable');
const RANGES = {
  latin: 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD',
  'latin-ext': 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF',
};
const faces = [];
for (const [pkg, family] of [['space-grotesk', 'Space Grotesk Variable'], ['manrope', 'Manrope Variable']]) {
  for (const sub of ['latin-ext', 'latin']) {
    const b64 = readFileSync(join(fsrc, pkg, 'files', `${pkg}-${sub}-wght-normal.woff2`)).toString('base64');
    faces.push(`@font-face{font-family:'${family}';font-style:normal;font-display:swap;font-weight:${pkg === 'manrope' ? '200 800' : '300 700'};src:url(data:font/woff2;base64,${b64}) format('woff2-variations');unicode-range:${RANGES[sub]};}`);
  }
}
const src = readFileSync(join(here, 'src/prototype.html'), 'utf8');
if (!src.includes('/*@FONTS@*/')) throw new Error('font marker missing');
const out = src.replace('/*@FONTS@*/', '/* BUILT FILE: edit src/prototype.html and run build.mjs */\n' + faces.join('\n'));
writeFileSync(join(here, 'index.html'), out);
console.log('index.html', (out.length / 1024).toFixed(0), 'KB');
