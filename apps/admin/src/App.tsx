import { useState } from 'react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import { AuditPage } from './pages/admin/Audit';
import { BookingDetailPage, BookingsPage } from './pages/admin/Bookings';
import { CompanionsPage } from './pages/admin/Companions';
import { DashboardPage } from './pages/admin/Dashboard';
import { DisputesPage } from './pages/admin/Disputes';
import { FinancePage } from './pages/admin/Finance';
import { GiftOrdersPage, ProductsPage, VendorsPage } from './pages/admin/Marketplace';
import { ReportsPage } from './pages/admin/Reports';
import { ReviewsPage } from './pages/admin/Reviews';
import { SosPage } from './pages/admin/Sos';
import { UserDetailPage, UsersPage } from './pages/admin/Users';
import { VerificationsPage } from './pages/admin/Verifications';
import { VendorEarningsPage } from './pages/vendor/Earnings';
import { VendorOrdersPage } from './pages/vendor/Orders';
import { VendorProductsPage } from './pages/vendor/Products';
import { VendorShopPage } from './pages/vendor/Shop';
import { ErrorBox, messageOf } from './ui';

const ADMIN_LINKS: [string, string][] = [
  ['/admin', 'Dashboard'],
  ['/admin/users', 'Foydalanuvchilar'],
  ['/admin/companions', 'Companion arizalari'],
  ['/admin/verifications', 'Verification'],
  ['/admin/bookings', 'Bronlar'],
  ['/admin/finance', "To'lovlar va payout"],
  ['/admin/reports', 'Reportlar'],
  ['/admin/disputes', 'Nizolar'],
  ['/admin/reviews', 'Sharhlar'],
  ['/admin/sos', 'SOS'],
  ['/admin/vendors', 'Vendorlar'],
  ['/admin/products', 'Mahsulotlar'],
  ['/admin/gift-orders', "Sovg'a buyurtmalari"],
  ['/admin/audit', 'Audit log'],
];

const VENDOR_LINKS: [string, string][] = [
  ['/vendor', "Do'kon"],
  ['/vendor/products', 'Mahsulotlar'],
  ['/vendor/orders', 'Buyurtmalar'],
  ['/vendor/earnings', 'Daromad va reyting'],
];

export function App() {
  const { me, loading, isAdmin, isVendor, logout } = useAuth();
  if (loading) return <div className="login muted">Yuklanmoqda…</div>;
  if (!me) return <LoginPage />;
  if (!isAdmin && !isVendor) {
    return (
      <div className="login">
        <div className="card">
          <h1>Ruxsat yo'q</h1>
          <p className="muted">
            Bu panel administratorlar va vendorlar uchun. Vendor bo'lish uchun ilovada "vendor" rolini tanlang.
          </p>
          <button onClick={() => void logout()}>Chiqish</button>
        </div>
      </div>
    );
  }
  const home = isAdmin ? '/admin' : '/vendor';
  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="brand">Yondo Panel</div>
        {isAdmin && <div className="group">Admin</div>}
        {isAdmin && ADMIN_LINKS.map(([to, text]) => <NavLink key={to} to={to} end>{text}</NavLink>)}
        {isVendor && <div className="group">Vendor</div>}
        {isVendor && VENDOR_LINKS.map(([to, text]) => <NavLink key={to} to={to} end>{text}</NavLink>)}
        <div className="footer">
          <div>{me.display_name ?? me.phone_number}</div>
          <button className="link" onClick={() => void logout()}>
            Chiqish
          </button>
        </div>
      </nav>
      <main className="main">
        <Routes>
          {isAdmin && (
            <>
              <Route path="/admin" element={<DashboardPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
              <Route path="/admin/users/:userId" element={<UserDetailPage />} />
              <Route path="/admin/companions" element={<CompanionsPage />} />
              <Route path="/admin/verifications" element={<VerificationsPage />} />
              <Route path="/admin/bookings" element={<BookingsPage />} />
              <Route path="/admin/bookings/:bookingId" element={<BookingDetailPage />} />
              <Route path="/admin/finance" element={<FinancePage />} />
              <Route path="/admin/reports" element={<ReportsPage />} />
              <Route path="/admin/disputes" element={<DisputesPage />} />
              <Route path="/admin/reviews" element={<ReviewsPage />} />
              <Route path="/admin/sos" element={<SosPage />} />
              <Route path="/admin/vendors" element={<VendorsPage />} />
              <Route path="/admin/products" element={<ProductsPage />} />
              <Route path="/admin/gift-orders" element={<GiftOrdersPage />} />
              <Route path="/admin/audit" element={<AuditPage />} />
            </>
          )}
          {isVendor && (
            <>
              <Route path="/vendor" element={<VendorShopPage />} />
              <Route path="/vendor/products" element={<VendorProductsPage />} />
              <Route path="/vendor/orders" element={<VendorOrdersPage />} />
              <Route path="/vendor/earnings" element={<VendorEarningsPage />} />
            </>
          )}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
      </main>
    </div>
  );
}

function LoginPage() {
  const { requestOtp, verifyOtp } = useAuth();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!sent) {
        const devCode = await requestOtp(phone);
        setSent(true);
        setHint(devCode ? `Development kodi: ${devCode}` : 'SMS kod yuborildi.');
      } else {
        await verifyOtp(phone, code);
      }
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <h1>Yondo Panel</h1>
        <p className="muted">Administrator yoki vendor sifatida telefon raqam orqali kiring.</p>
        <label className="field">
          <span>Telefon raqam</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+998 90 123 45 67" disabled={sent} autoFocus />
        </label>
        {sent && (
          <label className="field">
            <span>SMS kod</span>
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" maxLength={6} autoFocus />
          </label>
        )}
        {hint && <div className="notice">{hint}</div>}
        <ErrorBox error={error} />
        <button className="primary" disabled={busy || !phone || (sent && code.length !== 6)}>
          {sent ? 'Kirish' : 'Kod olish'}
        </button>
        {sent && (
          <button type="button" className="link" onClick={() => { setSent(false); setCode(''); setHint(null); }}>
            Raqamni o'zgartirish
          </button>
        )}
      </form>
    </div>
  );
}
