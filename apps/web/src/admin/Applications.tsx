import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { formatInstant, formatMoney } from '../lib/format';
import { APPLICATION_STATUS, CONTENT_STATUS, serviceLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Item } from '../ui/motion';
import { Id, PAGE_SIZE, Pager } from './shared';

type Row = Schemas['AdminApplicationSummary'];
type Application = Schemas['ApplicationResponse'];
type Review = Schemas['ContentReview'];
type Audit = Schemas['AdminAuditRead'];

const FILTERS = [
  { id: 'submitted', label: 'Ariza kutmoqda', q: { status: 'submitted' } },
  { id: 'content', label: 'Kontent kutmoqda', q: { content_status: 'pending' } },
  { id: 'approved', label: 'Tasdiqlangan', q: { status: 'approved' } },
  { id: 'rejected', label: 'Rad etilgan', q: { status: 'rejected' } },
  { id: 'all', label: 'Hammasi', q: {} },
] as const;

export function Applications() {
  const [params, setParams] = useSearchParams();
  const initial = params.get('content_status') ? 'content' : (params.get('status') ?? 'submitted');
  const active = FILTERS.find((f) => f.id === initial) ?? FILTERS[0];
  const [offset, setOffset] = useState(0);
  const res = useResource(
    (signal) => api.get<Row[]>('/companions/admin/applications', { query: { ...active.q, limit: PAGE_SIZE, offset }, signal }),
    [active.id, offset],
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="tabs" role="group" aria-label="Filtr">
        {FILTERS.map((f) => (
          <button key={f.id} className="chip" aria-pressed={f.id === active.id} onClick={() => { setOffset(0); setParams(f.id === 'content' ? { content_status: 'pending' } : f.id === 'all' ? {} : { status: f.id }, { replace: true }); }}>
            {f.label}
          </button>
        ))}
        <button className="chip" onClick={res.reload}>↻ Yangilash</button>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? (
        <Empty title="Bu filtr bo‘yicha arizalar yo‘q">Yangi arizalar kelganda shu yerda ko‘rinadi.</Empty>
      ) : (
        <div className="stack">
          {res.data.map((r, i) => (
            <Item key={r.id} index={i % 8}>
              <Link to={`/admin/applications/${r.id}`} className="glass pad tight spread" style={{ textDecoration: 'none' }}>
                <div>
                  <h3>{r.display_name ?? 'Profil hali yaratilmagan'}</h3>
                  <p className="hint">Ariza {formatInstant(r.submitted_at ?? r.created_at)} · foydalanuvchi <span className="mono">{r.user_id.slice(0, 8)}</span></p>
                </div>
                <div className="row">
                  <StatusTag map={APPLICATION_STATUS} value={r.status} />
                  {r.content_status && <StatusTag map={CONTENT_STATUS} value={r.content_status} />}
                </div>
              </Link>
            </Item>
          ))}
          <Pager offset={offset} count={res.data.length} onChange={setOffset} />
        </div>
      )}
    </div>
  );
}

type Decision = { target: 'application' | 'content'; decision: 'approve' | 'reject' };

