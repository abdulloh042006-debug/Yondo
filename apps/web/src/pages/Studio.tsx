import { motion } from 'motion/react';
import { useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Schemas } from '../api/client';
import { t, type Key } from '../i18n';
import { formatInstant, formatMoney, toMinor } from '../lib/format';
import { APPLICATION_STATUS, BLOCKERS, CONTENT_STATUS, IDENTITY_STATUS, ACCOUNT_STATUS, SERVICE_LABELS, serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Field, Select, TextArea } from '../ui/form';
import { Reveal } from '../ui/motion';

type Application = Schemas['ApplicationResponse'];
type Profile = Schemas['ProfileResponse'];
type Status = Schemas['CompanionStatus'];
type Service = Schemas['ServiceResponse'];
type Availability = Schemas['AvailabilityResponse'];
type PhotoRow = Schemas['PhotoResponse'];

const TABS = [
  ['status', 'studio.tab.status'],
  ['application', 'studio.tab.application'],
  ['profile', 'studio.tab.profile'],
  ['services', 'studio.tab.services'],
  ['photos', 'studio.tab.photos'],
  ['availability', 'studio.tab.availability'],
] as const satisfies ReadonlyArray<readonly [string, Key]>;
type Tab = (typeof TABS)[number][0];

const msg = (e: unknown) => (e instanceof ApiError ? e.message : t('common.unexpected'));
const none = (e: ApiError | undefined) => e?.status === 404;

