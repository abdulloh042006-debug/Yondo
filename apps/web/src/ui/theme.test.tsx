import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { applySavedTheme, applyTheme, THEMES, ThemePicker } from './theme';

const css = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const REQUIRED = ['--c-bg', '--c-fg', '--c-muted', '--c-surface', '--c-primary', '--c-on-primary', '--c-line', '--c-chip', '--c-scrim', '--c-on-media', '--f-display', '--f-sans'];

/** Declarations of every rule whose selector list contains exactly `selector` (so `[data-theme='x'] .btn` is not counted). */
function declarations(selector: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [, selectors, body] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!selectors.split(',').some((s) => s.trim() === selector)) continue;
    for (const [, name, value] of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[name] = value.trim();
  }
  return out;
}
const metaColor = () => document.querySelector('meta[name="theme-color"]')?.getAttribute('content');

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.removeAttribute('data-theme-switching');
  document.head.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.remove());
  vi.restoreAllMocks();
});

describe('theme registry vs styles.css', () => {
  it.each(THEMES.map((th) => th.id))('%s defines the whole token contract', (id) => {
    const decl = declarations(`[data-theme='${id}']`);
    for (const token of REQUIRED) expect(decl[token], `${id}: ${token}`).toBeTruthy();
  });

  it.each(THEMES)('browser chrome colour of $id equals its --c-bg', (th) => {
    const bg = declarations(`[data-theme='${th.id}']`)['--c-bg'];
    expect(th.chrome.toLowerCase()).toBe(bg.toLowerCase());
  });

  it('has the transition guard used while switching', () => {
    expect(css).toMatch(/\[data-theme-switching\] \*[^{]*\{[^}]*transition:\s*none\s*!important/);
  });
});

describe('applyTheme', () => {
  it('sets data-theme and the matching <meta name="theme-color"> (created when missing)', () => {
    expect(metaColor()).toBeUndefined();
    applyTheme('yondo-tun');
    expect(document.documentElement.dataset.theme).toBe('yondo-tun');
    expect(metaColor()).toBe('#111111');
    applyTheme('yondo');
    expect(metaColor()).toBe('#f5f2ec');
    expect(document.querySelectorAll('meta[name="theme-color"]')).toHaveLength(1);
  });

  it('computes the new styles while transitions are off, then re-enables them', () => {
    let during: { theme?: string; switching: boolean } | undefined;
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockImplementation(function (this: HTMLElement) {
      if (this === document.documentElement) during = { theme: this.dataset.theme, switching: 'themeSwitching' in this.dataset };
      return 0;
    });
    applyTheme('stone');
    expect(during).toEqual({ theme: 'stone', switching: true });
    expect(document.documentElement.hasAttribute('data-theme-switching')).toBe(false);
  });

  it('applySavedTheme: stored choice wins, unknown or missing falls back to Gul, and the meta follows', () => {
    applySavedTheme();
    expect(document.documentElement.dataset.theme).toBe('gul');
    expect(metaColor()).toBe('#f3ebdf');
    localStorage.setItem('yondo.theme', 'yondo-tun');
    applySavedTheme();
    expect(document.documentElement.dataset.theme).toBe('yondo-tun');
    expect(metaColor()).toBe('#111111');
    localStorage.setItem('yondo.theme', 'neon');
    applySavedTheme();
    expect(document.documentElement.dataset.theme).toBe('gul');
  });

  it('the Settings picker switches theme, persists it and updates the browser colour', async () => {
    applySavedTheme();
    render(<ThemePicker />);
    await userEvent.click(screen.getByRole('button', { name: /Yondo tungi mavzusi/ }));
    expect(document.documentElement.dataset.theme).toBe('yondo-tun');
    expect(localStorage.getItem('yondo.theme')).toBe('yondo-tun');
    expect(metaColor()).toBe('#111111');
    expect(screen.getByRole('button', { name: /Yondo tungi mavzusi/ })).toHaveAttribute('aria-pressed', 'true');
  });
});
