import { useEffect, useState } from 'react';
import { Image, Text, View } from 'react-native';

import { api, type Schemas } from '../api';
import { formatMoney, initial, t } from '../shared';
import { useTheme } from '../theme';
import { Tag } from '../ui';

export type Card = Schemas['CompanionCard'];
const urlCache = new Map<string, string>();

/** Short-lived signed photo URL from the API; without storage the initial is shown instead. */
export function CompanionImage({ card, size }: { card: Card; size: number }) {
  const { palette } = useTheme();
  const photo = card.photos[0];
  const [url, setUrl] = useState<string | null>(photo ? (urlCache.get(photo.id) ?? null) : null);
  useEffect(() => {
    if (!photo || urlCache.has(photo.id)) return;
    let live = true;
    api
      .get<Schemas['PhotoDownload']>(`/discovery/companions/${card.id}/photos/${photo.id}/download`, { anonymous: true })
      .then((r) => {
        urlCache.set(photo.id, r.url);
        if (live) setUrl(r.url);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [photo, card.id]);
  const box = { width: size, height: size, borderRadius: 16, backgroundColor: palette.chip, borderColor: palette.line, borderWidth: 1 };
  if (url) {
    return <Image source={{ uri: url }} style={box} alt={photo?.caption || t('card.photoAlt', { name: card.display_name })} />;
  }
  return (
    <View style={[box, { alignItems: 'center', justifyContent: 'center' }]} aria-hidden>
      <Text style={{ color: palette.fg, fontSize: size / 2.6, fontWeight: '700' }}>{initial(card.display_name)}</Text>
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
