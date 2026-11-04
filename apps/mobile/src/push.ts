// Registers the native FCM/APNs device token with the API (Phase 18 push delivery).
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { api } from './api';

export async function registerForPush(): Promise<void> {
  if (Platform.OS === 'web' || !Device.isDevice) return;
  try {
    const current = await Notifications.getPermissionsAsync();
    const granted = current.granted || (await Notifications.requestPermissionsAsync()).granted;
    if (!granted) return;
    // The backend sends through FCM HTTP v1, so the native device token is required
    // (Android builds need google-services.json from the Firebase project).
    const token = await Notifications.getDevicePushTokenAsync();
    await api.put('/notifications/devices', {
      token: String(token.data),
      platform: Platform.OS === 'ios' ? 'ios' : 'android',
    });
  } catch {
    // Push is optional; in-app notifications and realtime events still work.
  }
}
