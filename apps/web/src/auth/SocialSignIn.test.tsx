import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { t } from '../i18n';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
const reload = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
vi.mock('./AuthContext', () => ({ useAuth: () => ({ reload, user: null, state: { status: 'anon' } }) }));
import { tokens } from '../api/client';
import { completeSignup, pendingSignup, resetSocialConfigCache } from './social';
import { SocialCallback } from './SocialCallback';
import { SocialSignIn } from './SocialSignIn';

type GoogleCallback = (r: { credential: string }) => void;
let googleCallback: GoogleCallback | null = null;
const renderButton = vi.fn((el: HTMLElement) => {
  el.innerHTML = '<div role="button">Google</div>';
});

function config(telegram: boolean, google: string | null) {
  get.mockImplementation(async (path: string) => {
    if (path === '/auth/social/config')
      return { telegram, telegram_client_id: telegram ? '9000000001' : null, telegram_code_flow: false, google_client_id: google };
    throw new Error(`unexpected GET ${path}`);
  });
}

const signIn = (onSignedIn = vi.fn(), onPhoneRequired = vi.fn()) => {
  render(
    <MemoryRouter>
      <SocialSignIn onSignedIn={onSignedIn} onPhoneRequired={onPhoneRequired} />
    </MemoryRouter>,
  );
  return { onSignedIn, onPhoneRequired };
};

const TOKENS = { access_token: 'a1', refresh_token: 'r1', token_type: 'bearer', expires_in: 900 };

beforeEach(() => {
  resetSocialConfigCache();
  get.mockReset();
  post.mockReset();
  reload.mockReset();
  sessionStorage.clear();
  tokens.clear();
  googleCallback = null;
  window.google = {
    accounts: {
      id: {
        initialize: (opts) => {
          googleCallback = opts.callback;
        },
        renderButton,
      },
    },
  };
});
afterEach(() => {
  delete window.google;
  delete window.Telegram;
  vi.restoreAllMocks();
});

