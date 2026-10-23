import { useSyncExternalStore } from 'react';
import { uz, type Key } from './uz';

export type { Key };
export type Lang = 'uz' | 'ru' | 'en';
type Params = Record<string, string | number>;

/**
 * Uzbek has two Latin spellings in use: the 1995 alphabet (o‘ g‘ sh ch) and the 2026 alphabet (ö ğ ş ç; law signed
 * 2026-10-21, in force from 2027-04-22). `uz.ts` is written in the 2026 alphabet; the 1995 text is derived from it
 * (the mapping is one-to-one), so there is still a single source of truth.
 */
export type UzAlphabet = '1995' | '2026';
/** Midnight in Tashkent on the day the 2026 alphabet becomes official. */
export const NEW_ALPHABET_FROM = Date.parse('2027-04-22T00:00:00+05:00');
/** Until the law is in force we default to the alphabet people use today; afterwards to the new one. */
export const defaultUzAlphabet = (now: number = Date.now()): UzAlphabet => (now >= NEW_ALPHABET_FROM ? '2026' : '1995');

const TO_1995: Record<string, string> = { ş: 'sh', ç: 'ch', ö: 'o‘', ğ: 'g‘', Ş: 'Sh', Ç: 'Ch', Ö: 'O‘', Ğ: 'G‘', 'ʼ': '’' };
/** 2026 → 1995 spelling. `Ş`/`Ç` before another capital (all-caps words) become `SH`/`CH`. */
export function toUz1995(text: string): string {
  return text
    .replace(/[ŞÇ](?=\p{Lu})/gu, (c) => (c === 'Ş' ? 'SH' : 'CH'))
    .replace(/[şçöğŞÇÖĞʼ]/g, (c) => TO_1995[c]);
}

/** Each option is written in its own spelling, like a language name. */
export const UZ_ALPHABETS: ReadonlyArray<{ id: UzAlphabet; label: string; letters: string }> = [
  { id: '1995', label: 'O‘zbekcha', letters: 'o‘ g‘ sh ch' },
  { id: '2026', label: 'Özbekça', letters: 'ö ğ ş ç' },
];

/** `locale` feeds Intl (dates, plurals); `label` is always written in the language itself. */
export const LANGS: ReadonlyArray<{ readonly id: Lang; readonly label: string; readonly short: string; readonly locale: string }> = [
  { id: 'uz', get label() { return alphabet === '1995' ? 'O‘zbekcha' : 'Özbekça'; }, short: 'UZ', locale: 'uz-UZ' },
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
const ALPHABET_KEY = 'yondo.uzAlphabet';

function savedAlphabet(): UzAlphabet {
  try {
    const value = localStorage.getItem(ALPHABET_KEY);
    if (value === '1995' || value === '2026') return value;
  } catch {
    /* storage may be unavailable */
  }
  return defaultUzAlphabet();
}
let alphabet: UzAlphabet = savedAlphabet();
let uz1995: Record<Key, string> | undefined;
function dict(): Record<Key, string> | undefined {
  if (current !== 'uz') return DICTS[current];
  if (alphabet === '2026') return uz;
  return (uz1995 ??= Object.fromEntries(Object.entries(uz).map(([k, v]) => [k, toUz1995(v)])) as Record<Key, string>);
}

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
export const getUzAlphabet = (): UzAlphabet => alphabet;
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
  alphabet = savedAlphabet();
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

/** Locale tag shared with the server (`users.ui_locale`); the Uzbek alphabet year is a BCP 47 variant. */
export type UiLocale = 'uz-Latn-1995' | 'uz-Latn-2026' | 'ru' | 'en';
export const getLocaleTag = (): UiLocale => (current === 'uz' ? `uz-Latn-${alphabet}` : current);

/** Apply a tag saved on the server (another device). One notification, so listeners never see a half state. */
export async function applyLocaleTag(tag: string | null | undefined) {
  const m = /^uz-Latn-(1995|2026)$/.exec(tag ?? '');
  const nextLang: Lang | null = m ? 'uz' : tag === 'ru' || tag === 'en' ? tag : null;
  if (!nextLang) return;
  const nextAlphabet: UzAlphabet = m ? (m[1] as UzAlphabet) : alphabet;
  if (nextLang === current && nextAlphabet === alphabet) return;
  await load(nextLang);
  current = nextLang;
  alphabet = nextAlphabet;
  try {
    localStorage.setItem(STORAGE_KEY, current);
    localStorage.setItem(ALPHABET_KEY, alphabet);
  } catch {
    /* ignore */
  }
  syncDocument();
  listeners.forEach((l) => l());
}

/** Called after every language or alphabet change (used to save the choice to the account). */
export const onLocaleChange = (listener: () => void) => subscribe(listener);

/** Choose the Uzbek spelling (remembered on this device; it applies whenever the UI is Uzbek). */
export function setUzAlphabet(next: UzAlphabet) {
  if (next === alphabet) return;
  alphabet = next;
  try {
    localStorage.setItem(ALPHABET_KEY, next);
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
  const raw = dict()?.[key] ?? uz[key] ?? key;
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
/**
 * Re-renders the caller when the language changes. `App` calls it at the root: the router elements are then
 * rebuilt, so every page re-renders in place (no remount, hence typed text, dialogs and the OTP step survive).
 */
const snapshot = () => `${current}|${alphabet}`;
export const useLang = (): Lang => {
  useSyncExternalStore(subscribe, snapshot, snapshot); // language *or* Uzbek alphabet changed
  return current;
};
