import { Manrope_400Regular } from '@expo-google-fonts/manrope/400Regular';
import { Manrope_600SemiBold } from '@expo-google-fonts/manrope/600SemiBold';
import { Manrope_700Bold } from '@expo-google-fonts/manrope/700Bold';
import { SpaceGrotesk_600SemiBold } from '@expo-google-fonts/space-grotesk/600SemiBold';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, errorText, tokens, type Schemas } from './src/api';
import { AuthProvider, acceptLegal, useAuth } from './src/auth';
import { Aurora, BrandMark, ICONS, Icon, useReducedMotion } from './src/brand';
import { FavoritesProvider, useFavorites } from './src/favorites';
import { restoreLocale } from './src/locale';
import { NavProvider, useNav, type Tab } from './src/nav';
import { AccountScreen } from './src/screens/Account';
import { BookingDetailScreen } from './src/screens/BookingDetail';
import { BookingsScreen } from './src/screens/Bookings';
import { DiscoverScreen } from './src/screens/Discover';
import { FavoritesScreen } from './src/screens/Favorites';
import { HelpScreen } from './src/screens/Help';
import { ConsentCheck, LoginScreen } from './src/screens/Login';
import { PasswordSetupScreen } from './src/screens/Password';
import { NotificationsScreen } from './src/screens/Notifications';
import { ProfileScreen } from './src/screens/Profile';
import { SettingsScreen } from './src/screens/Settings';
import { t, useLang, type LegalDoc } from './src/shared';
import { FONT, ThemeProvider, useTheme } from './src/theme';
import { Button, ConfirmDialog, ErrorText, H1, Loading, P, Row, Screen, TOUCH } from './src/ui';
import { useResource } from './src/useResource';
import { hasLoginIntent } from './src/loginIntent';
import { biometricAvailable, biometricCheck, biometricEnabled, biometricOffered, setBiometricEnabled, setBiometricOffered } from './src/biometric';

/** Tokens, the saved language and the brand fonts are ready before the first render, so nothing flashes. */
export default function App() {
  const [ready, setReady] = useState(false);
  const [locked, setLocked] = useState(false);
  const [fontsLoaded, fontError] = useFonts({ SpaceGrotesk_600SemiBold, Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold });
  useEffect(() => {
    void Promise.all([tokens.load(), restoreLocale()])
      .then(async () => {
        // Face ID / fingerprint on: a saved session opens only after the check (BiometricUnlock below).
        if (!tokens.has() || !(await biometricEnabled())) return;
        if (await biometricAvailable()) return setLocked(true);
        await dropSession(); // biometrics were removed from the phone: sign in again instead
      })
      .finally(() => setReady(true));
  }, []);
  // A font that fails to load falls back to the system font instead of blocking the app.
  const go = ready && (fontsLoaded || !!fontError);
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        {go && locked ? (
          <BiometricUnlock onDone={() => setLocked(false)} />
        ) : go ? (
          <AuthProvider>
            <FavoritesProvider>
              <NavProvider>
                <Shell />
              </NavProvider>
            </FavoritesProvider>
          </AuthProvider>
        ) : (
          <Splash />
        )}
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

/** Ends the saved session on this phone (and on the server, best effort) and forgets the biometric choice. */
async function dropSession() {
  await api.post('/auth/logout').catch(() => {});
  await tokens.clear();
  await setBiometricEnabled(false);
}

/** App start with Face ID / fingerprint on: the OS check opens the saved session; nothing leaves the phone. */
function BiometricUnlock({ onDone }: { onDone: () => void }) {
  const { palette } = useTheme();
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const unlock = useCallback(async () => {
    setBusy(true);
    const ok = await biometricCheck();
    setBusy(false);
    if (ok) onDone();
    else setFailed(true);
  }, [onDone]);
  useEffect(() => {
    void unlock(); // ask once on open; the button asks again
  }, [unlock]);
  return (
    <View style={{ flex: 1, backgroundColor: palette.bg, justifyContent: 'center', padding: 24, gap: 16 }}>
      <View style={{ alignItems: 'center' }}>
        <BrandMark size={64} />
      </View>
      <H1>{t('bio.prompt')}</H1>
      {failed && <ErrorText text={t('bio.failed')} />}
      <Button label={t('bio.unlock')} busy={busy} onPress={() => void unlock()} />
      <Button kind="ghost" label={t('login.pw.usePassword')} onPress={() => void dropSession().then(onDone)} />
    </View>
  );
}

/**
 * After a sign-in (password or code) in this app run, offer Face ID / fingerprint once, if the phone has it
 * enrolled and it is not on yet. "Hozir emas" is remembered; Settings → Hisob can turn it on later.
 */
function BiometricOffer() {
  const { user, signIns } = useAuth();
  const [open, setOpen] = useState(false);
  const ready = signIns > 0 && !!user && !user.password_setup_required;
  useEffect(() => {
    if (!ready) return;
    let live = true;
    void (async () => {
      if ((await biometricOffered()) || (await biometricEnabled()) || !(await biometricAvailable())) return;
      if (live) setOpen(true);
    })();
    return () => {
      live = false;
    };
  }, [ready, signIns]);
  const close = async (enable: boolean) => {
    await setBiometricOffered();
    if (enable && (await biometricCheck())) await setBiometricEnabled(true);
    setOpen(false);
  };
  return (
    <ConfirmDialog open={open} title={t('bio.offer')} onClose={() => void close(false)}>
      <P>{t('bio.offerBody')}</P>
      <Row>
        <Button label={t('bio.enable')} onPress={() => void close(true)} />
        <Button kind="ghost" label={t('bio.later')} onPress={() => void close(false)} />
      </Row>
    </ConfirmDialog>
  );
}

function Splash() {
  const { palette } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: palette.bg, justifyContent: 'center', alignItems: 'center', gap: 16 }}>
      <BrandMark size={64} />
      <Loading />
    </View>
  );
}

