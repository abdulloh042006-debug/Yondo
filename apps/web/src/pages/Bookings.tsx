import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { formatInstant, formatMoney } from '../lib/format';
import { BOOKING_STATUS, serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Item } from '../ui/motion';

type Booking = Schemas['BookingResponse'];
type Action = { booking: Booking; kind: 'accept' | 'decline' | 'cancel' };

const COPY = {
  accept: { title: 'Bronni qabul qilasizmi?', confirm: 'Qabul qilish', body: 'Qabul qilgandan keyin mijoz to‘lov bosqichiga o‘tishi mumkin bo‘ladi.' },
  decline: { title: 'Bronni rad etasizmi?', confirm: 'Rad etish', body: 'Bu bronni keyin qayta tiklab bo‘lmaydi.' },
  cancel: { title: 'Bronni bekor qilasizmi?', confirm: 'Bekor qilish', body: 'Bekor qilishda har qanday qaytarish tartibi alohida ko‘rib chiqiladi; bu ilova hech qanday summani avtomatik qaytarmaydi.' },
} as const;

export function Bookings() {
  const { user } = useAuth();
  const res = useResource((signal) => api.get<Booking[]>('/bookings', { query: { limit: 50 }, signal }), []);
  const [action, setAction] = useState<Action>();
  const toast = useToast();
  const isCompanion = !!user?.roles.includes('companion');

  const run = async () => {
    if (!action) return;
    const { booking, kind } = action;
    const body = kind === 'cancel' || kind === 'decline' ? { reason: '' } : undefined;
    await api.post<Booking>(`/bookings/${booking.id}/${kind}`, body);
    toast.push('ok', kind === 'accept' ? 'Bron qabul qilindi.' : kind === 'decline' ? 'Bron rad etildi.' : 'Bron bekor qilindi.');
    setAction(undefined);
    res.reload();
  };

  return (
    <div className="stack" style={{ gap: 20 }}>
      <h1>Bronlarim</h1>
      <p className="banner">
        Bu versiyada bronlarni ko‘rish, yuborish, qabul qilish, rad etish va bekor qilish mavjud. To‘lov, chat va uchrashuv
        bosqichlari hali bu interfeysga ulanmagan.
      </p>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? (
        <Empty title="Hozircha bronlar yo‘q" action={<Link className="btn" to="/">Hamroh topish</Link>}>
          Bron yuborilgach, u shu yerda holati bilan ko‘rinadi.
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
                    <dt>Vaqt</dt><dd>{formatInstant(b.starts_at)} — {formatInstant(b.ends_at)} ({b.duration_minutes} daq)</dd>
                    <dt>Joy</dt><dd>{b.meeting_place}</dd>
                    <dt>Narx</dt><dd>{formatMoney(b.price_minor, b.currency)}</dd>
                    <dt>Rolingiz</dt><dd>{mine ? 'Mijoz' : 'Hamroh'}</dd>
                  </dl>
                  <div className="row">
                    {isCompanion && !mine && b.status === 'pending' && (
                      <>
                        <button className="btn sm" onClick={() => setAction({ booking: b, kind: 'accept' })}>Qabul qilish</button>
                        <button className="btn sm ghost" onClick={() => setAction({ booking: b, kind: 'decline' })}>Rad etish</button>
                      </>
                    )}
                    {['pending', 'accepted', 'confirmed'].includes(b.status) && (
                      <button className="btn sm ghost" onClick={() => setAction({ booking: b, kind: 'cancel' })}>Bekor qilish</button>
                    )}
                  </div>
                </article>
              </Item>
            );
          })}
        </div>
      )}
      {action && (
        <ConfirmDialog
          open
          danger={action.kind !== 'accept'}
          title={COPY[action.kind].title}
          body={COPY[action.kind].body}
          confirmLabel={COPY[action.kind].confirm}
          onConfirm={run}
          onClose={() => setAction(undefined)}
        />
      )}
    </div>
  );
}
