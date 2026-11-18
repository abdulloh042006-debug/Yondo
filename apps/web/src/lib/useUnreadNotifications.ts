import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { playNotifySound } from './notifySound';

export const POLL_MS = 30_000;

/**
 * Unread notification count while signed in (polled every POLL_MS). Plays the sound only when the count RISES,
 * never on the first load. Polling stops on 403 (inactive account). Signed out: 0, no requests.
 */
export function useUnreadNotifications(): number {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [state, setState] = useState<{ id: string; n: number } | null>(null);
  useEffect(() => {
    if (!userId) return;
    let stopped = false;
    let prev: number | null = null;
    const ctrl = new AbortController();
    const poll = async () => {
      try {
        const res = await api.get<{ unread_count: number }>('/notifications/unread-count', { signal: ctrl.signal });
        if (stopped) return;
        const n = res.unread_count;
        if (prev !== null && n > prev) playNotifySound();
        prev = n;
        setState({ id: userId, n });
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) {
          stopped = true;
          clearInterval(timer);
        }
        /* other failures: keep the last count, try again next tick */
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), POLL_MS);
    return () => {
      stopped = true;
      ctrl.abort();
      clearInterval(timer);
    };
  }, [userId]);
  return userId && state?.id === userId ? state.n : 0;
}
