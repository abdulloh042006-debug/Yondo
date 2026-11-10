import { useState } from 'react';
import { Linking } from 'react-native';

import { ApiError, api, errorText, idempotencyKey, type Schemas } from '../api';
import { useAuth } from '../auth';
import { useNav } from '../nav';
import { BOOKING_STATUS, REPORT_CATEGORY, formatInstant, formatMoney, roleLabel, serviceLabel, t, type Key } from '../shared';
import { Banner, Button, Card, Chip, ChipGroup, ErrorText, Field, H1, H2, Loading, P, Row, Screen, Sheet, Tag, useConfirm } from '../ui';
import { useResource } from '../useResource';
import { ATTENTION, type Booking } from './Bookings';
import { SosButton } from './Sos';

type Payment = Schemas['PaymentResponse'];
const PAYMENT_STATUS = ['creating', 'pending', 'succeeded', 'failed'];

export function BookingDetailScreen({ id }: { id: string }) {
  const nav = useNav();
  const { user } = useAuth();
  const res = useResource(() => api.get<Booking>(`/bookings/${id}`), [id]);
  const blocked = useResource(() => api.get<string[]>('/safety/blocked-bookings'), [id]);
  const confirm = useConfirm();
  const [reporting, setReporting] = useState(false);
  const [notice, setNotice] = useState<string>();
  const b = res.data;
  if (res.loading && !b) return <Screen><Loading /></Screen>;
  if (!b) {
    return (
      <Screen>
        <H1>{res.error instanceof ApiError && res.error.status === 404 ? t('bd.notFound') : t('common.failedTitle')}</H1>
        <P muted>{errorText(res.error)}</P>
        <Button kind="ghost" label={t('bd.back')} onPress={nav.back} />
      </Screen>
    );
  }
  const mine = b.customer_id === user?.id; // the customer side of this booking
  const isCompanion = !!user?.roles.includes('companion');
  const isBlocked = !!blocked.data?.includes(b.id);
  const act = (kind: 'accept' | 'decline' | 'cancel') =>
    confirm.ask({
      title: t(`bookings.${kind}.title` as Key),
      body: t(`bookings.${kind}.body` as Key),
      confirm: t(`bookings.${kind}.confirm` as Key),
      run: async () => {
        await api.post(`/bookings/${b.id}/${kind}`, kind === 'accept' ? undefined : { reason: '' });
        setNotice(t(`bookings.${kind}.done` as Key));
        res.reload();
      },
    });
  const toggleBlock = () =>
    isBlocked
      ? void api.del(`/safety/bookings/${b.id}/block`).then(() => { setNotice(t('block.undone')); blocked.reload(); }, (e) => setNotice(errorText(e)))
      : confirm.ask({
          title: t('block.title'),
          body: t('block.body'),
          confirm: t('block.action'),
          run: async () => {
            await api.put(`/safety/bookings/${b.id}/block`);
            setNotice(t('block.done'));
            blocked.reload();
          },
        });

  return (
    <Screen>
      <Button kind="ghost" small label={t('bd.back')} onPress={nav.back} />
      <H1>{t('bd.title')}</H1>
      <Row>
        <Tag text={BOOKING_STATUS[b.status]?.label ?? b.status} attention={ATTENTION.has(b.status)} />
        {isBlocked && <Tag text={t('block.blockedTag')} attention />}
      </Row>
      <Card>
        <P>{serviceLabel(b.service_code)}</P>
        <P muted>{`${t('common.time')}: ${formatInstant(b.starts_at)} — ${formatInstant(b.ends_at)} (${t('common.minutesShort', { n: b.duration_minutes })})`}</P>
        <P muted>{`${t('common.place')}: ${b.meeting_place}`}</P>
        <P muted>{`${t('common.price')}: ${formatMoney(b.price_minor, b.currency)}`}</P>
        <P muted>{`${t('bookings.yourRole')}: ${roleLabel(mine ? 'customer' : 'companion')}`}</P>
      </Card>
      {notice && <Banner text={notice} />}
      <PaymentSection booking={b} isCustomer={mine} onChanged={res.reload} />
      <Row>
        {isCompanion && !mine && b.status === 'pending' && (
          <>
            <Button small label={t('bookings.accept.confirm')} onPress={() => act('accept')} />
            <Button small kind="ghost" label={t('bookings.decline.confirm')} onPress={() => act('decline')} />
          </>
        )}
        {['pending', 'accepted', 'confirmed'].includes(b.status) && (
          <Button small kind="ghost" label={t('bookings.cancel.confirm')} onPress={() => act('cancel')} />
        )}
        <Button small kind="ghost" label={t('reportForm.action')} onPress={() => setReporting(true)} />
        <Button small kind="ghost" label={isBlocked ? t('block.undo') : t('block.action')} onPress={toggleBlock} />
        {(b.status === 'confirmed' || b.status === 'active') && <SosButton />}
      </Row>
      <P muted>{t('mobile.webOnly')}</P>
      {confirm.element}
      {reporting && <ReportSheet bookingId={b.id} aboutCompanion={mine} onClose={(sent) => { setReporting(false); if (sent) setNotice(t('reportForm.sent')); }} />}
    </Screen>
  );
}

