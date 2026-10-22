import { useState } from 'react';
import { api, type Schemas } from '../api/client';
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
      <p className="banner">Faqat ko‘rish: server bronlar bo‘yicha ma’mur amallarini (to‘lov qayta ishlash, qaytarish) taqdim etmaydi.</p>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title="Bronlar yo‘q" /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>ID</th><th>Holat</th><th>Yaratilgan</th></tr></thead>
            <tbody>{res.data.map((b) => <tr key={b.id}><td><Id value={b.id} /></td><td><StatusTag map={BOOKING_STATUS} value={b.status} /></td><td>{formatInstant(b.created_at)}</td></tr>)}</tbody>
          </table>
        </div>
      )}
      {res.data && <Pager offset={offset} count={res.data.length} onChange={setOffset} />}
    </div>
  );
}

const ACTIONS = [
  ['', 'Hammasi'],
  ['account_status', 'Hisob holati'],
  ['companion_application', 'Hamroh arizasi'],
  ['companion_content', 'Profil kontenti'],
  ['safety_report', 'Shikoyat'],
  ['safety_sos', 'SOS'],
] as const;

export function AuditLog() {
  const [offset, setOffset] = useState(0);
  const [prefix, setPrefix] = useState('');
  const res = useResource(
    (signal) => api.get<Schemas['AdminAuditRead'][]>('/admin/audit-events', { query: { limit: PAGE_SIZE, offset, action_prefix: prefix || undefined }, signal }),
    [offset, prefix],
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">Audit yozuvlari server tomonidan, qaror bilan bir tranzaksiyada yoziladi. Faqat o‘qish mumkin.</p>
      <div style={{ maxWidth: 280 }}>
        <Select label="Turi" value={prefix} onChange={(e) => { setOffset(0); setPrefix(e.target.value); }}>
          {ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title="Yozuvlar yo‘q" /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>Vaqt</th><th>Amal</th><th>Administrator</th><th>Maqsad</th><th>Sabab</th></tr></thead>
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
