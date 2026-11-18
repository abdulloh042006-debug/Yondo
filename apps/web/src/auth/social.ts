/**
 * Social sign-in helpers (docs/login-telegram-google.md): Telegram Login (OIDC code flow + PKCE,
 * exchanged by the server) and Google Identity Services. Accounts stay phone-anchored: a new Google
 * identity (or Telegram without a verified phone) gets a sign-up ticket that a phone code completes.
 */
import { api, tokens, type Schemas } from '../api/client';

export type SocialConfig = Schemas['SocialConfig'];
export type SocialResult = Schemas['SocialResult'];
export type SocialProvider = 'telegram' | 'google';
export type FlowIntent = 'login' | 'link';

const FLOW = 'yondo.social.flow';
const SIGNUP = 'yondo.social.signup';

function store(key: string, value: unknown | null): void {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: the flow cannot survive the redirect, the server answers social_state_invalid */
  }
}
function load<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

let configPromise: Promise<SocialConfig> | null = null;
/** Unknown (network error) = no buttons; a provider that is not configured is never shown as broken. */
export function socialConfig(): Promise<SocialConfig> {
  configPromise ??= api
    .get<SocialConfig>('/auth/social/config', { anonymous: true })
    .catch(() => {
      configPromise = null;
      return { telegram: false, google_client_id: null };
    });
  return configPromise;
}
export function resetSocialConfigCache(): void {
  configPromise = null;
}

/** Indirection so tests can observe the redirect (jsdom cannot navigate). */
export const browser = { go: (url: string) => window.location.assign(url) };

export const telegramRedirectUri = (): string => `${window.location.origin}/auth/callback/telegram`;

/** Opens oauth.telegram.org; the browser keeps the flow token to prove it started this attempt. */
export async function startTelegram(intent: FlowIntent): Promise<void> {
  const res = await api.post<Schemas['TelegramStarted']>(
    intent === 'link' ? '/auth/social/telegram/link/start' : '/auth/social/telegram/start',
    { redirect_uri: telegramRedirectUri() },
    { anonymous: intent === 'login' },
  );
  store(FLOW, { flow: res.flow_token, intent });
  browser.go(res.authorization_url);
}

export function takeTelegramFlow(): { flow: string; intent: FlowIntent } | null {
  const flow = load<{ flow: string; intent: FlowIntent }>(FLOW);
  store(FLOW, null);
  return flow;
}

type PendingSignup = { token: string; provider: SocialProvider; until: number };
export function savePendingSignup(result: SocialResult): void {
  if (!result.signup_token) return;
  const until = Date.now() + (result.expires_in_seconds ?? 600) * 1000;
  store(SIGNUP, { token: result.signup_token, provider: result.provider, until });
}
export function pendingSignup(): PendingSignup | null {
  const pending = load<PendingSignup>(SIGNUP);
  if (pending && pending.until > Date.now()) return pending;
  if (pending) store(SIGNUP, null);
  return null;
}
export function clearPendingSignup(): void {
  store(SIGNUP, null);
}

/** Phone proof for a pending social sign-up: the code from the usual code step. */
export async function completeSignup(phone: string, code: string): Promise<void> {
  const pending = pendingSignup();
  if (!pending) return;
  const result = await api.post<SocialResult>(
    '/auth/social/complete',
    { signup_token: pending.token, phone_number: phone, code },
    { anonymous: true },
  );
  clearPendingSignup();
  if (result.tokens) tokens.set(result.tokens);
}

/** Stores the session of a signed-in result; returns what the caller must do next. */
export function applyResult(result: SocialResult): 'signed_in' | 'phone_required' | 'linked' {
  if (result.status === 'signed_in' && result.tokens) tokens.set(result.tokens);
  if (result.status === 'phone_required') savePendingSignup(result);
  return result.status;
}

// ---- Google Identity Services (loaded only when a client ID is configured) --------------------

interface GoogleId {
  initialize(opts: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: string }): void;
  renderButton(el: HTMLElement, opts: Record<string, unknown>): void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

let gisPromise: Promise<GoogleId> | null = null;
export function loadGoogle(): Promise<GoogleId> {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id);
  gisPromise ??= new Promise<GoogleId>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = () => (window.google?.accounts?.id ? resolve(window.google.accounts.id) : reject(new Error('gis')));
    script.onerror = () => {
      gisPromise = null;
      reject(new Error('gis'));
    };
    document.head.appendChild(script);
  });
  return gisPromise;
}
