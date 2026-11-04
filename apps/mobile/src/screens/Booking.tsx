import * as Location from 'expo-location';
import * as WebBrowser from 'expo-web-browser';
import { useMemo, useState } from 'react';
import { Share, Text, View } from 'react-native';
import { api, API_ORIGIN, type Page } from '../api';
import { confirm, newIdempotencyKey } from '../confirm';
import { dayKey, formatDateTime, formatDay, formatMoney, formatTime, SERVICE_NAMES, STATUS_NAMES, tashkentInstant } from '../format';
import { useNav } from '../nav';
import type { Booking, Payment, ProductCard, PublicProfile, Quote } from '../types';
import {
  Badge, Body, Button, Card, Chip, Chips, Empty, ErrorText, Field, H2, Loading, Muted, Row, Screen, colors, useAction, useAsync,
} from '../ui';

const LEAD_MINUTES = 60;

function startOptions(profile: PublicProfile, day: string, duration: number): string[] {
  const earliest = Date.now() + LEAD_MINUTES * 60_000;
  const options: string[] = [];
  for (const slot of profile.availability) {
    if (dayKey(slot.starts_at) !== day) continue;
    const end = new Date(slot.ends_at).getTime();
    let cursor = new Date(slot.starts_at).getTime();
    cursor = Math.ceil(cursor / 1_800_000) * 1_800_000; // align to 30 minutes
    for (; cursor + duration * 60_000 <= end; cursor += 1_800_000) {
      if (cursor >= earliest) options.push(new Date(cursor).toISOString());
    }
  }
  return options;
}

