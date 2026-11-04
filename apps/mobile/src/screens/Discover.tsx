import * as Location from 'expo-location';
import { useEffect, useState } from 'react';
import { Image, Pressable, ScrollView, Text, View } from 'react-native';
import { api } from '../api';
import { formatMoney, SERVICE_NAMES } from '../format';
import { useNav } from '../nav';
import type { CompanionCard, Home, ProductCard, PublicProfile } from '../types';
import {
  Badge, Body, Button, Card, Chips, Empty, ErrorText, Field, H2, Loading, Muted, Photo, Row, Screen, colors, useAction, useAsync,
} from '../ui';

const BADGE_NAMES: Record<string, string> = { verified: 'Tasdiqlangan', trusted: 'Ishonchli', new: 'Yangi' };

export function CompanionTile({ item, wide }: { item: CompanionCard; wide?: boolean }) {
  const nav = useNav();
  return (
    <Pressable onPress={() => nav.push('companion', { profileId: item.profile_id })} style={{ width: wide ? undefined : 168 }}>
      <Card style={{ padding: 10 }}>
        {item.primary_photo?.url ? (
          <Image source={{ uri: item.primary_photo.url }} style={{ width: '100%', height: wide ? 180 : 150, borderRadius: 10, backgroundColor: colors.border }} />
        ) : <View style={{ height: wide ? 180 : 150, borderRadius: 10, backgroundColor: colors.primarySoft }} />}
        <Text style={{ fontWeight: '700', fontSize: 16 }} numberOfLines={1}>{item.display_name}{item.age ? `, ${item.age}` : ''}</Text>
        <Muted>{[item.area, item.distance_km !== null ? `${item.distance_km} km` : null].filter(Boolean).join(' · ') || item.city}</Muted>
        <Row>
          {item.stats.rating_average !== null && <Text>★ {item.stats.rating_average} ({item.stats.rating_count})</Text>}
          {item.badges.slice(0, 2).map((badge) => <Badge key={badge} label={BADGE_NAMES[badge] ?? badge} tone={badge === 'new' ? 'amber' : 'green'} />)}
        </Row>
        {item.min_price_minor !== null && <Text style={{ fontWeight: '600' }}>{formatMoney(item.min_price_minor, item.currency ?? 'UZS')} dan</Text>}
      </Card>
    </Pressable>
  );
}

export function ProductTile({ item }: { item: ProductCard }) {
  const nav = useNav();
  return (
    <Pressable onPress={() => nav.push('product', { productId: item.id })} style={{ width: 150 }}>
      <Card style={{ padding: 10 }}>
        <Photo uri={item.image?.url} size={128} radius={10} />
        <Text numberOfLines={2} style={{ fontWeight: '600' }}>{item.name}</Text>
        <Muted>{item.vendor_name}</Muted>
        <Text style={{ fontWeight: '700' }}>{formatMoney(item.price_minor, item.currency)}</Text>
      </Card>
    </Pressable>
  );
}

