import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

/** A small stack per tab is all the app needs; no navigation library (fewer native dependencies). */
export type Route =
  | { name: 'discover' }
  | { name: 'profile'; id: string }
  | { name: 'bookings' }
  | { name: 'booking'; id: string }
  | { name: 'settings' }
  | { name: 'login'; then?: Route };
export type Tab = 'discover' | 'bookings' | 'settings';

interface NavApi {
  tab: Tab;
  route: Route;
  canGoBack: boolean;
  push: (route: Route) => void;
  back: () => void;
  switchTab: (tab: Tab) => void;
  /** Back to the tab roots (after sign-in/out, so no screen of another account stays open). */
  reset: () => void;
}
const Ctx = createContext<NavApi | null>(null);
const ROOT: Record<Tab, Route> = { discover: { name: 'discover' }, bookings: { name: 'bookings' }, settings: { name: 'settings' } };

export function NavProvider({ children }: { children: ReactNode }) {
  const [tab, setTab] = useState<Tab>('discover');
  const [stacks, setStacks] = useState<Record<Tab, Route[]>>({ discover: [ROOT.discover], bookings: [ROOT.bookings], settings: [ROOT.settings] });
  const reset = useCallback(() => setStacks({ discover: [ROOT.discover], bookings: [ROOT.bookings], settings: [ROOT.settings] }), []);
  const value = useMemo<NavApi>(() => {
    const stack = stacks[tab];
    return {
      tab,
      route: stack[stack.length - 1],
      canGoBack: stack.length > 1,
      push: (route) => setStacks((s) => ({ ...s, [tab]: [...s[tab], route] })),
      back: () => setStacks((s) => ({ ...s, [tab]: s[tab].length > 1 ? s[tab].slice(0, -1) : s[tab] })),
      switchTab: (next) => {
        if (next === tab) setStacks((s) => ({ ...s, [next]: [ROOT[next]] }));
        setTab(next);
      },
      reset,
    };
  }, [tab, stacks, reset]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNav(): NavApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useNav must be used inside NavProvider');
  return ctx;
}
