import { ApiError, api, errorText } from '../api';
import { useFavorites } from '../favorites';
import { useNav } from '../nav';
import { t } from '../shared';
import { Button, ErrorText, H1, Loading, P, Screen } from '../ui';
import { useResource } from '../useResource';
import { CompanionRow, type Card } from './companion';

export function FavoritesScreen() {
  const nav = useNav();
  const fav = useFavorites();
  const res = useResource(() => api.get<Card[]>('/discovery/favorites'), [fav.version]);
  if (res.loading && !res.data) {
    return (
      <Screen>
        <H1>{t('nav.favorites')}</H1>
        <Loading />
      </Screen>
    );
  }
  if (res.error instanceof ApiError && res.error.status === 403) {
    return (
      <Screen>
        <H1>{t('favorites.customersOnly')}</H1>
        <P muted>{t('favorites.customersOnlyBody')}</P>
        <Button label={t('favorites.chooseCustomer')} onPress={() => nav.switchTab('account')} />
      </Screen>
    );
  }
  const items = res.data ?? [];
  return (
    <Screen>
      <H1>{t('nav.favorites')}</H1>
      {!!res.error && (
        <>
          <ErrorText text={errorText(res.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={res.reload} />
        </>
      )}
      {res.data && items.length === 0 && (
        <>
          <P>{t('favorites.empty')}</P>
          <P muted>{t('favorites.emptyBody')}</P>
          <Button label={t('favorites.explore')} onPress={() => nav.switchTab('discover')} />
        </>
      )}
      {items.map((card) => (
        <CompanionRow key={card.id} card={card} onOpen={() => nav.push({ name: 'profile', id: card.id })} />
      ))}
    </Screen>
  );
}
