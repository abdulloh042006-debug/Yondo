import Constants from 'expo-constants';
import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { WEB_URL, api, errorText, type Schemas } from '../api';
import { useAuth, type User } from '../auth';
import { useNav } from '../nav';
import { LANGS, UZ_ALPHABETS, formatInstant, getLang, getUzAlphabet, roleLabel, setLang, setUzAlphabet, t, useLang } from '../shared';
import { FONT, useTheme, type ThemeChoice } from '../theme';
import { Banner, Button, Card, Chip, ChipGroup, ConfirmDialog, ErrorText, H1, H2, Loading, MenuRow, P, Row, Screen } from '../ui';
import { useResource } from '../useResource';
import { ConsentCheck } from './Login';
import { openWeb } from './Account';

type Role = Schemas['UserRoleType'];

/**
 * The web's /settings (apps/web/src/pages/Settings.tsx), same groups and order. Owner decision 2026-11-14: everything
 * about the app and the account lives here — language, alphabet, theme, notifications, account (roles, companion
 * studio, sign out, deletion), help & safety, documents. Opened from Profil, and from Kirish when signed out.
 */
export function SettingsScreen() {
  useLang();
  const nav = useNav();
  const { user } = useAuth();
  const { choice, setChoice } = useTheme();
  const unread = useResource(() => (user ? api.get<{ unread_count: number }>('/notifications/unread-count') : Promise.resolve(null)), [user?.id]);
  const themes: { id: ThemeChoice; label: string }[] = [
    { id: 'system', label: t('mobile.themeSystem') },
    { id: 'yondo', label: t('theme.yondo.label') },
    { id: 'yondo-tun', label: t('theme.yondo-tun.label') },
  ];
  const n = unread.data?.unread_count ?? 0;
  return (
    <Screen>
      {nav.canGoBack && (
        <Row>
          <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
        </Row>
      )}
      <H1>{t('settings.title')}</H1>
      <Card>
        <H2>{t('settings.language')}</H2>
        <ChipGroup label={t('settings.language')}>
          {LANGS.map((l) => (
            <Chip key={l.id} label={l.label} selected={getLang() === l.id} onPress={() => void setLang(l.id).catch(() => {})} />
          ))}
        </ChipGroup>
        {getLang() === 'uz' && (
          <>
            <P>{t('settings.alphabet')}</P>
            <ChipGroup label={t('settings.alphabet')}>
              {UZ_ALPHABETS.map((a) => (
                <Chip key={a.id} label={`${a.label} (${a.letters})`} selected={getUzAlphabet() === a.id} onPress={() => setUzAlphabet(a.id)} />
              ))}
            </ChipGroup>
          </>
        )}
      </Card>
      <Card>
        <H2>{t('settings.themeGroup')}</H2>
        <ChipGroup label={t('settings.themeGroup')}>
          {themes.map((th) => (
            <Chip key={th.id} label={th.label} selected={choice === th.id} onPress={() => setChoice(th.id)} />
          ))}
        </ChipGroup>
      </Card>
      {user && (
        <Card style={{ gap: 0, paddingVertical: 8 }}>
          <MenuRow
            title={t('nav.notifications')}
            hint={t('account.menu.notificationsHint')}
            badge={n ? t('notif.unread', { n }) : undefined}
            onPress={() => nav.push({ name: 'notifications' })}
          />
        </Card>
      )}
      <Card style={{ gap: 12 }}>
        <H2>{t('settings.account')}</H2>
        {user ? <AccountGroup user={user} /> : <Button label={t('nav.login')} onPress={() => nav.switchTab('login')} />}
      </Card>
      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <View style={{ paddingHorizontal: 8, paddingBottom: 4 }}>
          <H2>{t('settings.safety')}</H2>
        </View>
        <MenuRow title={t('help.title')} hint={t('settings.safetyHint')} onPress={() => nav.push({ name: 'help' })} />
      </Card>
      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <View style={{ paddingHorizontal: 8, paddingBottom: 4, gap: 4 }}>
          <H2>{t('settings.about')}</H2>
          <P muted>{`${t('settings.version')}: ${Constants.expoConfig?.version ?? '—'}`}</P>
        </View>
        {WEB_URL ? (
          <>
            <MenuRow title={t('legal.terms')} web onPress={() => openWeb('/terms')} />
            <MenuRow title={t('legal.privacy')} web onPress={() => openWeb('/privacy')} />
          </>
        ) : (
          <P muted style={{ paddingHorizontal: 8 }}>{t('mobile.webMissing')}</P>
        )}
      </Card>
    </Screen>
  );
}

