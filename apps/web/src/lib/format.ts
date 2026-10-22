/** Money is integer tiyin (100 tiyin = 1 so'm); never floats. */
export function formatMoney(minor: number, currency: string): string {
  const whole = Math.trunc(minor / 100);
  const frac = Math.abs(minor % 100);
  const grouped = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const amount = frac ? `${grouped}.${String(frac).padStart(2, '0')}` : grouped;
  return `${amount} ${currency === 'UZS' ? 'so‘m' : currency}`;
}

/** Parse a user-typed amount in whole so'm into tiyin without floating point. */
export function toMinor(input: string): number | null {
  const clean = input.replace(/\s/g, '').replace(',', '.');
  const m = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(clean);
  if (!m) return null;
  return Number(m[1]) * 100 + Number((m[2] ?? '').padEnd(2, '0') || 0);
}

const dtf = new Intl.DateTimeFormat('uz-UZ', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Asia/Tashkent',
});
export function formatInstant(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : `${dtf.format(d)}`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function initial(name: string): string {
  return (name.trim()[0] ?? '·').toUpperCase();
}

/** +998901234567 -> +998 90 123 45 67 (display only). */
export function prettyPhone(phone: string): string {
  const m = /^\+?998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(phone.replace(/\s/g, ''));
  return m ? `+998 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : phone;
}
