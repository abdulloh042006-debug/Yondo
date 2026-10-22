import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading } from '../ui/feedback';
import { Item } from '../ui/motion';
import { CompanionCardView, useFavorites, type Card } from './companionParts';

export function Favorites() {
  const res = useResource((signal) => api.get<Card[]>('/discovery/favorites', { signal }), []);
  const fav = useFavorites(res.reload);
  if (res.loading && !res.data) return <Loading />;
  if (res.error?.status === 403)
    return <Empty title="Sevimlilar mijozlar uchun" action={<Link className="btn" to="/account">Mijoz rolini tanlash</Link>}>Sevimlilar ro‘yxati faqat mijoz roli bilan ishlaydi.</Empty>;
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const items = res.data ?? [];
  return (
    <div className="stack" style={{ gap: 20 }}>
      <h1>Sevimlilar</h1>
      {items.length === 0 ? (
        <Empty title="Sevimlilar bo‘sh" action={<Link className="btn" to="/">Kashf qilish</Link>}>Yoqqan profillardagi yurakcha tugmasini bosing.</Empty>
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
