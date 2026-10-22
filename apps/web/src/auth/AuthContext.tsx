import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, ApiError, onSessionExpired, tokens, type Schemas } from '../api/client';

export type User = Schemas['UserResponse'];
type State = { status: 'loading' } | { status: 'anon' } | { status: 'authed'; user: User };

interface AuthApi {
  state: State;
  user: User | null;
  /** UI convenience only; every privileged endpoint re-checks the role on the server. */
  isAdmin: boolean;
  isCompanion: boolean;
  requestCode: (phone: string) => Promise<Schemas['OtpRequestResponse']>;
  verify: (phone: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
}

const Ctx = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(tokens.has() ? { status: 'loading' } : { status: 'anon' });

  /** Resolve the current session into a State without touching React state. */
  const resolve = useCallback(async (): Promise<State> => {
    try {
      return { status: 'authed', user: await api.get<User>('/auth/me') };
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        tokens.clear();
        return { status: 'anon' };
      }
      if (e instanceof ApiError && e.unavailable) return { status: 'anon' }; // server temporarily unreachable
      throw e;
    }
  }, []);
  const reload = useCallback(async () => setState(await resolve()), [resolve]);

  useEffect(() => {
    let live = true;
    if (tokens.has()) {
      resolve()
        .then((next) => live && setState(next))
        .catch(() => live && setState({ status: 'anon' }));
    }
    const off = onSessionExpired(() => setState({ status: 'anon' }));
    return () => {
      live = false;
      off();
    };
  }, [resolve]);

  const value = useMemo<AuthApi>(() => {
    const user = state.status === 'authed' ? state.user : null;
    return {
      state,
      user,
      isAdmin: !!user?.roles.includes('admin'),
      isCompanion: !!user?.roles.includes('companion'),
      requestCode: (phone) =>
        api.post<Schemas['OtpRequestResponse']>('/auth/otp/request', { phone_number: phone }, { anonymous: true }),
      verify: async (phone, code) => {
        const pair = await api.post<Schemas['TokenResponse']>(
          '/auth/otp/verify',
          { phone_number: phone, code },
          { anonymous: true },
        );
        tokens.set(pair);
        await reload();
      },
      logout: async () => {
        try {
          await api.post('/auth/logout');
        } catch {
          /* the local session is dropped regardless; the server token expires on its own */
        }
        tokens.clear();
        setState({ status: 'anon' });
      },
      reload,
    };
  }, [state, reload]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
