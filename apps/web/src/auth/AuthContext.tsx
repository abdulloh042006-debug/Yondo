import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, ApiError, onSessionExpired, tokens, type Schemas } from '../api/client';
import { applyLocaleTag, getLocaleTag, onLocaleChange } from '../i18n';
import { acceptLegal } from '../legal/consent';

export type User = Schemas['UserResponse'];
type State = { status: 'loading' } | { status: 'anon' } | { status: 'authed'; user: User };

interface AuthApi {
  state: State;
  user: User | null;
  /** UI convenience only; every privileged endpoint re-checks the role on the server. */
  isAdmin: boolean;
  isCompanion: boolean;
  requestCode: (phone: string) => Promise<Schemas['OtpRequestResponse']>;
  /** `acceptLegal`: the user ticked the consent box; it is recorded right after the session starts. */
  verify: (phone: string, code: string, opts?: { acceptLegal?: boolean }) => Promise<void>;
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

  // Interface language follows the account across devices (users.ui_locale), without overriding the device
  // when the account has none yet: then the device's choice is saved to the account.
  const authedUser = state.status === 'authed' ? state.user : null;
  useEffect(() => {
    if (!authedUser) return;
    const save = () => {
      const tag = getLocaleTag();
      if (tag === authedUser.ui_locale) return;
      api
        .put<User>('/auth/profile', { ui_locale: tag })
        .then((user) => setState((s) => (s.status === 'authed' && s.user.id === user.id ? { status: 'authed', user } : s)))
        .catch(() => {
          /* not critical: the choice is still stored on this device */
        });
    };
    if (authedUser.ui_locale && authedUser.ui_locale !== getLocaleTag()) {
      applyLocaleTag(authedUser.ui_locale).catch(() => {
        /* language chunk unavailable: keep the current language */
      });
    } else if (!authedUser.ui_locale) {
      save();
    }
    return onLocaleChange(save);
  }, [authedUser]);

  const value = useMemo<AuthApi>(() => {
    const user = state.status === 'authed' ? state.user : null;
    return {
      state,
      user,
      isAdmin: !!user?.roles.includes('admin'),
      isCompanion: !!user?.roles.includes('companion'),
      requestCode: (phone) =>
        api.post<Schemas['OtpRequestResponse']>('/auth/otp/request', { phone_number: phone }, { anonymous: true }),
      verify: async (phone, code, opts) => {
        const pair = await api.post<Schemas['TokenResponse']>(
          '/auth/otp/verify',
          { phone_number: phone, code },
          { anonymous: true },
        );
        tokens.set(pair);
        if (opts?.acceptLegal) {
          await acceptLegal().catch(() => {
            /* the consent gate asks again if this did not land */
          });
        }
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