describe('SocialSignIn', () => {
  it('shows nothing when no provider is configured', async () => {
    config(false, null);
    const { container } = render(
      <MemoryRouter>
        <SocialSignIn onSignedIn={vi.fn()} onPhoneRequired={vi.fn()} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing when the config cannot be read (never a broken button)', async () => {
    get.mockRejectedValue(new Error('offline'));
    signIn();
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: t('social.telegram') })).toBeNull();
  });

  it('Telegram: round official button, server nonce, ID token verified by the server', async () => {
    config(true, null);
    const auth = vi.fn((_opts: unknown, cb: (r: { id_token?: string; error?: string }) => void) => cb({ id_token: 'tg-id-token' }));
    window.Telegram = { Login: { auth } };
    post.mockImplementation(async (path: string) => {
      if (path === '/auth/social/telegram/nonce') return { nonce: 'nonce-abcdefghijklmnop', expires_in_seconds: 600 };
      if (path === '/auth/social/telegram') return { status: 'signed_in', provider: 'telegram', tokens: TOKENS, password_setup_required: true };
      throw new Error(`unexpected POST ${path}`);
    });
    const { onSignedIn } = signIn();
    const button = await screen.findByRole('button', { name: t('social.telegram') });
    expect(button).toHaveClass('tg-auth-button');
    expect(button).toHaveAttribute('data-style', 'icon');
    await waitFor(() => expect(post).toHaveBeenCalledWith('/auth/social/telegram/nonce', undefined, { anonymous: true }));
    await act(async () => {
      fireEvent.click(button);
    });
    expect(auth).toHaveBeenCalledWith(
      expect.objectContaining({ client_id: 9000000001, request_access: ['phone', 'write'], nonce: 'nonce-abcdefghijklmnop' }),
      expect.any(Function),
    );
    expect(post).toHaveBeenCalledWith('/auth/social/telegram', { id_token: 'tg-id-token' }, { anonymous: true });
    expect(tokens.has()).toBe(true);
    expect(onSignedIn).toHaveBeenCalled();
  });

  it('Telegram: a closed popup shows a clear message and signs nobody in', async () => {
    config(true, null);
    window.Telegram = { Login: { auth: (_o: unknown, cb: (r: { error?: string }) => void) => cb({ error: 'popup_closed' }) } };
    post.mockResolvedValue({ nonce: 'nonce-abcdefghijklmnop', expires_in_seconds: 600 });
    const { onSignedIn } = signIn();
    const button = await screen.findByRole('button', { name: t('social.telegram') });
    await act(async () => {
      fireEvent.click(button);
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(t('err.social_cancelled'));
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it('Google: a known identity signs in', async () => {
    config(false, 'web.apps.googleusercontent.com');
    post.mockResolvedValue({ status: 'signed_in', provider: 'google', tokens: TOKENS, password_setup_required: false });
    const { onSignedIn, onPhoneRequired } = signIn();
    await waitFor(() => expect(renderButton).toHaveBeenCalled());
    await act(async () => googleCallback?.({ credential: 'id-token' }));
    expect(post).toHaveBeenCalledWith('/auth/social/google', { credential: 'id-token' }, { anonymous: true });
    expect(tokens.has()).toBe(true);
    expect(onSignedIn).toHaveBeenCalled();
    expect(onPhoneRequired).not.toHaveBeenCalled();
  });

  it('Google: a new identity asks for phone proof and keeps the sign-up ticket', async () => {
    config(false, 'web.apps.googleusercontent.com');
    post.mockResolvedValue({ status: 'phone_required', provider: 'google', signup_token: 'ticket-1234567890', expires_in_seconds: 600 });
    const { onSignedIn, onPhoneRequired } = signIn();
    await waitFor(() => expect(renderButton).toHaveBeenCalled());
    await act(async () => googleCallback?.({ credential: 'id-token' }));
    expect(onPhoneRequired).toHaveBeenCalled();
    expect(onSignedIn).not.toHaveBeenCalled();
    expect(tokens.has()).toBe(false);
    expect(pendingSignup()?.token).toBe('ticket-1234567890');
    // The phone code then completes it.
    post.mockResolvedValue({ status: 'signed_in', provider: 'google', tokens: TOKENS });
    await completeSignup('+998901234567', '123456');
    expect(post).toHaveBeenLastCalledWith(
      '/auth/social/complete',
      { signup_token: 'ticket-1234567890', phone_number: '+998901234567', code: '123456' },
      { anonymous: true },
    );
    expect(tokens.has()).toBe(true);
    expect(pendingSignup()).toBeNull();
  });
});

function Where() {
  const loc = useLocation();
  return <p data-testid="where">{loc.pathname}</p>;
}
const callback = (search: string) =>
  render(
    <MemoryRouter initialEntries={[`/auth/callback/telegram${search}`]}>
      <Routes>
        <Route path="/auth/callback/telegram" element={<SocialCallback />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );

describe('SocialCallback', () => {
  const setSearch = (search: string) => window.history.replaceState(null, '', `/auth/callback/telegram${search}`);
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('exchanges code + state with the stored flow token and signs in', async () => {
    sessionStorage.setItem('yondo.social.flow', JSON.stringify({ flow: 'flow-123', intent: 'login' }));
    setSearch('?code=abc&state=st-1');
    post.mockResolvedValue({ status: 'signed_in', provider: 'telegram', tokens: TOKENS, password_setup_required: true });
    callback('?code=abc&state=st-1');
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent('/'));
    expect(post).toHaveBeenCalledWith(
      '/auth/social/telegram/exchange',
      { code: 'abc', state: 'st-1', flow_token: 'flow-123' },
      { anonymous: true },
    );
    expect(reload).toHaveBeenCalled();
    expect(sessionStorage.getItem('yondo.social.flow')).toBeNull(); // single use
  });

  it('goes to the code step when Telegram gave no verified phone', async () => {
    sessionStorage.setItem('yondo.social.flow', JSON.stringify({ flow: 'flow-123', intent: 'login' }));
    setSearch('?code=abc&state=st-1');
    post.mockResolvedValue({ status: 'phone_required', provider: 'telegram', signup_token: 'ticket-1234567890', expires_in_seconds: 600 });
    callback('?code=abc&state=st-1');
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent('/login'));
    expect(pendingSignup()?.provider).toBe('telegram');
  });

  it('a missing flow token (another browser) is refused without calling the API', async () => {
    setSearch('?code=abc&state=st-1');
    callback('?code=abc&state=st-1');
    expect(await screen.findByRole('alert')).toHaveTextContent(t('err.social_state_invalid'));
    expect(post).not.toHaveBeenCalled();
  });

  it('a cancelled Telegram consent shows a clear message', async () => {
    setSearch('?error=access_denied');
    callback('?error=access_denied');
    expect(await screen.findByRole('alert')).toHaveTextContent(t('err.social_cancelled'));
  });
});
