import { useState } from 'react';
import { api, ApiError, type Schemas } from '../api/client';
import { t, type Key } from '../i18n';
import { formatInstant } from '../lib/format';
import { DELETION_STATUS, SUPPORT_STATUS } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Select, TextArea } from '../ui/form';
import { Id } from './shared';

type Ticket = Schemas['AdminSupportRead'];
type Filter = '' | Ticket['status'];

/** In-app support queue: the only support channel (no e-mail, no phone). Every reply is audited server-side. */
export function SupportQueue() {
  const [filter, setFilter] = useState<Filter>('open');
  const res = useResource(
    (signal) => api.get<Ticket[]>('/admin/support/requests', { query: { status: filter || undefined }, signal }),
    [filter],
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">{t('admin.support.banner')}</p>
      <div style={{ maxWidth: 280 }}>
        <Select label={t('admin.col.status')} value={filter} onChange={(e) => setFilter(e.target.value as Filter)}>
          <option value="">{t('discovery.all')}</option>
          {Object.entries(SUPPORT_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </Select>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('admin.support.none')} /> : (
        <div className="stack">
          {res.data.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} onDone={res.reload} />)}
        </div>
      )}
    </div>
  );
}

function TicketCard({ ticket, onDone }: { ticket: Ticket; onDone: () => void }) {
  const toast = useToast();
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const send = async (close: boolean) => {
    setBusy(true);
    try {
      await api.post(`/admin/support/requests/${ticket.id}/reply`, { reply: reply.trim(), close });
      toast.push('ok', t('admin.support.sent'));
      setReply('');
      onDone();
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };
  return (
    <article className="glass pad stack">
      <div className="spread">
        <b>{t(`help.support.cat.${ticket.category}` as Key)}</b>
        <StatusTag map={SUPPORT_STATUS} value={ticket.status} />
      </div>
      <p className="hint">{t('admin.col.user')}: <Id value={ticket.user_id} /> · {formatInstant(ticket.created_at)}</p>
      <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{ticket.message}</p>
      {ticket.reply && (
        <p className="banner" style={{ whiteSpace: 'pre-wrap' }}><b>{t('help.support.reply')}:</b> {ticket.reply}</p>
      )}
      {ticket.status !== 'closed' && (
        <>
          <TextArea label={t('admin.support.replyLabel')} rows={3} maxLength={4000} value={reply} onChange={(e) => setReply(e.target.value)} />
          <div className="row">
            <button className="btn sm" disabled={busy || reply.trim().length < 2} onClick={() => void send(false)}>{t('admin.support.send')}</button>
            <button className="btn sm ghost" disabled={busy || reply.trim().length < 2} onClick={() => void send(true)}>{t('admin.support.sendClose')}</button>
          </div>
        </>
      )}
    </article>
  );
}

export function Deletions() {
  const res = useResource((signal) => api.get<Schemas['AdminDeletionRead'][]>('/admin/account-deletions', { signal }), []);
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const run = async () => {
    const out = await api.post<Schemas['DeletionRun']>('/admin/account-deletions/process-due');
    toast.push('ok', t('admin.deletions.done', { erased: out.erased.length, skipped: out.skipped_open_bookings.length }));
    setConfirming(false);
    res.reload();
  };
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="banner">{t('admin.deletions.banner')}</p>
      <div><button className="btn danger" onClick={() => setConfirming(true)}>{t('admin.deletions.run')}</button></div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('admin.deletions.none')} /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>{t('admin.col.user')}</th><th>{t('admin.col.status')}</th><th>{t('admin.col.created')}</th><th>{t('admin.col.due')}</th></tr></thead>
            <tbody>{res.data.map((d) => (
              <tr key={d.id}><td><Id value={d.user_id} /></td><td><StatusTag map={DELETION_STATUS} value={d.status} /></td><td>{formatInstant(d.requested_at)}</td><td>{formatInstant(d.completed_at ?? d.due_at)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <ConfirmDialog open={confirming} danger title={t('admin.deletions.runTitle')} body={t('admin.deletions.runBody')} confirmLabel={t('admin.deletions.run')} onConfirm={run} onClose={() => setConfirming(false)} />
    </div>
  );
}
