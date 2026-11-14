import { useState } from 'react';
import { Linking, Text, View } from 'react-native';

import { WEB_URL, api, errorText, type Schemas } from '../api';
import { useAuth, type User } from '../auth';
import { ICONS, Icon } from '../brand';
import { useNav } from '../nav';
import { prettyPhone, roleLabel, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, ErrorText, Field, H1, H2, MenuRow, P, Row, Screen } from '../ui';
import { useResource } from '../useResource';

type CompanionProfile = Schemas['ProfileResponse'];
export const openWeb = (path: string) => void Linking.openURL(`${WEB_URL}${path}`);

/**
 * The Profil tab = the web's /account (apps/web/src/pages/Account.tsx). Owner decision 2026-11-14: Profil holds only
 * the person — picture, name, "about" (a companion's public profile), personal data with a "Tahrirlash" button — and
 * opens Sozlamalar, where everything about the app and the account lives. Bronlar/Sevimlilar are tabs, not repeated.
 */
export function AccountScreen() {
  const { user } = useAuth();
  if (!user) return null;
  // Remount when the server-side profile changes so the form always starts from saved values (as on the web).
  return <AccountView key={`${user.age}|${user.gender}|${user.city}`} user={user} />;
}

function AccountView({ user }: { user: User }) {
  const nav = useNav();
  const { palette } = useTheme();
  const { reload } = useAuth();
  const [editing, setEditing] = useState(false);
  const [age, setAge] = useState(user.age?.toString() ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [city, setCity] = useState(user.city ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [notice, setNotice] = useState<string>();
  // A companion's public profile gives the name and "about"; a customer has none, so the phone number stands in.
  const isCompanion = user.roles.includes('companion');
  const companion = useResource(
    () => (isCompanion ? api.get<CompanionProfile>('/companions/me/profile') : Promise.resolve(null)),
    [user.id, isCompanion],
  );
  const pub = companion.data ?? null;

  const ageNum = age.trim() === '' ? null : Number(age);
  const ageError = ageNum !== null && (!Number.isInteger(ageNum) || ageNum < 18 || ageNum > 120) ? t('account.ageRange') : undefined;

  const save = async () => {
    if (ageError) return;
    setBusy(true);
    setErr(undefined);
    setNotice(undefined);
    try {
      await api.put('/auth/profile', { age: ageNum, gender: gender.trim() || null, city: city.trim() || null });
      await reload();
      setNotice(t('account.saved'));
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const kv = (label: string, value: string) => (
    <View key={label} style={{ flexDirection: 'row', gap: 12, paddingVertical: 4 }}>
      <Text style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 15, width: 110 }}>{label}</Text>
      <Text style={{ color: palette.fg, fontFamily: FONT.medium, fontSize: 15, flex: 1 }}>{value}</Text>
    </View>
  );

  return (
    <Screen>
      <H1>{t('account.title')}</H1>
      {notice && <Banner text={notice} />}
      <Card>
        <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
          <View style={{ width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.pill }}>
            <Icon d={ICONS.user} size={28} color={palette.fg} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <H2>{pub?.display_name || prettyPhone(user.phone_number)}</H2>
            <Text style={{ color: palette.muted, fontFamily: FONT.body }}>{user.roles.map(roleLabel).join(', ') || '—'}</Text>
          </View>
        </View>
        {!!pub?.bio && (
          <View style={{ gap: 4, paddingTop: 4 }}>
            <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 15 }}>{t('common.description')}</Text>
            <P>{pub.bio}</P>
          </View>
        )}
      </Card>

      {editing ? (
        <Card style={{ gap: 12 }}>
          <H2>{t('account.personal')}</H2>
          <Field label={t('account.age')} inputMode="numeric" keyboardType="number-pad" value={age} onChangeText={setAge} error={ageError} />
          <Field label={t('account.gender')} value={gender} maxLength={64} onChangeText={setGender} />
          <Field label={t('common.city')} value={city} maxLength={128} onChangeText={setCity} />
          {err && <ErrorText text={err} />}
          <Row>
            <Button label={t('common.save')} busy={busy} disabled={!!ageError} onPress={() => void save()} />
            <Button kind="ghost" label={t('common.cancel')} disabled={busy} onPress={() => setEditing(false)} />
          </Row>
        </Card>
      ) : (
        <Card style={{ gap: 8 }}>
          <H2>{t('account.personal')}</H2>
          <View>
            {/* The phone is the heading when there is no public name; listed here only when a name replaces it. */}
            {pub?.display_name ? kv(t('account.phone'), prettyPhone(user.phone_number)) : null}
            {kv(t('account.age'), user.age?.toString() ?? '—')}
            {kv(t('account.gender'), user.gender || '—')}
            {kv(t('common.city'), user.city || '—')}
          </View>
          <Row>
            <Button label={t('common.edit')} onPress={() => setEditing(true)} />
          </Row>
        </Card>
      )}

      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <MenuRow title={t('settings.title')} hint={t('account.menu.settingsHint')} onPress={() => nav.push({ name: 'settings' })} />
      </Card>
    </Screen>
  );
}
