import { useCallback, useEffect, useRef, useState } from 'react';

/** Load data for a screen; `reload()` re-runs the loader. Stale responses are ignored. */
export function useResource<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const run = useRef(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loader = useCallback(load, deps);
  const reload = useCallback(() => {
    const id = ++run.current;
    setLoading(true);
    setError(undefined);
    loader()
      .then((value) => id === run.current && setData(value))
      .catch((e: unknown) => id === run.current && setError(e))
      .finally(() => id === run.current && setLoading(false));
  }, [loader]);
  useEffect(() => {
    reload();
    return () => {
      run.current++;
    };
  }, [reload]);
  return { data, setData, error, loading, reload };
}
