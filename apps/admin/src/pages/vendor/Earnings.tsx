import { Fragment } from 'react';
import { api } from '../../api';
import { formatDate, formatMoney } from '../../format';
import { Badge, Card, ErrorBox, Loading, PageHeader, Table, useAsync } from '../../ui';

interface Earnings {
  summary: { currency: string; held_minor: number; scheduled_minor: number; available_minor: number; paid_minor: number }[];
  payouts: { id: string; amount_minor: number; currency: string; status: string; available_at: string | null; paid_at: string | null; reference: string | null }[];
}
interface Ratings {
  rating_average: number | null;
  rating_count: number;
  reviews: { id: string; rating: number; text: string; created_at: string }[];
}

export function VendorEarningsPage() {
  const earnings = useAsync(() => api.get<Earnings>('/payouts/me'), []);
  const ratings = useAsync(() => api.get<Ratings>('/vendors/me/ratings'), []);
  return (
    <div className="stack">
      <PageHeader title="Daromad va reyting" />
      <ErrorBox error={earnings.error ?? ratings.error} />
      <Loading show={earnings.loading && !earnings.data} />
      {earnings.data && (
        <>
          <div className="kpis">
            {earnings.data.summary.map((s) => (
              <Fragment key={s.currency}>
                <div className="kpi"><div className="label">Ushlab turilgan</div><div className="value">{formatMoney(s.held_minor + s.scheduled_minor, s.currency)}</div></div>
                <div className="kpi"><div className="label">To'lashga tayyor</div><div className="value">{formatMoney(s.available_minor, s.currency)}</div></div>
                <div className="kpi"><div className="label">To'langan</div><div className="value">{formatMoney(s.paid_minor, s.currency)}</div></div>
              </Fragment>
            ))}
            <div className="kpi"><div className="label">Reyting</div><div className="value">{ratings.data?.rating_average ?? '—'} ({ratings.data?.rating_count ?? 0})</div></div>
          </div>
          <Card title="Payoutlar">
            <Table rows={earnings.data.payouts} empty="Hali payout yo'q" columns={[
              { header: 'Summa', render: (p) => formatMoney(p.amount_minor, p.currency) },
              { header: 'Holat', render: (p) => <Badge value={p.status} /> },
              { header: 'Mavjud', render: (p) => formatDate(p.available_at) },
              { header: "To'langan", render: (p) => formatDate(p.paid_at) },
              { header: 'Izoh', render: (p) => p.reference ?? '—' },
            ]} />
          </Card>
          <Card title="Mijoz sharhlari">
            <Table rows={ratings.data?.reviews ?? []} empty="Hali sharh yo'q" columns={[
              { header: 'Baho', render: (r) => '★'.repeat(r.rating) },
              { header: 'Matn', render: (r) => r.text || '—' },
              { header: 'Vaqt', render: (r) => formatDate(r.created_at) },
            ]} />
          </Card>
        </>
      )}
    </div>
  );
}
