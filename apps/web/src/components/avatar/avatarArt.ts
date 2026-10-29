/**
 * Customer avatar art: geometric Uzbek ornaments on a circle (no faces, no figures).
 * Pure port of the reference generator in design-prototype/brand/avatar/preview.html
 * (spec: docs/stories-avatars-design.md section 1). Same id -> same look on every device.
 */
export const PATTERN_IDS = ['star8', 'star10', 'bodom8', 'rhomb4', 'chain', 'strap8', 'lattice', 'bodom', 'quatrefoil', 'hex7', 'adras', 'anor'] as const;
export type PatternId = (typeof PATTERN_IDS)[number];
export const GROUNDS = ['ink', 'paper', 'carrot'] as const;
export type Ground = (typeof GROUNDS)[number];

export interface AvatarPick {
  /** Index into PATTERN_IDS (0..11). */
  pattern: number;
  /** Index into GROUNDS (0..2). */
  way: number;
  /** Fold 0 or 1. */
  phase: number;
}

/** FNV-1a 32-bit over UTF-16 units, then pattern = h mod 12, ground = floor(h/12) mod 3, fold = floor(h/36) mod 2. */
export function pick(id: string): AvatarPick {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619) >>> 0;
  const n = Math.floor(h / 12);
  return { pattern: h % 12, way: n % 3, phase: Math.floor(n / 3) % 2 };
}

const C = 24;
const rad = (d: number) => (d * Math.PI) / 180;
const f = (n: number) => +n.toFixed(2);
type Pt = [number, number];
const P = (r: number, d: number, cx = C, cy = C): Pt => [cx + r * Math.cos(rad(d)), cy + r * Math.sin(rad(d))];
const D = (pts: Pt[]) => 'M' + pts.map((p) => p.map(f).join(' ')).join('L') + 'Z';
const poly = (n: number, r: number, d0 = -90, cx = C, cy = C) => D(Array.from({ length: n }, (_, i) => P(r, d0 + (i * 360) / n, cx, cy)));
const star = (n: number, ro: number, ri: number, d0 = -90) => D(Array.from({ length: 2 * n }, (_, i) => P(i % 2 ? ri : ro, d0 + (i * 180) / n)));
const dia = (cx: number, cy: number, r: number) => D([[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]]);
const el = (c: string, d: string, x = '') => `<path class="${c}" d="${d}"${x}/>`;
const dot = (c: string, x: number, y: number, r: number) => `<circle class="${c}" cx="${f(x)}" cy="${f(y)}" r="${r}"/>`;
const ring = (c: string, x: number, y: number, r: number) => `<circle class="${c}" fill="none" cx="${f(x)}" cy="${f(y)}" r="${r}"/>`;
const spin = (n: number, fn: () => string, off = 0) => Array.from({ length: n }, (_, i) => `<g transform="rotate(${off + (i * 360) / n} 24 24)">${fn()}</g>`).join('');
const ZIG = (y: number) => 'M' + Array.from({ length: 8 }, (_, i) => `${-4 + i * 8} ${y + (i % 2 ? -5 : 5)}`).join('L');
const T = Math.tan(rad(36));
const BODOM = 'M32 4C26 10 10 18 10 31A13 13 0 0 0 36 31C36 20 33 10 32 4Z';

