import { StatusBar } from 'expo-status-bar';
import type { ComponentType } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { AuthProvider, useAuth } from './src/auth';
import { NavProvider, useNav } from './src/nav';
import { LoginScreen, ProfileSetupScreen } from './src/screens/Auth';
import { BookingCreateScreen, BookingDetailScreen, BookingsScreen, DisputeScreen, ReviewScreen } from './src/screens/Booking';
import { ChatScreen, ConversationsScreen } from './src/screens/Chat';
import {
  AvailabilityScreen, CompanionDashboardScreen, CompanionEditScreen, EarningsScreen, PhotosScreen, ServicesScreen,
} from './src/screens/Companion';
import { CompanionProfileScreen, HomeScreen, SearchScreen } from './src/screens/Discover';
import { CartScreen, GiftCheckoutScreen, GiftOrdersScreen, GiftsScreen, ProductScreen } from './src/screens/Gifts';
import {
  EditProfileScreen, FavoritesScreen, NotificationsScreen, ProfileScreen, VerificationScreen,
} from './src/screens/Profile';
import { ReportScreen, SafetyScreen } from './src/screens/Safety';
import { colors, Loading } from './src/ui';

const SCREENS: Record<string, ComponentType> = {
  home: HomeScreen,
  search: SearchScreen,
  companion: CompanionProfileScreen,
  bookingCreate: BookingCreateScreen,
  bookings: BookingsScreen,
  booking: BookingDetailScreen,
  review: ReviewScreen,
  dispute: DisputeScreen,
  chats: ConversationsScreen,
  chat: ChatScreen,
  gifts: GiftsScreen,
  product: ProductScreen,
  cart: CartScreen,
  giftCheckout: GiftCheckoutScreen,
  giftOrders: GiftOrdersScreen,
  profile: ProfileScreen,
  editProfile: EditProfileScreen,
  verification: VerificationScreen,
  notifications: NotificationsScreen,
  favorites: FavoritesScreen,
  safety: SafetyScreen,
  report: ReportScreen,
  dashboard: CompanionDashboardScreen,
  companionEdit: CompanionEditScreen,
  services: ServicesScreen,
  availability: AvailabilityScreen,
  photos: PhotosScreen,
  earnings: EarningsScreen,
};

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="dark" />
      <Root />
    </AuthProvider>
  );
}

function Root() {
  const { me, loading } = useAuth();
  if (loading) return <View style={styles.center}><Loading show /></View>;
  if (!me) return <NavProvider initialTab="login"><LoginScreen /></NavProvider>;
  if (!me.profile_complete || me.roles.length === 0 || me.account_status === 'verification_pending') {
    return <NavProvider initialTab="setup"><ProfileSetupScreen /></NavProvider>;
  }
  return (
    <NavProvider initialTab="home">
      <Shell />
    </NavProvider>
  );
}

function Shell() {
  const { me } = useAuth();
  const nav = useNav();
  const Screen = SCREENS[nav.route.name] ?? HomeScreen;
  const tabs: [string, string, string][] = [
    ['home', 'Asosiy', '⌂'],
    ['bookings', 'Bronlar', '▤'],
    ['chats', 'Chat', '✉'],
    ['gifts', "Sovg'alar", '✿'],
    ...(me?.roles.includes('companion') ? [['dashboard', 'Companion', '★'] as [string, string, string]] : []),
    ['profile', 'Profil', '☺'],
  ];
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ flex: 1 }} key={nav.route.key}>
        <Screen />
      </View>
      <View style={styles.tabs}>
        {tabs.map(([key, label, icon]) => {
          const active = nav.tab === key;
          return (
            <Pressable key={key} style={styles.tab} onPress={() => nav.setTab(key)} accessibilityRole="tab" accessibilityState={{ selected: active }}>
              <Text style={[styles.tabIcon, active && { color: colors.primary }]}>{icon}</Text>
              <Text style={[styles.tabLabel, active && { color: colors.primary, fontWeight: '700' }]}>{label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  tabs: { flexDirection: 'row', backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.border, paddingBottom: 18, paddingTop: 6 },
  tab: { flex: 1, alignItems: 'center', gap: 2 },
  tabIcon: { fontSize: 18, color: colors.muted },
  tabLabel: { fontSize: 11, color: colors.muted },
});
