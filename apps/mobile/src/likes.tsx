import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { api, errorText, type Schemas } from './api';
import { useAuth } from './auth';
import { ICONS, Icon, useReducedMotion } from './brand';
import { toggledLike } from './photoRules';
import { t } from './shared';
import { FONT, useTheme } from './theme';
import { TOUCH, Tag } from './ui';

type Card = Schemas['CompanionCard'];

/** Read-only public like count (cards; signed-out visitors). */
export function LikeCount({ count }: { count: number }) {
  const { palette } = useTheme();
  return (
    <View
      role="img"
      aria-label={t('like.count', { n: count })}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1.5, borderColor: palette.line, backgroundColor: palette.chip, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, alignSelf: 'flex-start' }}
    >
      <Icon d={ICONS.thumb} size={16} color={palette.fg} />
      <Text style={{ color: palette.fg, fontSize: 13, fontFamily: FONT.medium }}>{count}</Text>
    </View>
  );
}

/**
 * "Yoqdi" — the web's LikeButton: a public count, separate from the private favourite (heart / Sevimlilar).
 * Optimistic toggle with rollback; the error text comes from the API error `code`. Signed out: the count only.
 */
export function LikeButton({ card, onError }: { card: Pick<Card, 'id' | 'display_name' | 'like_count' | 'liked_by_me'>; onError?: (text: string) => void }) {
  const { user } = useAuth();
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const [state, setState] = useState({ like_count: card.like_count, liked_by_me: !!card.liked_by_me });
  const [busy, setBusy] = useState(false);
  if (!user) return <LikeCount count={state.like_count} />;
  const toggle = async () => {
    if (busy) return;
    const before = state;
    setState(toggledLike(before));
    setBusy(true);
    try {
      const path = `/discovery/companions/${card.id}/like`;
      const next = before.liked_by_me ? await api.del<Schemas['LikeState']>(path) : await api.put<Schemas['LikeState']>(path);
      setState({ like_count: next.like_count, liked_by_me: next.liked_by_me });
    } catch (e) {
      setState(before);
      onError?.(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const on = state.liked_by_me;
  return (
    <Pressable
      role="button"
      aria-pressed={on}
      aria-busy={busy}
      aria-label={`${on ? t('like.remove', { name: card.display_name }) : t('like.add', { name: card.display_name })} — ${t('like.count', { n: state.like_count })}`}
      onPress={() => void toggle()}
      style={({ pressed }) => [
        { minHeight: TOUCH, paddingHorizontal: 14, borderRadius: 999, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
        { backgroundColor: palette.glass, borderColor: on ? palette.accent : palette.glassLine },
        pressed && { opacity: 0.85 },
        pressed && !reduced && { transform: [{ scale: 0.95 }] },
      ]}
    >
      <Icon d={ICONS.thumb} size={18} color={on ? palette.accent : palette.fg} fill={on ? palette.accent : 'none'} />
      <Text style={{ color: palette.fg, fontFamily: FONT.medium, fontSize: 15 }}>{t('like.label')}</Text>
      <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 15 }}>{state.like_count}</Text>
    </Pressable>
  );
}

/** Stars (only from reviews of completed meetings, else "Hali baho yöq"), completed meetings, likes. */
export function CardStats({ card, likes = true }: { card: Card; likes?: boolean }) {
  const rated = card.rating != null && card.review_count > 0;
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
      {rated ? (
        <View role="img" aria-label={t('card.ratingAria', { rating: card.rating!.toFixed(1), count: card.review_count })}>
          <Tag text={`★ ${card.rating!.toFixed(1)} (${card.review_count})`} />
        </View>
      ) : (
        <Tag text={t('card.noRating')} />
      )}
      <Tag text={t('card.meetings', { n: card.meeting_count })} />
      {likes && <LikeCount count={card.like_count} />}
    </View>
  );
}
