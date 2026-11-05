import { t, type Key } from '../i18n';

/** `{ A: 'text' }`-style lookup whose values are translated lazily, in the current UI language. */
function lazyMap(prefix: string, codes: readonly string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const code of codes) Object.defineProperty(out, code, { enumerable: true, get: () => t(`${prefix}.${code}` as Key) });
  return out;
}
type Tone = 'ok' | 'warn' | 'bad' | '';
function statusMap(prefix: string, tones: Record<string, Tone>): Record<string, { label: string; tone: Tone }> {
  const out: Record<string, { label: string; tone: Tone }> = {};
  for (const [code, tone] of Object.entries(tones)) {
    Object.defineProperty(out, code, { enumerable: true, value: { get label() { return t(`${prefix}.${code}` as Key); }, tone } });
  }
  return out;
}

export const SERVICE_LABELS = lazyMap('service', [
  'coffee', 'walking', 'cinema', 'shopping', 'event', 'city_friend', 'conversation', 'study', 'online_call', 'custom_experience',
]);
export const serviceLabel = (code: string): string => SERVICE_LABELS[code] ?? code.replace(/_/g, ' ');

export const APPLICATION_STATUS = statusMap('status.application', { draft: '', submitted: 'warn', approved: 'ok', rejected: 'bad', withdrawn: '' });
export const CONTENT_STATUS = statusMap('status.content', { draft: '', pending: 'warn', approved: 'ok', rejected: 'bad' });
export const ACCOUNT_STATUS = statusMap('status.account', { active: 'ok', verification_pending: 'warn', restricted: 'warn', suspended: 'bad', banned: 'bad', deleted: '' });
export const BOOKING_STATUS = statusMap('status.booking', {
  pending: 'warn', accepted: 'ok', confirmed: 'ok', active: 'ok', completed: 'ok', cancelled: 'bad', 'no-show': 'bad', disputed: 'bad', expired: '',
});
export const IDENTITY_STATUS = lazyMap('status.identity', ['verified', 'pending', 'rejected', 'unknown']);
export const BLOCKERS = lazyMap('blocker', ['application_not_approved', 'content_not_approved', 'account_not_active', 'companion_role_required', 'identity_not_verified']);
export const REPORT_CATEGORY = lazyMap('report', ['harassment', 'inappropriate_request', 'fake_profile', 'fraud', 'unsafe_behavior', 'no_show', 'payment_issue', 'other']);
export const SUPPORT_STATUS = statusMap('help.support.status', { open: 'warn', answered: 'ok', closed: '' });
export const DELETION_STATUS = statusMap('deletion.status', { pending: 'warn', cancelled: '', completed: 'ok' });
/** Status of a report as its author sees it (`SafetyReport.status`: open → in_review). */
export const REPORT_STATUS = statusMap('help.status', { open: 'warn', in_review: 'ok' });
/** Role code → label; unknown codes fall back to the code itself. */
export const roleLabel = (code: string): string => (['customer', 'companion', 'admin'].includes(code) ? t(`role.${code}` as Key) : code);
