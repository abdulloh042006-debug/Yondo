// Thin typed client for the Yondo API with access-token refresh.

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '') + '/api/v1';
const TOKEN_KEY = 'yondo.panel.tokens';

export interface Tokens {
  access_token: string;
  refresh_token: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export function loadTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

export function saveTokens(tokens: Tokens | null): void {
  try {
    if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage may be unavailable (private mode); the session then lasts for this tab only.
  }
  memoryTokens = tokens;
}

let memoryTokens: Tokens | null = loadTokens();
let refreshing: Promise<boolean> | null = null;

export type Query = Record<string, string | number | boolean | null | undefined>;

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  const suffix = params.toString();
  return `${BASE}${path}${suffix ? `?${suffix}` : ''}`;
}

async function refresh(): Promise<boolean> {
  const tokens = memoryTokens;
  if (!tokens) return false;
  const response = await fetch(buildUrl('/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!response.ok) {
    saveTokens(null);
    return false;
  }
  const body = (await response.json()) as Tokens;
  saveTokens({ access_token: body.access_token, refresh_token: body.refresh_token });
  return true;
}

interface RequestOptions {
  query?: Query;
  body?: unknown;
  raw?: Blob;
  contentType?: string;
}

export async function request<T>(method: string, path: string, options: RequestOptions = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {};
  if (memoryTokens) headers.Authorization = `Bearer ${memoryTokens.access_token}`;
  let body: BodyInit | undefined;
  if (options.raw) {
    body = options.raw;
    headers['Content-Type'] = options.contentType ?? options.raw.type;
  } else if (options.body !== undefined) {
    body = JSON.stringify(options.body);
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(buildUrl(path, options.query), { method, headers, body });
  if (response.status === 401 && retry && memoryTokens) {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
    if (await refreshing) return request<T>(method, path, options, false);
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!response.ok) {
    const detail = data?.errors?.map((e: { msg: string }) => e.msg).join('; ');
    throw new ApiError(response.status, data?.code ?? 'error', detail || data?.message || response.statusText);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body: body ?? {} }),
  del: <T>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, file: File) => request<T>('POST', path, { raw: file }),
};

export interface Page<T> {
  items: T[];
  next_offset: number | null;
}

export interface Me {
  id: string;
  phone_number: string;
  display_name: string | null;
  roles: string[];
  account_status: string | null;
}