export function HomeScreen() {
  const nav = useNav();
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const permission = await Location.requestForegroundPermissionsAsync();
        if (permission.granted) {
          const position = await Location.getLastKnownPositionAsync();
          if (position) setCoords({ latitude: position.coords.latitude, longitude: position.coords.longitude });
        }
      } catch {
        // Location is optional; the "Nearby" section is simply omitted.
      }
    })();
  }, []);
  const { data, error, loading } = useAsync(() => api.get<Home>('/discovery/home', coords ?? {}), [coords]);
  return (
    <Screen title="Yondo" back={false} right={<Button small variant="secondary" title="🔔" onPress={() => nav.push('notifications')} />}>
      <Pressable onPress={() => nav.push('search')}>
        <View style={{ backgroundColor: colors.surface, borderRadius: 12, borderWidth: 1, borderColor: colors.border, padding: 14 }}>
          <Muted>🔍 Companion qidirish: xizmat, til, narx…</Muted>
        </View>
      </Pressable>
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.popular_experiences.length ? (
        <>
          <H2>Mashhur xizmatlar</H2>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {data.popular_experiences.map((exp) => (
              <Button key={exp.service_code} small variant="secondary" title={`${SERVICE_NAMES[exp.service_code] ?? exp.service_code} (${exp.companions})`}
                onPress={() => nav.push('search', { service: exp.service_code })} />
            ))}
          </ScrollView>
        </>
      ) : null}
      {data?.sections.filter((section) => section.items.length).map((section) => (
        <View key={section.key} style={{ gap: 8 }}>
          <H2>{SECTION_TITLES[section.key] ?? section.title}</H2>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10 }}>
            {section.items.map((item) => <CompanionTile key={item.profile_id} item={item} />)}
          </ScrollView>
        </View>
      ))}
      {data?.gift_sections.filter((section) => section.items.length).map((section) => (
        <View key={section.key} style={{ gap: 8 }}>
          <Row style={{ justifyContent: 'space-between' }}>
            <H2>{section.key === 'flowers' ? 'Gullar' : "Sovg'alar"}</H2>
            <Pressable onPress={() => nav.setTab('gifts')}><Text style={{ color: colors.primary }}>Barchasi ›</Text></Pressable>
          </Row>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10 }}>
            {section.items.map((item) => <ProductTile key={item.id} item={item} />)}
          </ScrollView>
        </View>
      ))}
      {data && !data.sections.some((s) => s.items.length) && <Empty text="Hozircha faol companionlar yo'q." />}
    </Screen>
  );
}

const SECTION_TITLES: Record<string, string> = {
  available_today: 'Bugun bo‘sh',
  nearby: 'Yaqin atrofda',
  top_rated: 'Eng yuqori baholangan',
  new_companions: 'Yangi companionlar',
  recommended: 'Tavsiya etiladi',
};

const SORTS: [string, string][] = [['recommended', 'Tavsiya'], ['rating', 'Reyting'], ['price_asc', 'Arzon'], ['price_desc', 'Qimmat'], ['newest', 'Yangi']];

export function SearchScreen() {
  const nav = useNav();
  const initial = nav.params<{ service?: string }>();
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [service, setService] = useState(initial.service ?? '');
  const [gender, setGender] = useState('');
  const [language, setLanguage] = useState('');
  const [sort, setSort] = useState('recommended');
  const [maxPrice, setMaxPrice] = useState('');
  const { data, error, loading } = useAsync(
    () => api.get<{ items: CompanionCard[]; total: number }>('/discovery/companions', {
      q: query, service, gender, language, sort: sort || 'recommended',
      price_max: maxPrice ? Number(maxPrice) * 100 : undefined, limit: 50,
    }),
    [query, service, gender, language, sort, maxPrice],
  );
  return (
    <Screen title="Qidiruv">
      <Field label="Ism yoki bio bo'yicha" value={q} onChangeText={setQ} onSubmitEditing={() => setQuery(q)} returnKeyType="search" />
      <Chips value={service} onChange={setService} options={Object.entries(SERVICE_NAMES)} />
      <Chips value={gender} onChange={setGender} options={[['female', 'Ayol'], ['male', 'Erkak']]} />
      <Chips value={language} onChange={setLanguage} options={[['uz', "O'zbek"], ['ru', 'Rus'], ['en', 'Ingliz']]} />
      <Chips value={sort} onChange={(v) => setSort(v || 'recommended')} options={SORTS} />
      <Field label="Maksimal narx (so'm)" value={maxPrice} onChangeText={setMaxPrice} keyboardType="number-pad" />
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data && <Muted>{data.total} ta natija</Muted>}
      {data?.items.map((item) => <CompanionTile key={item.profile_id} item={item} wide />)}
      {data && !data.items.length && <Empty text="Mos companion topilmadi." />}
    </Screen>
  );
}

interface ReviewSummary {
  rating_average: number | null;
  rating_count: number;
  criteria_average: Record<string, number>;
  tag_counts: Record<string, number>;
  items: { id: string; author_name: string | null; rating: number; text: string; tags: string[] }[];
}

