import { useCallback, useEffect, useEffectEvent, useState } from 'react';
import { ApiError } from '../api/client';

export interface Resource<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
  setData: (value: T) => void;
}

interface Snapshot<T> {
  /** Identity of the inputs this snapshot belongs to (never shown for a different key). */
  key: string;
  /** Identity of the exact request (key + reload counter) that produced it. */
  request: string;
  data?: T;
  error?: ApiError;
}

/** Load a resource; re-runs when `key` changes or `reload()` is called. Stale responses are discarded. */
export function useResource<T>(load: (signal: AbortSignal) => Promise<T>, key: unknown[]): Resource<T> {
  const serialized = JSON.stringify(key);
  const [tick, setTick] = useState(0);
  const [snap, setSnap] = useState<Snapshot<T>>();
  const request = `${serialized}#${tick}`;
  const run = useEffectEvent(load);

  useEffect(() => {
    const controller = new AbortController();
    run(controller.signal)
      .then((data) => !controller.signal.aborted && setSnap({ key: serialized, request, data }))
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setSnap({ key: serialized, request, error: e instanceof ApiError ? e : new ApiError(0, 'network_error') });
      });
    return () => controller.abort();
  }, [serialized, request]);

  const current = snap?.key === serialized ? snap : undefined;
  const reload = useCallback(() => setTick((n) => n + 1), []);
  const setData = useCallback(
    (data: T) => setSnap({ key: serialized, request: `${serialized}#${tick}`, data }),
    [serialized, tick],
  );
  return {
    // After reload() the previous data stays visible until the new response arrives.
    data: current?.data,
    error: current?.request === request || current?.error ? current?.error : undefined,
    loading: current?.request !== request,
    reload,
    setData,
  };
}
