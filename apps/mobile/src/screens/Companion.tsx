import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { useEffect, useState } from 'react';
import { Image, Text, View } from 'react-native';
import { api, ApiError, type Page } from '../api';
import { confirm } from '../confirm';
import { dayKey, formatDateTime, formatDay, formatMoney, formatTime, SERVICE_NAMES, tashkentInstant } from '../format';
import { useNav } from '../nav';
import type { Booking } from '../types';
import { Badge, Body, Button, Card, Chip, Chips, Empty, ErrorText, Field, H2, Loading, Muted, Row, Screen, colors, useAction, useAsync } from '../ui';

interface Status {
  application_status: string;
  content_status: string;
  account_status: string;
  identity_status: string;
  activation_requested: boolean;
  publicly_active: boolean;
  blockers: string[];
}

const BLOCKERS: Record<string, [string, string | null]> = {
  application_not_approved: ['Ariza tasdiqlanmagan', 'companionEdit'],
  content_not_approved: ['Profil kontenti tasdiqlanmagan', 'companionEdit'],
  account_not_active: ['Akkaunt faol emas', 'editProfile'],
  companion_role_required: ['Companion roli tanlanmagan', 'editProfile'],
  identity_not_verified: ['Shaxs tasdiqlanmagan (ID + selfie)', 'verification'],
};

async function optional<T>(load: () => Promise<T>): Promise<T | null> {
  try {
    return await load();
  } catch (exc) {
    if (exc instanceof ApiError && exc.status === 404) return null;
    throw exc;
  }
}

export function CompanionDashboardScreen() {
  const nav = useNav();
  const status = useAsync(() => optional(() => api.get<Status>('/companions/me/status')), []);
  const requests = useAsync(() => api.get<Page<Booking>>('/bookings', { role: 'companion', status: 'pending', limit: 20 }), []);
  const upcoming = useAsync(() => api.get<Page<Booking>>('/bookings', { role: 'companion', scope: 'upcoming', limit: 20 }), []);
  const action = useAction();
  const s = status.data;
  return (
    <Screen title="Companion paneli" back={false}>
      <ErrorText error={status.error ?? action.error} />
      <Loading show={status.loading && !s} />
      {!status.loading && !s && (
        <Card>
          <Text style={{ fontWeight: '700', fontSize: 16 }}>Companion bo'lish</Text>
          <Muted>Ariza va profilni to'ldiring, xizmatlar, rasmlar va bo'sh vaqtlarni qo'shing, so'ng tekshiruvga yuboring.</Muted>
          <Button title="Boshlash" onPress={() => nav.push('companionEdit')} />
        </Card>
      )}
      {s && (
        <Card>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700', fontSize: 16 }}>Holat</Text>
            <Badge label={s.publicly_active ? 'Faol — qidiruvda ko‘rinadi' : 'Faol emas'} tone={s.publicly_active ? 'green' : 'amber'} />
          </Row>
          <Muted>Ariza: {s.application_status} · Kontent: {s.content_status} · Identity: {s.identity_status}</Muted>
          {s.blockers.map((blocker) => {
            const [label, screen] = BLOCKERS[blocker] ?? [blocker, null];
            return <Chip key={blocker} label={`⚠ ${label}`} onPress={screen ? () => nav.push(screen) : undefined} />;
          })}
          {!s.blockers.length && !s.activation_requested && (
            <Button title="Profilni faollashtirish" onPress={() => void action.run(() => api.post('/companions/me/activate'), status.reload)} disabled={action.busy} />
          )}
          {s.activation_requested && (
            <Button title="Vaqtincha o'chirish" variant="secondary" onPress={() => void action.run(() => api.post('/companions/me/deactivate'), status.reload)} disabled={action.busy} />
          )}
        </Card>
      )}
      <Row>
        <Button small variant="secondary" title="Profil va ariza" onPress={() => nav.push('companionEdit')} />
        <Button small variant="secondary" title="Xizmatlar" onPress={() => nav.push('services')} />
        <Button small variant="secondary" title="Bo'sh vaqtlar" onPress={() => nav.push('availability')} />
        <Button small variant="secondary" title="Rasmlar" onPress={() => nav.push('photos')} />
        <Button small variant="secondary" title="Daromad" onPress={() => nav.push('earnings')} />
      </Row>
      <H2>Bron so'rovlari</H2>
      {requests.data?.items.map((b) => (
        <Card key={b.id} onPress={() => nav.push('booking', { bookingId: b.id })}>
          <Text style={{ fontWeight: '700' }}>{b.customer.display_name}{b.customer.rating_average ? ` · ★ ${b.customer.rating_average}` : ''}</Text>
          <Muted>{SERVICE_NAMES[b.service_code] ?? b.service_code} · {formatDateTime(b.starts_at, b.timezone)} · {b.meeting_place.name}</Muted>
          <Text>{formatMoney(b.companion_payout_minor, b.currency)}</Text>
        </Card>
      ))}
      {requests.data && !requests.data.items.length && <Muted>Yangi so'rovlar yo'q.</Muted>}
      <H2>Kelgusi uchrashuvlar</H2>
      {upcoming.data?.items.filter((b) => b.status !== 'pending').map((b) => (
        <Card key={b.id} onPress={() => nav.push('booking', { bookingId: b.id })}>
          <Text style={{ fontWeight: '700' }}>{b.customer.display_name} · {b.status}</Text>
          <Muted>{formatDateTime(b.starts_at, b.timezone)} · {b.meeting_place.name}</Muted>
        </Card>
      ))}
    </Screen>
  );
}

