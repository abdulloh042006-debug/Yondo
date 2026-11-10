import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useNav } from '../nav';
import { serviceLabel, t } from '../shared';
import { useTheme } from '../theme';
import { Button, Card as Box, Chip, ChipGroup, ErrorText, Field, H1, Loading, P, Row, Screen } from '../ui';
import { useResource } from '../useResource';
import { CompanionImage, VerifiedTag, priceFrom, type Card } from './companion';

type Page = Schemas['DiscoveryPage'];
const SERVICES = ['coffee', 'walking', 'cinema', 'shopping', 'event', 'city_friend', 'conversation', 'study'];
const LIMIT = 20;

export function DiscoverScreen() {
  const nav = useNav();
  const { palette } = useTheme();
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [service, setService] = useState<string>();
  const [extra, setExtra] = useState<Card[]>([]);
  const [more, setMore] = useState<{ busy: boolean; done: boolean; err?: string }>({ busy: false, done: false });
  const base = { q: query, service_code: service, limit: LIMIT };
  const first = useResource(() => {
    setExtra([]);
    setMore({ busy: false, done: false });
    return api.get<Page>('/discovery/companions', { query: { ...base, offset: 0 }, anonymous: true });
  }, [query, service]);
  const items = [...(first.data?.items ?? []), ...extra];
  const hasMore = !!first.data?.has_more && !more.done;

  const loadMore = async () => {
    setMore({ busy: true, done: false });
    try {
      const page = await api.get<Page>('/discovery/companions', { query: { ...base, offset: items.length }, anonymous: true });
      setExtra((x) => [...x, ...page.items]);
      setMore({ busy: false, done: !page.has_more });
    } catch (e) {
      setMore({ busy: false, done: false, err: errorText(e) });
    }
  };

  return (
    <Screen>
      <H1>{t('discovery.h1')}</H1>
      <P muted>{t('discovery.lead')}</P>
      <Field label={t('discovery.searchLabel')} value={q} onChangeText={setQ} returnKeyType="search" onSubmitEditing={() => setQuery(q.trim())} />
      <Row>
        <Button small label={t('discovery.search')} onPress={() => setQuery(q.trim())} />
      </Row>
      <ChipGroup label={t('discovery.serviceType')}>
        <Chip label={t('discovery.all')} selected={!service} onPress={() => setService(undefined)} />
        {SERVICES.map((code) => (
          <Chip key={code} label={serviceLabel(code)} selected={service === code} onPress={() => setService(code)} />
        ))}
      </ChipGroup>
      {first.loading && <Loading />}
      {!!first.error && (
        <>
          <ErrorText text={errorText(first.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={first.reload} />
        </>
      )}
      {first.data && items.length === 0 && <P muted>{query || service ? t('discovery.noMatch') : t('discovery.noneVisible')}</P>}
      {items.map((card) => (
        <Pressable
          key={card.id}
          role="button"
          aria-label={t('card.open', { name: card.display_name })}
          onPress={() => nav.push({ name: 'profile', id: card.id })}
        >
          <Box style={{ flexDirection: 'row', gap: 12 }}>
            <CompanionImage card={card} size={84} />
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={{ color: palette.fg, fontSize: 18, fontWeight: '700' }}>{card.display_name}</Text>
              <Text style={{ color: palette.muted }}>
                {[card.city, card.age ? t('profile.ageYears', { n: card.age }) : null].filter(Boolean).join(' · ')}
              </Text>
              <VerifiedTag card={card} />
              <Text style={{ color: palette.fg }}>{priceFrom(card)}</Text>
            </View>
          </Box>
        </Pressable>
      ))}
      {more.err && <ErrorText text={more.err} />}
      {hasMore && <Button kind="ghost" label={t('discovery.more')} busy={more.busy} onPress={() => void loadMore()} />}
    </Screen>
  );
}