/** "Men kimman" (roles), the companion studio (web) and sign out, as in the web's Settings → Hisob. */
function AccountGroup({ user }: { user: User }) {
  const { reload, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string>();
  const toggleRole = async (role: 'customer' | 'companion') => {
    // The server replaces the whole non-admin role set, so every other role we know of is sent again (as on the web).
    const current = user.roles.filter((r) => r !== 'admin');
    const next: Role[] = current.includes(role) ? current.filter((r) => r !== role) : [...current, role];
    if (next.length === 0) return setNotice(t('account.minRole'));
    setBusy(true);
    setNotice(undefined);
    try {
      await api.put('/auth/roles', { roles: next });
      await reload();
      setNotice(t('account.rolesUpdated'));
    } catch (e) {
      setNotice(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <P style={{ fontFamily: FONT.bold }}>{t('account.whoAmI')}</P>
      <P muted>{t('account.whoAmIHint')}</P>
      {notice && <Banner text={notice} />}
      <Row>
        {(['customer', 'companion'] as const).map((r) => (
          <Chip toggle key={r} label={roleLabel(r)} selected={user.roles.includes(r)} onPress={() => !busy && void toggleRole(r)} />
        ))}
      </Row>
      {user.roles.includes('companion') && WEB_URL ? (
        <View style={{ marginHorizontal: -8 }}>
          <MenuRow title={t('account.studio')} hint={t('account.menu.studioHint')} web onPress={() => openWeb('/studio')} />
        </View>
      ) : null}
      <DeleteAccount before={<Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />} />
    </>
  );
}

type Deletion = Schemas['DeletionState'];

/**
 * In-app account deletion, the same API and texts as the web (apps/web/src/pages/DeleteAccount.tsx). Owner,
 * 2026-11-15: the button looks exactly like "Chiqish" (no red block); the question opens in a blurred dialog.
 */
function DeleteAccount({ before }: { before: ReactNode }) {
  const res = useResource(() => api.get<Deletion>('/account/deletion'), []);
  const [open, setOpen] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const days = res.data?.window_days ?? 30;
  const request = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      res.setData(await api.post<Deletion>('/account/deletion', { confirm: true }));
      setNotice(t('account.delete.requested'));
      setOpen(false);
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const cancel = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      await api.del('/account/deletion');
      setNotice(t('account.delete.cancelled'));
      res.reload();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <View style={{ gap: 10 }}>
      {notice && <Banner text={notice} />}
      {res.data?.pending ? (
        <>
          <Row>
            {before}
            <Button kind="ghost" label={t('account.delete.cancel')} busy={busy} onPress={() => void cancel()} />
          </Row>
          <Banner text={t('account.delete.pending', { date: formatInstant(res.data.due_at) })} />
          <P muted>{t('account.delete.pendingNote')}</P>
        </>
      ) : (
        <Row>
          {before}
          {res.data && (
            <Button kind="ghost" label={t('account.delete.title')} onPress={() => { setUnderstood(false); setErr(undefined); setOpen(true); }} />
          )}
        </Row>
      )}
      {res.loading && !res.data && <Loading />}
      {!!res.error && (
        <>
          <ErrorText text={errorText(res.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={res.reload} />
        </>
      )}
      {err && !open && <ErrorText text={err} />}
      <ConfirmDialog open={open} title={t('account.delete.ask')} onClose={() => !busy && setOpen(false)}>
        <P>{t('account.delete.body', { days })}</P>
        <P muted>{t('account.delete.pendingNote')}</P>
        <P muted style={{ fontSize: 14 }}>{t('account.delete.openBookings')}</P>
        <ConsentCheck checked={understood} onChange={setUnderstood} label={t('account.delete.confirmCheck')} />
        {err && <ErrorText text={err} />}
        <Row>
          <Button label={t('account.delete.yes')} busy={busy} disabled={!understood} onPress={() => void request()} />
          <Button kind="ghost" label={t('account.delete.no')} disabled={busy} onPress={() => setOpen(false)} />
        </Row>
      </ConfirmDialog>
    </View>
  );
}