interface Application { id: string; status: string; statement: string; review_note: string | null }
interface Profile {
  id: string; display_name: string; bio: string; languages: string[]; interests: string[];
  content_status: string; review_note: string | null; area: string | null;
}

export function CompanionEditScreen() {
  const application = useAsync(() => optional(() => api.get<Application>('/companions/me/application')), []);
  const profile = useAsync(() => optional(() => api.get<Profile>('/companions/me/profile')), []);
  const [statement, setStatement] = useState('');
  const [name, setName] = useState('');
  const [bio, setBio] = useState('');
  const [languages, setLanguages] = useState('uz');
  const [interests, setInterests] = useState('');
  const [area, setArea] = useState('');
  const action = useAction();
  useEffect(() => {
    if (application.data) setStatement(application.data.statement);
  }, [application.data]);
  useEffect(() => {
    if (profile.data) {
      setName(profile.data.display_name);
      setBio(profile.data.bio);
      setLanguages(profile.data.languages.join(', '));
      setInterests(profile.data.interests.join(', '));
      setArea(profile.data.area ?? '');
    }
  }, [profile.data]);
  const list = (value: string) => value.split(',').map((v) => v.trim()).filter(Boolean);
  const reload = async () => { await application.reload(); await profile.reload(); };
  const app = application.data;
  const prof = profile.data;

  const saveLocation = () => void action.run(async () => {
    let coords = {};
    try {
      if ((await Location.requestForegroundPermissionsAsync()).granted) {
        const position = await Location.getCurrentPositionAsync();
        coords = { latitude: position.coords.latitude, longitude: position.coords.longitude };
      }
    } catch {
      // Area name alone is enough; coordinates only power distance search.
    }
    await api.put('/companions/me/location', { area: area || null, ...coords });
  }, reload);

  return (
    <Screen title="Profil va ariza">
      <ErrorText error={application.error ?? profile.error ?? action.error} />
      <H2>1. Ariza</H2>
      {app && <Row><Badge label={app.status} />{app.review_note ? <Muted>{app.review_note}</Muted> : null}</Row>}
      <Field label="Nega companion bo'lmoqchisiz?" value={statement} onChangeText={setStatement} multiline />
      <Row>
        <Button small title={app ? 'Arizani saqlash' : 'Ariza yaratish'} disabled={action.busy || app?.status === 'submitted' || app?.status === 'approved'}
          onPress={() => void action.run(() => (app ? api.put('/companions/me/application', { statement }) : api.post('/companions/me/application', { statement })), reload)} />
        {app?.status === 'draft' && <Button small variant="secondary" title="Yuborish" onPress={() => void action.run(() => api.post('/companions/me/application/submit'), reload)} />}
      </Row>
      {app && (
        <>
          <H2>2. Profil (moderatsiyadan o'tadi)</H2>
          {prof && <Row><Badge label={prof.content_status} />{prof.review_note ? <Muted>{prof.review_note}</Muted> : null}</Row>}
          <Muted>Profil, xizmat yoki rasm o'zgarsa, qayta tasdiqlash talab qilinadi.</Muted>
          <Field label="Ko'rinadigan ism" value={name} onChangeText={setName} />
          <Field label="Bio" value={bio} onChangeText={setBio} multiline />
          <Field label="Tillar (vergul bilan)" value={languages} onChangeText={setLanguages} />
          <Field label="Qiziqishlar (vergul bilan)" value={interests} onChangeText={setInterests} />
          <Row>
            <Button small title="Profilni saqlash" disabled={action.busy || !name.trim()}
              onPress={() => void action.run(() => {
                const body = { display_name: name, bio, languages: list(languages), interests: list(interests) };
                return prof ? api.put('/companions/me/profile', body) : api.post('/companions/me/profile', body);
              }, reload)} />
            {prof && ['draft', 'rejected'].includes(prof.content_status) && (
              <Button small variant="secondary" title="Tekshiruvga yuborish" onPress={() => void action.run(() => api.post('/companions/me/profile/submit'), reload)} />
            )}
          </Row>
          {prof && (
            <>
              <H2>3. Taxminiy hudud</H2>
              <Muted>Aniq manzil ko'rsatilmaydi; koordinatalar ~1 km gacha yaxlitlanadi.</Muted>
              <Field label="Hudud (masalan, Yunusobod)" value={area} onChangeText={setArea} />
              <Button small variant="secondary" title="Hududni saqlash" onPress={saveLocation} disabled={action.busy} />
            </>
          )}
        </>
      )}
    </Screen>
  );
}

interface Service { id: string; service_code: string; description: string; price_minor: number; currency: string; unit_minutes: number }

export function ServicesScreen() {
  const { data, error, reload } = useAsync(() => api.get<Service[]>('/companions/me/services'), []);
  const [code, setCode] = useState('coffee');
  const [price, setPrice] = useState('');
  const [unit, setUnit] = useState('60');
  const [description, setDescription] = useState('');
  const action = useAction();
  return (
    <Screen title="Xizmatlar va narxlar">
      <ErrorText error={error ?? action.error} />
      {data?.map((service) => (
        <Card key={service.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700' }}>{SERVICE_NAMES[service.service_code] ?? service.service_code}</Text>
            <Text>{formatMoney(service.price_minor, service.currency)} / {service.unit_minutes} daq</Text>
          </Row>
          {service.description ? <Muted>{service.description}</Muted> : null}
          <Button small variant="secondary" title="O'chirish" onPress={() => void action.run(() => api.del(`/companions/me/services/${service.id}`), reload)} />
        </Card>
      ))}
      {data && !data.length && <Empty text="Hali xizmat qo'shilmagan." />}
      <H2>Yangi xizmat</H2>
      <Chips value={code} onChange={(v) => setCode(v || 'coffee')} options={Object.entries(SERVICE_NAMES)} />
      <Field label="Narx (so'm)" value={price} onChangeText={setPrice} keyboardType="number-pad" />
      <Row>{['30', '60', '120'].map((m) => <Chip key={m} label={`${m} daq uchun`} selected={unit === m} onPress={() => setUnit(m)} />)}</Row>
      <Field label="Tavsif" value={description} onChangeText={setDescription} multiline />
      <Button title="Qo'shish" disabled={!price || action.busy} onPress={() => void action.run(() => api.post('/companions/me/services', {
        service_code: code, price_minor: Math.round(Number(price) * 100), currency: 'UZS', unit_minutes: Number(unit), description,
      }), async () => { setPrice(''); setDescription(''); await reload(); })} />
    </Screen>
  );
}

interface Window { id: string; starts_at: string; ends_at: string; timezone: string }
const HOURS = Array.from({ length: 16 }, (_, i) => `${String(i + 8).padStart(2, '0')}:00`);

export function AvailabilityScreen() {
  const { data, error, reload } = useAsync(() => api.get<Window[]>('/companions/me/availability'), []);
  const days = Array.from({ length: 14 }, (_, i) => dayKey(new Date(Date.now() + (i + 1) * 86_400_000)));
  const [day, setDay] = useState(days[0]);
  const [from, setFrom] = useState('10:00');
  const [to, setTo] = useState('18:00');
  const action = useAction();
  const future = (data ?? []).filter((w) => new Date(w.ends_at).getTime() > Date.now());
  return (
    <Screen title="Bo'sh vaqtlar">
      <Muted>Mijozlar faqat shu oraliqlarda bron qila oladi. Bron qilingan vaqtni o'chirib bo'lmaydi.</Muted>
      <ErrorText error={error ?? action.error} />
      {future.map((window) => (
        <Card key={window.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text>{formatDay(window.starts_at)} {formatTime(window.starts_at)}–{formatTime(window.ends_at)}</Text>
            <Button small variant="secondary" title="O'chirish" onPress={async () => {
              if (await confirm("O'chirish", "Bu oraliq o'chirilsinmi?")) await action.run(() => api.del(`/companions/me/availability/${window.id}`), reload);
            }} />
          </Row>
        </Card>
      ))}
      {data && !future.length && <Empty text="Kelgusi bo'sh vaqtlar yo'q." />}
      <H2>Qo'shish</H2>
      <Chips value={day} onChange={(v) => setDay(v || days[0])} options={days.map((d) => [d, formatDay(`${d}T12:00:00+05:00`)])} />
      <Muted>Boshlanish</Muted>
      <Chips value={from} onChange={(v) => setFrom(v || from)} options={HOURS.map((h) => [h, h])} />
      <Muted>Tugash</Muted>
      <Chips value={to} onChange={(v) => setTo(v || to)} options={HOURS.map((h) => [h, h])} />
      <Button title="Qo'shish" disabled={action.busy || to <= from} onPress={() => void action.run(() => api.post('/companions/me/availability', {
        starts_at: tashkentInstant(day, from), ends_at: tashkentInstant(day, to), timezone: 'Asia/Tashkent',
      }), reload)} />
    </Screen>
  );
}

interface Photo { id: string; caption: string; position: number }

export function PhotosScreen() {
  const { data, error, reload } = useAsync(async () => {
    const photos = await api.get<Photo[]>('/companions/me/photos');
    const urls = await Promise.all(photos.map((p) => api.get<{ url: string }>(`/companions/me/photos/${p.id}/download`).then((r) => r.url).catch(() => '')));
    return photos.map((photo, index) => ({ ...photo, url: urls[index] }));
  }, []);
  const action = useAction();
  const add = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85 });
    if (result.canceled) return;
    const asset = result.assets[0];
    await action.run(() => api.uploadImage('/companions/me/photos', asset.uri, asset.mimeType), reload);
  };
  const makePrimary = (id: string) => {
    if (!data) return;
    const order = [id, ...data.map((p) => p.id).filter((p) => p !== id)];
    void action.run(() => api.put('/companions/me/photos/order', { photo_ids: order }), reload);
  };
  return (
    <Screen title="Rasmlar">
      <Muted>Birinchi rasm asosiy rasm. Joylashuv (EXIF) ma'lumotlari serverda o'chiriladi.</Muted>
      <ErrorText error={error ?? action.error} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
        {data?.map((photo, index) => (
          <Card key={photo.id} style={{ padding: 8, width: 160 }}>
            {photo.url ? <Image source={{ uri: photo.url }} style={{ width: 142, height: 142, borderRadius: 8 }} /> : null}
            {index === 0 ? <Badge label="Asosiy" tone="green" /> : <Button small variant="secondary" title="Asosiy qilish" onPress={() => makePrimary(photo.id)} />}
            <Button small variant="danger" title="O'chirish" onPress={() => void action.run(() => api.del(`/companions/me/photos/${photo.id}`), reload)} />
          </Card>
        ))}
      </View>
      <Button title="Rasm qo'shish" onPress={() => void add()} disabled={action.busy} />
    </Screen>
  );
}

