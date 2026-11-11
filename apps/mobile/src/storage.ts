import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * Tokens: the device keychain/keystore on phones; sessionStorage on the web build (cleared with the tab).
 * Preferences (language, theme): the same store on phones, localStorage on the web build.
 * Every access is guarded: a failure falls back to memory for the running app only.
 */
const memory = new Map<string, string>();
type Kind = 'secret' | 'pref';

function webStore(kind: Kind): Storage | null {
  try {
    return kind === 'secret' ? globalThis.sessionStorage : globalThis.localStorage;
  } catch {
    return null;
  }
}

export async function getItem(key: string, kind: Kind): Promise<string | null> {
  try {
    if (Platform.OS === 'web') return webStore(kind)?.getItem(key) ?? memory.get(key) ?? null;
    return (await SecureStore.getItemAsync(key)) ?? memory.get(key) ?? null;
  } catch {
    return memory.get(key) ?? null;
  }
}

export async function setItem(key: string, value: string | null, kind: Kind): Promise<void> {
  if (value === null) memory.delete(key);
  else memory.set(key, value);
  try {
    if (Platform.OS === 'web') {
      const store = webStore(kind);
      if (value === null) store?.removeItem(key);
      else store?.setItem(key, value);
    } else if (value === null) await SecureStore.deleteItemAsync(key);
    else await SecureStore.setItemAsync(key, value);
  } catch {
    /* memory fallback above */
  }
}
