import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MIN_GAP_MS, playNotifySound, resetNotifySound, setSoundEnabled, soundEnabled, VOLUME } from './notifySound';

class FakeAudio {
  static instances: FakeAudio[] = [];
  static rejectPlay = false;
  volume = 1;
  paused = true;
  ended = false;
  currentTime = 0;
  plays = 0;
  constructor(public src: string) {
    FakeAudio.instances.push(this);
  }
  play() {
    this.plays += 1;
    this.paused = false;
    return FakeAudio.rejectPlay ? Promise.reject(new DOMException('blocked', 'NotAllowedError')) : Promise.resolve();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));
  FakeAudio.instances = [];
  FakeAudio.rejectPlay = false;
  vi.stubGlobal('Audio', FakeAudio);
  localStorage.clear();
  resetNotifySound();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
const plays = () => FakeAudio.instances.reduce((n, a) => n + a.plays, 0);

describe('notifySound', () => {
  it('plays at volume 0.7', () => {
    playNotifySound();
    expect(plays()).toBe(1);
    expect(FakeAudio.instances[0].volume).toBe(VOLUME);
    expect(VOLUME).toBe(0.7);
  });

  it('is silent when the switch is off, but force (test button) still plays', () => {
    setSoundEnabled(false);
    expect(soundEnabled()).toBe(false);
    playNotifySound();
    expect(plays()).toBe(0);
    playNotifySound({ force: true });
    expect(plays()).toBe(1);
  });

  it('defaults to ON and survives broken storage', () => {
    expect(soundEnabled()).toBe(true);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(soundEnabled()).toBe(true);
    expect(() => setSoundEnabled(false)).not.toThrow();
    vi.restoreAllMocks();
  });

  it('swallows a play() rejected by the autoplay policy', async () => {
    FakeAudio.rejectPlay = true;
    const onErr = vi.fn();
    process.on('unhandledRejection', onErr);
    expect(() => playNotifySound()).not.toThrow();
    await vi.advanceTimersByTimeAsync(0);
    process.off('unhandledRejection', onErr);
    expect(onErr).not.toHaveBeenCalled();
  });

  it('keeps a 5 s gap and never overlaps', () => {
    playNotifySound();
    FakeAudio.instances[0].paused = true; // finished quickly
    vi.advanceTimersByTime(MIN_GAP_MS - 1);
    playNotifySound();
    expect(plays()).toBe(1);
    vi.advanceTimersByTime(1);
    playNotifySound();
    expect(plays()).toBe(2);
    // still playing (paused=false) after the gap: no overlap
    vi.advanceTimersByTime(MIN_GAP_MS);
    playNotifySound();
    expect(plays()).toBe(2);
  });

  it('force restarts a playing sound instead of stacking', () => {
    playNotifySound();
    playNotifySound({ force: true });
    expect(FakeAudio.instances).toHaveLength(1);
    expect(FakeAudio.instances[0].currentTime).toBe(0);
    expect(plays()).toBe(2);
  });
});
