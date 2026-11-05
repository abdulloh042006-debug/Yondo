import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { hasKey, t, type Key } from '../i18n';
import { formatInstant, formatMoney } from '../lib/format';
import { BOOKING_STATUS, roleLabel, serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { TextArea } from '../ui/form';
import { Reveal } from '../ui/motion';
import { ReportDialog } from '../ui/ReportDialog';
import { SosButton } from '../ui/Sos';

type Booking = Schemas['BookingResponse'];
type Payment = Schemas['PaymentResponse'];
type Meeting = Schemas['MeetingState'];
type Message = Schemas['ChatMessageResponse'];
type Review = Schemas['ReviewRead'];

const CHAT_OPEN = ['pending', 'accepted', 'confirmed', 'active'];
const MEETING_STEP = ['confirmed', 'active', 'completed'];
const PAYMENT_STATUS = ['creating', 'pending', 'succeeded', 'failed'];

/** One booking end to end: payment → meeting → chat → review, plus safety tools. Every rule is the server's. */
export function BookingDetail() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const res = useResource((signal) => api.get<Booking>(`/bookings/${id}`, { signal }), [id]);
  const [reporting, setReporting] = useState(false);

  if (res.loading && !res.data) return <Loading />;
  if (res.error) {
    return res.error.status === 404 ? (
      <Empty title={t('bd.notFound')} action={<Link className="btn" to="/bookings">{t('bd.back')}</Link>} />
    ) : (
      <ErrorState error={res.error} onRetry={res.reload} />
    );
  }
  const b = res.data;
  if (!b || !user) return null;
  const mine = b.customer_id === user.id;

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 820, margin: '0 auto', width: '100%' }}>
      <Link to="/bookings" className="hint">{t('bd.back')}</Link>
      <Reveal>
        <section className="glass pad stack" aria-labelledby="bd-h">
          <div className="spread">
            <h1 id="bd-h" style={{ margin: 0 }}>{serviceLabel(b.service_code)}</h1>
            <StatusTag map={BOOKING_STATUS} value={b.status} />
          </div>
          <dl className="kv">
            <dt>{t('common.time')}</dt><dd>{formatInstant(b.starts_at)} — {formatInstant(b.ends_at)}</dd>
            <dt>{t('common.place')}</dt><dd>{b.meeting_place}</dd>
            <dt>{t('common.price')}</dt><dd>{formatMoney(b.price_minor, b.currency)}</dd>
            <dt>{t('bookings.yourRole')}</dt><dd>{roleLabel(mine ? 'customer' : 'companion')}</dd>
          </dl>
        </section>
      </Reveal>
      <PaymentSection booking={b} isCustomer={mine} onChanged={res.reload} />
      <MeetingSection booking={b} onChanged={res.reload} />
      <ChatSection booking={b} userId={user.id} />
      <ReviewSection booking={b} userId={user.id} />
      <section className="glass pad stack" aria-labelledby="bd-safe-h">
        <h2 id="bd-safe-h">{t('bd.safety.title')}</h2>
        <div className="row">
          <button className="btn ghost" onClick={() => setReporting(true)}>{t('reportForm.action')}</button>
          <SosButton className="btn danger" />
        </div>
      </section>
      {reporting && <ReportDialog bookingId={b.id} aboutCompanion={mine} onClose={() => setReporting(false)} />}
    </div>
  );
}

/** A stable key per booking so a retried click never creates a second payment (server requires it). */
function idempotencyKey(bookingId: string): string {
  const k = `yondo.pay.${bookingId}`;
  try {
    const existing = sessionStorage.getItem(k);
    if (existing) return existing;
    const fresh = crypto.randomUUID();
    sessionStorage.setItem(k, fresh);
    return fresh;
  } catch {
    return `${bookingId}-${Date.now()}`;
  }
}

