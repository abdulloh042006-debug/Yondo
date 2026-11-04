import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, formatMoney, shortId } from '../../format';
import { Badge, ErrorBox, Loading, PageHeader, Pager, Select, Table, useAction, useAsync } from '../../ui';

interface Payment {
  id: string; booking_id: string | null; provider: string; status: string; currency: string;
  amount_minor: number; refunded_minor: number; created_at: string; paid_at: string | null;
}
interface Refund {
  id: string; payment_id: string; amount_minor: number; status: string; reason: string;
  attempts: number; created_at: string;
}
interface Payout {
  id: string; beneficiary_id: string; booking_id: string | null; gift_order_id: string | null;
  amount_minor: number; currency: string; status: string; available_at: string | null;
  paid_at: string | null; reference: string | null; due: boolean;
}

const LIMIT = 25;

export function FinancePage() {
  const [tab, setTab] = useState<'payments' | 'refunds' | 'payouts'>('payouts');
  return (
    <div className="stack">
      <PageHeader title="To'lovlar va payoutlar" subtitle="Payout provayderi ulanmaguncha o'tkazmalar qo'lda bajariladi va bu yerda belgilanadi." />
      <div className="tabs">
        {(['payouts', 'payments', 'refunds'] as const).map((key) => (
          <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>
            {{ payouts: 'Payoutlar', payments: "To'lovlar", refunds: 'Refundlar' }[key]}
          </button>
        ))}
      </div>
      {tab === 'payments' && <Payments />}
      {tab === 'refunds' && <Refunds />}
      {tab === 'payouts' && <Payouts />}
    </div>
  );
}

function Payments() {
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const { data, error, loading } = useAsync(
    () => api.get<Page<Payment>>('/admin/payments', { status, offset, limit: LIMIT }), [status, offset],
  );
  return (
    <>
      <Select label="Holat" value={status} onChange={(v) => { setStatus(v); setOffset(0); }}
        options={['', 'pending', 'succeeded', 'failed', 'cancelled', 'refunded', 'partially_refunded']} />
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <>
          <Table rows={data.items} columns={[
            { header: 'ID', render: (p) => shortId(p.id) },
            { header: 'Turi', render: (p) => (p.booking_id ? 'Bron' : "Sovg'a") },
            { header: 'Summa', render: (p) => formatMoney(p.amount_minor, p.currency) },
            { header: 'Qaytarilgan', render: (p) => formatMoney(p.refunded_minor, p.currency) },
            { header: 'Holat', render: (p) => <Badge value={p.status} /> },
            { header: 'Provayder', render: (p) => p.provider },
            { header: 'Yaratilgan', render: (p) => formatDate(p.created_at) },
          ]} />
          <Pager offset={offset} nextOffset={data.next_offset} limit={LIMIT} onChange={setOffset} />
        </>
      )}
    </>
  );
}

function Refunds() {
  const { data, error, loading, reload } = useAsync(() => api.get<Page<Refund>>('/admin/refunds', { limit: 50 }), []);
  const action = useAction();
  return (
    <>
      <div className="row">
        <button disabled={action.busy} onClick={() => void action.run(() => api.post('/admin/refunds/process'), reload)}>
          Navbatdagi refundlarni yuborish
        </button>
      </div>
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: "To'lov", render: (r) => shortId(r.payment_id) },
        { header: 'Summa', render: (r) => formatMoney(r.amount_minor) },
        { header: 'Sabab', render: (r) => r.reason },
        { header: 'Holat', render: (r) => <Badge value={r.status} /> },
        { header: 'Urinishlar', render: (r) => r.attempts },
        { header: 'Yaratilgan', render: (r) => formatDate(r.created_at) },
      ]} />}
    </>
  );
}

function Payouts() {
  const [dueOnly, setDueOnly] = useState('true');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Payout>>('/admin/payouts', { due_only: dueOnly === 'true' ? true : undefined, limit: 50 }),
    [dueOnly],
  );
  const action = useAction();
  const markPaid = (payout: Payout) => {
    const reference = window.prompt("Bank o'tkazmasi raqami / izoh");
    if (reference) void action.run(() => api.post(`/admin/payouts/${payout.id}/mark-paid`, { reference }), reload);
  };
  return (
    <>
      <Select value={dueOnly} onChange={setDueOnly} options={[['true', "To'lash vaqti kelganlar"], ['false', 'Hammasi']]} />
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} columns={[
        { header: 'Oluvchi', render: (p) => shortId(p.beneficiary_id) },
        { header: 'Manba', render: (p) => (p.booking_id ? `Bron ${shortId(p.booking_id)}` : `Sovg'a ${shortId(p.gift_order_id ?? '')}`) },
        { header: 'Summa', render: (p) => formatMoney(p.amount_minor, p.currency) },
        { header: 'Holat', render: (p) => <Badge value={p.status} /> },
        { header: 'Mavjud vaqti', render: (p) => formatDate(p.available_at) },
        { header: 'Izoh', render: (p) => p.reference ?? '—' },
        { header: '', render: (p) => p.due && <button className="primary" disabled={action.busy} onClick={() => markPaid(p)}>To'landi</button> },
      ]} />}
    </>
  );
}
