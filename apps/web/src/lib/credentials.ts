import type { Key } from '../i18n';

/**
 * Client-side mirror of the server's password and username rules (docs/login-password.md). The server
 * stays the authority (weak_password / invalid_username); these only give the answer before a round trip.
 * Pure TypeScript: the mobile app imports it through src/shared.ts.
 */
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

const digits = (s: string) => s.replace(/\D/g, '');

/** The first problem with a new password, or null. `phone` is the account's number (E.164). */
export function passwordProblem(password: string, phone?: string | null): Key | null {
  if (password.length < PASSWORD_MIN) return 'pw.tooShort';
  if (password.length > PASSWORD_MAX) return 'pw.tooLong';
  if (phone && /^[\d\s+()-]+$/.test(password)) {
    const p = digits(phone);
    const d = digits(password);
    if (d === p || (p.length > 9 && d === p.slice(-9)) || d === `0${p.slice(-9)}`) return 'pw.isPhone';
  }
  return null;
}

/** Usernames are stored in lower case; spaces around are ignored. */
export const normalizeUsername = (s: string) => s.trim().toLowerCase();

/** 3–30 characters of a–z 0–9 _ ., starts with a letter, no "..". Reserved names are left to the server. */
export function usernameValid(name: string): boolean {
  return /^[a-z][a-z0-9_.]{2,29}$/.test(name) && !name.includes('..');
}
