import { describe, expect, it } from 'vitest';
import { ageOn, dobProblem, latestAdultDob } from './age';

describe('18+ helpers (the server decides; these only explain early)', () => {
  it('counts birthdays exactly', () => {
    expect(ageOn('2008-11-19', '2026-11-19')).toBe(18);
    expect(ageOn('2008-11-20', '2026-11-19')).toBe(17);
  });
  it('flags under 18, future and implausible dates', () => {
    expect(dobProblem('2008-11-19', '2026-11-19')).toBeNull();
    expect(dobProblem('2008-11-20', '2026-11-19')).toBe('age.under18');
    expect(dobProblem('2027-01-01', '2026-11-19')).toBe('age.invalid');
    expect(dobProblem('1890-01-01', '2026-11-19')).toBe('age.invalid');
    expect(dobProblem('', '2026-11-19')).toBe('age.invalid');
  });
  it('gives the latest adult birth date for the date picker', () => {
    expect(latestAdultDob('2026-11-19')).toBe('2008-11-19');
  });
});
