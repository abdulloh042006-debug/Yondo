import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { t, type Key } from '../i18n';
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
  { id: 'submitted', label: 'apps.filter.submitted', q: { status: 'submitted' } },
  { id: 'content', label: 'apps.filter.content', q: { content_status: 'pending' } },
  { id: 'approved', label: 'apps.filter.approved', q: { status: 'approved' } },
  { id: 'rejected', label: 'apps.filter.rejected', q: { status: 'rejected' } },
  { id: 'all', label: 'discovery.all', q: {} },
] as const satisfies ReadonlyArray<{ id: string; label: Key; q: Record<string, string> }>;

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
      <div className="tabs" role="group" aria-label={t('apps.filterAria')}>
        {FILTERS.map((f) => (
          <button key={f.id} className="chip" aria-pressed={f.id === active.id} onClick={() => { setOffset(0); setParams(f.id === 'content' ? { content_status: 'pending' } : f.id === 'all' ? {} : { status: f.id }, { replace: true }); }}>
            {t(f.label)}
          </button>
        ))}
        <button className="chip" onClick={res.reload}>{t('safety.refresh')}</button>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? (
        <Empty title={t('apps.none')}>{t('apps.noneBody')}</Empty>
      ) : (
        <div className="stack">
          {res.data.map((r, i) => (
            <Item key={r.id} index={i % 8}>
              <Link to={`/admin/applications/${r.id}`} className="glass pad tight spread" style={{ textDecoration: 'none' }}>
                <div>
                  <h3>{r.display_name ?? t('apps.noProfile')}</h3>
                  <p className="hint">{t('apps.rowMeta', { date: formatInstant(r.submitted_at ?? r.created_at) })}<span className="mono">{r.user_id.slice(0, 8)}</span></p>
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
    toast.push('ok', decision.decision === 'approve' ? t('apps.decidedApprove') : t('apps.decidedReject'));
    setDecision(undefined);
    refresh();
  };

  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="row">
        <Link to="/admin/applications" className="chip" style={{ textDecoration: 'none' }}>{t('apps.back')}</Link>
        <button className="chip" onClick={refresh}>{t('apps.refreshState')}</button>
      </div>
      <p className="banner">
        <b>{t('apps.noteBold')}</b>{t('apps.noteBody')}
      </p>

      <section className="glass pad stack" aria-labelledby="h-app">
        <div className="spread"><h2 id="h-app">{t('studio.tab.application')}</h2><StatusTag map={APPLICATION_STATUS} value={a.status} /></div>
        <dl className="kv">
          <dt>{t('apps.appId')}</dt><dd><Id value={a.id} /></dd>
          <dt>{t('apps.user')}</dt><dd><Id value={a.user_id} /></dd>
          <dt>{t('apps.version')}</dt><dd>{a.revision}</dd>
          <dt>{t('apps.lastNote')}</dt><dd>{a.review_note ?? '—'}</dd>
        </dl>
        <div><h3>{t('apps.statement')}</h3><p style={{ whiteSpace: 'pre-line' }}>{a.statement || <span className="hint">{t('apps.empty')}</span>}</p></div>
        {a.status === 'submitted' ? (
          <div className="row">
            <button className="btn" onClick={() => setDecision({ target: 'application', decision: 'approve' })}>{t('apps.approveApp')}</button>
            <button className="btn danger" onClick={() => setDecision({ target: 'application', decision: 'reject' })}>{t('apps.rejectApp')}</button>
          </div>
        ) : <p className="hint">{t('apps.onlySubmittedApp')}</p>}
      </section>

      <section className="glass pad stack" aria-labelledby="h-prof">
        <div className="spread"><h2 id="h-prof">{t('studio.status.content')}</h2>{p && <StatusTag map={CONTENT_STATUS} value={p.content_status} />}</div>
        {review.data === undefined && !review.error ? <Loading rows={1} /> : review.error ? <ErrorState error={review.error} onRetry={review.reload} /> : !p ? (
          <p className="hint">{t('apps.noProfileYet')}</p>
        ) : (
          <>
            <dl className="kv">
              <dt>{t('apps.name')}</dt><dd>{p.display_name}</dd>
              <dt>{t('apps.version')}</dt><dd>{p.revision}</dd>
              <dt>{t('profile.languages')}</dt><dd>{p.languages.join(', ') || '—'}</dd>
              <dt>{t('profile.interests')}</dt><dd>{p.interests.join(', ') || '—'}</dd>
              <dt>{t('apps.activationRequested')}</dt><dd>{p.activation_requested ? t('apps.yes') : t('apps.no')}</dd>
              <dt>{t('apps.lastNote')}</dt><dd>{p.review_note ?? '—'}</dd>
            </dl>
            <div><h3>{t('common.description')}</h3><p style={{ whiteSpace: 'pre-line' }}>{p.bio || <span className="hint">{t('apps.empty')}</span>}</p></div>
            <div>
              <h3>{t('studio.tab.services')}</h3>
              {review.data!.services.length === 0 ? <p className="hint">{t('apps.noService')}</p> : review.data!.services.map((s) => (
                <p key={s.id}>{serviceLabel(s.service_code)} — {formatMoney(s.price_minor, s.currency)} / {t('common.minutesShort', { n: s.unit_minutes })}{s.description ? ` · ${s.description}` : ''}</p>
              ))}
            </div>
            <div>
              <h3>{t('apps.photos', { n: review.data!.photos.length })}</h3>
              <div className="gallery">{review.data!.photos.map((ph) => <ReviewPhoto key={ph.id} userId={a.user_id} photoId={ph.id} caption={ph.caption} />)}</div>
            </div>
            {p.content_status === 'pending' ? (
              <div className="row">
                <button className="btn" onClick={() => setDecision({ target: 'content', decision: 'approve' })}>{t('apps.approveContent')}</button>
                <button className="btn danger" onClick={() => setDecision({ target: 'content', decision: 'reject' })}>{t('apps.rejectContent')}</button>
              </div>
            ) : <p className="hint">{t('apps.onlyPendingContent')}</p>}
          </>
        )}
      </section>

      <section className="glass pad stack" aria-labelledby="h-hist">
        <h2 id="h-hist">{t('apps.history')}</h2>
        {history.error ? <ErrorState error={history.error} onRetry={history.reload} /> : !history.data?.length ? <p className="hint">{t('apps.historyNone')}</p> : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {history.data.map((h) => <li key={h.id}><span className="mono">{h.action}</span> — {formatInstant(h.created_at)} — “{h.reason}”</li>)}
          </ul>
        )}
      </section>

      <ConfirmDialog
        open={!!decision}
        danger={decision?.decision === 'reject'}
        title={decision ? t(`apps.dlg.${decision.target === 'application' ? 'app' : 'content'}.${decision.decision}`) : ''}
        body={decision?.decision === 'reject'
          ? t('apps.rejectBody')
          : t('apps.approveBody')}
        confirmLabel={decision?.decision === 'approve' ? t('apps.confirmApprove') : t('bookings.decline.confirm')}
        reason={{ label: decision?.decision === 'reject' ? t('apps.reasonReject') : t('apps.reasonNote'), min: decision?.decision === 'reject' ? 8 : 3, max: 2000 }}
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
      {res.data ? <img src={res.data.url} alt={caption || t('apps.reviewPhotoAlt')} loading="lazy" /> : <span className="hint">{res.error ? res.error.message : '…'}</span>}
    </div>
  );
}
