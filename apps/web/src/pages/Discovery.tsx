import { AnimatePresence, motion } from 'motion/react';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { toMinor } from '../lib/format';
import { SERVICE_LABELS } from '../lib/labels';
import { Empty, ErrorState } from '../ui/feedback';
import { useResource } from '../lib/useResource';
import { Select } from '../ui/form';
import { Item } from '../ui/motion';
import { Orbs, useParallax } from '../ui/Orbs';
import { CompanionCardView, useFavorites } from './companionParts';

type Page = Schemas['DiscoveryPage'];
const PAGE = 12;
const FILTER_KEYS = ['q', 'city', 'service_code', 'language', 'rating_min', 'price_max'] as const;

export function Discovery() {
  const [params, setParams] = useSearchParams();
  const [draftQ, setDraftQ] = useState(params.get('q') ?? '');
  const [priceError, setPriceError] = useState<string>();
  const par = useParallax();

  const set = (key: (typeof FILTER_KEYS)[number], value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const active = FILTER_KEYS.filter((k) => params.get(k));

  return (
    <div className="stack" style={{ gap: 24 }}>
      <motion.section className="glass hero" onPointerMove={par.onPointerMove} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7 }}>
        <Orbs sx={par.sx} sy={par.sy} />
        <span className="tag" style={{ width: 'fit-content' }}>Yondo doim yoningda</span>
        <h1>Suhbat, sayr yoki shahar bo‘ylab hamroh toping</h1>
        <p>
          Tasdiqlangan profillar, aniq xizmatlar va narxlar. Uchrashuvlar faqat jamoat joylarida, xavfsizlik vositalari
          bilan.
        </p>
        <form
          className="row"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            set('q', draftQ.trim());
          }}
        >
          <label className="sr-only" htmlFor="q">Ism yoki tavsif bo‘yicha qidirish</label>
          <input id="q" className="input" style={{ flex: '1 1 240px', maxWidth: 420 }} placeholder="Ism yoki tavsif bo‘yicha qidirish" value={draftQ} onChange={(e) => setDraftQ(e.target.value)} maxLength={128} />
          <button className="btn">Qidirish</button>
        </form>
      </motion.section>

      <section aria-label="Filtrlar" className="glass pad stack">
        <div role="group" aria-label="Xizmat turi" className="row" style={{ gap: 6 }}>
          {[['', 'Hammasi'], ...Object.entries(SERVICE_LABELS)].map(([code, label]) => {
            const on = (params.get('service_code') ?? '') === code;
            return (
              <button key={code} className="chip chip-wrap" style={on ? { background: 'transparent', color: 'var(--c-bg)' } : undefined} aria-pressed={on} onClick={() => set('service_code', code)}>
                {on && <motion.span layoutId="svc-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                {label}
              </button>
            );
          })}
        </div>
        <div className="row" style={{ alignItems: 'end' }}>
          <div style={{ flex: '1 1 160px' }} className="field">
            <label htmlFor="city">Shahar</label>
            <input id="city" key={params.get('city') ?? ''} className="input" defaultValue={params.get('city') ?? ''} onBlur={(e) => set('city', e.target.value.trim())} onKeyDown={(e) => e.key === 'Enter' && set('city', e.currentTarget.value.trim())} maxLength={128} placeholder="Toshkent" />
          </div>
          <div style={{ flex: '1 1 140px' }} className="field">
            <label htmlFor="lang">Til</label>
            <input id="lang" key={params.get('language') ?? ''} className="input" defaultValue={params.get('language') ?? ''} onBlur={(e) => set('language', e.target.value.trim())} onKeyDown={(e) => e.key === 'Enter' && set('language', e.currentTarget.value.trim())} maxLength={64} placeholder="uz, ru, en" />
          </div>
          <div style={{ flex: '1 1 160px' }} className="field">
            <label htmlFor="price">Eng yuqori narx (so‘m)</label>
            <input
              id="price" key={params.get('price_max') ?? ''}
              className="input"
              inputMode="numeric"
              aria-invalid={!!priceError}
              defaultValue={params.get('price_max') ?? ''}
              onBlur={(e) => {
                const v = e.target.value.trim();
                if (v && toMinor(v) === null) return setPriceError('Faqat raqam kiriting.');
                setPriceError(undefined);
                set('price_max', v);
              }}
              placeholder="200 000"
            />
            {priceError && <span className="err" role="alert">{priceError}</span>}
          </div>
          <div style={{ flex: '1 1 140px' }}>
            <Select label="Reyting" value={params.get('rating_min') ?? ''} onChange={(e) => set('rating_min', e.target.value)}>
              <option value="">Istalgan</option>
              {[4, 3, 2].map((n) => (
                <option key={n} value={n}>{n}+ ★</option>
              ))}
            </Select>
          </div>
        </div>
        <AnimatePresence>
          {active.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="row">
              {active.map((k) => (
                <button key={k} className="chip" onClick={() => { set(k, ''); if (k === 'q') setDraftQ(''); }}>
                  {k === 'service_code' ? (SERVICE_LABELS[params.get(k)!] ?? params.get(k)) : params.get(k)} ✕
                </button>
              ))}
              <button className="chip" onClick={() => { setParams({}, { replace: true }); setDraftQ(''); }}>Hammasini tozalash</button>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Keyed by the filters: changing them remounts Results, which resets paging cleanly. */}
      <Results key={params.toString()} params={params} onClear={() => setParams({}, { replace: true })} hasFilters={active.length > 0} />
    </div>
  );
}

