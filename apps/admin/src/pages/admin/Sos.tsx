import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Page } from '../../api';
import { formatDate, shortId } from '../../format';
import { Badge, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

interface Sos {
  id: string; user_id: string; booking_id: string | null; latitude: number | null;
  longitude: number | null; message: string; status: string; resolution_note: string | null; created_at: string;
}

export function SosPage() {
  const [status, setStatus] = useState('open');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Sos>>('/admin/sos', { status, limit: 50 }), [status],
  );
  const action = useAction();
  const update = (alert: Sos, next: string) => {
    const note = window.prompt('Izoh') ?? '';
    void action.run(() => api.post(`/admin/sos/${alert.id}/status`, { status: next, note }), reload);
  };
  return (
    <div className="stack">
      <PageHeader title="SOS signallari" subtitle="Ochiq signallarga darhol javob bering: foydalanuvchi va kerak bo'lsa 112 bilan bog'laning."
        actions={<Select value={status} onChange={setStatus} options={['', 'open', 'acknowledged', 'resolved']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} empty="SOS signal yo'q" columns={[
        { header: 'Vaqt', render: (s) => formatDate(s.created_at) },
        { header: 'Foydalanuvchi', render: (s) => <Link to={`/admin/users/${s.user_id}`}>{shortId(s.user_id)}</Link> },
        { header: 'Bron', render: (s) => (s.booking_id ? <Link to={`/admin/bookings/${s.booking_id}`}>{shortId(s.booking_id)}</Link> : '—') },
        { header: 'Joylashuv', render: (s) => (s.latitude !== null ? <a target="_blank" rel="noreferrer" href={`https://www.openstreetmap.org/?mlat=${s.latitude}&mlon=${s.longitude}#map=16/${s.latitude}/${s.longitude}`}>Xaritada</a> : '—') },
        { header: 'Xabar', render: (s) => s.message || '—' },
        { header: 'Holat', render: (s) => <Badge value={s.status} /> },
        { header: '', render: (s) => (
          <div className="row">
            {s.status === 'open' && <button className="primary" onClick={() => update(s, 'acknowledged')}>Qabul qilindi</button>}
            {s.status !== 'resolved' && <button onClick={() => update(s, 'resolved')}>Yopish</button>}
          </div>
        ) },
      ]} />}
    </div>
  );
}
