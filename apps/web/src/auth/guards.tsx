import { Navigate, useLocation } from 'react-router-dom';
import { t } from '../i18n';
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
      <Empty title={t('guard.title')}>
        {role === 'admin' ? t('guard.admin') : t('guard.companion')}
      </Empty>
    );
  }
  return <>{children}</>;
}
