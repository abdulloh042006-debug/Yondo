import * as LocalAuthentication from 'expo-local-authentication';
import { Platform } from 'react-native';

import { t } from './shared';
import { getItem, setItem } from './storage';

/**
 * Face ID / fingerprint sign-in (owner, 2026-11-15). Only on the phone: the face or fingerprint check is done
 * by the operating system (expo-local-authentication) and nothing about it ever leaves the device; the server
 * is not involved. When it is on, a saved session (tokens in SecureStore, the device keystore) is opened only
 * after a successful check on app start. Off by default; offered once after a sign-in; opt-out in Settings.
 *
 * Test seam: the web build has no biometrics, so `globalThis.__YONDO_BIO_MOCK__` (set by e2e/smoke.mjs) can
 * stand in for the OS check there. It is read only when Platform.OS === 'web'; phones always ask the OS.
 */
const ENABLED = 'yondo.biometric';
const OFFERED = 'yondo.biometric.offered';

type Mock = { available: boolean; result: boolean; calls?: number };
const mock = (): Mock | null =>
  Platform.OS === 'web' ? ((globalThis as { __YONDO_BIO_MOCK__?: Mock }).__YONDO_BIO_MOCK__ ?? null) : null;

/** True only when the device has the hardware and at least one face or fingerprint enrolled. */
export async function biometricAvailable(): Promise<boolean> {
  const m = mock();
  if (m) return m.available;
  if (Platform.OS === 'web') return false;
  try {
    return (await LocalAuthentication.hasHardwareAsync()) && (await LocalAuthentication.isEnrolledAsync());
  } catch {
    return false;
  }
}

/** Ask the OS for Face ID / fingerprint (the device passcode is the OS's own fallback). */
export async function biometricCheck(): Promise<boolean> {
  const m = mock();
  if (m) {
    m.calls = (m.calls ?? 0) + 1;
    return m.result;
  }
  try {
    const r = await LocalAuthentication.authenticateAsync({ promptMessage: t('bio.prompt'), cancelLabel: t('common.cancel') });
    return r.success;
  } catch {
    return false;
  }
}

export const biometricEnabled = async () => (await getItem(ENABLED, 'pref')) === '1';
export const setBiometricEnabled = (on: boolean) => setItem(ENABLED, on ? '1' : null, 'pref');
export const biometricOffered = async () => (await getItem(OFFERED, 'pref')) === '1';
export const setBiometricOffered = () => setItem(OFFERED, '1', 'pref');
