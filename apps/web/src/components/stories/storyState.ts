/** Pure helpers for stories: seen state (this device only), timings, small formatting. */
import type { Schemas } from '../../api/client';

export type Ring = Schemas['StoryRing'];
export type Slide = Schemas['StorySlide'];
export type OwnStory = Schemas['OwnStory'];

/** Server rule: at most 5 active cards per companion (stories_max_active). */
export const MAX_ACTIVE = 5;
export const CAPTION_MAX = 80;
/** Auto-advance: 6 s for a note, 8 s for an availability card. None under prefers-reduced-motion. */
export const NOTE_MS = 6000;
export const AVAILABILITY_MS = 8000;

export function autoAdvanceMs(kind: Slide['kind'], reducedMotion: boolean): number | null {
  if (reducedMotion) return null;
  return kind === 'note' ? NOTE_MS : AVAILABILITY_MS;
}

/* Seen state: profile_id -> latest_at that was viewed. Kept in localStorage only; it is NEVER sent to the server
   (the API records no viewers). A newer latest_at makes the ring unseen again. */
const SEEN_KEY = 'yondo.storiesSeen';

function readSeen(): Record<string, string> {
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function isSeen(profileId: string, latestAt: string): boolean {
  return readSeen()[profileId] === latestAt;
}

export function markSeen(profileId: string, latestAt: string): void {
  try {
    const all = readSeen();
    all[profileId] = latestAt;
    // keep the record small: the newest 200 profiles are plenty
    const keys = Object.keys(all);
    if (keys.length > 200) for (const k of keys.slice(0, keys.length - 200)) delete all[k];
    localStorage.setItem(SEEN_KEY, JSON.stringify(all));
  } catch {
    /* storage blocked: the ring simply stays unseen */
  }
}

export function prefersReducedMotion(): boolean {
  try {
    return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

/** Minutes since `iso`, floored at 0. */
export function ageMinutes(iso: string, now: number = Date.now()): number {
  return Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000));
}

/** "HH:MM" in the viewer's local time zone, digits only (same in every UI language). */
export function clock(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso));
}

/** 0 = today, 1 = tomorrow, otherwise null (local calendar days). */
export function dayOffset(iso: string, now: Date = new Date()): 0 | 1 | null {
  const a = new Date(iso);
  const start = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((start(a) - start(now)) / 86400000);
  return diff === 0 ? 0 : diff === 1 ? 1 : null;
}

/** Arc geometry for a ring of `count` (1..5) segments with 14 degree gaps; the single-card case is a full circle. */
export function arcPaths(size: number, count: number): string[] {
  const n = Math.min(Math.max(Math.round(count), 1), MAX_ACTIVE);
  const r = size / 2 - 2;
  const c = size / 2;
  const gap = n > 1 ? 14 : 0;
  const step = 360 / n;
  const pt = (d: number): [number, number] => [c + r * Math.cos((d * Math.PI) / 180), c + r * Math.sin((d * Math.PI) / 180)];
  if (n === 1) return [`M${c - r} ${c}a${r} ${r} 0 1 1 ${2 * r} 0a${r} ${r} 0 1 1 ${-2 * r} 0`];
  return Array.from({ length: n }, (_, k) => {
    const a0 = -90 + k * step + gap / 2;
    const a1 = -90 + (k + 1) * step - gap / 2;
    const [x0, y0] = pt(a0);
    const [x1, y1] = pt(a1);
    return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
  });
}
