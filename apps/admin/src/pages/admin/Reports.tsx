import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Page } from '../../api';
import { formatDate, shortId } from '../../format';
import { Badge, Card, DecisionForm, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

interface Report {
  id: string; reporter_id: string; reported_user_id: string; booking_id: string | null;
  category: string; description: string; status: string; resolution_note: string | null; created_at: string;
}

export function ReportsPage() {
  const [status, setStatus] = useState('open');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Report>>('/admin/reports', { status, limit: 50 }), [status],
  );
  const [selected, setSelected] = useState<Report | null>(null);
  const action = useAction();
  return (
    <div className="stack">
      <PageHeader title="Reportlar (TZ §24)" actions={<Select value={status} onChange={setStatus} options={['', 'open', 'in_review', 'resolved', 'dismissed']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} onRow={setSelected} columns={[
        { header: 'Kategoriya', render: (r) => r.category },
        { header: 'Kim haqida', render: (r) => <Link to={`/admin/users/${r.reported_user_id}`} onClick={(e) => e.stopPropagation()}>{shortId(r.reported_user_id)}</Link> },
        { header: 'Tavsif', render: (r) => r.description.slice(0, 80) || '—' },
        { header: 'Holat', render: (r) => <Badge value={r.status} /> },
        { header: 'Vaqt', render: (r) => formatDate(r.created_at) },
      ]} />}
      {selected && (
        <Card title={`Report: ${selected.category}`}>
          <p>{selected.description || <span className="muted">Tavsif yo'q</span>}</p>
          <p className="muted">Kerak bo'lsa foydalanuvchi sahifasidan moderatsiya qiling.</p>
          {['open', 'in_review'].includes(selected.status) && (
            <DecisionForm busy={action.busy} noteRequired={false}
              actions={[['in_review', "Ko'rib chiqishga olish"], ['resolved', 'Hal qilindi'], ['dismissed', 'Rad etish']]}
              onSubmit={(next, note) => void action.run(
                () => api.post(`/admin/reports/${selected.id}/status`, { status: next, note }),
                async () => { setSelected(null); await reload(); },
              )} />
          )}
        </Card>
      )}
    </div>
  );
}
