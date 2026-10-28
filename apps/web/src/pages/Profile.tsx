import { motion } from 'motion/react';
import { useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { formatMoney } from '../lib/format';
import { serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { Dialog, Empty, ErrorState, Loading, useToast } from '../ui/feedback';
import { Field, Select } from '../ui/form';
import { Item, Reveal } from '../ui/motion';
import { CompanionImage, HeartButton, useFavorites, type Card } from './companionParts';

export function Profile() {
  const { id = '' } = useParams();
  const res = useResource((signal) => api.get<Card>(`/discovery/companions/${id}`, { anonymous: true, signal }), [id]);
  const fav = useFavorites();
  const [booking, setBooking] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  if (res.loading && !res.data) return <Loading rows={3} />;
  if (res.error?.status === 404)
    return (
      <Empty title={t('profile.notFound')} action={<Link className="btn ghost" to="/">{t('profile.backToDiscover')}</Link>}>
        {t('profile.notFoundBody')}
      </Empty>
    );
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const c = res.data!;
  const isCustomer = !!user?.roles.includes('customer');

  return (
    <div className="stack" style={{ gap: 22 }}>
      <Link to="/" className="chip" style={{ width: 'fit-content', textDecoration: 'none' }}>{t('profile.back')}</Link>
      <div className="profile-grid">
        <Reveal>
          <div className="stack">
            <div style={{ position: 'relative' }} className="glass tight">
              <CompanionImage profileId={c.id} photo={c.photos[0]} name={c.display_name} />
              <HeartButton id={c.id} name={c.display_name} fav={fav} />
            </div>
            {c.photos.length > 1 && (
              <div className="gallery">
                {c.photos.slice(1).map((p) => (
                  <CompanionImage key={p.id} profileId={c.id} photo={p} name={c.display_name} rounded />
                ))}
              </div>
            )}
            {c.photos.length === 0 && <p className="hint">{t('profile.noPhotos')}</p>}
          </div>
        </Reveal>

        <div className="stack" style={{ gap: 18 }}>
          <Reveal>
            <div className="glass pad stack">
              <div className="row">
                <h1>{c.display_name}</h1>
                {c.verified === true && <span className="tag ok">{t('card.verified')}</span>}
              </div>
              <p className="muted">
                {[c.age ? t('profile.ageYears', { n: c.age }) : null, c.city, c.gender].filter(Boolean).join(' · ') || t('profile.noPersonal')}
              </p>
              {c.rating != null && c.review_count > 0 ? (
                <p><span className="tag">★ {c.rating.toFixed(1)}</span> <span className="muted">{t('profile.reviews', { count: c.review_count })}</span></p>
              ) : (
                <p className="hint">{t('profile.noReviews')}</p>
              )}
              {c.bio ? <p style={{ whiteSpace: 'pre-line' }}>{c.bio}</p> : <p className="hint">{t('profile.noBio')}</p>}
            </div>
          </Reveal>

          <Reveal delay={0.05}>
            <div className="bento">
              <div className="glass pad stack tight">
                <h3>{t('profile.languages')}</h3>
                <div className="row" style={{ gap: 6 }}>
                  {c.languages.length ? c.languages.map((l) => <span key={l} className="tag">{l}</span>) : <span className="hint">{t('profile.notSpecified')}</span>}
                </div>
              </div>
              <div className="glass pad stack tight">
                <h3>{t('profile.interests')}</h3>
                <div className="row" style={{ gap: 6 }}>
                  {c.interests.length ? c.interests.map((l) => <span key={l} className="tag">{l}</span>) : <span className="hint">{t('profile.notSpecified')}</span>}
                </div>
              </div>
            </div>
          </Reveal>

          <section aria-labelledby="svc" className="stack">
            <h2 id="svc">{t('profile.services')}</h2>
            {c.services.length === 0 && <p className="hint">{t('profile.noServices')}</p>}
            {c.services.map((s, i) => (
              <Item key={s.id} index={i}>
                <div className="glass pad tight spread">
                  <div>
                    <h3>{serviceLabel(s.service_code)}</h3>
                    {s.description && <p className="muted">{s.description}</p>}
                  </div>
                  <p className="price">{formatMoney(s.price_minor, s.currency)} <span className="muted">/ {t('common.minutesShort', { n: s.unit_minutes })}</span></p>
                </div>
              </Item>
            ))}
            <p className="hint">{t('profile.availabilityNote')}</p>
          </section>
        </div>
      </div>

      {/* Portal: the page transition leaves a CSS filter on its wrapper, which would make `position: fixed`
          relative to the page instead of the viewport (the bar would scroll away or sit behind the dock). */}
      {createPortal(
        <div className="book-bar glass-bar">
          <div>
            <b>{c.display_name}</b>
            <p className="hint">{c.services.length ? t('profile.bookNote') : t('profile.noServicesShort')}</p>
          </div>
          <motion.div whileTap={{ scale: 0.96 }}>
            {!user ? (
              <button className="btn" onClick={() => navigate('/login', { state: { from: `/c/${c.id}` } })}>{t('profile.book')}</button>
            ) : isCustomer ? (
              <button className="btn" disabled={!c.services.length} onClick={() => setBooking(true)}>{t('profile.book')}</button>
            ) : (
              <Link className="btn ghost" to="/account">{t('profile.chooseCustomer')}</Link>
            )}
          </motion.div>
        </div>,
        document.body,
      )}
      <BookingDialog card={c} open={booking} onClose={() => setBooking(false)} />
    </div>
  );
}

function BookingDialog({ card, open, onClose }: { card: Card; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [serviceId, setServiceId] = useState(card.services[0]?.id ?? '');
  const [when, setWhen] = useState('');
  const [units, setUnits] = useState(1);
  const [place, setPlace] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const [local, setLocal] = useState<Record<string, string>>({});
  const service = card.services.find((s) => s.id === serviceId) ?? card.services[0];
  if (!service) return null;
  const minutes = service.unit_minutes * units;
  const estimate = service.price_minor * units;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problems: Record<string, string> = {};
    // The picker yields wall-clock time; Uzbekistan is UTC+5 all year, so send an explicit instant.
    const start = when ? new Date(`${when}:00+05:00`) : null;
    if (!start || Number.isNaN(start.getTime())) problems.when = t('book.errWhen');
    else if (start.getTime() < Date.now()) problems.when = t('err.booking_start_in_past');
    if (place.trim().length < 3) problems.place = t('book.errPlace');
    setLocal(problems);
    if (Object.keys(problems).length || !start) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.post<Schemas['BookingResponse']>('/bookings', {
        service_id: service.id,
        starts_at: start.toISOString(),
        duration_minutes: minutes,
        meeting_place: place.trim(),
        timezone: 'Asia/Tashkent',
      });
      toast.push('ok', t('book.sent'));
      onClose();
      navigate('/bookings');
    } catch (error) {
      setErr(error instanceof ApiError ? error : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} title={t('book.title', { name: card.display_name })} onClose={busy ? () => {} : onClose}>
      <form className="stack" onSubmit={submit} noValidate>
        <Select label={t('book.service')} value={service.id} onChange={(e) => { setServiceId(e.target.value); setUnits(1); }}>
          {card.services.map((s) => (
            <option key={s.id} value={s.id}>{serviceLabel(s.service_code)} — {formatMoney(s.price_minor, s.currency)} / {t('common.minutesShort', { n: s.unit_minutes })}</option>
          ))}
        </Select>
        <Field label={t('book.start')} type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} error={local.when} />
        <Select label={t('book.duration')} value={units} onChange={(e) => setUnits(Number(e.target.value))}>
          {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{t('book.minutesLong', { n: service.unit_minutes * n })}</option>)}
        </Select>
        <Field label={t('book.place')} value={place} maxLength={512} onChange={(e) => setPlace(e.target.value)} error={local.place} hint={t('book.placeHint')} />
        <p className="banner">
          {t('book.estimateBefore')}<b>{formatMoney(estimate, service.currency)}</b>{t('book.estimateAfter')}
        </p>
        {err && <p className="err" role="alert">{err.message}</p>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button type="button" className="btn ghost" onClick={onClose} disabled={busy}>{t('common.cancel')}</button>
          <button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('book.send')}</button>
        </div>
      </form>
    </Dialog>
  );
}
