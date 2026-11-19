import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant } from '../lib/format';
import { useResource } from '../lib/useResource';
import { ErrorState, Loading, useToast } from '../ui/feedback';
import { HoldToConfirm } from '../ui/HoldToConfirm';

type State = Schemas['DeletionState'];

/** In-app account deletion (owner decision 2026-10-23): personal data erased within 30 days, cancellable meanwhile. */
/** `before` = the sign-out button. Owner, 2026-11-18: the 1.5 s Hold-to-Confirm button replaces the blurred
 *  confirmation dialog of 2026-11-15; the consequences are shown next to it in the danger zone. */
export function DeleteAccount({ before }: { before?: ReactNode }) {
  const res = useResource((signal) => api.get<State>('/account/deletion', { signal }), []);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const location = useLocation();
  const ref = useRef<HTMLDivElement>(null);
  const loaded = res.data !== undefined;
  useEffect(() => {
    // Lives in Settings (/settings#delete); the router does not scroll to hashes by itself.
    if (loaded && location.hash === '#delete') ref.current?.scrollIntoView({ block: 'start' });
  }, [loaded, location.hash]);

  // Errors are shown by HoldToConfirm under the button (message chosen by the API error code).
  const request = async () => {
    res.setData(await api.post<State>('/account/deletion', { confirm: true }));
    toast.push('ok', t('account.delete.requested'));
  };
  const cancel = async () => {
    setBusy(true);
    try {
      await api.del('/account/deletion');
      toast.push('ok', t('account.delete.cancelled'));
      res.reload();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  const days = res.data?.window_days ?? 30;
  return (
    <div ref={ref} id="delete" className="stack" style={{ scrollMarginTop: 96 }}>
      {res.loading && !res.data ? (
        <div className="row">{before}<Loading rows={1} /></div>
      ) : res.error ? (
        <>
          <div className="row">{before}</div>
          <ErrorState error={res.error} onRetry={res.reload} />
        </>
      ) : res.data?.pending ? (
        <>
          <div className="row">
            {before}
            <button className="btn ghost" disabled={busy} onClick={() => void cancel()}>{t('account.delete.cancel')}</button>
          </div>
          <p className="banner" role="status">{t('account.delete.pending', { date: formatInstant(res.data.due_at) })}</p>
          <p className="muted">{t('account.delete.pendingNote')}</p>
        </>
      ) : (
        <>
          {before && <div className="row">{before}</div>}
          <HoldToConfirm label={t('account.delete.title')} yesLabel={t('account.delete.yes')} doneLabel={t('account.delete.requested')} onConfirm={request}>
            <h3>{t('account.delete.title')}</h3>
            <p>{t('account.delete.body', { days })}</p>
            <p className="muted">{t('account.delete.pendingNote')}</p>
            <p className="hint">{t('account.delete.openBookings')} <Link to="/privacy">{t('legal.privacy')}</Link></p>
          </HoldToConfirm>
        </>
      )}
    </div>
  );
}