export function CompanionProfileScreen() {
  const nav = useNav();
  const { profileId } = nav.params<{ profileId: string }>();
  const { data, error, reload } = useAsync(() => api.get<PublicProfile>(`/discovery/companions/${profileId}`), [profileId]);
  const reviews = useAsync(() => api.get<ReviewSummary>(`/discovery/companions/${profileId}/reviews`, { limit: 10 }), [profileId]);
  const action = useAction();
  if (!data) return <Screen title="Profil"><ErrorText error={error} /><Loading show={!error} /></Screen>;
  const toggleFavorite = () => void action.run(
    () => (data.is_favorite ? api.del(`/favorites/companions/${profileId}`) : api.put(`/favorites/companions/${profileId}`)),
    reload,
  );
  return (
    <Screen title={data.display_name} right={<Button small variant="secondary" title={data.is_favorite ? '♥' : '♡'} onPress={toggleFavorite} />}>
      <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {data.photos.map((photo) => photo.url && <Image key={photo.id} source={{ uri: photo.url }} style={{ width: 300, height: 360, borderRadius: 14, backgroundColor: colors.border }} />)}
      </ScrollView>
      <Card>
        <Text style={{ fontSize: 22, fontWeight: '800' }}>{data.display_name}{data.age ? `, ${data.age}` : ''}</Text>
        <Muted>{[data.area, data.city].filter(Boolean).join(', ')}</Muted>
        <Row>
          {data.badges.map((badge) => <Badge key={badge} label={BADGE_NAMES[badge] ?? badge} tone={badge === 'new' ? 'amber' : 'green'} />)}
        </Row>
        <Row>
          <Text>★ {data.stats.rating_average ?? '—'} ({data.stats.rating_count} baho)</Text>
          <Muted>· {data.stats.completed_bookings} ta uchrashuv</Muted>
        </Row>
        {data.bio ? <Body>{data.bio}</Body> : null}
        {data.languages.length ? <Muted>Tillar: {data.languages.join(', ')}</Muted> : null}
        {data.interests.length ? <Muted>Qiziqishlar: {data.interests.join(', ')}</Muted> : null}
      </Card>
      <H2>Xizmatlar</H2>
      {data.service_details.map((service) => (
        <Card key={service.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700' }}>{SERVICE_NAMES[service.service_code] ?? service.service_code}</Text>
            <Text style={{ fontWeight: '700' }}>{formatMoney(service.price_minor, service.currency)} / {service.unit_minutes} daq</Text>
          </Row>
          {service.description ? <Muted>{service.description}</Muted> : null}
        </Card>
      ))}
      <Button title="Bron qilish" disabled={!data.availability.length} onPress={() => nav.push('bookingCreate', { profileId })} />
      {!data.availability.length && <Muted>Yaqin 2 haftada bo'sh vaqt yo'q.</Muted>}
      <H2>Sharhlar</H2>
      {reviews.data && Object.keys(reviews.data.tag_counts).length ? (
        <Row>{Object.entries(reviews.data.tag_counts).map(([tag, count]) => <Badge key={tag} label={`${tag} · ${count}`} />)}</Row>
      ) : null}
      {reviews.data?.items.map((review) => (
        <Card key={review.id}>
          <Text style={{ fontWeight: '600' }}>{'★'.repeat(review.rating)} {review.author_name ?? ''}</Text>
          {review.text ? <Body>{review.text}</Body> : null}
        </Card>
      ))}
      {reviews.data && !reviews.data.items.length && <Muted>Hali sharhlar yo'q.</Muted>}
      <ErrorText error={action.error} />
      <Row>
        <Button small variant="secondary" title="Shikoyat qilish" onPress={() => nav.push('report', { userId: data.user_id, name: data.display_name })} />
        <Button small variant="danger" title="Bloklash" disabled={action.busy}
          onPress={() => void action.run(() => api.put(`/blocks/${data.user_id}`), nav.pop)} />
      </Row>
    </Screen>
  );
}
