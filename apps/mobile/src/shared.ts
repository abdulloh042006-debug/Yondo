/**
 * One source of truth with the web client: the uz/ru/en dictionaries (uz in the 2026 alphabet, 1995 derived),
 * formatting (money in integer tiyin, Tashkent time), error texts chosen by backend error `code`, labels and
 * the legal document versions are imported from apps/web/src, never copied. metro.config.js makes them
 * resolve React from this app.
 */
export {
  LANGS,
  UZ_ALPHABETS,
  applyLocaleTag,
  getLang,
  getLocaleTag,
  getUzAlphabet,
  hasKey,
  onLocaleChange,
  setLang,
  setUzAlphabet,
  t,
  useLang,
  type Key,
  type Lang,
  type UzAlphabet,
} from '../../web/src/i18n';
export { dedupePhonePrefix, formatInstant, formatMoney, initial, prettyPhone } from '../../web/src/lib/format';
export { messageFor } from '../../web/src/lib/messages';
export { BOOKING_STATUS, REPORT_CATEGORY, roleLabel, serviceLabel } from '../../web/src/lib/labels';
export { LEGAL_VERSIONS, type LegalDoc } from '../../web/src/legal/versions';
import type { components } from '../../web/src/api/schema';

export type Schemas = components['schemas'];