/** [fold step in degrees, bold layer (every shape >= 3 units), fine layer (drawn from 44 px up)] */
type Art = [number, () => string, () => string];
const ART: Record<PatternId, Art> = {
  star8: [22.5, () => el('m', poly(4, 20, 0) + poly(4, 20, 45)) + dot('a', 24, 24, 3.4), () => el('g', poly(4, 9, 0) + poly(4, 9, 45)) + dot('a', 24, 24, 3.4)],
  star10: [18, () => el('m', star(10, 21, 13)) + dot('a', 24, 24, 3.4), () => el('g', poly(10, 8)) + dot('a', 24, 24, 3.4)],
  bodom8: [22.5, () => spin(8, () => el('m', 'M24 25C15 17 17 8 24 3.5C31 8 33 17 24 25Z')) + dot('a', 24, 24, 3.6), () => spin(8, () => el('gs', 'M24 8V16')) + dot('a', 24, 24, 3.6)],
  rhomb4: [45, () => spin(4, () => el('m', `M24 24L${24 + 10.5} ${24 - 10.5 * T}L45 24L${24 + 10.5} ${24 + 10.5 * T}Z`)) + spin(4, () => el('a', 'M35 24L39 21.1L43 24L39 26.9Z'), 45), () => spin(4, () => el('gs', 'M30 24H38'))],
  chain: [45, () => [[24, 24], [44, 24], [4, 24], [24, 44], [24, 4]].map(([x, y]) => el('m', dia(x, y, 10.5))).join('') + [[10, 10], [38, 10], [10, 38], [38, 38]].map(([x, y]) => el('a', dia(x, y, 4.6))).join(''), () => el('g', dia(24, 24, 4.4))],
  strap8: [22.5, () => el('ms', poly(4, 19, 0)) + el('ms', poly(4, 19, 45)) + Array.from({ length: 8 }, (_, k) => {
      const th = 22.5 + 45 * k;
      const [x, y] = P(14.54, th);
      const al = k % 2 ? Math.round(th / 90) * 90 : 45 + 90 * Math.floor(th / 90);
      const c = Math.cos(rad(al + 90));
      const s = Math.sin(rad(al + 90));
      const seg = (L: number, cls: string, w: number) => `<path class="${cls}" d="M${f(x - c * L)} ${f(y - s * L)}L${f(x + c * L)} ${f(y + s * L)}" stroke-width="${w}"/>`;
      return seg(3, 'gs', 5.6) + seg(4.6, 'ms', 3.2);
    }).join('') + dot('a', 24, 24, 3.4), () => el('m', poly(4, 6.5, 0) + poly(4, 6.5, 45)) + dot('a', 24, 24, 3)],
  lattice: [45, () => [-32, -16, 0, 16, 32].map((c) => el('ms', `M-10 ${-10 - c}L58 ${58 - c}`)).join('') + [16, 32, 48, 64, 80].map((s) => el('ms', `M-10 ${s + 10}L58 ${s - 58}`)).join('') + [[24, 24], [16, 16], [32, 32], [16, 32], [32, 16]].map(([x, y]) => dot('g', x, y, 5.4) + dot('a', x, y, 3.4)).join(''), () => [[32, 24], [16, 24], [24, 32], [24, 16]].map(([x, y]) => el('m', dia(x, y, 2.4))).join('')],
  bodom: [0, () => el('m', BODOM) + el('a', BODOM, ' transform="translate(12 15.5) scale(.5)"'), () => el('gs', 'M23 22C25 16 28 11 31 8')],
  quatrefoil: [45, () => [[8.5, 0], [-8.5, 0], [0, 8.5], [0, -8.5]].map(([x, y]) => dot('m', 24 + x, 24 + y, 11)).join('') + dot('a', 24, 24, 3.4), () => ring('gs', 24, 24, 6.2) + [[12, 12], [36, 12], [12, 36], [36, 36]].map(([x, y]) => dot('a', x, y, 2.2)).join('')],
  hex7: [30, () => Array.from({ length: 6 }, (_, i) => { const [x, y] = P(14.4, i * 60); return el('m', poly(6, 7.4, -90, x, y)); }).join('') + el('a', poly(6, 7.4)), () => Array.from({ length: 6 }, (_, i) => { const [x, y] = P(14.4, i * 60); return el('g', poly(6, 3, -90, x, y)); }).join('')],
  adras: [90, () => el('ms', ZIG(11)) + el('ms', ZIG(37)) + el('as', ZIG(24)), () => [11, 37].map((y) => el('gs', ZIG(y))).join('')],
  anor: [0, () => dot('m', 24, 28, 14) + el('m', 'M16.5 17L18 9L21.5 13L24 7L26.5 13L30 9L31.5 17Z') + dot('a', 24, 28, 5.2), () => ring('gs', 24, 28, 9) + Array.from({ length: 8 }, (_, i) => { const [x, y] = P(11.6, i * 45, 24, 28); return dot('g', x, y, 1.4); }).join('')],
};

/** Degrees the motif turns when fold = 1 (0 = special case, see foldTransform). */
export const STEP: number[] = PATTERN_IDS.map((id) => ART[id][0]);

/** Transform for the <use> when fold = 1: rotate by STEP; the single almond is mirrored; the pomegranate has no fold. */
export function foldTransform(pattern: number): string {
  const id = PATTERN_IDS[pattern];
  if (id === 'bodom') return 'translate(48 0) scale(-1 1)';
  if (id === 'anor') return '';
  return `rotate(${STEP[pattern]} 24 24)`;
}

/** Class names get an `av-` prefix so they cannot collide with the app stylesheet. */
const prefixed = (svg: string) => svg.replace(/class="(\w+)"/g, 'class="av-$1"');

export function symbolMarkup(pattern: number): string {
  const [, bold, fine] = ART[PATTERN_IDS[pattern]];
  return `<symbol id="av-${PATTERN_IDS[pattern]}" viewBox="0 0 48 48">${prefixed(`<g class="bold">${bold()}</g><g class="fine">${fine()}</g>`)}</symbol>`;
}

export const spriteMarkup = (): string => PATTERN_IDS.map((_, i) => symbolMarkup(i)).join('');

export interface AvatarLook {
  id: PatternId;
  ground: Ground;
  fold: 0 | 1;
  /** transform for the <use>, '' when none */
  transform: string;
}

export function look(seed: string): AvatarLook {
  const p = pick(seed);
  const fold = p.phase as 0 | 1;
  return { id: PATTERN_IDS[p.pattern], ground: GROUNDS[p.way], fold, transform: fold ? foldTransform(p.pattern) : '' };
}