export function ApplicationDetail() {
  const { id = '' } = useParams();
  const toast = useToast();
  const app = useResource((signal) => api.get<Application>(`/companions/admin/applications/${id}`, { signal }), [id]);
  const userId = app.data?.user_id;
  const review = useResource(
    async (signal) => {
      if (!userId) return null;
      try {
        return await api.get<Review>(`/companions/admin/users/${userId}/content-review`, { signal });
      } catch (e) {
        if ((e as { status?: number }).status === 404) return null; // applicant has not created a profile yet
        throw e;
      }
    },
    [userId],
  );
  const history = useResource(
    async (signal) => (userId ? api.get<Audit[]>('/admin/audit-events', { query: { target_id: userId, limit: 50 }, signal }) : []),
    [userId],
  );
  const [decision, setDecision] = useState<Decision>();

  if (app.loading && !app.data) return <Loading />;
  if (app.error) return <ErrorState error={app.error} onRetry={app.reload} />;
  const a = app.data!;
  const p = review.data?.profile;
  const refresh = () => { app.reload(); review.reload(); history.reload(); };

  const submit = async (note: string) => {
    if (!decision) return;
    if (decision.target === 'application') {
      await api.post(`/companions/admin/applications/${a.id}/decision`, { decision: decision.decision, expected_revision: a.revision, note });
    } else {
      await api.post(`/companions/admin/profiles/${p!.id}/decision`, { decision: decision.decision, expected_revision: p!.revision, note });
    }
    toast.push('ok', decision.decision === 'approve' ? 'Qaror saqlandi: tasdiqlandi.' : 'Qaror saqlandi: rad etildi.');
    setDecision(undefined);
    refresh();
  };

  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="row">
        <Link to="/admin/applications" className="chip" style={{ textDecoration: 'none' }}>← Arizalar</Link>
        <button className="chip" onClick={refresh}>↻ Holatni yangilash</button>
      </div>
      <p className="banner">
        <b>Eslatma:</b> kontent tasdig‘i shaxs tasdig‘i emas. Profil kontenti tasdiqlansa ham, shaxs tekshiruvi (alohida
        integratsiya) ulanmaguncha profil ommaga chiqmaydi — bu server tomonidan majburlanadi.
      </p>

      <section className="glass pad stack" aria-labelledby="h-app">
        <div className="spread"><h2 id="h-app">Ariza</h2><StatusTag map={APPLICATION_STATUS} value={a.status} /></div>
        <dl className="kv">
          <dt>Ariza ID</dt><dd><Id value={a.id} /></dd>
          <dt>Foydalanuvchi</dt><dd><Id value={a.user_id} /></dd>
          <dt>Versiya</dt><dd>{a.revision}</dd>
          <dt>Izoh (oxirgi qaror)</dt><dd>{a.review_note ?? '—'}</dd>
        </dl>
        <div><h3>Arizachi bayoni</h3><p style={{ whiteSpace: 'pre-line' }}>{a.statement || <span className="hint">Bo‘sh</span>}</p></div>
        {a.status === 'submitted' ? (
          <div className="row">
            <button className="btn" onClick={() => setDecision({ target: 'application', decision: 'approve' })}>Arizani tasdiqlash</button>
            <button className="btn danger" onClick={() => setDecision({ target: 'application', decision: 'reject' })}>Arizani rad etish</button>
          </div>
        ) : <p className="hint">Faqat “Ko‘rib chiqilmoqda” holatidagi arizaga qaror qabul qilinadi.</p>}
      </section>

      <section className="glass pad stack" aria-labelledby="h-prof">
        <div className="spread"><h2 id="h-prof">Profil kontenti</h2>{p && <StatusTag map={CONTENT_STATUS} value={p.content_status} />}</div>
        {review.data === undefined && !review.error ? <Loading rows={1} /> : review.error ? <ErrorState error={review.error} onRetry={review.reload} /> : !p ? (
          <p className="hint">Arizachi hali profil yaratmagan.</p>
        ) : (
          <>
            <dl className="kv">
              <dt>Ism</dt><dd>{p.display_name}</dd>
              <dt>Versiya</dt><dd>{p.revision}</dd>
              <dt>Tillar</dt><dd>{p.languages.join(', ') || '—'}</dd>
              <dt>Qiziqishlar</dt><dd>{p.interests.join(', ') || '—'}</dd>
              <dt>Faollashtirish so‘ralgan</dt><dd>{p.activation_requested ? 'Ha' : 'Yo‘q'}</dd>
              <dt>Izoh (oxirgi qaror)</dt><dd>{p.review_note ?? '—'}</dd>
            </dl>
            <div><h3>Tavsif</h3><p style={{ whiteSpace: 'pre-line' }}>{p.bio || <span className="hint">Bo‘sh</span>}</p></div>
            <div>
              <h3>Xizmatlar</h3>
              {review.data!.services.length === 0 ? <p className="hint">Xizmat yo‘q</p> : review.data!.services.map((s) => (
                <p key={s.id}>{serviceLabel(s.service_code)} — {formatMoney(s.price_minor, s.currency)} / {s.unit_minutes} daq{s.description ? ` · ${s.description}` : ''}</p>
              ))}
            </div>
            <div>
              <h3>Rasmlar ({review.data!.photos.length})</h3>
              <div className="gallery">{review.data!.photos.map((ph) => <ReviewPhoto key={ph.id} userId={a.user_id} photoId={ph.id} caption={ph.caption} />)}</div>
            </div>
            {p.content_status === 'pending' ? (
              <div className="row">
                <button className="btn" onClick={() => setDecision({ target: 'content', decision: 'approve' })}>Kontentni tasdiqlash</button>
                <button className="btn danger" onClick={() => setDecision({ target: 'content', decision: 'reject' })}>Kontentni rad etish</button>
              </div>
            ) : <p className="hint">Faqat “Ko‘rib chiqilmoqda” kontentga qaror qabul qilinadi.</p>}
          </>
        )}
      </section>

      <section className="glass pad stack" aria-labelledby="h-hist">
        <h2 id="h-hist">Tarix (audit jurnali)</h2>
        {history.error ? <ErrorState error={history.error} onRetry={history.reload} /> : !history.data?.length ? <p className="hint">Bu foydalanuvchi bo‘yicha yozuvlar yo‘q.</p> : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {history.data.map((h) => <li key={h.id}><span className="mono">{h.action}</span> — {formatInstant(h.created_at)} — “{h.reason}”</li>)}
          </ul>
        )}
      </section>

      <ConfirmDialog
        open={!!decision}
        danger={decision?.decision === 'reject'}
        title={decision ? `${decision.target === 'application' ? 'Ariza' : 'Profil kontenti'}ni ${decision.decision === 'approve' ? 'tasdiqlash' : 'rad etish'}` : ''}
        body={decision?.decision === 'reject'
          ? 'Rad etish sababi arizachiga ko‘rinadi. Qaror audit jurnaliga yoziladi va qaytarib bo‘lmaydi (arizachi qayta yuborishi mumkin).'
          : 'Qaror audit jurnaliga yoziladi. Bu shaxs tasdig‘i emas.'}
        confirmLabel={decision?.decision === 'approve' ? 'Tasdiqlash' : 'Rad etish'}
        reason={{ label: decision?.decision === 'reject' ? 'Rad etish sababi' : 'Izoh', min: decision?.decision === 'reject' ? 8 : 3, max: 2000 }}
        onConfirm={submit}
        onClose={() => setDecision(undefined)}
      />
    </div>
  );
}

function ReviewPhoto({ userId, photoId, caption }: { userId: string; photoId: string; caption: string }) {
  const res = useResource((signal) => api.get<Schemas['PhotoDownload']>(`/companions/admin/users/${userId}/photos/${photoId}/download`, { signal }), [userId, photoId]);
  return (
    <div className="media" style={{ borderRadius: 'var(--r-sm)', aspectRatio: '3 / 4' }}>
      {res.data ? <img src={res.data.url} alt={caption || 'Ko‘rib chiqilayotgan rasm'} loading="lazy" /> : <span className="hint">{res.error ? res.error.message : '…'}</span>}
    </div>
  );
}