/** Pay only when the booking is `accepted`; one Idempotency-Key per booking. 503 = unavailable, not declined. */
function PaymentSection({ booking, isCustomer, onChanged }: { booking: Booking; isCustomer: boolean; onChanged: () => void }) {
  const payments = useResource(() => api.get<Payment[]>(`/payments/bookings/${booking.id}`), [booking.id, booking.status]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const latest = payments.data?.[payments.data.length - 1];
  const pay = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      const key = await idempotencyKey(booking.id);
      const p = await api.post<Payment>(`/payments/bookings/${booking.id}`, undefined, { headers: { 'Idempotency-Key': key } });
      payments.setData([...(payments.data ?? []), p]);
    } catch (e) {
      const error = e instanceof ApiError ? e : new ApiError(0, 'network_error');
      setErr(error);
      if (error.code === 'booking_expired') onChanged();
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card>
      <H2>{t('bd.pay.title')}</H2>
      <P muted>{t('bd.pay.note')}</P>
      {latest && PAYMENT_STATUS.includes(latest.status) && (
        <P>{t('bd.pay.status', { status: t(`payment.status.${latest.status}` as Key) })}</P>
      )}
      {latest?.checkout_url && booking.status === 'accepted' && (
        <>
          <Banner text={t('bd.pay.waiting')} />
          <Button label={t('bd.pay.open')} onPress={() => void Linking.openURL(latest.checkout_url!)} />
        </>
      )}
      {booking.status === 'accepted'
        ? isCustomer
          ? !latest?.checkout_url && <Button label={t('bd.pay.button')} busy={busy} onPress={() => void pay()} />
          : <P muted>{t('bd.pay.customerOnly')}</P>
        : !['confirmed', 'active', 'completed'].includes(booking.status) && <P muted>{t('bd.pay.notNow')}</P>}
      {err && (err.unavailable ? <Banner text={err.message} /> : <ErrorText text={err.message} />)}
    </Card>
  );
}

type Category = Schemas['ReportWrite']['category'];
const CATEGORIES = Object.keys(REPORT_CATEGORY) as Category[];

/** Reports go through `booking_id`: the server derives the other side; the app never sees their user id. */
function ReportSheet({ bookingId, aboutCompanion, onClose }: { bookingId: string; aboutCompanion: boolean; onClose: (sent: boolean) => void }) {
  const [category, setCategory] = useState<Category>('other');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const send = async () => {
    if (!description.trim()) return setErr(t('reportForm.descriptionRequired'));
    setBusy(true);
    setErr(undefined);
    try {
      await api.post('/safety/reports', { booking_id: bookingId, category, description: description.trim() });
      onClose(true);
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Sheet open title={t('reportForm.action')} onClose={() => !busy && onClose(false)}>
      <P muted>{aboutCompanion ? t('reportForm.aboutCompanion') : t('reportForm.aboutCustomer')}</P>
      <P>{t('reportForm.category')}</P>
      <ChipGroup label={t('reportForm.category')}>
        {CATEGORIES.map((c) => (
          <Chip key={c} label={REPORT_CATEGORY[c]} selected={c === category} onPress={() => setCategory(c)} />
        ))}
      </ChipGroup>
      <Field label={t('reportForm.description')} value={description} onChangeText={setDescription} multiline maxLength={2000} style={{ minHeight: 96, textAlignVertical: 'top' }} />
      <Banner text={t('reportForm.note')} />
      {err && <ErrorText text={err} />}
      <Row>
        <Button kind="ghost" label={t('common.cancel')} disabled={busy} onPress={() => onClose(false)} />
        <Button label={t('reportForm.send')} busy={busy} onPress={() => void send()} />
      </Row>
    </Sheet>
  );
}
