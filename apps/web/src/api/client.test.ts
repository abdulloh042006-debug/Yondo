import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, onSessionExpired, tokens } from './client';

const json = (status: number, body: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

beforeEach(() => {
  sessionStorage.clear();
  tokens.clear();
});
afterEach(() => vi.restoreAllMocks());

describe('api client', () => {
  it('turns a structured error into ApiError (code, status, request id, field names)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json(422, { code: 'validation_error', message: 'English text', request_id: 'r-1', errors: [{ loc: ['body', 'age'], msg: 'x' }] }),
    );
    const err = (await api.get('/x').catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('validation_error');
    expect(err.requestId).toBe('r-1');
    expect(err.fields.age).toBeTruthy();
    expect(err.message).not.toContain('English text'); // UI text never comes from the server message
  });

  it('503 is flagged unavailable; network failures too', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json(503, { code: 'payment_provider_unavailable', message: 'm' }));
    expect(((await api.get('/x').catch((e) => e)) as ApiError).unavailable).toBe(true);
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('offline'));
    const net = (await api.get('/x').catch((e) => e)) as ApiError;
    expect(net.code).toBe('network_error');
    expect(net.unavailable).toBe(true);
  });

  it('sends the bearer token and refreshes once on 401, then retries', async () => {
    tokens.set({ access_token: 'old', refresh_token: 'r1' });
    const spy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json(401, { code: 'invalid_access_token', message: '' }))
      .mockResolvedValueOnce(json(200, { access_token: 'new', refresh_token: 'r2', expires_in: 1 }))
      .mockResolvedValueOnce(json(200, { ok: true }));
    expect(await api.get('/secure')).toEqual({ ok: true });
    const retry = spy.mock.calls[2][1] as RequestInit;
    expect((retry.headers as Record<string, string>).Authorization).toBe('Bearer new');
    expect(spy).toHaveBeenCalledTimes(3);
  });

  it('clears the session and notifies listeners when refresh fails', async () => {
    tokens.set({ access_token: 'old', refresh_token: 'bad' });
    const expired = vi.fn();
    const off = onSessionExpired(expired);
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json(401, { code: 'invalid_access_token', message: '' }))
      .mockResolvedValueOnce(json(401, { code: 'invalid_refresh_token', message: '' }));
    await expect(api.get('/secure')).rejects.toBeInstanceOf(ApiError);
    expect(tokens.has()).toBe(false);
    expect(expired).toHaveBeenCalled();
    off();
  });

  it('anonymous requests never carry credentials; 204 resolves to undefined', async () => {
    tokens.set({ access_token: 'secret', refresh_token: 'r' });
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));
    expect(await api.del('/x', { anonymous: true })).toBeUndefined();
    const headers = (spy.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('raw uploads keep the image content type', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(201, { id: '1' }));
    await api.upload('/photos', new Blob(['x'], { type: 'image/png' }));
    expect(((spy.mock.calls[0][1] as RequestInit).headers as Record<string, string>)['Content-Type']).toBe('image/png');
  });
});
