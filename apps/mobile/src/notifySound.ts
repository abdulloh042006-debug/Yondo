/**
 * In-app notification sound (owner decision 2026-11-11, variant A "tomchi-rin"; same file as the web build).
 * Plays only while the app is open (no push yet). Same rules as apps/web/src/lib/notifySound.ts: at most once per
 * 5 s, never overlapping, volume 0.7, a refused play() is swallowed, per-device switch (default ON).
 * Silent mode: `playsInSilentMode: false` makes iOS respect the ring/silent switch, so the automatic sound stays
 * quiet there. Android has no such API for media playback; it follows the media volume. The Settings test button
 * (force) is an explicit tap, but still goes through the same audio mode and never overrides silent mode.
 */
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

import { getItem, setItem } from './storage';

export const MIN_GAP_MS = 5000;
export const VOLUME = 0.7;
const KEY = 'yondo.notifySound';
const DURATION_MS = 2400;

let player: AudioPlayer | null = null;
let lastPlayedAt = -Infinity;
let playingUntil = 0;
let enabled = true;
let loaded: Promise<void> | null = null;

/** Reads the saved switch once; until then the default (ON) applies. */
export function loadSoundPref(): Promise<void> {
  loaded ??= getItem(KEY, 'pref').then((v) => {
    enabled = v !== 'off';
  });
  return loaded;
}

export function soundEnabled(): boolean {
  return enabled;
}

export function setSoundEnabled(on: boolean): void {
  enabled = on;
  void setItem(KEY, on ? 'on' : 'off', 'pref');
}

export function playNotifySound(opts: { force?: boolean } = {}): void {
  const force = opts.force === true;
  if (!force && !enabled) return;
  const now = Date.now();
  if (!force && now - lastPlayedAt < MIN_GAP_MS) return;
  if (!force && now < playingUntil) return; // never overlap
  try {
    if (!player) {
      void setAudioModeAsync({ playsInSilentMode: false, interruptionMode: 'mixWithOthers', shouldPlayInBackground: false }).catch(() => {});
      player = createAudioPlayer(require('../assets/sounds/yondo-notify.mp3') as number);
      player.volume = VOLUME;
    }
    lastPlayedAt = now;
    playingUntil = now + DURATION_MS;
    const p = player;
    void Promise.resolve(p.seekTo(0))
      .catch(() => {})
      .then(() => p.play());
  } catch {
    /* audio unavailable: stay silent */
  }
}
