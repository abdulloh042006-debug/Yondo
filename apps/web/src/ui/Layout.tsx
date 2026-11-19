import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { IntroHost } from './Intro';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { ConsentGate } from './Consent';
import { PasswordSetupGate } from '../auth/PasswordSetup';
import { PageTransition } from './motion';
import { ShockwaveDock } from './ShockwaveDock';
import { useUnreadNotifications } from '../lib/useUnreadNotifications';

const Icon = ({ d }: { d: string }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);
const ICONS = {
  home: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  heart: 'M12 21s-7-4.4-9.3-9A5.4 5.4 0 0 1 12 6a5.4 5.4 0 0 1 9.3 6C19 16.6 12 21 12 21z',
  cal: 'M7 3v3m10-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0',
  shield: 'M12 3l8 3v6c0 4.5-3.2 8.2-8 9-4.8-.8-8-4.5-8-9V6z',
};

/** Carrot dot (graphic only, no text) on the Profil item while notifications are unread. */
function UnreadDot() {
  return (
    <>
      <span className="unread-dot" aria-hidden="true" />
      <span className="sr-only">{t('nav.unread')}</span>
    </>
  );
}

/** Official Yondo symbol (design-prototype/brand/logo): two converging lines, ink + the single accent node. */
function BrandMark() {
  return (
    <svg className="brand-mark" width="30" height="30" viewBox="0 0 64 64" aria-hidden="true">
      <g stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="9">
        <path d="M16 15 28 34Q31 38 32 40M48 15 36 34Q33 38 32 40M32 40v17" />
      </g>
      <circle cx="16" cy="15" r="9" fill="currentColor" />
      <circle cx="48" cy="15" r="9" fill="#E8501A" />
    </svg>
  );
}

function Pill() {
  return (
    <motion.span
      layoutId="nav-pill"
      className="nav-pill"
      transition={{ type: 'spring', stiffness: 420, damping: 34 }}
    />
  );
}

export function Layout() {
  const { user, state } = useAuth();
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const unreadCount = useUnreadNotifications();
  const items = [
    { to: '/', label: t('nav.discover'), icon: ICONS.home, end: true },
    ...(user ? [{ to: '/favorites', label: t('nav.favorites'), icon: ICONS.heart, end: false }] : []),
    ...(user ? [{ to: '/bookings', label: t('nav.bookings'), icon: ICONS.cal, end: false }] : []),
    { to: user ? '/account' : '/login', label: user ? t('nav.profile') : t('nav.login'), icon: ICONS.user, end: false, dot: Boolean(user) && unreadCount > 0 },
    ...(user?.roles.includes('admin') ? [{ to: '/admin', label: t('nav.admin'), icon: ICONS.shield, end: false }] : []),
  ];
  return (
    <>
      <IntroHost />
      <div className="aurora" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      <a href="#main" className="skip-link">
        {t('nav.skip')}
      </a>
      <div className="shell">
        <header className={`glass-bar topbar${scrolled ? ' scrolled' : ''}`}>
          <NavLink to="/" className="brand" aria-label={t('nav.brandHome')}>
            <BrandMark />
            Yondo
          </NavLink>
          <nav className="topnav" aria-label={t('nav.main')}>
            {items.map((i) => (
              <NavLink key={i.to} to={i.to} end={i.end}>
                {({ isActive }) => (
                  <>
                    {isActive && <Pill />}
                    {i.label}
                    {'dot' in i && i.dot && <UnreadDot />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          {/* Owner, 2026-11-15: the header is the logo and the navigation only. Language is chosen on Kirish and in
              Settings; SOS lives on Help and on confirmed/active bookings (CLAUDE.md S25). */}
        </header>
        <main id="main" className="page" tabIndex={-1}>
          <PageTransition key={location.pathname.split('/').slice(0, 2).join('/')}>
            <ConsentGate>
              <PasswordSetupGate>
                <Outlet />
              </PasswordSetupGate>
            </ConsentGate>
          </PageTransition>
          {state.status === 'loading' && <span className="sr-only">{t('nav.sessionChecking')}</span>}
          <footer className="site-foot">
            <NavLink to="/help">{t('help.title')}</NavLink>
            <NavLink to="/settings">{t('settings.title')}</NavLink>
            <NavLink to="/terms">{t('legal.terms')}</NavLink>
            <NavLink to="/privacy">{t('legal.privacy')}</NavLink>
          </footer>
        </main>
      </div>
      <ShockwaveDock
        label={t('nav.mobile')}
        items={items.map((i) => ({ to: i.to, label: i.label, end: i.end, icon: <Icon d={i.icon} />, extra: 'dot' in i && i.dot ? <UnreadDot /> : null }))}
      />
    </>
  );
}
