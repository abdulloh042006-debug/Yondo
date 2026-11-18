import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';

const auth = vi.hoisted(() => ({ value: { user: { id: 'u1', roles: ['customer'] } as unknown } }));
const put = vi.hoisted(() => vi.fn());
const del = vi.hoisted(() => vi.fn());
const get = vi.hoisted(() => vi.fn());
vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, put, del, get } };
});
import { ToastProvider } from '../ui/feedback';
import { CardDeck } from './CardDeck';
import { CardStats, LikeButton, useFavorites } from './companionParts';

type Card = Schemas['CompanionCard'];
const card = (id: string, extra: Partial<Card> = {}): Card =>
  ({ id, display_name: `DEMO ${id}`, age: null, bio: '', city: 'Toshkent', gender: null, interests: [], languages: [], photos: [],
    services: [{ id: `s-${id}`, service_code: 'coffee', price_minor: 100000, currency: 'UZS', unit_minutes: 60, description: '' }],
    rating: null, review_count: 0, meeting_count: 2, like_count: 5, liked_by_me: false, verified: false, ...extra }) as Card;

beforeEach(() => {
  put.mockReset();
  del.mockReset();
  get.mockReset();
  get.mockResolvedValue([]);
  auth.value = { user: { id: 'u1', roles: ['customer'] } };
});

describe('"Yoqdi" (public like, separate from favourites)', () => {
  it('signed out: shows the count only', () => {
    auth.value = { user: null };
    render(<ToastProvider><LikeButton card={card('a')} /></ToastProvider>);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByText(t('like.count', { n: 5 }))).toBeInTheDocument();
  });
  it('optimistic +1, then the server state', async () => {
    let resolve!: (v: unknown) => void;
    put.mockReturnValue(new Promise((r) => (resolve = r)));
    render(<ToastProvider><LikeButton card={card('a')} /></ToastProvider>);
    const btn = screen.getByRole('button');
    expect(btn).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(btn);
    expect(btn).toHaveAttribute('aria-pressed', 'true');
    expect(btn).toHaveTextContent('6');
    expect(put).toHaveBeenCalledWith('/discovery/companions/a/like');
    await act(async () => resolve({ profile_id: 'a', like_count: 9, liked_by_me: true }));
    expect(btn).toHaveTextContent('9');
  });
  it('rolls back and explains by error code when the server refuses', async () => {
    put.mockRejectedValue(new ApiError(409, 'like_own_profile'));
    render(<ToastProvider><LikeButton card={card('a')} /></ToastProvider>);
    await act(async () => fireEvent.click(screen.getByRole('button')));
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button')).toHaveTextContent('5');
    expect(await screen.findByText(t('err.like_own_profile'))).toBeInTheDocument();
  });
  it('unlike sends DELETE', async () => {
    del.mockResolvedValue({ profile_id: 'a', like_count: 4, liked_by_me: false });
    render(<ToastProvider><LikeButton card={card('a', { liked_by_me: true })} /></ToastProvider>);
    await act(async () => fireEvent.click(screen.getByRole('button')));
    expect(del).toHaveBeenCalledWith('/discovery/companions/a/like');
    expect(screen.getByRole('button')).toHaveTextContent('4');
  });
});

describe('stars only from reviews of completed meetings', () => {
  it('"Hali baho yöq" when there are none; stars + meetings otherwise', () => {
    const { rerender } = render(<CardStats card={card('a')} />);
    expect(screen.getByText(t('card.noRating'))).toBeInTheDocument();
    expect(screen.getByText(t('card.meetings', { n: 2 }))).toBeInTheDocument();
    rerender(<CardStats card={card('a', { rating: 4.5, review_count: 3 })} />);
    expect(screen.queryByText(t('card.noRating'))).toBeNull();
    expect(screen.getByText(t('card.ratingAria', { rating: '4.5', count: 3 }))).toBeInTheDocument();
  });
});

function Deck({ items }: { items: Card[] }) {
  const fav = useFavorites();
  return <CardDeck items={items} fav={fav} canMore={false} loadingMore={false} loadMore={async () => {}} />;
}

describe('Kartoçkalar', () => {
  const mount = (items: Card[]) => render(<MemoryRouter><ToastProvider><Deck items={items} /></ToastProvider></MemoryRouter>);
  it('Keyingisi shows the next card; no dislike or match controls', async () => {
    mount([card('a'), card('b')]);
    expect(screen.getByRole('heading', { name: /DEMO a/ })).toBeInTheDocument();
    expect(screen.queryByText(/dislike|match/i)).toBeNull();
    await act(async () => fireEvent.click(screen.getByRole('button', { name: new RegExp(t('card.next')) })));
    expect(await screen.findByRole('heading', { name: /DEMO b/ })).toBeInTheDocument();
  });
  it('Saqlaş adds to favourites (PUT /discovery/favorites/{id}); the deck stays on the card', async () => {
    put.mockResolvedValue(undefined);
    mount([card('a'), card('b')]);
    await act(async () => fireEvent.click(screen.getByRole('button', { name: new RegExp(t('card.save')) })));
    expect(put).toHaveBeenCalledWith('/discovery/favorites/a');
    expect(screen.getByRole('button', { name: new RegExp(t('card.saved')) })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: /DEMO a/ })).toBeInTheDocument();
  });
  it('keyboard: → / N next, S save; the end offers a restart', async () => {
    put.mockResolvedValue(undefined);
    mount([card('a')]);
    const deck = screen.getByRole('region', { name: t('card.deckAria') });
    await act(async () => fireEvent.keyDown(deck, { key: 's' }));
    expect(put).toHaveBeenCalledWith('/discovery/favorites/a');
    await act(async () => fireEvent.keyDown(deck, { key: 'ArrowRight' }));
    expect(await screen.findByText(t('card.end'))).toBeInTheDocument();
    await act(async () => fireEvent.click(screen.getByRole('button', { name: t('card.restart') })));
    expect(await screen.findByRole('heading', { name: /DEMO a/ })).toBeInTheDocument();
  });
});
