import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { t } from '../../i18n';
import { serviceLabel } from '../../lib/labels';
import { useResource } from '../../lib/useResource';
import { usePublicPhotoUrl } from '../../pages/companionParts';
import { ReportStory } from './ReportStory';
import { RoundPhoto } from './RoundPhoto';
import { ageMinutes, autoAdvanceMs, clock, dayOffset, markSeen, prefersReducedMotion, type Ring, type Slide } from './storyState';

const TICK = 100;
const HOLD_MS = 250;

function ageLabel(iso: string): string {
  const m = ageMinutes(iso);
  if (m < 1) return t('stories.agoNow');
  if (m < 60) return t('stories.agoMin', { n: m });
  return t('stories.agoHour', { n: Math.min(Math.floor(m / 60), 99) });
}

function windowLabel(w: { starts_at: string; ends_at: string }): string {
  const d = dayOffset(w.starts_at);
  const day = d === 0 ? `${t('stories.today')} ` : d === 1 ? `${t('stories.tomorrow')} ` : '';
  return `${day}${clock(w.starts_at)}–${clock(w.ends_at)}`;
}

/** Full-bleed 9:16 on phones, a 360 px card centred on desktop. Public: no sign-in, and no viewer is ever recorded. */
export function StoryViewer({ ring, opener, onClose }: { ring: Ring; opener?: HTMLElement | null; onClose: () => void }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const res = useResource((signal) => api.get<Slide[]>(`/discovery/companions/${ring.profile_id}/stories`, { anonymous: true, signal }), [ring.profile_id]);
  const slides = res.data ?? [];
  const [reduced] = useState(prefersReducedMotion);
  const [i, setI] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [held, setHeld] = useState(false);
  const [pressing, setPressing] = useState(false);
  const [reporting, setReporting] = useState(false);
  const acc = useRef(0);
  const holdTimer = useRef<number>(undefined);
  const holdFired = useRef(false);
  const swipe = useRef<{ x: number; y: number } | null>(null);
  const root = useRef<HTMLDivElement>(null);

  const slide: Slide | undefined = slides[Math.min(i, Math.max(slides.length - 1, 0))];
  const ms = slide ? autoAdvanceMs(slide.kind, reduced) : null;
  const paused = held || pressing || reporting || !slide;

  const go = (n: number) => {
    if (n >= slides.length) return onClose();
    acc.current = 0;
    setElapsed(0);
    setI(Math.max(n, 0));
  };
  const goEvent = useRefCallback(go);

  // Viewing counts as seen on this device only (nothing is sent to the server).
  useEffect(() => {
    if (slides.length) markSeen(ring.profile_id, ring.latest_at);
  }, [slides.length, ring.profile_id, ring.latest_at]);

  // Auto-advance: none at all under prefers-reduced-motion (ms === null), and none while paused.
  useEffect(() => {
    if (ms === null || paused) return;
    const id = window.setInterval(() => {
      acc.current += TICK;
      setElapsed(acc.current);
      if (acc.current >= ms) goEvent(i + 1);
    }, TICK);
    return () => window.clearInterval(id);
  }, [ms, paused, i, goEvent]);

  // Keyboard, focus trap, scroll lock, focus return to the ring.
  useEffect(() => {
    const el = root.current;
    const focusables = () => Array.from(el?.querySelectorAll<HTMLElement>('button:not([tabindex="-1"]), [href], input, select, textarea') ?? []).filter((x) => !x.hasAttribute('disabled'));
    (el?.querySelector<HTMLElement>('[data-autofocus]') ?? focusables()[0] ?? el)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (reporting) return; // the report sheet owns the keyboard while it is open
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowRight') goEvent(i + 1);
      else if (e.key === 'ArrowLeft') goEvent(i - 1);
      else if (e.key === 'Tab') {
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
    return () => document.removeEventListener('keydown', onKey);
  }, [reporting, i, onClose, goEvent]);
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
      opener?.focus?.();
    };
  }, [opener]);

  const startHold = () => {
    holdFired.current = false;
    window.clearTimeout(holdTimer.current);
    holdTimer.current = window.setTimeout(() => {
      holdFired.current = true;
      setPressing(true);
    }, HOLD_MS);
  };
  const endHold = () => {
    window.clearTimeout(holdTimer.current);
    setPressing(false);
  };
  useEffect(() => () => window.clearTimeout(holdTimer.current), []);
  const tap = (n: number) => {
    if (holdFired.current) {
      holdFired.current = false; // the press was a hold, not a tap
      return;
    }
    go(n);
  };

  const carrot = slide?.kind === 'note' && !slide.photo;
  const book = () => {
    const target = `/c/${ring.profile_id}${slide?.service ? `?service=${slide.service.id}` : ''}`;
    onClose();
    navigate(target);
  };
  const total = slides.length;

  return createPortal(
    <div className="st-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={root}
        role="dialog"
        aria-modal="true"
        aria-label={ring.display_name}
        tabIndex={-1}
        className={`st-card${carrot ? ' nt' : ''}`}
        onPointerDown={(e) => (swipe.current = { x: e.clientX, y: e.clientY })}
        onPointerUp={(e) => {
          const s = swipe.current;
          swipe.current = null;
          if (s && e.clientY - s.y > 90 && Math.abs(e.clientX - s.x) < 60) onClose();
        }}
      >
        {slide && <SlideFace key={slide.id} profileId={ring.profile_id} slide={slide} />}

        <div className="st-prog" role="img" aria-label={t('stories.progress', { n: Math.min(i + 1, Math.max(total, 1)), total: Math.max(total, 1) })}>
          {Array.from({ length: Math.max(total, 1) }, (_, j) => {
            const pct = j < i ? 100 : j === i ? (ms === null ? 100 : Math.min(100, (elapsed / ms) * 100)) : 0;
            return <i key={j} className={j === i ? 'cur' : undefined}><b style={{ width: `${pct}%` }} /></i>;
          })}
        </div>

        <div className="st-head">
          <RoundPhoto profileId={ring.profile_id} photo={ring.photo} size={32} />
          <span className="st-hname">
            <b>{ring.display_name}</b>
            {ring.verified === true && <span className="tag st-vtag">{t('card.verified')}</span>}
            {slide && <span className="st-age">{ageLabel(slide.created_at)}</span>}
          </span>
          <span className="st-sp" />
          {ms !== null && (
            <button type="button" className="st-ib" aria-pressed={held} aria-label={held ? t('stories.resume') : t('stories.pause')} onClick={() => setHeld((h) => !h)}>
              <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
                {held ? <path d="M6 3.5l10 6.5-10 6.5z" fill="currentColor" /> : <path d="M5.5 3.5h3.2v13H5.5zM11.3 3.5h3.2v13h-3.2z" fill="currentColor" />}
              </svg>
            </button>
          )}
          <button type="button" className="st-ib" data-autofocus aria-label={t('stories.close')} onClick={onClose}>
            <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><path d="M4.5 4.5l11 11M15.5 4.5l-11 11" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" fill="none" /></svg>
          </button>
        </div>

        {res.loading && !res.data && (
          <div className="st-state"><span className="spinner" aria-hidden="true" /><span className="sr-only">{t('common.loading')}…</span></div>
        )}
        {res.error && <div className="st-state" role="alert"><p>{res.error.message}</p></div>}
        {res.data && total === 0 && <div className="st-state"><p>{t('stories.empty')}</p></div>}

        {slide && (
          <>
            <button type="button" className="st-zone st-zl" tabIndex={-1} aria-label={t('stories.prev')} onPointerDown={startHold} onPointerUp={endHold} onPointerLeave={endHold} onPointerCancel={endHold} onClick={() => tap(i - 1)} />
            <button type="button" className="st-zone st-zr" tabIndex={-1} aria-label={t('stories.next')} onPointerDown={startHold} onPointerUp={endHold} onPointerLeave={endHold} onPointerCancel={endHold} onClick={() => tap(i + 1)} />
          </>
        )}

        <div className="st-foot">
          {slide && (
            <button type="button" className="st-cta" onClick={book}>
              {slide.kind === 'availability' ? t('stories.book') : t('stories.profile')}
            </button>
          )}
          {slide && (
            <button type="button" className="st-flag" onClick={() => setReporting(true)}>
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false"><path d="M3.5 14V2.5M3.5 3h8l-1.8 3 1.8 3h-8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              {t('stories.report')}
            </button>
          )}
        </div>
      </div>
      {reporting && slide && <ReportStory storyId={slide.id} signedIn={!!user} onClose={() => setReporting(false)} onSignIn={() => { setReporting(false); onClose(); navigate('/login'); }} />}
    </div>,
    document.body,
  );
}

