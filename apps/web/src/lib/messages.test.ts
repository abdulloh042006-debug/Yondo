import { describe, expect, it } from 'vitest';
import { hasMessage, messageFor } from './messages';

describe('error messages are chosen by code, not by server text', () => {
  it('maps known codes to Uzbek', () => {
    expect(messageFor('invalid_otp', 422)).toMatch(/Kod notöğri/);
    expect(messageFor('stale_companion_revision', 409)).toMatch(/özgargan/);
    expect(hasMessage('self_approval_forbidden')).toBe(true);
  });
  it('falls back by status and keeps 503 distinct from refusals', () => {
    expect(messageFor('something_new', 503)).toMatch(/mavjud emas/);
    expect(messageFor(undefined, 403)).toMatch(/ruxsat/);
    expect(messageFor('x', 500)).toMatch(/Serverda xatolik/);
  });
});
