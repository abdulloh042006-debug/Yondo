import { useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { acceptLegal } from '../legal/consent';
import { useResource } from '../lib/useResource';

/** Explicit, unticked-by-default consent box with links to both documents. */
export function ConsentCheck({ checked, onChange, error }: { checked: boolean; onChange: (v: boolean) => void; error?: string }) {
  return (
    <div className="stack" style={{ gap: 6 }}>
      <label className="consent">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-invalid={!!error} />
        <span>{t('legal.agree')}</span>
      </label>
      <p className="hint consent-links">
        <Link to="/terms" target="_blank" rel="noopener">{t('legal.terms')}</Link>
        <Link to="/privacy" target="_blank" rel="noopener">{t('legal.privacy')}</Link>
      </p>
      {error && <p className="err" role="alert">{error}</p>}
    </div>
  );
}

/**
 * Signed-in users must have accepted the current versions before using the app (e.g. after a document
 * update). The documents themselves stay readable. `overlay` is rendered next to the page, but never while consent
 * is still being checked or required.
 */
export function ConsentGate({ children, overlay }: { children: ReactNode; overlay?: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const res = useResource(
    (signal) => (user ? api.get<Schemas['ConsentState']>('/account/consents', { signal }) : Promise.resolve(null)),
    [user?.id],
  );
  const [agree, setAgree] = useState(false);
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const required = res.data?.required ?? [];
  if (!user || required.length === 0 || ['/terms', '/privacy'].includes(location.pathname)) {
    // `overlay` (the first-run guide) comes only once the consent question is settled: legal first, then the guide.
    return <>{children}{!res.loading && required.length === 0 ? overlay : null}</>;
  }

  const accept = async () => {
    setTouched(true);
    if (!agree) return;
    setBusy(true);
    setErr(undefined);
    try {
      await acceptLegal(required.map((r) => r.document));
      res.reload();
    } catch (error) {
      setErr(error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass pad stack" style={{ maxWidth: 560, margin: '0 auto' }} aria-labelledby="consent-h">
      <h1 id="consent-h">{t('legal.gate.title')}</h1>
      <p className="muted">{t('legal.gate.body')}</p>
      <ConsentCheck checked={agree} onChange={setAgree} error={touched && !agree ? t('legal.agreeRequired') : err} />
      <div className="row">
        <button className="btn" disabled={busy} onClick={() => void accept()}>{busy && <span className="spinner" aria-hidden="true" />}{t('legal.gate.accept')}</button>
        <button className="btn ghost" onClick={() => void logout()}>{t('account.logout')}</button>
      </div>
    </section>
  );
}
