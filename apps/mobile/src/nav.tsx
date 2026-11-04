// Minimal stack + tab navigation (no native navigation dependency; works on web too).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { BackHandler } from 'react-native';

export interface Route {
  name: string;
  params?: Record<string, unknown>;
  key: number;
}

interface NavState {
  tab: string;
  route: Route;
  depth: number;
  push: (name: string, params?: Record<string, unknown>) => void;
  replace: (name: string, params?: Record<string, unknown>) => void;
  pop: () => void;
  setTab: (tab: string) => void;
  params: <T = Record<string, unknown>>() => T;
}

const NavContext = createContext<NavState | null>(null);
let counter = 0;

export function NavProvider({ initialTab, children }: { initialTab: string; children: ReactNode }) {
  const [tab, setTabState] = useState(initialTab);
  const [stack, setStack] = useState<Route[]>([{ name: initialTab, key: counter++ }]);

  const push = useCallback((name: string, params?: Record<string, unknown>) => {
    setStack((current) => [...current, { name, params, key: counter++ }]);
  }, []);
  const replace = useCallback((name: string, params?: Record<string, unknown>) => {
    setStack((current) => [...current.slice(0, -1), { name, params, key: counter++ }]);
  }, []);
  const pop = useCallback(() => {
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : current));
  }, []);
  const setTab = useCallback((next: string) => {
    setTabState(next);
    setStack([{ name: next, key: counter++ }]);
  }, []);

  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (stack.length > 1) {
        pop();
        return true;
      }
      return false;
    });
    return () => subscription.remove();
  }, [stack.length, pop]);

  const route = stack[stack.length - 1];
  const value = useMemo<NavState>(() => ({
    tab, route, depth: stack.length, push, replace, pop, setTab,
    params: <T,>() => (route.params ?? {}) as T,
  }), [tab, route, stack.length, push, replace, pop, setTab]);
  return <NavContext.Provider value={value}>{children}</NavContext.Provider>;
}

export function useNav(): NavState {
  const context = useContext(NavContext);
  if (!context) throw new Error('useNav must be used inside NavProvider');
  return context;
}
