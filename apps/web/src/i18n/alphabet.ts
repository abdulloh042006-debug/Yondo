// Pure helpers (no React, no DOM): also imported by vite.config.ts for the static opening screen.
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
