import { Pressable, Text } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useAuth } from '../auth';
import { useNav } from '../nav';
import { BOOKING_STATUS, formatInstant, formatMoney, serviceLabel, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, ErrorText, H1, Loading, P, Row, Screen, Tag } from '../ui';
import { useResource } from '../useResource';

export type Booking = Schemas['BookingResponse'];
export const ATTENTION = new Set(['pending', 'cancelled', 'no-show', 'disputed']);

export function BookingsScreen() {
  const nav = useNav();
  const { user } = useAuth();
  const { palette } = useTheme();
  const res = useResource(
    () => (user ? api.get<Booking[]>('/bookings', { query: { limit: 50 } }) : Promise.resolve([] as Booking[])),
    [user?.id],
  );
  if (!user) {
    return (
      <Screen>
        <H1>{t('bookings.title')}</H1>
        <P muted>{t('mobile.loginForBookings')}</P>
        <Button label={t('nav.login')} onPress={() => nav.push({ name: 'login' })} />
      </Screen>
    );
  }
  return (
    <Screen>
      <H1>{t('bookings.title')}</H1>
      <Banner text={t('bookings.banner')} />
      <Row>
        <Button kind="ghost" small label={t('common.retry')} onPress={res.reload} />
      </Row>
      {res.loading && !res.data && <Loading />}
      {!!res.error && <ErrorText text={errorText(res.error)} />}
      {res.data?.length === 0 && (
        <>
          <P>{t('bookings.empty')}</P>
          <P muted>{t('bookings.emptyBody')}</P>
          <Button label={t('bookings.find')} onPress={() => nav.switchTab('discover')} />
        </>
      )}
      {res.data?.map((b) => (
        <Pressable
          key={b.id}
          role="button"
          aria-label={`${t('bd.open')}: ${serviceLabel(b.service_code)}, ${formatInstant(b.starts_at)}, ${BOOKING_STATUS[b.status]?.label ?? b.status}`}
          onPress={() => nav.push({ name: 'booking', id: b.id })}
        >
          <Card>
            <Row style={{ justifyContent: 'space-between' }}>
              <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 16 }}>{serviceLabel(b.service_code)}</Text>
              <Tag text={BOOKING_STATUS[b.status]?.label ?? b.status} attention={ATTENTION.has(b.status)} />
            </Row>
            <P muted>{formatInstant(b.starts_at)}</P>
            <P>{b.meeting_place}</P>
            <P>{formatMoney(b.price_minor, b.currency)}</P>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}
