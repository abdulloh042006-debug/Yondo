import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import { Text, View } from 'react-native';
import { api, type Page } from '../api';
import { useAuth } from '../auth';
import { formatDateTime } from '../format';
import { useNav } from '../nav';
import type { CompanionCard, Notification } from '../types';
import { Badge, Button, Card, Chip, Empty, ErrorText, Field, H2, Loading, Muted, Row, Screen, useAction, useAsync } from '../ui';
import { CompanionTile } from './Discover';

export function ProfileScreen() {
  const nav = useNav();
  const { me, logout } = useAuth();
  const links: [string, string][] = [
    ['editProfile', "Shaxsiy ma'lumotlar"],
    ['verification', 'ID va selfie tasdiqlash'],
    ['favorites', 'Sevimlilar'],
    ['giftOrders', "Sovg'a buyurtmalari"],
    ['notifications', 'Bildirishnomalar'],
    ['safety', 'Xavfsizlik markazi'],
  ];
  if (me?.roles.includes('companion')) links.push(['dashboard', 'Companion paneli'], ['earnings', 'Daromadlar']);
  return (
    <Screen title="Profil" back={false}>
      <Card>
        <Text style={{ fontSize: 20, fontWeight: '800' }}>{me?.display_name}</Text>
        <Muted>{me?.phone_number} · {me?.city}</Muted>
        <Row>{me?.roles.map((role) => <Badge key={role} label={role} />)}</Row>
      </Card>
      {links.map(([screen, label]) => (
        <Card key={screen} onPress={() => nav.push(screen)}>
          <Row style={{ justifyContent: 'space-between' }}><Text style={{ fontSize: 16 }}>{label}</Text><Text>›</Text></Row>
        </Card>
      ))}
      {me?.roles.includes('vendor') && <Muted>Vendor paneli veb-saytda: do'kon, mahsulotlar va buyurtmalarni boshqarish.</Muted>}
      <Muted>Yordam va shikoyatlar uchun Xavfsizlik markazidan foydalaning.</Muted>
      <Button title="Chiqish" variant="secondary" onPress={() => void logout()} />
    </Screen>
  );
}

const GENDERS: [string, string][] = [['female', 'Ayol'], ['male', 'Erkak']];

export function EditProfileScreen() {
  const nav = useNav();
  const { me, refreshMe } = useAuth();
  const [name, setName] = useState(me?.display_name ?? '');
  const [age, setAge] = useState(me?.age ? String(me.age) : '');
  const [gender, setGender] = useState(me?.gender ?? '');
  const [city, setCity] = useState(me?.city ?? '');
  const [roles, setRoles] = useState<string[]>(me?.roles.filter((r) => r !== 'admin') ?? []);
  const action = useAction();
  const toggle = (role: string) => setRoles(roles.includes(role) ? roles.filter((r) => r !== role) : [...roles, role]);
  return (
    <Screen title="Shaxsiy ma'lumotlar">
      <Field label="Ism" value={name} onChangeText={setName} />
      <Field label="Yosh" value={age} onChangeText={setAge} keyboardType="number-pad" />
      <Row>{GENDERS.map(([key, label]) => <Chip key={key} label={label} selected={gender === key} onPress={() => setGender(key)} />)}</Row>
      <Field label="Shahar" value={city} onChangeText={setCity} />
      <H2>Rollar</H2>
      <Row>
        {[['customer', 'Mijoz'], ['companion', 'Companion'], ['vendor', 'Vendor']].map(([role, label]) => (
          <Chip key={role} label={label} selected={roles.includes(role)} onPress={() => toggle(role)} />
        ))}
      </Row>
      <ErrorText error={action.error} />
      <Button title="Saqlash" disabled={action.busy || !roles.length} onPress={() => void action.run(async () => {
        await api.put('/auth/profile', { display_name: name, age: Number(age), gender, city });
        await api.put('/auth/roles', { roles });
        await refreshMe();
      }, nav.pop)} />
    </Screen>
  );
}

interface Verification {
  id: string;
  status: string;
  has_document: boolean;
  has_selfie: boolean;
  review_note: string | null;
}

export function VerificationScreen() {
  const { data, error, reload } = useAsync(() => api.get<Verification | null>('/verification/me'), []);
  const action = useAction();
  const upload = async (part: 'document' | 'selfie') => {
    const picker = part === 'selfie' ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
    const result = await picker({ mediaTypes: ['images'], quality: 0.85 });
    if (result.canceled) return;
    const asset = result.assets[0];
    await action.run(() => api.uploadImage(`/verification/me/${part}`, asset.uri, asset.mimeType), reload);
  };
  const editable = !data || data.status === 'draft' || data.status === 'rejected';
  return (
    <Screen title="Shaxsni tasdiqlash">
      <Muted>Hujjat va selfie faqat moderatorlar uchun ko'rinadi va ochiq profilda ko'rsatilmaydi. Companion bo'lish uchun tasdiqlash majburiy.</Muted>
      <ErrorText error={error ?? action.error} />
      {data && (
        <Card>
          <Row><Text style={{ fontWeight: '700' }}>Holat:</Text><Badge label={data.status} tone={data.status === 'verified' ? 'green' : data.status === 'rejected' ? 'danger' : 'amber'} /></Row>
          {data.review_note ? <Muted>Izoh: {data.review_note}</Muted> : null}
        </Card>
      )}
      {editable && (!data || data.status !== 'draft') && (
        <Row>
          {[['passport', 'Pasport'], ['id_card', 'ID karta'], ['driver_license', "Haydovchilik guvohnomasi"]].map(([type, label]) => (
            <Button key={type} small variant="secondary" title={label} disabled={action.busy}
              onPress={() => void action.run(() => api.post('/verification/me', { document_type: type }), reload)} />
          ))}
        </Row>
      )}
      {data?.status === 'draft' && (
        <View style={{ gap: 8 }}>
          <Button title={data.has_document ? 'Hujjat yuklandi ✓ (almashtirish)' : 'Hujjat rasmini yuklash'} variant="secondary" onPress={() => void upload('document')} disabled={action.busy} />
          <Button title={data.has_selfie ? 'Selfie yuklandi ✓ (almashtirish)' : 'Selfie olish'} variant="secondary" onPress={() => void upload('selfie')} disabled={action.busy} />
          <Button title="Tekshiruvga yuborish" disabled={!data.has_document || !data.has_selfie || action.busy}
            onPress={() => void action.run(() => api.post('/verification/me/submit'), reload)} />
        </View>
      )}
    </Screen>
  );
}

export function NotificationsScreen() {
  const nav = useNav();
  const { data, error, loading, reload } = useAsync(() => api.get<Page<Notification>>('/notifications', { limit: 50 }), []);
  const action = useAction();
  return (
    <Screen title="Bildirishnomalar" right={<Button small variant="secondary" title="Hammasini o'qish" onPress={() => void action.run(() => api.post('/notifications/read-all'), reload)} />}>
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.items.map((item) => (
        <Card key={item.id} onPress={() => {
          void api.post(`/notifications/${item.id}/read`).catch(() => undefined);
          if (item.data.booking_id) nav.push('booking', { bookingId: item.data.booking_id });
        }}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: item.read_at ? '400' : '700' }}>{item.title}</Text>
            {!item.read_at && <Badge label="yangi" />}
          </Row>
          {item.body ? <Muted>{item.body}</Muted> : null}
          <Muted>{formatDateTime(item.created_at)}</Muted>
        </Card>
      ))}
      {data && !data.items.length && <Empty text="Bildirishnomalar yo'q." />}
    </Screen>
  );
}

export function FavoritesScreen() {
  const { data, error, loading } = useAsync(() => api.get<CompanionCard[]>('/favorites/companions'), []);
  return (
    <Screen title="Sevimlilar">
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.map((item) => <CompanionTile key={item.profile_id} item={item} wide />)}
      {data && !data.length && <Empty text="Sevimli companionlar yo'q." />}
    </Screen>
  );
}
