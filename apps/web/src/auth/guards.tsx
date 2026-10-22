import { Navigate, useLocation } from 'react-router-dom';
import { Empty, Loading } from '../ui/feedback';
import { useAuth } from './AuthContext';
import type { ReactNode } from 'react';

export function RequireAuth({ children, role }: { children: ReactNode; role?: 'admin' | 'companion' }) {
  const { state, user } = useAuth();
  const location = useLocation();
  if (state.status === 'loading') return <Loading rows={2} />;
  if (state.status === 'anon') return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (role && !user?.roles.includes(role)) {
    return (
      <Empty title="Bu bo‘lim siz uchun emas">
        {role === 'admin'
          ? 'Administrator paneli faqat administrator rolidagi hisoblar uchun.'
          : 'Avval hisobingizda hamroh rolini tanlang.'}
      </Empty>
    );
  }
  return <>{children}</>;
}
