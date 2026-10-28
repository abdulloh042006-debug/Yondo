import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
vi.mock('./AuthContext', () => ({ useAuth: () => auth.value }));
import { RequireAuth } from './guards';

const mount = (value: unknown, role?: 'admin') => {
  auth.value = value;
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/login" element={<p>LOGIN PAGE</p>} />
        <Route path="/admin" element={<RequireAuth role={role}><p>SECRET</p></RequireAuth>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe('RequireAuth (UX guard only; the server enforces the real rule)', () => {
  it('sends anonymous visitors to login', () => {
    mount({ state: { status: 'anon' }, user: null }, 'admin');
    expect(screen.getByText('LOGIN PAGE')).toBeInTheDocument();
  });
  it('shows a denial for a signed-in non-admin and never renders children', () => {
    mount({ state: { status: 'authed' }, user: { roles: ['customer'] } }, 'admin');
    expect(screen.getByText('Bu bölim siz uçun emas')).toBeInTheDocument();
    expect(screen.queryByText('SECRET')).toBeNull();
  });
  it('renders for an admin', () => {
    mount({ state: { status: 'authed' }, user: { roles: ['admin'] } }, 'admin');
    expect(screen.getByText('SECRET')).toBeInTheDocument();
  });
});
