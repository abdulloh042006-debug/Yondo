// Yondo API client with secure token storage and automatic refresh.
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export const API_ORIGIN = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
const BASE = `${API_ORIGIN}/api/v1`;
const TOKEN_KEY = 'yondo.tokens';

export interface Tokens {
  access_token: string;
  refresh_token: string;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

let tokens: Tokens | null = null;
let refreshing: Promise<boolean> | null = null;

async function readStored(): Promise<string | null> {
  try {
    if (Platform.OS === 'web') return globalThis.localStorage?.getItem(TOKEN_KEY) ?? null;
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}

async function writeStored(value: string | null): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (value) globalThis.localStorage?.setItem(TOKEN_KEY, value);
      else globalThis.localStorage?.removeItem(TOKEN_KEY);
      return;
    }
    if (value) await SecureStore.setItemAsync(TOKEN_KEY, value);
    else await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch {
    // Storage failures only shorten the session.
  }
}

export async function loadTokens(): Promise<Tokens | null> {
  const raw = await readStored();
  tokens = raw ? (JSON.parse(raw) as Tokens) : null;
  return tokens;
}

export async function setTokens(next: Tokens | null): Promise<void> {
  tokens = next;
  await writeStored(next ? JSON.stringify(next) : null);
}

export function accessToken(): string | null {
  return tokens?.access_token ?? null;
}

export type Query = Record<string, string | number | boolean | null | undefined | string[]>;

export function buildUrl(path: string, query?: Query): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(item))}`);
  }
  return `${BASE}${path}${parts.length ? `?${parts.join('&')}` : ''}`;
}

/** Realtime endpoint; the client authenticates with an ``auth`` message after connecting. */
export function realtimeUrl(): string | null {
  if (!tokens) return null;
  return `${BASE.replace(/^http/, 'ws')}/realtime/ws`;
}

async function refresh(): Promise<boolean> {
  if (!tokens) return false;
  const response = await fetch(buildUrl('/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!response.ok) {
    await setTokens(null);
    return false;
  }
  const body = await response.json();
  await setTokens({ access_token: body.access_token, refresh_token: body.refresh_token });
  return true;
}

interface Options {
  query?: Query;
  body?: unknown;
  blob?: Blob;
  contentType?: string;
}

export async function request<T>(method: string, path: string, options: Options = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {};
  if (tokens) headers.Authorization = `Bearer ${tokens.access_token}`;
  let body: BodyInit | undefined;
  if (options.blob) {
    body = options.blob;
    headers['Content-Type'] = options.contentType ?? (options.blob.type || 'image/jpeg');
  } else if (options.body !== undefined) {
    body = JSON.stringify(options.body);
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(buildUrl(path, options.query), { method, headers, body });
  if (response.status === 401 && retry && tokens) {
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
    throw new ApiError(response.status, data?.code ?? 'error', detail || data?.message || 'Request failed');
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body: body ?? {} }),
  del: <T>(path: string) => request<T>('DELETE', path),
  /** Upload a local image (picker URI) as a raw request body. */
  uploadImage: async <T>(path: string, uri: string, mimeType?: string | null) => {
    const blob = await (await fetch(uri)).blob();
    const type = mimeType && ['image/jpeg', 'image/png', 'image/webp'].includes(mimeType) ? mimeType : blob.type || 'image/jpeg';
    return request<T>('POST', path, { blob, contentType: type });
  },
};

export interface Page<T> {
  items: T[];
  next_offset: number | null;
}