function PaymentSection({ booking, isCustomer, onChanged }: { booking: Booking; isCustomer: boolean; onChanged: () => void }) {
  const payments = useResource((signal) => api.get<Payment[]>(`/payments/bookings/${booking.id}`, { signal }), [booking.id, booking.status]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const latest = payments.data?.[payments.data.length - 1];
  const pay = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      const p = await api.post<Payment>(`/payments/bookings/${booking.id}`, undefined, { headers: { 'Idempotency-Key': idempotencyKey(booking.id) } });
      payments.setData([...(payments.data ?? []), p]);
    } catch (error) {
      const e = error instanceof ApiError ? error : new ApiError(0, 'network_error');
      setErr(e);
      if (e.code === 'booking_expired') onChanged();
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="glass pad stack" aria-labelledby="bd-pay-h">
      <h2 id="bd-pay-h">{t('bd.pay.title')}</h2>
      <p className="hint">{t('bd.pay.note')}</p>
      {latest && PAYMENT_STATUS.includes(latest.status) && (
        <p>{t('bd.pay.status', { status: t(`payment.status.${latest.status}` as Key) })}</p>
      )}
      {latest?.checkout_url && booking.status === 'accepted' && (
        <>
          <p className="banner">{t('bd.pay.waiting')}</p>
          <a className="btn" href={latest.checkout_url} rel="noopener">{t('bd.pay.open')}</a>
        </>
      )}
      {booking.status === 'accepted' ? (
        isCustomer ? (
          !latest?.checkout_url && <div><button className="btn" disabled={busy} onClick={() => void pay()}>{busy && <span className="spinner" aria-hidden="true" />}{t('bd.pay.button')}</button></div>
        ) : (
          <p className="muted">{t('bd.pay.customerOnly')}</p>
        )
      ) : (
        !['confirmed', 'active', 'completed'].includes(booking.status) && <p className="muted">{t('bd.pay.notNow')}</p>
      )}
      {/* 503 = provider/config unavailable: shown as such, never as "declined". */}
      {err && <p className={err.unavailable ? 'banner' : 'err'} role="alert">{err.message}</p>}
    </section>
  );
}

function MeetingSection({ booking, onChanged }: { booking: Booking; onChanged: () => void }) {
  const open = MEETING_STEP.includes(booking.status);
  const state = useResource(
    (signal) => (open ? api.get<Meeting>(`/meetings/bookings/${booking.id}`, { signal }) : Promise.resolve(undefined)),
    [booking.id, booking.status, open],
  );
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [ended, setEnded] = useState(false);
  const act = async (step: 'check-in' | 'start' | 'end') => {
    setBusy(true);
    try {
      const next = await api.post<Meeting>(`/meetings/bookings/${booking.id}/${step}`);
      state.setData(next);
      if (step === 'end') setEnded(true);
      if (next.booking_status !== booking.status) onChanged();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };
  const m = state.data;
  return (
    <section className="glass pad stack" aria-labelledby="bd-meet-h">
      <h2 id="bd-meet-h">{t('bd.meet.title')}</h2>
      {!open ? (
        <p className="muted">{t('bd.meet.notYet')}</p>
      ) : booking.status === 'completed' ? (
        <p>{t('bd.meet.done')}</p>
      ) : !m ? (
        <Loading rows={1} />
      ) : (
        <>
          <p className="hint">{t('bd.meet.note')}</p>
          <p role="status">{t('bd.meet.arrived', { n: m.arrived_count })}</p>
          <div className="row">
            {booking.status === 'confirmed' && (
              <>
                <button className="btn" disabled={busy} onClick={() => void act('check-in')}>{t('bd.meet.checkIn')}</button>
                <button className="btn ghost" disabled={busy || m.arrived_count < 2} onClick={() => void act('start')}>{t('bd.meet.start')}</button>
              </>
            )}
            {booking.status === 'active' && (
              <button className="btn" disabled={busy || ended} onClick={() => void act('end')}>{t('bd.meet.end')}</button>
            )}
          </div>
          {ended && <p className="hint">{t('bd.meet.ended')}</p>}
        </>
      )}
    </section>
  );
}

function systemText(code: string | null | undefined): string {
  const key = `sys.${code ?? ''}`;
  return hasKey(key) ? t(key) : t('bd.chat.system');
}

function ChatSection({ booking, userId }: { booking: Booking; userId: string }) {
  const res = useResource((signal) => api.get<Message[]>(`/chat/bookings/${booking.id}/messages`, { query: { limit: 50 }, signal }), [booking.id]);
  const toast = useToast();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const writable = CHAT_OPEN.includes(booking.status);
  const reload = res.reload;
  const endRef = useRef<HTMLLIElement>(null);
  const count = res.data?.length ?? 0;

  // Light polling while the page is open (the realtime socket is not wired into the web client).
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') reload();
    }, 8000);
    return () => window.clearInterval(timer);
  }, [reload]);
  useEffect(() => {
    if (count) {
      void api.post(`/chat/bookings/${booking.id}/read`).catch(() => {});
      endRef.current?.scrollIntoView?.({ block: 'nearest' });
    }
  }, [booking.id, count]);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    setBusy(true);
    try {
      const m = await api.post<Message>(`/chat/bookings/${booking.id}/messages`, { body, kind: 'text' });
      res.setData([...(res.data ?? []), m]);
      setText('');
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass pad stack" aria-labelledby="bd-chat-h">
      <h2 id="bd-chat-h">{t('bd.chat.title')}</h2>
      {res.loading && !res.data ? (
        <Loading rows={2} />
      ) : res.error ? (
        <ErrorState error={res.error} onRetry={res.reload} />
      ) : !res.data?.length ? (
        <p className="muted">{t('bd.chat.empty')}</p>
      ) : (
        <ul className="chat" aria-live="polite">
          {res.data.map((m) => {
            const who = m.sender_id === null ? 'system' : m.sender_id === userId ? 'me' : 'them';
            return (
              <li key={m.id} className={`chat-msg ${who}`}>
                <span className="hint">
                  {who === 'system' ? t('bd.chat.system') : who === 'me' ? t('bd.chat.you') : t('bd.chat.them')} · {formatInstant(m.created_at)}
                </span>
                <span>{who === 'system' ? systemText(m.system_code) : m.body}</span>
              </li>
            );
          })}
          <li ref={endRef} aria-hidden="true" />
        </ul>
      )}
      {writable ? (
        <form className="stack" onSubmit={send} noValidate>
          <TextArea label={t('bd.chat.label')} rows={2} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} hint={t('bd.chat.note')} />
          <div><button className="btn" disabled={busy || !text.trim()}>{t('bd.chat.send')}</button></div>
        </form>
      ) : (
        <p className="hint">{t('bd.chat.readOnly')}</p>
      )}
    </section>
  );
}

