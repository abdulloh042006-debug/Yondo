import { useEffect, useRef, useState } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';

import { useAuth } from '../auth';
import { useReducedMotion } from '../brand';
import { useFavorites } from '../favorites';
import { CardStats, LikeButton } from '../likes';
import { serviceLabel, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Button, ErrorText, P, Tag } from '../ui';
import { CompanionImage, VerifiedTag, priceFrom, type Card } from './companion';

/**
 * "Kartoçkalar" (the web's CardDeck): one companion at a time, two actions only — "Saqlaş" (adds to the private
 * favourites) and "Keyingisi" (skip, on the device). No dislike, no match, no swipe gesture. The card slides in;
 * with the OS "reduce motion" setting it only appears.
 */
export function CardDeck({
  items,
  canMore,
  loadingMore,
  loadMore,
  onOpen,
  onSignIn,
}: {
  items: Card[];
  canMore: boolean;
  loadingMore: boolean;
  loadMore: () => Promise<void>;
  onOpen: (id: string) => void;
  onSignIn: () => void;
}) {
  const { user } = useAuth();
  const fav = useFavorites();
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [likeErr, setLikeErr] = useState<string>();
  const slide = useRef(new Animated.Value(1)).current;
  const card = items[index];

  useEffect(() => {
    if (canMore && !loadingMore && index >= items.length - 2) void loadMore();
  }, [index, items.length, canMore, loadingMore, loadMore]);
  useEffect(() => {
    if (reduced) return slide.setValue(1);
    slide.setValue(0);
    const a = Animated.spring(slide, { toValue: 1, useNativeDriver: true, stiffness: 260, damping: 26, mass: 1 });
    a.start();
    return () => a.stop();
  }, [index, reduced, slide]);

  if (!card) {
    if (canMore || loadingMore) return <P muted>{t('common.loading')}…</P>;
    return (
      <View style={{ gap: 10 }}>
        <Text role="heading" style={{ color: palette.fg, fontFamily: FONT.display, fontSize: 22 }}>{t('card.end')}</Text>
        <P muted>{t('card.endBody')}</P>
        <Button label={t('card.restart')} onPress={() => setIndex(0)} />
      </View>
    );
  }
  const saved = fav.ids.has(card.id);
  const categories = [...new Set(card.services.map((s) => s.service_code))].slice(0, 4);
  const save = () => {
    if (!user) return onSignIn();
    if (fav.canFavorite && !saved) void fav.toggle(card.id);
  };
  return (
    <View aria-label={t('card.deckAria')} style={{ gap: 12 }}>
      <Text aria-live="polite" style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 14 }}>
        {t('card.position', { i: index + 1, n: items.length })}
        {canMore ? '+' : ''}
      </Text>
      <Animated.View
        key={card.id}
        style={{
          opacity: slide,
          transform: [{ translateX: slide.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }],
          borderRadius: 22,
          borderWidth: 1,
          borderColor: palette.glassLine,
          backgroundColor: palette.glass,
          padding: 8,
          gap: 10,
        }}
      >
        <CompanionImage card={card} />
        <View style={{ paddingHorizontal: 8, paddingBottom: 8, gap: 8 }}>
          <Pressable role="link" aria-label={t('card.open', { name: card.display_name })} onPress={() => onOpen(card.id)}>
            <Text role="heading" style={{ color: palette.fg, fontSize: 22, fontFamily: FONT.display, textDecorationLine: 'underline' }}>
              {card.display_name}
              {card.age ? `, ${card.age}` : ''}
            </Text>
          </Pressable>
          {!!card.city && <Text style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 15 }}>{card.city}</Text>}
          <VerifiedTag card={card} />
          {categories.length > 0 && (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {categories.map((code) => (
                <Tag key={code} text={serviceLabel(code)} />
              ))}
            </View>
          )}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
            <CardStats card={card} likes={false} />
            <LikeButton key={card.id} card={card} onError={setLikeErr} />
          </View>
          {likeErr && <ErrorText text={likeErr} />}
          <Text style={{ color: palette.fg, fontFamily: FONT.medium, fontSize: 15 }}>{priceFrom(card)}</Text>
        </View>
      </Animated.View>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Button
            kind="ghost"
            label={saved ? t('card.saved') : t('card.save')}
            busy={fav.pending.has(card.id)}
            disabled={!!user && (!fav.canFavorite || saved)}
            onPress={save}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Button label={t('card.next')} onPress={() => { setLikeErr(undefined); setIndex((i) => Math.min(i + 1, items.length)); }} />
        </View>
      </View>
      {!!user && !fav.canFavorite && <P muted>{t('card.saveSignIn')}</P>}
    </View>
  );
}
