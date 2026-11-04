import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, shortId } from '../../format';
import { ErrorBox, Loading, PageHeader, Pager, Select, Table, useAsync } from '../../ui';

interface AuditRecord {
  id: string; admin_id: string | null; action: string; target_type: string; target_id: string;
  reason: string; data: Record<string, string>; created_at: string;
}

const LIMIT = 30;

export function AuditPage() {
  const [targetType, setTargetType] = useState('');
  const [offset, setOffset] = useState(0);
  const { data, error, loading } = useAsync(
    () => api.get<Page<AuditRecord>>('/admin/audit', { target_type: targetType, offset, limit: LIMIT }),
    [targetType, offset],
  );
  return (
    <div className="stack">
      <PageHeader title="Audit log" subtitle="Barcha administrator amallari"
        actions={<Select value={targetType} onChange={(v) => { setTargetType(v); setOffset(0); }}
          options={['', 'user', 'booking', 'payout', 'dispute', 'report', 'review', 'sos', 'verification', 'vendor', 'product', 'gift_order']} />} />
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <>
          <Table rows={data.items} columns={[
            { header: 'Vaqt', render: (a) => formatDate(a.created_at) },
            { header: 'Admin', render: (a) => (a.admin_id ? shortId(a.admin_id) : '—') },
            { header: 'Amal', render: (a) => a.action },
            { header: 'Obyekt', render: (a) => `${a.target_type} ${shortId(a.target_id)}` },
            { header: 'Sabab', render: (a) => a.reason || '—' },
            { header: "Ma'lumot", render: (a) => (Object.keys(a.data).length ? JSON.stringify(a.data) : '—') },
          ]} />
          <Pager offset={offset} nextOffset={data.next_offset} limit={LIMIT} onChange={setOffset} />
        </>
      )}
    </div>
  );
}
