import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant } from '../lib/format';
import { useResource } from '../lib/useResource';
import { Dialog, ErrorState, Loading, useToast } from '../ui/feedback';

type State = Schemas['DeletionState'];

/** In-app account deletion (owner decision 2026-10-23): personal data erased within 30 days, cancellable meanwhile. */
/** `before` = the sign-out button, so both account actions sit side by side and look the same. */
export function DeleteAccount({ before }: { before?: ReactNode }) {
  const res = useResource((signal) => api.get<State>('/account/deletion', { signal }), []);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const location = useLocation();
  const ref = useRef<HTMLDivElement>(null);
  const loaded = res.data !== undefined;
  useEffect(() => {
    // Lives in Settings (/settings#delete); the router does not scroll to hashes by itself.
    if (loaded && location.hash === '#delete') ref.current?.scrollIntoView({ block: 'start' });
  }, [loaded, location.hash]);

  const request = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      res.setData(await api.post<State>('/account/deletion', { confirm: true }));
      toast.push('ok', t('account.delete.requested'));
      setOpen(false);
    } catch (error) {
      setErr(error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
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
  /* Owner, 2026-11-15: "Hisobni o'chirish" looks exactly like "Chiqish" (no red block); the question and the
     explanation live in a confirmation dialog over a blurred backdrop (Dialog: aria-modal, focus trap, Esc). */
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
        <div className="row">
          {before}
          <button className="btn ghost" onClick={() => { setUnderstood(false); setErr(undefined); setOpen(true); }}>{t('account.delete.title')}</button>
        </div>
      )}
      <Dialog open={open} title={t('account.delete.ask')} onClose={() => !busy && setOpen(false)}>
        <div className="stack">
          <p>{t('account.delete.body', { days })}</p>
          <p className="muted">{t('account.delete.pendingNote')}</p>
          <p className="hint">{t('account.delete.openBookings')} <Link to="/privacy">{t('legal.privacy')}</Link></p>
          <label className="consent">
            <input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} />
            <span>{t('account.delete.confirmCheck')}</span>
          </label>
          {err && <p className="err" role="alert">{err}</p>}
          <div className="row">
            <button className="btn" disabled={!understood || busy} onClick={() => void request()}>{busy && <span className="spinner" aria-hidden="true" />}{t('account.delete.yes')}</button>
            <button className="btn ghost" disabled={busy} onClick={() => setOpen(false)}>{t('account.delete.no')}</button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
