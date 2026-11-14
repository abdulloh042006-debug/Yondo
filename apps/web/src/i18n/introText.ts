import { NEW_ALPHABET_FROM, toUz1995 } from './alphabet';
import { en } from './en';
import { ru } from './ru';
import { uz } from './uz';

/**
 * The two texts the static opening screen (index.html) may need before the app's code has loaded: "no connection"
 * and "try again". They come from the dictionaries, so index.html holds no copy of its own: vite.config.ts writes
 * this object into the page at build time. `from` is the day the 2026 Uzbek alphabet becomes the default.
 */
export function introFallbackText() {
  const pick = (d: Record<'err.network_error' | 'common.retry', string>, map: (s: string) => string = (s) => s) => ({
    m: map(d['err.network_error']),
    r: map(d['common.retry']),
  });
  return { from: NEW_ALPHABET_FROM, uz26: pick(uz), uz95: pick(uz, toUz1995), ru: pick(ru), en: pick(en) };
}
