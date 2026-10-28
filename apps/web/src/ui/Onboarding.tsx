import { motion, useReducedMotion } from 'motion/react';
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { t, type Key } from '../i18n';
import { firstRun, type FlowName } from '../lib/firstRun';
import { Dialog } from './feedback';
import { ease } from './motion';
import { OnboardingArt, type ArtKind } from './OnboardingArt';

/**
 * The 3-card guide: Top (discover) → Bron qil (book) → Xavfsiz uçraşuv (safe meeting).
 *
 * - First visit: `OnboardingHost` (mounted in Layout, next to the page) opens it on `/` and, for companions, `/studio`.
 *   It never opens on `/login` (so never over the code step), `/terms`, `/privacy` or any deep link.
 * - Later: `GuideButton` (Help and Settings) opens the same dialog on demand.
 * - Dismissing it (Skip, Finish, Escape, click outside) is remembered on this device only (`lib/firstRun`).
 * - Wording is deliberately modest about safety: tools and information, SOS = an alert recorded for a moderator.
 */
export type GuideVariant = 'customer' | 'companion';

const CARDS: ReadonlyArray<{ art: ArtKind }> = [{ art: 'discover' }, { art: 'book' }, { art: 'safe' }];
const VARIANTS = ['customer', 'companion'] as const;
const PREFIX: Record<GuideVariant, 'c' | 'p'> = { customer: 'c', companion: 'p' };
const flowOf = (variant: GuideVariant): FlowName => `onboarding.${variant}`;

/** Signed out or customer → customer wording; companion-only → companion wording; both roles → customer + a switch. */
function useAudience(): { variant: GuideVariant; canSwitch: boolean } {
  const { user } = useAuth();
  const companion = !!user?.roles.includes('companion');
  const customer = !!user?.roles.includes('customer');
  return { variant: companion && !customer ? 'companion' : 'customer', canSwitch: companion && customer };
}

function GuideDialog({ open, variant, canSwitch, onDone }: { open: boolean; variant: GuideVariant; canSwitch: boolean; onDone: (shown?: GuideVariant) => void }) {
  // Must stay stable: Dialog re-runs its focus handling whenever `onClose` changes identity.
  const close = useCallback(() => onDone(), [onDone]);
  return (
    <Dialog open={open} title={t('guide.title')} onClose={close}>
      <GuideBody initial={variant} canSwitch={canSwitch} onDone={onDone} />
    </Dialog>
  );
}

// The body mounts fresh every time the dialog opens, so the step never leaks between uses.
function GuideBody({ initial, canSwitch, onDone }: { initial: GuideVariant; canSwitch: boolean; onDone: (shown?: GuideVariant) => void }) {
  const reduce = useReducedMotion();
  const [variant, setVariant] = useState(initial);
  // `refocus`: "Back" vanishes on the first card; when it had focus, hand focus to "Next" instead of dropping it to <body>.
  const [nav, setNav] = useState({ step: 0, dir: 1, refocus: false });
  const nextRef = useRef<HTMLButtonElement>(null);
  const { step, dir } = nav;
  const last = step === CARDS.length - 1;
  const prefix = PREFIX[variant];
  const n = step + 1;

  useEffect(() => {
    if (nav.refocus) nextRef.current?.focus();
  }, [nav]);

  return (
    <div className="stack guide">
      {canSwitch && (
        <div className="row" role="group" aria-label={t('guide.forWhom')}>
          {VARIANTS.map((v) => (
            <button
              key={v}
              type="button"
              className="chip"
              aria-pressed={variant === v}
              onClick={() => {
                setVariant(v);
                setNav({ step: 0, dir: 1, refocus: false });
              }}
            >
              {t(v === 'customer' ? 'guide.asCustomer' : 'guide.asCompanion')}
            </button>
          ))}
        </div>
      )}
      <div className="spread guide-top">
        <ol className="guide-dots" aria-label={t('guide.progress')}>
          {CARDS.map((_, i) => (
            <li key={i} aria-current={i === step ? 'step' : undefined}>
              <span className="sr-only">{t('guide.stepOf', { n: i + 1, total: CARDS.length })}</span>
            </li>
          ))}
        </ol>
        <button type="button" className="btn ghost sm" onClick={() => onDone(variant)}>
          {t('guide.skip')}
        </button>
      </div>
      <div className="guide-stage" aria-live="polite" aria-atomic="true">
        <motion.div
          key={`${variant}-${step}`}
          className="stack guide-card"
          initial={reduce ? false : { opacity: 0, x: dir * 28 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.28, ease }}
        >
          <OnboardingArt kind={CARDS[step].art} />
          <h3 className="guide-title">{t(`guide.${prefix}${n}.title` as Key)}</h3>
          <p>{t(`guide.${prefix}${n}.body` as Key)}</p>
          {last && <p className="guide-note">{t('guide.note')}</p>}
        </motion.div>
      </div>
      <div className="guide-nav">
        {step > 0 && (
          <button type="button" className="btn ghost" onClick={() => setNav({ step: step - 1, dir: -1, refocus: step === 1 })}>
            {t('guide.back')}
          </button>
        )}
        <button
          ref={nextRef}
          type="button"
          className="btn"
          data-autofocus
          onClick={() => (last ? onDone(variant) : setNav({ step: step + 1, dir: 1, refocus: false }))}
        >
          {last ? t('guide.finish') : t('guide.next')}
        </button>
      </div>
    </div>
  );
}

/** First-visit guide. Rendered by Layout next to the page, and only once the consent question is settled. */
export function OnboardingHost() {
  const { state } = useAuth();
  const { pathname } = useLocation();
  const { variant, canSwitch } = useAudience();
  const [, rerender] = useReducer((x: number) => x + 1, 0);
  // `/studio` is companion-only, whatever else the user is.
  const trigger: GuideVariant | null = pathname === '/' ? variant : pathname === '/studio' ? 'companion' : null;

  const onDone = useCallback(
    (shown?: GuideVariant) => {
      if (trigger) firstRun.markSeen(flowOf(trigger));
      if (shown) firstRun.markSeen(flowOf(shown));
      rerender();
    },
    [trigger],
  );
  if (!trigger) return null;
  // Wait for the session check: a companion must not be shown the customer wording first.
  const open = state.status !== 'loading' && !firstRun.isSeen(flowOf(trigger));
  return <GuideDialog open={open} variant={trigger} canSwitch={canSwitch && trigger === variant} onDone={onDone} />;
}

/** "Show the guide again" control for Help and Settings. */
export function GuideButton({ className = 'btn ghost' }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const { variant, canSwitch } = useAudience();
  const onDone = useCallback((shown?: GuideVariant) => {
    if (shown) firstRun.markSeen(flowOf(shown));
    setOpen(false);
  }, []);
  return (
    <>
      <button type="button" className={className} aria-haspopup="dialog" onClick={() => setOpen(true)}>
        {t('guide.open')}
      </button>
      <GuideDialog open={open} variant={variant} canSwitch={canSwitch} onDone={onDone} />
    </>
  );
}
