import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { SafeImage } from '../ui/SafeImage';
import { t } from '../i18n';
import { formatMoney, initial } from '../lib/format';
import { toggledLike } from '../lib/photos';
import { serviceLabel } from '../lib/labels';
import { useToast } from '../ui/feedback';

export type Card = Schemas['CompanionCard'];
export type Photo = Schemas['DiscoveryPhoto'];

const urlCache = new Map<string, string>();
const NO_IDS: Set<string> = new Set();

/** Fetches the short-lived signed URL for a public photo; falls back to a gradient + initial. */
export function CompanionImage({ profileId, photo, name, rounded }: { profileId: string; photo?: Photo; name: string; rounded?: boolean }) {
  // undefined = the signed URL is being fetched, null = it could not be obtained (SafeImage then shows the logo).
  const [url, setUrl] = useState<string | null | undefined>(photo ? urlCache.get(photo.id) : undefined);
  useEffect(() => {
    if (!photo || urlCache.has(photo.id)) return;
    let live = true;
    api
      .get<Schemas['PhotoDownload']>(`/discovery/companions/${profileId}/photos/${photo.id}/download`, { anonymous: true })
      .then((r) => {
        urlCache.set(photo.id, r.url);
        if (live) setUrl(r.url);
      })
      .catch(() => {
        if (live) setUrl(null); // storage unavailable: the logo tile stays
      });
    return () => {
      live = false;
    };
  }, [photo, profileId]);
  return (
    <div className="media" style={rounded ? { borderRadius: 'var(--r-md)' } : undefined}>
      {photo ? (
        <SafeImage src={url} alt={photo.caption || t('card.photoAlt', { name })} loading="lazy" width={photo.width} height={photo.height} />
      ) : (
        <span className="initial" aria-hidden="true">{initial(name)}</span>
      )}
    </div>
  );
}

export function minPrice(card: Card): string | null {
  if (!card.services.length) return null;
  const s = card.services.reduce((a, b) => (b.price_minor < a.price_minor ? b : a));
  return `${formatMoney(s.price_minor, s.currency)} / ${t('common.minutesShort', { n: s.unit_minutes })}`;
}

/* -------- favourites (customers only; every change waits for the server) -------- */
export function useFavorites(onChanged?: () => void) {
  const { user } = useAuth();
  const toast = useToast();
  const canFavorite = !!user?.roles.includes('customer');
  const [ids, setIds] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!canFavorite) return;
    let live = true;
    api
      .get<Card[]>('/discovery/favorites')
      .then((list) => live && setIds(new Set(list.map((c) => c.id))))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [canFavorite]);
  const toggle = async (id: string) => {
    if (pending.has(id)) return;
    const had = ids.has(id);
    setPending((p) => new Set(p).add(id));
    try {
      if (had) await api.del(`/discovery/favorites/${id}`);
      else await api.put(`/discovery/favorites/${id}`);
      setIds((s) => {
        const n = new Set(s);
        if (had) n.delete(id);
        else n.add(id);
        return n;
      });
      toast.push('ok', had ? t('card.favRemoved') : t('card.favAdded'));
      onChanged?.();
    } catch (e) {
      toast.push('bad', e instanceof ApiError ? e.message : t('common.actionFailed'));
    } finally {
      setPending((p) => {
        const n = new Set(p);
        n.delete(id);
        return n;
      });
    }
  };
  return { canFavorite, ids: canFavorite ? ids : NO_IDS, pending, toggle };
}

export function HeartButton({ id, name, fav }: { id: string; name: string; fav: ReturnType<typeof useFavorites> }) {
  if (!fav.canFavorite) return null;
  const on = fav.ids.has(id);
  return (
    <motion.button
      whileTap={{ scale: 0.82 }}
      className="chip"
      style={{ position: 'absolute', top: 10, right: 10, width: 44, padding: 0, justifyContent: 'center', background: 'color-mix(in oklab, var(--c-surface) 70%, transparent)' }}
      aria-pressed={on}
      aria-label={on ? t('card.favRemove', { name }) : t('card.favAdd', { name })}
      disabled={fav.pending.has(id)}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void fav.toggle(id);
      }}
    >
      <motion.svg animate={{ scale: on ? [1, 1.35, 1] : 1 }} transition={{ duration: 0.35 }} width="22" height="22" viewBox="0 0 24 24" fill={on ? 'var(--c-primary)' : 'none'} stroke={on ? 'var(--c-primary)' : 'currentColor'} strokeWidth="1.8" aria-hidden="true">
        <path d="M12 21s-7-4.4-9.3-9A5.4 5.4 0 0 1 12 6a5.4 5.4 0 0 1 9.3 6C19 16.6 12 21 12 21z" />
      </motion.svg>
    </motion.button>
  );
}

