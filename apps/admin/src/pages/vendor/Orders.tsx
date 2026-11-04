import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, formatMoney, shortId } from '../../format';
import { Badge, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';
import type { GiftOrder } from '../admin/Marketplace';

// TZ §31 status flow.
const NEXT: Record<string, [string, string]> = {
  new: ['accepted', 'Qabul qilish'],
  accepted: ['preparing', 'Tayyorlash'],
  preparing: ['courier_assigned', 'Kuryer tayinlandi'],
  courier_assigned: ['delivering', "Yo'lda"],
  delivering: ['delivered', 'Yetkazildi'],
};

export function VendorOrdersPage() {
  const [status, setStatus] = useState('');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<GiftOrder>>('/vendors/me/orders', { status, limit: 50 }), [status],
  );
  const action = useAction();
  const move = (order: GiftOrder, next: string) =>
    void action.run(() => api.post(`/vendors/me/orders/${order.id}/status`, { status: next }), reload);
  return (
    <div className="stack">
      <PageHeader title="Buyurtmalar" actions={<Select value={status} onChange={setStatus}
        options={['', 'new', 'accepted', 'preparing', 'courier_assigned', 'delivering', 'delivered', 'cancelled']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} empty="Buyurtmalar yo'q" columns={[
        { header: 'ID', render: (o) => shortId(o.id) },
        { header: 'Mahsulotlar', render: (o) => o.items.map((i) => <div key={i.product_name}>{i.product_name} ×{i.quantity}{i.note && <span className="muted"> — {i.note}</span>}</div>) },
        { header: 'Qabul qiluvchi', render: (o) => <>{o.recipient_name}<div className="muted">{o.recipient_phone}</div></> },
        { header: 'Manzil va vaqt', render: (o) => <>{o.delivery_address}<div className="muted">{formatDate(o.delivery_at)}</div>{o.note && <div className="muted">{o.note}</div>}</> },
        { header: 'Summa', render: (o) => formatMoney(o.subtotal_minor + o.delivery_fee_minor, o.currency) },
        { header: 'Holat', render: (o) => <Badge value={o.status} /> },
        { header: '', render: (o) => (
          <div className="row">
            {NEXT[o.status] && <button className="primary" disabled={action.busy} onClick={() => move(o, NEXT[o.status][0])}>{NEXT[o.status][1]}</button>}
            {['new', 'accepted'].includes(o.status) && (
              <button className="danger" disabled={action.busy}
                onClick={() => window.confirm('Buyurtmani bekor qilasizmi? Mijozga pul qaytariladi.') && move(o, 'cancelled')}>Bekor qilish</button>
            )}
          </div>
        ) },
      ]} />}
    </div>
  );
}
