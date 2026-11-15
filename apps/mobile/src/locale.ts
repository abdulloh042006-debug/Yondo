import { applyLocaleTag, applySavedLang, getLocaleTag, onLocaleChange } from './shared';
import { getItem, setItem } from './storage';

/**
 * Phones have no localStorage, so the shared i18n store would forget the language on every start.
 * The locale tag (uz-Latn-1995 / uz-Latn-2026 / ru / en) is kept in the app's store instead.
 * No device-language guessing: Uzbek stays the default, as on the web.
 */
const KEY = 'yondo.locale';

export async function restoreLocale(): Promise<void> {
  // The shared i18n module starts from the web build's localStorage choice without loading its dictionary:
  // load it first, or a reload of the web build shows Uzbek while thinking it is already English/Russian.
  await applySavedLang();
  const saved = await getItem(KEY, 'pref');
  if (saved) await applyLocaleTag(saved).catch(() => {});
  onLocaleChange(() => void setItem(KEY, getLocaleTag(), 'pref'));
}