export function BookingCreateScreen() {
  const nav = useNav();
  const { profileId } = nav.params<{ profileId: string }>();
  const { data: profile, error } = useAsync(() => api.get<PublicProfile>(`/discovery/companions/${profileId}`), [profileId]);
  const [serviceId, setServiceId] = useState('');
  const [duration, setDuration] = useState(0);
  const [day, setDay] = useState('');
  const [start, setStart] = useState('');
  const [place, setPlace] = useState('');
  const [address, setAddress] = useState('');
  const [note, setNote] = useState('');
  const [quote, setQuote] = useState<Quote | null>(null);
  const [accepted, setAccepted] = useState(false);
  const action = useAction();

  const service = profile?.service_details.find((s) => s.id === serviceId) ?? profile?.service_details[0];
  const unit = service?.unit_minutes ?? 60;
  const durations = useMemo(() => [1, 2, 3, 4].map((n) => n * unit).filter((m) => m <= 480), [unit]);
  const effectiveDuration = duration || durations[0];
  const days = useMemo(() => Array.from(new Set((profile?.availability ?? []).map((s) => dayKey(s.starts_at)))), [profile]);
  const starts = profile && day ? startOptions(profile, day, effectiveDuration) : [];

  if (!profile) return <Screen title="Bron"><ErrorText error={error} /><Loading show={!error} /></Screen>;
  const payload = () => ({
    profile_id: profileId,
    service_id: service!.id,
    starts_at: start,
    duration_minutes: effectiveDuration,
    meeting_place: { name: place.trim(), address: address.trim() },
    note: note.trim(),
  });
  return (
    <Screen title={`Bron: ${profile.display_name}`}>
      <H2>1. Xizmat</H2>
      <Row>
        {profile.service_details.map((s) => (
          <Chip key={s.id} label={`${SERVICE_NAMES[s.service_code] ?? s.service_code} · ${formatMoney(s.price_minor, s.currency)}/${s.unit_minutes}m`}
            selected={service?.id === s.id} onPress={() => { setServiceId(s.id); setDuration(0); setStart(''); setQuote(null); }} />
        ))}
      </Row>
      <H2>2. Davomiylik</H2>
      <Row>{durations.map((m) => <Chip key={m} label={`${m} daq`} selected={effectiveDuration === m} onPress={() => { setDuration(m); setStart(''); setQuote(null); }} />)}</Row>
      <H2>3. Sana</H2>
      <Chips value={day} onChange={(v) => { setDay(v); setStart(''); setQuote(null); }} options={days.map((d) => [d, formatDay(`${d}T12:00:00+05:00`)])} />
      {day ? (
        <>
          <H2>4. Vaqt</H2>
          <Row>{starts.map((s) => <Chip key={s} label={formatTime(s)} selected={start === s} onPress={() => { setStart(s); setQuote(null); }} />)}</Row>
          {!starts.length && <Muted>Bu kunda ushbu davomiylik uchun bo'sh vaqt yo'q.</Muted>}
        </>
      ) : null}
      <H2>5. Uchrashuv joyi</H2>
      <Muted>Faqat jamoat joylari (kafe, park, kino, savdo markazi).</Muted>
      <Field label="Joy nomi" value={place} onChangeText={(t) => { setPlace(t); setQuote(null); }} placeholder="Masalan: Cafe Central" />
      <Field label="Manzil" value={address} onChangeText={(t) => { setAddress(t); setQuote(null); }} />
      <Field label="Izoh (ixtiyoriy)" value={note} onChangeText={setNote} multiline />
      <ErrorText error={action.error} />
      {!quote ? (
        <Button title="Narxni ko'rish" disabled={!start || !place.trim() || action.busy}
          onPress={() => void action.run(async () => setQuote(await api.post<Quote>('/bookings/quote', payload())))} />
      ) : (
        <Card>
          <H2>Bron xulosasi</H2>
          <Row style={{ justifyContent: 'space-between' }}><Muted>Xizmat</Muted><Text>{formatMoney(quote.service_amount_minor, quote.currency)}</Text></Row>
          <Row style={{ justifyContent: 'space-between' }}><Muted>Platforma to'lovi</Muted><Text>{formatMoney(quote.platform_fee_minor, quote.currency)}</Text></Row>
          <Row style={{ justifyContent: 'space-between' }}><Text style={{ fontWeight: '700' }}>Jami</Text><Text style={{ fontWeight: '700' }}>{formatMoney(quote.total_minor, quote.currency)}</Text></Row>
          <Muted>{formatDateTime(quote.starts_at, quote.timezone)} – {formatTime(quote.ends_at, quote.timezone)}</Muted>
          <Muted>
            Bekor qilish: uchrashuvdan {quote.contract.cancellation_policy.free_cancellation_hours} soat oldin — bepul; keyinroq —
            {' '}{quote.contract.cancellation_policy.late_cancellation_refund_bps / 100}% qaytariladi; boshlangandan keyin — qaytarilmaydi.
          </Muted>
          <Muted>Jinsiy, escort va noqonuniy xizmatlar qat'iyan taqiqlangan. Muloqot va to'lov faqat Yondo ichida.</Muted>
          <Chip label={accepted ? '✓ Shartnoma va qoidalarga roziman' : 'Shartnoma va qoidalarga roziman'} selected={accepted} onPress={() => setAccepted(!accepted)} />
          <Button title="So'rov yuborish" disabled={!accepted || action.busy}
            onPress={() => void action.run(async () => {
              const booking = await api.post<Booking>('/bookings', { ...payload(), accept_contract: true });
              nav.replace('booking', { bookingId: booking.id });
            })} />
          <Muted>To'lov companion so'rovni qabul qilgandan keyin amalga oshiriladi.</Muted>
        </Card>
      )}
    </Screen>
  );
}

export function BookingsScreen() {
  const nav = useNav();
  const [scope, setScope] = useState('upcoming');
  const { data, error, loading } = useAsync(
    () => api.get<Page<Booking>>('/bookings', { scope, limit: 50 }), [scope],
  );
  return (
    <Screen title="Bronlar" back={false}>
      <Chips value={scope} onChange={(v) => setScope(v || 'upcoming')} options={[['upcoming', 'Kelgusi'], ['past', "O'tgan"], ['all', 'Hammasi']]} />
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.items.map((booking) => <BookingRow key={booking.id} booking={booking} onPress={() => nav.push('booking', { bookingId: booking.id })} />)}
      {data && !data.items.length && <Empty text="Bronlar yo'q." />}
    </Screen>
  );
}

function tone(status: string) {
  if (['confirmed', 'completed', 'active'].includes(status)) return 'green' as const;
  if (['cancelled', 'no_show', 'disputed'].includes(status)) return 'danger' as const;
  return 'amber' as const;
}

