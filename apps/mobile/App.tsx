import { Manrope_400Regular } from '@expo-google-fonts/manrope/400Regular';
import { Manrope_600SemiBold } from '@expo-google-fonts/manrope/600SemiBold';
import { Manrope_700Bold } from '@expo-google-fonts/manrope/700Bold';
import { SpaceGrotesk_600SemiBold } from '@expo-google-fonts/space-grotesk/600SemiBold';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState, type ReactNode } from 'react';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, errorText, tokens, type Schemas } from './src/api';
import { AuthProvider, acceptLegal, useAuth } from './src/auth';
import { Aurora, BrandMark, ICONS } from './src/brand';
import { FavoritesProvider, useFavorites } from './src/favorites';
import { restoreLocale } from './src/locale';
import { NavProvider, useNav, type Tab } from './src/nav';
import { ShockwaveDock } from './src/dock';
import { PushOffer, usePushRouting } from './src/pushUi';
import { AccountScreen } from './src/screens/Account';
import { BookingDetailScreen } from './src/screens/BookingDetail';
import { BookingsScreen } from './src/screens/Bookings';
import { DiscoverScreen } from './src/screens/Discover';
import { FavoritesScreen } from './src/screens/Favorites';
import { HelpScreen } from './src/screens/Help';
import { ConsentCheck, LoginScreen } from './src/screens/Login';
import { AgeRestrictedScreen, DobStepScreen, PasswordSetupScreen } from './src/screens/Password';
import { NotificationsScreen } from './src/screens/Notifications';
import { ProfileScreen } from './src/screens/Profile';
import { SettingsScreen } from './src/screens/Settings';
import { t, useLang, type LegalDoc } from './src/shared';
import { FONT, ThemeProvider, useTheme } from './src/theme';
import { Button, ErrorText, H1, Loading, P, Row, Screen, TOUCH } from './src/ui';
import { useResource } from './src/useResource';
import { useUnreadNotifications } from './src/useUnreadNotifications';
import { hasLoginIntent } from './src/loginIntent';
import { setItem } from './src/storage';

/** Tokens, the saved language and the brand fonts are ready before the first render, so nothing flashes. */
export default function App() {
  const [ready, setReady] = useState(false);
  const [fontsLoaded, fontError] = useFonts({ SpaceGrotesk_600SemiBold, Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold });
  useEffect(() => {
    // Owner, 2026-11-16: no in-app Face ID lock. A build that had it may have left its flags: forget them.
    void Promise.all([tokens.load(), restoreLocale(), forgetBiometricFlags()]).finally(() => setReady(true));
  }, []);
  // A font that fails to load falls back to the system font instead of blocking the app.
  const go = ready && (fontsLoaded || !!fontError);
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        {go ? (
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

/** Flags of the removed in-app biometric lock (S68, removed 2026-11-16): cleared so nothing can lock a session. */
async function forgetBiometricFlags() {
  await Promise.all(['yondo.biometric', 'yondo.biometric.offered'].map((key) => setItem(key, null, 'pref')));
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
  usePushRouting();
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
  // 18+ (owner, 2026-11-19), as on the web: a restricted account sees why (Help stays open); an older account
  // without a date of birth gives it once.
  else if (user?.age_restricted && r.name !== 'help') screen = <AgeRestrictedScreen onHelp={() => nav.push({ name: 'help' })} />;
  else if (user && !user.date_of_birth && r.name !== 'help') screen = <DobStepScreen />;
  // The web dock (apps/web/src/ui/Layout.tsx): same items, order, icons and labels.
  const unreadCount = useUnreadNotifications();
  const tabs: { id: Tab; label: string; icon: string; dot?: boolean }[] = user
    ? [
        { id: 'discover', label: t('nav.discover'), icon: ICONS.home },
        { id: 'favorites', label: t('nav.favorites'), icon: ICONS.heart },
        { id: 'bookings', label: t('nav.bookings'), icon: ICONS.cal },
        { id: 'account', label: t('nav.profile'), icon: ICONS.user, dot: unreadCount > 0 },
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
      {signedIn && <PushOffer />}
      <ShockwaveDock tabs={tabs} active={nav.tab} onSelect={(id) => nav.switchTab(id)} bottom={insets.bottom + 10} height={DOCK_H} />
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
