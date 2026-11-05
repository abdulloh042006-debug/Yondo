import { useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { ApiError, api, errorText, type Schemas } from '../api';
import { useAuth } from '../auth';
import { useNav } from '../nav';
import { formatMoney, serviceLabel, t } from '../shared';
import { useTheme } from '../theme';
import { Banner, Button, Card as Box, Chip, ChipGroup, ErrorText, Field, H1, H2, Loading, P, Row, Screen } from '../ui';
import { useResource } from '../useResource';
import { CompanionImage, VerifiedTag, type Card } from './companion';

export function ProfileScreen({ id }: { id: string }) {
  const nav = useNav();
  const { palette } = useTheme();
  const { user, reload } = useAuth();
  const res = useResource(() => api.get<Card>(`/discovery/companions/${id}`, { anonymous: true }), [id]);
  const [booking, setBooking] = useState(false);
  const [roleErr, setRoleErr] = useState<string>();
  const [roleBusy, setRoleBusy] = useState(false);
  const c = res.data;
  if (res.loading && !c) return <Screen><Loading /></Screen>;
  if (!c) {
    const missing = res.error instanceof ApiError && res.error.status === 404;
    return (
      <Screen>
        <H1>{missing ? t('profile.notFound') : t('common.failedTitle')}</H1>
        <P muted>{missing ? t('profile.notFoundBody') : errorText(res.error)}</P>
        <Button kind="ghost" label={t('profile.back')} onPress={nav.back} />
      </Screen>
    );
  }
  const isCustomer = !!user?.roles.includes('customer');
  const enableCustomer = async () => {
    if (!user) return;
    setRoleBusy(true);
    setRoleErr(undefined);
    try {
      const roles = [...new Set([...user.roles.filter((r) => r !== 'admin'), 'customer'])];
      await api.put('/auth/roles', { roles });
      await reload();
    } catch (e) {
      setRoleErr(errorText(e));
    } finally {
      setRoleBusy(false);
    }
  };

  return (
    <Screen>
      <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
      <View style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
        <CompanionImage card={c} size={112} />
        <View style={{ flex: 1, gap: 6 }}>
          <H1>{c.display_name}</H1>
          <Text style={{ color: palette.muted }}>
            {[c.city, c.age ? t('profile.ageYears', { n: c.age }) : null].filter(Boolean).join(' · ')}
          </Text>
          <VerifiedTag card={c} />
        </View>
      </View>
      <P>{c.bio || t('profile.noBio')}</P>
      {c.languages.length > 0 && <P muted>{`${t('profile.languages')}: ${c.languages.join(', ')}`}</P>}
      <H2>{t('profile.services')}</H2>
      {c.services.length === 0 && <P muted>{t('profile.noServices')}</P>}
      {c.services.map((s) => (
        <Box key={s.id}>
          <Text style={{ color: palette.fg, fontWeight: '700', fontSize: 16 }}>{serviceLabel(s.service_code)}</Text>
          {!!s.description && <P muted>{s.description}</P>}
          <Text style={{ color: palette.fg }}>{`${formatMoney(s.price_minor, s.currency)} / ${t('common.minutesShort', { n: s.unit_minutes })}`}</Text>
        </Box>
      ))}
      <P muted>{t('profile.bookNote')}</P>
      {!user ? (
        <Button label={t('profile.book')} onPress={() => nav.push({ name: 'login', then: { name: 'profile', id: c.id } })} />
      ) : isCustomer ? (
        <Button label={t('profile.book')} disabled={!c.services.length} onPress={() => setBooking(true)} />
      ) : (
        <>
          <P>{t('profile.chooseCustomer')}</P>
          {roleErr && <ErrorText text={roleErr} />}
          <Button label={t('mobile.enableCustomer')} busy={roleBusy} onPress={() => void enableCustomer()} />
        </>
      )}
      {booking && <BookingForm card={c} onDone={() => { setBooking(false); nav.switchTab('bookings'); }} onCancel={() => setBooking(false)} />}
    </Screen>
  );
}

/** Tashkent is UTC+5 all year: build the next 14 calendar days there and send an explicit +05:00 instant. */
function nextDays(): string[] {
  const days: string[] = [];
  const base = Date.now() + 5 * 3600_000;
  for (let i = 0; i < 14; i++) days.push(new Date(base + i * 86_400_000).toISOString().slice(0, 10));
  return days;
}

/** Exactly the 5 booking fields the API takes (service, start instant, duration, place, timezone). */
function BookingForm({ card, onDone, onCancel }: { card: Card; onDone: () => void; onCancel: () => void }) {
  const days = useMemo(nextDays, []);
  const [serviceId, setServiceId] = useState(card.services[0]?.id ?? '');
  const [day, setDay] = useState(days[0]);
  const [time, setTime] = useState('');
  const [units, setUnits] = useState(1);
  const [place, setPlace] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [local, setLocal] = useState<{ when?: string; place?: string }>({});
  const service = card.services.find((s) => s.id === serviceId) ?? card.services[0];
  if (!service) return null;
  const estimate = service.price_minor * units;

  const submit = async () => {
    const problems: { when?: string; place?: string } = {};
    const ok = /^([01]\d|2[0-3]):[0-5]\d$/.test(time.trim());
    const start = ok ? new Date(`${day}T${time.trim()}:00+05:00`) : null;
    if (!start || Number.isNaN(start.getTime())) problems.when = t('book.errWhen');
    else if (start.getTime() < Date.now()) problems.when = t('err.booking_start_in_past');
    if (place.trim().length < 3) problems.place = t('book.errPlace');
    setLocal(problems);
    if (problems.when || problems.place || !start) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.post<Schemas['BookingResponse']>('/bookings', {
        service_id: service.id,
        starts_at: start.toISOString(),
        duration_minutes: service.unit_minutes * units,
        meeting_place: place.trim(),
        timezone: 'Asia/Tashkent',
      });
      onDone();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <H2>{t('book.title', { name: card.display_name })}</H2>
      <P>{t('book.service')}</P>
      <ChipGroup label={t('book.service')}>
        {card.services.map((s) => (
          <Chip key={s.id} label={serviceLabel(s.service_code)} selected={s.id === service.id} onPress={() => { setServiceId(s.id); setUnits(1); }} />
        ))}
      </ChipGroup>
      <P>{t('mobile.day')}</P>
      <ChipGroup label={t('mobile.day')}>
        {days.map((d) => (
          <Chip key={d} label={`${d.slice(8, 10)}.${d.slice(5, 7)}`} selected={d === day} onPress={() => setDay(d)} />
        ))}
      </ChipGroup>
      <Field label={t('mobile.time')} value={time} onChangeText={setTime} placeholder="18:30" keyboardType="numbers-and-punctuation" maxLength={5} error={local.when} />
      <P>{t('book.duration')}</P>
      <ChipGroup label={t('book.duration')}>
        {[1, 2, 3, 4].map((n) => (
          <Chip key={n} label={t('book.minutesLong', { n: service.unit_minutes * n })} selected={n === units} onPress={() => setUnits(n)} />
        ))}
      </ChipGroup>
      <Field label={t('book.place')} hint={t('book.placeHint')} value={place} onChangeText={setPlace} maxLength={512} error={local.place} />
      <Banner text={`${t('book.estimateBefore')}${formatMoney(estimate, service.currency)}${t('book.estimateAfter')}`} />
      {err && <ErrorText text={err} />}
      <Row>
        <Button kind="ghost" label={t('common.cancel')} disabled={busy} onPress={onCancel} />
        <Button label={t('book.send')} busy={busy} onPress={() => void submit()} />
      </Row>
    </Box>
  );
}
