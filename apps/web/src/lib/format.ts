import { getLocale, getLang, t } from '../i18n';

/** Money is integer tiyin (100 tiyin = 1 so'm); never floats. */
export function formatMoney(minor: number, currency: string): string {
  const whole = Math.trunc(minor / 100);
  const frac = Math.abs(minor % 100);
  const grouped = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const sep = getLang() === 'ru' ? ',' : '.';
  const amount = frac ? `${grouped}${sep}${String(frac).padStart(2, '0')}` : grouped;
  return `${amount} ${currency === 'UZS' ? t('currency.UZS') : currency}`;
}

/** Parse a user-typed amount in whole so'm into tiyin without floating point. */
export function toMinor(input: string): number | null {
  const clean = input.replace(/\s/g, '').replace(',', '.');
  const m = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(clean);
  if (!m) return null;
  return Number(m[1]) * 100 + Number((m[2] ?? '').padEnd(2, '0') || 0);
}

const dtfCache = new Map<string, Intl.DateTimeFormat>();
/** Date formatter for the current UI language; times are always shown in Tashkent time. */
function dtf(locale: string, month: 'short' | 'numeric'): Intl.DateTimeFormat {
  const id = `${locale}|${month}`;
  let f = dtfCache.get(id);
  if (!f) {
    f = new Intl.DateTimeFormat(locale, { day: 'numeric', month, year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'Asia/Tashkent' });
    dtfCache.set(id, f);
  }
  return f;
}
/** Browsers ship little Uzbek CLDR data (Chromium prints "2026 M10 23"), so Uzbek dates are assembled here.
 *  The month names are the same in the 1995 and 2026 alphabets. */
const UZ_MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'];
export function formatInstant(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const locale = getLocale();
  if (!locale.startsWith('uz')) return dtf(locale, 'short').format(d);
  const p = Object.fromEntries(dtf('en-GB', 'numeric').formatToParts(d).map((x) => [x.type, x.value]));
  return `${Number(p.day)}-${UZ_MONTHS[Number(p.month) - 1]} ${p.year}, ${p.hour}:${p.minute}`;
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
