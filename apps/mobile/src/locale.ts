import { applyLocaleTag, getLocaleTag, onLocaleChange } from './shared';
import { getItem, setItem } from './storage';

/**
 * Phones have no localStorage, so the shared i18n store would forget the language on every start.
 * The locale tag (uz-Latn-1995 / uz-Latn-2026 / ru / en) is kept in the app's store instead.
 * No device-language guessing: Uzbek stays the default, as on the web.
 */
const KEY = 'yondo.locale';

export async function restoreLocale(): Promise<void> {
  const saved = await getItem(KEY, 'pref');
  if (saved) await applyLocaleTag(saved).catch(() => {});
  onLocaleChange(() => void setItem(KEY, getLocaleTag(), 'pref'));
}
