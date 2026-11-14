import { useEffect, useState } from 'react';
import { Image, Pressable, Text, View, type DimensionValue } from 'react-native';

import { api, type Schemas } from '../api';
import { useReducedMotion } from '../brand';
import { HeartButton } from '../favorites';
import { formatMoney, initial, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Tag } from '../ui';

export type Card = Schemas['CompanionCard'];
/** Signed URLs live 5 minutes on the server; a cached one is reused for 4. */
const URL_TTL_MS = 4 * 60_000;
const urlCache = new Map<string, { url: string; at: number }>();
const cached = (id: string): string | null => {
  const hit = urlCache.get(id);
  return hit && Date.now() - hit.at < URL_TTL_MS ? hit.url : null;
};

/**
 * Short-lived signed photo URL from the API (the same download endpoint as the web); the initial is only a
 * fallback when there is no photo or storage is unavailable. `size` = square thumbnail; without it the image fills
 * the card width in the web card's 4:5 frame.
 */
export function CompanionImage({ card, size }: { card: Card; size?: number }) {
  const { palette } = useTheme();
  const photo = card.photos[0];
  const [url, setUrl] = useState<string | null>(photo ? cached(photo.id) : null);
  useEffect(() => {
    if (!photo || cached(photo.id)) return;
    let live = true;
    api
      .get<Schemas['PhotoDownload']>(`/discovery/companions/${card.id}/photos/${photo.id}/download`, { anonymous: true })
      .then((r) => {
        urlCache.set(photo.id, { url: r.url, at: Date.now() });
        if (live) setUrl(r.url);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [photo, card.id]);
  const w: DimensionValue = size ?? '100%';
  const box = size
    ? { width: w, height: size, borderRadius: 16, backgroundColor: palette.chip, borderColor: palette.glassLine, borderWidth: 1 }
    : { width: w, aspectRatio: 4 / 5, borderRadius: 18, backgroundColor: palette.chip };
  if (url) {
    return <Image source={{ uri: url }} style={box} alt={photo?.caption || t('card.photoAlt', { name: card.display_name })} />;
  }
  return (
    <View style={[box, { alignItems: 'center', justifyContent: 'center' }]} aria-hidden>
      <Text style={{ color: palette.fg, fontSize: (size ?? 180) / 2.6, fontFamily: FONT.display }}>{initial(card.display_name)}</Text>
    </View>
  );
}

/** Verified only when the API says `verified: true` (never inferred on the client). */
export function VerifiedTag({ card }: { card: Card }) {
  return card.verified === true ? <Tag text={t('card.verified')} attention /> : null;
}

export function priceFrom(card: Card): string {
  if (!card.services.length) return t('card.noPrices');
  const cheapest = card.services.reduce((a, b) => (b.price_minor < a.price_minor ? b : a));
  return t('card.priceFrom', { price: formatMoney(cheapest.price_minor, cheapest.currency) });
}

/** The web's companion card (photo, heart, verified tag, name, city/age, price) as one pressable glass card. */
export function CompanionRow({ card, onOpen }: { card: Card; onOpen: () => void }) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  return (
    <View style={{ borderRadius: 22, borderWidth: 1, borderColor: palette.glassLine, backgroundColor: palette.glass, padding: 8 }}>
      <Pressable
        role="button"
        aria-label={t('card.open', { name: card.display_name })}
        onPress={onOpen}
        style={({ pressed }) => [{ gap: 10 }, pressed && { opacity: 0.9 }, pressed && !reduced && { transform: [{ scale: 0.985 }] }]}
      >
        <CompanionImage card={card} />
        <View style={{ paddingHorizontal: 8, paddingBottom: 8, gap: 4 }}>
          <Text style={{ color: palette.fg, fontSize: 20, fontFamily: FONT.display }}>
            {card.display_name}
            {card.age ? `, ${card.age}` : ''}
          </Text>
          {!!card.city && <Text style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 15 }}>{card.city}</Text>}
          <Text style={{ color: palette.fg, fontFamily: FONT.medium, fontSize: 15 }}>{priceFrom(card)}</Text>
        </View>
      </Pressable>
      <View style={{ position: 'absolute', top: 16, right: 16 }}>
        <HeartButton id={card.id} name={card.display_name} />
      </View>
      {card.verified === true && (
        <View style={{ position: 'absolute', top: 16, left: 16 }}>
          <Tag text={t('card.verified')} attention />
        </View>
      )}
    </View>
  );
}
