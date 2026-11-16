import { useId, useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { User } from '../auth/AuthContext';
import { t } from '../i18n';
import { passwordProblem } from '../lib/credentials';
import { useToast } from '../ui/feedback';
import { Field, ShowPassword } from '../ui/form';

/**
 * Settings → Hisob: "Parolni almaştiriş" (PUT /auth/password, docs/login-password.md). The server signs out
 * every other session; this one stays. Shown only when the account has a password.
 */
export function ChangePassword({ user }: { user: User }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [repeat, setRepeat] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errs, setErrs] = useState<{ current?: string; next?: string; repeat?: string; form?: string }>({});
  const formId = useId();
  const showId = useId();
  if (!user.has_password) return null;

  const close = () => {
    setOpen(false);
    setCurrent('');
    setNext('');
    setRepeat('');
    setErrs({});
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(next, user.phone_number);
    const found: typeof errs = {};
    if (!current) found.current = t('pw.currentWrong');
    if (problem) found.next = t(problem);
    else if (next !== repeat) found.repeat = t('pw.mismatch');
    setErrs(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      await api.put('/auth/password', { current_password: current, new_password: next });
      toast.push('ok', t('pwchange.done'));
      close();
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'network_error');
      if (apiErr.code === 'invalid_credentials') setErrs({ current: t('pw.currentWrong') });
      else if (apiErr.code === 'weak_password') setErrs({ next: apiErr.message });
      else setErrs({ form: apiErr.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      {user.username && <p className="muted">{t('pwchange.username', { name: user.username })}</p>}
      {!open ? (
        <button className="btn ghost" style={{ width: 'fit-content' }} aria-expanded={false} aria-controls={formId} onClick={() => setOpen(true)}>
          {t('pwchange.title')}
        </button>
      ) : (
        <form id={formId} className="stack" onSubmit={submit} noValidate aria-label={t('pwchange.title')}>
          <h3 style={{ margin: 0 }}>{t('pwchange.title')}</h3>
          <p className="hint">{t('pwchange.note')}</p>
          {/* Lets a password manager tie the new password to the right account. */}
          <input type="text" name="username" autoComplete="username" value={user.username ?? user.phone_number} readOnly hidden />
          <Field label={t('pw.current')} type={show ? 'text' : 'password'} autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} error={errs.current} autoFocus />
          <Field label={t('pw.new')} type={show ? 'text' : 'password'} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} hint={t('pw.rules')} error={errs.next} />
          <Field label={t('pw.repeat')} type={show ? 'text' : 'password'} autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} error={errs.repeat} />
          <ShowPassword id={showId} checked={show} onChange={setShow} />
          {errs.form && <p className="err" role="alert">{errs.form}</p>}
          <div className="row">
            <button className="btn" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              {t('pwchange.submit')}
            </button>
            <button type="button" className="btn ghost" disabled={busy} onClick={close}>{t('common.cancel')}</button>
          </div>
        </form>
      )}
    </div>
  );
}
