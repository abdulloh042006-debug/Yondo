import { describe, expect, it } from 'vitest';
import { formatMoney, parseMoney, percent } from './format';
import { buildUrl } from './api';

describe('money', () => {
  it('formats integer minor units without floating point', () => {
    expect(formatMoney(15_000_000)).toBe('150 000 UZS');
    expect(formatMoney(123_456)).toBe('1 234.56 UZS');
    expect(formatMoney(5)).toBe('0.05 UZS');
    expect(formatMoney(null)).toBe('—');
  });

  it('parses major units into minor units', () => {
    expect(parseMoney('150 000')).toBe(15_000_000);
    expect(parseMoney('12,5')).toBe(1250);
    expect(parseMoney('0.01')).toBe(1);
    expect(parseMoney('1.234')).toBeNull();
    expect(parseMoney('abc')).toBeNull();
  });

  it('formats rates', () => {
    expect(percent(0.1234)).toBe('12.3%');
    expect(percent(null)).toBe('—');
  });
});

describe('api urls', () => {
  it('drops empty query values', () => {
    expect(buildUrl('/admin/users', { q: '', status: 'active', offset: 0 })).toBe(
      '/api/v1/admin/users?status=active&offset=0',
    );
  });
});
