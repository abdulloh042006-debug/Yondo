import { t } from '../i18n';
import { messageFor } from '../lib/messages';
import type { components } from './schema';

export type Schemas = components['schemas'];

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly fields: Record<string, string>;
  constructor(status: number, code: string, requestId?: string, fields: Record<string, string> = {}) {
    super(messageFor(code, status));
    // Looked up on every read, so an error already on screen follows a language change.
    Object.defineProperty(this, 'message', { get: () => messageFor(code, status), enumerable: false });
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.fields = fields;
  }
  /** 503 means a dependency is unavailable; it must never be presented as a refusal. */
  get unavailable(): boolean {
    return this.status === 503 || this.status === 0;
  }
}

const BASE = '/api/v1';
const ACCESS = 'yondo.access';
const REFRESH = 'yondo.refresh';

/* Tokens live in sessionStorage (cleared with the tab). If storage is blocked we fall back to
   memory so the app still works for the current page view. */
const memory = new Map<string, string>();
function read(key: string): string | null {
  try {
    return sessionStorage.getItem(key) ?? memory.get(key) ?? null;
  } catch {
    return memory.get(key) ?? null;
  }
}
function write(key: string, value: string | null): void {
  if (value === null) memory.delete(key);
  else memory.set(key, value);
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    /* memory fallback above */
  }
}

type Listener = () => void;
const expiredListeners = new Set<Listener>();
export const onSessionExpired = (fn: Listener): (() => void) => {
  expiredListeners.add(fn);
  return () => expiredListeners.delete(fn);
};

export const tokens = {
  has: (): boolean => read(ACCESS) !== null,
  set(pair: { access_token: string; refresh_token: string }) {
    write(ACCESS, pair.access_token);
    write(REFRESH, pair.refresh_token);
  },
  clear() {
    write(ACCESS, null);
    write(REFRESH, null);
  },
};

let refreshing: Promise<boolean> | null = null;
async function refresh(): Promise<boolean> {
  const token = read(REFRESH);
  if (!token) return false;
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token }),
      });
      if (!res.ok) return false;
      tokens.set((await res.json()) as Schemas['TokenResponse']);
      return true;
    } catch {
      return false;
    } finally {
      queueMicrotask(() => (refreshing = null));
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
  signal?: AbortSignal;
  raw?: Blob;
}

function toFieldErrors(payload: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  const errors = (payload as { errors?: { loc?: unknown[]; field?: string }[] })?.errors;
  for (const e of errors ?? []) {
    const name = e.field ?? (Array.isArray(e.loc) ? String(e.loc[e.loc.length - 1]) : '');
    if (name && !out[name]) out[name] = t('err.fieldInvalid');
  }
  return out;
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, String(v));
  }
  const send = async (): Promise<Response> => {
    const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers };
    const access = opts.anonymous ? null : read(ACCESS);
    if (access) headers.Authorization = `Bearer ${access}`;
    if (opts.raw) headers['Content-Type'] = opts.raw.type;
    else if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    try {
      return await fetch(url, {
        method,
        headers,
        body: opts.raw ?? (opts.body === undefined ? undefined : JSON.stringify(opts.body)),
        signal: opts.signal,
      });
    } catch (error) {
      if ((error as Error).name === 'AbortError') throw error;
      throw new ApiError(0, 'network_error');
    }
  };
  let res = await send();
  if (res.status === 401 && !opts.anonymous && read(REFRESH)) {
    if (await refresh()) res = await send();
    if (res.status === 401) {
      tokens.clear();
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
    throw new ApiError(res.status, p?.code ?? `http_${res.status}`, p?.request_id, toFieldErrors(payload));
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>('POST', path, { ...opts, body: body ?? undefined }),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>('PUT', path, { ...opts, body: body ?? undefined }),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>('PATCH', path, { ...opts, body: body ?? undefined }),
  del: <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, opts),
  /** Raw image bytes: the backend takes the file as the request body, typed by Content-Type. */
  upload: <T>(path: string, file: Blob): Promise<T> => requestRaw<T>('POST', path, file),
};

const requestRaw = <T>(method: string, path: string, raw: Blob): Promise<T> => request<T>(method, path, { raw });
