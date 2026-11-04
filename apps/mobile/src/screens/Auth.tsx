import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Text, View } from 'react-native';
import { api } from '../api';
import { useAuth } from '../auth';
import { Body, Button, Card, Chip, ErrorText, Field, Muted, Row, Screen, colors, messageOf, styles } from '../ui';

export function LoginScreen() {
  const { requestOtp, verifyOtp } = useAuth();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!sent) {
        const devCode = await requestOtp(phone);
        setSent(true);
        setHint(devCode ? `Test kodi: ${devCode}` : 'SMS kod yuborildi.');
      } else {
        await verifyOtp(phone, code);
      }
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: colors.bg, justifyContent: 'center', padding: 20 }}>
      <View style={{ gap: 6, marginBottom: 24 }}>
        <Text style={{ fontSize: 36, fontWeight: '800', color: colors.primary }}>Yondo</Text>
        <Body>Ishonchli companion toping, xavfsiz bron qiling.</Body>
        <Muted>Bu dating yoki escort platforma emas — ijtimoiy companion va experience booking.</Muted>
      </View>
      <Card>
        <Field label="Telefon raqam" value={phone} onChangeText={setPhone} placeholder="+998 90 123 45 67" keyboardType="phone-pad" editable={!sent} />
        {sent && <Field label="SMS kod" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />}
        {hint && <Text style={{ color: colors.primary }}>{hint}</Text>}
        <ErrorText error={error} />
        <Button title={sent ? 'Kirish' : 'Kod olish'} disabled={busy || !phone || (sent && code.length !== 6)} onPress={() => void submit()} />
        {sent && <Button title="Raqamni o'zgartirish" variant="secondary" onPress={() => { setSent(false); setCode(''); setHint(null); }} />}
      </Card>
    </KeyboardAvoidingView>
  );
}

const GENDERS: [string, string][] = [['female', 'Ayol'], ['male', 'Erkak']];
const CITIES = ['Tashkent', 'Samarkand', 'Andijan', 'Fergana', 'Bukhara'];

export function ProfileSetupScreen() {
  const { me, refreshMe, logout } = useAuth();
  const [name, setName] = useState(me?.display_name ?? '');
  const [age, setAge] = useState(me?.age ? String(me.age) : '');
  const [gender, setGender] = useState(me?.gender ?? '');
  const [city, setCity] = useState(me?.city ?? 'Tashkent');
  const [roles, setRoles] = useState<string[]>(me?.roles.filter((r) => r !== 'admin').length ? me!.roles.filter((r) => r !== 'admin') : ['customer']);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toggle = (role: string) => setRoles((current) => (current.includes(role) ? current.filter((r) => r !== role) : [...current, role]));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const profile = await api.put<{ account_status: string }>('/auth/profile', {
        display_name: name.trim(), age: Number(age), gender, city,
      });
      await api.put('/auth/roles', { roles });
      if (profile.account_status !== 'active') {
        setError("Akkaunt faollashmadi: platformadan foydalanish uchun yoshingiz talabga mos bo'lishi kerak.");
      }
      await refreshMe();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="Profilni to'ldirish" back={false}>
      <Muted>Telefon raqamingiz va uy manzilingiz boshqalarga ko'rsatilmaydi.</Muted>
      <Card>
        <Field label="Ism" value={name} onChangeText={setName} placeholder="Ismingiz" />
        <Field label="Yosh" value={age} onChangeText={setAge} keyboardType="number-pad" maxLength={3} />
        <Text style={styles.label}>Jins</Text>
        <Row>{GENDERS.map(([key, label]) => <Chip key={key} label={label} selected={gender === key} onPress={() => setGender(key)} />)}</Row>
        <Text style={styles.label}>Shahar</Text>
        <Row>{CITIES.map((item) => <Chip key={item} label={item} selected={city === item} onPress={() => setCity(item)} />)}</Row>
        <Text style={styles.label}>Platformadan qanday foydalanasiz?</Text>
        <Row>
          <Chip label="Companion topaman" selected={roles.includes('customer')} onPress={() => toggle('customer')} />
          <Chip label="Companion bo'laman" selected={roles.includes('companion')} onPress={() => toggle('companion')} />
          <Chip label="Gul/sovg'a sotaman" selected={roles.includes('vendor')} onPress={() => toggle('vendor')} />
        </Row>
        <ErrorText error={error} />
        <Button title="Davom etish" disabled={busy || !name.trim() || !age || !gender || !roles.length} onPress={() => void save()} />
      </Card>
      <Button title="Chiqish" variant="secondary" onPress={() => void logout()} />
    </Screen>
  );
}