function Results({ params, hasFilters, onClear }: { params: URLSearchParams; hasFilters: boolean; onClear: () => void }) {
  const fav = useFavorites();
  const priceMax = params.get('price_max');
  const max = priceMax ? toMinor(priceMax) : null;
  const base = {
    q: params.get('q'),
    city: params.get('city'),
    service_code: params.get('service_code'),
    language: params.get('language'),
    rating_min: params.get('rating_min'),
    price_max_minor: max,
    limit: PAGE,
  };
  const first = useResource((signal) => api.get<Page>('/discovery/companions', { query: { ...base, offset: 0 }, anonymous: true, signal }), []);
  const [extra, setExtra] = useState<Page['items']>([]);
  const [hasMore, setHasMore] = useState<boolean | null>(null);
  const [more, setMore] = useState(false);
  const [moreError, setMoreError] = useState<ApiError>();

  const items = [...(first.data?.items ?? []), ...extra];
  const canMore = hasMore ?? first.data?.has_more ?? false;
  const loadMore = async () => {
    setMore(true);
    setMoreError(undefined);
    try {
      const page = await api.get<Page>('/discovery/companions', { query: { ...base, offset: items.length }, anonymous: true });
      setExtra((e) => [...e, ...page.items]);
      setHasMore(page.has_more);
    } catch (e) {
      setMoreError(e instanceof ApiError ? e : new ApiError(0, 'network_error'));
    } finally {
      setMore(false);
    }
  };

  return (
    <section aria-live="polite" aria-label="Natijalar">
      {first.loading && !first.data ? (
        <div className="grid-cards">
          {Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton" style={{ minHeight: 360 }} />)}
          <span className="sr-only">Yuklanmoqda…</span>
        </div>
      ) : first.error ? (
        <ErrorState error={first.error} onRetry={first.reload} />
      ) : items.length === 0 ? (
        <Empty
          title={hasFilters ? 'Mos hamroh topilmadi' : 'Hozircha ko‘rinadigan hamroh yo‘q'}
          action={hasFilters ? <button className="btn ghost" onClick={onClear}>Filtrlarni tozalash</button> : undefined}
        >
          {hasFilters ? 'Filtrlarni o‘zgartirib ko‘ring.' : 'Profillar ariza, kontent va shaxs tekshiruvidan o‘tgandan keyingina ko‘rinadi.'}
        </Empty>
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
                {more && <span className="spinner" aria-hidden="true" />}Yana ko‘rsatish
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
