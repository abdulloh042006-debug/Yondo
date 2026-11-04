import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, formatMoney, shortId } from '../../format';
import { Badge, ErrorBox, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

export interface Vendor {
  id: string; user_id: string; name: string; description: string; city: string; status: string;
  currency: string; delivery_fee_minor: number; delivery_time_minutes: number;
  review_note: string | null; created_at: string;
}
export interface Product {
  id: string; category: string; name: string; description: string; price_minor: number;
  currency: string; stock: number; is_active: boolean; hidden_by_admin: boolean;
  hidden_reason: string | null; delivery_time_minutes: number | null;
  images: { id: string; url: string | null }[];
}
export interface GiftOrder {
  id: string; vendor_name: string | null; booking_id: string | null; status: string;
  recipient_name: string; recipient_phone: string; delivery_address: string; delivery_at: string;
  note: string; currency: string; subtotal_minor: number; delivery_fee_minor: number;
  total_minor: number; created_at: string;
  items: { product_name: string; quantity: number; unit_price_minor: number; note: string }[];
}

export function VendorsPage() {
  const [status, setStatus] = useState('pending');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Vendor>>('/admin/vendors', { status, limit: 50 }), [status],
  );
  const action = useAction();
  const decide = (vendor: Vendor, decision: string) => {
    const note = window.prompt('Izoh');
    if (note) void action.run(() => api.post(`/admin/vendors/${vendor.id}/decision`, { decision, note }), reload);
  };
  return (
    <div className="stack">
      <PageHeader title="Vendorlar" actions={<Select value={status} onChange={setStatus} options={['', 'pending', 'approved', 'rejected', 'suspended']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: "Do'kon", render: (v) => <><b>{v.name}</b><div className="muted">{v.description.slice(0, 80)}</div></> },
        { header: 'Shahar', render: (v) => v.city },
        { header: 'Yetkazish', render: (v) => `${formatMoney(v.delivery_fee_minor, v.currency)}, ~${v.delivery_time_minutes} min` },
        { header: 'Holat', render: (v) => <Badge value={v.status} /> },
        { header: '', render: (v) => (
          <div className="row">
            {v.status !== 'approved' && <button className="primary" onClick={() => decide(v, 'approve')}>Tasdiqlash</button>}
            {v.status === 'pending' && <button className="danger" onClick={() => decide(v, 'reject')}>Rad etish</button>}
            {v.status === 'approved' && <button className="danger" onClick={() => decide(v, 'suspend')}>To'xtatish</button>}
          </div>
        ) },
      ]} />}
    </div>
  );
}

export function ProductsPage() {
  const [hidden, setHidden] = useState('');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Product>>('/admin/products', { hidden: hidden || undefined, limit: 50 }), [hidden],
  );
  const action = useAction();
  const moderate = (product: Product, hide: boolean) => {
    const reason = hide ? window.prompt('Yashirish sababi') : '';
    if (hide && !reason) return;
    void action.run(() => api.post(`/admin/products/${product.id}/moderation`, { action: hide ? 'hide' : 'unhide', reason: reason ?? '' }), reload);
  };
  return (
    <div className="stack">
      <PageHeader title="Mahsulotlar" actions={<Select value={hidden} onChange={setHidden} options={[['', 'Hammasi'], ['false', "Ko'rinadigan"], ['true', 'Yashirilgan']]} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: '', width: '64px', render: (p) => p.images[0]?.url ? <img src={p.images[0].url} alt="" width={48} height={48} style={{ objectFit: 'cover', borderRadius: 6 }} /> : null },
        { header: 'Nomi', render: (p) => p.name },
        { header: 'Kategoriya', render: (p) => p.category },
        { header: 'Narx', render: (p) => formatMoney(p.price_minor, p.currency) },
        { header: 'Qoldiq', render: (p) => p.stock },
        { header: 'Holat', render: (p) => <Badge value={p.hidden_by_admin ? 'hidden' : p.is_active ? 'active' : 'draft'} /> },
        { header: '', render: (p) => p.hidden_by_admin
          ? <button onClick={() => moderate(p, false)}>Qaytarish</button>
          : <button className="danger" onClick={() => moderate(p, true)}>Yashirish</button> },
      ]} />}
    </div>
  );
}

export function GiftOrdersPage() {
  const [status, setStatus] = useState('');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<GiftOrder>>('/admin/gift-orders', { status, limit: 50 }), [status],
  );
  const action = useAction();
  const cancel = (order: GiftOrder) => {
    const reason = window.prompt('Bekor qilish sababi (mijozga to‘liq refund qilinadi)');
    if (reason) void action.run(() => api.post(`/admin/gift-orders/${order.id}/cancel`, { reason, refund: true }), reload);
  };
  return (
    <div className="stack">
      <PageHeader title="Sovg'a buyurtmalari" actions={<Select value={status} onChange={setStatus}
        options={['', 'pending_payment', 'new', 'accepted', 'preparing', 'courier_assigned', 'delivering', 'delivered', 'cancelled']} />} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: 'ID', render: (o) => shortId(o.id) },
        { header: 'Vendor', render: (o) => o.vendor_name },
        { header: 'Mahsulotlar', render: (o) => o.items.map((i) => `${i.product_name} ×${i.quantity}`).join(', ') },
        { header: 'Yetkazish', render: (o) => <>{formatDate(o.delivery_at)}<div className="muted">{o.delivery_address}</div></> },
        { header: 'Jami', render: (o) => formatMoney(o.total_minor, o.currency) },
        { header: 'Bron', render: (o) => (o.booking_id ? shortId(o.booking_id) : '—') },
        { header: 'Holat', render: (o) => <Badge value={o.status} /> },
        { header: '', render: (o) => !['delivered', 'cancelled', 'pending_payment'].includes(o.status) && <button className="danger" onClick={() => cancel(o)}>Bekor qilish</button> },
      ]} />}
    </div>
  );
}
