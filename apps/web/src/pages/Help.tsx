import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t, type Key } from '../i18n';
import { REPORT_CATEGORY, REPORT_STATUS, SUPPORT_STATUS } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Field, Select, TextArea } from '../ui/form';
import { Reveal } from '../ui/motion';
import { SosButton } from '../ui/Sos';

type Report = Schemas['ReportRead'];
type Contact = Schemas['ContactRead'];
type FeedbackCategory = Schemas['FeedbackWrite']['category'];
type SupportCategory = Schemas['SupportWrite']['category'];
type Ticket = Schemas['SupportRead'];

const FAQ = ['what', 'book', 'pay', 'cancel', 'verified', 'companion', 'privacy', 'data', 'delete'] as const;
const SUPPORT_CATEGORIES: SupportCategory[] = ['account', 'booking', 'payment', 'safety', 'technical', 'other'];
const FEEDBACK_CATEGORIES: FeedbackCategory[] = ['bug', 'usability', 'safety', 'pricing', 'other'];
const PHONE = /^\+?[0-9]{7,15}$/;

/** Help, safety and reports: one place, reachable from the footer, Profile and Settings (also signed out). */
export function Help() {
  const { user } = useAuth();
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <div className="stack" style={{ gap: 6 }}>
        <h1>{t('help.title')}</h1>
        <p className="muted">{t('help.lead')}</p>
      </div>

      <Reveal>
        <section className="glass pad stack emergency" aria-labelledby="sos-h">
          <h2 id="sos-h">{t('help.emergency.title')}</h2>
          <p>{t('help.emergency.body')}</p>
          <div className="row">
            <a className="btn" href="tel:112">{t('help.emergency.call')}</a>
            <SosButton className="btn ghost" />
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.03}>
        <section className="glass pad stack" aria-labelledby="rep-h">
          <h2 id="rep-h">{t('help.report.title')}</h2>
          <p>{t('help.report.body')}</p>
          <p className="hint">{t('help.report.noBooking')}</p>
          {user ? (
            <Link className="btn ghost" to="/bookings" style={{ width: 'fit-content' }}>{t('help.report.toBookings')}</Link>
          ) : (
            <Link className="btn ghost" to="/login" style={{ width: 'fit-content' }}>{t('nav.login')}</Link>
          )}
        </section>
      </Reveal>

      {user ? (
        <>
          <MyReports />
          <TrustedContacts />
          <BetaFeedback />
        </>
      ) : (
        <p className="banner">{t('help.loginFor')}</p>
      )}

      <Reveal delay={0.06}>
        <section className="glass pad stack" aria-labelledby="faq-h">
          <h2 id="faq-h">{t('help.faq.title')}</h2>
          <div className="faq">
            {FAQ.map((id) => (
              <details key={id}>
                <summary>{t(`help.faq.${id}.q` as Key)}</summary>
                <p>{t(`help.faq.${id}.a` as Key)}</p>
              </details>
            ))}
          </div>
        </section>
      </Reveal>

      <Reveal delay={0.08}>
        <section className="glass pad stack" aria-labelledby="sup-h">
          <h2 id="sup-h">{t('help.contact.title')}</h2>
          <p className="muted">{t('help.support.body')}</p>
          {user ? <SupportRequests /> : <Link className="btn ghost" to="/login" style={{ width: 'fit-content' }}>{t('help.support.login')}</Link>}
        </section>
      </Reveal>
    </div>
  );
}

