import { messageFor, t, type Schemas } from './shared';
import { getItem, setItem } from './storage';

export type { Schemas };

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  constructor(status: number, code: string, requestId?: string) {
    super(messageFor(code, status));
    // Read on every access, so an error on screen follows a language change.
    Object.defineProperty(this, 'message', { get: () => messageFor(code, status), enumerable: false });
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
  /** 503 (or no connection) means a dependency is unavailable: never shown as a refusal or "declined". */
  get unavailable(): boolean {
    return this.status === 503 || this.status === 0;
  }
}

/** Empty on the web build = same origin (a reverse proxy routes /api). Phones need the API's LAN/HTTPS URL. */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/+$/, '');
export const WEB_URL = (process.env.EXPO_PUBLIC_WEB_URL ?? '').replace(/\/+$/, '');
const BASE = `${API_URL}/api/v1`;
const ACCESS = 'yondo.access';
const REFRESH = 'yondo.refresh';

/* Tokens are read synchronously by every request, so they are cached in memory after `tokens.load()`. */
let access: string | null = null;
let refreshToken: string | null = null;

const expiredListeners = new Set<() => void>();
export const onSessionExpired = (fn: () => void): (() => void) => {
  expiredListeners.add(fn);
  return () => expiredListeners.delete(fn);
};

export const tokens = {
  async load() {
    access = await getItem(ACCESS, 'secret');
    refreshToken = await getItem(REFRESH, 'secret');
  },
  has: (): boolean => access !== null,
  async set(pair: { access_token: string; refresh_token: string }) {
    access = pair.access_token;
    refreshToken = pair.refresh_token;
    await setItem(ACCESS, access, 'secret');
    await setItem(REFRESH, refreshToken, 'secret');
  },
  async clear() {
    access = null;
    refreshToken = null;
    await setItem(ACCESS, null, 'secret');
    await setItem(REFRESH, null, 'secret');
  },
};

let refreshing: Promise<boolean> | null = null;
function refresh(): Promise<boolean> {
  if (!refreshToken) return Promise.resolve(false);
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) return false;
      await tokens.set((await res.json()) as Schemas['TokenResponse']);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

export interface RequestOptions {
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  headers?: Record<string, string>;
  /** Public endpoints skip the bearer header. */
  anonymous?: boolean;
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const params = Object.entries(opts.query ?? {})
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  const url = `${BASE}${path}${params.length ? `?${params.join('&')}` : ''}`;
  const send = async (): Promise<Response> => {
    const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers };
    if (!opts.anonymous && access) headers.Authorization = `Bearer ${access}`;
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    try {
      return await fetch(url, { method, headers, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
    } catch {
      throw new ApiError(0, 'network_error');
    }
  };
  let res = await send();
  if (res.status === 401 && !opts.anonymous && refreshToken) {
    if (await refresh()) res = await send();
    if (res.status === 401) {
      await tokens.clear();
      expiredListeners.forEach((fn) => fn());
    }
  }
  if (res.status === 204) return undefined as T;
  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    /* non-JSON bodies (proxy errors) fall through to the status mapping */
  }
  if (!res.ok) {
    const p = payload as { code?: string; request_id?: string } | null;
    throw new ApiError(res.status, p?.code ?? `http_${res.status}`, p?.request_id);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>('POST', path, { ...opts, body }),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>('PUT', path, { ...opts, body }),
  del: <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, opts),
};

export const errorText = (error: unknown): string => (error instanceof ApiError ? error.message : t('common.actionFailed'));

/** One key per booking, kept on the device, so a retried "pay" never creates a second charge. */
export async function idempotencyKey(bookingId: string): Promise<string> {
  const k = `yondo.pay.${bookingId}`;
  const existing = await getItem(k, 'pref');
  if (existing) return existing;
  const hex = Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
  const fresh = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20)}`;
  await setItem(k, fresh, 'pref');
  return fresh;
}