function ReviewSection({ booking, userId }: { booking: Booking; userId: string }) {
  const done = booking.status === 'completed';
  const res = useResource(
    (signal) => (done ? api.get<Review[]>(`/reviews/bookings/${booking.id}`, { signal }) : Promise.resolve([] as Review[])),
    [booking.id, done],
  );
  const toast = useToast();
  const [stars, setStars] = useState(0);
  const [comment, setComment] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const mine = res.data?.find((r) => r.reviewer_id === userId);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!stars) return;
    setBusy(true);
    try {
      const r = await api.post<Review>(`/reviews/bookings/${booking.id}`, { stars, comment: comment.trim(), tags: [] });
      res.setData([...(res.data ?? []), r]);
      toast.push('ok', t('bd.review.sent'));
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass pad stack" aria-labelledby="bd-rev-h">
      <h2 id="bd-rev-h">{t('bd.review.title')}</h2>
      {!done ? (
        <p className="muted">{t('bd.review.afterMeeting')}</p>
      ) : mine ? (
        <p>{t('bd.review.yours', { n: mine.stars })}</p>
      ) : (
        <form className="stack" onSubmit={send} noValidate>
          <div role="radiogroup" aria-label={t('bd.review.stars')} className="stars">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" role="radio" aria-checked={stars === n} aria-label={t('bd.review.starsAria', { n })} className={`star${n <= stars ? ' on' : ''}`} onClick={() => setStars(n)}>
                ★
              </button>
            ))}
          </div>
          {touched && !stars && <p className="err" role="alert">{t('bd.review.pick')}</p>}
          <TextArea label={t('bd.review.comment')} rows={3} maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} />
          <div><button className="btn" disabled={busy}>{t('bd.review.send')}</button></div>
        </form>
      )}
    </section>
  );
}
