import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { formatMoney, initial } from '../lib/format';
import { serviceLabel } from '../lib/labels';
import { useToast } from '../ui/feedback';

export type Card = Schemas['CompanionCard'];
export type Photo = Schemas['DiscoveryPhoto'];

const urlCache = new Map<string, string>();
const NO_IDS: Set<string> = new Set();

/** Fetches the short-lived signed URL for a public photo; falls back to a gradient + initial. */
export function CompanionImage({ profileId, photo, name, rounded }: { profileId: string; photo?: Photo; name: string; rounded?: boolean }) {
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
  return (
    <div className="media" style={rounded ? { borderRadius: 'var(--r-md)' } : undefined}>
      {url ? <img className="img-in" onLoad={(e) => e.currentTarget.classList.add('loaded')} src={url} alt={photo?.caption || `${name} rasmi`} loading="lazy" width={photo?.width} height={photo?.height} /> : <span className="initial" aria-hidden="true">{initial(name)}</span>}
    </div>
  );
}

export function minPrice(card: Card): string | null {
  if (!card.services.length) return null;
  const s = card.services.reduce((a, b) => (b.price_minor < a.price_minor ? b : a));
  return `${formatMoney(s.price_minor, s.currency)} / ${s.unit_minutes} daq`;
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
      toast.push('ok', had ? 'Sevimlilardan olib tashlandi.' : 'Sevimlilarga qo‘shildi.');
      onChanged?.();
    } catch (e) {
      toast.push('bad', e instanceof ApiError ? e.message : 'Amal bajarilmadi.');
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
      aria-label={on ? `${name}ni sevimlilardan olib tashlash` : `${name}ni sevimlilarga qo‘shish`}
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

export function CompanionCardView({ card, fav }: { card: Card; fav: ReturnType<typeof useFavorites> }) {
  const price = minPrice(card);
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ type: 'spring', stiffness: 300, damping: 24 }}>
      <Link to={`/c/${card.id}`} className="glass card spot" aria-label={`${card.display_name} profilini ochish`}>
        <div style={{ position: 'relative' }}>
          <CompanionImage profileId={card.id} photo={card.photos[0]} name={card.display_name} />
          <HeartButton id={card.id} name={card.display_name} fav={fav} />
          {card.verified === true && (
            <span className="tag ok glass" style={{ position: 'absolute', left: 10, bottom: 10 }}>
              ✓ Shaxsi tasdiqlangan
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
              <span className="tag" aria-label={`Reyting ${card.rating.toFixed(1)}, ${card.review_count} ta sharh`}>
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
          {price ? <p className="price">dan {price}</p> : <p className="hint">Narxlar hali ko‘rsatilmagan</p>}
        </div>
      </Link>
    </motion.div>
  );
}
