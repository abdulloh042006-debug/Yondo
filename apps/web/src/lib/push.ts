/**
 * Web Push for the site (docs/push-notifications.md). Permission is asked ONLY from the Settings switch (a user
 * gesture), never on page load. Flow: Notification.requestPermission → service worker → pushManager.subscribe with
 * the server's VAPID key → PUT /push/devices. Off = unsubscribe + DELETE /push/devices/{id}.
 */
import { api, ApiError } from '../api/client';

export type PushState = 'unsupported' | 'ios-install' | 'denied' | 'off' | 'on' | 'unavailable';

const DEVICE_KEY = 'yondo.push.device';
const SW_URL = '/sw.js';

type PushConfig = { web: { enabled: boolean; vapid_public_key: string | null }; android: { enabled: boolean } };

function storedDevice(): string | null {
  try {
    return localStorage.getItem(DEVICE_KEY);
  } catch {
    return null;
  }
}
function storeDevice(id: string | null) {
  try {
    if (id) localStorage.setItem(DEVICE_KEY, id);
    else localStorage.removeItem(DEVICE_KEY);
  } catch {
    /* storage unavailable: the server copy is pruned when the browser drops the subscription */
  }
}

/** iPhone/iPad Safari exposes Web Push only to a site added to the Home Screen (iOS 16.4+). */
export function isIosBrowserTab(): boolean {
  const nav = navigator as Navigator & { standalone?: boolean };
  const ios = /iPhone|iPad|iPod/.test(nav.userAgent) || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
  if (!ios) return false;
  const standalone = nav.standalone === true || window.matchMedia?.('(display-mode: standalone)').matches === true;
  return !standalone;
}

export function supported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;
}

async function registration(): Promise<ServiceWorkerRegistration | undefined> {
  return navigator.serviceWorker.getRegistration(SW_URL);
}

/** The state shown in Settings, without asking for anything. */
export async function pushState(): Promise<PushState> {
  if (isIosBrowserTab()) return 'ios-install';
  if (!supported()) return 'unsupported';
  if (Notification.permission === 'denied') return 'denied';
  if (Notification.permission !== 'granted' || !storedDevice()) return 'off';
  const sub = await (await registration())?.pushManager.getSubscription();
  return sub ? 'on' : 'off';
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const b64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (base64url.length % 4)) % 4);
  const raw = atob(b64);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

/** Turn push on. MUST be called from a click handler: the browser only shows its prompt after a gesture. */
export async function enablePush(): Promise<PushState> {
  if (isIosBrowserTab()) return 'ios-install';
  if (!supported()) return 'unsupported';
  const permission = await Notification.requestPermission();
  if (permission === 'denied') return 'denied';
  if (permission !== 'granted') return 'off';
  const config = await api.get<PushConfig>('/push/config');
  if (!config.web.enabled || !config.web.vapid_public_key) return 'unavailable';
  await navigator.serviceWorker.register(SW_URL);
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(config.web.vapid_public_key) });
  const json = sub.toJSON();
  const device = await api.put<{ id: string }>('/push/devices', {
    platform: 'web',
    endpoint: json.endpoint ?? sub.endpoint,
    p256dh: json.keys?.p256dh,
    auth: json.keys?.auth,
  });
  storeDevice(device.id);
  return 'on';
}

/** Turn push off on this browser: unsubscribe and remove the device on the server (also used at sign-out). */
export async function disablePush(): Promise<PushState> {
  const id = storedDevice();
  storeDevice(null);
  if (supported()) {
    try {
      const sub = await (await registration())?.pushManager.getSubscription();
      await sub?.unsubscribe();
    } catch {
      /* the browser copy may already be gone */
    }
  }
  if (id) {
    try {
      await api.del(`/push/devices/${id}`);
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 404) throw e;
    }
  }
  if (!supported()) return isIosBrowserTab() ? 'ios-install' : 'unsupported';
  return Notification.permission === 'denied' ? 'denied' : 'off';
}

/** Sign-out: best effort, never blocks the sign-out itself. */
export async function forgetPushDevice(): Promise<void> {
  if (!storedDevice()) return;
  try {
    await disablePush();
  } catch {
    /* the server prunes the subscription once the push service reports it gone */
  }
}
