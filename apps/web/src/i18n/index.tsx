import { Fragment, useSyncExternalStore, type ReactNode } from 'react';
import { uz, type Key } from './uz';

export type { Key };
export type Lang = 'uz' | 'ru' | 'en';
type Params = Record<string, string | number>;

/** `locale` feeds Intl (dates, plurals); `label` is always written in the language itself. */
export const LANGS: ReadonlyArray<{ id: Lang; label: string; short: string; locale: string }> = [
  { id: 'uz', label: 'O‘zbekcha', short: 'UZ', locale: 'uz-UZ' },
  { id: 'ru', label: 'Русский', short: 'RU', locale: 'ru-RU' },
  { id: 'en', label: 'English', short: 'EN', locale: 'en-GB' },
];

/** Uzbek is bundled; Russian and English are separate chunks, fetched only when that language is chosen. */
const DICTS: Partial<Record<Lang, Record<Key, string>>> = { uz };
const LOADERS: Record<Exclude<Lang, 'uz'>, () => Promise<Record<Key, string>>> = {
  ru: () => import('./ru').then((m) => m.ru),
  en: () => import('./en').then((m) => m.en),
};

async function load(lang: Lang) {
  if (!DICTS[lang] && lang !== 'uz') DICTS[lang] = await LOADERS[lang]();
}
const STORAGE_KEY = 'yondo.lang';

function saved(): Lang {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (LANGS.some((l) => l.id === value)) return value as Lang;
  } catch {
    /* storage may be unavailable */
  }
  // Uzbek is the product language; we deliberately do not guess from the browser.
  return 'uz';
}

let current: Lang = saved();
const listeners = new Set<() => void>();

export const getLang = (): Lang => current;
/** True when `key` is a known translation key (lets callers build keys from backend codes safely). */
export const hasKey = (key: string): key is Key => key in uz;
export const getLocale = (): string => LANGS.find((l) => l.id === current)!.locale;

/** Keep <html lang>, the tab title and the meta description in step with the UI language. */
function syncDocument() {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = current;
  document.title = t('app.title');
  document.querySelector('meta[name="description"]')?.setAttribute('content', t('app.description'));
}

/** Applied once at start-up (main.tsx), before the first render. Falls back to Uzbek if the chunk cannot be fetched. */
export async function applySavedLang() {
  current = saved();
  try {
    await load(current);
  } catch {
    current = 'uz';
  }
  syncDocument();
}

/** Resolves once the new language is active. Rejects (and keeps the old language) if its chunk cannot be fetched. */
export async function setLang(next: Lang) {
  if (next === current) return;
  await load(next);
  current = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    /* ignore */
  }
  syncDocument();
  listeners.forEach((l) => l());
}

const PLURAL = /\{(\w+), plural,((?:\s*\w+ \{[^{}]*\})+)\s*\}/g;
const FORM = /(\w+) \{([^{}]*)\}/g;

/**
 * Translate `key` into the current language.
 *  - `{name}` is replaced by params.name
 *  - `{count, plural, one {# xizmat} few {# услуги} other {# xizmat}}` picks a CLDR plural form
 *    for the current locale (`#` = the number)
 */
export function t(key: Key, params?: Params): string {
  const raw = DICTS[current]?.[key] ?? uz[key] ?? key;
  if (!params) return raw;
  const plural = raw.replace(PLURAL, (_m, name: string, body: string) => {
    const n = Number(params[name] ?? 0);
    const forms: Record<string, string> = {};
    for (const m of body.matchAll(FORM)) forms[m[1]] = m[2];
    const rule = new Intl.PluralRules(getLocale()).select(n);
    return (forms[rule] ?? forms.other ?? '').replace(/#/g, String(n));
  });
  return plural.replace(/\{(\w+)\}/g, (m, name: string) => (name in params ? String(params[name]) : m));
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
/** Re-renders the caller when the language changes. */
export const useLang = (): Lang => useSyncExternalStore(subscribe, getLang, getLang);

/**
 * Remounts everything below it when the language changes, so every string (including those produced by
 * plain helper functions such as `serviceLabel`) is re-evaluated. Place it inside the providers that must
 * keep their state (router, session, toasts).
 */
export function LanguageBoundary({ children }: { children: ReactNode }) {
  const lang = useLang();
  return <Fragment key={lang}>{children}</Fragment>;
}
