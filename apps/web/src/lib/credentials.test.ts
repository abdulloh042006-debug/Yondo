import { describe, expect, it } from 'vitest';
import { normalizeUsername, passwordProblem, usernameValid } from './credentials';

describe('password and username rules (client mirror of the server)', () => {
  it('passwords: 8–128 characters, not the phone number in common spellings', () => {
    expect(passwordProblem('short')).toBe('pw.tooShort');
    expect(passwordProblem('x'.repeat(129))).toBe('pw.tooLong');
    expect(passwordProblem('a long enough phrase')).toBeNull();
    const phone = '+998901110003';
    for (const spelling of ['+998901110003', '998901110003', '901110003', '+998 90 111 00 03', '0901110003'])
      expect(passwordProblem(spelling, phone)).toBe('pw.isPhone');
    expect(passwordProblem('90111000312', phone)).toBeNull();
  });
  it('usernames: 3–30 of a–z 0–9 _ ., starts with a letter, no ".."', () => {
    expect(normalizeUsername('  Aziz.K ')).toBe('aziz.k');
    for (const ok of ['abc', 'aziz.k', 'a_1', 'a'.repeat(30)]) expect(usernameValid(ok)).toBe(true);
    for (const bad of ['ab', '1abc', '_abc', 'a..b', 'a b', 'aziz-k', 'a'.repeat(31), 'Aziz']) expect(usernameValid(bad)).toBe(false);
  });
});
