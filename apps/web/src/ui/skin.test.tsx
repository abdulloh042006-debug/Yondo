import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../i18n';
import { applyTheme, setSkin, setTheme, ThemePicker } from './theme';
import { BrandMark } from './Brand';
import { Icon } from './Icon';
import { SKINS, skinOfTheme } from './skin';
import { SkinPicker } from './SkinPickers';

afterEach(async () => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.head.querySelectorAll('meta[name="theme-color"], link').forEach((m) => m.remove());
  vi.restoreAllMocks();
  await setLang('uz');
});

describe('skin registry', () => {
  it('maps theme ids to skins (legacy themes render the classic skin)', () => {
    expect(skinOfTheme('yondo')).toBe('classic');
    expect(skinOfTheme('yondo-tun')).toBe('classic');
    expect(skinOfTheme('gul')).toBe('classic');
    expect(skinOfTheme(undefined)).toBe('classic');
    expect(skinOfTheme('yondo-warm')).toBe('warm');
    expect(skinOfTheme('yondo-warm-tun')).toBe('warm');
  });
  it('bundles themes, icon set, lockup and default app icon per skin', () => {
    expect(SKINS.classic).toMatchObject({ themes: { day: 'yondo', night: 'yondo-tun' }, iconSet: 'classic', lockup: 'classic', appIconDefault: 'joriy' });
    expect(SKINS.warm).toMatchObject({ themes: { day: 'yondo-warm', night: 'yondo-warm-tun' }, iconSet: 'warm', lockup: 'warm', appIconDefault: 'kartochka' });
  });
});

describe('Icon and lockup follow the skin', () => {
  it('classic (default render): exactly the old nav icon markup', () => {
    const { container } = render(<Icon name="home" />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('data-icon-set')).toBe('classic');
    expect(svg.getAttribute('width')).toBe('22');
    expect(svg.getAttribute('stroke-width')).toBe('1.8');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.innerHTML).toBe('<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"></path>');
  });
  it('classic logo is the untouched symbol, warm is the tile', () => {
    const { container, rerender } = render(<BrandMark />);
    expect(container.querySelector('[data-lockup="classic"]')).toBeTruthy();
    expect(container.querySelectorAll('circle')).toHaveLength(2);
    applyTheme('yondo-warm');
    rerender(<BrandMark />);
    expect(container.querySelector('[data-lockup="warm"]')).toBeTruthy();
  });
  it('swaps the icon set when the theme (skin) changes, without a remount', async () => {
    applyTheme('yondo');
    const { container } = render(<Icon name="cal" />);
    const classic = container.querySelector('svg')!.innerHTML;
    expect(container.querySelector('svg')!.getAttribute('data-icon-set')).toBe('classic');
    applyTheme('yondo-warm-tun');
    await vi.waitFor(() => expect(container.querySelector('svg')!.getAttribute('data-icon-set')).toBe('warm'));
    const warm = container.querySelector('svg')!;
    expect(warm.innerHTML).not.toBe(classic);
    expect(warm.querySelectorAll('path')).toHaveLength(2); // outline + rhombus accent
  });
});

describe('setSkin', () => {
  it('keeps day/night and restores the previous theme when leaving warm', () => {
    setTheme('gul');
    setSkin('warm');
    expect(document.documentElement.dataset.theme).toBe('yondo-warm');
    setSkin('classic');
    expect(document.documentElement.dataset.theme).toBe('gul');
    setTheme('yondo-tun');
    setSkin('warm');
    expect(document.documentElement.dataset.theme).toBe('yondo-warm-tun');
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#111111');
    setTheme('yondo-warm');
    setSkin('classic');
    expect(document.documentElement.dataset.theme).toBe('yondo-tun'); // remembered classic theme wins
  });
  it('survives unavailable storage', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    expect(() => { setTheme('yondo'); setSkin('warm'); setSkin('classic'); }).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe('yondo');
  });
});

describe('Settings tiles', () => {
  it('skin tiles are a radio group: aria-checked, roving tabindex, arrow keys select', async () => {
    applyTheme('yondo');
    const user = userEvent.setup();
    render(<SkinPicker />);
    const group = screen.getByRole('radiogroup', { name: 'Köriniş uslubi' });
    const [classic, warm] = screen.getAllByRole('radio');
    expect(group).toBeTruthy();
    expect(classic.getAttribute('aria-checked')).toBe('true');
    expect(warm.getAttribute('aria-checked')).toBe('false');
    expect(classic.tabIndex).toBe(0);
    expect(warm.tabIndex).toBe(-1);
    classic.focus();
    await user.keyboard('{ArrowRight}');
    expect(document.documentElement.dataset.theme).toBe('yondo-warm');
    await vi.waitFor(() => expect(screen.getAllByRole('radio')[1].getAttribute('aria-checked')).toBe('true'));
    expect(document.activeElement).toBe(screen.getAllByRole('radio')[1]);
    await user.keyboard('{ArrowLeft}');
    expect(document.documentElement.dataset.theme).toBe('yondo');
  });
  it('ThemePicker only lists the themes of the active skin', async () => {
    applyTheme('yondo-warm');
    render(<ThemePicker />);
    await vi.waitFor(() => expect(screen.getAllByRole('button')).toHaveLength(2));
    expect(screen.getAllByRole('button').map((b) => b.getAttribute('aria-pressed'))).toEqual(['true', 'false']);
  });
});
