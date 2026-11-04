import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, shortId } from '../../format';
import { Badge, Card, DecisionForm, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

interface Verification {
  id: string;
  user_id: string;
  status: string;
  document_type: string;
  submitted_at: string | null;
  review_note: string | null;
  document_url: string | null;
  selfie_url: string | null;
}

export function VerificationsPage() {
  const [status, setStatus] = useState('pending');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Verification>>('/admin/verifications', { status, limit: 50 }),
    [status],
  );
  const [selected, setSelected] = useState<Verification | null>(null);
  const action = useAction();
  return (
    <div className="stack">
      <PageHeader title="ID va selfie verification"
        actions={<Select value={status} onChange={setStatus} options={['pending', 'verified', 'rejected']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && (
        <Table rows={data.items} onRow={setSelected} empty="Navbat bo'sh" columns={[
          { header: 'Foydalanuvchi', render: (v) => shortId(v.user_id) },
          { header: 'Hujjat', render: (v) => v.document_type },
          { header: 'Holat', render: (v) => <Badge value={v.status} /> },
          { header: 'Yuborilgan', render: (v) => formatDate(v.submitted_at) },
          { header: 'Izoh', render: (v) => v.review_note ?? '—' },
        ]} />
      )}
      {selected && (
        <Card title={`Verification ${shortId(selected.id)}`}>
          <p className="muted">Hujjatdagi yuz selfie bilan mosligini va hujjat haqiqiyligini tekshiring. Havolalar 5 daqiqa amal qiladi.</p>
          <div className="photos">
            {selected.document_url && <img src={selected.document_url} alt="Hujjat" />}
            {selected.selfie_url && <img src={selected.selfie_url} alt="Selfie" />}
          </div>
          {selected.status === 'pending' && (
            <DecisionForm
              busy={action.busy}
              actions={[['approve', 'Tasdiqlash'], ['reject', 'Rad etish']]}
              onSubmit={(decision, note) => void action.run(
                () => api.post(`/admin/verifications/${selected.id}/decision`, { decision, note }),
                async () => { setSelected(null); await reload(); },
              )}
            />
          )}
        </Card>
      )}
    </div>
  );
}
