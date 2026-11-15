import { useState } from 'react';
import { Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useNav } from '../nav';
import { formatInstant, hasKey, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, ErrorText, H1, Loading, Row, Screen, Tag } from '../ui';
import { useResource } from '../useResource';

type Notice = Schemas['NotificationRead'];

const kindLabel = (kind: string) => {
  const key = `notif.kind.${kind}`;
  return hasKey(key) ? t(key as Parameters<typeof t>[0]) : kind;
};

/** The web's /notifications on the same API: list, "new" tag, open the booking (marks read), mark all read. */
export function NotificationsScreen() {
  const nav = useNav();
  const { palette } = useTheme();
  const res = useResource(() => api.get<Notice[]>('/notifications', { query: { limit: 50 } }), []);
  const [err, setErr] = useState<string>();
  const unread = (res.data ?? []).filter((n) => !n.read_at).length;
  const readAll = async () => {
    setErr(undefined);
    try {
      await api.post('/notifications/read-all');
      res.reload();
    } catch (e) {
      setErr(errorText(e));
    }
  };
  const open = (n: Notice) => {
    if (!n.read_at) void api.post(`/notifications/${n.id}/read`).catch(() => {});
    if (n.booking_id) nav.push({ name: 'booking', id: n.booking_id });
  };
  return (
    <Screen>
      {nav.canGoBack && (
        <Row>
          <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
        </Row>
      )}
      <H1>{t('nav.notifications')}</H1>
      {unread > 0 && (
        <Row>
          <Button kind="ghost" small label={t('notif.readAll')} onPress={() => void readAll()} />
        </Row>
      )}
      {err && <ErrorText text={err} />}
      {res.loading && !res.data ? (
        <Loading />
      ) : res.error ? (
        <>
          <ErrorText text={errorText(res.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={res.reload} />
        </>
      ) : !res.data?.length ? (
        <Banner text={t('notif.empty')} />
      ) : (
        <Card style={{ gap: 0, paddingVertical: 4 }}>
          {res.data.map((n, i) => (
            <View
              key={n.id}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12, paddingHorizontal: 4, borderTopWidth: i ? 1 : 0, borderTopColor: palette.glassLine }}
            >
              <View style={{ flex: 1, gap: 4 }}>
                <Row>
                  <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 16 }}>{kindLabel(n.kind)}</Text>
                  {!n.read_at && <Tag text={t('notif.new')} attention />}
                </Row>
                <Text style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 14 }}>{formatInstant(n.created_at)}</Text>
              </View>
              {n.booking_id && <Button small kind="ghost" label={t('notif.open')} onPress={() => open(n)} />}
            </View>
          ))}
        </Card>
      )}
    </Screen>
  );
}
