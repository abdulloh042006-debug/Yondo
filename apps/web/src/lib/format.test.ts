import { describe, expect, it } from 'vitest';
import { formatMoney, prettyPhone, toMinor } from './format';

describe('money is integer tiyin', () => {
  it('formats whole so‘m with grouping', () => {
    expect(formatMoney(15000000, 'UZS')).toBe('150 000 so‘m');
    expect(formatMoney(0, 'UZS')).toBe('0 so‘m');
  });
  it('shows tiyin only when present', () => {
    expect(formatMoney(150050, 'UZS')).toBe('1 500.50 so‘m');
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
  it('prettifies Uzbek phones for display only', () => {
    expect(prettyPhone('+998901110003')).toBe('+998 90 111 00 03');
    expect(prettyPhone('123')).toBe('123');
  });
});
