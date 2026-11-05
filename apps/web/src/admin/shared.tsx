import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { motion } from 'motion/react';
import { t, type Key } from '../i18n';
import { shortId } from '../lib/format';

export const PAGE_SIZE = 25;

export function AdminLayout() {
  const links = [
    ['/admin', 'admin.nav.overview', true],
    ['/admin/applications', 'admin.nav.applications', false],
    ['/admin/safety', 'admin.nav.safety', false],
    ['/admin/users', 'admin.nav.users', false],
    ['/admin/support', 'admin.nav.support', false],
    ['/admin/deletions', 'admin.nav.deletions', false],
    ['/admin/bookings', 'nav.bookings', false],
    ['/admin/audit', 'admin.nav.audit', false],
  ] as const satisfies ReadonlyArray<readonly [string, Key, boolean]>;
  return (
    <div className="admin-layout">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>{t('admin.title')}</h1>
        <span className="tag warn">{t('admin.serverNote')}</span>
      </div>
      <nav className="glass-bar admin-nav" aria-label={t('admin.navAria')}>
        {links.map(([to, labelKey, end]) => (
          <NavLink key={to} to={to} end={end}>
            {({ isActive }) => (
              <>
                {isActive && <motion.span layoutId="admin-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                {t(labelKey)}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}

export function Pager({ offset, count, onChange }: { offset: number; count: number; onChange: (offset: number) => void }) {
  return (
    <div className="row" style={{ justifyContent: 'space-between' }}>
      <button className="btn sm ghost" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}>{t('common.prev')}</button>
      <span className="hint">{count === 0 ? '—' : `${offset + 1}–${offset + count}`}</span>
      <button className="btn sm ghost" disabled={count < PAGE_SIZE} onClick={() => onChange(offset + PAGE_SIZE)}>{t('common.next')}</button>
    </div>
  );
}

export function Id({ value }: { value: string }) {
  const [full, setFull] = useState(false);
  return (
    <button className="mono" style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', color: 'inherit', minHeight: 24 }} title={t('admin.idShowFull')} onClick={() => setFull((f) => !f)}>
      {full ? value : shortId(value)}
    </button>
  );
}
