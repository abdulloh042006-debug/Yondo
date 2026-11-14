import { useState } from 'react';
import { Linking, Text, View } from 'react-native';

import { WEB_URL, api, errorText, type Schemas } from '../api';
import { useAuth, type User } from '../auth';
import { ICONS, Icon } from '../brand';
import { useNav } from '../nav';
import { formatInstant, prettyPhone, roleLabel, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, Chip, ErrorText, Field, H1, H2, MenuRow, P, Row, Screen } from '../ui';
import { useResource } from '../useResource';

type Role = Schemas['UserRoleType'];
export const openWeb = (path: string) => void Linking.openURL(`${WEB_URL}${path}`);

/**
 * The Profil tab = the web's /account hub (apps/web/src/pages/Account.tsx), same blocks in the same order:
 * header card → menu (Bronlar, Bildirişnomalar, Sevimlilar, Hamroh studiyasi, Yordam, Sozlamalar) → personal data →
 * "Men kimman" roles → sign out → account deletion. The web footer's documents follow. A row whose screen exists
 * only on the web says so and opens the web page in the browser.
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
  const { reload, logout } = useAuth();
  const [age, setAge] = useState(user.age?.toString() ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [city, setCity] = useState(user.city ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [rolesBusy, setRolesBusy] = useState(false);
  const unread = useResource(() => api.get<{ unread_count: number }>('/notifications/unread-count'), [user.id]);
  const web = !!WEB_URL;

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

  const toggleRole = async (role: 'customer' | 'companion') => {
    // The server replaces the whole non-admin role set, so every other role we know of is sent again (as on the web).
    const current = user.roles.filter((r) => r !== 'admin');
    const next: Role[] = current.includes(role) ? current.filter((r) => r !== role) : [...current, role];
    if (next.length === 0) return setNotice(t('account.minRole'));
    setRolesBusy(true);
    setNotice(undefined);
    try {
      await api.put('/auth/roles', { roles: next });
      await reload();
      setNotice(t('account.rolesUpdated'));
    } catch (e) {
      setNotice(errorText(e));
    } finally {
      setRolesBusy(false);
    }
  };

  const n = unread.data?.unread_count ?? 0;
  return (
    <Screen>
      <H1>{t('account.title')}</H1>
      {notice && <Banner text={notice} />}
      <Card>
        <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
          <View style={{ width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.pill }}>
            <Icon d={ICONS.user} size={26} color={palette.fg} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <H2>{prettyPhone(user.phone_number)}</H2>
            <Text style={{ color: palette.muted, fontFamily: FONT.body }}>{user.roles.map(roleLabel).join(', ') || '—'}</Text>
          </View>
        </View>
        <P muted>{`${t('account.memberSince')}: ${formatInstant(user.created_at)}`}</P>
        {!user.roles.includes('admin') && <P muted style={{ fontSize: 14 }}>{t('account.statusNote')}</P>}
      </Card>

      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <View aria-label={t('account.menu')}>
          <MenuRow title={t('nav.bookings')} hint={t('account.menu.bookingsHint')} onPress={() => nav.switchTab('bookings')} />
          {web && (
            <MenuRow
              title={t('nav.notifications')}
              hint={t('account.menu.notificationsHint')}
              badge={n ? t('notif.unread', { n }) : undefined}
              web
              onPress={() => openWeb('/notifications')}
            />
          )}
          <MenuRow title={t('nav.favorites')} hint={t('account.menu.favoritesHint')} onPress={() => nav.switchTab('favorites')} />
          {web && user.roles.includes('companion') && (
            <MenuRow title={t('account.studio')} hint={t('account.menu.studioHint')} web onPress={() => openWeb('/studio')} />
          )}
          {web && <MenuRow title={t('help.title')} hint={t('account.menu.helpHint')} web onPress={() => openWeb('/help')} />}
          <MenuRow title={t('settings.title')} hint={t('account.menu.settingsHint')} onPress={() => nav.push({ name: 'settings' })} />
        </View>
        {!web && <P muted style={{ fontSize: 14, paddingHorizontal: 8, paddingTop: 8 }}>{t('mobile.webMissing')}</P>}
      </Card>

      <Card style={{ gap: 12 }}>
        <H2>{t('account.personal')}</H2>
        <Field label={t('account.age')} inputMode="numeric" keyboardType="number-pad" value={age} onChangeText={setAge} error={ageError} />
        <Field label={t('account.gender')} value={gender} maxLength={64} onChangeText={setGender} />
        <Field label={t('common.city')} value={city} maxLength={128} onChangeText={setCity} />
        {err && <ErrorText text={err} />}
        <Row>
          <Button label={t('common.save')} busy={busy} disabled={!!ageError} onPress={() => void save()} />
        </Row>
      </Card>

      <Card style={{ gap: 12 }}>
        <H2>{t('account.whoAmI')}</H2>
        <P muted>{t('account.whoAmIHint')}</P>
        <Row>
          {(['customer', 'companion'] as const).map((r) => (
            <Chip toggle key={r} label={roleLabel(r)} selected={user.roles.includes(r)} onPress={() => !rolesBusy && void toggleRole(r)} />
          ))}
        </Row>
      </Card>

      <Row>
        <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
      </Row>

      {web ? (
        <Card style={{ gap: 0, paddingVertical: 8 }}>
          <View aria-label={t('mobile.documents')}>
            <MenuRow title={t('account.delete.title')} web onPress={() => openWeb('/account')} />
            <MenuRow title={t('legal.terms')} web onPress={() => openWeb('/terms')} />
            <MenuRow title={t('legal.privacy')} web onPress={() => openWeb('/privacy')} />
          </View>
        </Card>
      ) : null}
    </Screen>
  );
}
