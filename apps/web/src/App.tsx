import { lazy, Suspense } from 'react';
import { Link, Route, Routes } from 'react-router-dom';
import { t } from './i18n';
import { RequireAuth } from './auth/guards';
import { Account } from './pages/Account';
import { Bookings } from './pages/Bookings';
import { Discovery } from './pages/Discovery';
import { Favorites } from './pages/Favorites';
import { Login } from './pages/Login';
import { Profile } from './pages/Profile';
import { Settings } from './pages/Settings';
import { Empty, Loading } from './ui/feedback';
import { Layout } from './ui/Layout';

// Companion studio and the admin console are separate chunks: ordinary visitors never download
// admin code. (Hiding the code is not security — every admin endpoint is authorized on the server.)
const Studio = lazy(() => import('./pages/Studio').then((m) => ({ default: m.Studio })));
const AdminRoutes = lazy(() => import('./admin/routes'));

export function App() {
  return (
    <Suspense fallback={<div className="shell page"><Loading rows={2} /></div>}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Discovery />} />
          <Route path="c/:id" element={<Profile />} />
          <Route path="login" element={<Login />} />
          <Route path="settings" element={<Settings />} />
          <Route path="favorites" element={<RequireAuth><Favorites /></RequireAuth>} />
          <Route path="bookings" element={<RequireAuth><Bookings /></RequireAuth>} />
          <Route path="account" element={<RequireAuth><Account /></RequireAuth>} />
          <Route path="studio" element={<RequireAuth role="companion"><Studio /></RequireAuth>} />
          <Route path="admin/*" element={<RequireAuth role="admin"><AdminRoutes /></RequireAuth>} />
          <Route path="*" element={<Empty title={t('app.notFound.title')} action={<Link className="btn" to="/">{t('app.notFound.home')}</Link>}>{t('app.notFound.body')}</Empty>} />
        </Route>
      </Routes>
    </Suspense>
  );
}
