import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth.value }));
import { setLang } from '../i18n';
import { firstRun } from '../lib/firstRun';
import { IntroHost, INTRO_MS, resetIntroForTests } from './Intro';
import { OnboardingHost } from './Onboarding';

const FLAG = 'yondo.intro.v1';
const intro = () => screen.queryByRole('dialog', { name: 'Yondo — ochiliş animatsiyasi' });
const guide = () => screen.queryByRole('dialog', { name: 'Yondo qanday işlaydi' });
const tick = (ms: number) => act(() => void vi.advanceTimersByTime(ms));

function app(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <div id="root">
        <button>behind</button>
        <IntroHost />
        <OnboardingHost />
      </div>
    </MemoryRouter>,
  );
}
// The overlay is portalled to <body>; the app container is the element with id="root".
const root = () => document.getElementById('root')!;

function reduced(on: boolean) {
  window.matchMedia = ((q: string) => ({ matches: on && q.includes('reduce'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} })) as never;
}

beforeEach(() => {
  vi.useFakeTimers();
  auth.value = { state: { status: 'anon' }, user: null };
  reduced(false);
});
afterEach(async () => {
  vi.useRealTimers();
  localStorage.clear();
  firstRun.forget('intro');
  firstRun.forget('onboarding.customer');
  resetIntroForTests();
  // @ts-expect-error jsdom has no matchMedia
  delete window.matchMedia;
  await setLang('uz');
});

describe('opening animation', () => {
  it('shows on the first visit to /, writes the flag at the START, announces itself, auto-closes in about 2.8 s', () => {
    app();
    expect(intro()).toBeInTheDocument();
    expect(localStorage.getItem(FLAG)).toBe('1');
    expect(intro()).toHaveAttribute('aria-modal', 'true');
    expect(intro()!.querySelector('.yi-stage')).toHaveAttribute('aria-hidden', 'true');
    expect(intro()!.querySelector('audio')).toBeNull();
    expect(root()).toHaveAttribute('inert');
    expect(screen.getByRole('button', { name: 'Ötkazib yuboriş' })).toHaveFocus();
    tick(INTRO_MS.full - 10);
    expect(intro()).toBeInTheDocument();
    tick(10 + INTRO_MS.fadeOut);
    expect(intro()).toBeNull();
    expect(root()).not.toHaveAttribute('inert');
  });

  it('does not play again after completion (new page load = reset module) nor on later navigation', () => {
    app();
    tick(3000);
    expect(intro()).toBeNull();
    resetIntroForTests();
    app();
    expect(intro()).toBeNull();
  });

  it.each([
    ['click on the overlay', () => fireEvent.pointerDown(intro()!)],
    ['the Skip button', () => fireEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }))],
    ['Enter', () => fireEvent.keyDown(document, { key: 'Enter' })],
    ['Escape', () => fireEvent.keyDown(document, { key: 'Escape' })],
  ])('skips instantly with %s and stays remembered', (_n, act1) => {
    app();
    act(() => void act1());
    tick(INTRO_MS.fadeFast + 5);
    expect(intro()).toBeNull();
    expect(localStorage.getItem(FLAG)).toBe('1');
  });

  it('moves focus to Skip and returns it to the previously focused element on close', () => {
    const before = document.createElement('button');
    document.body.appendChild(before);
    before.focus();
    render(
      <MemoryRouter>
        <IntroHost />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: 'Ötkazib yuboriş' })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Escape' });
    tick(INTRO_MS.fadeFast + 5);
    expect(before).toHaveFocus();
    before.remove();
  });

  it('reduced motion: static frame, about 0.6 s in total, still skippable', () => {
    reduced(true);
    app();
    expect(intro()).toHaveClass('yi-rm');
    tick(INTRO_MS.reduced - 10);
    expect(intro()).toBeInTheDocument();
    tick(10 + INTRO_MS.fadeFast);
    expect(intro()).toBeNull();
    expect(INTRO_MS.reduced + INTRO_MS.fadeFast).toBeLessThanOrEqual(650);
  });

  it('reduced motion is skippable too', () => {
    reduced(true);
    app();
    fireEvent.keyDown(document, { key: 'Escape' });
    tick(INTRO_MS.fadeFast + 5);
    expect(intro()).toBeNull();
  });

  it.each(['/login', '/terms', '/privacy', '/profile/abc', '/help'])('never on the deep link %s (and not written)', (path) => {
    app(path);
    expect(intro()).toBeNull();
    expect(localStorage.getItem(FLAG)).toBeNull();
    expect(root()).not.toHaveAttribute('inert');
  });

  it('storage failure: shown once per page load, never loops', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    const first = app();
    expect(intro()).toBeInTheDocument();
    tick(3000);
    expect(intro()).toBeNull();
    first.unmount();
    app(); // same page load (module state survives): no second run
    tick(100);
    expect(intro()).toBeNull();
    vi.restoreAllMocks();
  });

  it('uses the language of the app (ru, en)', async () => {
    await setLang('ru');
    app();
    expect(screen.getByRole('dialog', { name: 'Yondo — заставка при открытии' })).toBeInTheDocument();
    expect(screen.getByText('Yondo. Всегда рядом.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Пропустить' })).toBeInTheDocument();
  });
});

describe('sequencing with the first-run guide', () => {
  it('the guide waits for the intro: intro first, then the guide, and the intro never comes back', () => {
    app();
    expect(intro()).toBeInTheDocument();
    expect(guide()).toBeNull();
    tick(INTRO_MS.full + INTRO_MS.fadeOut + 10);
    expect(intro()).toBeNull();
    expect(guide()).toBeInTheDocument();
  });

  it('a skipped intro hands over to the guide at once', () => {
    app();
    fireEvent.keyDown(document, { key: 'Escape' });
    tick(INTRO_MS.fadeFast + 5);
    expect(guide()).toBeInTheDocument();
  });

  it('a returning visitor (intro seen) gets the guide straight away, without the intro', () => {
    firstRun.markSeen('intro');
    app();
    expect(intro()).toBeNull();
    expect(guide()).toBeInTheDocument();
  });
});
