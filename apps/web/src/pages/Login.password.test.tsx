import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { t } from '../i18n';

const auth = vi.hoisted(() => ({ requestCode: vi.fn(), verify: vi.fn(), passwordLogin: vi.fn(), resetPassword: vi.fn() }));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ state: { status: 'anon' }, ...auth }) }));
import { Login } from './Login';

const mount = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
const signIn = async (login: string, password: string) => {
  fireEvent.change(screen.getByLabelText(t('login.pw.login')), { target: { value: login } });
  fireEvent.change(screen.getByLabelText(t('login.pw.password')), { target: { value: password } });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: t('login.submit') }));
  });
};

beforeEach(() => {
  Object.values(auth).forEach((f) => f.mockReset());
});

describe('Kirish: username or phone + password (owner, 2026-11-15)', () => {
  it('is the first way in, with accessible fields; the code and the reset are the other options', () => {
    mount();
    expect(screen.getByLabelText(t('login.pw.login'))).toHaveAttribute('autocomplete', 'username');
    const pw = screen.getByLabelText(t('login.pw.password'));
    expect(pw).toHaveAttribute('autocomplete', 'current-password');
    expect(pw).toHaveAttribute('type', 'password');
    fireEvent.click(screen.getByLabelText(t('login.pw.show')));
    expect(pw).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: t('login.pw.useCode') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: t('login.pw.forgot') })).toBeInTheDocument();
  });

  it('sends the username (or phone) and password as typed', async () => {
    auth.passwordLogin.mockResolvedValue(undefined);
    mount();
    await signIn(' aziz.k ', 'a long passphrase');
    expect(auth.passwordLogin).toHaveBeenCalledWith('aziz.k', 'a long passphrase');
  });

  it.each([
    ['invalid_credentials', 401, 'err.invalid_credentials'],
    ['password_login_blocked', 429, 'err.password_login_blocked'],
    ['rate_limited', 429, 'err.rate_limited'],
  ] as const)('maps %s by its code, tied to the password field, and clears the password', async (code, status, key) => {
    auth.passwordLogin.mockRejectedValue(new ApiError(status, code));
    mount();
    await signIn('aziz.k', 'wrong password');
    const pw = screen.getByLabelText(t('login.pw.password')) as HTMLInputElement;
    expect(pw).toHaveAccessibleDescription(t(key));
    expect(pw.value).toBe('');
  });

  it('the lockout message says how long and offers the code', () => {
    expect(t('err.password_login_blocked')).toMatch(/15/);
    expect(t('err.password_login_blocked')).toMatch(/kod/);
  });

  it('reset: phone → code → new password; checks the rules before calling the server', async () => {
    auth.requestCode.mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 30, development_otp: '123456' });
    auth.resetPassword.mockResolvedValue(undefined);
    mount();
    fireEvent.click(screen.getByRole('button', { name: t('login.pw.forgot') }));
    expect(screen.getByRole('heading', { level: 1, name: t('login.reset.title') })).toBeInTheDocument();
    expect(document.querySelector('.consent input[aria-invalid]')).toBeNull(); // no consent box: the account exists
    fireEvent.change(screen.getByLabelText(t('login.phone')), { target: { value: '+998901234567' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.sendCode') }));
    });
    fireEvent.change(screen.getByLabelText(t('login.code')), { target: { value: '123456' } });
    const next = screen.getByLabelText(t('pw.new'));
    expect(next).toHaveAttribute('autocomplete', 'new-password');
    fireEvent.change(next, { target: { value: '901234567' } });
    fireEvent.change(screen.getByLabelText(t('pw.repeat')), { target: { value: '901234567' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.reset.submit') }));
    });
    expect(auth.resetPassword).not.toHaveBeenCalled();
    expect(next).toHaveAccessibleDescription(t('pw.isPhone'));
    fireEvent.change(next, { target: { value: 'a new long one' } });
    fireEvent.change(screen.getByLabelText(t('pw.repeat')), { target: { value: 'a new long one' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.reset.submit') }));
    });
    expect(auth.resetPassword).toHaveBeenCalledWith('+998901234567', '123456', 'a new long one');
  });
});
