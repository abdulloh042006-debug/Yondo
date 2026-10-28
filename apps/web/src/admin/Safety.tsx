import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant } from '../lib/format';
import { REPORT_CATEGORY } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, useToast } from '../ui/feedback';
import { Item } from '../ui/motion';
import { Id, PAGE_SIZE, Pager } from './shared';

type Report = Schemas['AdminReportRead'];
type Alert = Schemas['AdminAlertRead'];
type Target = { kind: 'reports' | 'alerts'; id: string };

export function Safety() {
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'sos' ? 'sos' : 'reports';
  const [onlyOpen, setOnlyOpen] = useState(true);
  const [offset, setOffset] = useState(0);
  const [target, setTarget] = useState<Target>();
  const toast = useToast();

  const reports = useResource(
    (signal) => (tab === 'reports' ? api.get<Report[]>('/admin/safety/reports', { query: { status: onlyOpen ? 'open' : undefined, limit: PAGE_SIZE, offset }, signal }) : Promise.resolve([] as Report[])),
    [tab, onlyOpen, offset],
  );
  const alerts = useResource(
    (signal) => (tab === 'sos' ? api.get<Alert[]>('/admin/safety/alerts', { query: { unacknowledged_only: onlyOpen, limit: PAGE_SIZE, offset }, signal }) : Promise.resolve([] as Alert[])),
    [tab, onlyOpen, offset],
  );
  const cur = tab === 'reports' ? reports : alerts;

  const acknowledge = async (note: string) => {
    if (!target) return;
    await api.post(`/admin/safety/${target.kind}/${target.id}/acknowledge`, { note });
    toast.push('ok', t('safety.ackDone'));
    setTarget(undefined);
    cur.reload();
  };

  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">
        {t('safety.bannerBefore')}<b>{t('safety.bannerBold')}</b>{t('safety.bannerAfter')}
      </p>
      <div className="tabs">
        <button className="chip" aria-pressed={tab === 'reports'} onClick={() => { setOffset(0); setParams({}, { replace: true }); }}>{t('safety.tab.reports')}</button>
        <button className="chip" aria-pressed={tab === 'sos'} onClick={() => { setOffset(0); setParams({ tab: 'sos' }, { replace: true }); }}>{t('safety.tab.sos')}</button>
        <button className="chip" aria-pressed={onlyOpen} onClick={() => { setOffset(0); setOnlyOpen((v) => !v); }}>{t('safety.onlyOpen')}</button>
        <button className="chip" onClick={cur.reload}>{t('safety.refresh')}</button>
      </div>
      {cur.loading && !cur.data ? <Loading /> : cur.error ? <ErrorState error={cur.error} onRetry={cur.reload} /> : !cur.data?.length ? (
        <Empty title={tab === 'reports' ? t('safety.noReports') : t('safety.noSos')}>{onlyOpen ? t('safety.noneUnreviewed') : t('safety.noneYet')}</Empty>
      ) : (
        <div className="stack">
          {tab === 'reports' && reports.data!.map((r, i) => (
            <Item key={r.id} index={i % 8}>
              <article className="glass pad stack">
                <div className="spread"><h3>{REPORT_CATEGORY[r.category] ?? r.category}</h3><span className={`tag ${r.acknowledged ? 'ok' : 'warn'}`}>{r.acknowledged ? t('safety.inReview') : t('safety.open')}</span></div>
                <p style={{ whiteSpace: 'pre-line' }}>{r.description}</p>
                <dl className="kv">
                  <dt>{t('safety.sent')}</dt><dd>{formatInstant(r.created_at)}</dd>
                  <dt>{t('safety.reporter')}</dt><dd><Id value={r.reporter_id} /></dd>
                  <dt>{t('safety.reported')}</dt><dd><Id value={r.reported_user_id} /></dd>
                  {r.booking_id && (<><dt>{t('common.booking')}</dt><dd><Id value={r.booking_id} /></dd></>)}
                </dl>
                {!r.acknowledged && <div><button className="btn sm" onClick={() => setTarget({ kind: 'reports', id: r.id })}>{t('safety.markReviewed')}</button></div>}
              </article>
            </Item>
          ))}
          {tab === 'sos' && alerts.data!.map((a, i) => (
            <Item key={a.id} index={i % 8}>
              <article className="glass pad stack">
                <div className="spread"><h3>{t('safety.sosTitle')}</h3><span className={`tag ${a.acknowledged ? 'ok' : 'bad'}`}>{a.acknowledged ? t('safety.sosReviewed') : t('safety.sosUnreviewed')}</span></div>
                <dl className="kv">
                  <dt>{t('safety.recorded')}</dt><dd>{formatInstant(a.created_at)}</dd>
                  <dt>{t('safety.sender')}</dt><dd><Id value={a.creator_id} /></dd>
                  <dt>{t('common.booking')}</dt><dd><Id value={a.booking_id} /></dd>
                  <dt>{t('safety.emergency')}</dt><dd>{a.emergency_service_contacted ? t('safety.emergencyYes') : t('safety.emergencyNo')}</dd>
                </dl>
                {!a.acknowledged && <div><button className="btn sm" onClick={() => setTarget({ kind: 'alerts', id: a.id })}>{t('safety.markReviewed')}</button></div>}
              </article>
            </Item>
          ))}
          <Pager offset={offset} count={cur.data!.length} onChange={setOffset} />
        </div>
      )}
      <ConfirmDialog
        open={!!target}
        title={t('safety.ackTitle')}
        body={t('safety.ackBody')}
        confirmLabel={t('safety.ackConfirm')}
        reason={{ label: t('safety.operatorNote'), min: 8, max: 2000 }}
        onConfirm={acknowledge}
        onClose={() => setTarget(undefined)}
      />
    </div>
  );
}
