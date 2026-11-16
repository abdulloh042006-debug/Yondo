import { useEffect, useId, useState, type FormEvent, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t, type Key } from '../i18n';
import { normalizeUsername, passwordProblem, usernameValid } from '../lib/credentials';
import { introReady } from '../ui/Intro';
import { Field, ShowPassword } from '../ui/form';
import { useAuth } from './AuthContext';

/** Pages that stay open without a password: the documents and Help (SOS must never be behind a form). */
const OPEN_PATHS = ['/terms', '/privacy', '/help'];
const CHECK_DELAY_MS = 400;

type Check = { name: string; state: 'checking' | 'available' | 'taken' | 'reserved' | 'invalid' | 'unknown' };
const CHECK_TEXT: Record<Exclude<Check['state'], 'unknown'>, Key> = {
  checking: 'setup.checking',
  available: 'setup.available',
  taken: 'setup.taken',
  reserved: 'setup.reserved',
  invalid: 'setup.invalid',
};

/**
 * Owner, 2026-11-15 (docs/login-password.md): an account made with a code has no username or password yet
 * (`password_setup_required`). Right after that code sign-in the app asks for both before anything else.
 * The server accepts it only within 15 minutes of a code sign-in; later, `reauth_required` sends the user
 * back to a code sign-in. The server-side gate (YONDO_AUTH_REQUIRE_PASSWORD_SETUP) stays off: owner's call.
 */
export function PasswordSetupGate({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  const open = !user?.password_setup_required || OPEN_PATHS.includes(location.pathname);
  useEffect(() => {
    if (!open) introReady();
  }, [open]);
  if (open) return <>{children}</>;
  return <PasswordSetup />;
}

function PasswordSetup() {
  const { user, reload, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fixed = user?.username ?? null; // a username set earlier stays; only the password is missing
  const [username, setUsername] = useState(fixed ?? '');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [show, setShow] = useState(false);
  const showId = useId();
  const [remote, setRemote] = useState<Check | null>(null);
  const [errs, setErrs] = useState<{ username?: string; password?: string; repeat?: string; form?: string }>({});
  const [busy, setBusy] = useState(false);
  const name = normalizeUsername(username);

  // Live availability, debounced; the rules are checked here first so a bad name costs no request.
  const needsRemote = !fixed && !!name && usernameValid(name);
  useEffect(() => {
    if (!needsRemote) return;
    const ctl = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .get<Schemas['UsernameAvailability']>(`/auth/username/available?username=${encodeURIComponent(name)}`, { signal: ctl.signal })
        .then((r) => setRemote({ name, state: r.available ? 'available' : (r.reason ?? 'taken') }))
        .catch(() => !ctl.signal.aborted && setRemote({ name, state: 'unknown' })); // the server decides on submit
    }, CHECK_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      ctl.abort();
    };
  }, [name, needsRemote]);
  const check: Check | null =
    fixed || !name ? null : !needsRemote ? { name, state: 'invalid' } : remote?.name === name ? remote : { name, state: 'checking' };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const next: typeof errs = {};
    if (!fixed && !usernameValid(name)) next.username = t('setup.invalid');
    else if (!fixed && (check?.state === 'taken' || check?.state === 'reserved')) next.username = t(CHECK_TEXT[check.state]);
    const problem = passwordProblem(password, user?.phone_number);
    if (problem) next.password = t(problem);
    else if (password !== password2) next.repeat = t('pw.mismatch');
    setErrs(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      await api.post<Schemas['UserResponse']>('/auth/registration', { username: fixed ?? name, password });
      await reload();
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'network_error');
      if (apiErr.code === 'reauth_required') {
        await logout();
        navigate('/login', { replace: true, state: { mode: 'code', notice: t('setup.reauth'), from: location.pathname } });
        return;
      }
      if (apiErr.code === 'registration_complete') return void reload();
      if (['invalid_username', 'username_unavailable', 'username_already_set'].includes(apiErr.code)) setErrs({ username: apiErr.message });
      else if (apiErr.code === 'weak_password') setErrs({ password: apiErr.message });
      else setErrs({ form: apiErr.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass pad stack" style={{ maxWidth: 520, margin: '0 auto' }} aria-labelledby="setup-h">
      <h1 id="setup-h">{t('setup.title')}</h1>
      <p className="muted">{t('setup.lead')}</p>
      <form className="stack" onSubmit={submit} noValidate>
        <Field
          label={t('setup.username')}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          maxLength={30}
          value={username}
          readOnly={!!fixed}
          onChange={(e) => setUsername(e.target.value)}
          hint={`${t('setup.usernameRules')} ${t('setup.usernamePrivate')}`}
          error={errs.username}
          live={check && check.state !== 'unknown' && !errs.username ? t(CHECK_TEXT[check.state]) : ''}
          autoFocus={!fixed}
        />
        <Field
          label={t('pw.new')}
          type={show ? 'text' : 'password'}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={t('pw.rules')}
          error={errs.password}
        />
        <Field
          label={t('pw.repeat')}
          type={show ? 'text' : 'password'}
          autoComplete="new-password"
          value={password2}
          onChange={(e) => setPassword2(e.target.value)}
          error={errs.repeat}
        />
        <ShowPassword id={showId} checked={show} onChange={setShow} />
        {errs.form && <p className="err" role="alert">{errs.form}</p>}
        <div className="row">
          <button className="btn" disabled={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            {t('setup.submit')}
          </button>
          <button type="button" className="btn ghost" onClick={() => void logout()}>{t('account.logout')}</button>
        </div>
      </form>
    </section>
  );
}
