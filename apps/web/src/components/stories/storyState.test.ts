import { afterEach, describe, expect, it } from 'vitest';
import { arcPaths, autoAdvanceMs, dayOffset, isSeen, markSeen } from './storyState';

afterEach(() => localStorage.clear());

describe('seen state', () => {
  it('is per profile and latest_at, and a newer card makes the ring unseen again', () => {
    expect(isSeen('p1', '2026-10-29T10:00:00Z')).toBe(false);
    markSeen('p1', '2026-10-29T10:00:00Z');
    expect(isSeen('p1', '2026-10-29T10:00:00Z')).toBe(true);
    expect(isSeen('p1', '2026-10-29T11:00:00Z')).toBe(false);
    expect(isSeen('p2', '2026-10-29T10:00:00Z')).toBe(false);
  });
  it('lives in localStorage only and survives corrupt data', () => {
    markSeen('p1', 'x');
    expect(Object.keys(localStorage)).toContain('yondo.storiesSeen');
    localStorage.setItem('yondo.storiesSeen', '{not json');
    expect(isSeen('p1', 'x')).toBe(false);
    expect(() => markSeen('p1', 'x')).not.toThrow();
  });
});

describe('timings and geometry', () => {
  it('auto-advances 6 s (note) / 8 s (availability), never under reduced motion', () => {
    expect(autoAdvanceMs('note', false)).toBe(6000);
    expect(autoAdvanceMs('availability', false)).toBe(8000);
    expect(autoAdvanceMs('note', true)).toBeNull();
    expect(autoAdvanceMs('availability', true)).toBeNull();
  });
  it('draws one arc per card (1 to 5)', () => {
    for (const n of [1, 2, 3, 4, 5]) expect(arcPaths(76, n)).toHaveLength(n);
    expect(arcPaths(76, 9)).toHaveLength(5);
  });
  it('labels today and tomorrow in local days', () => {
    const now = new Date(2026, 9, 29, 12, 0, 0);
    expect(dayOffset(new Date(2026, 9, 29, 18, 0).toISOString(), now)).toBe(0);
    expect(dayOffset(new Date(2026, 9, 30, 9, 0).toISOString(), now)).toBe(1);
    expect(dayOffset(new Date(2026, 10, 2, 9, 0).toISOString(), now)).toBeNull();
  });
});
