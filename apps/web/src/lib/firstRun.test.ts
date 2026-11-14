import { describe, expect, it } from 'vitest';
import { createFirstRun } from './firstRun';

const DEFS = { intro: { topic: 'intro', version: 1 } } as const;

function memoryStorage(): Storage {
  const m = new Map<string, string>();
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, String(v)),
    removeItem: (k) => void m.delete(k),
    clear: () => m.clear(),
    key: () => null,
    get length() {
      return m.size;
    },
  } as Storage;
}
const broken = (): Storage => {
  throw new Error('storage blocked');
};

describe('first-run flag', () => {
  it('uses a versioned key and remembers across instances that share the storage', () => {
    const s = memoryStorage();
    const a = createFirstRun(DEFS, () => s);
    expect(a.keyOf('intro')).toBe('yondo.intro.v1');
    expect(a.isSeen('intro')).toBe(false);
    expect(a.markSeen('intro')).toBe(true);
    expect(createFirstRun(DEFS, () => s).isSeen('intro')).toBe(true);
    a.forget('intro');
    expect(createFirstRun(DEFS, () => s).isSeen('intro')).toBe(false);
  });

  it('never throws without storage and still remembers for the rest of the page load', () => {
    const f = createFirstRun(DEFS, broken);
    expect(f.isSeen('intro')).toBe(false);
    expect(f.markSeen('intro')).toBe(false);
    expect(f.isSeen('intro')).toBe(true);
    expect(() => f.forget('intro')).not.toThrow();
  });
});
