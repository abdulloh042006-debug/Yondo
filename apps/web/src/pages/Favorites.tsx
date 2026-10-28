import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { t } from '../i18n';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading } from '../ui/feedback';
import { Item } from '../ui/motion';
import { CompanionCardView, useFavorites, type Card } from './companionParts';

export function Favorites() {
  const res = useResource((signal) => api.get<Card[]>('/discovery/favorites', { signal }), []);
  const fav = useFavorites(res.reload);
  if (res.loading && !res.data) return <Loading />;
  if (res.error?.status === 403)
    return <Empty title={t('favorites.customersOnly')} action={<Link className="btn" to="/account">{t('favorites.chooseCustomer')}</Link>}>{t('favorites.customersOnlyBody')}</Empty>;
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const items = res.data ?? [];
  return (
    <div className="stack" style={{ gap: 20 }}>
      <h1>{t('nav.favorites')}</h1>
      {items.length === 0 ? (
        <Empty title={t('favorites.empty')} action={<Link className="btn" to="/">{t('favorites.explore')}</Link>}>{t('favorites.emptyBody')}</Empty>
      ) : (
        <div className="grid-cards">
          {items.map((c, i) => (
            <Item key={c.id} index={i}><CompanionCardView card={c} fav={fav} /></Item>
          ))}
        </div>
      )}
    </div>
  );
}
