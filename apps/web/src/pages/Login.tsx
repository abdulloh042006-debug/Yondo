import { motion } from 'motion/react';
import { useEffect, useId, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { dedupePhonePrefix } from '../lib/format';
import { ConsentCheck } from '../ui/Consent';
import { Field } from '../ui/form';

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

const CODE_LENGTH = 6;
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
  const { requestCode, verify, state } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';
  const [step, setStep] = useState<Step>({ kind: 'phone' });
  const [phone, setPhone] = useState('+998');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [agree, setAgree] = useState(false);
  const [agreeErr, setAgreeErr] = useState(false);
  const [noTelegram, setNoTelegram] = useState(false);
  const noTelegramId = useId();
  const [botEnabled, setBotEnabled] = useState(false);

  useEffect(() => {
    let live = true;
    api
      .get<Schemas['LinkConfig']>('/auth/telegram/link/config', { anonymous: true })
      .then((cfg) => live && setBotEnabled(cfg.enabled))
      .catch(() => undefined); // unknown = keep the existing (demo) login
    return () => {
      live = false;
    };
  }, []);

  // Poll the link status while the user is in Telegram; stop on any final state.
  useEffect(() => {
    if (step.kind !== 'link' || step.state !== 'waiting') return;
    const timer = window.setTimeout(async () => {
      try {
        const st = await api.get<Schemas['LinkStatus']>('/auth/telegram/link/status', {
          anonymous: true,
          headers: { 'X-Yondo-Link-Poll': step.poll },
        });
        setStep((cur) => {
          if (cur.kind !== 'link' || cur.poll !== step.poll) return cur;
          if (st.status === 'otp_sent') return codeStepFor(cur.phone, null, true);
          if (st.status === 'expired') return { ...cur, state: 'expired' };
          if (st.status === 'failed') return { ...cur, state: 'failed', failure: st.failure_code };
          return { ...cur }; // new object = schedule the next poll
        });
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setStep((cur) => (cur.kind === 'link' && cur.poll === step.poll ? { ...cur, state: 'expired' } : cur));
        } else {
          setStep((cur) => (cur.kind === 'link' ? { ...cur } : cur)); // network blip: keep polling
        }
      }
    }, POLL_MS);
    return () => window.clearTimeout(timer);
  }, [step]);

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

  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!agree) {
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
      // Bot login: a phone without a verified chat links first; a linked phone just gets a code.
      if (botEnabled && step.kind === 'phone' && (await startLink(number))) return;
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
    setBusy(true);
    setError(undefined);
    try {
      await verify(step.phone, code, { acceptLegal: agree });
      navigate(from, { replace: true });
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'network_error');
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
        <h1>{t('login.title')}</h1>
        <p className="muted">{t('login.lead')}</p>
        <p className="hint"><Link to="/settings">{t('settings.link')}</Link>: {t('settings.linkHint')}</p>
      </div>
      <motion.div layout className="glass pad" transition={{ type: 'spring', stiffness: 380, damping: 34 }}>
        {step.kind === 'phone' ? (
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
            <ConsentCheck checked={agree} onChange={(v) => { setAgree(v); setAgreeErr(false); }} error={agreeErr ? t('legal.agreeRequired') : undefined} />
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
            {step.state !== 'waiting' && (
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
            <button className="btn" disabled={busy || code.length !== CODE_LENGTH}>
              {busy && <span className="spinner" aria-hidden="true" />}{t('login.submit')}
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
      <p className="hint">{t('login.disclaimer')}</p>
    </div>
  );
}
