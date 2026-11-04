import * as Location from 'expo-location';
import { useState } from 'react';
import { Linking, Text } from 'react-native';
import { api } from '../api';
import { confirm } from '../confirm';
import { useNav } from '../nav';
import type { Contact } from '../types';
import { Body, Button, Card, Chip, ErrorText, Field, H2, Loading, Muted, Row, Screen, colors, useAction, useAsync } from '../ui';

interface Center {
  guide: { key: string; text: string }[];
  emergency_numbers: { service: string; number: string }[];
  trusted_contacts: Contact[];
  active_booking_id: string | null;
  open_reports: number;
}

const SERVICES: Record<string, string> = {
  unified_emergency: 'Yagona favqulodda xizmat',
  fire: "Yong'in xizmati",
  police: 'Politsiya',
  ambulance: 'Tez yordam',
  gas: 'Gaz xizmati',
};

export function SafetyScreen() {
  const nav = useNav();
  const { data, error, reload } = useAsync(() => api.get<Center>('/safety/center'), []);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const action = useAction();
  const sos = async () => {
    if (!(await confirm('SOS', 'Xavfsizlik jamoasiga signal yuboriladi. Hayotga xavf bo‘lsa, 112 ga qo‘ng‘iroq qiling.'))) return;
    await action.run(async () => {
      let coords = {};
      try {
        if ((await Location.requestForegroundPermissionsAsync()).granted) {
          const position = await Location.getCurrentPositionAsync();
          coords = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        }
      } catch {
        // Send without location.
      }
      await api.post('/safety/sos', { confirm: true, ...coords });
    });
  };
  if (!data) return <Screen title="Xavfsizlik markazi"><ErrorText error={error} /><Loading show={!error} /></Screen>;
  return (
    <Screen title="Xavfsizlik markazi">
      <Button title="🆘 SOS signal yuborish" variant="danger" onPress={() => void sos()} disabled={action.busy} />
      {data.active_booking_id && (
        <Button title="Faol bronni ochish" variant="secondary" onPress={() => nav.push('booking', { bookingId: data.active_booking_id })} />
      )}
      <ErrorText error={action.error} />
      <H2>Favqulodda raqamlar</H2>
      <Row>
        {data.emergency_numbers.map((item) => (
          <Chip key={item.number} label={`${item.number} · ${SERVICES[item.service] ?? item.service}`} onPress={() => void Linking.openURL(`tel:${item.number}`)} />
        ))}
      </Row>
      <H2>Ishonchli kontaktlar</H2>
      {data.trusted_contacts.map((contact) => (
        <Card key={contact.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '600' }}>{contact.name}</Text>
            <Button small variant="secondary" title="O'chirish" onPress={() => void action.run(() => api.del(`/safety/contacts/${contact.id}`), reload)} />
          </Row>
          <Muted>{contact.phone_number}</Muted>
        </Card>
      ))}
      {data.trusted_contacts.length < 5 && (
        <Card>
          <Field label="Ism" value={name} onChangeText={setName} />
          <Field label="Telefon" value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
          <Button title="Kontakt qo'shish" disabled={!name || !phone || action.busy}
            onPress={() => void action.run(() => api.post('/safety/contacts', { name, phone_number: phone }), async () => { setName(''); setPhone(''); await reload(); })} />
        </Card>
      )}
      <H2>Xavfsizlik qoidalari</H2>
      {data.guide.map((item) => <Body key={item.key}>• {item.text}</Body>)}
      <Muted>Ochiq shikoyatlaringiz: {data.open_reports}</Muted>
      <Text style={{ color: colors.muted, fontSize: 12 }}>Bloklangan foydalanuvchilar sizni ko'ra olmaydi, sizga yoza olmaydi va bron qila olmaydi.</Text>
    </Screen>
  );
}

const CATEGORIES: [string, string][] = [
  ['harassment', 'Bezovtalik'], ['inappropriate_request', "Noo'rin taklif"], ['fake_profile', 'Soxta profil'],
  ['fraud', 'Firibgarlik'], ['unsafe_behavior', 'Xavfli xatti-harakat'], ['no_show', 'Kelmadi'],
  ['payment_issue', "To'lov muammosi"], ['other', 'Boshqa'],
];

export function ReportScreen() {
  const nav = useNav();
  const { userId, name, bookingId } = nav.params<{ userId: string; name?: string; bookingId?: string }>();
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [sent, setSent] = useState(false);
  const action = useAction();
  return (
    <Screen title="Shikoyat">
      <Muted>{name ? `${name} haqida shikoyat. ` : ''}Moderatorlar ko'rib chiqadi; shikoyatchi ma'lumotlari sir saqlanadi.</Muted>
      <Row>{CATEGORIES.map(([key, label]) => <Chip key={key} label={label} selected={category === key} onPress={() => setCategory(key)} />)}</Row>
      <Field label="Tavsif" value={description} onChangeText={setDescription} multiline />
      <ErrorText error={action.error} />
      {sent ? <Body>Rahmat! Shikoyatingiz qabul qilindi.</Body> : (
        <Button title="Yuborish" disabled={!category || action.busy} onPress={() => void action.run(
          () => api.post('/reports', { reported_user_id: userId, booking_id: bookingId ?? null, category, description }),
          () => setSent(true),
        )} />
      )}
      <Button title="Bu foydalanuvchini bloklash" variant="danger" disabled={action.busy}
        onPress={() => void action.run(() => api.put(`/blocks/${userId}`), nav.pop)} />
    </Screen>
  );
}
