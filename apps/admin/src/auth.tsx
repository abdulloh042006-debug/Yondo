import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, loadTokens, saveTokens, type Me } from './api';

interface AuthState {
  me: Me | null;
  loading: boolean;
  requestOtp: (phone: string) => Promise<string | undefined>;
  verifyOtp: (phone: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isVendor: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!loadTokens()) {
      setMe(null);
      return;
    }
    try {
      setMe(await api.get<Me>('/auth/me'));
    } catch {
      saveTokens(null);
      setMe(null);
    }
  }, []);

  useEffect(() => {
    loadMe().finally(() => setLoading(false));
  }, [loadMe]);

  const value: AuthState = {
    me,
    loading,
    isAdmin: !!me?.roles.includes('admin'),
    isVendor: !!me?.roles.includes('vendor'),
    requestOtp: async (phone) => {
      const result = await api.post<{ development_otp?: string }>('/auth/otp/request', {
        phone_number: phone,
      });
      return result.development_otp;
    },
    verifyOtp: async (phone, code) => {
      const tokens = await api.post<{ access_token: string; refresh_token: string }>(
        '/auth/otp/verify',
        { phone_number: phone, code },
      );
      saveTokens({ access_token: tokens.access_token, refresh_token: tokens.refresh_token });
      await loadMe();
    },
    logout: async () => {
      try {
        await api.post('/auth/logout');
      } finally {
        saveTokens(null);
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