function MyReports() {
  const res = useResource((signal) => api.get<Report[]>('/safety/reports', { signal }), []);
  return (
    <Reveal delay={0.04}>
      <section className="glass pad stack" aria-labelledby="my-h">
        <h2 id="my-h">{t('help.myReports')}</h2>
        {res.loading && !res.data ? (
          <Loading rows={1} />
        ) : res.error ? (
          <ErrorState error={res.error} onRetry={res.reload} />
        ) : !res.data?.length ? (
          <p className="muted">{t('help.myReportsEmpty')}</p>
        ) : (
          <ul className="plain-list">
            {res.data.map((r) => (
              <li key={r.id} className="spread">
                <span className="stack" style={{ gap: 2 }}>
                  <b>{REPORT_CATEGORY[r.category] ?? r.category}</b>
                  <span className="hint clamp">{r.description}</span>
                </span>
                <StatusTag map={REPORT_STATUS} value={r.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </Reveal>
  );
}

function TrustedContacts() {
  const res = useResource((signal) => api.get<Contact[]>('/safety/trusted-contacts', { signal }), []);
  const toast = useToast();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const cleanPhone = phone.replace(/[\s()-]/g, '');
  const nameErr = touched && !name.trim() ? t('help.contacts.nameRequired') : undefined;
  const phoneErr = touched && !PHONE.test(cleanPhone) ? t('help.contacts.phoneInvalid') : undefined;

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!name.trim() || !PHONE.test(cleanPhone)) return;
    setBusy(true);
    try {
      await api.post<Contact>('/safety/trusted-contacts', { name: name.trim(), phone_number: cleanPhone });
      toast.push('ok', t('help.contacts.added'));
      setName('');
      setPhone('');
      setTouched(false);
      res.reload();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (c: Contact) => {
    try {
      await api.del(`/safety/trusted-contacts/${c.id}`);
      toast.push('ok', t('help.contacts.removed'));
      res.reload();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    }
  };

  return (
    <Reveal delay={0.05}>
      <section className="glass pad stack" aria-labelledby="tc-h">
        <h2 id="tc-h">{t('help.contacts.title')}</h2>
        <p className="muted">{t('help.contacts.body')}</p>
        {res.loading && !res.data ? (
          <Loading rows={1} />
        ) : res.error ? (
          <ErrorState error={res.error} onRetry={res.reload} />
        ) : !res.data?.length ? (
          <p className="hint">{t('help.contacts.empty')}</p>
        ) : (
          <ul className="plain-list">
            {res.data.map((c) => (
              <li key={c.id} className="spread">
                <span className="stack" style={{ gap: 2 }}>
                  <b>{c.name}</b>
                  <span className="hint">{c.phone_number}</span>
                </span>
                <button className="btn sm ghost" aria-label={t('help.contacts.remove', { name: c.name })} onClick={() => void remove(c)}>
                  {t('help.contacts.removeShort')}
                </button>
              </li>
            ))}
          </ul>
        )}
        <form className="bento" onSubmit={add} noValidate>
          <Field label={t('help.contacts.name')} value={name} maxLength={128} autoComplete="off" onChange={(e) => setName(e.target.value)} error={nameErr} />
          <Field
            label={t('help.contacts.phone')}
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            hint={t('help.contacts.phoneHint')}
            error={phoneErr}
          />
          <div style={{ alignSelf: 'end' }}>
            <button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('help.contacts.add')}</button>
          </div>
        </form>
      </section>
    </Reveal>
  );
}

/** Shown only to invited closed-beta participants (`GET /beta/me` succeeds); everyone else sees nothing. */
function BetaFeedback() {
  const beta = useResource((signal) => api.get<Schemas['EnrollmentRead']>('/beta/me', { signal }), []);
  const toast = useToast();
  const [category, setCategory] = useState<FeedbackCategory>('usability');
  const [rating, setRating] = useState(4);
  const [text, setText] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!beta.data?.enabled) return null;
  const short = text.trim().length < 10;

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (short) return;
    setBusy(true);
    try {
      await api.post('/beta/feedback', { category, rating, description: text.trim() });
      toast.push('ok', t('help.feedback.sent'));
      setText('');
      setTouched(false);
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Reveal delay={0.05}>
      <form className="glass pad stack" onSubmit={send} noValidate aria-labelledby="fb-h">
        <h2 id="fb-h">{t('help.feedback.title')}</h2>
        <p className="muted">{t('help.feedback.body')}</p>
        <div className="bento">
          <Select label={t('help.feedback.category')} value={category} onChange={(e) => setCategory(e.target.value as FeedbackCategory)}>
            {FEEDBACK_CATEGORIES.map((c) => (
              <option key={c} value={c}>{t(`help.feedback.cat.${c}` as Key)}</option>
            ))}
          </Select>
          <Select label={t('help.feedback.rating')} value={rating} onChange={(e) => setRating(Number(e.target.value))}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </Select>
        </div>
        <TextArea label={t('help.feedback.text')} rows={3} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} error={touched && short ? t('help.feedback.min') : undefined} />
        <div><button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('help.feedback.send')}</button></div>
      </form>
    </Reveal>
  );
}

/** The in-app support channel (owner decision: no e-mail, no phone). Replies show up here. */
function SupportRequests() {
  const res = useResource((signal) => api.get<Ticket[]>('/support/requests', { signal }), []);
  const toast = useToast();
  const [category, setCategory] = useState<SupportCategory>('account');
  const [message, setMessage] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const short = message.trim().length < 10;

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (short) return;
    setBusy(true);
    try {
      await api.post<Ticket>('/support/requests', { category, message: message.trim() });
      toast.push('ok', t('help.support.sent'));
      setMessage('');
      setTouched(false);
      res.reload();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <form className="stack" onSubmit={send} noValidate>
        <Select label={t('help.support.category')} value={category} onChange={(e) => setCategory(e.target.value as SupportCategory)}>
          {SUPPORT_CATEGORIES.map((c) => (
            <option key={c} value={c}>{t(`help.support.cat.${c}` as Key)}</option>
          ))}
        </Select>
        <TextArea label={t('help.support.message')} rows={4} maxLength={4000} value={message} onChange={(e) => setMessage(e.target.value)} error={touched && short ? t('help.feedback.min') : undefined} />
        <div><button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('help.support.send')}</button></div>
      </form>
      {!!res.data?.length && (
        <div className="stack" style={{ gap: 8 }}>
          <h3>{t('help.support.mine')}</h3>
          <ul className="plain-list">
            {res.data.map((r) => (
              <li key={r.id} className="stack" style={{ gap: 4 }}>
                <span className="spread">
                  <b>{t(`help.support.cat.${r.category}` as Key)}</b>
                  <StatusTag map={SUPPORT_STATUS} value={r.status} />
                </span>
                <span className="hint clamp">{r.message}</span>
                {r.reply && <span className="banner" style={{ whiteSpace: 'pre-wrap' }}><b>{t('help.support.reply')}:</b> {r.reply}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