/** Keeps a stable function identity that always calls the latest closure (so timers/listeners never go stale). */
function useRefCallback<A extends unknown[]>(fn: (...args: A) => void): (...args: A) => void {
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  return useCallback((...args: A) => ref.current(...args), []);
}

function SlideFace({ profileId, slide }: { profileId: string; slide: Slide }) {
  const url = usePublicPhotoUrl(profileId, slide.photo);
  const windows = (slide.windows ?? []).slice(0, 3);
  return (
    <>
      {url && <img className="st-img" src={url} alt="" />}
      {slide.photo && <span className="st-scrim" aria-hidden="true" />}
      <div className="st-body" key={slide.id}>
        {slide.kind === 'note' ? (
          <>
            <p className="st-kind">{t('stories.kind.note')}</p>
            <p className="st-note">{slide.caption}</p>
          </>
        ) : (
          <>
            <p className="st-kind">{t('stories.kind.availability')}</p>
            {slide.service && <h3>{serviceLabel(slide.service.service_code)}</h3>}
            {slide.caption && <p>{slide.caption}</p>}
            {windows.length > 0 && (
              <ul className="st-win" aria-label={t('stories.windows')}>
                {windows.map((w) => <li key={w.starts_at}>{windowLabel(w)}</li>)}
              </ul>
            )}
          </>
        )}
      </div>
    </>
  );
}