const DOCK_H = 64;

function Shell() {
  useLang(); // every screen re-renders in place when the language or Uzbek alphabet changes
  const { palette } = useTheme();
  const insets = useSafeAreaInsets();
  const { state, user } = useAuth();
  const nav = useNav();
  const signedIn = !!user;
  const { reset } = nav;
  useEffect(() => {
    // Signed out (or the session expired): close the account's screens. Sign-in resets in LoginScreen.
    // A pending login intent (the password setup asked for a fresh code sign-in) opens Kirish instead.
    if (!signedIn) reset(hasLoginIntent() ? 'login' : 'discover');
  }, [signedIn, reset]);
  const r = nav.route;
  let screen;
  if (state.status === 'loading') screen = <Screen><Loading /></Screen>;
  else if (r.name === 'login') screen = <LoginScreen then={r.then} mode={r.mode} notice={r.notice} />;
  else if (r.name === 'profile') screen = <ProfileScreen id={r.id} />;
  else if (r.name === 'booking') screen = <BookingDetailScreen id={r.id} />;
  else if (r.name === 'bookings') screen = <BookingsScreen />;
  else if (r.name === 'favorites') screen = <FavoritesScreen />;
  else if (r.name === 'account') screen = <AccountScreen />;
  else if (r.name === 'settings') screen = <SettingsScreen />;
  else if (r.name === 'notifications') screen = <NotificationsScreen />;
  else if (r.name === 'help') screen = <HelpScreen />;
  else screen = <DiscoverScreen />;
  // Owner, 2026-11-15: after a code sign-in an account without a username/password sets both first (Help stays open).
  if (user?.password_setup_required && r.name !== 'help') screen = <PasswordSetupScreen user={user} />;
  // The web dock (apps/web/src/ui/Layout.tsx): same items, order, icons and labels.
  const tabs: { id: Tab; label: string; icon: string }[] = user
    ? [
        { id: 'discover', label: t('nav.discover'), icon: ICONS.home },
        { id: 'favorites', label: t('nav.favorites'), icon: ICONS.heart },
        { id: 'bookings', label: t('nav.bookings'), icon: ICONS.cal },
        { id: 'account', label: t('nav.profile'), icon: ICONS.user },
      ]
    : [
        { id: 'discover', label: t('nav.discover'), icon: ICONS.home },
        { id: 'login', label: t('nav.login'), icon: ICONS.user },
      ];
  return (
    <View style={{ flex: 1, backgroundColor: palette.bg }}>
      <StatusBar style={palette.dark ? 'light' : 'dark'} />
      <Aurora />
      <Header />
      <View style={{ flex: 1, paddingBottom: DOCK_H + insets.bottom + 18 }}>
        <ConsentGate>{screen}</ConsentGate>
      </View>
      <Toast bottom={DOCK_H + insets.bottom + 18} />
      <BiometricOffer />
      <View
        role="tablist"
        aria-label={t('nav.mobile')}
        style={{
          position: 'absolute',
          left: 12,
          right: 12,
          bottom: insets.bottom + 10,
          height: DOCK_H,
          flexDirection: 'row',
          padding: 6,
          borderRadius: 999,
          backgroundColor: palette.bar,
          borderWidth: 1,
          borderColor: palette.glassLine,
          shadowColor: '#000000',
          shadowOpacity: 0.18,
          shadowRadius: 18,
          shadowOffset: { width: 0, height: 10 },
          elevation: 8,
        }}
      >
        {tabs.map((tab) => (
          <DockItem key={tab.id} label={tab.label} icon={tab.icon} on={nav.tab === tab.id} onPress={() => nav.switchTab(tab.id)} />
        ))}
      </View>
    </View>
  );
}

