import { afterEach, describe, expect, it, vi } from 'vitest';
import { createFirstRun, firstRun, FLOWS, type FlowDef } from './firstRun';

const defs = {
  onboarding: { topic: 'onboarding', variant: 'customer', version: 1, whenUnavailable: 'show' },
  intro: { topic: 'intro', version: 1, whenUnavailable: 'skip' },
} satisfies Record<string, FlowDef>;

/** A storage that fails the way private modes / blocked site data do. */
function brokenStorage(failing: Array<'getItem' | 'setItem' | 'removeItem'>): Storage {
  const real = window.localStorage;
  return new Proxy(real, {
    get(target, prop) {
      if (failing.includes(prop as never)) {
        return () => {
          throw new DOMException('denied', 'SecurityError');
        };
      }
      const value = Reflect.get(target, prop, target);
      return typeof value === 'function' ? value.bind(target) : value;
    },
  });
}

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('firstRun', () => {
  it('is unseen until marked, then stays seen across a "reload" (new instance, same storage)', () => {
    const a = createFirstRun(defs);
    expect(a.isSeen('onboarding')).toBe(false);
    expect(a.markSeen('onboarding')).toBe(true);
    expect(a.isSeen('onboarding')).toBe(true);
    expect(createFirstRun(defs).isSeen('onboarding')).toBe(true);
    expect(createFirstRun(defs).isSeen('intro')).toBe(false); // flows are independent
  });

  it('stores only a versioned flag under a key without personal data', () => {
    const a = createFirstRun(defs);
    a.markSeen('onboarding');
    a.markSeen('intro');
    expect(Object.fromEntries(Object.entries(localStorage))).toEqual({ 'yondo.onboarding.v1.customer': '1', 'yondo.intro.v1': '1' });
  });

  it('uses the keys the app ships with', () => {
    expect(firstRun.keyOf('onboarding.customer')).toBe('yondo.onboarding.v1.customer');
    expect(firstRun.keyOf('onboarding.companion')).toBe('yondo.onboarding.v1.companion');
    expect(firstRun.keyOf('intro')).toBe('yondo.intro.v1');
    expect(Object.keys(FLOWS)).toEqual(['intro', 'onboarding.customer', 'onboarding.companion']);
  });

  it('a version bump shows the flow again and leaves the old flag untouched', () => {
    createFirstRun(defs).markSeen('onboarding');
    const v2 = createFirstRun({ ...defs, onboarding: { ...defs.onboarding, version: 2 } });
    expect(v2.keyOf('onboarding')).toBe('yondo.onboarding.v2.customer');
    expect(v2.isSeen('onboarding')).toBe(false);
    v2.markSeen('onboarding');
    expect(createFirstRun(defs).isSeen('onboarding')).toBe(true);
    expect(localStorage.getItem('yondo.onboarding.v1.customer')).toBe('1');
  });

  it('ignores a corrupt stored value', () => {
    localStorage.setItem('yondo.onboarding.v1.customer', 'true');
    expect(createFirstRun(defs).isSeen('onboarding')).toBe(false);
  });

  it('forget() makes the flow unseen again', () => {
    const a = createFirstRun(defs);
    a.markSeen('onboarding');
    a.forget('onboarding');
    expect(a.isSeen('onboarding')).toBe(false);
    expect(localStorage.getItem('yondo.onboarding.v1.customer')).toBeNull();
  });

  it('storage that throws on read: never throws; "show" flows are shown, "skip" flows are not', () => {
    const a = createFirstRun(defs, () => brokenStorage(['getItem', 'setItem', 'removeItem']));
    expect(() => a.isSeen('onboarding')).not.toThrow();
    expect(a.isSeen('onboarding')).toBe(false);
    expect(a.isSeen('intro')).toBe(true);
  });

  it('storage that cannot be written: marking still works for this page load, so nothing loops', () => {
    const a = createFirstRun(defs, () => brokenStorage(['setItem']));
    expect(a.isSeen('onboarding')).toBe(false);
    expect(a.markSeen('onboarding')).toBe(false); // reported, not thrown
    expect(a.isSeen('onboarding')).toBe(true);
    expect(() => a.forget('onboarding')).not.toThrow();
  });

  it('accessing localStorage itself may throw (blocked site data)', () => {
    const a = createFirstRun(defs, () => {
      throw new DOMException('denied', 'SecurityError');
    });
    expect(a.isSeen('onboarding')).toBe(false);
    expect(a.markSeen('onboarding')).toBe(false);
    expect(a.isSeen('onboarding')).toBe(true);
    expect(() => a.forget('intro')).not.toThrow();
  });
});
