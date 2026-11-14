import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { t } from '../i18n';

const auth = vi.hoisted(() => ({ requestCode: vi.fn(), verify: vi.fn() }));
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ state: { status: 'anon' }, requestCode: auth.requestCode, verify: auth.verify }),
}));
const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { Login } from './Login';

const DEEP = 'https://t.me/YondoTestBot?start=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG';
let statuses: { status: string; failure_code?: string | null }[] = [];

function routeGet(enabled: boolean) {
  get.mockImplementation(async (path: string) => {
    if (path === '/auth/telegram/link/config') return { enabled, bot_username: enabled ? 'YondoTestBot' : null };
    if (path === '/auth/telegram/link/status') return { expires_in_seconds: 500, ...(statuses.shift() ?? { status: 'awaiting_contact' }) };
    throw new Error(`unexpected GET ${path}`);
  });
}

const mount = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );

async function continueWithTelegram() {
  const button = await screen.findByRole('button', { name: t('login.bot.continue') });
  fireEvent.change(screen.getByLabelText(t('login.phone')), { target: { value: '+998901234567' } });
  fireEvent.click(document.querySelector('.consent input') as HTMLInputElement);
  await act(async () => {
    fireEvent.click(button);
  });
}

const tick = async (ms = 2100) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
};

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  auth.requestCode.mockReset();
  get.mockReset();
  post.mockReset();
  statuses = [];
  post.mockResolvedValue({
    status: 'initiated', deep_link: DEEP, poll_token: 'poll-1', expires_in_seconds: 600, already_linked: false,
  });
});
afterEach(() => vi.useRealTimers());

describe('Login: Telegram bot', () => {
  it('opens the bot, waits (polling with the poll token), then asks for the code', async () => {
    routeGet(true);
    statuses = [{ status: 'awaiting_contact' }, { status: 'otp_sent' }];
    mount();
    await continueWithTelegram();
    expect(post).toHaveBeenCalledWith('/auth/telegram/link/start', { phone_number: '+998901234567' }, { anonymous: true });
    const open = screen.getByRole('link', { name: t('login.bot.open') });
    expect(open).toHaveAttribute('href', DEEP);
    expect(open).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByText(t('login.bot.steps'))).toBeInTheDocument();
    expect(screen.getByText(t('login.bot.waiting'))).toBeInTheDocument();
    await tick();
    expect(get).toHaveBeenCalledWith('/auth/telegram/link/status', { anonymous: true, headers: { 'X-Yondo-Link-Poll': 'poll-1' } });
    await tick();
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
    expect(screen.queryByText(t('login.tg.noTelegram'))).toBeNull(); // Gateway-only hint hidden
    expect(screen.getByRole('button', { name: t('login.resendIn', { n: 60 }) })).toBeDisabled();
    expect(auth.requestCode).not.toHaveBeenCalled();
  });

  it('a phone that is already linked goes straight to the code (no bot dance)', async () => {
    routeGet(true);
    post.mockResolvedValue({
      status: 'initiated', deep_link: DEEP, poll_token: 'p', expires_in_seconds: 600, already_linked: true,
    });
    auth.requestCode.mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 60, delivery_channel: 'telegram' });
    mount();
    await continueWithTelegram();
    expect(auth.requestCode).toHaveBeenCalledWith('+998901234567');
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
  });

  it('bot blocked: explains it and offers a new link', async () => {
    routeGet(true);
    statuses = [{ status: 'failed', failure_code: 'telegram_bot_unreachable' }];
    mount();
    await continueWithTelegram();
    await tick();
    expect(screen.getByText(t('err.telegram_bot_unreachable'))).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.bot.newLink') }));
    });
    expect(post).toHaveBeenCalledTimes(2);
    expect(screen.getByText(t('login.bot.waiting'))).toBeInTheDocument();
  });

  it('an expired link is recoverable', async () => {
    routeGet(true);
    statuses = [{ status: 'expired' }];
    mount();
    await continueWithTelegram();
    await tick();
    expect(screen.getByText(t('login.bot.expired'))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: t('login.bot.newLink') })).toBeEnabled();
  });

  it('bot disabled (public demo): the old phone + code login is unchanged', async () => {
    routeGet(false);
    auth.requestCode.mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 60, development_otp: '123456' });
    mount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    fireEvent.change(screen.getByLabelText(t('login.phone')), { target: { value: '+998901234567' } });
    fireEvent.click(document.querySelector('.consent input') as HTMLInputElement);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.sendCode') }));
    });
    expect(post).not.toHaveBeenCalled();
    expect(document.querySelector('b.mono')?.textContent).toBe('123456');
  });
});
