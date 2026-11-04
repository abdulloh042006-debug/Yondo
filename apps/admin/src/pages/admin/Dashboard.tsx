import { useState } from 'react';
import { api } from '../../api';
import { formatMoney, percent } from '../../format';
import { ErrorBox, Loading, PageHeader, Select, useAsync } from '../../ui';

interface Metrics {
  [key: string]: number | null;
}

const COUNTS: [string, string][] = [
  ['registrations', "Ro'yxatdan o'tganlar"],
  ['registrations_total', 'Jami foydalanuvchilar'],
  ['verified_users', 'Tasdiqlangan foydalanuvchilar'],
  ['active_companions', 'Faol companionlar'],
  ['booking_requests', "Bron so'rovlari"],
  ['accepted_bookings', 'Qabul qilingan'],
  ['completed_bookings', 'Yakunlangan'],
  ['cancelled_bookings', 'Bekor qilingan'],
  ['no_show_bookings', 'No-show'],
  ['disputed_bookings', 'Nizoli'],
  ['reports', 'Reportlar'],
];
const RATES: [string, string][] = [
  ['booking_conversion_rate', "So'rov → to'lov"],
  ['completion_rate', 'Yakunlanish'],
  ['cancellation_rate', 'Bekor qilish'],
  ['no_show_rate', 'No-show'],
  ['repeat_booking_rate', 'Qayta bron'],
  ['report_rate', 'Report darajasi'],
  ['gift_attach_rate', "Sovg'a qo'shilishi"],
];

export function DashboardPage() {
  const [days, setDays] = useState('30');
  const { data, error, loading } = useAsync(() => api.get<Metrics>('/admin/analytics', { days }), [days]);
  return (
    <div className="stack">
      <PageHeader
        title="Dashboard"
        subtitle="MVP muvaffaqiyat mezonlari (TZ §47)"
        actions={<Select label="Davr" value={days} onChange={setDays} options={[['7', '7 kun'], ['30', '30 kun'], ['90', '90 kun'], ['365', '1 yil']]} />}
      />
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <>
          <div className="kpis">
            {COUNTS.map(([key, label]) => (
              <div className="kpi" key={key}>
                <div className="label">{label}</div>
                <div className="value">{data[key] ?? '—'}</div>
              </div>
            ))}
            <div className="kpi">
              <div className="label">O'rtacha reyting</div>
              <div className="value">{data.average_rating ?? '—'}</div>
            </div>
          </div>
          <h2>Konversiyalar</h2>
          <div className="kpis">
            {RATES.map(([key, label]) => (
              <div className="kpi" key={key}>
                <div className="label">{label}</div>
                <div className="value">{percent(data[key])}</div>
              </div>
            ))}
          </div>
          <h2>Moliya</h2>
          <div className="kpis">
            <div className="kpi"><div className="label">Yalpi tushum</div><div className="value">{formatMoney(data.gross_volume_minor)}</div></div>
            <div className="kpi"><div className="label">Qaytarilgan</div><div className="value">{formatMoney(data.refunded_minor)}</div></div>
            <div className="kpi"><div className="label">Platforma komissiyasi</div><div className="value">{formatMoney(data.platform_fee_minor)}</div></div>
          </div>
        </>
      )}
    </div>
  );
}
