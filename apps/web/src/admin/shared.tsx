import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { motion } from 'motion/react';
import { shortId } from '../lib/format';

export const PAGE_SIZE = 25;

export function AdminLayout() {
  const links = [
    ['/admin', 'Umumiy', true],
    ['/admin/applications', 'Arizalar', false],
    ['/admin/safety', 'Xavfsizlik', false],
    ['/admin/users', 'Foydalanuvchilar', false],
    ['/admin/bookings', 'Bronlar', false],
    ['/admin/audit', 'Audit jurnali', false],
  ] as const;
  return (
    <div className="admin-layout">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Administrator paneli</h1>
        <span className="tag warn">Barcha amallar serverda tekshiriladi va audit qilinadi</span>
      </div>
      <nav className="glass-bar admin-nav" aria-label="Admin bo‘limlari">
        {links.map(([to, label, end]) => (
          <NavLink key={to} to={to} end={end}>
            {({ isActive }) => (
              <>
                {isActive && <motion.span layoutId="admin-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                {label}
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
      <button className="btn sm ghost" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}>← Oldingi</button>
      <span className="hint">{count === 0 ? '—' : `${offset + 1}–${offset + count}`}</span>
      <button className="btn sm ghost" disabled={count < PAGE_SIZE} onClick={() => onChange(offset + PAGE_SIZE)}>Keyingi →</button>
    </div>
  );
}

export function Id({ value }: { value: string }) {
  const [full, setFull] = useState(false);
  return (
    <button className="mono" style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', color: 'inherit', minHeight: 24 }} title="To‘liq ID ni ko‘rsatish" onClick={() => setFull((f) => !f)}>
      {full ? value : shortId(value)}
    </button>
  );
}
