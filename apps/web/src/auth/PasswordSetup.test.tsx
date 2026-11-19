import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { t } from '../i18n';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
const put = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post, put } };
});
const auth = vi.hoisted(() => ({ reload: vi.fn(), logout: vi.fn(), user: null as unknown }));
vi.mock('./AuthContext', () => ({ useAuth: () => auth }));
import { PasswordSetupGate } from './PasswordSetup';

const user = { id: 'u1', phone_number: '+998901110003', username: null, has_password: false, password_setup_required: true };
function LoginProbe() {
  const loc = useLocation();
  return <p>login:{JSON.stringify(loc.state)}</p>;
}
const mount = (path = '/') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route path="*" element={<PasswordSetupGate><p>the page</p></PasswordSetupGate>} />
      </Routes>
    </MemoryRouter>,
  );
const fill = (name: string, pw: string, pw2 = pw) => {
  fireEvent.change(screen.getByLabelText(t('setup.username')), { target: { value: name } });
  fireEvent.change(screen.getByLabelText(t('pw.new')), { target: { value: pw } });
  fireEvent.change(screen.getByLabelText(t('pw.repeat')), { target: { value: pw2 } });
  fireEvent.change(screen.getByLabelText(t('age.dob')), { target: { value: '1995-05-15' } });
};
const save = () => act(async () => fireEvent.click(screen.getByRole('button', { name: t('setup.submit') })));

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  auth.reload.mockReset();
  auth.logout.mockReset();
  auth.user = user;
});

describe('password setup after a code sign-in (owner, 2026-11-15)', () => {
  it('replaces the page while password_setup_required; Help and the documents stay open', () => {
    mount();
    expect(screen.getByRole('heading', { level: 1, name: t('setup.title') })).toBeInTheDocument();
    expect(screen.queryByText('the page')).toBeNull();
    mount('/help');
    expect(screen.getByText('the page')).toBeInTheDocument();
  });

  it('checks the username live (debounced, only valid names), then registers', async () => {
    get.mockResolvedValue({ username: 'aziz.k', available: true, reason: null });
    post.mockResolvedValue({});
    mount();
    fill('1bad', 'long enough pw');
    expect(screen.getByLabelText(t('setup.username'))).toHaveAccessibleDescription(expect.stringContaining(t('setup.invalid')));
    fill('Aziz.K', 'long enough pw');
    await waitFor(() => expect(get).toHaveBeenCalledTimes(1), { timeout: 2000 });
    expect(get.mock.calls[0][0]).toBe('/auth/username/available?username=aziz.k');
    await screen.findByText(t('setup.available'));
    expect(screen.getByLabelText(t('setup.username'))).toHaveAttribute('autocomplete', 'username');
    expect(screen.getByLabelText(t('pw.new'))).toHaveAttribute('autocomplete', 'new-password');
    await save();
    expect(post).toHaveBeenCalledWith('/auth/registration', { username: 'aziz.k', password: 'long enough pw', date_of_birth: '1995-05-15' });
    expect(auth.reload).toHaveBeenCalled();
  });

  it('a taken name, a mismatch and the phone as password are refused before the server', async () => {
    get.mockResolvedValue({ username: 'taken.one', available: false, reason: 'taken' });
    mount();
    fill('taken.one', '+998 90 111 00 03', 'other');
    await screen.findByText(t('setup.taken'));
    await save();
    expect(post).not.toHaveBeenCalled();
    expect(screen.getByLabelText(t('setup.username'))).toHaveAccessibleDescription(expect.stringContaining(t('setup.taken')));
    expect(screen.getByLabelText(t('pw.new'))).toHaveAccessibleDescription(t('pw.isPhone'));
  });

  it('reauth_required (code sign-in older than 15 min): signs out and returns to the code sign-in', async () => {
    get.mockResolvedValue({ username: 'aziz.k', available: true, reason: null });
    post.mockRejectedValue(new ApiError(403, 'reauth_required'));
    mount();
    fill('aziz.k', 'long enough pw');
    await save();
    expect(auth.logout).toHaveBeenCalled();
    expect(await screen.findByText(/login:/)).toHaveTextContent('"mode":"code"');
    expect(screen.getByText(/login:/)).toHaveTextContent(t('setup.reauth'));
  });
});


describe('18+ (owner, 2026-11-19)', () => {
  beforeEach(() => {
    put.mockReset();
    auth.reload.mockReset();
    auth.logout.mockReset();
  });

  it('a new sign-up under 18 is refused: signed out, back to Kirish with a notice', async () => {
    auth.user = user;
    get.mockResolvedValue({ username: 'aziz.k', available: true });
    post.mockRejectedValue(new ApiError(403, 'age_restricted'));
    mount();
    fill('aziz.k', 'long enough pw');
    await save();
    expect(auth.logout).toHaveBeenCalled();
    expect(await screen.findByText(/login:/)).toHaveTextContent(t('age.restrictedNew'));
  });

  it('an older account without a date of birth gives it once', async () => {
    auth.user = { ...user, username: 'aziz.k', has_password: true, password_setup_required: false, date_of_birth: null };
    put.mockResolvedValue({});
    mount();
    expect(screen.queryByText('the page')).toBeNull();
    fireEvent.change(screen.getByLabelText(t('age.dob')), { target: { value: '1990-01-31' } });
    await save();
    expect(put).toHaveBeenCalledWith('/auth/date-of-birth', { date_of_birth: '1990-01-31' });
    expect(auth.reload).toHaveBeenCalled();
  });

  it('a restricted account sees why, with support and account deletion; the app stays closed', async () => {
    auth.user = { ...user, username: 'aziz.k', has_password: true, password_setup_required: false, date_of_birth: null, age_restricted: true };
    get.mockResolvedValue(null);
    mount();
    expect(screen.getByRole('heading', { name: t('age.restrictedTitle') })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: t('age.contactSupport') })).toHaveAttribute('href', '/help');
    expect(screen.queryByText('the page')).toBeNull();
  });

  it('Help stays open for a restricted account (support form, SOS)', () => {
    auth.user = { ...user, password_setup_required: false, age_restricted: true };
    mount('/help');
    expect(screen.getByText('the page')).toBeInTheDocument();
  });
});
