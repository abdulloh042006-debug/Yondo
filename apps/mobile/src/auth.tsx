import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, loadTokens, setTokens } from './api';
import { registerForPush } from './push';
import type { Me } from './types';

interface AuthState {
  me: Me | null;
  loading: boolean;
  requestOtp: (phone: string) => Promise<string | undefined>;
  verifyOtp: (phone: string, code: string) => Promise<void>;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      setMe(await api.get<Me>('/auth/me'));
    } catch {
      await setTokens(null);
      setMe(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      if (await loadTokens()) await refreshMe();
      setLoading(false);
    })();
  }, [refreshMe]);

  useEffect(() => {
    if (me) void registerForPush();
  }, [me?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const value: AuthState = {
    me,
    loading,
    refreshMe,
    requestOtp: async (phone) => {
      const result = await api.post<{ development_otp?: string }>('/auth/otp/request', { phone_number: phone });
      return result.development_otp;
    },
    verifyOtp: async (phone, code) => {
      const tokens = await api.post<{ access_token: string; refresh_token: string }>('/auth/otp/verify', { phone_number: phone, code });
      await setTokens({ access_token: tokens.access_token, refresh_token: tokens.refresh_token });
      await refreshMe();
    },
    logout: async () => {
      try {
        await api.post('/auth/logout');
      } finally {
        await setTokens(null);
        setMe(null);
      }
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
