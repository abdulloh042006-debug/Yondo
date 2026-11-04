import { useEffect, useState } from 'react';
import { api, ApiError } from '../../api';
import { formatMoney, parseMoney } from '../../format';
import { Badge, Card, ErrorBox, Field, Loading, PageHeader, useAction, useAsync } from '../../ui';
import type { Vendor } from '../admin/Marketplace';

export function VendorShopPage() {
  const { data, error, loading, reload } = useAsync(async () => {
    try {
      return await api.get<Vendor>('/vendors/me');
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 404) return null;
      throw exc;
    }
  }, []);
  const action = useAction();
  const [form, setForm] = useState({ name: '', description: '', city: 'Tashkent', currency: 'UZS', fee: '0', minutes: '120' });
  useEffect(() => {
    if (data) {
      setForm({
        name: data.name, description: data.description, city: data.city, currency: data.currency,
        fee: String(data.delivery_fee_minor / 100), minutes: String(data.delivery_time_minutes),
      });
    }
  }, [data]);
  const fee = parseMoney(form.fee, form.currency);
  const submit = () => {
    const body = {
      name: form.name, description: form.description, city: form.city, currency: form.currency,
      delivery_fee_minor: fee, delivery_time_minutes: Number(form.minutes),
    };
    void action.run(() => (data ? api.put('/vendors/me', body) : api.post('/vendors/me', body)), reload);
  };
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });
  return (
    <div className="stack">
      <PageHeader title="Do'kon" subtitle="Vendor profili (TZ §30)" actions={data && <Badge value={data.status} />} />
      <ErrorBox error={error} />
      <Loading show={loading} />
      {!loading && (
        <>
          {!data && <div className="notice">Vendor sifatida ishlash uchun ariza yuboring. Administrator tasdiqlagach mahsulot qo'sha olasiz.</div>}
          {data?.status === 'pending' && <div className="notice">Arizangiz ko'rib chiqilmoqda.</div>}
          {data?.review_note && <div className="notice">Administrator izohi: {data.review_note}</div>}
          <Card title={data ? 'Profilni tahrirlash' : 'Ariza'}>
            <div className="form">
              <Field label="Do'kon nomi"><input value={form.name} onChange={set('name')} /></Field>
              <Field label="Shahar"><input value={form.city} onChange={set('city')} /></Field>
              <Field label="Valyuta"><input value={form.currency} onChange={set('currency')} maxLength={3} /></Field>
              <Field label={`Yetkazish narxi (${form.currency})`}><input value={form.fee} onChange={set('fee')} /></Field>
              <Field label="Yetkazish vaqti (daqiqa)"><input value={form.minutes} onChange={set('minutes')} inputMode="numeric" /></Field>
            </div>
            <Field label="Tavsif"><textarea rows={3} value={form.description} onChange={set('description')} /></Field>
            <ErrorBox error={action.error} />
            <button className="primary" style={{ marginTop: 10 }} disabled={action.busy || !form.name || fee === null} onClick={submit}>
              {data ? 'Saqlash' : 'Ariza yuborish'}
            </button>
            {data && <p className="muted">Hozirgi yetkazish narxi: {formatMoney(data.delivery_fee_minor, data.currency)}</p>}
          </Card>
        </>
      )}
    </div>
  );
}
