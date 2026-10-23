import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { formatInstant, formatMoney } from '../lib/format';
import { BOOKING_STATUS, roleLabel, serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Item } from '../ui/motion';
import { ReportDialog } from '../ui/ReportDialog';

type Booking = Schemas['BookingResponse'];
type Action = { booking: Booking; kind: 'accept' | 'decline' | 'cancel' };

const copy = (kind: Action['kind']) => ({
  title: t(`bookings.${kind}.title`),
  confirm: t(`bookings.${kind}.confirm`),
  body: t(`bookings.${kind}.body`),
});

export function Bookings() {
  const { user } = useAuth();
  const res = useResource((signal) => api.get<Booking[]>('/bookings', { query: { limit: 50 }, signal }), []);
  const [action, setAction] = useState<Action>();
  const [reporting, setReporting] = useState<{ id: string; aboutCompanion: boolean }>();
  const toast = useToast();
  const isCompanion = !!user?.roles.includes('companion');

  const run = async () => {
    if (!action) return;
    const { booking, kind } = action;
    const body = kind === 'cancel' || kind === 'decline' ? { reason: '' } : undefined;
    await api.post<Booking>(`/bookings/${booking.id}/${kind}`, body);
    toast.push('ok', t(`bookings.${kind}.done`));
    setAction(undefined);
    res.reload();
  };

  return (
    <div className="stack" style={{ gap: 20 }}>
      <h1>{t('bookings.title')}</h1>
      <p className="banner">{t('bookings.banner')}</p>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? (
        <Empty title={t('bookings.empty')} action={<Link className="btn" to="/">{t('bookings.find')}</Link>}>
          {t('bookings.emptyBody')}
        </Empty>
      ) : (
        <div className="stack">
          {res.data.map((b, i) => {
            const mine = b.customer_id === user?.id;
            return (
              <Item key={b.id} index={i}>
                <article className="glass pad stack">
                  <div className="spread">
                    <h3>{serviceLabel(b.service_code)}</h3>
                    <StatusTag map={BOOKING_STATUS} value={b.status} />
                  </div>
                  <dl className="kv">
                    <dt>{t('common.time')}</dt><dd>{formatInstant(b.starts_at)} — {formatInstant(b.ends_at)} ({t('common.minutesShort', { n: b.duration_minutes })})</dd>
                    <dt>{t('common.place')}</dt><dd>{b.meeting_place}</dd>
                    <dt>{t('common.price')}</dt><dd>{formatMoney(b.price_minor, b.currency)}</dd>
                    <dt>{t('bookings.yourRole')}</dt><dd>{roleLabel(mine ? 'customer' : 'companion')}</dd>
                  </dl>
                  <div className="row">
                    {isCompanion && !mine && b.status === 'pending' && (
                      <>
                        <button className="btn sm" onClick={() => setAction({ booking: b, kind: 'accept' })}>{t('bookings.accept.confirm')}</button>
                        <button className="btn sm ghost" onClick={() => setAction({ booking: b, kind: 'decline' })}>{t('bookings.decline.confirm')}</button>
                      </>
                    )}
                    {['pending', 'accepted', 'confirmed'].includes(b.status) && (
                      <button className="btn sm ghost" onClick={() => setAction({ booking: b, kind: 'cancel' })}>{t('bookings.cancel.confirm')}</button>
                    )}
                    <button className="btn sm ghost" onClick={() => setReporting({ id: b.id, aboutCompanion: mine })}>{t('reportForm.action')}</button>
                  </div>
                </article>
              </Item>
            );
          })}
        </div>
      )}
      {reporting && <ReportDialog bookingId={reporting.id} aboutCompanion={reporting.aboutCompanion} onClose={() => setReporting(undefined)} />}
      {action && (
        <ConfirmDialog
          open
          danger={action.kind !== 'accept'}
          title={copy(action.kind).title}
          body={copy(action.kind).body}
          confirmLabel={copy(action.kind).confirm}
          onConfirm={run}
          onClose={() => setAction(undefined)}
        />
      )}
    </div>
  );
}