interface Earnings {
  summary: { currency: string; held_minor: number; scheduled_minor: number; available_minor: number; paid_minor: number }[];
  payouts: { id: string; amount_minor: number; currency: string; status: string; available_at: string | null; booking_id: string | null }[];
}

export function EarningsScreen() {
  const { data, error, loading } = useAsync(() => api.get<Earnings>('/payouts/me'), []);
  return (
    <Screen title="Daromadlar">
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.summary.map((s) => (
        <Card key={s.currency}>
          <Row style={{ justifyContent: 'space-between' }}><Muted>Uchrashuv kutilmoqda</Muted><Text>{formatMoney(s.held_minor, s.currency)}</Text></Row>
          <Row style={{ justifyContent: 'space-between' }}><Muted>Rejalashtirilgan</Muted><Text>{formatMoney(s.scheduled_minor, s.currency)}</Text></Row>
          <Row style={{ justifyContent: 'space-between' }}><Muted>To'lashga tayyor</Muted><Text style={{ fontWeight: '700' }}>{formatMoney(s.available_minor, s.currency)}</Text></Row>
          <Row style={{ justifyContent: 'space-between' }}><Muted>To'langan</Muted><Text>{formatMoney(s.paid_minor, s.currency)}</Text></Row>
        </Card>
      ))}
      {data?.payouts.map((p) => (
        <Card key={p.id}>
          <Row style={{ justifyContent: 'space-between' }}><Text>{formatMoney(p.amount_minor, p.currency)}</Text><Badge label={p.status} /></Row>
          {p.available_at ? <Muted>Mavjud: {formatDateTime(p.available_at)}</Muted> : null}
        </Card>
      ))}
      {data && !data.payouts.length && <Empty text="Hali daromad yo'q." />}
      <Body style={{ color: colors.muted }}>Nizo ochilsa, payout qaror chiqquncha ushlab turiladi.</Body>
    </Screen>
  );
}
