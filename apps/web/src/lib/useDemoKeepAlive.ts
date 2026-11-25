import { useEffect } from 'react';

const PROBE_INTERVAL_MS = 10 * 60 * 1000;
const FAILURE_RETRY_MS = 60 * 1000;
const REQUEST_TIMEOUT_MS = 20 * 1000;

/**
 * Keep a Render Free demo warm only while a real visitor is actively viewing it.
 * Hidden tabs pause probes; returning after an idle period triggers one immediate probe.
 * This is a UX optimization, not an always-on guarantee: Render Free can still sleep.
 */
export function useDemoKeepAlive(): void {
  useEffect(() => {
    if (!import.meta.env.PROD) return;

    let timer: number | undefined;
    let controller: AbortController | undefined;
    let lastProbeAt = Date.now();
    let nextDelay = PROBE_INTERVAL_MS;
    let disposed = false;

    const clearTimer = () => {
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
    };

    const schedule = () => {
      clearTimer();
      if (disposed || document.visibilityState !== 'visible') return;
      const remaining = Math.max(0, nextDelay - (Date.now() - lastProbeAt));
      timer = window.setTimeout(() => void probe(), remaining);
    };

    const probe = async () => {
      if (disposed || document.visibilityState !== 'visible' || controller) return;
      const current = new AbortController();
      controller = current;
      const timeout = window.setTimeout(() => current.abort(), REQUEST_TIMEOUT_MS);
      try {
        const response = await fetch('/health', {
          method: 'GET',
          cache: 'no-store',
          credentials: 'omit',
          signal: current.signal,
        });
        lastProbeAt = Date.now();
        nextDelay = response.ok ? PROBE_INTERVAL_MS : FAILURE_RETRY_MS;
      } catch {
        if (!current.signal.aborted || !disposed) {
          lastProbeAt = Date.now();
          nextDelay = FAILURE_RETRY_MS;
        }
      } finally {
        window.clearTimeout(timeout);
        if (controller === current) controller = undefined;
        schedule();
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState !== 'visible') {
        clearTimer();
        controller?.abort();
        return;
      }
      schedule();
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    schedule();

    return () => {
      disposed = true;
      clearTimer();
      controller?.abort();
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);
}
