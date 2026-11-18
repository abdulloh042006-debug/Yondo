import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect, useState, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { serviceLabel } from '../lib/labels';
import { Empty } from '../ui/feedback';
import { CardStats, CompanionImage, LikeButton, minPrice, type Card, type useFavorites } from './companionParts';

/**
 * "Kartoçkalar": one companion at a time with two actions only — "Saqlaş" (adds to the private favourites)
 * and "Keyingisi" (skip, client-side). No dislike, no match (Yondo is never a dating app). Buttons are the main
 * path; the keyboard path is → / N (next) and S (save) while the deck has focus. No swipe gesture.
 */
export function CardDeck({
  items,
  fav,
  canMore,
  loadingMore,
  loadMore,
  moreError,
}: {
  items: Card[];
  fav: ReturnType<typeof useFavorites>;
  canMore: boolean;
  loadingMore: boolean;
  loadMore: () => Promise<void>;
  moreError?: string;
}) {
  const [index, setIndex] = useState(0);
  const still = useReducedMotion();
  const { user } = useAuth();
  const navigate = useNavigate();
  const card = items[index];

  // Fetch the next page shortly before the deck runs out, so "Keyingisi" never waits at a page boundary.
  useEffect(() => {
    if (canMore && !loadingMore && index >= items.length - 2) void loadMore();
  }, [index, items.length, canMore, loadingMore, loadMore]);

  const next = () => setIndex((i) => Math.min(i + 1, items.length));
  const save = () => {
    if (!card) return;
    if (!user) return navigate('/login', { state: { from: '/?view=cards' } });
    if (fav.canFavorite && !fav.ids.has(card.id)) void fav.toggle(card.id);
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'ArrowRight' || e.key.toLowerCase() === 'n') {
      e.preventDefault();
      next();
    } else if (e.key.toLowerCase() === 's') {
      e.preventDefault();
      save();
    }
  };

  if (!card) {
    if (canMore || loadingMore) return <div className="deck"><div className="skeleton" style={{ minHeight: 420 }} /></div>;
    return (
      <Empty title={t('card.end')} action={<button className="btn" onClick={() => setIndex(0)}>{t('card.restart')}</button>}>
        {moreError ?? t('card.endBody')}
      </Empty>
    );
  }
  const saved = fav.ids.has(card.id);
  const price = minPrice(card);
  const categories = [...new Set(card.services.map((s) => s.service_code))];
  return (
    <div className="deck" role="region" aria-roledescription={t('card.deckAria')} aria-label={t('card.deckAria')} tabIndex={0} onKeyDown={onKey}>
      <p className="hint" aria-live="polite">
        {t('card.position', { i: index + 1, n: items.length })}
        {canMore ? '+' : ''} · {t('card.keysHint')}
      </p>
      <AnimatePresence mode="wait" initial={false}>
        <motion.article
          key={card.id}
          className="glass deck-card"
          aria-labelledby={`deck-${card.id}`}
          initial={still ? { opacity: 0 } : { opacity: 0, x: 48, rotate: 1.5 }}
          animate={still ? { opacity: 1 } : { opacity: 1, x: 0, rotate: 0 }}
          exit={still ? { opacity: 0 } : { opacity: 0, x: -64, rotate: -2 }}
          transition={{ type: 'spring', stiffness: 320, damping: 30 }}
        >
          <CompanionImage profileId={card.id} photo={card.photos[0]} name={card.display_name} />
          <div className="body stack" style={{ padding: '16px 18px 18px', gap: 8 }}>
            <h2 id={`deck-${card.id}`} style={{ margin: 0 }}>
              <Link to={`/c/${card.id}`}>{card.display_name}</Link>
              {card.age ? `, ${card.age}` : ''}
              {card.verified === true && <span className="tag ok" style={{ marginLeft: 8, verticalAlign: 'middle' }}>{t('card.verified')}</span>}
            </h2>
            {card.city && <p className="muted" style={{ margin: 0 }}>{card.city}</p>}
            {categories.length > 0 && (
              <div className="row" style={{ gap: 6 }}>
                {categories.slice(0, 4).map((code) => <span key={code} className="tag">{serviceLabel(code)}</span>)}
              </div>
            )}
            <div className="row" style={{ gap: 6 }}>
              <CardStats card={card} likes={false} />
              <LikeButton key={card.id} card={card} />
            </div>
            {price ? <p className="price" style={{ margin: 0 }}>{t('card.priceFrom', { price })}</p> : <p className="hint" style={{ margin: 0 }}>{t('card.noPrices')}</p>}
          </div>
        </motion.article>
      </AnimatePresence>
      <div className="deck-actions">
        <motion.button
          type="button"
          whileTap={still ? undefined : { scale: 0.96 }}
          className="btn ghost"
          aria-pressed={saved}
          disabled={fav.pending.has(card.id) || (!!user && !fav.canFavorite)}
          onClick={save}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill={saved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M12 21s-7-4.4-9.3-9A5.4 5.4 0 0 1 12 6a5.4 5.4 0 0 1 9.3 6C19 16.6 12 21 12 21z" />
          </svg>
          {saved ? t('card.saved') : t('card.save')}
        </motion.button>
        <motion.button type="button" whileTap={still ? undefined : { scale: 0.96 }} className="btn" onClick={next}>
          {t('card.next')} <span aria-hidden="true">→</span>
        </motion.button>
      </div>
      {!!user && !fav.canFavorite && <p className="hint">{t('card.saveSignIn')}</p>}
    </div>
  );
}
