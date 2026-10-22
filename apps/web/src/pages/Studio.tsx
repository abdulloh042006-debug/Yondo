import { motion } from 'motion/react';
import { useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Schemas } from '../api/client';
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
  ['status', 'Holat'],
  ['application', 'Ariza'],
  ['profile', 'Profil'],
  ['services', 'Xizmatlar'],
  ['photos', 'Rasmlar'],
  ['availability', 'Bo‘sh vaqt'],
] as const;
type Tab = (typeof TABS)[number][0];

const msg = (e: unknown) => (e instanceof ApiError ? e.message : 'Kutilmagan xatolik yuz berdi.');
const none = (e: ApiError | undefined) => e?.status === 404;

export function Studio() {
  const [tab, setTab] = useState<Tab>('status');
  return (
    <div className="stack" style={{ gap: 18 }}>
      <h1>Hamroh studiyasi</h1>
      <div className="glass-bar admin-nav" role="tablist" aria-label="Studiya bo‘limlari">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            className="chip"
            style={{ border: 0, position: 'relative', background: 'transparent' }}
            onClick={() => setTab(id)}
          >
            {tab === id && <motion.span layoutId="studio-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
            {label}
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
      <Empty title="Avval ariza va profil yarating" action={<button className="btn" onClick={() => goto('application')}>Ariza yaratish</button>}>
        Hamroh holati profil yaratilgandan keyin ko‘rinadi.
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
      toast.push('ok', path === 'activate' ? 'Faollashtirish so‘rovi qabul qilindi.' : 'Profil ommaviy ro‘yxatdan olindi.');
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
          <h2>Ommaga chiqish holati</h2>
          <span className={`tag ${s.publicly_active ? 'ok' : 'warn'}`}>{s.publicly_active ? 'Ommaga ko‘rinadi' : 'Ommaga ko‘rinmaydi'}</span>
        </div>
        <dl className="kv">
          <dt>Ariza</dt><dd><StatusTag map={APPLICATION_STATUS} value={s.application_status} /></dd>
          <dt>Profil kontenti</dt><dd><StatusTag map={CONTENT_STATUS} value={s.content_status} /></dd>
          <dt>Hisob</dt><dd><StatusTag map={ACCOUNT_STATUS} value={s.account_status} /></dd>
          <dt>Shaxs</dt><dd>{IDENTITY_STATUS[s.identity_status] ?? s.identity_status}</dd>
        </dl>
        <p className="hint">
          Kontent tasdig‘i shaxs tasdig‘i emas: profil mazmuni ma’qullansa ham, shaxs tekshiruvi ulanmaguncha profil ommaga chiqmaydi.
        </p>
        {s.blockers.length > 0 && (
          <div className="banner">
            <b>Hozircha to‘siqlar:</b>
            <ul>{s.blockers.map((b) => <li key={b}>{BLOCKERS[b] ?? b}</li>)}</ul>
          </div>
        )}
        <div className="row">
          {!s.activation_requested ? (
            <button className="btn" disabled={busy || s.content_status !== 'approved'} onClick={() => void act('activate')}>Faollashtirishni so‘rash</button>
          ) : (
            <button className="btn ghost" disabled={busy} onClick={() => void act('deactivate')}>Ommaviy ro‘yxatdan olish</button>
          )}
          {s.content_status !== 'approved' && <span className="hint">Faollashtirish uchun profil kontenti tasdiqlangan bo‘lishi kerak.</span>}
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
    void run(() => (app ? api.put<Application>('/companions/me/application', { statement: text }) : api.post<Application>('/companions/me/application', { statement: text })), 'Ariza saqlandi.');
  };

  return (
    <Reveal>
      <div className="glass pad stack">
        <div className="spread">
          <h2>Hamroh arizasi</h2>
          {app && <StatusTag map={APPLICATION_STATUS} value={app.status} />}
        </div>
        {app?.status === 'rejected' && app.review_note && (
          <div className="banner bad"><b>Rad etish sababi:</b> {app.review_note}</div>
        )}
        {app?.status === 'submitted' && <p className="banner">Arizangiz administrator ko‘rib chiqishini kutmoqda. Bu vaqtda tahrirlab bo‘lmaydi.</p>}
        {app?.status === 'approved' && <p className="banner">Ariza tasdiqlangan. Endi profilni to‘ldirib, ko‘rib chiqishga yuboring.</p>}
        <form className="stack" onSubmit={save}>
          <TextArea label="O‘zingiz haqingizda qisqacha" value={text} onChange={(e) => setText(e.target.value)} disabled={!editable} hint="Tahrir qilsangiz ariza qoralamaga qaytadi." />
          <div className="row">
            {editable && <button className="btn ghost" disabled={busy}>Saqlash</button>}
            {app?.status === 'draft' && (
              <button type="button" className="btn" disabled={busy} onClick={() => void run(() => api.post<Application>('/companions/me/application/submit'), 'Ariza ko‘rib chiqishga yuborildi.')}>Ko‘rib chiqishga yuborish</button>
            )}
            {app && app.status !== 'withdrawn' && (
              <button type="button" className="btn ghost" disabled={busy} onClick={() => setConfirmWithdraw(true)}>Arizani qaytarib olish</button>
            )}
          </div>
        </form>
        <ConfirmDialog
          open={confirmWithdraw}
          danger
          title="Arizani qaytarib olasizmi?"
          body="Ariza qaytarib olinadi va profilingiz ommaga ko‘rinmay qoladi."
          confirmLabel="Qaytarib olish"
          onClose={() => setConfirmWithdraw(false)}
          onConfirm={async () => {
            onSaved(await api.post<Application>('/companions/me/application/withdraw'));
            toast.push('ok', 'Ariza qaytarib olindi.');
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
      setErr(new ApiError(422, 'validation_error', undefined, { display_name: 'Ko‘rsatiladigan ismni yozing.' }));
      return;
    }
    setBusy(true);
    setErr(undefined);
    const body = { display_name: name.trim(), bio, languages: split(langs), interests: split(interests) };
    try {
      onSaved(p ? await api.put<Profile>('/companions/me/profile', body) : await api.post<Profile>('/companions/me/profile', body));
      toast.push('ok', 'Profil saqlandi.');
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
      toast.push('ok', 'Profil kontenti ko‘rib chiqishga yuborildi.');
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
          <h2>Ommaviy profil</h2>
          {p && <StatusTag map={CONTENT_STATUS} value={p.content_status} />}
        </div>
        {p?.content_status === 'rejected' && p.review_note && <div className="banner bad"><b>Rad etish sababi:</b> {p.review_note}</div>}
        {p?.content_status === 'pending' && <p className="banner">Profil kontenti ko‘rib chiqilmoqda.</p>}
        {!p && <p className="hint">Profil yaratish uchun avval “Ariza” bo‘limida ariza yarating.</p>}
        <Field label="Ko‘rsatiladigan ism" value={name} maxLength={128} onChange={(e) => setName(e.target.value)} error={err?.fields.display_name} />
        <TextArea label="Tavsif" value={bio} maxLength={8000} onChange={(e) => setBio(e.target.value)} hint="Uy manzili, telefon yoki ijtimoiy tarmoq havolalarini yozmang." />
        <Field label="Tillar" value={langs} onChange={(e) => setLangs(e.target.value)} hint="Vergul bilan ajrating: uz, ru, en" />
        <Field label="Qiziqishlar" value={interests} onChange={(e) => setInterests(e.target.value)} hint="Vergul bilan ajrating" />
        {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
        <p className="hint">Har qanday tahrir tasdiqni bekor qiladi: profil qoralamaga qaytadi va ommaviy ro‘yxatdan chiqadi.</p>
        <div className="row">
          {editable && <button className="btn ghost" disabled={busy}>Saqlash</button>}
          {p && ['draft', 'rejected'].includes(p.content_status) && (
            <button type="button" className="btn" disabled={busy} onClick={() => void submit()}>Ko‘rib chiqishga yuborish</button>
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
          <h2>Xizmatlar va narxlar</h2>
          <button className="btn sm" onClick={() => setEditing('new')}>Xizmat qo‘shish</button>
        </div>
        {list.length === 0 && !editing && <Empty title="Hali xizmat yo‘q">Mijozlar bron qilishi uchun kamida bitta xizmat qo‘shing.</Empty>}
        {list.map((s) => (
          <div key={s.id} className="glass pad tight spread">
            <div>
              <h3>{serviceLabel(s.service_code)}</h3>
              <p className="muted">{formatMoney(s.price_minor, s.currency)} / {s.unit_minutes} daqiqa</p>
              {s.description && <p className="hint">{s.description}</p>}
            </div>
            <div className="row">
              <button className="btn sm ghost" onClick={() => setEditing(s)}>Tahrirlash</button>
              <button className="btn sm ghost" onClick={() => setRemoving(s)}>O‘chirish</button>
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
          title="Xizmatni o‘chirasizmi?"
          body={removing ? `“${serviceLabel(removing.service_code)}” xizmati o‘chiriladi va profil qoralamaga qaytadi.` : ''}
          confirmLabel="O‘chirish"
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await api.del(`/companions/me/services/${removing!.id}`);
            toast.push('ok', 'Xizmat o‘chirildi.');
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
    if (minor === null || minor <= 0) return setPriceErr('Narxni so‘mda kiriting (masalan, 150 000).');
    setPriceErr(undefined);
    setBusy(true);
    setErr(undefined);
    const body = { service_code: code, price_minor: minor, currency: 'UZS', unit_minutes: unit, description: desc.trim() };
    try {
      if (initial) await api.put(`/companions/me/services/${initial.id}`, body);
      else await api.post('/companions/me/services', body);
      toast.push('ok', 'Xizmat saqlandi.');
      onDone();
    } catch (error) {
      setErr(msg(error));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="glass pad stack" onSubmit={submit} noValidate>
      <h3>{initial ? 'Xizmatni tahrirlash' : 'Yangi xizmat'}</h3>
      <Select label="Xizmat turi" value={code} disabled={!!initial} onChange={(e) => setCode(e.target.value)}>
        {Object.entries(SERVICE_LABELS).map(([c, l]) => <option key={c} value={c} disabled={!initial && taken.includes(c)}>{l}</option>)}
      </Select>
      <div className="bento">
        <Field label="Narx (so‘m)" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value)} error={priceErr} />
        <Select label="Narx birligi" value={unit} onChange={(e) => setUnit(Number(e.target.value))}>
          {[30, 60, 90, 120].map((n) => <option key={n} value={n}>{n} daqiqa</option>)}
        </Select>
      </div>
      <TextArea label="Tavsif" value={desc} maxLength={2000} onChange={(e) => setDesc(e.target.value)} />
      {err && <p className="err" role="alert">{err}</p>}
      <div className="row"><button className="btn" disabled={busy}>Saqlash</button><button type="button" className="btn ghost" onClick={onCancel}>Bekor qilish</button></div>
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
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return toast.push('bad', 'Faqat JPEG, PNG yoki WebP rasm yuklash mumkin.');
    setBusy(true);
    try {
      await api.upload('/companions/me/photos', file);
      toast.push('ok', 'Rasm yuklandi.');
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
          <h2>Rasmlar</h2>
          <button className="btn sm" disabled={busy} onClick={() => input.current?.click()}>{busy && <span className="spinner" aria-hidden="true" />}Rasm yuklash</button>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Rasm tanlash" onChange={(e) => void upload(e.target.files?.[0])} />
        </div>
        <p className="hint">Rasmlar ommaga chiqishdan oldin administrator tomonidan ko‘rib chiqiladi. O‘zgarish profilni qoralamaga qaytaradi.</p>
        {(res.data ?? []).length === 0 ? <Empty title="Rasm yo‘q">Profilingizga kamida bitta aniq rasm yuklang.</Empty> : (
          <div className="gallery">
            {res.data!.map((p) => (
              <div key={p.id} className="glass tight stack" style={{ padding: 10 }}>
                <OwnPhoto id={p.id} />
                <div className="spread"><span className="hint">№ {p.position + 1}</span><button className="btn sm ghost" onClick={() => setRemoving(p)}>O‘chirish</button></div>
              </div>
            ))}
          </div>
        )}
        <ConfirmDialog
          open={!!removing}
          danger
          title="Rasmni o‘chirasizmi?"
          body="Rasm o‘chiriladi va profil qoralamaga qaytadi."
          confirmLabel="O‘chirish"
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await api.del(`/companions/me/photos/${removing!.id}`);
            toast.push('ok', 'Rasm o‘chirildi.');
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
      {res.data ? <img src={res.data.url} alt="Yuklangan rasm" loading="lazy" /> : <span className="hint">{res.error ? 'Rasm mavjud emas' : '…'}</span>}
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
    if (!a || !b || Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return setErr('Boshlanish va tugash vaqtini tanlang.');
    if (b <= a) return setErr('Tugash vaqti boshlanishdan keyin bo‘lishi kerak.');
    setBusy(true);
    setErr(undefined);
    try {
      await api.post('/companions/me/availability', { starts_at: a.toISOString(), ends_at: b.toISOString(), timezone: 'Asia/Tashkent' });
      toast.push('ok', 'Bo‘sh vaqt qo‘shildi.');
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
      toast.push('ok', 'Oraliq o‘chirildi.');
      res.reload();
    } catch (e) {
      toast.push('bad', msg(e));
    }
  };
  return (
    <Reveal>
      <div className="stack">
        <h2>Bo‘sh vaqtlar</h2>
        <form className="glass pad stack" onSubmit={add} noValidate>
          <div className="bento">
            <Field label="Boshlanishi (Toshkent vaqti)" type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} />
            <Field label="Tugashi (Toshkent vaqti)" type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          {err && <p className="err" role="alert">{err}</p>}
          <div><button className="btn" disabled={busy}>Oraliq qo‘shish</button></div>
        </form>
        {(res.data ?? []).length === 0 ? <Empty title="Bo‘sh vaqt kiritilmagan">Vaqt bo‘yicha qidirganda faqat bo‘sh vaqti bor hamrohlar chiqadi.</Empty> : res.data!.map((a) => (
          <div key={a.id} className="glass pad tight spread">
            <span>{formatInstant(a.starts_at)} — {formatInstant(a.ends_at)}</span>
            <button className="btn sm ghost" onClick={() => void remove(a.id)}>O‘chirish</button>
          </div>
        ))}
      </div>
    </Reveal>
  );
}
