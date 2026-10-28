import { useCallback, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { t } from '../i18n';
import { firstRun } from '../lib/firstRun';

/**
 * Opening animation (owner-approved 2026-10-28; choreography: design-prototype/brand/ornament/README.md section 7).
 *
 * - Shown ONLY on the very first opening of the app on this device, and only when the page was opened on `/`
 *   (never on a deep link such as /login, /terms, /privacy). The decision is taken once per page load.
 * - The flag (`yondo.intro.v1`) is written when it STARTS, so a refresh half-way does not replay it. If storage is
 *   unavailable it still shows at most once per page load (in-memory flag), never on every navigation.
 * - Overlay in a portal on `document.body`: the app mounts underneath (no layout shift, loading is not blocked) and
 *   is `inert` while the overlay is up. No audio of any kind. Skip = tap/click, Enter, Space, Escape or the button.
 * - Order: this intro first; the first-run guide (Onboarding) opens only after it has closed (`useIntroActive`);
 *   the consent page renders below it and is simply uncovered afterwards.
 * - Reduced motion: a static brand frame, shown for about half a second, opacity-only exit; still skippable.
 * - Transform and opacity only. Colours: ink/paper by theme (night themes `*-tun` = ink ground), carrot as graphic only.
 */
export const INTRO_MS = { full: 2450, reduced: 450, fadeOut: 350, fadeFast: 150 } as const;

type Phase = 'idle' | 'active' | 'done';
let phase: Phase = 'idle';
let decided = false;
const listeners = new Set<() => void>();
const setPhase = (next: Phase) => {
  if (phase === next) return;
  phase = next;
  listeners.forEach((l) => l());
};
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => void listeners.delete(l);
};

/** Decide once per page load. Pure apart from the module flags; the first-run flag is written when the overlay mounts. */
function decide(pathname: string): void {
  if (decided) return;
  decided = true;
  if (pathname === '/' && !firstRun.isSeen('intro')) phase = 'active';
}

/** Tests only: forget the per-page-load decision. */
export function resetIntroForTests(): void {
  phase = 'idle';
  decided = false;
  listeners.clear();
}

/** True while the opening animation is on screen; other first-run flows wait for it. */
export function useIntroActive(): boolean {
  return useSyncExternalStore(subscribe, () => phase === 'active', () => false);
}

