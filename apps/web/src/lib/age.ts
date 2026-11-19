/** 18+ (owner, 2026-11-19). The server decides; this only gives the user a quick, clear answer. */
export const ADULT_AGE = 18;

const todayIso = (): string => new Date().toISOString().slice(0, 10);

export function ageOn(dobIso: string, todayIsoValue: string = todayIso()): number {
  const [y, m, d] = dobIso.split('-').map(Number);
  const [ty, tm, td] = todayIsoValue.split('-').map(Number);
  return ty - y - (tm < m || (tm === m && td < d) ? 1 : 0);
}

/** i18n key of the problem with a typed date of birth (YYYY-MM-DD), or null when it is fine. */
export function dobProblem(dobIso: string, todayIsoValue: string = todayIso()): 'age.invalid' | 'age.under18' | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dobIso) || Number.isNaN(Date.parse(`${dobIso}T00:00:00Z`))) return 'age.invalid';
  if (dobIso > todayIsoValue || ageOn(dobIso, todayIsoValue) > 120) return 'age.invalid';
  return ageOn(dobIso, todayIsoValue) < ADULT_AGE ? 'age.under18' : null;
}

/** The latest date of birth that is 18 today (for the date input's `max`). */
export function latestAdultDob(todayIsoValue: string = todayIso()): string {
  const [y, m, d] = todayIsoValue.split('-');
  return `${Number(y) - ADULT_AGE}-${m}-${d}`;
}
