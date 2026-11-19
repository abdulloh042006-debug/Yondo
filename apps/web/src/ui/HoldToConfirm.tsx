import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { ApiError } from '../api/client';
import { t } from '../i18n';

/** Hold time (owner, 2026-11-18): exactly 1.5 s of continuous press. Exported for tests. */
export const HOLD_MS = 1500;

type Phase = 'idle' | 'holding' | 'busy' | 'done';

/**
 * Hold-to-Confirm destructive button (docs/design/redesign-2026-11.md §4.4). Used ONLY for account deletion,
 * blocking and cancelling a booking; red (--c-danger) is allowed only here (owner, 2026-11-18).
 * - Press and hold (pointer, or Space/Enter) for 1.5 s: the red fill sweeps left → right, the label reads
 *   "Tasdiqlanmoqda…"; only a full hold runs `onConfirm`, once.
 * - Early release / blur / pointer cancel: the fill retracts in 0.25 s and nothing runs.
 * - Any activation that is not our own hold (screen-reader double-tap, switch or voice control) opens an inline
 *   two-step confirmation: never a one-tap action, but an equivalent path.
 * - Every step is announced in a polite live region. Reduced motion: stepped fill (CSS), same timing.
 */
export function HoldToConfirm({
  label,
  yesLabel,
  doneLabel,
  onConfirm,
  disabled,
  children,
}: {
  label: string;
  /** The second-step button for non-hold activation, e.g. "Ha, öçiriş". */
  yesLabel: string;
  /** Announced (and briefly shown) after success. */
  doneLabel?: string;
  onConfirm: () => Promise<void> | void;
  disabled?: boolean;
  /** Optional consequence text shown above the button inside the danger zone. */
  children?: ReactNode;
}) {
  const id = useId();
  const [phase, setPhase] = useState<Phase>('idle');
  const [retract, setRetract] = useState(false);
  const [twoStep, setTwoStep] = useState(false);
  const [live, setLive] = useState('');
  const [error, setError] = useState<string>();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const ownPress = useRef(false);
  const yesRef = useRef<HTMLButtonElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (twoStep) yesRef.current?.focus();
  }, [twoStep]);

  const run = async () => {
    setPhase('busy');
    setError(undefined);
    try {
      await onConfirm();
      setPhase('done');
      if (doneLabel) setLive(doneLabel);
    } catch (e) {
      setPhase('idle');
      setRetract(true);
      setError(e instanceof ApiError ? e.message : t('common.actionFailed'));
    }
  };
  const start = () => {
    if (disabled || phase !== 'idle') return;
    setTwoStep(false);
    setError(undefined);
    setRetract(false);
    setPhase('holding');
    setLive(t('hold.started'));
    timer.current = setTimeout(() => void run(), HOLD_MS);
  };
  const cancel = () => {
    if (phase !== 'holding') return;
    clearTimeout(timer.current);
    setPhase('idle');
    setRetract(true);
    setLive(t('hold.cancelled'));
  };
  const release = () => {
    cancel();
    // the click that follows our own press must not open the two-step path
    setTimeout(() => (ownPress.current = false), 60);
  };

  const holding = phase === 'holding';
  const text = holding || phase === 'busy' ? t('hold.confirming') : phase === 'done' && doneLabel ? doneLabel : label;
  return (
    <div className="danger-zone">
      {children}
      <button
        ref={btnRef}
        type="button"
        className={`hold${holding ? ' holding' : ''}${phase === 'done' || phase === 'busy' ? ' done' : ''}${retract ? ' retract' : ''}`}
        disabled={disabled}
        aria-describedby={`${id}-hint`}
        aria-busy={phase === 'busy'}
        onPointerDown={(e) => {
          if (e.button > 0) return; // main button / touch / pen only
          ownPress.current = true;
          e.currentTarget.setPointerCapture?.(e.pointerId);
          start();
        }}
        onPointerUp={release}
        onPointerCancel={release}
        onLostPointerCapture={cancel}
        onContextMenu={(e) => e.preventDefault()}
        onKeyDown={(e) => {
          if (e.key !== ' ' && e.key !== 'Enter') return;
          e.preventDefault();
          if (e.repeat) return;
          ownPress.current = true;
          start();
        }}
        onKeyUp={(e) => {
          if (e.key !== ' ' && e.key !== 'Enter') return;
          e.preventDefault();
          release();
        }}
        onBlur={cancel}
        onClick={() => {
          if (ownPress.current || phase !== 'idle') return;
          setTwoStep(true);
          setLive(t('hold.twoStep', { action: label }));
        }}
      >
        <span className="hold-fill" aria-hidden="true">
          <span>{text}</span>
        </span>
        <span className="hold-label">{text}</span>
      </button>
      <p id={`${id}-hint`} className="hint hold-hint">{t('hold.hint')}</p>
      {twoStep && (
        <div className="hold-two-step" role="group" aria-label={label}>
          <button type="button" className="btn ghost sm" onClick={() => { setTwoStep(false); setLive(t('hold.cancelled')); btnRef.current?.focus(); }}>
            {t('hold.no')}
          </button>
          <button ref={yesRef} type="button" className="btn sm hold-yes" onClick={() => { setTwoStep(false); void run(); }}>
            {yesLabel}
          </button>
        </div>
      )}
      {error && <p className="err" role="alert">{error}</p>}
      <p className="sr-only" aria-live="polite">{live}</p>
    </div>
  );
}
