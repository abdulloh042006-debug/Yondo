import { useEffect, useLayoutEffect, useSyncExternalStore } from 'react';
import { useLocation } from 'react-router-dom';
import { t } from '../i18n';
import { firstRun } from '../lib/firstRun';

/**
 * Opening animation, the app's half. Owner rule (2026-11-13): "the user must not feel that they are waiting for the
 * app to open, and the app must not make them wait on purpose".
 *
 * The animation itself is static markup, CSS and two small scripts in `index.html`, so it is on screen from the first
 * paint, while this code and the first data are still loading. That page decides the mode before anything is painted
 * (`<html data-intro="full | short | reduced | off">`): only at `/`; the full piece on a device's first visit, the
 * finished mark with a pulse on later visits, one still frame (once) under `prefers-reduced-motion`, nothing on deep
 * links or when `localStorage['yondo.intro.off'] = '1'`.
 *
 * This module takes the overlay over when the app has mounted and lets it leave as soon as the first screen is ready:
 * - READY = the first screen has its primary content, or its own error or gate (`introReady()`; the home page calls
 *   it when its first list request settles). Images and secondary data are not waited for.
 * - ready early            -> it leaves at once; on a first visit not before the mark has formed (`minFull`);
 * - ready late             -> the piece (about 2.5 s) is followed by a slow pulse until the app is ready;
 * - not ready after `cap`  -> it leaves anyway and the page shows its own loading state;
 * - offline                -> it leaves and the page shows its own "no connection" message with a retry button
 *                             (before this code has loaded, `index.html` shows that message itself);
 * - a tap or Escape        -> it leaves.
 * Leaving = the mark flies to the place where the app shell's logo sits (a FLIP: measured, then one transform) while
 * the ground clears; an opacity exit when that cannot be measured. Transform and opacity only, no audio, no library.
 */
export const INTRO_MS = { minFull: 700, fly: 620, shortFly: 460, reduced: 450, fade: 150, cap: 6000, slogan: 2000 } as const;
export const INTRO_OFF_KEY = 'yondo.intro.off';

type Mode = 'full' | 'short' | 'reduced';
declare global {
  interface Window {
    /** Written by index.html: the mode it chose and when; `app` tells its watchdog that the app has taken over. */
    __yondoIntro?: { mode: string; t0: number; app?: boolean; failed?: boolean };
  }
}

let active = false;
let ready = false;
let run: { check(): void; stop(): void; end(): void } | null = null;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => void listeners.delete(l);
};

/** The first screen has what it needs (or its own error, or a gate): the opening animation may leave. */
export function introReady(): void {
  if (ready) return;
  ready = true;
  run?.check();
}

/** True while the opening animation is on screen; other first-run flows can wait for it. */
export function useIntroActive(): boolean {
  return useSyncExternalStore(subscribe, () => active, () => false);
}

/** Tests only: forget this page load. */
export function resetIntroForTests(): void {
  run?.stop();
  run = null;
  active = false;
  ready = false;
  listeners.clear();
}

/** Where the app shell's logo sits, relative to the flying mark: one translate + scale. Null when it cannot be measured. */
function flightTo(mark: Element | null, from: Element | null): { dx: number; dy: number; s: number } | null {
  if (!mark || !from) return null;
  const a = from.getBoundingClientRect();
  const b = mark.getBoundingClientRect();
  if (a.width < 1 || b.width < 1) return null;
  return { dx: b.left + b.width / 2 - (a.left + a.width / 2), dy: b.top + b.height / 2 - (a.top + a.height / 2), s: b.width / a.width };
}

