/**
 * Android push (FCM) for the Expo app (docs/push-notifications.md). Permission is asked only after the user taps
 * "Yoqish" (the one-time card after sign-in, or the Settings switch). Flow: Android 13+ POST_NOTIFICATIONS prompt →
 * getDevicePushTokenAsync (the raw FCM token) → PUT /push/devices. Off / sign-out = DELETE /push/devices/{id}.
 *
 * A build without google-services.json (no Firebase project yet) cannot get a token: the switch then says push is
 * not set up, and nothing else breaks. iOS push is out of scope (paid Apple account + iOS build).
 */
import { Linking, Platform } from 'react-native';
import { api, ApiError } from './api';
import { getItem, setItem } from './storage';

export type PushState = 'unsupported' | 'unavailable' | 'denied' | 'off' | 'on';
export const CHANNEL_ID = 'yondo';
const DEVICE_KEY = 'yondo.push.device';
const OFFERED_KEY = 'yondo.push.offered';

type Perm = { status: 'granted' | 'denied' | 'undetermined'; canAskAgain?: boolean };
/** The part of expo-notifications this module uses; the web smoke test injects a fake with the same shape. */
export interface NativePush {
  getPermissionsAsync(): Promise<Perm>;
  requestPermissionsAsync(): Promise<Perm>;
  getDevicePushTokenAsync(): Promise<{ type: string; data: string }>;
  setNotificationChannelAsync(id: string, channel: Record<string, unknown>): Promise<unknown>;
}
type PushConfig = { web: { enabled: boolean }; android: { enabled: boolean } };

export function native(): NativePush | null {
  const fake = (globalThis as { __YONDO_PUSH_FAKE__?: NativePush }).__YONDO_PUSH_FAKE__;
  if (fake) return fake;
  if (Platform.OS !== 'android') return null;
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require('expo-notifications') as NativePush;
}

async function serverAndroidEnabled(): Promise<boolean> {
  try {
    return (await api.get<PushConfig>('/push/config', { anonymous: true })).android.enabled;
  } catch {
    return false;
  }
}

export async function pushState(): Promise<PushState> {
  const n = native();
  if (!n) return 'unsupported';
  if (!(await serverAndroidEnabled())) return 'unavailable';
  const perm = await n.getPermissionsAsync();
  if (perm.status === 'denied' && perm.canAskAgain === false) return 'denied';
  return perm.status === 'granted' && (await getItem(DEVICE_KEY, 'pref')) ? 'on' : 'off';
}

/** Android 8+ needs a channel before the first notification; created before the permission prompt (Android 13+). */
async function ensureChannel(n: NativePush) {
  await n.setNotificationChannelAsync(CHANNEL_ID, {
    name: 'Yondo',
    importance: 4, // AndroidImportance.HIGH: heads-up banner
    sound: 'yondo_notify.mp3', // variant A "tomchi-rin" (PR #44), bundled by the expo-notifications plugin
    lightColor: '#E8501A',
    vibrationPattern: [0, 200, 120, 200],
  });
}

/** "Yoqish": MUST follow a tap. */
export async function enablePush(): Promise<PushState> {
  await setItem(OFFERED_KEY, '1', 'pref');
  const n = native();
  if (!n) return 'unsupported';
  if (!(await serverAndroidEnabled())) return 'unavailable';
  await ensureChannel(n);
  let perm = await n.getPermissionsAsync();
  if (perm.status !== 'granted') perm = await n.requestPermissionsAsync();
  if (perm.status !== 'granted') return 'denied';
  let token: string;
  try {
    token = (await n.getDevicePushTokenAsync()).data;
  } catch {
    return 'unavailable'; // e.g. an APK built without google-services.json
  }
  const device = await api.put<{ id: string }>('/push/devices', { platform: 'android', token });
  await setItem(DEVICE_KEY, device.id, 'pref');
  return 'on';
}

/** A refreshed FCM token replaces the old one on the server (only while push is on). */
export async function refreshToken(token: string): Promise<void> {
  if (!(await getItem(DEVICE_KEY, 'pref'))) return;
  try {
    const device = await api.put<{ id: string }>('/push/devices', { platform: 'android', token });
    await setItem(DEVICE_KEY, device.id, 'pref');
  } catch {
    /* retried at the next token change or by turning the switch off/on */
  }
}

export async function disablePush(): Promise<PushState> {
  const id = await getItem(DEVICE_KEY, 'pref');
  await setItem(DEVICE_KEY, null, 'pref');
  if (id) {
    try {
      await api.del(`/push/devices/${id}`);
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 404) throw e;
    }
  }
  return native() ? 'off' : 'unsupported';
}

/** Sign-out: this phone stops receiving the account's pushes. Best effort, never blocks sign-out. */
export async function forgetPushDevice(): Promise<void> {
  try {
    if (await getItem(DEVICE_KEY, 'pref')) await disablePush();
  } catch {
    /* the server prunes the token once FCM reports it gone */
  }
}

/** The one-time card after sign-in: only where push can work and was never offered. */
export async function shouldOffer(): Promise<boolean> {
  if (await getItem(OFFERED_KEY, 'pref')) return false;
  return (await pushState()) === 'off';
}
export const markOffered = () => setItem(OFFERED_KEY, '1', 'pref');

export const openSystemSettings = () => Linking.openSettings();
