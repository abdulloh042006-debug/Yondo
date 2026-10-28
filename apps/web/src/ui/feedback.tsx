import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { ApiError } from '../api/client';
import { t } from '../i18n';
import { Orb } from './motion';

/* ---------------- toasts: only ever created after the server confirmed the outcome ---------------- */
interface Toast {
  id: number;
  tone: 'ok' | 'bad';
  text: string;
}
const ToastCtx = createContext<{ push: (tone: 'ok' | 'bad', text: string) => void }>({ push: () => {} });
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const next = useRef(1);
  const push = useCallback((tone: 'ok' | 'bad', text: string) => {
    const id = next.current++;
    setItems((list) => [...list.slice(-2), { id, tone, text }]);
    window.setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)), 5200);
  }, []);
  const value = useMemo(() => ({ push }), [push]);
  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div
              key={t.id}
              className={`glass toast ${t.tone}`}
              initial={{ opacity: 0, y: -18, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.97 }}
              transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            >
              <span className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
                {t.tone === 'ok' && (
                  <svg className="check-draw" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12.5l4.5 4.5L19 7.5" />
                  </svg>
                )}
                {t.text}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

/* ---------------- dialog with focus trap ---------------- */
export function Dialog({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const root = ref.current;
    const focusables = () =>
      Array.from(
        root?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])') ?? [],
      ).filter((el) => !el.hasAttribute('disabled'));
    (focusables()[0] ?? root)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
      if (e.key === 'Tab') {
        const list = focusables();
        if (!list.length) return;
        const first = list[0];
        const last = list[list.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      previous?.focus?.();
    };
  }, [open, onClose]);
  // Portal: an ancestor with a filter/backdrop-filter/transform (glass top bar, page transition) would
  // otherwise become the containing block of this `position: fixed` overlay and clip the dialog.
  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className="glass dialog"
            initial={{ opacity: 0, y: 40, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 360, damping: 32 }}
          >
            <h2 id={titleId}>{title}</h2>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

/** Consequential action: requires an explicit confirm and, optionally, a written reason. */
interface ConfirmProps {
  title: string;
  body: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  reason?: { label: string; min: number; max: number };
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}

export function ConfirmDialog({ open, ...props }: ConfirmProps & { open: boolean }) {
  // The body mounts fresh each time the dialog opens, so reason/error never leak between uses.
  return (
    <Dialog open={open} title={props.title} onClose={props.onClose}>
      <ConfirmBody {...props} />
    </Dialog>
  );
}

function ConfirmBody({ body, confirmLabel, danger, reason, onConfirm, onClose }: ConfirmProps) {
  const rid = useId();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const tooShort = reason ? text.trim().length < reason.min : false;
  const submit = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await onConfirm(text.trim());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('common.unexpected'));
      setBusy(false);
    }
  };
  return (
    <div className="stack">
      <div className="muted">{body}</div>
      {reason && (
        <div className="field">
          <label htmlFor={`${rid}-r`}>{reason.label}</label>
          <textarea
            id={`${rid}-r`}
            className="input"
            value={text}
            maxLength={reason.max}
            onChange={(e) => setText(e.target.value)}
            aria-invalid={text.length > 0 && tooShort}
            aria-describedby={`${rid}-h`}
          />
          <span id={`${rid}-h`} className="hint">{t('confirm.reasonHint', { min: reason.min })}</span>
        </div>
      )}
      {error && (
        <p className="err" role="alert">
          {error}
        </p>
      )}
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button className="btn ghost" onClick={onClose} disabled={busy}>
          {t('common.cancel')}
        </button>
        <button className={`btn ${danger ? 'danger' : ''}`} onClick={submit} disabled={busy || tooShort}>
          {busy && <span className="spinner" aria-hidden="true" />}
          {confirmLabel}
        </button>
      </div>
    </div>
  );
}

/* ---------------- states ---------------- */
export function Loading({ rows = 3, label = t('common.loading') }: { rows?: number; label?: string }) {
  return (
    <div className="stack" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" />
      ))}
    </div>
  );
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="glass state">
      <Orb />
      <h3>{title}</h3>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const unavailable = error.unavailable;
  return (
    <div className="glass state" role="alert">
      <Orb />
      <h3>{unavailable ? t('common.unavailableTitle') : t('common.failedTitle')}</h3>
      <p className="muted">{error.message}</p>
      {error.requestId && <p className="hint mono">{t('common.requestId', { id: error.requestId })}</p>}
      {onRetry && (
        <button className="btn ghost" onClick={onRetry}>
          {t('common.retry')}
        </button>
      )}
    </div>
  );
}

export function StatusTag({ map, value }: { map: Record<string, { label: string; tone: string }>; value: string }) {
  const s = map[value] ?? { label: value, tone: '' };
  return <span className={`tag ${s.tone}`}>{s.label}</span>;
}
