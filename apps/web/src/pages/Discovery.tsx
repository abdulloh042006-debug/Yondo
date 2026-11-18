import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t, type Key } from '../i18n';
import { toMinor } from '../lib/format';
import { SERVICE_LABELS } from '../lib/labels';
import { Dialog, Empty, ErrorState } from '../ui/feedback';
import { introReady } from '../ui/Intro';
import { useResource } from '../lib/useResource';
import { Select } from '../ui/form';
import { Item } from '../ui/motion';
import { Orbs, useParallax } from '../ui/Orbs';
import { CardDeck } from './CardDeck';
import { CompanionCardView, useFavorites } from './companionParts';

type Page = Schemas['DiscoveryPage'];
export type Card = Schemas['CompanionCard'];
const PAGE = 12;
/** Filters shown as chips. `sort` and `view` are not filters: they never narrow the list. */
const FILTER_KEYS = ['q', 'city', 'service_code', 'language', 'rating_min', 'price_max'] as const;
type FilterKey = (typeof FILTER_KEYS)[number];
/** The sort orders the API offers (`/discovery/companions?sort=`); stars only come from reviews of completed meetings. */
export const SORTS = ['default', 'rating', 'meetings', 'likes'] as const;
const STARS = ['4.5', '4', '3'];

export function Discovery() {
  const [params, setParams] = useSearchParams();
  const [draftQ, setDraftQ] = useState(params.get('q') ?? '');
  const [sheet, setSheet] = useState(false);
  const { user } = useAuth();
  const par = useParallax();

  // Built from the live URL, not this render's `params`: React Router commits navigations in a transition, so a
  // fast second change (clear all, then a new sort) would otherwise start from a stale copy and bring filters back.
  const live = () => new URLSearchParams(window.location.search);
  const update = (changes: Record<string, string>) => {
    const next = live();
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next, { replace: true });
  };
  const active = FILTER_KEYS.filter((k) => params.get(k));
  const sort = (SORTS as readonly string[]).includes(params.get('sort') ?? '') ? params.get('sort')! : 'default';
  const view = params.get('view') === 'cards' ? 'cards' : 'list';
  const clearAll = () => {
    const now = live();
    const next = new URLSearchParams();
    if (now.get('view')) next.set('view', now.get('view')!);
    if (now.get('sort')) next.set('sort', now.get('sort')!);
    setParams(next, { replace: true });
    setDraftQ('');
  };
  const chipLabel = (k: FilterKey): string => {
    const v = params.get(k)!;
    if (k === 'service_code') return SERVICE_LABELS[v] ?? v;
    if (k === 'rating_min') return `${v}+ ★`;
    return v;
  };
  // Results remount when what is fetched changes (filters, sort, who is signed in), not when the view mode does.
  const fetchKey = new URLSearchParams(params);
  fetchKey.delete('view');

  return (
    <div className="stack" style={{ gap: 24 }}>
      <motion.section className="glass hero" onPointerMove={par.onPointerMove} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7 }}>
        <Orbs sx={par.sx} sy={par.sy} />
        <span className="tag" style={{ width: 'fit-content' }}>{t('discovery.tag')}</span>
        <h1>{t('discovery.h1')}</h1>
        <p>{t('discovery.lead')}</p>
        <form
          className="row"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: draftQ.trim() });
          }}
        >
          <label className="sr-only" htmlFor="q">{t('discovery.searchLabel')}</label>
          <input id="q" className="input" style={{ flex: '1 1 240px', maxWidth: 420 }} placeholder={t('discovery.searchLabel')} value={draftQ} onChange={(e) => setDraftQ(e.target.value)} maxLength={128} />
          <button className="btn">{t('discovery.search')}</button>
        </form>
      </motion.section>

      <section aria-label={t('discovery.filters')} className="glass pad stack">
        <div className="toolbar">
          <button type="button" className="btn ghost" aria-haspopup="dialog" onClick={() => setSheet(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M7 12h10M10 18h4" />
            </svg>
            {active.length ? t('discovery.filtersCount', { n: active.length }) : t('discovery.filters')}
          </button>
          <div style={{ flex: '1 1 180px', maxWidth: 260 }}>
            <Select label={t('discovery.sort')} value={sort} onChange={(e) => update({ sort: e.target.value === 'default' ? '' : e.target.value })}>
              {SORTS.map((s) => (
                <option key={s} value={s}>{t(`discovery.sort.${s}` as Key)}</option>
              ))}
            </Select>
          </div>
          <div className="seg" role="group" aria-label={t('discovery.view')}>
            {(['list', 'cards'] as const).map((v) => (
              <button key={v} type="button" className="chip" aria-pressed={view === v} onClick={() => update({ view: v === 'list' ? '' : v })}>
                {t(`discovery.view.${v}`)}
              </button>
            ))}
          </div>
        </div>
        <AnimatePresence>
          {active.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="row">
              {active.map((k) => (
                <button key={k} type="button" className="chip" aria-label={t('discovery.chipRemove', { label: chipLabel(k) })} onClick={() => { update({ [k]: '' }); if (k === 'q') setDraftQ(''); }}>
                  {chipLabel(k)} <span aria-hidden="true">✕</span>
                </button>
              ))}
              <button type="button" className="chip" onClick={clearAll}>{t('discovery.clearAll')}</button>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <Dialog open={sheet} title={t('discovery.filters')} onClose={() => setSheet(false)}>
        <FilterSheet
          params={params}
          onApply={(changes) => {
            update(changes);
            if ('q' in changes) setDraftQ(changes.q);
            setSheet(false);
          }}
          onClear={() => {
            clearAll();
            setSheet(false);
          }}
          onClose={() => setSheet(false)}
        />
      </Dialog>

      <Results key={`${fetchKey.toString()}|${user?.id ?? ''}`} params={params} view={view} signedIn={!!user} onClear={clearAll} hasFilters={active.length > 0} />
    </div>
  );
}

/** The filter sheet edits a draft; nothing is fetched until "Natijalarni körsatiş". */
function FilterSheet({ params, onApply, onClear, onClose }: { params: URLSearchParams; onApply: (c: Record<string, string>) => void; onClear: () => void; onClose: () => void }) {
  const [service, setService] = useState(params.get('service_code') ?? '');
  const [stars, setStars] = useState(params.get('rating_min') ?? '');
  const [city, setCity] = useState(params.get('city') ?? '');
  const [language, setLanguage] = useState(params.get('language') ?? '');
  const [price, setPrice] = useState(params.get('price_max') ?? '');
  const [sort, setSort] = useState(params.get('sort') ?? 'default');
  const priceError = price.trim() && toMinor(price.trim()) === null ? t('discovery.numbersOnly') : undefined;
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (priceError) return;
        onApply({ service_code: service, rating_min: stars, city: city.trim(), language: language.trim(), price_max: price.trim(), sort: sort === 'default' ? '' : sort });
      }}
    >
      <fieldset className="stack tight" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">{t('discovery.serviceType')}</legend>
        <div className="row" style={{ gap: 6 }}>
          {[['', t('discovery.all')], ...Object.entries(SERVICE_LABELS)].map(([code, label]) => (
            <button key={code} type="button" className="chip" aria-pressed={service === code} onClick={() => setService(code)}>
              {label}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="stack tight" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">{t('discovery.minStars')}</legend>
        <div className="row" style={{ gap: 6 }}>
          {['', ...STARS].map((v) => (
            <button key={v} type="button" className="chip" aria-pressed={stars === v} onClick={() => setStars(v)}>
              {v ? `${v}+ ★` : t('discovery.anyRating')}
            </button>
          ))}
        </div>
        <span className="hint">{t('discovery.starsNote')}</span>
      </fieldset>
      <fieldset className="stack tight" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">{t('discovery.sort')}</legend>
        <div className="row" style={{ gap: 6 }}>
          {SORTS.map((s) => (
            <button key={s} type="button" className="chip" aria-pressed={sort === s} onClick={() => setSort(s)}>
              {t(`discovery.sort.${s}` as Key)}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="bento">
        <div className="field">
          <label htmlFor="f-city">{t('common.city')}</label>
          <input id="f-city" className="input" value={city} onChange={(e) => setCity(e.target.value)} maxLength={128} placeholder="Toshkent" />
        </div>
        <div className="field">
          <label htmlFor="f-lang">{t('settings.language')}</label>
          <input id="f-lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value)} maxLength={64} placeholder="uz, ru, en" />
        </div>
        <div className="field">
          <label htmlFor="f-price">{t('discovery.maxPrice')}</label>
          <input id="f-price" className="input" inputMode="numeric" aria-invalid={!!priceError} aria-describedby={priceError ? 'f-price-err' : undefined} value={price} onChange={(e) => setPrice(e.target.value)} placeholder="200 000" />
          {priceError && <span id="f-price-err" className="err" role="alert">{priceError}</span>}
        </div>
      </div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <button type="button" className="btn ghost" onClick={onClear}>{t('discovery.clearAll')}</button>
        <div className="row">
          <button type="button" className="btn ghost" onClick={onClose}>{t('discovery.close')}</button>
          <button className="btn" disabled={!!priceError}>{t('discovery.apply')}</button>
        </div>
      </div>
    </form>
  );
}

function Results({ params, view, signedIn, hasFilters, onClear }: { params: URLSearchParams; view: 'list' | 'cards'; signedIn: boolean; hasFilters: boolean; onClear: () => void }) {
  const fav = useFavorites();
  const priceMax = params.get('price_max');
  const max = priceMax ? toMinor(priceMax) : null;
  const sort = params.get('sort');
  const base = {
    q: params.get('q'),
    city: params.get('city'),
    service_code: params.get('service_code'),
    language: params.get('language'),
    rating_min: params.get('rating_min'),
    price_max_minor: max,
    sort: sort && (SORTS as readonly string[]).includes(sort) ? sort : null,
    limit: PAGE,
  };
  // Signed in: the token is sent so each card carries `liked_by_me`; discovery stays public otherwise.
  const first = useResource((signal) => api.get<Page>('/discovery/companions', { query: { ...base, offset: 0 }, anonymous: !signedIn, signal }), []);
  // The opening animation leaves when the first list has arrived or failed; pictures are not waited for.
  useEffect(() => {
    if (!first.loading) introReady();
  }, [first.loading]);
  const [extra, setExtra] = useState<Page['items']>([]);
  const [hasMore, setHasMore] = useState<boolean | null>(null);
  const [more, setMore] = useState(false);
  const [moreError, setMoreError] = useState<ApiError>();

  const items = [...(first.data?.items ?? []), ...extra];
  const canMore = hasMore ?? first.data?.has_more ?? false;
  const loadMore = async () => {
    if (more) return;
    setMore(true);
    setMoreError(undefined);
    try {
      const page = await api.get<Page>('/discovery/companions', { query: { ...base, offset: items.length }, anonymous: !signedIn });
      setExtra((e) => [...e, ...page.items]);
      setHasMore(page.has_more);
    } catch (e) {
      setMoreError(e instanceof ApiError ? e : new ApiError(0, 'network_error'));
    } finally {
      setMore(false);
    }
  };

  return (
    <section aria-live="polite" aria-label={t('discovery.results')}>
      {first.loading && !first.data ? (
        <div className="grid-cards">
          {Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton" style={{ minHeight: 360 }} />)}
          <span className="sr-only">{t('common.loading')}…</span>
        </div>
      ) : first.error ? (
        <ErrorState error={first.error} onRetry={first.reload} />
      ) : items.length === 0 ? (
        <Empty
          title={hasFilters ? t('discovery.noMatch') : t('discovery.noneVisible')}
          action={hasFilters ? <button className="btn ghost" onClick={onClear}>{t('discovery.clearFilters')}</button> : undefined}
        >
          {hasFilters ? t('discovery.tryChange') : t('discovery.visibleAfter')}
        </Empty>
      ) : view === 'cards' ? (
        <CardDeck items={items} fav={fav} canMore={canMore} loadingMore={more} loadMore={loadMore} moreError={moreError?.message} />
      ) : (
        <>
          <div className="grid-cards">
            {items.map((c, i) => (
              <Item key={c.id} index={i % PAGE}>
                <CompanionCardView card={c} fav={fav} />
              </Item>
            ))}
          </div>
          {moreError && <p className="err" role="alert" style={{ marginTop: 12 }}>{moreError.message}</p>}
          {canMore && (
            <div className="row" style={{ justifyContent: 'center', marginTop: 24 }}>
              <button className="btn ghost" disabled={more} onClick={() => void loadMore()}>
                {more && <span className="spinner" aria-hidden="true" />}{t('discovery.more')}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
