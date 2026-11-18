import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useAuth } from '../auth';
import { ICONS, Icon } from '../brand';
import { useNav } from '../nav';
import { serviceLabel, t, type Key } from '../shared';
import { FONT, useTheme } from '../theme';
import { Button, Card, Chip, ChipGroup, ErrorText, Field, H1, Loading, P, Row, Screen, Sheet, Tag, TOUCH } from '../ui';
import { useResource } from '../useResource';
import { CardDeck } from './CardDeck';
import { CompanionRow, type Card as CompanionCard } from './companion';

type Page = Schemas['DiscoveryPage'];
const SERVICES = ['coffee', 'walking', 'cinema', 'shopping', 'event', 'city_friend', 'conversation', 'study'];
/** The API's sort orders (`/discovery/companions?sort=`). Stars only come from reviews of completed meetings. */
const SORTS = ['default', 'rating', 'meetings', 'likes'] as const;
type Sort = (typeof SORTS)[number];
const STARS = ['4.5', '4', '3'];
const LIMIT = 20;

interface Filters {
  service?: string;
  stars?: string;
  sort: Sort;
}

export function DiscoverScreen() {
  const nav = useNav();
  const { user } = useAuth();
  const { palette } = useTheme();
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<Filters>({ sort: 'default' });
  const [sheet, setSheet] = useState(false);
  const [view, setView] = useState<'list' | 'cards'>('list');
  const [extra, setExtra] = useState<CompanionCard[]>([]);
  const [more, setMore] = useState<{ busy: boolean; done: boolean; err?: string }>({ busy: false, done: false });
  const base = {
    q: query,
    service_code: filters.service,
    rating_min: filters.stars,
    sort: filters.sort === 'default' ? undefined : filters.sort,
    limit: LIMIT,
  };
  // Signed in: the token is sent so each card carries `liked_by_me`; discovery stays public otherwise.
  const first = useResource(() => {
    setExtra([]);
    setMore({ busy: false, done: false });
    return api.get<Page>('/discovery/companions', { query: { ...base, offset: 0 }, anonymous: !user });
  }, [query, filters.service, filters.stars, filters.sort, user?.id]);
  const items = [...(first.data?.items ?? []), ...extra];
  const hasMore = !!first.data?.has_more && !more.done;

  const loadMore = async () => {
    if (more.busy) return;
    setMore({ busy: true, done: false });
    try {
      const page = await api.get<Page>('/discovery/companions', { query: { ...base, offset: items.length }, anonymous: !user });
      setExtra((x) => [...x, ...page.items]);
      setMore({ busy: false, done: !page.has_more });
    } catch (e) {
      setMore({ busy: false, done: false, err: errorText(e) });
    }
  };

  const chips: { key: 'q' | 'service' | 'stars'; label: string }[] = [];
  if (query) chips.push({ key: 'q', label: query });
  if (filters.service) chips.push({ key: 'service', label: serviceLabel(filters.service) });
  if (filters.stars) chips.push({ key: 'stars', label: `${filters.stars}+ ★` });
  const clearAll = () => {
    setQ('');
    setQuery('');
    setFilters((f) => ({ sort: f.sort }));
  };
  const removeChip = (key: 'q' | 'service' | 'stars') => {
    if (key === 'q') {
      setQ('');
      setQuery('');
    } else setFilters((f) => ({ ...f, [key]: undefined }));
  };

  return (
    <Screen>
      <Card style={{ gap: 12, padding: 20 }}>
        <Row>
          <Tag text={t('discovery.tag')} />
        </Row>
        <H1>{t('discovery.h1')}</H1>
        <P muted>{t('discovery.lead')}</P>
        <Field label={t('discovery.searchLabel')} value={q} onChangeText={setQ} returnKeyType="search" onSubmitEditing={() => setQuery(q.trim())} />
        <Row>
          <Button small label={t('discovery.search')} onPress={() => setQuery(q.trim())} />
        </Row>
      </Card>

      <Row style={{ justifyContent: 'space-between' }}>
        <Pressable
          role="button"
          aria-label={chips.filter((c) => c.key !== 'q').length ? t('discovery.filtersCount', { n: chips.filter((c) => c.key !== 'q').length }) : t('discovery.filters')}
          onPress={() => setSheet(true)}
          style={({ pressed }) => [{ minHeight: TOUCH, paddingHorizontal: 16, borderRadius: 999, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: palette.glass, borderColor: palette.glassLine }, pressed && { opacity: 0.85 }]}
        >
          <Icon d={ICONS.filter} size={18} color={palette.fg} />
          <Text style={{ color: palette.fg, fontFamily: FONT.medium, fontSize: 15 }}>
            {chips.filter((c) => c.key !== 'q').length ? t('discovery.filtersCount', { n: chips.filter((c) => c.key !== 'q').length }) : t('discovery.filters')}
          </Text>
        </Pressable>
        <ChipGroup label={t('discovery.view')}>
          <Chip label={t('discovery.view.list')} selected={view === 'list'} onPress={() => setView('list')} />
          <Chip label={t('discovery.view.cards')} selected={view === 'cards'} onPress={() => setView('cards')} />
        </ChipGroup>
      </Row>
      <ChipGroup label={t('discovery.sort')}>
        {SORTS.map((s) => (
          <Chip key={s} label={t(`discovery.sort.${s}` as Key)} selected={filters.sort === s} onPress={() => setFilters((f) => ({ ...f, sort: s }))} />
        ))}
      </ChipGroup>
      {chips.length > 0 && (
        <Row>
          {chips.map((c) => (
            <Pressable
              key={c.key}
              role="button"
              aria-label={t('discovery.chipRemove', { label: c.label })}
              onPress={() => removeChip(c.key)}
              style={({ pressed }) => [{ minHeight: TOUCH, paddingHorizontal: 14, borderRadius: 999, borderWidth: 1, justifyContent: 'center', backgroundColor: palette.glass, borderColor: palette.glassLine }, pressed && { opacity: 0.85 }]}
            >
              <Text style={{ color: palette.fg, fontFamily: FONT.medium }}>{`${c.label}  ✕`}</Text>
            </Pressable>
          ))}
          <Button kind="ghost" small label={t('discovery.clearAll')} onPress={clearAll} />
        </Row>
      )}

      {first.loading && <Loading />}
      {!!first.error && (
        <>
          <ErrorText text={errorText(first.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={first.reload} />
        </>
      )}
      {first.data && items.length === 0 && (
        <>
          <P muted>{chips.length ? t('discovery.noMatch') : t('discovery.noneVisible')}</P>
          {chips.length > 0 && <Button kind="ghost" label={t('discovery.clearFilters')} onPress={clearAll} />}
        </>
      )}
      {first.data && items.length > 0 && view === 'cards' && (
        <CardDeck
          key={JSON.stringify([query, filters])}
          items={items}
          canMore={hasMore}
          loadingMore={more.busy}
          loadMore={loadMore}
          onOpen={(id) => nav.push({ name: 'profile', id })}
          onSignIn={() => nav.push({ name: 'login', then: { name: 'discover' } })}
        />
      )}
      {view === 'list' && items.map((card) => <CompanionRow key={card.id} card={card} onOpen={() => nav.push({ name: 'profile', id: card.id })} />)}
      {more.err && <ErrorText text={more.err} />}
      {view === 'list' && hasMore && <Button kind="ghost" label={t('discovery.more')} busy={more.busy} onPress={() => void loadMore()} />}

      <Sheet open={sheet} title={t('discovery.filters')} onClose={() => setSheet(false)}>
        <FilterSheet
          value={filters}
          onApply={(f) => {
            setFilters(f);
            setSheet(false);
          }}
          onClear={() => {
            clearAll();
            setSheet(false);
          }}
          onClose={() => setSheet(false)}
        />
      </Sheet>
    </Screen>
  );
}

/** Edits a draft; nothing is fetched until "Natijalarni körsatiş" (as on the web). */
function FilterSheet({ value, onApply, onClear, onClose }: { value: Filters; onApply: (f: Filters) => void; onClear: () => void; onClose: () => void }) {
  const [draft, setDraft] = useState<Filters>(value);
  const { palette } = useTheme();
  const label = (text: string) => <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 15 }}>{text}</Text>;
  return (
    <View style={{ gap: 12 }}>
      {label(t('discovery.serviceType'))}
      <ChipGroup label={t('discovery.serviceType')}>
        <Chip label={t('discovery.all')} selected={!draft.service} onPress={() => setDraft((d) => ({ ...d, service: undefined }))} />
        {SERVICES.map((code) => (
          <Chip key={code} label={serviceLabel(code)} selected={draft.service === code} onPress={() => setDraft((d) => ({ ...d, service: code }))} />
        ))}
      </ChipGroup>
      {label(t('discovery.minStars'))}
      <ChipGroup label={t('discovery.minStars')}>
        <Chip label={t('discovery.anyRating')} selected={!draft.stars} onPress={() => setDraft((d) => ({ ...d, stars: undefined }))} />
        {STARS.map((s) => (
          <Chip key={s} label={`${s}+ ★`} selected={draft.stars === s} onPress={() => setDraft((d) => ({ ...d, stars: s }))} />
        ))}
      </ChipGroup>
      <P muted>{t('discovery.starsNote')}</P>
      {label(t('discovery.sort'))}
      <ChipGroup label={t('discovery.sort')}>
        {SORTS.map((s) => (
          <Chip key={s} label={t(`discovery.sort.${s}` as Key)} selected={draft.sort === s} onPress={() => setDraft((d) => ({ ...d, sort: s }))} />
        ))}
      </ChipGroup>
      <Row>
        <Button label={t('discovery.apply')} onPress={() => onApply(draft)} />
        <Button kind="ghost" label={t('discovery.close')} onPress={onClose} />
        <Button kind="ghost" label={t('discovery.clearAll')} onPress={onClear} />
      </Row>
    </View>
  );
}
