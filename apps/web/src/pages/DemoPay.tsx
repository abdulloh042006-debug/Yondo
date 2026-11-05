import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { t, type Key } from '../i18n';
import { formatMoney } from '../lib/format';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading, useToast } from '../ui/feedback';

interface DemoPayment {
  booking_id: string;
  amount_minor: number;
  currency: string;
  status: string;
}

/**
 * DEMO checkout page: the stand-in for CLICK/Payme while no real provider is connected. No money moves; the two buttons
 * only tell the demo provider (a server started with the demo payment provider) how the "payment" ended. Any other server
 * answers 404 here, and only the paying customer's session may open it.
 */
export function DemoPay() {
  const { reference = '' } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const res = useResource((signal) => api.get<DemoPayment>(`/demo-pay/${reference}`, { signal }), [reference]);
  const [busy, setBusy] = useState(false);

  if (res.loading && !res.data) return <Loading />;
  if (res.error) {
    return res.error.status === 404 ? (
      <Empty title={t('demoPay.unavailable')} action={<Link className="btn" to="/bookings">{t('demoPay.back')}</Link>} />
    ) : (
      <ErrorState error={res.error} onRetry={res.reload} />
    );
  }
  const p = res.data;
  if (!p) return null;
  const decide = async (outcome: 'succeed' | 'fail') => {
    setBusy(true);
    try {
      const done = await api.post<DemoPayment>(`/demo-pay/${reference}/${outcome}`);
      toast.push('ok', t('bd.pay.status', { status: t(`payment.status.${done.status}` as Key) }));
      navigate(`/bookings/${done.booking_id}`);
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
      setBusy(false);
    }
  };
  return (
    <div className="stack" style={{ maxWidth: 480, margin: '0 auto' }}>
      <div className="glass pad stack">
        <p><span className="chip">{t('demoPay.badge')}</span></p>
        <h1>{t('demoPay.title')}</h1>
        <p className="banner" role="note">{t('demoPay.note')}</p>
        <p>{t('demoPay.amount', { amount: formatMoney(p.amount_minor, p.currency) })}</p>
        <p>{t('bd.pay.status', { status: t(`payment.status.${p.status}` as Key) })}</p>
        <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
          <button className="btn" disabled={busy || p.status === 'succeeded'} onClick={() => void decide('succeed')}>
            {busy && <span className="spinner" aria-hidden="true" />}{t('demoPay.confirm')}
          </button>
          <button className="btn ghost" disabled={busy || p.status === 'succeeded'} onClick={() => void decide('fail')}>
            {t('demoPay.reject')}
          </button>
          <Link className="btn ghost" to={`/bookings/${p.booking_id}`}>{t('demoPay.back')}</Link>
        </div>
      </div>
    </div>
  );
}