/* -------- public likes ("Yoqdi"): separate from the private favourites (heart / Sevimlilar) -------- */
function ThumbIcon({ filled }: { filled?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 10v11H3V10h4zm0 0 4-7c1.7 0 2.6 1.2 2.3 2.8L12.6 9H19a2 2 0 0 1 2 2.3l-1.3 7.6A2.5 2.5 0 0 1 17.2 21H7" />
    </svg>
  );
}

/** Read-only like count (cards, signed-out visitors). */
export function LikeCount({ count }: { count: number }) {
  return (
    <span className="tag">
      <ThumbIcon /> <span aria-hidden="true">{count}</span>
      <span className="sr-only">{t('like.count', { n: count })}</span>
    </span>
  );
}

/**
 * "Yoqdi" toggle with its public count. Optimistic: the new state shows at once and is rolled back if the
 * server refuses (branching on nothing but success/failure; the message comes from the error `code`).
 * Signed-out visitors see the count only.
 */
export function LikeButton({ card }: { card: Pick<Card, 'id' | 'display_name' | 'like_count' | 'liked_by_me'> }) {
  const { user } = useAuth();
  const toast = useToast();
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
      toast.push('bad', e instanceof ApiError ? e.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };
  const on = state.liked_by_me;
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.9 }}
      className="chip like-btn"
      aria-pressed={on}
      aria-busy={busy}
      aria-label={`${on ? t('like.remove', { name: card.display_name }) : t('like.add', { name: card.display_name })} — ${t('like.count', { n: state.like_count })}`}
      onClick={() => void toggle()}
    >
      <ThumbIcon filled={on} /> {t('like.label')} <b aria-hidden="true">{state.like_count}</b>
    </motion.button>
  );
}

/** Stars (only from reviews of completed meetings), completed meetings and likes, as one line of tags. */
export function CardStats({ card, likes = true }: { card: Card; likes?: boolean }) {
  return (
    <div className="row" style={{ gap: 6 }}>
      {card.rating != null && card.review_count > 0 ? (
        <span className="tag">
          <span aria-hidden="true">★ {card.rating.toFixed(1)} <span className="muted">({card.review_count})</span></span>
          <span className="sr-only">{t('card.ratingAria', { rating: card.rating.toFixed(1), count: card.review_count })}</span>
        </span>
      ) : (
        <span className="tag">{t('card.noRating')}</span>
      )}
      <span className="tag">{t('card.meetings', { n: card.meeting_count })}</span>
      {likes && <LikeCount count={card.like_count} />}
    </div>
  );
}

export function CompanionCardView({ card, fav }: { card: Card; fav: ReturnType<typeof useFavorites> }) {
  const price = minPrice(card);
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ type: 'spring', stiffness: 300, damping: 24 }}>
      <Link to={`/c/${card.id}`} className="glass card spot" aria-label={t('card.open', { name: card.display_name })}>
        <div style={{ position: 'relative' }}>
          <CompanionImage profileId={card.id} photo={card.photos[0]} name={card.display_name} />
          <HeartButton id={card.id} name={card.display_name} fav={fav} />
          {card.verified === true && (
            <span className="tag ok glass" style={{ position: 'absolute', left: 10, bottom: 10 }}>
              {t('card.verified')}
            </span>
          )}
        </div>
        <div className="body">
          <h3>
            {card.display_name}
            {card.age ? `, ${card.age}` : ''}
          </h3>
          {card.city && <p className="muted">{card.city}</p>}
          <CardStats card={card} />
          <div className="row" style={{ gap: 6 }}>
            {card.services.slice(0, 3).map((s) => (
              <span key={s.id} className="tag">
                {serviceLabel(s.service_code)}
              </span>
            ))}
          </div>
          {price ? <p className="price">{t('card.priceFrom', { price })}</p> : <p className="hint">{t('card.noPrices')}</p>}
        </div>
      </Link>
    </motion.div>
  );
}
