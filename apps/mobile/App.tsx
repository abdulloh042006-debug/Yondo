import { StatusBar } from 'expo-status-bar';
import { useEffect, useState, type ReactNode } from 'react';
import { Pressable, SafeAreaView, Text, View } from 'react-native';

import { api, errorText, tokens, type Schemas } from './src/api';
import { AuthProvider, acceptLegal, useAuth } from './src/auth';
import { restoreLocale } from './src/locale';
import { NavProvider, useNav, type Tab } from './src/nav';
import { BookingDetailScreen } from './src/screens/BookingDetail';
import { BookingsScreen } from './src/screens/Bookings';
import { DiscoverScreen } from './src/screens/Discover';
import { ConsentCheck, LoginScreen } from './src/screens/Login';
import { ProfileScreen } from './src/screens/Profile';
import { SettingsScreen } from './src/screens/Settings';
import { t, useLang, type LegalDoc } from './src/shared';
import { ThemeProvider, useTheme } from './src/theme';
import { Button, ErrorText, H1, Loading, P, Row, Screen } from './src/ui';
import { useResource } from './src/useResource';

/** Tokens and the saved language are read before the first render, so nothing flashes in the wrong state. */
export default function App() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    void Promise.all([tokens.load(), restoreLocale()]).finally(() => setReady(true));
  }, []);
  return (
    <ThemeProvider>
      {ready ? (
        <AuthProvider>
          <NavProvider>
            <Shell />
          </NavProvider>
        </AuthProvider>
      ) : (
        <Splash />
      )}
    </ThemeProvider>
  );
}

function Splash() {
  const { palette } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: palette.bg, justifyContent: 'center' }}>
      <Loading />
    </View>
  );
}

function Shell() {
  useLang(); // every screen re-renders in place when the language or Uzbek alphabet changes
  const { palette } = useTheme();
  const { state, user } = useAuth();
  const nav = useNav();
  const signedIn = !!user;
  const { reset } = nav;
  useEffect(() => {
    // Signed out (or the session expired): close the account's screens. Sign-in resets in LoginScreen.
    if (!signedIn) reset();
  }, [signedIn, reset]);
  const r = nav.route;
  let screen;
  if (state.status === 'loading') screen = <Screen><Loading /></Screen>;
  else if (r.name === 'login') screen = <LoginScreen then={r.then} />;
  else if (r.name === 'profile') screen = <ProfileScreen id={r.id} />;
  else if (r.name === 'booking') screen = <BookingDetailScreen id={r.id} />;
  else if (r.name === 'bookings') screen = <BookingsScreen />;
  else if (r.name === 'settings') screen = <SettingsScreen />;
  else screen = <DiscoverScreen />;
  const tabs: { id: Tab; label: string }[] = [
    { id: 'discover', label: t('nav.discover') },
    { id: 'bookings', label: t('nav.bookings') },
    { id: 'settings', label: t('settings.title') },
  ];
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.bg }}>
      <StatusBar style={palette.dark ? 'light' : 'dark'} />
      <View style={{ flex: 1 }}>
        <ConsentGate>{screen}</ConsentGate>
      </View>
      <View role="tablist" style={{ flexDirection: 'row', borderTopWidth: 1, borderTopColor: palette.line, backgroundColor: palette.bg }}>
        {tabs.map((tab) => {
          const on = nav.tab === tab.id;
          return (
            <Pressable
              key={tab.id}
              role="tab"
              aria-selected={on}
              onPress={() => nav.switchTab(tab.id)}
              style={{ flex: 1, minHeight: 56, alignItems: 'center', justifyContent: 'center', gap: 4 }}
            >
              <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: on ? palette.accent : 'transparent' }} />
              <Text style={{ color: palette.fg, fontWeight: on ? '700' : '500' }}>{tab.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
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