export function Studio() {
  const [tab, setTab] = useState<Tab>('status');
  return (
    <div className="stack" style={{ gap: 18 }}>
      <h1>{t('account.studio')}</h1>
      <div className="glass-bar admin-nav" role="tablist" aria-label={t('studio.tabsAria')}>
        {TABS.map(([id, labelKey]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            className="chip"
            style={{ border: 0, position: 'relative', background: 'transparent' }}
            onClick={() => setTab(id)}
          >
            {tab === id && <motion.span layoutId="studio-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
            {t(labelKey)}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === 'status' && <StatusTab goto={setTab} />}
        {tab === 'application' && <ApplicationTab />}
        {tab === 'profile' && <ProfileTab />}
        {tab === 'services' && <ServicesTab />}
        {tab === 'photos' && <PhotosTab />}
        {tab === 'availability' && <AvailabilityTab />}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ status */
function StatusTab({ goto }: { goto: (t: Tab) => void }) {
  const res = useResource((signal) => api.get<Status>('/companions/me/status', { signal }), []);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (res.loading && !res.data) return <Loading rows={2} />;
  if (none(res.error))
    return (
      <Empty title={t('studio.status.createFirst')} action={<button className="btn" onClick={() => goto('application')}>{t('studio.status.createApp')}</button>}>
        {t('studio.status.appearsAfter')}
      </Empty>
    );
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const s = res.data!;
  const act = async (path: 'activate' | 'deactivate') => {
    setBusy(true);
    try {
      const out = await api.post<Status | undefined>(`/companions/me/${path}`);
      if (out) res.setData(out);
      else res.reload();
      toast.push('ok', path === 'activate' ? t('studio.status.activateOk') : t('studio.status.deactivateOk'));
      res.reload();
    } catch (e) {
      toast.push('bad', msg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Reveal>
      <div className="glass pad stack">
        <div className="spread">
          <h2>{t('studio.status.publicTitle')}</h2>
          <span className={`tag ${s.publicly_active ? 'ok' : 'warn'}`}>{s.publicly_active ? t('studio.status.visible') : t('studio.status.hidden')}</span>
        </div>
        <dl className="kv">
          <dt>{t('studio.tab.application')}</dt><dd><StatusTag map={APPLICATION_STATUS} value={s.application_status} /></dd>
          <dt>{t('studio.status.content')}</dt><dd><StatusTag map={CONTENT_STATUS} value={s.content_status} /></dd>
          <dt>{t('settings.account')}</dt><dd><StatusTag map={ACCOUNT_STATUS} value={s.account_status} /></dd>
          <dt>{t('studio.status.identity')}</dt><dd>{IDENTITY_STATUS[s.identity_status] ?? s.identity_status}</dd>
        </dl>
        <p className="hint">{t('studio.status.note')}</p>
        {s.blockers.length > 0 && (
          <div className="banner">
            <b>{t('studio.status.blockers')}</b>
            <ul>{s.blockers.map((b) => <li key={b}>{BLOCKERS[b] ?? b}</li>)}</ul>
          </div>
        )}
        <div className="row">
          {!s.activation_requested ? (
            <button className="btn" disabled={busy || s.content_status !== 'approved'} onClick={() => void act('activate')}>{t('studio.status.requestActivation')}</button>
          ) : (
            <button className="btn ghost" disabled={busy} onClick={() => void act('deactivate')}>{t('studio.status.unlist')}</button>
          )}
          {s.content_status !== 'approved' && <span className="hint">{t('studio.status.needApproved')}</span>}
        </div>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------- application */
function ApplicationTab() {
  const res = useResource((signal) => api.get<Application>('/companions/me/application', { signal }), []);
  if (res.loading && res.data === undefined && !res.error) return <Loading rows={2} />;
  if (res.error && !none(res.error)) return <ErrorState error={res.error} onRetry={res.reload} />;
  // Remount whenever the server-side revision/status changes so the editor shows saved text.
  return <ApplicationForm key={`${res.data?.id}|${res.data?.revision}|${res.data?.status}`} app={res.data} onSaved={res.setData} />;
}

function ApplicationForm({ app, onSaved }: { app: Application | undefined; onSaved: (a: Application) => void }) {
  const toast = useToast();
  const [text, setText] = useState(app?.statement ?? '');
  const [busy, setBusy] = useState(false);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const editable = !app || ['draft', 'rejected', 'withdrawn'].includes(app.status);

  const run = async (fn: () => Promise<Application>, ok: string) => {
    setBusy(true);
    try {
      onSaved(await fn());
      toast.push('ok', ok);
    } catch (e) {
      toast.push('bad', msg(e));
    } finally {
      setBusy(false);
    }
  };
  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(() => (app ? api.put<Application>('/companions/me/application', { statement: text }) : api.post<Application>('/companions/me/application', { statement: text })), t('studio.app.saved'));
  };

  return (
    <Reveal>
      <div className="glass pad stack">
        <div className="spread">
          <h2>{t('studio.app.title')}</h2>
          {app && <StatusTag map={APPLICATION_STATUS} value={app.status} />}
        </div>
        {app?.status === 'rejected' && app.review_note && (
          <div className="banner bad"><b>{t('studio.app.rejectReason')}</b> {app.review_note}</div>
        )}
        {app?.status === 'submitted' && <p className="banner">{t('studio.app.submittedBanner')}</p>}
        {app?.status === 'approved' && <p className="banner">{t('studio.app.approvedBanner')}</p>}
        <form className="stack" onSubmit={save}>
          <TextArea label={t('studio.app.statement')} value={text} onChange={(e) => setText(e.target.value)} disabled={!editable} hint={t('studio.app.statementHint')} />
          <div className="row">
            {editable && <button className="btn ghost" disabled={busy}>{t('common.save')}</button>}
            {app?.status === 'draft' && (
              <button type="button" className="btn" disabled={busy} onClick={() => void run(() => api.post<Application>('/companions/me/application/submit'), t('studio.app.submitted'))}>{t('studio.app.submit')}</button>
            )}
            {app && app.status !== 'withdrawn' && (
              <button type="button" className="btn ghost" disabled={busy} onClick={() => setConfirmWithdraw(true)}>{t('studio.app.withdraw')}</button>
            )}
          </div>
        </form>
        <ConfirmDialog
          open={confirmWithdraw}
          danger
          title={t('studio.app.withdrawTitle')}
          body={t('studio.app.withdrawBody')}
          confirmLabel={t('studio.app.withdrawConfirm')}
          onClose={() => setConfirmWithdraw(false)}
          onConfirm={async () => {
            onSaved(await api.post<Application>('/companions/me/application/withdraw'));
            toast.push('ok', t('studio.app.withdrawn'));
            setConfirmWithdraw(false);
          }}
        />
      </div>
    </Reveal>
  );
}

/* ----------------------------------------------------------------- profile */
const split = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean);

function ProfileTab() {
  const res = useResource((signal) => api.get<Profile>('/companions/me/profile', { signal }), []);
  if (res.loading && res.data === undefined && !res.error) return <Loading rows={2} />;
  if (res.error && !none(res.error)) return <ErrorState error={res.error} onRetry={res.reload} />;
  return <ProfileForm key={`${res.data?.id}|${res.data?.revision}|${res.data?.content_status}`} p={res.data} onSaved={res.setData} />;
}

function ProfileForm({ p, onSaved }: { p: Profile | undefined; onSaved: (p: Profile) => void }) {
  const toast = useToast();
  const [name, setName] = useState(p?.display_name ?? '');
  const [bio, setBio] = useState(p?.bio ?? '');
  const [langs, setLangs] = useState(p?.languages.join(', ') ?? '');
  const [interests, setInterests] = useState(p?.interests.join(', ') ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const editable = !p || ['draft', 'rejected', 'approved'].includes(p.content_status);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErr(new ApiError(422, 'validation_error', undefined, { display_name: t('studio.profile.nameRequired') }));
      return;
    }
    setBusy(true);
    setErr(undefined);
    const body = { display_name: name.trim(), bio, languages: split(langs), interests: split(interests) };
    try {
      onSaved(p ? await api.put<Profile>('/companions/me/profile', body) : await api.post<Profile>('/companions/me/profile', body));
      toast.push('ok', t('account.saved'));
    } catch (error) {
      setErr(error instanceof ApiError ? error : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };
  const submit = async () => {
    setBusy(true);
    try {
      onSaved(await api.post<Profile>('/companions/me/profile/submit'));
      toast.push('ok', t('studio.profile.submitted'));
    } catch (error) {
      toast.push('bad', msg(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Reveal>
      <form className="glass pad stack" onSubmit={save} noValidate>
        <div className="spread">
          <h2>{t('studio.profile.title')}</h2>
          {p && <StatusTag map={CONTENT_STATUS} value={p.content_status} />}
        </div>
        {p?.content_status === 'rejected' && p.review_note && <div className="banner bad"><b>{t('studio.app.rejectReason')}</b> {p.review_note}</div>}
        {p?.content_status === 'pending' && <p className="banner">{t('studio.profile.pendingBanner')}</p>}
        {!p && <p className="hint">{t('studio.profile.createFirst')}</p>}
        <Field label={t('studio.profile.displayName')} value={name} maxLength={128} onChange={(e) => setName(e.target.value)} error={err?.fields.display_name} />
        <TextArea label={t('common.description')} value={bio} maxLength={8000} onChange={(e) => setBio(e.target.value)} hint={t('studio.profile.bioHint')} />
        <Field label={t('profile.languages')} value={langs} onChange={(e) => setLangs(e.target.value)} hint={t('studio.profile.languagesHint')} />
        <Field label={t('profile.interests')} value={interests} onChange={(e) => setInterests(e.target.value)} hint={t('studio.profile.interestsHint')} />
        {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
        <p className="hint">{t('studio.profile.editWarning')}</p>
        <div className="row">
          {editable && <button className="btn ghost" disabled={busy}>{t('common.save')}</button>}
          {p && ['draft', 'rejected'].includes(p.content_status) && (
            <button type="button" className="btn" disabled={busy} onClick={() => void submit()}>{t('studio.app.submit')}</button>
          )}
        </div>
      </form>
    </Reveal>
  );
}

/* ---------------------------------------------------------------- services */
function ServicesTab() {
  const res = useResource((signal) => api.get<Service[]>('/companions/me/services', { signal }), []);
  const toast = useToast();
  const [editing, setEditing] = useState<Service | 'new' | null>(null);
  const [removing, setRemoving] = useState<Service | null>(null);
  if (res.loading && !res.data) return <Loading rows={2} />;
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const list = res.data ?? [];
  return (
    <Reveal>
      <div className="stack">
        <div className="spread">
          <h2>{t('profile.services')}</h2>
          <button className="btn sm" onClick={() => setEditing('new')}>{t('studio.svc.add')}</button>
        </div>
        {list.length === 0 && !editing && <Empty title={t('studio.svc.none')}>{t('studio.svc.noneBody')}</Empty>}
        {list.map((s) => (
          <div key={s.id} className="glass pad tight spread">
            <div>
              <h3>{serviceLabel(s.service_code)}</h3>
              <p className="muted">{formatMoney(s.price_minor, s.currency)} / {t('book.minutesLong', { n: s.unit_minutes })}</p>
              {s.description && <p className="hint">{s.description}</p>}
            </div>
            <div className="row">
              <button className="btn sm ghost" onClick={() => setEditing(s)}>{t('common.edit')}</button>
              <button className="btn sm ghost" onClick={() => setRemoving(s)}>{t('common.delete')}</button>
            </div>
          </div>
        ))}
        {editing && (
          <ServiceForm
            key={editing === 'new' ? 'new' : editing.id}
            initial={editing === 'new' ? null : editing}
            taken={list.map((s) => s.service_code)}
            onDone={() => { setEditing(null); res.reload(); }}
            onCancel={() => setEditing(null)}
          />
        )}
        <ConfirmDialog
          open={!!removing}
          danger
          title={t('studio.svc.removeTitle')}
          body={removing ? t('studio.svc.removeBody', { name: serviceLabel(removing.service_code) }) : ''}
          confirmLabel={t('common.delete')}
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await api.del(`/companions/me/services/${removing!.id}`);
            toast.push('ok', t('studio.svc.removed'));
            setRemoving(null);
            res.reload();
          }}
        />
      </div>
    </Reveal>
  );
}

function ServiceForm({ initial, taken, onDone, onCancel }: { initial: Service | null; taken: string[]; onDone: () => void; onCancel: () => void }) {
  const toast = useToast();
  const [code, setCode] = useState(initial?.service_code ?? Object.keys(SERVICE_LABELS).find((c) => !taken.includes(c)) ?? 'coffee');
  const [price, setPrice] = useState(initial ? String(initial.price_minor / 100) : '');
  const [unit, setUnit] = useState(initial?.unit_minutes ?? 60);
  const [desc, setDesc] = useState(initial?.description ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [priceErr, setPriceErr] = useState<string>();
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const minor = toMinor(price);
    if (minor === null || minor <= 0) return setPriceErr(t('studio.svc.priceErr'));
    setPriceErr(undefined);
    setBusy(true);
    setErr(undefined);
    const body = { service_code: code, price_minor: minor, currency: 'UZS', unit_minutes: unit, description: desc.trim() };
    try {
      if (initial) await api.put(`/companions/me/services/${initial.id}`, body);
      else await api.post('/companions/me/services', body);
      toast.push('ok', t('studio.svc.saved'));
      onDone();
    } catch (error) {
      setErr(msg(error));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="glass pad stack" onSubmit={submit} noValidate>
      <h3>{initial ? t('studio.svc.editTitle') : t('studio.svc.newTitle')}</h3>
      <Select label={t('discovery.serviceType')} value={code} disabled={!!initial} onChange={(e) => setCode(e.target.value)}>
        {Object.entries(SERVICE_LABELS).map(([c, l]) => <option key={c} value={c} disabled={!initial && taken.includes(c)}>{l}</option>)}
      </Select>
      <div className="bento">
        <Field label={t('studio.svc.price')} inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value)} error={priceErr} />
        <Select label={t('studio.svc.unit')} value={unit} onChange={(e) => setUnit(Number(e.target.value))}>
          {[30, 60, 90, 120].map((n) => <option key={n} value={n}>{t('book.minutesLong', { n })}</option>)}
        </Select>
      </div>
      <TextArea label={t('common.description')} value={desc} maxLength={2000} onChange={(e) => setDesc(e.target.value)} />
      {err && <p className="err" role="alert">{err}</p>}
      <div className="row"><button className="btn" disabled={busy}>{t('common.save')}</button><button type="button" className="btn ghost" onClick={onCancel}>{t('common.cancel')}</button></div>
    </form>
  );
}

/* ------------------------------------------------------------------ photos */
function PhotosTab() {
  const res = useResource((signal) => api.get<PhotoRow[]>('/companions/me/photos', { signal }), []);
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<PhotoRow | null>(null);
  if (res.loading && !res.data) return <Loading rows={2} />;
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const upload = async (file: File | undefined) => {
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return toast.push('bad', t('studio.photo.typeErr'));
    setBusy(true);
    try {
      await api.upload('/companions/me/photos', file);
      toast.push('ok', t('studio.photo.uploaded'));
      res.reload();
    } catch (e) {
      toast.push('bad', msg(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = '';
    }
  };
  return (
    <Reveal>
      <div className="stack">
        <div className="spread">
          <h2>{t('studio.tab.photos')}</h2>
          <button className="btn sm" disabled={busy} onClick={() => input.current?.click()}>{busy && <span className="spinner" aria-hidden="true" />}{t('studio.photo.upload')}</button>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label={t('studio.photo.choose')} onChange={(e) => void upload(e.target.files?.[0])} />
        </div>
        <p className="hint">{t('studio.photo.reviewNote')}</p>
        {(res.data ?? []).length === 0 ? <Empty title={t('studio.photo.none')}>{t('studio.photo.noneBody')}</Empty> : (
          <div className="gallery">
            {res.data!.map((p) => (
              <div key={p.id} className="glass tight stack" style={{ padding: 10 }}>
                <OwnPhoto id={p.id} />
                <div className="spread"><span className="hint">№ {p.position + 1}</span><button className="btn sm ghost" onClick={() => setRemoving(p)}>{t('common.delete')}</button></div>
              </div>
            ))}
          </div>
        )}
        <ConfirmDialog
          open={!!removing}
          danger
          title={t('studio.photo.removeTitle')}
          body={t('studio.photo.removeBody')}
          confirmLabel={t('common.delete')}
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await api.del(`/companions/me/photos/${removing!.id}`);
            toast.push('ok', t('studio.photo.removed'));
            setRemoving(null);
            res.reload();
          }}
        />
      </div>
    </Reveal>
  );
}

function OwnPhoto({ id }: { id: string }) {
  const res = useResource((signal) => api.get<Schemas['PhotoDownload']>(`/companions/me/photos/${id}/download`, { signal }), [id]);
  return (
    <div className="media" style={{ borderRadius: 'var(--r-sm)', aspectRatio: '3 / 4' }}>
      {res.data ? <img src={res.data.url} alt={t('studio.photo.uploadedAlt')} loading="lazy" /> : <span className="hint">{res.error ? t('studio.photo.missing') : '…'}</span>}
    </div>
  );
}

/* ------------------------------------------------------------ availability */
function AvailabilityTab() {
  const res = useResource((signal) => api.get<Availability[]>('/companions/me/availability', { signal }), []);
  const toast = useToast();
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  if (res.loading && !res.data) return <Loading rows={2} />;
  if (res.error) return <ErrorState error={res.error} onRetry={res.reload} />;
  const add = async (e: FormEvent) => {
    e.preventDefault();
    const a = from ? new Date(`${from}:00+05:00`) : null;
    const b = to ? new Date(`${to}:00+05:00`) : null;
    if (!a || !b || Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return setErr(t('studio.av.pickErr'));
    if (b <= a) return setErr(t('studio.av.orderErr'));
    setBusy(true);
    setErr(undefined);
    try {
      await api.post('/companions/me/availability', { starts_at: a.toISOString(), ends_at: b.toISOString(), timezone: 'Asia/Tashkent' });
      toast.push('ok', t('studio.av.added'));
      setFrom('');
      setTo('');
      res.reload();
    } catch (error) {
      setErr(msg(error));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (id: string) => {
    try {
      await api.del(`/companions/me/availability/${id}`);
      toast.push('ok', t('studio.av.removed'));
      res.reload();
    } catch (e) {
      toast.push('bad', msg(e));
    }
  };
  return (
    <Reveal>
      <div className="stack">
        <h2>{t('studio.av.title')}</h2>
        <form className="glass pad stack" onSubmit={add} noValidate>
          <div className="bento">
            <Field label={t('studio.av.from')} type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} />
            <Field label={t('studio.av.to')} type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          {err && <p className="err" role="alert">{err}</p>}
          <div><button className="btn" disabled={busy}>{t('studio.av.add')}</button></div>
        </form>
        {(res.data ?? []).length === 0 ? <Empty title={t('studio.av.none')}>{t('studio.av.noneBody')}</Empty> : res.data!.map((a) => (
          <div key={a.id} className="glass pad tight spread">
            <span>{formatInstant(a.starts_at)} — {formatInstant(a.ends_at)}</span>
            <button className="btn sm ghost" onClick={() => void remove(a.id)}>{t('common.delete')}</button>
          </div>
        ))}
      </div>
    </Reveal>
  );
}
