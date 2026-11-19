import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppBar } from './AppBar';
import { ShockwaveDock } from './ShockwaveDock';

const items = [
  { to: '/', label: 'Kaşf', end: true, icon: <svg /> },
  { to: '/bookings', label: 'Bronlar', end: false, icon: <svg /> },
  { to: '/account', label: 'Profil', end: false, icon: <svg /> },
];

describe('ShockwaveDock (redesign §4.1)', () => {
  it('marks the tab of the current route (nested routes too) and keeps the effects out of the a11y tree', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/bookings/42']}>
        <ShockwaveDock items={items} label="Asosiy" />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Bronlar' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Kaşf' })).not.toHaveAttribute('aria-current');
    expect(container.querySelectorAll('.dock-particle')).toHaveLength(8);
    for (const el of container.querySelectorAll('.dock-pill, .dock-orb, .dock-particle, .dock-clip')) {
      expect(el).toHaveAttribute('aria-hidden', 'true');
    }
    expect(screen.getByRole('navigation', { name: 'Asosiy' })).toBeInTheDocument();
  });
});

describe('AppBar (redesign §3.2)', () => {
  it('has one h1 with the title and a named back button', () => {
    render(
      <MemoryRouter>
        <AppBar back="/bookings" title="Bron tafsilotlari" />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Bron tafsilotlari' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Orqaga' })).toBeInTheDocument();
  });
});
