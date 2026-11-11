import { afterEach, expect, it, vi } from 'vitest';
import { applySavedTheme } from './theme';

afterEach(() => vi.unstubAllGlobals());

it('turns CSS transitions off while a theme change is drawn, then back on', async () => {
  const frames: FrameRequestCallback[] = [];
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb));
  const root = document.documentElement;
  applySavedTheme();
  frames.splice(0).forEach((cb) => cb(0));
  frames.splice(0).forEach((cb) => cb(0));
  expect(root.dataset.themeSwitching).toBeUndefined();

  root.dataset.theme = 'yondo-tun'; // a change from anywhere (Settings, tests, devtools)
  await Promise.resolve(); // the observer runs as a microtask, before the browser restyles
  expect(root.dataset.themeSwitching).toBe('');
  frames.splice(0).forEach((cb) => cb(0)); // frame 1: new colours drawn without transitions
  expect(root.dataset.themeSwitching).toBe('');
  frames.splice(0).forEach((cb) => cb(0)); // frame 2: transitions back on
  expect(root.dataset.themeSwitching).toBeUndefined();
});
