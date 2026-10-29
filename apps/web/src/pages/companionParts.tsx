import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Avatar } from '../components/avatar/Avatar';
import { t } from '../i18n';
import { formatMoney, initial } from '../lib/format';
import { serviceLabel } from '../lib/labels';
import { useToast } from '../ui/feedback';
import { Icon } from '../ui/Icon';

export type Card = Schemas['CompanionCard'];
export type Photo = Schemas['DiscoveryPhoto'];

const urlCache = new Map<string, string>();
const NO_IDS: Set<string> = new Set();

/** Short-lived signed URL of a public photo (cached per photo id); null while loading, absent or unavailable. */
export function usePublicPhotoUrl(profileId: string, photo?: Photo | null): string | null {
  const [url, setUrl] = useState<string | null>(photo ? (urlCache.get(photo.id) ?? null) : null);
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
        /* storage unavailable: keep the placeholder */
      });
    return () => {
      live = false;
    };
  }, [photo, profileId]);
  return photo ? url : null;
}

/** Shows the photo; without one the geometric avatar (seeded by the profile id) stands in, with the initial while a photo loads. */
export function CompanionImage({ profileId, photo, name, rounded }: { profileId: string; photo?: Photo; name: string; rounded?: boolean }) {
  const url = usePublicPhotoUrl(profileId, photo);
  return (
    <div className="media" style={rounded ? { borderRadius: 'var(--r-md)' } : undefined}>
      {url ? (
        <img className="img-in" onLoad={(e) => e.currentTarget.classList.add('loaded')} src={url} alt={photo?.caption || t('card.photoAlt', { name })} loading="lazy" width={photo?.width} height={photo?.height} />
      ) : photo ? (
        <span className="initial" aria-hidden="true">{initial(name)}</span>
      ) : (
        <Avatar seed={profileId} size={96} className="media-avatar" />
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
      <motion.span style={{ display: 'grid' }} animate={{ scale: on ? [1, 1.35, 1] : 1 }} transition={{ duration: 0.35 }}>
        <Icon name="heart" filled={on} />
      </motion.span>
    </motion.button>
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
          <div className="spread" style={{ flexWrap: 'nowrap' }}>
            <h3>
              {card.display_name}
              {card.age ? `, ${card.age}` : ''}
            </h3>
            {card.rating != null && card.review_count > 0 && (
              <span className="tag" aria-label={t('card.ratingAria', { rating: card.rating.toFixed(1), count: card.review_count })}>
                ★ {card.rating.toFixed(1)} <span className="muted">({card.review_count})</span>
              </span>
            )}
          </div>
          {card.city && <p className="muted">{card.city}</p>}
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
