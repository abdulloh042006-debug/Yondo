import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppIconPicker } from './SkinPickers';
import { applyTheme } from './theme';

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.head.innerHTML = '';
  vi.restoreAllMocks();
});

describe('AppIconPicker', () => {
  it('five radio tiles, default marked, choice persists and updates the head', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:x') as never;
    URL.revokeObjectURL = vi.fn() as never;
    applyTheme('yondo-warm');
    const user = userEvent.setup();
    render(<AppIconPicker />);
    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(5);
    expect(radios.map((r) => r.getAttribute('aria-checked'))).toEqual(['false', 'true', 'false', 'false', 'false']);
    expect(radios[1].textContent).toContain('Standart');
    radios[1].focus();
    await user.keyboard('{ArrowRight}{ArrowRight}');
    expect(screen.getAllByRole('radio')[3].getAttribute('aria-checked')).toBe('true');
    expect(localStorage.getItem('yondo.appicon')).toBe('karrot');
    expect(document.head.querySelector('link[rel="apple-touch-icon"]')?.getAttribute('href')).toBe('/icons/karrot/180.png');
    await user.click(screen.getAllByRole('radio')[0]);
    expect(localStorage.getItem('yondo.appicon')).toBe('joriy');
  });
});
