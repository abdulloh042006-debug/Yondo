/** Uzbek (Latin) messages keyed by the backend's stable error `code`. Never match message text. */
const BY_CODE: Record<string, string> = {
  authentication_required: 'Davom etish uchun tizimga kiring.',
  invalid_access_token: 'Seans tugagan. Qaytadan kiring.',
  invalid_refresh_token: 'Seans tugagan. Qaytadan kiring.',
  invalid_phone_number: 'Telefon raqami noto‘g‘ri. Namuna: +998 90 123 45 67.',
  invalid_otp: 'Kod noto‘g‘ri. Qayta urinib ko‘ring.',
  otp_expired: 'Kod muddati tugadi. Yangi kod so‘rang.',
  otp_rate_limited: 'Juda ko‘p urinish. Birozdan keyin qayta urinib ko‘ring.',
  otp_resend_cooldown: 'Yangi kodni biroz kutib so‘rang.',
  otp_temporarily_blocked: 'Urinishlar vaqtincha cheklangan. Keyinroq qayta urinib ko‘ring.',
  otp_delivery_unavailable: 'SMS xizmati hozircha ulanmagan. Keyinroq urinib ko‘ring.',
  validation_error: 'Kiritilgan ma’lumotlarni tekshiring.',
  account_unavailable: 'Hisobingiz hozir bu amalni bajara olmaydi.',
  account_role_required: 'Bu amal uchun mos rol kerak.',
  role_required: 'Bu amal uchun mos rol kerak.',
  companion_role_required: 'Avval hamroh rolini tanlang.',
  customer_role_required: 'Bu amal faqat mijozlar uchun.',
  companion_forbidden: 'Bu amalga ruxsat yo‘q.',
  invalid_role: 'Bu rolni tanlab bo‘lmaydi.',
  duplicate_role: 'Rollar takrorlanmasligi kerak.',
  application_not_found: 'Ariza topilmadi.',
  profile_not_found: 'Profil topilmadi.',
  companion_not_found: 'Hamroh topilmadi yoki hozir ko‘rinmaydi.',
  companion_service_not_found: 'Xizmat topilmadi.',
  companion_record_conflict: 'Bu yozuv allaqachon mavjud yoki o‘zgargan.',
  invalid_companion_transition: 'Bu amal hozirgi holatda mumkin emas.',
  stale_companion_revision: 'Ma’lumot siz ochgandan keyin o‘zgargan. Yangilab, qayta ko‘rib chiqing.',
  self_approval_forbidden: 'O‘z arizangizni o‘zingiz tasdiqlay olmaysiz.',
  admin_self_change_forbidden: 'O‘z hisobingiz holatini o‘zgartira olmaysiz.',
  admin_target_forbidden: 'Administrator hisoblari alohida ko‘rib chiqiladi.',
  user_not_found: 'Foydalanuvchi topilmadi.',
  invalid_discovery_filter: 'Filtr qiymatlari noto‘g‘ri.',
  invalid_service: 'Xizmat ma’lumotlari noto‘g‘ri.',
  invalid_price: 'Narx noto‘g‘ri.',
  invalid_currency: 'Valyuta noto‘g‘ri.',
  availability_overlap: 'Bu vaqt boshqa oraliq bilan kesishadi.',
  availability_reserved: 'Bu oraliqda band qilingan uchrashuv bor.',
  photo_limit: 'Rasmlar soni chegaraga yetdi.',
  photo_too_large: 'Rasm hajmi juda katta.',
  invalid_photo_type: 'Faqat JPEG yoki PNG rasm yuklash mumkin.',
  invalid_photo: 'Rasmni o‘qib bo‘lmadi.',
  storage_unavailable: 'Rasm saqlash xizmati hozir mavjud emas. Keyinroq urinib ko‘ring.',
  booking_time_unavailable: 'Tanlangan vaqt band yoki hamroh bo‘sh emas.',
  booking_start_in_past: 'Boshlanish vaqti o‘tib ketgan.',
  invalid_booking_duration: 'Davomiylik xizmat birligiga mos kelishi kerak.',
  self_booking_forbidden: 'O‘zingizga bron qila olmaysiz.',
  booking_blocked: 'Bu hamroh bilan bron qilib bo‘lmaydi.',
  booking_not_found: 'Bron topilmadi.',
  invalid_booking_transition: 'Bron holatini bu tarzda o‘zgartirib bo‘lmaydi.',
  safety_item_not_found: 'Xavfsizlik yozuvi topilmadi.',
  invalid_safety_note: 'Izoh juda qisqa (kamida 8 belgi).',
  report_not_open: 'Bu shikoyat allaqachon ko‘rib chiqilmoqda.',
  safety_review_conflict: 'Holat o‘zgargan. Yangilab, qayta urinib ko‘ring.',
  payment_provider_unavailable: 'To‘lov xizmati hozircha ulanmagan.',
  network_error: 'Aloqa yo‘q. Internetni tekshirib, qayta urinib ko‘ring.',
};

const BY_STATUS: Record<number, string> = {
  401: 'Davom etish uchun tizimga kiring.',
  403: 'Bu amalga ruxsatingiz yo‘q.',
  404: 'Topilmadi.',
  409: 'Ma’lumot o‘zgargan. Yangilab, qayta urinib ko‘ring.',
  422: 'Kiritilgan ma’lumotlarni tekshiring.',
  429: 'Juda ko‘p so‘rov. Birozdan keyin urinib ko‘ring.',
  503: 'Xizmat hozircha mavjud emas. Keyinroq urinib ko‘ring.',
};

export function messageFor(code: string | undefined, status: number): string {
  if (code && BY_CODE[code]) return BY_CODE[code];
  if (BY_STATUS[status]) return BY_STATUS[status];
  if (status >= 500) return 'Serverda xatolik. Keyinroq qayta urinib ko‘ring.';
  return 'Kutilmagan xatolik yuz berdi.';
}

export const hasMessage = (code: string): boolean => code in BY_CODE;
