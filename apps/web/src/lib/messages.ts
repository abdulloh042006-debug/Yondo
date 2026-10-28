import { hasKey, t, type Key } from '../i18n';

/** Error messages are chosen by the backend's stable error `code` (never by message text), in the current UI language. */
export function messageFor(code: string | undefined, status: number): string {
  if (code && hasKey(`err.${code}`)) return t(`err.${code}` as Key);
  if (hasKey(`errStatus.${status}`)) return t(`errStatus.${status}` as Key);
  if (status >= 500) return t('errStatus.5xx');
  return t('errStatus.other');
}

export const hasMessage = (code: string): boolean => hasKey(`err.${code}`);
