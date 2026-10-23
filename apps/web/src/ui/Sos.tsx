import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { Dialog, useToast } from './feedback';

type Booking = Schemas['BookingResponse'];
type Contact = Schemas['ContactRead'];

/**
 * SOS, honest by construction (owner rules 2026-10-23):
 * - opening it does nothing by itself (the dialog is the confirmation step against accidental taps);
 * - 112 and trusted contacts are reached through the user's own phone (tel:/sms: links) — the app never
 *   claims it called or messaged anyone;
 * - location is read only after an explicit tap (browser permission) and only goes into the SMS text;
 * - the moderator signal exists only for a meeting in progress and is a recorded alert, not a rescue.
 */
export function SosButton({ className = 'sos-btn' }: { className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className={className} aria-label={t('sos.buttonAria')} aria-haspopup="dialog" onClick={() => setOpen(true)}>
        {t('sos.button')}
      </button>
      {open && <SosDialog onClose={() => setOpen(false)} />}
    </>
  );
}

function SosDialog({ onClose }: { onClose: () => void }) {
  const { user } = useAuth();
  const [coords, setCoords] = useState<string>();
  const [locErr, setLocErr] = useState<string>();
  const [locBusy, setLocBusy] = useState(false);

  const addLocation = () => {
    if (!('geolocation' in navigator)) {
      setLocErr(t('sos.locationUnavailable'));
      return;
    }
    setLocBusy(true);
    setLocErr(undefined);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy } = pos.coords;
        setCoords(`${latitude.toFixed(5)}, ${longitude.toFixed(5)} (±${Math.round(accuracy)} m)`);
        setLocBusy(false);
      },
      (err) => {
        setLocErr(err.code === err.PERMISSION_DENIED ? t('sos.locationDenied') : t('sos.locationUnavailable'));
        setLocBusy(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  };

  const smsText = coords ? `${t('sos.smsBody')} ${t('sos.smsLocation', { coords })}` : t('sos.smsBody');

  return (
    <Dialog open title={t('sos.title')} onClose={onClose}>
      <div className="stack sos-dialog">
        <p>{t('sos.intro')}</p>
        <a className="btn danger" href="tel:112">{t('help.emergency.call')}</a>
        <div className="stack" style={{ gap: 6 }}>
          <button type="button" className="btn ghost" disabled={locBusy} onClick={addLocation}>
            {locBusy && <span className="spinner" aria-hidden="true" />}{t('sos.location')}
          </button>
          {coords && <p className="hint" role="status">{t('sos.locationAdded', { coords })}</p>}
          {locErr && <p className="err" role="alert">{locErr}</p>}
          <p className="hint">{t('sos.locationHint')}</p>
        </div>
        {user ? (
          <>
            <TrustedContactLinks smsText={smsText} onNavigate={onClose} />
            <ModeratorSignal />
          </>
        ) : (
          <p className="hint">{t('sos.loginForMore')}</p>
        )}
        <button type="button" className="btn ghost" onClick={onClose}>{t('sos.close')}</button>
      </div>
    </Dialog>
  );
}

function TrustedContactLinks({ smsText, onNavigate }: { smsText: string; onNavigate: () => void }) {
  const res = useResource((signal) => api.get<Contact[]>('/safety/trusted-contacts', { signal }), []);
  // `?&body=` is understood by both iOS and Android messaging apps.
  const sms = (phone: string) => `sms:${phone}?&body=${encodeURIComponent(smsText)}`;
  return (
    <section className="stack" style={{ gap: 6 }} aria-labelledby="sos-contacts-h">
      <h3 id="sos-contacts-h">{t('help.contacts.title')}</h3>
      {res.data && res.data.length === 0 ? (
        <p className="hint">
          {t('sos.noContacts')} <Link to="/help" onClick={onNavigate}>{t('sos.addContacts')}</Link>
        </p>
      ) : (
        <ul className="plain-list">
          {(res.data ?? []).map((c) => (
            <li key={c.id} className="spread">
              <b>{c.name}</b>
              <span className="row">
                <a className="btn sm" href={sms(c.phone_number)} aria-label={t('sos.smsAria', { name: c.name })}>{t('sos.sms')}</a>
                <a className="btn sm ghost" href={`tel:${c.phone_number}`} aria-label={t('sos.callAria', { name: c.name })}>{t('sos.callContact')}</a>
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="hint">{t('sos.deviceNote')}</p>
    </section>
  );
}

function ModeratorSignal() {
  const res = useResource((signal) => api.get<Booking[]>('/bookings', { query: { limit: 50 }, signal }), []);
  const toast = useToast();
  const [sent, setSent] = useState<string>();
  const [busy, setBusy] = useState(false);
  const active = (res.data ?? []).filter((b) => b.status === 'active');

  const send = async (b: Booking) => {
    setBusy(true);
    try {
      await api.post(`/safety/bookings/${b.id}/sos`, undefined, { query: { confirmed: true } });
      setSent(b.id);
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="stack" style={{ gap: 6 }} aria-labelledby="sos-mod-h">
      <h3 id="sos-mod-h">{t('sos.moderator')}</h3>
      <p className="hint">{t('sos.moderatorHint')}</p>
      {res.data && active.length === 0 && <p className="muted">{t('sos.noActive')}</p>}
      {active.map((b) =>
        sent === b.id ? (
          <p key={b.id} className="banner" role="status">{t('sos.signalSent')}</p>
        ) : (
          <button key={b.id} type="button" className="btn danger" disabled={busy} onClick={() => void send(b)}>
            {t('sos.sendSignal', { service: serviceLabel(b.service_code) })}
          </button>
        ),
      )}
    </section>
  );
}
