import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ user: { id: 'u1' } as { id: string } | null }));
const get = vi.hoisted(() => vi.fn());
const play = vi.hoisted(() => vi.fn());
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }));
vi.mock('./notifySound', () => ({ playNotifySound: play }));
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get } };
});
import { ApiError } from '../api/client';
import { POLL_MS, useUnreadNotifications } from './useUnreadNotifications';

const tick = (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

beforeEach(() => {
  vi.useFakeTimers();
  auth.user = { id: 'u1' };
  get.mockReset();
  play.mockReset();
});
afterEach(() => vi.useRealTimers());

describe('useUnreadNotifications', () => {
  it('no sound on the first load, one sound when the count rises, none when it falls', async () => {
    get.mockResolvedValue({ unread_count: 3 });
    const { result } = renderHook(() => useUnreadNotifications());
    await tick(0);
    expect(result.current).toBe(3);
    expect(play).not.toHaveBeenCalled();
    get.mockResolvedValue({ unread_count: 4 });
    await tick(POLL_MS);
    expect(result.current).toBe(4);
    expect(play).toHaveBeenCalledTimes(1);
    get.mockResolvedValue({ unread_count: 1 });
    await tick(POLL_MS);
    expect(play).toHaveBeenCalledTimes(1);
  });

  it('stops polling on 403', async () => {
    get.mockRejectedValue(new ApiError(403, 'forbidden'));
    renderHook(() => useUnreadNotifications());
    await tick(0);
    await tick(POLL_MS * 3);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('keeps polling after a transient error', async () => {
    get.mockRejectedValueOnce(new ApiError(503, 'unavailable')).mockResolvedValue({ unread_count: 0 });
    renderHook(() => useUnreadNotifications());
    await tick(0);
    await tick(POLL_MS);
    expect(get).toHaveBeenCalledTimes(2);
  });

  it('signed out: 0 and no requests', async () => {
    auth.user = null;
    const { result } = renderHook(() => useUnreadNotifications());
    await tick(POLL_MS * 2);
    expect(result.current).toBe(0);
    expect(get).not.toHaveBeenCalled();
  });
});
