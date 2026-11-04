import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, type Page } from '../../api';
import { formatDate, formatMoney, shortId } from '../../format';
import { Badge, Card, Details, ErrorBox, Field, Loading, PageHeader, Pager, Select, Table, useAction, useAsync } from '../../ui';

export interface Booking {
  id: string;
  status: string;
  customer: { id: string; display_name: string | null };
  companion: { id: string; display_name: string | null };
  service_code: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  duration_minutes: number;
  meeting_place: { name: string; address: string };
  total_minor: number;
  service_amount_minor: number;
  platform_fee_minor: number;
  companion_payout_minor: number | null;
  refund_minor: number;
  currency: string;
  cancellation_reason: string | null;
  cancellation_note: string | null;
  no_show_party: string | null;
  created_at: string;
}

interface Detail {
  booking: Booking;
  events: { id: string; event: string; from_status: string | null; to_status: string; created_at: string; data: Record<string, unknown> }[];
  payments: { id: string; status: string; amount_minor: number; refunded_minor: number; currency: string; provider: string; created_at: string }[];
}

const STATUSES = ['', 'pending', 'accepted', 'confirmed', 'active', 'completed', 'cancelled', 'no_show', 'disputed'];
const LIMIT = 20;

export function BookingsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const { data, error, loading } = useAsync(
    () => api.get<Page<Booking>>('/admin/bookings', { status, offset, limit: LIMIT }),
    [status, offset],
  );
  return (
    <div className="stack">
      <PageHeader title="Bronlar" actions={<Select label="Holat" value={status} onChange={(v) => { setStatus(v); setOffset(0); }} options={STATUSES} />} />
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <>
          <Table rows={data.items} onRow={(b) => navigate(`/admin/bookings/${b.id}`)} columns={[
            { header: 'ID', render: (b) => shortId(b.id) },
            { header: 'Mijoz', render: (b) => b.customer.display_name ?? '—' },
            { header: 'Companion', render: (b) => b.companion.display_name ?? '—' },
            { header: 'Xizmat', render: (b) => b.service_code },
            { header: 'Vaqt', render: (b) => formatDate(b.starts_at, b.timezone) },
            { header: 'Summa', render: (b) => formatMoney(b.total_minor, b.currency) },
            { header: 'Holat', render: (b) => <Badge value={b.status} /> },
          ]} />
          <Pager offset={offset} nextOffset={data.next_offset} limit={LIMIT} onChange={setOffset} />
        </>
      )}
    </div>
  );
}

export function BookingDetailPage() {
  const { bookingId } = useParams();
  const { data, error, reload } = useAsync(() => api.get<Detail>(`/admin/bookings/${bookingId}`), [bookingId]);
  const action = useAction();
  const [reason, setReason] = useState('');
  const [refund, setRefund] = useState('100');
  if (!data) return <><ErrorBox error={error} /><Loading show={!error} /></>;
  const b = data.booking;
  const cancellable = ['pending', 'accepted', 'confirmed', 'active'].includes(b.status);
  return (
    <div className="stack">
      <PageHeader title={`Bron ${shortId(b.id)}`} subtitle={b.id} actions={<Badge value={b.status} />} />
      <Card title="Tafsilotlar">
        <Details items={[
          ['Mijoz', b.customer.display_name],
          ['Companion', b.companion.display_name],
          ['Xizmat', `${b.service_code}, ${b.duration_minutes} min`],
          ['Boshlanish', formatDate(b.starts_at, b.timezone)],
          ['Joy', `${b.meeting_place.name} ${b.meeting_place.address}`],
          ['Xizmat narxi', formatMoney(b.service_amount_minor, b.currency)],
          ['Platforma to‘lovi', formatMoney(b.platform_fee_minor, b.currency)],
          ['Jami', formatMoney(b.total_minor, b.currency)],
          ['Companion payout', formatMoney(b.companion_payout_minor, b.currency)],
          ['Qaytarilgan', formatMoney(b.refund_minor, b.currency)],
          ['Bekor qilish sababi', b.cancellation_reason ? `${b.cancellation_reason} ${b.cancellation_note ?? ''}` : '—'],
          ['No-show', b.no_show_party],
        ]} />
      </Card>
      <div className="grid2">
        <Card title="To'lovlar">
          <Table rows={data.payments} columns={[
            { header: 'Holat', render: (p) => <Badge value={p.status} /> },
            { header: 'Summa', render: (p) => formatMoney(p.amount_minor, p.currency) },
            { header: 'Qaytarilgan', render: (p) => formatMoney(p.refunded_minor, p.currency) },
            { header: 'Provayder', render: (p) => p.provider },
          ]} />
        </Card>
        {cancellable && (
          <Card title="Admin bekor qilishi">
            <div className="form">
              <Field label="Sabab"><input value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
              <Field label="Mijozga qaytariladigan %"><input value={refund} onChange={(e) => setRefund(e.target.value)} inputMode="numeric" /></Field>
              <button className="danger" disabled={action.busy || !reason.trim() || !(Number(refund) >= 0 && Number(refund) <= 100)}
                onClick={() => void action.run(() => api.post(`/admin/bookings/${b.id}/cancel`, {
                  reason, refund_bps: Math.round(Number(refund) * 100),
                }), reload)}>Bekor qilish</button>
            </div>
            <ErrorBox error={action.error} />
          </Card>
        )}
      </div>
      <Card title="Hodisalar tarixi">
        <Table rows={data.events} columns={[
          { header: 'Hodisa', render: (e) => e.event },
          { header: 'Holat', render: (e) => `${e.from_status ?? '—'} → ${e.to_status}` },
          { header: "Ma'lumot", render: (e) => Object.keys(e.data).length ? JSON.stringify(e.data) : '—' },
          { header: 'Vaqt', render: (e) => formatDate(e.created_at) },
        ]} />
      </Card>
    </div>
  );
}
