import { useState } from 'react';
import { api, type Schemas } from '../api/client';
import { t, type Key } from '../i18n';
import { formatInstant } from '../lib/format';
import { BOOKING_STATUS } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading, StatusTag } from '../ui/feedback';
import { Select } from '../ui/form';
import { Id, PAGE_SIZE, Pager } from './shared';

export function AdminBookings() {
  const [offset, setOffset] = useState(0);
  const res = useResource((signal) => api.get<Schemas['AdminBookingRead'][]>('/admin/bookings', { query: { limit: PAGE_SIZE, offset }, signal }), [offset]);
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">{t('admin.bookings.banner')}</p>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('admin.bookings.none')} /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>ID</th><th>{t('admin.col.status')}</th><th>{t('admin.col.created')}</th></tr></thead>
            <tbody>{res.data.map((b) => <tr key={b.id}><td><Id value={b.id} /></td><td><StatusTag map={BOOKING_STATUS} value={b.status} /></td><td>{formatInstant(b.created_at)}</td></tr>)}</tbody>
          </table>
        </div>
      )}
      {res.data && <Pager offset={offset} count={res.data.length} onChange={setOffset} />}
    </div>
  );
}

const ACTIONS = [
  ['', 'discovery.all'],
  ['account_status', 'admin.audit.account_status'],
  ['companion_application', 'studio.app.title'],
  ['companion_content', 'studio.status.content'],
  ['safety_report', 'admin.audit.safety_report'],
  ['safety_sos', 'admin.audit.safety_sos'],
] as const satisfies ReadonlyArray<readonly [string, Key]>;

export function AuditLog() {
  const [offset, setOffset] = useState(0);
  const [prefix, setPrefix] = useState('');
  const res = useResource(
    (signal) => api.get<Schemas['AdminAuditRead'][]>('/admin/audit-events', { query: { limit: PAGE_SIZE, offset, action_prefix: prefix || undefined }, signal }),
    [offset, prefix],
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">{t('admin.audit.banner')}</p>
      <div style={{ maxWidth: 280 }}>
        <Select label={t('admin.audit.type')} value={prefix} onChange={(e) => { setOffset(0); setPrefix(e.target.value); }}>
          {ACTIONS.map(([v, l]) => <option key={v} value={v}>{t(l)}</option>)}
        </Select>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('admin.audit.none')} /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>{t('common.time')}</th><th>{t('admin.col.action')}</th><th>{t('role.admin')}</th><th>{t('admin.col.target')}</th><th>{t('admin.col.reason')}</th></tr></thead>
            <tbody>{res.data.map((e) => (
              <tr key={e.id}><td>{formatInstant(e.created_at)}</td><td className="mono">{e.action}</td><td><Id value={e.admin_id} /></td><td><Id value={e.target_id} /></td><td>{e.reason}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {res.data && <Pager offset={offset} count={res.data.length} onChange={setOffset} />}
    </div>
  );
}
