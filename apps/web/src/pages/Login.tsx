import { motion } from 'motion/react';
import { useEffect, useId, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { clearPendingSignup, completeSignup, pendingSignup } from '../auth/social';
import { SocialSignIn } from '../auth/SocialSignIn';
import { acceptLegal } from '../legal/consent';
import { t } from '../i18n';
import { LanguageSwitch } from '../i18n/LanguageSwitch';
import { passwordProblem } from '../lib/credentials';
import { dedupePhonePrefix } from '../lib/format';
import { ConsentCheck } from '../ui/Consent';
import { Field, ShowPassword } from '../ui/form';

type CodeStep = {
  kind: 'code';
  phone: string;
  resendIn: number;
  devOtp?: string | null;
  /** Only the literal 'telegram' changes the screen; absent/null/unknown keeps the generic (and dev) layout. */
  channel: 'telegram' | null;
  validMin: number;
  /** Bumped to remount the code field, which re-runs autoFocus after a resend or an expired code. */
  focusKey: number;
  resent: boolean;
  /** The code came from the free Yondo bot (not the Gateway's «Verification Codes» chat). */
  bot?: boolean;
};
/** Linking the phone to the Yondo Telegram bot (docs/login-telegram-bot.md). */
type LinkStep = {
  kind: 'link';
  phone: string;
  deepLink: string;
  poll: string;
  state: 'waiting' | 'expired' | 'failed';
  failure?: string | null;
};
type Step = { kind: 'phone' } | CodeStep | LinkStep;
const POLL_MS = 2000;
/** A status request that hangs (a phone browser paused it while the user was in Telegram) is dropped. */
const POLL_TIMEOUT_MS = 8000;
/** Failures of the link itself; any other failure means the link is done and only the code was not sent. */
const LINK_FAILURES = new Set(['telegram_phone_mismatch', 'telegram_account_linked_elsewhere']);

const CODE_LENGTH = 6;
/**
 * Owner, 2026-11-15 (docs/login-password.md): username or phone + password is the main way in; a code via
 * Telegram stays the second way (and the sign-up path); "reset" = phone → code → new password.
 */
export type LoginMode = 'password' | 'code' | 'reset';
type LoginState = { from?: string; mode?: LoginMode; notice?: string } | null;
/** Errors about the number itself are shown under the phone field. */
const PHONE_FIELD_ERRORS = new Set(['invalid_phone_number', 'otp_channel_unavailable']);

function codeStepFor(phone: string, prev: CodeStep | null, bot: boolean): CodeStep {
  return {
    kind: 'code',
    phone,
    resendIn: 60,
    devOtp: null,
    channel: 'telegram',
    validMin: 5,
    focusKey: (prev?.focusKey ?? 0) + 1,
    resent: false,
    bot,
  };
}

export function Login() {
  const { requestCode, verify, passwordLogin, resetPassword, reload, state } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nav = location.state as LoginState;
  const from = nav?.from ?? '/';
  const [mode, setMode] = useState<LoginMode>(nav?.mode ?? 'password');
  const [notice, setNotice] = useState(nav?.notice);
  const [step, setStep] = useState<Step>({ kind: 'phone' });
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [pwErr, setPwErr] = useState<string>();
  const [repeatErr, setRepeatErr] = useState<string>();
  const showPwId = useId();
  const [phone, setPhone] = useState('+998');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [agree, setAgree] = useState(false);
  const [agreeErr, setAgreeErr] = useState(false);
  const [noTelegram, setNoTelegram] = useState(false);
  const noTelegramId = useId();
  const [botEnabled, setBotEnabled] = useState(false);
  const [botUsername, setBotUsername] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api
      .get<Schemas['LinkConfig']>('/auth/telegram/link/config', { anonymous: true })
      .then((cfg) => {
        if (!live) return;
        setBotEnabled(cfg.enabled);
        setBotUsername(cfg.enabled && cfg.bot_username ? cfg.bot_username : null);
      })
      .catch(() => undefined); // unknown = keep the existing (demo) login
    return () => {
      live = false;
    };
  }, []);

  // Poll the link status while the user is in Telegram; stop on any final state. Phone browsers pause
  // a page that is in the background, so a request may hang: each one has a timeout, and coming back
  // to the page checks at once instead of waiting for the next round.
  const waitingPoll = step.kind === 'link' && step.state === 'waiting' ? step.poll : null;
  useEffect(() => {
    if (waitingPoll === null) return;
    let done = false;
    let timer = 0;
    let current: AbortController | null = null;
    const check = async () => {
      window.clearTimeout(timer);
      current?.abort();
      const mine = new AbortController();
      current = mine;
      const limit = window.setTimeout(() => mine.abort(), POLL_TIMEOUT_MS);
      try {
        const st = await api.get<Schemas['LinkStatus']>('/auth/telegram/link/status', {
          anonymous: true,
          headers: { 'X-Yondo-Link-Poll': waitingPoll },
          signal: mine.signal,
        });
        if (done || current !== mine) return;
        if (st.status === 'otp_sent' || st.status === 'expired' || st.status === 'failed') {
          setStep((cur) => {
            if (cur.kind !== 'link' || cur.poll !== waitingPoll) return cur;
            if (st.status === 'otp_sent') return codeStepFor(cur.phone, null, true);
            if (st.status === 'expired') return { ...cur, state: 'expired' };
            return { ...cur, state: 'failed', failure: st.failure_code };
          });
          return;
        }
      } catch (err) {
        if (done || current !== mine) return;
        if (err instanceof ApiError && err.status === 404) {
          setStep((cur) => (cur.kind === 'link' && cur.poll === waitingPoll ? { ...cur, state: 'expired' } : cur));
          return;
        }
        // a timeout or a network blip: keep polling
      } finally {
        window.clearTimeout(limit);
      }
      timer = window.setTimeout(() => void check(), POLL_MS);
    };
    const wake = () => {
      if (document.visibilityState === 'visible') void check();
    };
    timer = window.setTimeout(() => void check(), POLL_MS);
    document.addEventListener('visibilitychange', wake);
    window.addEventListener('focus', wake);
    return () => {
      done = true;
      window.clearTimeout(timer);
      current?.abort();
      document.removeEventListener('visibilitychange', wake);
      window.removeEventListener('focus', wake);
    };
  }, [waitingPoll]);

  useEffect(() => {
    if (step.kind !== 'code' || step.resendIn <= 0) return;
    const t = window.setTimeout(() => setStep({ ...step, resendIn: step.resendIn - 1 }), 1000);
    return () => window.clearTimeout(t);
  }, [step]);

  if (state.status === 'authed') return <Navigate to={from} replace />;

  const startLink = async (number: string) => {
    const res = await api.post<Schemas['LinkStarted']>(
      '/auth/telegram/link/start',
      { phone_number: number },
      { anonymous: true },
    );
    if (res.already_linked) return false;
    setStep({ kind: 'link', phone: number, deepLink: res.deep_link, poll: res.poll_token, state: 'waiting' });
    return true;
  };

  const switchMode = (next: LoginMode) => {
    clearPendingSignup(); // leaving the phone step abandons a pending Telegram/Google sign-up
    setMode(next);
    setError(undefined);
    setPwErr(undefined);
    setNotice(undefined);
    setStep({ kind: 'phone' });
    setPassword('');
    setPassword2('');
  };

  const signInWithPassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(undefined);
    if (!login.trim() || !password) {
      setError(new ApiError(401, 'invalid_credentials'));
      return;
    }
    setBusy(true);
    try {
      await passwordLogin(login.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'network_error'));
      setPassword('');
    } finally {
      setBusy(false);
    }
  };

  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    // A reset is for an existing account, which consented when it was made; the consent gate covers new versions.
    if (mode !== 'reset' && !agree) {
      setAgreeErr(true);
      return;
    }
    const number = step.kind === 'phone' ? dedupePhonePrefix(phone) : step.phone;
    const digits = number.replace(/\D/g, '');
    if (digits.length < 9) {
      setError(new ApiError(422, 'invalid_phone_number'));
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      // Bot login: ask for the code first. A linked phone gets it in Telegram; a phone without a
      // verified chat answers telegram_link_required and starts the link (catch below). Asking first
      // creates no link challenge for linked phones and lets the demo's sample numbers keep their
      // on-screen code.
      const res = await requestCode(number);
      const prev = step.kind === 'code' ? step : null;
      setStep({
        kind: 'code',
        phone: number,
        resendIn: res.resend_after_seconds,
        devOtp: res.development_otp,
        channel: res.delivery_channel === 'telegram' ? 'telegram' : null,
        validMin: Math.max(1, Math.round(res.expires_in_seconds / 60)),
        focusKey: (prev?.focusKey ?? 0) + 1,
        resent: prev !== null,
        bot: botEnabled,
      });
      setNoTelegram(false);
      setCode('');
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'network_error');
      // A phone whose link was removed: start the bot link again instead of a dead end.
      if (apiErr.code === 'telegram_link_required' && botEnabled) {
        try {
          await startLink(number);
          return;
        } catch (linkErr) {
          setError(linkErr instanceof ApiError ? linkErr : apiErr);
          return;
        }
      }
      setError(apiErr);
    } finally {
      setBusy(false);
    }
  };

  const newLink = async () => {
    if (step.kind !== 'link') return;
    setBusy(true);
    setError(undefined);
    try {
      await startLink(step.phone);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (e: FormEvent) => {
    e.preventDefault();
    if (step.kind !== 'code') return;
    setError(undefined);
    if (mode === 'reset') {
      const problem = passwordProblem(password, step.phone);
      setPwErr(problem ? t(problem) : undefined);
      setRepeatErr(!problem && password !== password2 ? t('pw.mismatch') : undefined);
      if (problem || password !== password2) return;
    }
    setPwErr(undefined);
    setRepeatErr(undefined);
    setBusy(true);
    try {
      if (mode === 'reset') await resetPassword(step.phone, code, password);
      else if (pendingSignup()) {
        // Phone proof for a Telegram/Google sign-up: the phone's account gets that identity linked.
        await completeSignup(step.phone, code);
        if (agree) await acceptLegal().catch(() => undefined);
        await reload();
      } else await verify(step.phone, code, { acceptLegal: agree });
      navigate(from, { replace: true });
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'network_error');
      if (apiErr.code === 'weak_password') {
        setPwErr(apiErr.message);
        return;
      }
      setError(apiErr);
      if (apiErr.code === 'otp_expired') {
        setCode('');
        setStep((cur) => (cur.kind === 'code' ? { ...cur, resendIn: 0, focusKey: cur.focusKey + 1 } : cur));
      }
    } finally {
      setBusy(false);
    }
  };

  const changeNumber = () => {
    setError(undefined);
    setStep({ kind: 'phone' });
  };

  return (
    <div className="stack" style={{ maxWidth: 480, margin: '0 auto' }}>
      <div className="stack">
        <div className="login-lang">
          <span className="muted">{t('settings.language')}</span>
          <LanguageSwitch />
        </div>
        <h1>{mode === 'reset' ? t('login.reset.title') : t('login.title')}</h1>
        <p className="muted">{t(mode === 'password' ? 'login.pw.lead' : mode === 'reset' ? 'login.reset.lead' : 'login.pw.codeLead')}</p>
        <p className="hint"><Link to="/settings">{t('settings.link')}</Link>: {t('settings.linkHint')}</p>
      </div>
      {notice && <p className="banner" role="status">{notice}</p>}
      <motion.div layout className="glass pad" transition={{ type: 'spring', stiffness: 380, damping: 34 }}>
        {mode === 'password' ? (
          <form className="stack" onSubmit={signInWithPassword} noValidate>
            <Field
              label={t('login.pw.login')}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              hint={t('login.pw.loginHint')}
            />
            <Field
              label={t('login.pw.password')}
              type={showPw ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={error ? error.message : undefined}
            />
            <ShowPassword id={showPwId} checked={showPw} onChange={setShowPw} />
            <button className="btn" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              {t('login.submit')}
            </button>
            <div className="row">
              <button type="button" className="btn ghost" onClick={() => switchMode('code')}>{t('login.pw.useCode')}</button>
              <button type="button" className="chip" onClick={() => switchMode('reset')}>{t('login.pw.forgot')}</button>
            </div>
            <p className="hint">{t('login.pw.firstTime')}</p>
          </form>
        ) : step.kind === 'phone' ? (
          <form className="stack" onSubmit={send} noValidate>
            <Field
              label={t('login.phone')}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              hint={t('login.phoneHint')}
              error={error && PHONE_FIELD_ERRORS.has(error.code) ? error.message : undefined}
            />
            {mode === 'code' && (
              <ConsentCheck checked={agree} onChange={(v) => { setAgree(v); setAgreeErr(false); }} error={agreeErr ? t('legal.agreeRequired') : undefined} />
            )}
            {error && !PHONE_FIELD_ERRORS.has(error.code) && (
              <p className="err" role="alert">
                {error.message}
              </p>
            )}
            <button className="btn" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              {botEnabled ? t('login.bot.continue') : t('login.sendCode')}
            </button>
          </form>
        ) : step.kind === 'link' ? (
          <motion.div className="stack" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <h2>{t('login.bot.title')}</h2>
            <p>
              {t('login.tg.number', { phone: step.phone })}{' '}
              <button type="button" className="chip" onClick={changeNumber}>
                {t('login.changeNumber')}
              </button>
            </p>
            {step.state === 'waiting' && (
              <>
                <a className="btn" href={step.deepLink} target="_blank" rel="noopener noreferrer">
                  {t('login.bot.open')}
                </a>
                <p className="hint">{t('login.bot.steps')}</p>
                <p role="status" className="hint">
                  <span className="spinner" aria-hidden="true" /> {t('login.bot.waiting')}
                </p>
                <button type="button" className="btn ghost" onClick={() => setStep(codeStepFor(step.phone, null, true))}>
                  {t('login.bot.haveCode')}
                </button>
              </>
            )}
            {step.state === 'expired' && (
              <p className="err" role="alert">{t('login.bot.expired')}</p>
            )}
            {step.state === 'failed' && (
              <p className="err" role="alert">
                {new ApiError(0, step.failure ?? 'otp_delivery_failed').message}
              </p>
            )}
            {error && <p className="err" role="alert">{error.message}</p>}
            {step.state === 'failed' && !LINK_FAILURES.has(step.failure ?? '') ? (
              <button type="button" className="btn" disabled={busy} onClick={() => void send()}>
                {busy && <span className="spinner" aria-hidden="true" />}{t('login.resend')}
              </button>
            ) : step.state !== 'waiting' && (
              <button type="button" className="btn" disabled={busy} onClick={() => void newLink()}>
                {busy && <span className="spinner" aria-hidden="true" />}{t('login.bot.newLink')}
              </button>
            )}
          </motion.div>
        ) : (
          <form className="stack" onSubmit={confirm} noValidate>
            {step.channel === 'telegram' ? (
              <motion.div className="stack" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
                <h2>{t('login.tg.title')}</h2>
                <p>
                  {t('login.tg.number', { phone: step.phone })}{' '}
                  <button type="button" className="chip" onClick={changeNumber}>
                    {t('login.changeNumber')}
                  </button>
                </p>
                <p className="hint">{t('login.validFor', { n: step.validMin })}</p>
              </motion.div>
            ) : (
              <p>
                {t('login.codeSentBefore')}<b>{step.phone}</b>{t('login.codeSentAfter')}{' '}
                <button type="button" className="chip" onClick={changeNumber}>
                  {t('login.changeNumber')}
                </button>
              </p>
            )}
            {step.devOtp && (
              <p className="banner" role="note">
                {t('login.devBefore')}<b className="mono">{step.devOtp}</b>{t('login.devAfter')}
              </p>
            )}
            {/* Always mounted so a screen reader announces the text when it appears; invisible while empty. */}
            <p role="status" className={step.resent ? 'hint' : 'sr-only'}>
              {step.resent ? t('login.resent') : ''}
            </p>
            {step.bot && step.channel === 'telegram' && botUsername && (
              // The code is in the bot chat: one tap opens it; the user copies the code and comes back.
              <a
                className="btn ghost"
                href={`https://t.me/${encodeURIComponent(botUsername)}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {t('login.bot.open')}
              </a>
            )}
            <Field
              key={step.focusKey}
              label={t('login.code')}
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]*"
              style={step.channel === 'telegram' ? { letterSpacing: '0.18em', fontVariantNumeric: 'tabular-nums' } : undefined}
              value={code}
              // No native maxLength: it would cut a pasted "123 456" to "123 45" before we strip the space.
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, CODE_LENGTH))}
              hint={step.bot ? t('login.bot.codeHint') : step.channel === 'telegram' ? t('login.tg.open') : undefined}
              error={error ? error.message : undefined}
              autoFocus
            />
            {mode === 'reset' && (
              <>
                <Field
                  label={t('pw.new')}
                  type={showPw ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  hint={t('pw.rules')}
                  error={pwErr}
                />
                <Field
                  label={t('pw.repeat')}
                  type={showPw ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  error={repeatErr}
                />
                <ShowPassword id={showPwId} checked={showPw} onChange={setShowPw} />
                <p className="hint">{t('login.reset.note')}</p>
              </>
            )}
            <button className="btn" disabled={busy || code.length !== CODE_LENGTH}>
              {busy && <span className="spinner" aria-hidden="true" />}{mode === 'reset' ? t('login.reset.submit') : t('login.submit')}
            </button>
            <button type="button" className="btn ghost" disabled={busy || step.resendIn > 0} onClick={() => void send()}>
              {step.resendIn > 0 ? t('login.resendIn', { n: step.resendIn }) : t('login.resend')}
            </button>
            {step.channel === 'telegram' && !step.bot && (
              <div className="stack">
                <p className="hint">{t('login.tg.noCode')}</p>
                <div>
                  <button
                    type="button"
                    className="chip"
                    aria-expanded={noTelegram}
                    aria-controls={noTelegramId}
                    onClick={() => setNoTelegram((v) => !v)}
                  >
                    {t('login.tg.noTelegram')}
                  </button>
                </div>
                {noTelegram && (
                  <motion.p
                    id={noTelegramId}
                    className="hint"
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {t('login.tg.noTelegramBody')}
                  </motion.p>
                )}
              </div>
            )}
          </form>
        )}
      </motion.div>
      {mode !== 'reset' && step.kind === 'phone' && !pendingSignup() && (
        <SocialSignIn
          onSignedIn={async () => {
            await reload();
            navigate(from, { replace: true });
          }}
          onPhoneRequired={() => {
            setMode('code');
            setStep({ kind: 'phone' });
            setError(undefined);
            setNotice(t('social.phoneRequired'));
          }}
        />
      )}
      {mode !== 'password' && (
        <button type="button" className="btn ghost" onClick={() => switchMode('password')}>
          {t('login.pw.usePassword')}
        </button>
      )}
      <p className="hint">{t('login.disclaimer')}</p>
    </div>
  );
}

