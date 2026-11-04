// Formatting helpers. Money is always integer minor units; never use floats for amounts.

const DIGITS: Record<string, number> = { UZS: 2, USD: 2, EUR: 2 };

export function formatMoney(minor: number | null | undefined, currency = 'UZS'): string {
  if (minor === null || minor === undefined) return '—';
  const digits = DIGITS[currency] ?? 2;
  const negative = minor < 0;
  const abs = Math.abs(minor);
  const divisor = 10 ** digits;
  const whole = Math.floor(abs / divisor);
  const fraction = abs % divisor;
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const text = fraction ? `${grouped}.${fraction.toString().padStart(digits, '0')}` : grouped;
  return `${negative ? '-' : ''}${text} ${currency}`;
}

/** Parse a user-entered major-unit amount ("150 000.50") into integer minor units. */
export function parseMoney(input: string, currency = 'UZS'): number | null {
  const digits = DIGITS[currency] ?? 2;
  const clean = input.replace(/\s/g, '').replace(',', '.');
  if (!/^\d+(\.\d+)?$/.test(clean)) return null;
  const [whole, fraction = ''] = clean.split('.');
  if (fraction.length > digits) return null;
  return Number(whole) * 10 ** digits + Number(fraction.padEnd(digits, '0') || '0');
}

export function formatDate(value: string | null | undefined, timeZone = 'Asia/Tashkent'): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat('uz-UZ', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone,
  }).format(new Date(value));
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}