function BookingRow({ booking, onPress }: { booking: Booking; onPress: () => void }) {
  const other = booking.role === 'customer' ? booking.companion : booking.customer;
  return (
    <Card onPress={onPress}>
      <Row style={{ justifyContent: 'space-between' }}>
        <Text style={{ fontWeight: '700', fontSize: 16 }}>{other.display_name}</Text>
        <Badge label={STATUS_NAMES[booking.status] ?? booking.status} tone={tone(booking.status)} />
      </Row>
      <Muted>{SERVICE_NAMES[booking.service_code] ?? booking.service_code} · {formatDateTime(booking.starts_at, booking.timezone)}</Muted>
      <Muted>{booking.meeting_place.name} · {formatMoney(booking.total_minor, booking.currency)}</Muted>
      {booking.role === 'companion' && <Badge label="Siz companion" tone="primary" />}
    </Card>
  );
}

export function BookingDetailScreen() {
  const nav = useNav();
  const { bookingId } = nav.params<{ bookingId: string }>();
  const { data: booking, error, reload } = useAsync(() => api.get<Booking>(`/bookings/${bookingId}`), [bookingId]);
  const action = useAction();
  const [giftId, setGiftId] = useState('');
  const flowers = useAsync(() => api.get<{ items: ProductCard[] }>('/gifts/products', { category: 'flowers', limit: 10 }), []);
  if (!booking) return <Screen title="Bron"><ErrorText error={error} /><Loading show={!error} /></Screen>;
  const other = booking.role === 'customer' ? booking.companion : booking.customer;
  const can = (name: string) => booking.actions.includes(name);
  const post = (path: string, body?: unknown) => action.run(() => api.post(`/bookings/${bookingId}/${path}`, body), reload);

  const pay = () => action.run(async () => {
    const payment = await api.post<Payment>(`/payments/bookings/${bookingId}/checkout`, {
      idempotency_key: newIdempotencyKey('pay'),
      gifts: giftId ? { items: [{ product_id: giftId, quantity: 1 }], note: '' } : null,
    });
    if (payment.checkout_url) await WebBrowser.openBrowserAsync(payment.checkout_url);
  }, reload);
  const cancel = async () => {
    const preview = await api.get<{ refund_minor: number; policy: string }>(`/bookings/${bookingId}/cancellation`);
    const ok = await confirm('Bronni bekor qilish', preview.refund_minor ? `${formatMoney(preview.refund_minor, booking.currency)} qaytariladi.` : "Pul qaytarilmaydi yoki to'lov qilinmagan.");
    if (ok) await post('cancel', {});
  };
  const share = () => action.run(async () => {
    const result = await api.post<{ path: string; message: string }>(`/bookings/${bookingId}/share`, {});
    await Share.share({ message: `${result.message} ${API_ORIGIN}${result.path}` });
  });
  const sos = async () => {
    if (!(await confirm('SOS', 'Xavfsizlik jamoasiga signal yuboriladi. Favqulodda holatda 112 ga qo‘ng‘iroq qiling.'))) return;
    await action.run(async () => {
      let coords: { latitude?: number; longitude?: number } = {};
      try {
        const permission = await Location.requestForegroundPermissionsAsync();
        if (permission.granted) {
          const position = await Location.getCurrentPositionAsync();
          coords = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        }
      } catch {
        // Send without location rather than not at all.
      }
      await api.post('/safety/sos', { booking_id: bookingId, confirm: true, ...coords });
    });
  };

  return (
    <Screen title={other.display_name ?? 'Bron'}>
      <Card>
        <Row style={{ justifyContent: 'space-between' }}>
          <Text style={{ fontWeight: '700', fontSize: 17 }}>{SERVICE_NAMES[booking.service_code] ?? booking.service_code}</Text>
          <Badge label={STATUS_NAMES[booking.status] ?? booking.status} tone={tone(booking.status)} />
        </Row>
        <Body>{formatDateTime(booking.starts_at, booking.timezone)} – {formatTime(booking.ends_at, booking.timezone)} ({booking.duration_minutes} daq)</Body>
        <Body>📍 {booking.meeting_place.name} {booking.meeting_place.address}</Body>
        {booking.note ? <Muted>Izoh: {booking.note}</Muted> : null}
        <Muted>{booking.role === 'customer' ? 'Companion' : 'Mijoz'}: {other.display_name}{other.rating_average ? ` · ★ ${other.rating_average}` : ''}</Muted>
        <Row style={{ justifyContent: 'space-between' }}><Muted>Jami</Muted><Text style={{ fontWeight: '700' }}>{formatMoney(booking.total_minor, booking.currency)}</Text></Row>
        {booking.companion_payout_minor !== null && <Muted>Sizga to'lanadi: {formatMoney(booking.companion_payout_minor, booking.currency)}</Muted>}
        {booking.refund_minor ? <Muted>Qaytarilgan: {formatMoney(booking.refund_minor, booking.currency)}</Muted> : null}
        {booking.payment_due_at && <Muted>To'lov muddati: {formatDateTime(booking.payment_due_at)}</Muted>}
        {booking.status === 'pending' && <Muted>Companion javobi kutilmoqda ({formatDateTime(booking.request_expires_at)} gacha).</Muted>}
        {booking.customer_checked_in_at && <Muted>Mijoz yetib keldi ✓</Muted>}
        {booking.companion_checked_in_at && <Muted>Companion yetib keldi ✓</Muted>}
      </Card>
      <ErrorText error={action.error} />
      {can('pay') && (
        <Card>
          <H2>To'lov</H2>
          {flowers.data?.items.length ? (
            <>
              <Muted>Uchrashuvga gul qo'shish (uchrashuv joyiga yetkaziladi):</Muted>
              <Chips value={giftId} onChange={setGiftId} options={flowers.data.items.map((p) => [p.id, `${p.name} · ${formatMoney(p.price_minor, p.currency)}`])} />
            </>
          ) : null}
          <Button title="To'lash" disabled={action.busy} onPress={() => void pay()} />
        </Card>
      )}
      <View style={{ gap: 8 }}>
        {can('accept') && <Button title="Qabul qilish" onPress={() => void post('accept')} disabled={action.busy} />}
        {can('decline') && <Button title="Rad etish" variant="danger" onPress={() => void post('decline', {})} disabled={action.busy} />}
        {can('check_in') && <Button title="I'm here — yetib keldim" onPress={() => void post('check-in')} disabled={action.busy} />}
        {can('start') && <Button title="Uchrashuvni boshlash" onPress={() => void post('start')} disabled={action.busy} />}
        {can('end') && <Button title="Uchrashuvni yakunlash" onPress={() => void post('end')} disabled={action.busy} />}
        {can('sos') && <Button title="🆘 SOS" variant="danger" onPress={() => void sos()} disabled={action.busy} />}
        {can('chat') && <Button title="Chat" variant="secondary" onPress={() => nav.push('chat', { bookingId })} />}
        {can('share') && <Button title="Ishonchli kontakt bilan ulashish" variant="secondary" onPress={() => void share()} disabled={action.busy} />}
        {can('review') && <Button title="Baho qoldirish" onPress={() => nav.push('review', { bookingId, role: booking.role })} />}
        {can('rebook') && <Button title="Qayta bron qilish (Book Again)" variant="secondary" onPress={() => nav.push('bookingCreate', { profileId: booking.profile_id })} />}
        {can('report_no_show') && <Button title="Ikkinchi tomon kelmadi (no-show)" variant="secondary" onPress={() => void post('no-show', {})} disabled={action.busy} />}
        {can('dispute') && <Button title="Muammo haqida xabar (nizo)" variant="secondary" onPress={() => nav.push('dispute', { bookingId })} />}
        {can('cancel') && <Button title="Bekor qilish" variant="danger" onPress={() => void cancel()} disabled={action.busy} />}
        <Button title="Shikoyat qilish" variant="secondary" onPress={() => nav.push('report', { userId: other.id, name: other.display_name, bookingId })} />
      </View>
    </Screen>
  );
}

const TAGS: Record<string, string[]> = {
  customer: ['punctual', 'friendly', 'great_conversation', 'respectful', 'as_described'],
  companion: ['respectful', 'punctual', 'polite', 'followed_rules', 'pleasant'],
};
const CRITERIA: Record<string, string[]> = {
  customer: ['punctuality', 'communication', 'friendliness', 'professionalism', 'profile_accuracy'],
  companion: ['respect', 'punctuality', 'communication', 'safety', 'rule_compliance'],
};

export function ReviewScreen() {
  const nav = useNav();
  const { bookingId, role } = nav.params<{ bookingId: string; role: string }>();
  const [rating, setRating] = useState(5);
  const [criteria, setCriteria] = useState<Record<string, number>>({});
  const [tags, setTags] = useState<string[]>([]);
  const [text, setText] = useState('');
  const action = useAction();
  return (
    <Screen title="Baho qoldirish">
      <H2>Umumiy baho</H2>
      <Row>{[1, 2, 3, 4, 5].map((n) => <Chip key={n} label={'★'.repeat(n)} selected={rating === n} onPress={() => setRating(n)} />)}</Row>
      <H2>Mezonlar (ixtiyoriy)</H2>
      {CRITERIA[role]?.map((name) => (
        <View key={name} style={{ gap: 4 }}>
          <Muted>{name}</Muted>
          <Row>{[1, 2, 3, 4, 5].map((n) => <Chip key={n} label={String(n)} selected={criteria[name] === n} onPress={() => setCriteria({ ...criteria, [name]: n })} />)}</Row>
        </View>
      ))}
      <H2>Teglar</H2>
      <Row>{TAGS[role]?.map((tag) => <Chip key={tag} label={tag} selected={tags.includes(tag)} onPress={() => setTags(tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag])} />)}</Row>
      <Field label="Fikr (ixtiyoriy)" value={text} onChangeText={setText} multiline />
      <ErrorText error={action.error} />
      <Button title="Yuborish" disabled={action.busy} onPress={() => void action.run(
        () => api.post(`/bookings/${bookingId}/review`, { rating, criteria, tags, text }), nav.pop,
      )} />
    </Screen>
  );
}

const CATEGORIES: [string, string][] = [
  ['unsafe_behavior', 'Xavfli xatti-harakat'], ['harassment', 'Bezovtalik'], ['inappropriate_request', "Noo'rin taklif"],
  ['no_show', 'Kelmadi'], ['payment_issue', "To'lov muammosi"], ['fraud', 'Firibgarlik'], ['other', 'Boshqa'],
];

export function DisputeScreen() {
  const nav = useNav();
  const { bookingId } = nav.params<{ bookingId: string }>();
  const existing = useAsync(async () => {
    try {
      return await api.get<{ id: string; status: string; category: string; description: string }>(`/bookings/${bookingId}/dispute`);
    } catch {
      return null;
    }
  }, [bookingId]);
  const [category, setCategory] = useState('unsafe_behavior');
  const [description, setDescription] = useState('');
  const [evidence, setEvidence] = useState('');
  const action = useAction();
  const dispute = existing.data;
  return (
    <Screen title="Nizo markazi">
      {dispute ? (
        <Card>
          <Text style={{ fontWeight: '700' }}>Nizo: {dispute.category}</Text>
          <Badge label={dispute.status} />
          <Body>{dispute.description}</Body>
          {dispute.status !== 'resolved' && (
            <>
              <Field label="Qo'shimcha dalil (matn)" value={evidence} onChangeText={setEvidence} multiline />
              <Button title="Dalil qo'shish" disabled={!evidence.trim() || action.busy}
                onPress={() => void action.run(() => api.post(`/disputes/${dispute.id}/evidence`, { note: evidence }), () => setEvidence(''))} />
            </>
          )}
        </Card>
      ) : (
        <>
          <Muted>Muammo turini tanlang va batafsil yozing. Administrator ko'rib chiqadi; shu vaqtda payout ushlab turiladi.</Muted>
          <Row>{CATEGORIES.map(([key, label]) => <Chip key={key} label={label} selected={category === key} onPress={() => setCategory(key)} />)}</Row>
          <Field label="Tavsif" value={description} onChangeText={setDescription} multiline />
          <Button title="Yuborish" disabled={!description.trim() || action.busy}
            onPress={() => void action.run(() => api.post(`/bookings/${bookingId}/dispute`, { category, description }), existing.reload)} />
        </>
      )}
      <ErrorText error={action.error ?? existing.error} />
      <Text style={{ color: colors.muted }}>Favqulodda holatda: 112</Text>
    </Screen>
  );
}
