import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { ApiError, api, onSessionExpired, tokens, type Schemas } from './api';
import { LEGAL_VERSIONS, applyLocaleTag, getLocaleTag, onLocaleChange, type LegalDoc } from './shared';

export type User = Schemas['UserResponse'];
type State = { status: 'loading' } | { status: 'anon' } | { status: 'authed'; user: User };

interface AuthApi {
  state: State;
  user: User | null;
  requestCode: (phone: string) => Promise<Schemas['OtpRequestResponse']>;
  verify: (phone: string, code: string, acceptLegal: boolean) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
}
const Ctx = createContext<AuthApi | null>(null);

/** Same rule as the web client: the server refuses any other version, so shown text and consent never drift. */
export async function acceptLegal(docs: readonly LegalDoc[] = ['terms', 'privacy']) {
  for (const document of docs) {
    await api.post('/account/consents', { document, version: LEGAL_VERSIONS[document] });
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(tokens.has() ? { status: 'loading' } : { status: 'anon' });

  const resolve = useCallback(async (): Promise<State> => {
    try {
      return { status: 'authed', user: await api.get<User>('/auth/me') };
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        await tokens.clear();
        return { status: 'anon' };
      }
      return { status: 'anon' }; // server unreachable: the login screen explains on the next request
    }
  }, []);
  const reload = useCallback(async () => setState(await resolve()), [resolve]);

  useEffect(() => {
    let live = true;
    if (tokens.has()) void resolve().then((next) => live && setState(next));
    const off = onSessionExpired(() => setState({ status: 'anon' }));
    return () => {
      live = false;
      off();
    };
  }, [resolve]);

  // The interface language follows the account across devices (users.ui_locale), as on the web.
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
      applyLocaleTag(authedUser.ui_locale).catch(() => {});
    } else if (!authedUser.ui_locale) {
      save();
    }
    return onLocaleChange(save);
  }, [authedUser]);

  const value = useMemo<AuthApi>(
    () => ({
      state,
      user: state.status === 'authed' ? state.user : null,
      requestCode: (phone) =>
        api.post<Schemas['OtpRequestResponse']>('/auth/otp/request', { phone_number: phone }, { anonymous: true }),
      verify: async (phone, code, accept) => {
        const pair = await api.post<Schemas['TokenResponse']>('/auth/otp/verify', { phone_number: phone, code }, { anonymous: true });
        await tokens.set(pair);
        if (accept) await acceptLegal().catch(() => {}); // the consent gate asks again if this did not land
        await reload();
      },
      logout: async () => {
        try {
          await api.post('/auth/logout');
        } catch {
          /* the local session is dropped regardless */
        }
        await tokens.clear();
        setState({ status: 'anon' });
      },
      reload,
    }),
    [state, reload],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
