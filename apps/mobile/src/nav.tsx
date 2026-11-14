import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

/**
 * A small stack per tab is all the app needs; no navigation library (fewer native dependencies).
 * The tabs are the web app's bottom dock (apps/web/src/ui/Layout.tsx): signed in = Kashf · Sevimlilar · Bronlar ·
 * Profil; signed out = Kashf · Kirish. Settings is not a tab: it opens from the Profil hub (and from Kirish).
 */
export type Route =
  | { name: 'discover' }
  | { name: 'profile'; id: string }
  | { name: 'favorites' }
  | { name: 'bookings' }
  | { name: 'booking'; id: string }
  | { name: 'account' }
  | { name: 'settings' }
  | { name: 'login'; then?: Route };
export type Tab = 'discover' | 'favorites' | 'bookings' | 'account' | 'login';

interface NavApi {
  tab: Tab;
  route: Route;
  canGoBack: boolean;
  push: (route: Route) => void;
  back: () => void;
  switchTab: (tab: Tab) => void;
  /** Back to the tab roots on the Kashf tab (after sign-in/out, so no screen of another account stays open). */
  reset: () => void;
}
const Ctx = createContext<NavApi | null>(null);
const ROOT: Record<Tab, Route> = {
  discover: { name: 'discover' },
  favorites: { name: 'favorites' },
  bookings: { name: 'bookings' },
  account: { name: 'account' },
  login: { name: 'login' },
};
const roots = (): Record<Tab, Route[]> => ({
  discover: [ROOT.discover],
  favorites: [ROOT.favorites],
  bookings: [ROOT.bookings],
  account: [ROOT.account],
  login: [ROOT.login],
});
interface State {
  tab: Tab;
  stacks: Record<Tab, Route[]>;
}

export function NavProvider({ children }: { children: ReactNode }) {
  // One state object, so `reset()` followed by `push()` in the same tick lands on the new tab's stack.
  const [s, setS] = useState<State>(() => ({ tab: 'discover', stacks: roots() }));
  const reset = useCallback(() => setS({ tab: 'discover', stacks: roots() }), []);
  const value = useMemo<NavApi>(() => {
    const stack = s.stacks[s.tab];
    return {
      tab: s.tab,
      route: stack[stack.length - 1],
      canGoBack: stack.length > 1,
      push: (route) => setS((p) => ({ ...p, stacks: { ...p.stacks, [p.tab]: [...p.stacks[p.tab], route] } })),
      back: () =>
        setS((p) => {
          const st = p.stacks[p.tab];
          return st.length > 1 ? { ...p, stacks: { ...p.stacks, [p.tab]: st.slice(0, -1) } } : p;
        }),
      switchTab: (next) =>
        setS((p) => ({
          tab: next,
          // Tapping the active tab again goes back to its root, as on the web dock.
          stacks: next === p.tab ? { ...p.stacks, [next]: [ROOT[next]] } : p.stacks,
        })),
      reset,
    };
  }, [s, reset]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNav(): NavApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useNav must be used inside NavProvider');
  return ctx;
}
