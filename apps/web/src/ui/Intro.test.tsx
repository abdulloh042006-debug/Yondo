import { act, fireEvent, render } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toUz1995 } from '../i18n';
import { en } from '../i18n/en';
import { introFallbackText } from '../i18n/introText';
import { ru } from '../i18n/ru';
import { uz } from '../i18n/uz';
import { firstRun } from '../lib/firstRun';
import { INTRO_MS, INTRO_OFF_KEY, IntroHost, introReady, resetIntroForTests } from './Intro';

// The real page: its markup and its two inline scripts are what runs here (vitest's cwd is apps/web).
const PAGE = readFileSync('index.html', 'utf8');
const page = new DOMParser().parseFromString(PAGE, 'text/html');
const scriptOf = (id: string) => page.getElementById(id)!.textContent!;
const KEY = firstRun.keyOf('intro');
const html = document.documentElement;
let root: HTMLElement;
let added: Array<[string, EventListenerOrEventListenerObject, boolean | AddEventListenerOptions | undefined]> = [];

/** What the browser does before any app code runs: parse index.html and run its inline scripts. */
function load(path = '/') {
  window.history.replaceState(null, '', path);
  root = document.createElement('div');
  root.id = 'root';
  document.body.append(root, document.importNode(page.getElementById('yi')!, true));
  const add = window.addEventListener.bind(window);
  const spy = vi.spyOn(window, 'addEventListener').mockImplementation((type: string, fn: EventListenerOrEventListenerObject, opts?: boolean | AddEventListenerOptions) => {
    added.push([type, fn, opts]);
    add(type, fn, opts);
  });
  new Function(scriptOf('yi-decide'))();
  new Function(scriptOf('yi-watch').replace('"__YONDO_INTRO_TEXT__"', JSON.stringify(introFallbackText())))();
  spy.mockRestore();
}
/** The app arrives: the shell (with the header logo the mark flies to) mounts into #root. */
const mount = (path = '/', strict = false) => {
  const shell = (
    <MemoryRouter initialEntries={[path]}>
      <a className="brand" href="/">
        <svg className="brand-mark" />
      </a>
      <IntroHost />
    </MemoryRouter>
  );
  return render(strict ? <StrictMode>{shell}</StrictMode> : shell, { container: root });
};
const overlay = () => document.getElementById('yi');
const mode = () => html.dataset.intro;
const tick = (ms: number) => act(() => void vi.advanceTimersByTime(ms));
/** jsdom has no layout: give the flying mark and the shell's logo real boxes. */
const layout = (slideOffset = 0) =>
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    if (this.classList.contains('brand-mark')) return new DOMRect(20, 14, 26, 26);
    if (this.classList.contains('yi-fly')) return new DOMRect(100, 300, 104, 104);
    if (this.classList.contains('yi-slide')) return new DOMRect(100 + slideOffset, 300, 104, 104);
    return new DOMRect(0, 0, 0, 0);
  });
const reducedMotion = () => vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('reduce'), addEventListener() {}, removeEventListener() {} }));
const scriptFails = () => {
  const s = document.createElement('script');
  document.body.append(s);
  s.dispatchEvent(new Event('error'));
  s.remove();
};

beforeEach(() => {
  vi.useFakeTimers();
  for (const k of [INTRO_OFF_KEY, 'yondo.theme', 'yondo.lang']) localStorage.removeItem(k);
  localStorage.setItem('yondo.uzAlphabet', '2026'); // as in test-setup.ts
  firstRun.forget('intro');
  resetIntroForTests();
});
afterEach(() => {
  resetIntroForTests();
  added.forEach(([type, fn, opts]) => window.removeEventListener(type, fn, opts));
  added = [];
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
  html.classList.remove('yi-on');
  html.removeAttribute('data-intro');
  html.removeAttribute('data-intro-night');
  delete window.__yondoIntro;
});

