import { describe, expect, it } from 'vitest';
import { dedupePhonePrefix, formatInstant, formatMoney, prettyPhone, toMinor } from './format';

describe('money is integer tiyin', () => {
  it('formats Uzbek dates by hand in Tashkent time (browsers lack Uzbek month names)', () => {
    expect(formatInstant('2026-10-23T00:51:00Z')).toBe('23-oktyabr 2026, 05:51');
    expect(formatInstant('2026-12-31T19:00:00Z')).toBe('1-yanvar 2027, 00:00');
  });
  it('formats whole söm with grouping', () => {
    expect(formatMoney(15000000, 'UZS')).toBe('150 000 söm');
    expect(formatMoney(0, 'UZS')).toBe('0 söm');
  });
  it('shows tiyin only when present', () => {
    expect(formatMoney(150050, 'UZS')).toBe('1 500.50 söm');
  });
  it('parses user input without floating point', () => {
    expect(toMinor('150 000')).toBe(15000000);
    expect(toMinor('1,5')).toBe(150);
    expect(toMinor('0.1')).toBe(10);
    expect(toMinor('0.07')).toBe(7);
    expect(toMinor('abc')).toBeNull();
    expect(toMinor('-5')).toBeNull();
    expect(toMinor('1.234')).toBeNull();
  });
  it('drops the doubled +998 prefix of a pasted number but keeps numbers that merely contain 998', () => {
    expect(dedupePhonePrefix('+998+998901110003')).toBe('+998901110003');
    expect(dedupePhonePrefix('+998998901110003')).toBe('+998901110003');
    expect(dedupePhonePrefix(' +998 90 111 00 03 ')).toBe('+998 90 111 00 03');
    expect(dedupePhonePrefix('+998998123456')).toBe('+998998123456');
  });
  it('prettifies Uzbek phones for display only', () => {
    expect(prettyPhone('+998901110003')).toBe('+998 90 111 00 03');
    expect(prettyPhone('123')).toBe('123');
  });
});