/** The web's toast: a short status line above the dock (favourite saved/removed), gone after 3 s. */
function Toast({ bottom }: { bottom: number }) {
  const { palette } = useTheme();
  const fav = useFavorites();
  if (!fav.notice) return null;
  return (
    <View pointerEvents="none" style={{ position: 'absolute', left: 16, right: 16, bottom, alignItems: 'center' }}>
      <View role="status" style={{ paddingVertical: 10, paddingHorizontal: 16, borderRadius: 999, backgroundColor: palette.primary, borderWidth: 1, borderColor: palette.accent }}>
        <Text style={{ color: palette.onPrimary, fontFamily: FONT.medium, fontSize: 15 }}>{fav.notice}</Text>
      </View>
    </View>
  );
}

function DockItem({ label, icon, on, onPress }: { label: string; icon: string; on: boolean; onPress: () => void }) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  return (
    <Pressable
      role="tab"
      aria-selected={on}
      aria-label={label}
      onPress={onPress}
      style={({ pressed }) => [
        { flex: 1, minHeight: TOUCH, borderRadius: 999, alignItems: 'center', justifyContent: 'center', gap: 2 },
        on && { backgroundColor: palette.pill },
        pressed && !reduced && { transform: [{ scale: 0.92 }] },
      ]}
    >
      <Icon d={icon} color={on ? palette.fg : palette.muted} />
      <Text numberOfLines={1} style={{ color: on ? palette.fg : palette.muted, fontSize: 12, fontFamily: on ? FONT.bold : FONT.medium }}>
        {label}
      </Text>
    </Pressable>
  );
}

/**
 * The web's glass top bar. Owner, 2026-11-15: logo only — SOS lives on Help and on confirmed/active bookings
 * (CLAUDE.md S25), the language is chosen on Kirish and in Settings. No scroll-linked styles: the bar sits outside
 * the ScrollView, so it cannot shift while the page scrolls.
 */
function Header() {
  const { palette } = useTheme();
  const insets = useSafeAreaInsets();
  const nav = useNav();
  return (
    <View style={{ paddingTop: insets.top + 8, paddingHorizontal: 12, paddingBottom: 4 }}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 8,
          minHeight: 52,
          paddingLeft: 14,
          paddingRight: 6,
          borderRadius: 999,
          backgroundColor: palette.bar,
          borderWidth: 1,
          borderColor: palette.glassLine,
        }}
      >
        <Pressable
          role="link"
          aria-label={t('nav.brandHome')}
          onPress={() => nav.switchTab('discover')}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: TOUCH, flex: 1 }}
        >
          <BrandMark size={28} />
          <Text style={{ color: palette.fg, fontSize: 22, fontFamily: FONT.display }}>Yondo</Text>
        </Pressable>
      </View>
    </View>
  );
}

/** Signed-in users accept the current Terms/Privacy versions before using the app (as on the web). */
function ConsentGate({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const res = useResource(
    () => (user ? api.get<Schemas['ConsentState']>('/account/consents') : Promise.resolve(null)),
    [user?.id],
  );
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const required = res.data?.required ?? [];
  if (!user || required.length === 0) return <>{children}</>;
  const accept = async () => {
    if (!agree) return setErr(t('legal.agreeRequired'));
    setBusy(true);
    setErr(undefined);
    try {
      await acceptLegal(required.map((r) => r.document as LegalDoc));
      res.reload();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Screen>
      <H1>{t('legal.gate.title')}</H1>
      <P muted>{t('legal.gate.body')}</P>
      <ConsentCheck checked={agree} onChange={setAgree} />
      {err && <ErrorText text={err} />}
      <Row>
        <Button label={t('legal.gate.accept')} busy={busy} onPress={() => void accept()} />
        <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
      </Row>
    </Screen>
  );
}
