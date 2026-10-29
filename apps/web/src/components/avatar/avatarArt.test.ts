import { describe, expect, it } from 'vitest';
import { GROUNDS, look, pick, PATTERN_IDS, spriteMarkup, STEP } from './avatarArt';

describe('avatar pick (spec section 1 test vectors)', () => {
  it.each([
    ['7c1d6f0e-5b6a-4d0e-9b53-1a2f3c4d5e61', 'bodom8', 'paper', 1],
    ['c0ffee00-0000-4000-8000-00000000a001', 'lattice', 'paper', 1],
    ['demo-customer-1', 'anor', 'carrot', 0],
    ['b2a9e8d4-77aa-4c10-8f3e-0f9d5c2a1b77', 'anor', 'ink', 1],
  ] as const)('%s -> %s, %s, fold %i', (id, pattern, ground, fold) => {
    const l = look(id);
    expect([l.id, l.ground, l.fold]).toEqual([pattern, ground, fold]);
  });

  it('stays inside 12 patterns x 3 grounds x 2 folds and is deterministic', () => {
    const seen = { p: new Set<number>(), w: new Set<number>(), f: new Set<number>() };
    for (let i = 0; i < 3000; i++) {
      const id = `user-${i}-${(i * 2654435761) % 99991}`;
      const a = pick(id);
      expect(pick(id)).toEqual(a);
      expect(a.pattern).toBeGreaterThanOrEqual(0);
      expect(a.pattern).toBeLessThan(12);
      expect(a.way).toBeLessThan(3);
      expect([0, 1]).toContain(a.phase);
      seen.p.add(a.pattern);
      seen.w.add(a.way);
      seen.f.add(a.phase);
    }
    expect([seen.p.size, seen.w.size, seen.f.size]).toEqual([12, 3, 2]);
  });

  it('draws the pomegranate the same in both folds', () => {
    expect(look('b2a9e8d4-77aa-4c10-8f3e-0f9d5c2a1b77').transform).toBe('');
    expect(STEP).toHaveLength(12);
    expect(GROUNDS).toEqual(['ink', 'paper', 'carrot']);
  });

  it('builds one prefixed symbol per pattern', () => {
    const sprite = spriteMarkup();
    for (const id of PATTERN_IDS) expect(sprite).toContain(`id="av-${id}"`);
    expect(sprite).not.toMatch(/class="(m|a|g|ms|as|gs|bold|fine)"/);
    expect(sprite).toContain('class="av-fine"');
  });
});
