import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
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
    toast.push('ok', 'Ko‘rib chiqildi deb qayd etildi.');
    setTarget(undefined);
    cur.reload();
  };

  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">
        Shikoyatlar va SOS — <b>qayd etilgan signallar</b>. Tizim hech kimga (favqulodda xizmatlar, politsiya, ishonchli
        kontaktlar) avtomatik xabar yubormaydi; “ko‘rib chiqildi” faqat operator ko‘rib chiqqanini bildiradi.
      </p>
      <div className="tabs">
        <button className="chip" aria-pressed={tab === 'reports'} onClick={() => { setOffset(0); setParams({}, { replace: true }); }}>Shikoyatlar</button>
        <button className="chip" aria-pressed={tab === 'sos'} onClick={() => { setOffset(0); setParams({ tab: 'sos' }, { replace: true }); }}>SOS signallari</button>
        <button className="chip" aria-pressed={onlyOpen} onClick={() => { setOffset(0); setOnlyOpen((v) => !v); }}>Faqat ko‘rib chiqilmaganlar</button>
        <button className="chip" onClick={cur.reload}>↻ Yangilash</button>
      </div>
      {cur.loading && !cur.data ? <Loading /> : cur.error ? <ErrorState error={cur.error} onRetry={cur.reload} /> : !cur.data?.length ? (
        <Empty title={tab === 'reports' ? 'Shikoyatlar yo‘q' : 'SOS signallari yo‘q'}>{onlyOpen ? 'Ko‘rib chiqilmagan yozuv yo‘q.' : 'Hozircha yozuv yo‘q.'}</Empty>
      ) : (
        <div className="stack">
          {tab === 'reports' && reports.data!.map((r, i) => (
            <Item key={r.id} index={i % 8}>
              <article className="glass pad stack">
                <div className="spread"><h3>{REPORT_CATEGORY[r.category] ?? r.category}</h3><span className={`tag ${r.acknowledged ? 'ok' : 'warn'}`}>{r.acknowledged ? 'Ko‘rib chiqilmoqda' : 'Ochiq'}</span></div>
                <p style={{ whiteSpace: 'pre-line' }}>{r.description}</p>
                <dl className="kv">
                  <dt>Yuborilgan</dt><dd>{formatInstant(r.created_at)}</dd>
                  <dt>Shikoyatchi</dt><dd><Id value={r.reporter_id} /></dd>
                  <dt>Shikoyat qilingan</dt><dd><Id value={r.reported_user_id} /></dd>
                  {r.booking_id && (<><dt>Bron</dt><dd><Id value={r.booking_id} /></dd></>)}
                </dl>
                {!r.acknowledged && <div><button className="btn sm" onClick={() => setTarget({ kind: 'reports', id: r.id })}>Ko‘rib chiqildi deb belgilash</button></div>}
              </article>
            </Item>
          ))}
          {tab === 'sos' && alerts.data!.map((a, i) => (
            <Item key={a.id} index={i % 8}>
              <article className="glass pad stack">
                <div className="spread"><h3>SOS signali</h3><span className={`tag ${a.acknowledged ? 'ok' : 'bad'}`}>{a.acknowledged ? 'Ko‘rib chiqilgan' : 'Ko‘rib chiqilmagan'}</span></div>
                <dl className="kv">
                  <dt>Qayd etilgan</dt><dd>{formatInstant(a.created_at)}</dd>
                  <dt>Signal yuborgan</dt><dd><Id value={a.creator_id} /></dd>
                  <dt>Bron</dt><dd><Id value={a.booking_id} /></dd>
                  <dt>Favqulodda xizmatga xabar</dt><dd>{a.emergency_service_contacted ? 'Server qayd etgan' : 'Yuborilmagan (tizim yubormaydi)'}</dd>
                </dl>
                {!a.acknowledged && <div><button className="btn sm" onClick={() => setTarget({ kind: 'alerts', id: a.id })}>Ko‘rib chiqildi deb belgilash</button></div>}
              </article>
            </Item>
          ))}
          <Pager offset={offset} count={cur.data!.length} onChange={setOffset} />
        </div>
      )}
      <ConfirmDialog
        open={!!target}
        title="Ko‘rib chiqildi deb belgilaysizmi?"
        body="Izoh o‘zgarmas yoziladi va audit jurnaliga tushadi. Bu amal hech kimga xabar yubormaydi."
        confirmLabel="Belgilash"
        reason={{ label: 'Operator izohi', min: 8, max: 2000 }}
        onConfirm={acknowledge}
        onClose={() => setTarget(undefined)}
      />
    </div>
  );
}
