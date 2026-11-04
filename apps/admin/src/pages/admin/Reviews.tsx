import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate } from '../../format';
import { Badge, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

interface Review {
  id: string; direction: string; rating: number; tags: string[]; text: string; status: string;
  hidden_reason: string | null; created_at: string;
}

export function ReviewsPage() {
  const [status, setStatus] = useState('');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Review>>('/admin/reviews', { status, limit: 50 }), [status],
  );
  const action = useAction();
  const moderate = (review: Review, hide: boolean) => {
    const reason = hide ? window.prompt('Yashirish sababi') : '';
    if (hide && !reason) return;
    void action.run(() => api.post(`/admin/reviews/${review.id}/moderation`, { action: hide ? 'hide' : 'unhide', reason: reason ?? '' }), reload);
  };
  return (
    <div className="stack">
      <PageHeader title="Sharhlar" actions={<Select value={status} onChange={setStatus} options={['', 'published', 'hidden']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: "Yo'nalish", render: (r) => (r.direction === 'customer_to_companion' ? 'Mijoz → Companion' : 'Companion → Mijoz') },
        { header: 'Baho', render: (r) => '★'.repeat(r.rating) },
        { header: 'Matn', render: (r) => r.text || r.tags.join(', ') || '—' },
        { header: 'Holat', render: (r) => <Badge value={r.status} /> },
        { header: 'Vaqt', render: (r) => formatDate(r.created_at) },
        { header: '', render: (r) => r.status === 'published'
          ? <button className="danger" onClick={() => moderate(r, true)}>Yashirish</button>
          : <button onClick={() => moderate(r, false)}>Qaytarish</button> },
      ]} />}
    </div>
  );
}