describe('opening animation: what index.html decides before the first paint', () => {
  it('the full piece on a first visit at /, the short form later, nothing on deep links or when switched off', () => {
    load();
    expect(mode()).toBe('full');
    expect(window.__yondoIntro).toMatchObject({ mode: 'full' });

    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    localStorage.setItem(KEY, '1');
    load();
    expect(mode()).toBe('short');

    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    load('/login');
    expect(mode()).toBe('off');

    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    localStorage.setItem(INTRO_OFF_KEY, '1');
    load();
    expect(mode()).toBe('off');
  });

  it('prefers-reduced-motion: one still frame on the first visit, nothing later', () => {
    reducedMotion();
    load();
    expect(mode()).toBe('reduced');
    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    localStorage.setItem(KEY, '1');
    load();
    expect(mode()).toBe('off');
  });

  it('blocked storage counts as a first visit and never throws; a night theme gets the ink ground', () => {
    localStorage.setItem('yondo.theme', 'yondo-tun');
    load();
    expect(html.hasAttribute('data-intro-night')).toBe(true);
    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    html.removeAttribute('data-intro-night');
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    expect(() => load()).not.toThrow();
    expect(mode()).toBe('full');
    expect(html.hasAttribute('data-intro-night')).toBe(false);
  });

  it('uses the same storage keys as the app, the official wordmark, and has no skip button', () => {
    for (const key of [KEY, INTRO_OFF_KEY, 'yondo.theme', 'yondo.lang', 'yondo.uzAlphabet']) expect(PAGE).toContain(`'${key}'`);
    const brand = readFileSync('../../marketing/ad-video/wordmark.svgfrag', 'utf8');
    expect(brand).toContain(page.querySelector('.yi-wm path')!.getAttribute('d')!);
    expect([...page.querySelectorAll('#yi button')].map((b) => b.id)).toEqual(['yi-retry']); // only the fallback's retry
  });
});

