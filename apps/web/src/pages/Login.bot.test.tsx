import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
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

// What /auth/otp/request answers for a phone without a verified Telegram chat.
const linkRequired = () => new ApiError(422, 'telegram_link_required');
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
    // The code path (Kirish opens on username/phone + password since 2026-11-15).
    <MemoryRouter initialEntries={[{ pathname: '/login', state: { mode: 'code' } }]}>
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
  auth.requestCode.mockRejectedValue(linkRequired());
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
    expect(get).toHaveBeenCalledWith(
      '/auth/telegram/link/status',
      expect.objectContaining({ anonymous: true, headers: { 'X-Yondo-Link-Poll': 'poll-1' } }),
    );
    await tick();
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
    expect(screen.queryByText(t('login.tg.noTelegram'))).toBeNull(); // Gateway-only hint hidden
    // The code step links to the bot chat, so the user can open it, copy the code and come back.
    const toBot = screen.getByRole('link', { name: t('login.bot.open') });
    expect(toBot).toHaveAttribute('href', 'https://t.me/YondoTestBot');
    expect(toBot).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByRole('button', { name: t('login.resendIn', { n: 60 }) })).toBeDisabled();
    expect(auth.requestCode).toHaveBeenCalledTimes(1); // the first ask; the bot then sent the code
  });

  it('a phone that is already linked goes straight to the code (no link challenge)', async () => {
    routeGet(true);
    auth.requestCode.mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 60, delivery_channel: 'telegram' });
    mount();
    await continueWithTelegram();
    expect(auth.requestCode).toHaveBeenCalledWith('+998901234567');
    expect(post).not.toHaveBeenCalled();
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
  });

  it('demo: a sample number keeps its on-screen code while the bot is on', async () => {
    routeGet(true);
    auth.requestCode.mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 60, development_otp: '123456' });
    mount();
    await continueWithTelegram();
    expect(post).not.toHaveBeenCalled();
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
    expect(screen.getByText('123456')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: t('login.bot.open') })).toBeNull(); // on-screen code: no bot link
  });

  it('bot blocked: the link is done, so it explains and offers to request the code again', async () => {
    routeGet(true);
    statuses = [{ status: 'failed', failure_code: 'telegram_bot_unreachable' }];
    auth.requestCode.mockRejectedValueOnce(linkRequired()).mockResolvedValue({ message: 'x', expires_in_seconds: 300, resend_after_seconds: 60, delivery_channel: 'telegram' });
    mount();
    await continueWithTelegram();
    await tick();
    expect(screen.getByText(t('err.telegram_bot_unreachable'))).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: t('login.bot.newLink') })).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.resend') }));
    });
    expect(auth.requestCode).toHaveBeenCalledWith('+998901234567');
    expect(post).toHaveBeenCalledTimes(1); // no second link
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
  });

  it('a phone mismatch is a failed link: offers a new link', async () => {
    routeGet(true);
    statuses = [{ status: 'failed', failure_code: 'telegram_phone_mismatch' }];
    mount();
    await continueWithTelegram();
    await tick();
    expect(screen.getByText(t('err.telegram_phone_mismatch'))).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.bot.newLink') }));
    });
    expect(post).toHaveBeenCalledTimes(2);
    expect(screen.getByText(t('login.bot.waiting'))).toBeInTheDocument();
  });

  it('a status request that hangs is dropped and polling goes on (phone browser paused the page)', async () => {
    let first = true;
    get.mockImplementation(async (path: string, opts?: { signal?: AbortSignal }) => {
      if (path === '/auth/telegram/link/config') return { enabled: true, bot_username: 'YondoTestBot' };
      if (path !== '/auth/telegram/link/status') throw new Error(`unexpected GET ${path}`);
      if (first) {
        first = false;
        return new Promise((_, reject) => opts?.signal?.addEventListener('abort', () => reject(new DOMException('x', 'AbortError'))));
      }
      return { status: 'otp_sent', expires_in_seconds: 500 };
    });
    mount();
    await continueWithTelegram();
    await tick(); // first poll starts and hangs
    expect(screen.getByText(t('login.bot.waiting'))).toBeInTheDocument();
    await tick(8000); // dropped after the timeout
    await tick(); // the next poll answers
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
  });

  it('coming back to the page checks the status at once', async () => {
    routeGet(true);
    statuses = [{ status: 'otp_sent' }];
    mount();
    await continueWithTelegram();
    await act(async () => {
      window.dispatchEvent(new Event('focus'));
    });
    await tick(10);
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
  });

  it('"I have the code" opens the code field without waiting for the status', async () => {
    routeGet(true);
    mount();
    await continueWithTelegram();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.bot.haveCode') }));
    });
    expect(screen.getByLabelText(t('login.code'))).toBeInTheDocument();
    expect(screen.getByText(t('login.bot.codeHint'))).toBeInTheDocument();
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
