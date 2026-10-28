import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { LanguageSwitch } from '../i18n/LanguageSwitch';
import { BrandMark } from './Brand';
import { ConsentGate } from './Consent';
import { Icon } from './Icon';
import { IntroHost } from './Intro';
import { OnboardingHost } from './Onboarding';
import { SosButton } from './Sos';
import { PageTransition } from './motion';

const ICONS = { home: 'home', heart: 'heart', cal: 'cal', user: 'user', shield: 'shield' } as const;

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
  const items = [
    { to: '/', label: t('nav.discover'), icon: ICONS.home, end: true },
    ...(user ? [{ to: '/favorites', label: t('nav.favorites'), icon: ICONS.heart, end: false }] : []),
    ...(user ? [{ to: '/bookings', label: t('nav.bookings'), icon: ICONS.cal, end: false }] : []),
    { to: user ? '/account' : '/login', label: user ? t('nav.profile') : t('nav.login'), icon: ICONS.user, end: false },
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
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          {user && <SosButton />}
          <LanguageSwitch />
        </header>
        <main id="main" className="page" tabIndex={-1}>
          <PageTransition key={location.pathname.split('/').slice(0, 2).join('/')}>
            <ConsentGate overlay={<OnboardingHost />}>
              <Outlet />
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
      <nav className="glass-bar dock" aria-label={t('nav.mobile')}>
        {items.map((i) => (
          <NavLink key={i.to} to={i.to} end={i.end}>
            {({ isActive }) => (
              <>
                {isActive && <Pill />}
                <motion.span whileTap={{ scale: 0.8, y: -2 }} transition={{ type: 'spring', stiffness: 500, damping: 18 }} style={{ display: 'grid' }}>
                  <Icon name={i.icon} />
                </motion.span>
                {i.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
