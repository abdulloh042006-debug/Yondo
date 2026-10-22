export const SERVICE_LABELS: Record<string, string> = {
  coffee: 'Kofe',
  walking: 'Sayr',
  cinema: 'Kino',
  shopping: 'Shopping',
  event: 'Tadbir',
  city_friend: 'Shahar do‘sti',
  conversation: 'Suhbat',
  study: 'O‘qish / Coworking',
  online_call: 'Onlayn suhbat',
  custom_experience: 'Maxsus tajriba',
};
export const serviceLabel = (code: string): string => SERVICE_LABELS[code] ?? code.replace(/_/g, ' ');

export const APPLICATION_STATUS: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | '' }> = {
  draft: { label: 'Qoralama', tone: '' },
  submitted: { label: 'Ko‘rib chiqilmoqda', tone: 'warn' },
  approved: { label: 'Tasdiqlangan', tone: 'ok' },
  rejected: { label: 'Rad etilgan', tone: 'bad' },
  withdrawn: { label: 'Qaytarib olingan', tone: '' },
};
export const CONTENT_STATUS: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | '' }> = {
  draft: { label: 'Qoralama', tone: '' },
  pending: { label: 'Ko‘rib chiqilmoqda', tone: 'warn' },
  approved: { label: 'Tasdiqlangan', tone: 'ok' },
  rejected: { label: 'Rad etilgan', tone: 'bad' },
};
export const ACCOUNT_STATUS: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | '' }> = {
  active: { label: 'Faol', tone: 'ok' },
  verification_pending: { label: 'Tasdiq kutilmoqda', tone: 'warn' },
  restricted: { label: 'Cheklangan', tone: 'warn' },
  suspended: { label: 'To‘xtatilgan', tone: 'bad' },
  banned: { label: 'Bloklangan', tone: 'bad' },
};
export const BOOKING_STATUS: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | '' }> = {
  pending: { label: 'Javob kutilmoqda', tone: 'warn' },
  accepted: { label: 'Qabul qilingan', tone: 'ok' },
  confirmed: { label: 'Tasdiqlangan', tone: 'ok' },
  active: { label: 'Davom etmoqda', tone: 'ok' },
  completed: { label: 'Yakunlangan', tone: 'ok' },
  cancelled: { label: 'Bekor qilingan', tone: 'bad' },
  'no-show': { label: 'Kelmagan', tone: 'bad' },
  disputed: { label: 'Nizoli', tone: 'bad' },
};
export const IDENTITY_STATUS: Record<string, string> = {
  verified: 'Shaxs tasdiqlangan',
  pending: 'Shaxs tekshirilmoqda',
  rejected: 'Shaxs tasdiqlanmadi',
  unknown: 'Shaxs tekshiruvi hali ulanmagan',
};
export const BLOCKERS: Record<string, string> = {
  application_not_approved: 'Ariza hali tasdiqlanmagan',
  content_not_approved: 'Profil kontenti tasdiqlanmagan',
  account_not_active: 'Hisob hali faollashtirilmagan (administrator tasdiqi kerak)',
  companion_role_required: 'Hamroh roli tanlanmagan',
  identity_not_verified: 'Shaxs tasdiqi hali mavjud emas',
};
export const REPORT_CATEGORY: Record<string, string> = {
  harassment: 'Bezovta qilish',
  inappropriate_request: 'Nomaqbul so‘rov',
  fake_profile: 'Soxta profil',
  fraud: 'Firibgarlik',
  unsafe_behavior: 'Xavfli xatti-harakat',
  no_show: 'Kelmadi',
  payment_issue: 'To‘lov muammosi',
  other: 'Boshqa',
};
