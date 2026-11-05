import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant } from '../lib/format';
import { useResource } from '../lib/useResource';
import { Dialog, ErrorState, Loading, useToast } from '../ui/feedback';

type State = Schemas['DeletionState'];

/** In-app account deletion (owner decision 2026-10-23): personal data erased within 30 days, cancellable meanwhile. */
export function DeleteAccount() {
  const res = useResource((signal) => api.get<State>('/account/deletion', { signal }), []);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const location = useLocation();
  const ref = useRef<HTMLElement>(null);
  const loaded = res.data !== undefined;
  useEffect(() => {
    // Settings links here as /account#delete; the router does not scroll to hashes by itself.
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
  return (
    <section ref={ref} id="delete" className="glass pad stack danger-zone" aria-labelledby="del-h">
      <h2 id="del-h">{t('account.delete.title')}</h2>
      {res.loading && !res.data ? (
        <Loading rows={1} />
      ) : res.error ? (
        <ErrorState error={res.error} onRetry={res.reload} />
      ) : res.data?.pending ? (
        <>
          <p className="banner" role="status">{t('account.delete.pending', { date: formatInstant(res.data.due_at) })}</p>
          <p className="muted">{t('account.delete.pendingNote')}</p>
          <div><button className="btn" disabled={busy} onClick={() => void cancel()}>{t('account.delete.cancel')}</button></div>
        </>
      ) : (
        <>
          <p className="muted">{t('account.delete.body', { days })}</p>
          <p className="hint">{t('account.delete.openBookings')} <Link to="/privacy">{t('legal.privacy')}</Link></p>
          <div><button className="btn danger" onClick={() => { setUnderstood(false); setErr(undefined); setOpen(true); }}>{t('account.delete.button')}</button></div>
        </>
      )}
      <Dialog open={open} title={t('account.delete.confirmTitle')} onClose={() => !busy && setOpen(false)}>
        <div className="stack">
          <p>{t('account.delete.body', { days })}</p>
          <p className="muted">{t('account.delete.pendingNote')}</p>
          <label className="consent">
            <input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} />
            <span>{t('account.delete.confirmCheck')}</span>
          </label>
          {err && <p className="err" role="alert">{err}</p>}
          <div className="row">
            <button className="btn danger" disabled={!understood || busy} onClick={() => void request()}>{busy && <span className="spinner" aria-hidden="true" />}{t('account.delete.confirm')}</button>
            <button className="btn ghost" disabled={busy} onClick={() => setOpen(false)}>{t('common.cancel')}</button>
          </div>
        </div>
      </Dialog>
    </section>
  );
}
