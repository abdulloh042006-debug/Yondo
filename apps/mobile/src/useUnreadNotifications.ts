import { useEffect, useState } from 'react';

import { ApiError, api } from './api';
import { useAuth } from './auth';
import { loadSoundPref, playNotifySound } from './notifySound';

export const POLL_MS = 30_000;

/** Same behaviour as apps/web/src/lib/useUnreadNotifications.ts: poll while signed in, sound only on a RISE, stop on 403. */
export function useUnreadNotifications(): number {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [state, setState] = useState<{ id: string; n: number } | null>(null);
  useEffect(() => {
    if (!userId) return;
    void loadSoundPref();
    let stopped = false;
    let prev: number | null = null;
    const poll = async () => {
      try {
        const res = await api.get<{ unread_count: number }>('/notifications/unread-count');
        if (stopped) return;
        if (prev !== null && res.unread_count > prev) playNotifySound();
        prev = res.unread_count;
        setState({ id: userId, n: res.unread_count });
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) {
          stopped = true;
          clearInterval(timer);
        }
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), POLL_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [userId]);
  return userId && state?.id === userId ? state.n : 0;
}
