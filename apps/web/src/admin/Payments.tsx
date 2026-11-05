import { useState } from 'react';
import { api } from '../api/client';
import type { Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant, formatMoney } from '../lib/format';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, useToast } from '../ui/feedback';
import { Id } from './shared';

type Row = Schemas['AdminManualPaymentRead'];

/** Manual card transfers (beta): confirm only money actually seen in the bank, with this amount and code. */
export function AdminPayments() {
  const [status, setStatus] = useState<'pending' | 'succeeded'>('pending');
  const res = useResource((signal) => api.get<Row[]>('/admin/payments/manual', { query: { status }, signal }), [status]);
  const [confirming, setConfirming] = useState<Row>();
  const toast = useToast();
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">{t('admin.payments.banner')}</p>
      <div className="row" role="group" aria-label={t('admin.nav.payments')}>
        <button type="button" className={status === 'pending' ? 'btn sm' : 'btn sm ghost'} aria-pressed={status === 'pending'} onClick={() => setStatus('pending')}>{t('admin.payments.tabPending')}</button>
        <button type="button" className={status === 'succeeded' ? 'btn sm' : 'btn sm ghost'} aria-pressed={status === 'succeeded'} onClick={() => setStatus('succeeded')}>{t('admin.payments.tabDone')}</button>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('admin.payments.none')} /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>{t('admin.col.reference')}</th><th>{t('admin.col.amount')}</th><th>{t('admin.col.created')}</th><th>{t('common.booking')}</th><th /></tr></thead>
            <tbody>
              {res.data.map((p) => (
                <tr key={p.payment_id}>
                  <td><b className="mono">{p.reference}</b></td>
                  <td>{formatMoney(p.amount_minor, p.currency)}</td>
                  <td>{formatInstant(p.created_at)}</td>
                  <td><Id value={p.booking_id} /></td>
                  <td>
                    {p.status === 'pending' ? (
                      <button type="button" className="btn sm" onClick={() => setConfirming(p)}>{t('admin.payments.received')}</button>
                    ) : p.refund_required ? (
                      <span className="tag bad">{t('admin.payments.refund')}</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ConfirmDialog
        open={!!confirming}
        title={t('admin.payments.confirmTitle')}
        body={confirming ? <p>{t('admin.payments.confirmBody', { amount: formatMoney(confirming.amount_minor, confirming.currency), reference: confirming.reference })}</p> : null}
        confirmLabel={t('admin.payments.received')}
        onClose={() => setConfirming(undefined)}
        onConfirm={async () => {
          const done = await api.post<Row>(`/admin/payments/manual/${confirming!.reference}/received`);
          setConfirming(undefined);
          toast.push(done.refund_required ? 'bad' : 'ok', done.refund_required ? t('admin.payments.refund') : t('admin.payments.done'));
          res.reload();
        }}
      />
    </div>
  );
}
