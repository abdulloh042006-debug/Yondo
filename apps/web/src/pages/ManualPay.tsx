import { Link, useParams } from 'react-router-dom';
import type { Schemas } from '../api/client';
import { api } from '../api/client';
import { t } from '../i18n';
import { formatMoney } from '../lib/format';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading, useToast } from '../ui/feedback';

type ManualPayment = Schemas['ManualPaymentRead'];

/**
 * Manual card transfer (beta): the customer sends exactly this amount from their own bank app to one of the
 * configured cards, with the code in the transfer comment; an admin confirms the money by hand. The app moves
 * no money and promises no confirmation time.
 */
export function ManualPay() {
  const { reference = '' } = useParams();
  const toast = useToast();
  const res = useResource((signal) => api.get<ManualPayment>(`/payments/manual/${reference}`, { signal }), [reference]);
  const copy = (text: string) => {
    void navigator.clipboard
      ?.writeText(text.replace(/\s/g, ''))
      .then(() => toast.push('ok', t('manualPay.copied')))
      .catch(() => {});
  };

  if (res.loading && !res.data) return <Loading />;
  if (res.error) {
    return res.error.status === 404 ? (
      <Empty title={t('manualPay.notOpen')} action={<Link className="btn" to="/bookings">{t('nav.bookings')}</Link>} />
    ) : (
      <ErrorState error={res.error} onRetry={res.reload} />
    );
  }
  const p = res.data;
  if (!p) return null;
  return (
    <div className="stack" style={{ maxWidth: 520, margin: '0 auto' }}>
      <div className="glass pad stack">
        <h1>{t('manualPay.title')}</h1>
        <p className="big">{t('manualPay.amount', { amount: formatMoney(p.amount_minor, p.currency) })}</p>
        {p.state === 'confirmed' ? (
          <p className="banner" role="status">{t('manualPay.confirmed')}</p>
        ) : p.state === 'refund_required' ? (
          <p className="banner" role="status">{t('manualPay.refund')}</p>
        ) : p.state !== 'open' ? (
          <p className="banner" role="status">{t('manualPay.notOpen')}</p>
        ) : (
          <>
            <p className="banner" role="note">{t('manualPay.note')}</p>
            <div className="stack" style={{ gap: 6 }}>
              <span className="muted">{t('manualPay.reference')}</span>
              <div className="row">
                <b className="mono big">{p.reference}</b>
                <button type="button" className="btn sm ghost" onClick={() => copy(p.reference)} aria-label={`${t('manualPay.copy')}: ${t('manualPay.reference')}`}>{t('manualPay.copy')}</button>
              </div>
            </div>
            <ul className="stack" style={{ listStyle: 'none', padding: 0, margin: 0, gap: 10 }}>
              {p.cards.map((c) => (
                <li key={c.number} className="glass pad stack" style={{ gap: 4 }}>
                  <span className="muted">{c.label}</span>
                  <div className="row">
                    <b className="mono">{c.number}</b>
                    <button type="button" className="btn sm ghost" onClick={() => copy(c.number)} aria-label={`${t('manualPay.copy')}: ${c.label}`}>{t('manualPay.copy')}</button>
                  </div>
                  <span>{t('manualPay.holder', { name: c.holder })}</span>
                </li>
              ))}
            </ul>
            <p className="hint">{t('manualPay.waiting')}</p>
          </>
        )}
        <div className="row">
          {p.state === 'open' && (
            <button type="button" className="btn ghost" onClick={res.reload}>{t('manualPay.refresh')}</button>
          )}
          <Link className="btn ghost" to={`/bookings/${p.booking_id}`}>{t('manualPay.back')}</Link>
        </div>
      </div>
    </div>
  );
}