describe('opening animation: the app takes over and lets it leave when the first screen is ready', () => {
  it('takes over: the app underneath is inert, the first run is remembered, the page watchdog steps back', () => {
    load();
    mount();
    expect(overlay()).toBeInTheDocument();
    expect(root).toHaveAttribute('inert');
    expect(root).toHaveAttribute('aria-busy', 'true');
    expect(html).toHaveClass('yi-on'); // the shell's own logo waits for the flying one
    expect(localStorage.getItem(KEY)).toBe('1'); // a refresh half-way does not replay the full piece
    expect(window.__yondoIntro?.app).toBe(true);
    expect(overlay()!.querySelector('.yi-slogan')).toHaveTextContent('doim yoningda');
    expect(overlay()).toHaveAttribute('aria-hidden', 'true');
  });

  it('ready within half a second: it does not wait for the 2.5 s piece, only for the mark to form', () => {
    layout();
    load();
    mount();
    tick(300);
    act(() => introReady());
    expect(overlay()).not.toHaveClass('yi-land');
    tick(INTRO_MS.minFull - 300 - 1);
    expect(overlay()).not.toHaveClass('yi-land');
    tick(6);
    const el = overlay()!;
    expect(el).toHaveClass('yi-land');
    expect(root).not.toHaveAttribute('inert'); // usable from the moment the exit starts
    const fly = el.querySelector<HTMLElement>('.yi-fly')!;
    expect(fly.style.getPropertyValue('--yi-sx')).toBe('0.0px');
    expect(fly.style.getPropertyValue('--yi-dx')).toBe('-119.0px'); // logo centre (33, 27) - mark centre (152, 352)
    expect(fly.style.getPropertyValue('--yi-dy')).toBe('-325.0px');
    expect(fly.style.getPropertyValue('--yi-ds')).toBe('0.2500');
    tick(INTRO_MS.fly - 140);
    expect(html).not.toHaveClass('yi-on'); // hand-over to the real logo just before the end
    expect(overlay()).toBeInTheDocument();
    tick(140);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    expect(root).not.toHaveAttribute('aria-busy');
    expect(mode()).toBe('done');
  });

  it('an early exit starts from where the mark is (still in the middle of the frame), so nothing jumps', () => {
    layout(122); // the wordmark has not come out yet: the mark's wrapper is still shifted 122 px to the right
    load();
    mount();
    tick(INTRO_MS.minFull);
    act(() => introReady());
    const fly = overlay()!.querySelector<HTMLElement>('.yi-fly')!;
    expect(fly.style.getPropertyValue('--yi-sx')).toBe('122.0px'); // frozen where it is ...
    expect(fly.style.getPropertyValue('--yi-dx')).toBe('-149.5px'); // ... and the flight makes up for it: -119 - 0.25 * 122
    expect(PAGE).toMatch(/\.yi-land \.yi-slide \{\s*animation: none;\s*transform: translateX\(var\(--yi-sx, 0px\)\);/);
  });

  it('ready in the middle of the piece: it leaves at that moment', () => {
    layout();
    load();
    mount();
    tick(1500);
    expect(overlay()).not.toHaveClass('yi-land');
    act(() => introReady());
    expect(overlay()).toHaveClass('yi-land');
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('a slow start: the piece and its pulse stay while the app loads, then leave at the cap at the latest', () => {
    layout();
    load();
    mount();
    tick(INTRO_MS.slogan - 1);
    expect(overlay()).not.toHaveClass('yi-say');
    tick(1);
    expect(overlay()).toHaveClass('yi-say'); // the slogan comes in on time
    tick(INTRO_MS.cap - INTRO_MS.slogan - 1);
    expect(overlay()).toBeInTheDocument();
    expect(overlay()).not.toHaveClass('yi-land');
    tick(6);
    expect(overlay()).toHaveClass('yi-land'); // never an endless animation: the page shows its own loading state
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
  });

  it('the connection drops: it leaves and the app shows its own message (not the page fallback)', () => {
    layout();
    load();
    mount();
    tick(1000);
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    act(() => void window.dispatchEvent(new Event('offline')));
    expect(overlay()).toHaveClass('yi-land');
    expect(document.getElementById('yi-msg')).toHaveAttribute('hidden');
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('later visits: the finished mark leaves the moment the app is ready, and waits when it is not', () => {
    layout();
    localStorage.setItem(KEY, '1');
    load();
    mount();
    tick(3000);
    expect(overlay()).toBeInTheDocument();
    expect(overlay()).not.toHaveClass('yi-land');
    act(() => introReady());
    expect(overlay()).toHaveClass('yi-land');
    tick(INTRO_MS.shortFly);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('later visits, app ready at once: no minimum time', () => {
    layout();
    localStorage.setItem(KEY, '1');
    load();
    act(() => introReady());
    mount();
    expect(overlay()).toHaveClass('yi-land');
    tick(INTRO_MS.shortFly);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('prefers-reduced-motion: the still frame shows briefly, nothing flies, an opacity exit', () => {
    layout();
    reducedMotion();
    load();
    mount();
    expect(html).not.toHaveClass('yi-on');
    expect(overlay()).toHaveClass('yi-say');
    act(() => introReady());
    tick(INTRO_MS.reduced - 1);
    expect(overlay()).not.toHaveClass('yi-fade');
    tick(6);
    expect(overlay()).toHaveClass('yi-fade');
    expect(overlay()).not.toHaveClass('yi-land');
    tick(INTRO_MS.fade);
    expect(overlay()).not.toBeInTheDocument();
  });

  it.each([
    ['Escape', () => fireEvent.keyDown(document, { key: 'Escape' })],
    ['a tap', () => fireEvent.pointerDown(overlay()!)],
  ])('%s dismisses it at any moment, ready or not', (_name, dismiss) => {
    layout();
    load();
    mount();
    tick(400);
    dismiss();
    expect(overlay()).toHaveClass('yi-fade');
    expect(html).not.toHaveClass('yi-on');
    tick(INTRO_MS.fade);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    tick(INTRO_MS.cap); // nothing brings it back
    expect(overlay()).not.toBeInTheDocument();
  });

  it('when the header logo cannot be measured it leaves with the fade instead of a flight', () => {
    load(); // jsdom: every box is 0 x 0
    mount();
    tick(1000);
    act(() => introReady());
    expect(overlay()).toHaveClass('yi-fade');
    tick(INTRO_MS.fade);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('deep links and the switch-off key: the element is removed, the app is never inert, the first run is not spent', () => {
    load('/login');
    mount('/login');
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    expect(localStorage.getItem(KEY)).toBeNull();

    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    resetIntroForTests();
    localStorage.setItem(INTRO_OFF_KEY, '1');
    load();
    mount();
    expect(overlay()).not.toBeInTheDocument();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('blocked storage: it plays, never throws and leaves normally', () => {
    layout();
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    load();
    expect(() => mount()).not.toThrow();
    tick(1000);
    act(() => introReady());
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
  });

  it('React StrictMode (effects run twice): one take-over, one exit, nothing left behind', () => {
    layout();
    load();
    mount('/', true);
    expect(root).toHaveAttribute('inert');
    tick(1000);
    act(() => introReady());
    expect(overlay()).toHaveClass('yi-land');
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    expect(html).not.toHaveClass('yi-on');
  });

  it('if the shell goes away before the exit (a crash, an unmount) the overlay does not stay for ever', () => {
    layout();
    load();
    const shell = mount();
    tick(1000);
    expect(overlay()).toBeInTheDocument();
    shell.unmount();
    tick(1);
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    expect(root).not.toHaveAttribute('aria-busy');
    expect(html).not.toHaveClass('yi-on');
    expect(mode()).toBe('done');
  });

  it('if the shell unmounts during the exit the app is not left inert', () => {
    layout();
    load();
    const shell = mount();
    tick(1000);
    act(() => introReady());
    expect(overlay()).toHaveClass('yi-land');
    shell.unmount();
    expect(overlay()).not.toBeInTheDocument();
    expect(root).not.toHaveAttribute('inert');
    expect(html).not.toHaveClass('yi-on');
  });
});

describe('opening animation: the app code never arrives (index.html alone)', () => {
  const message = () => document.getElementById('yi-msg')!;

  it.each([
    ['uz', '2026', uz['err.network_error'], uz['common.retry']],
    ['uz', '1995', toUz1995(uz['err.network_error']), toUz1995(uz['common.retry'])],
    ['ru', '2026', ru['err.network_error'], ru['common.retry']],
    ['en', '2026', en['err.network_error'], en['common.retry']],
  ])('a failed script shows "no connection" and a retry button, in %s (%s)', (lang, alphabet, text, retry) => {
    localStorage.setItem('yondo.lang', lang);
    localStorage.setItem('yondo.uzAlphabet', alphabet);
    load();
    expect(message()).toHaveAttribute('hidden');
    scriptFails();
    expect(message()).not.toHaveAttribute('hidden');
    expect(message()).toHaveAttribute('role', 'alert');
    expect(document.getElementById('yi-msg-text')).toHaveTextContent(text);
    expect(document.getElementById('yi-retry')).toHaveTextContent(retry);
    expect(document.getElementById('yi-retry')!.onclick).toBeTypeOf('function');
    expect(overlay()).toHaveClass('yi-failed'); // the pulse stops
    expect(overlay()).not.toHaveAttribute('aria-hidden');
  });

  it('twelve seconds without the app, or going offline, shows it too: never an endless animation', () => {
    load();
    tick(11999);
    expect(message()).toHaveAttribute('hidden');
    tick(1);
    expect(message()).not.toHaveAttribute('hidden');

    document.querySelectorAll('#root, #yi').forEach((n) => n.remove());
    load();
    expect(message()).toHaveAttribute('hidden');
    act(() => void window.dispatchEvent(new Event('offline')));
    expect(message()).not.toHaveAttribute('hidden');
  });

  it('the app arrives after all: the message goes away and the app drives the exit', () => {
    layout();
    load();
    scriptFails();
    expect(message()).not.toHaveAttribute('hidden');
    mount();
    expect(message()).toHaveAttribute('hidden');
    expect(overlay()).not.toHaveClass('yi-failed');
    expect(overlay()).toHaveAttribute('aria-hidden', 'true');
    scriptFails(); // later failures belong to the app
    expect(message()).toHaveAttribute('hidden');
    tick(1000);
    act(() => introReady());
    tick(INTRO_MS.fly);
    expect(overlay()).not.toBeInTheDocument();
  });

  it('does nothing when the animation is off', () => {
    load('/login');
    scriptFails();
    tick(12000);
    expect(message()).toHaveAttribute('hidden');
  });

  it('its texts come from the dictionaries', () => {
    const x = introFallbackText();
    expect(x.uz26).toEqual({ m: uz['err.network_error'], r: uz['common.retry'] });
    expect(x.uz95).toEqual({ m: toUz1995(uz['err.network_error']), r: toUz1995(uz['common.retry']) });
    expect(x.ru).toEqual({ m: ru['err.network_error'], r: ru['common.retry'] });
    expect(x.en).toEqual({ m: en['err.network_error'], r: en['common.retry'] });
    expect(PAGE).toContain('"__YONDO_INTRO_TEXT__"'); // vite.config.ts writes them in
  });
});
