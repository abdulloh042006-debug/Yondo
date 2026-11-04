// Money is integer minor units (UZS has 2 minor digits). Never use floats for amounts.

export function formatMoney(minor: number | null | undefined, currency = 'UZS'): string {
  if (minor === null || minor === undefined) return '—';
  const whole = Math.floor(Math.abs(minor) / 100);
  const fraction = Math.abs(minor) % 100;
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return `${minor < 0 ? '-' : ''}${grouped}${fraction ? `.${fraction.toString().padStart(2, '0')}` : ''} ${currency === 'UZS' ? "so'm" : currency}`;
}

const TZ = 'Asia/Tashkent';

function parts(value: string | Date, timeZone = TZ) {
  const date = typeof value === 'string' ? new Date(value) : value;
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  });
  const out: Record<string, string> = {};
  for (const part of fmt.formatToParts(date)) out[part.type] = part.value;
  return out;
}

export function formatDateTime(value: string | null | undefined, timeZone = TZ): string {
  if (!value) return '—';
  const p = parts(value, timeZone);
  return `${p.day}.${p.month}.${p.year} ${p.hour}:${p.minute}`;
}

export function formatTime(value: string, timeZone = TZ): string {
  const p = parts(value, timeZone);
  return `${p.hour}:${p.minute}`;
}

const WEEKDAYS = ['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'];

export function formatDay(value: string | Date, timeZone = TZ): string {
  const p = parts(value, timeZone);
  const weekday = new Date(`${p.year}-${p.month}-${p.day}T12:00:00Z`).getUTCDay();
  return `${WEEKDAYS[weekday]}, ${p.day}.${p.month}`;
}

export function dayKey(value: string | Date, timeZone = TZ): string {
  const p = parts(value, timeZone);
  return `${p.year}-${p.month}-${p.day}`;
}

export const SERVICE_NAMES: Record<string, string> = {
  coffee: 'Coffee Companion',
  walking: 'Walking Companion',
  cinema: 'Cinema Companion',
  shopping: 'Shopping Companion',
  event: 'Event Companion',
  city_friend: 'City Friend',
  conversation: 'Conversation Companion',
  study_coworking: 'Study/Coworking',
};

export const CATEGORY_NAMES: Record<string, string> = {
  flowers: 'Gullar',
  chocolate: 'Shokolad',
  gift_box: "Sovg'a qutisi",
  toys: "O'yinchoqlar",
  birthday: "Tug'ilgan kun",
  romantic: 'Romantik',
  custom: 'Maxsus',
};

export const STATUS_NAMES: Record<string, string> = {
  pending: 'Kutilmoqda',
  accepted: "To'lov kutilmoqda",
  confirmed: 'Tasdiqlangan',
  active: 'Davom etmoqda',
  completed: 'Yakunlangan',
  cancelled: 'Bekor qilingan',
  no_show: 'Kelmagan',
  disputed: 'Nizoli',
  new: 'Yangi',
  preparing: 'Tayyorlanmoqda',
  courier_assigned: 'Kuryer tayinlandi',
  delivering: "Yo'lda",
  delivered: 'Yetkazildi',
  pending_payment: "To'lov kutilmoqda",
};

/** Combine a Tashkent-local date key and HH:MM into an ISO instant (Tashkent is UTC+5, no DST). */
export function tashkentInstant(day: string, time: string): string {
  return new Date(`${day}T${time}:00+05:00`).toISOString();
}
