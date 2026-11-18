/**
 * Notification sound (owner decision 2026-11-11, variant A "tomchi-rin": original synthesis, tools/sounds/yondo_notify.py).
 * Plays when a new notification arrives while the app is open. Per-device switch, default ON.
 * Rules: at most once per MIN_GAP_MS, never overlapping itself, volume 0.7, a play() the browser refuses
 * (autoplay policy before the first user gesture) is swallowed silently.
 */
export const SOUND_URL = '/sounds/yondo-notify.mp3';
export const MIN_GAP_MS = 5000;
export const VOLUME = 0.7;
const KEY = 'yondo.notifySound';

let audio: HTMLAudioElement | null = null;
let lastPlayedAt = -Infinity;

/** Device-local switch; ON unless explicitly turned off. Storage errors never throw. */
export function soundEnabled(): boolean {
  try {
    return window.localStorage.getItem(KEY) !== 'off';
  } catch {
    return true;
  }
}

export function setSoundEnabled(on: boolean): void {
  try {
    window.localStorage.setItem(KEY, on ? 'on' : 'off');
  } catch {
    /* private mode / blocked storage: the switch simply does not persist */
  }
}

/** `force` (the Settings test button) ignores the switch and the 5 s gap; it restarts a playing sound instead of stacking. */
export function playNotifySound(opts: { force?: boolean } = {}): void {
  const force = opts.force === true;
  if (!force && !soundEnabled()) return;
  const now = Date.now();
  if (!force && now - lastPlayedAt < MIN_GAP_MS) return;
  try {
    if (!audio) {
      audio = new Audio(SOUND_URL);
      audio.volume = VOLUME;
    }
    if (!audio.paused && !audio.ended) {
      if (!force) return; // never overlap
      audio.currentTime = 0;
    }
    lastPlayedAt = now;
    const p = audio.play() as Promise<void> | undefined;
    if (p && typeof p.catch === 'function') p.catch(() => {});
  } catch {
    /* no audio support: stay silent */
  }
}

/** Tests only. */
export function resetNotifySound(): void {
  audio = null;
  lastPlayedAt = -Infinity;
}
