"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// TD-6 polling intervals.
export const FOLLOW_MS = 1_000;
export const ACTIVE_MS = 2_000;
export const IDLE_MS = 10_000;
const RETRY_MS = 2_000;

/**
 * Loads data now, then again after `nextDelay(data)` milliseconds, until `nextDelay` returns null.
 * After a failed load it keeps the last data, exposes the error and retries.
 */
export function usePolling<T>(load: () => Promise<T>, nextDelay: (data: T) => number | null, key = "") {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [restarts, setRestarts] = useState(0);
  const loadRef = useRef(load);
  const nextDelayRef = useRef(nextDelay);

  useEffect(() => {
    loadRef.current = load;
    nextDelayRef.current = nextDelay;
  });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const value = await loadRef.current();
        if (cancelled) return;
        setData(value);
        setError(undefined);
        const delay = nextDelayRef.current(value);
        if (delay !== null) timer = setTimeout(poll, delay);
      } catch (caught) {
        if (cancelled) return;
        setError(caught as Error);
        timer = setTimeout(poll, RETRY_MS);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, restarts]);

  const refresh = useCallback(() => setRestarts((count) => count + 1), []);
  return { data, error, refresh };
}
