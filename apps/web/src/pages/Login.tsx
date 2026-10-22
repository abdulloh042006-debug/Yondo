import { motion } from 'motion/react';
import { useEffect, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Field } from '../ui/form';

type Step = { kind: 'phone' } | { kind: 'code'; phone: string; resendIn: number; devOtp?: string | null };

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

  useEffect(() => {
    if (step.kind !== 'code' || step.resendIn <= 0) return;
    const t = window.setTimeout(() => setStep({ ...step, resendIn: step.resendIn - 1 }), 1000);
    return () => window.clearTimeout(t);
  }, [step]);

  if (state.status === 'authed') return <Navigate to={from} replace />;

  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 9) {
      setError(new ApiError(422, 'invalid_phone_number'));
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const res = await requestCode(phone.trim());
      setStep({ kind: 'code', phone: phone.trim(), resendIn: res.resend_after_seconds, devOtp: res.development_otp });
      setCode('');
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
      await verify(step.phone, code.trim());
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack" style={{ maxWidth: 480, margin: '0 auto' }}>
      <div className="stack">
        <h1>Yondo’ga kirish</h1>
        <p className="muted">Telefon raqamingizni kiriting — SMS orqali bir martalik kod yuboramiz.</p>
        <p className="hint"><Link to="/settings">Sozlamalar</Link>: ilova ko‘rinishi (rang mavzulari).</p>
      </div>
      <motion.div layout className="glass pad" transition={{ type: 'spring', stiffness: 380, damping: 34 }}>
        {step.kind === 'phone' ? (
          <form className="stack" onSubmit={send} noValidate>
            <Field
              label="Telefon raqami"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              hint="Namuna: +998 90 123 45 67"
              error={error?.code === 'invalid_phone_number' ? error.message : undefined}
            />
            {error && error.code !== 'invalid_phone_number' && (
              <p className="err" role="alert">
                {error.message}
              </p>
            )}
            <button className="btn" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}Kod yuborish
            </button>
          </form>
        ) : (
          <form className="stack" onSubmit={confirm} noValidate>
            <p>
              <b>{step.phone}</b> raqamiga kod yuborildi.{' '}
              <button type="button" className="chip" onClick={() => setStep({ kind: 'phone' })}>
                Raqamni o‘zgartirish
              </button>
            </p>
            {step.devOtp && (
              <p className="banner" role="note">
                Faqat ishlab chiqish muhitida: kod <b className="mono">{step.devOtp}</b>. Ishlab chiqarishda server kodni
                qaytarmaydi.
              </p>
            )}
            <Field
              label="Tasdiqlash kodi"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              error={error ? error.message : undefined}
              autoFocus
            />
            <button className="btn" disabled={busy || code.trim().length < 4}>
              {busy && <span className="spinner" aria-hidden="true" />}Kirish
            </button>
            <button type="button" className="btn ghost" disabled={busy || step.resendIn > 0} onClick={() => void send()}>
              {step.resendIn > 0 ? `Yangi kod: ${step.resendIn} s` : 'Kodni qayta yuborish'}
            </button>
          </form>
        )}
      </motion.div>
      <p className="hint">
        Davom etib, Yondo — tanishuv yoki eskort xizmati emas, balki ochiq joylarda uchrashuvlar uchun hamroh topish
        platformasi ekanini tasdiqlaysiz.
      </p>
    </div>
  );
}
