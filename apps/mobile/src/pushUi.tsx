import { useEffect, useState } from 'react';
import { Platform, Switch, Text, View } from 'react-native';
import { errorText } from './api';
import { useAuth } from './auth';
import { useNav } from './nav';
import {
  disablePush,
  enablePush,
  markOffered,
  openSystemSettings,
  pushState,
  refreshToken,
  shouldOffer,
  type PushState,
} from './push';
import { t, type Key } from './shared';
import { FONT, useTheme } from './theme';
import { Button, ErrorText, P, Row, Sheet } from './ui';

const HINT: Record<PushState, Key> = {
  on: 'push.mobile.on',
  off: 'push.mobile.off',
  denied: 'push.mobile.denied',
  unsupported: 'push.mobile.unsupported',
  unavailable: 'push.state.unavailable',
};

/** Settings → "Push bildirishnomalar" switch. */
export function PushSwitch() {
  const { palette } = useTheme();
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    pushState().then((s) => live && setState(s), () => live && setState('unavailable'));
    return () => {
      live = false;
    };
  }, []);
  const on = state === 'on';
  const locked = busy || state === null || state === 'unsupported' || state === 'unavailable';
  const flip = async () => {
    setBusy(true);
    setError('');
    try {
      setState(on ? await disablePush() : await enablePush());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <View style={{ gap: 8, paddingHorizontal: 4, paddingVertical: 8 }}>
      <Row style={{ justifyContent: 'space-between', gap: 12 }}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 16 }}>{t('push.title')}</Text>
          <P muted>{state ? t(HINT[state]) : t('common.loading')}</P>
        </View>
        <Switch
          value={on}
          disabled={locked}
          onValueChange={() => void flip()}
          accessibilityLabel={t('push.title')}
          trackColor={{ false: palette.line, true: palette.primary }}
        />
      </Row>
      {state === 'denied' && <Button small kind="ghost" label={t('push.mobile.openSettings')} onPress={() => void openSystemSettings()} />}
      {!!error && <ErrorText text={error} />}
    </View>
  );
}

/** Shown ONCE after a sign-in where push can work: a short reason + "Yoqish" / "Keyinroq". */
export function PushOffer() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!user || user.password_setup_required) return;
    let live = true;
    shouldOffer().then((yes) => live && yes && setOpen(true), () => undefined);
    return () => {
      live = false;
    };
  }, [user]);
  const close = () => {
    void markOffered();
    setOpen(false);
  };
  const yes = async () => {
    setBusy(true);
    setError('');
    try {
      const next = await enablePush();
      setState(next);
      if (next === 'on') setOpen(false);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Sheet open={open} title={t('push.offer.title')} onClose={close}>
      <P>{t('push.offer.body')}</P>
      {state === 'denied' && (
        <>
          <P muted>{t('push.mobile.denied')}</P>
          <Button kind="ghost" label={t('push.mobile.openSettings')} onPress={() => void openSystemSettings()} />
        </>
      )}
      {state === 'unavailable' && <P muted>{t('push.state.unavailable')}</P>}
      {!!error && <ErrorText text={error} />}
      <Row style={{ gap: 12, flexWrap: 'wrap' }}>
        {state !== 'denied' && state !== 'unavailable' && <Button label={t('push.offer.yes')} busy={busy} onPress={() => void yes()} />}
        <Button kind="ghost" label={t('push.offer.later')} onPress={close} />
      </Row>
    </Sheet>
  );
}

type Response = { notification: { request: { content: { data?: Record<string, unknown> }; trigger?: unknown } } };

/** The in-app path a push carries (FCM data), from either place Android puts it. */
export function pushPath(response: Response | null | undefined): string | null {
  if (!response) return null;
  const req = response.notification.request;
  const trigger = req.trigger as { remoteMessage?: { data?: Record<string, unknown> } } | undefined;
  const url = req.content.data?.url ?? trigger?.remoteMessage?.data?.url;
  return typeof url === 'string' ? url : null;
}

/** Native only: a tap on a notification opens the booking (or the notifications list); token refresh re-registers. */
export function usePushRouting() {
  const { user } = useAuth();
  const nav = useNav();
  const signedIn = !!user;
  const { push } = nav;
  useEffect(() => {
    if (Platform.OS !== 'android' || !signedIn) return;
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const N = require('expo-notifications') as typeof import('expo-notifications');
    N.setNotificationHandler({
      handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
    });
    const open = (path: string | null) => {
      const m = path?.match(/^\/bookings\/([0-9a-f-]{36})$/);
      push(m ? { name: 'booking', id: m[1] } : { name: 'notifications' });
    };
    const sub = N.addNotificationResponseReceivedListener((r) => open(pushPath(r as Response)));
    const tok = N.addPushTokenListener((token) => void refreshToken(String(token.data)));
    const last = N.getLastNotificationResponse(); // the tap that started the app
    if (last) {
      open(pushPath(last as Response));
      N.clearLastNotificationResponse();
    }
    return () => {
      sub.remove();
      tok.remove();
    };
  }, [signedIn, push]);
}
