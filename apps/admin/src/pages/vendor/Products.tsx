import { useState } from 'react';
import { api } from '../../api';
import { formatMoney, parseMoney } from '../../format';
import { Badge, Card, ErrorBox, Field, Loading, PageHeader, Table, useAction, useAsync } from '../../ui';
import type { Product } from '../admin/Marketplace';

const CATEGORIES = ['flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', 'custom'];
const EMPTY = { category: 'flowers', name: '', description: '', price: '', stock: '0', minutes: '', active: true };

export function VendorProductsPage() {
  const { data, error, loading, reload } = useAsync(() => api.get<Product[]>('/vendors/me/products'), []);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState(EMPTY);
  const action = useAction();
  const price = parseMoney(form.price);

  const startEdit = (product: Product | null) => {
    setEditing(product);
    setForm(product ? {
      category: product.category, name: product.name, description: product.description,
      price: String(product.price_minor / 100), stock: String(product.stock),
      minutes: product.delivery_time_minutes ? String(product.delivery_time_minutes) : '', active: product.is_active,
    } : EMPTY);
  };
  const save = () => {
    const body = {
      category: form.category, name: form.name, description: form.description, price_minor: price,
      stock: Number(form.stock), is_active: form.active,
      delivery_time_minutes: form.minutes ? Number(form.minutes) : null,
    };
    void action.run(
      () => (editing ? api.put(`/vendors/me/products/${editing.id}`, body) : api.post('/vendors/me/products', body)),
      async () => { startEdit(null); await reload(); },
    );
  };
  const upload = (product: Product, file: File | undefined) => {
    if (file) void action.run(() => api.upload(`/vendors/me/products/${product.id}/images`, file), reload);
  };
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  return (
    <div className="stack">
      <PageHeader title="Mahsulotlar" actions={<button className="primary" onClick={() => startEdit(null)}>Yangi mahsulot</button>} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      <Card title={editing ? `Tahrirlash: ${editing.name}` : "Mahsulot qo'shish"}>
        <div className="form">
          <Field label="Kategoriya">
            <select value={form.category} onChange={set('category')}>
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Nomi"><input value={form.name} onChange={set('name')} /></Field>
          <Field label="Narx (UZS)"><input value={form.price} onChange={set('price')} /></Field>
          <Field label="Qoldiq"><input value={form.stock} onChange={set('stock')} inputMode="numeric" /></Field>
          <Field label="Yetkazish vaqti (daq., ixtiyoriy)"><input value={form.minutes} onChange={set('minutes')} inputMode="numeric" /></Field>
          <label className="inline"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Sotuvda</label>
        </div>
        <Field label="Tavsif"><textarea rows={2} value={form.description} onChange={set('description')} /></Field>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="primary" disabled={action.busy || !form.name || !price} onClick={save}>Saqlash</button>
          {editing && <button onClick={() => startEdit(null)}>Bekor qilish</button>}
        </div>
      </Card>
      {data && <Table rows={data} empty="Hali mahsulot yo'q" columns={[
        { header: '', width: '64px', render: (p) => p.images[0]?.url ? <img src={p.images[0].url} alt="" width={48} height={48} style={{ objectFit: 'cover', borderRadius: 6 }} /> : null },
        { header: 'Nomi', render: (p) => <><b>{p.name}</b>{p.hidden_reason && <div className="muted">Yashirilgan: {p.hidden_reason}</div>}</> },
        { header: 'Kategoriya', render: (p) => p.category },
        { header: 'Narx', render: (p) => formatMoney(p.price_minor, p.currency) },
        { header: 'Qoldiq', render: (p) => p.stock },
        { header: 'Holat', render: (p) => <Badge value={p.hidden_by_admin ? 'hidden' : p.is_active ? 'active' : 'draft'} /> },
        { header: '', render: (p) => (
          <div className="row">
            <button onClick={() => startEdit(p)}>Tahrirlash</button>
            <label className="inline" style={{ cursor: 'pointer' }}>
              <span className="link">Rasm</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => upload(p, e.target.files?.[0])} />
            </label>
            {p.images.map((image) => (
              <button key={image.id} title="Rasmni o'chirish"
                onClick={() => void action.run(() => api.del(`/vendors/me/products/${p.id}/images/${image.id}`), reload)}>✕ rasm</button>
            ))}
          </div>
        ) },
      ]} />}
    </div>
  );
}