const prefersReduced = () => typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function IntroOverlay() {
  const [leaving, setLeaving] = useState<null | 'slow' | 'fast'>(null);
  const [reduced] = useState(prefersReduced);
  const skipRef = useRef<HTMLButtonElement>(null);
  const timers = useRef<number[]>([]);
  const finished = useRef(false);

  const leave = useCallback((fast: boolean) => {
    if (finished.current) return;
    finished.current = true;
    timers.current.forEach(window.clearTimeout);
    timers.current = [window.setTimeout(() => setPhase('done'), fast || reduced ? INTRO_MS.fadeFast : INTRO_MS.fadeOut)];
    setLeaving(fast || reduced ? 'fast' : 'slow');
  }, [reduced]);

  // Start: remember it (so a refresh does not replay), make the app inert, take focus; undo all of it on close.
  useLayoutEffect(() => {
    firstRun.markSeen('intro');
    const root = document.getElementById('root');
    const before = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    root?.setAttribute('inert', '');
    skipRef.current?.focus({ preventScroll: true });
    return () => {
      root?.removeAttribute('inert');
      if (before && before !== document.body && before.isConnected) before.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    timers.current = [window.setTimeout(() => leave(false), reduced ? INTRO_MS.reduced : INTRO_MS.full)];
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        leave(true);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      timers.current.forEach(window.clearTimeout);
    };
  }, [leave, reduced]);

  return createPortal(
    <div
      className={`yi${reduced ? ' yi-rm' : ''}${leaving ? ` yi-leaving${leaving === 'fast' ? ' yi-fast' : ''}` : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label={t('intro.label')}
      data-testid="intro"
      onPointerDown={() => leave(true)}
    >
      <div className="yi-stage" aria-hidden="true">
        <svg className="yi-sym" viewBox="0 0 64 64">
          <defs>
            <mask id="yi-mr" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
              <rect width="64" height="64" fill="#fff" />
              <path d="M32 55V40Q31 37 28 33L17.6 17.4" stroke="#000" strokeWidth="9.4" fill="none" strokeLinejoin="round" />
              <path d="M32 40Q33 37 36 33L46.4 17.4" stroke="#000" strokeWidth="2.5" fill="none" />
            </mask>
            <mask id="yi-ml" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
              <rect width="64" height="64" fill="#fff" />
              <path d="M32 50V40Q31 37 28 33L17.6 17.4" stroke="#000" strokeWidth="2.5" fill="none" strokeLinejoin="round" />
            </mask>
          </defs>
          <g fill="none" stroke="currentColor" strokeWidth="7.4" strokeLinejoin="round">
            <path className="yi-draw yi-r" pathLength="100" d="M32 40Q33 37 36 33L46.4 17.4" mask="url(#yi-mr)" />
            <path className="yi-draw yi-l" pathLength="100" d="M32 55V40Q31 37 28 33L17.6 17.4" mask="url(#yi-ml)" />
          </g>
          <path className="yi-foot" d="M32 50.2L36.36 56.2L32 62.2L27.64 56.2Z" fill="currentColor" />
          <path className="yi-star yi-s1" d="M14 2.4L16.76 5.35L20.79 5.21L20.65 9.24L23.6 12L20.65 14.76L20.79 18.79L16.76 18.65L14 21.6L11.24 18.65L7.21 18.79L7.35 14.76L4.4 12L7.35 9.24L7.21 5.21L11.24 5.35ZM11.6 12a2.4 2.4 0 1 0 4.8 0a2.4 2.4 0 1 0 -4.8 0Z" fill="currentColor" fillRule="evenodd" />
          <path className="yi-star yi-s2" d="M50 2.4L52.76 5.35L56.79 5.21L56.65 9.24L59.6 12L56.65 14.76L56.79 18.79L52.76 18.65L50 21.6L47.24 18.65L43.21 18.79L43.35 14.76L40.4 12L43.35 9.24L43.21 5.21L47.24 5.35ZM47.6 12a2.4 2.4 0 1 0 4.8 0a2.4 2.4 0 1 0 -4.8 0Z" fill="#E8501A" fillRule="evenodd" />
          <circle className="yi-ring" cx="50" cy="12" r="10" fill="none" stroke="#E8501A" strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
        </svg>
        <svg className="yi-wm" viewBox="80.34 17.4 134.31 31.2">
          <path fill="currentColor" d="M90.54285714285714 48.0V37.67142857142857L80.34285714285714 18.0H86.64285714285714L92.98571428571428 30.857142857142858H93.75714285714285L100.1 18.0H106.4L96.2 37.67142857142857V48.0ZM119.94285714285714 48.6Q114.28571428571428 48.6 110.94285714285714 45.49285714285715Q107.6 42.385714285714286 107.6 36.6V29.4Q107.6 23.614285714285714 110.94285714285714 20.507142857142856Q114.28571428571428 17.4 119.94285714285714 17.4Q125.6 17.4 128.94285714285712 20.507142857142856Q132.28571428571428 23.614285714285714 132.28571428571428 29.4V36.6Q132.28571428571428 42.385714285714286 128.94285714285712 45.49285714285715Q125.6 48.6 119.94285714285714 48.6ZM119.94285714285714 43.542857142857144Q123.11428571428571 43.542857142857144 124.87142857142857 41.7Q126.62857142857143 39.85714285714286 126.62857142857143 36.77142857142857V29.228571428571428Q126.62857142857143 26.142857142857142 124.87142857142857 24.299999999999997Q123.11428571428571 22.457142857142856 119.94285714285714 22.457142857142856Q116.81428571428572 22.457142857142856 115.03571428571428 24.299999999999997Q113.25714285714285 26.142857142857142 113.25714285714285 29.228571428571428V36.77142857142857Q113.25714285714285 39.85714285714286 115.03571428571428 41.7Q116.81428571428572 43.542857142857144 119.94285714285714 43.542857142857144ZM135.97142857142856 48.0V18.0H146.72857142857143L152.68571428571428 44.142857142857146H153.45714285714286V18.0H159.0285714285714V48.0H148.27142857142857L142.31428571428572 21.857142857142858H141.54285714285714V48.0ZM162.54285714285712 48.0V43.028571428571425H166.48571428571427V22.97142857142857H162.54285714285712V18.0H174.88571428571427Q180.92857142857142 18.0 184.07857142857142 21.064285714285717Q187.2285714285714 24.12857142857143 187.2285714285714 30.17142857142857V35.82857142857143Q187.2285714285714 41.871428571428574 184.07857142857142 44.93571428571428Q180.92857142857142 48.0 174.88571428571427 48.0ZM172.14285714285714 42.857142857142854H174.97142857142856Q178.39999999999998 42.857142857142854 179.98571428571427 41.05714285714285Q181.57142857142856 39.25714285714285 181.57142857142856 36.0V30.0Q181.57142857142856 26.7 179.98571428571427 24.92142857142857Q178.39999999999998 23.142857142857142 174.97142857142856 23.142857142857142H172.14285714285714ZM202.31428571428572 48.6Q196.65714285714284 48.6 193.3142857142857 45.49285714285715Q189.97142857142856 42.385714285714286 189.97142857142856 36.6V29.4Q189.97142857142856 23.614285714285714 193.3142857142857 20.507142857142856Q196.65714285714284 17.4 202.31428571428572 17.4Q207.97142857142856 17.4 211.3142857142857 20.507142857142856Q214.65714285714284 23.614285714285714 214.65714285714284 29.4V36.6Q214.65714285714284 42.385714285714286 211.3142857142857 45.49285714285715Q207.97142857142856 48.6 202.31428571428572 48.6ZM202.31428571428572 43.542857142857144Q205.48571428571427 43.542857142857144 207.24285714285713 41.7Q209.0 39.85714285714286 209.0 36.77142857142857V29.228571428571428Q209.0 26.142857142857142 207.24285714285713 24.299999999999997Q205.48571428571427 22.457142857142856 202.31428571428572 22.457142857142856Q199.18571428571428 22.457142857142856 197.40714285714284 24.299999999999997Q195.62857142857143 26.142857142857142 195.62857142857143 29.228571428571428V36.77142857142857Q195.62857142857143 39.85714285714286 197.40714285714284 41.7Q199.18571428571428 43.542857142857144 202.31428571428572 43.542857142857144Z" />
        </svg>
        <div className="yi-rule">
          <i />
          <svg width="14" height="14" viewBox="-11 -11 22 22">
            <path d="M0 -10L2.87 -6.93L7.07 -7.07L6.93 -2.87L10 0L6.93 2.87L7.07 7.07L2.87 6.93L0 10L-2.87 6.93L-7.07 7.07L-6.93 2.87L-10 0L-6.93 -2.87L-7.07 -7.07L-2.87 -6.93ZM-2.6 0a2.6 2.6 0 1 0 5.2 0a2.6 2.6 0 1 0 -5.2 0Z" fill="#E8501A" fillRule="evenodd" />
          </svg>
          <i />
        </div>
        <p className="yi-slogan">{t('intro.slogan')}</p>
      </div>
      <button ref={skipRef} type="button" className="yi-skip" onClick={() => leave(true)}>
        {t('intro.skip')}
      </button>
    </div>,
    document.body,
  );
}

/** Mounted once in Layout, before the page, so the decision precedes every other first-run flow. */
export function IntroHost() {
  const { pathname } = useLocation();
  decide(pathname);
  const active = useIntroActive();
  return active ? <IntroOverlay /> : null;
}
