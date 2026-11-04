import { Alert, Platform } from 'react-native';

/** Cross-platform confirmation dialog (Alert on native, window.confirm on web). */
export function confirm(title: string, message: string): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(globalThis.confirm?.(`${title}\n\n${message}`) ?? false);
  }
  return new Promise((resolve) => {
    Alert.alert(title, message, [
      { text: 'Yo‘q', style: 'cancel', onPress: () => resolve(false) },
      { text: 'Ha', style: 'destructive', onPress: () => resolve(true) },
    ]);
  });
}

export function newIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