function start(el: HTMLElement, mode: Mode) {
  const html = document.documentElement;
  const root = document.getElementById('root');
  const fly = el.querySelector<HTMLElement>('.yi-fly');
  const page = window.__yondoIntro;
  const t0 = page?.t0 ?? performance.now();
  const timers: number[] = [];
  let leaving = false;
  let stopped = false;
  let ended = false;

  /** Time since index.html chose the mode. Wall clock on purpose: an animation's own clock stands still while the
      page draws no frames (a background tab), and the exit must never depend on that. */
  const elapsed = (): number => performance.now() - t0;
  const clear = () => {
    timers.forEach(window.clearTimeout);
    timers.length = 0;
  };
  /** The app is usable from the moment the exit starts: the overlay no longer takes pointer events then. */
  const release = () => {
    root?.removeAttribute('inert');
    root?.removeAttribute('aria-busy');
  };
  const end = () => {
    if (ended) return;
    ended = true;
    stop();
    el.remove();
    release();
    html.classList.remove('yi-on');
    html.dataset.intro = 'done';
    active = false;
    emit();
  };
  /** A plain opacity exit: a tap, Escape, the still frame, or a header that cannot be measured. */
  const fade = () => {
    if (leaving) return;
    leaving = true;
    clear();
    release();
    html.classList.remove('yi-on');
    el.classList.add('yi-fade');
    timers.push(window.setTimeout(end, INTRO_MS.fade));
  };
  /** The mark flies to the shell's logo while the ground clears. */
  const land = () => {
    if (leaving) return;
    const to = mode === 'reduced' ? null : flightTo(document.querySelector('.brand .brand-mark'), fly);
    if (!to || !fly) return fade();
    leaving = true;
    clear();
    release();
    const ms = mode === 'short' ? INTRO_MS.shortFly : INTRO_MS.fly;
    // On an early exit the mark is still in the middle of the frame (its wrapper is shifted until the wordmark comes
    // out). That shift is frozen where it is and the flight is aimed so that the visible mark, not its box, arrives.
    const slide = el.querySelector('.yi-slide');
    const sx = slide ? slide.getBoundingClientRect().left - fly.getBoundingClientRect().left : 0;
    to.dx -= to.s * sx;
    fly.style.setProperty('--yi-sx', `${sx.toFixed(1)}px`);
    fly.style.setProperty('--yi-dx', `${to.dx.toFixed(1)}px`);
    fly.style.setProperty('--yi-dy', `${to.dy.toFixed(1)}px`);
    fly.style.setProperty('--yi-ds', to.s.toFixed(4));
    el.classList.add('yi-land');
    // hand over to the real logo just before the flight ends, then remove the overlay
    timers.push(window.setTimeout(() => html.classList.remove('yi-on'), ms - 140), window.setTimeout(end, ms));
  };
  const min = mode === 'full' ? INTRO_MS.minFull : mode === 'reduced' ? INTRO_MS.reduced : 0;
  /** Leave as soon as there is a reason to, but not before the mark is there. Never waits on purpose beyond that. */
  const check = () => {
    if (leaving || stopped) return;
    const e = elapsed();
    if (!(ready || e >= INTRO_MS.cap || navigator.onLine === false)) return;
    if (e < min) return void timers.push(window.setTimeout(check, min - e + 4));
    land();
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') fade();
  };
  function stop() {
    stopped = true;
    clear();
    window.removeEventListener('offline', check);
    document.removeEventListener('keydown', onKey);
    el.removeEventListener('pointerdown', fade);
  }

  // Take over: the page's own watchdog steps back, the first run is remembered (a refresh half-way does not replay
  // the full piece), and the app under the overlay cannot be reached until it has left.
  if (page) page.app = true;
  const msg = el.querySelector<HTMLElement>('.yi-msg');
  if (msg && !msg.hidden) {
    msg.hidden = true;
    el.classList.remove('yi-failed');
    el.setAttribute('aria-hidden', 'true');
  }
  firstRun.markSeen('intro');
  root?.setAttribute('inert', '');
  root?.setAttribute('aria-busy', 'true');
  if (mode !== 'reduced') html.classList.add('yi-on');
  if (mode !== 'short') {
    const slogan = el.querySelector('.yi-slogan');
    if (slogan) slogan.textContent = t('intro.slogan');
    if (mode === 'reduced') el.classList.add('yi-say');
    else timers.push(window.setTimeout(() => el.classList.add('yi-say'), Math.max(0, INTRO_MS.slogan - elapsed())));
  }
  timers.push(window.setTimeout(check, Math.max(0, INTRO_MS.cap - elapsed()) + 4));
  window.addEventListener('offline', check);
  document.addEventListener('keydown', onKey);
  el.addEventListener('pointerdown', fade);
  active = true;
  emit();
  return {
    check,
    /** React is cleaning the effect up: a started exit is finished at once, anything else is only paused (see IntroHost). */
    stop: () => (leaving ? end() : stop()),
    end,
  };
}

/** Mounted once in Layout. Renders nothing: the overlay is the `#yi` element of index.html. */
export function IntroHost() {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    const el = document.getElementById('yi');
    const mode = document.documentElement.dataset.intro;
    if (!el) return;
    if (mode !== 'full' && mode !== 'short' && mode !== 'reduced') return void el.remove();
    run = start(el, mode);
    run.check();
    return () => {
      const mine = run;
      run = null;
      if (!mine) return;
      mine.stop();
      // StrictMode runs the effect again at once and takes the overlay over anew. If nothing does (the shell crashed,
      // was unmounted, or is hidden by a Suspense boundary), the overlay must not stay on screen for ever.
      window.setTimeout(() => {
        if (run === null) mine.end();
      }, 0);
    };
  }, []);
  // Anything but the home page has no reason to keep it.
  useEffect(() => {
    if (pathname !== '/') introReady();
  }, [pathname]);
  return null;
}
