import { useState } from 'react';
import { api, type Schemas } from '../api/client';
import { t } from '../i18n';
import { formatInstant } from '../lib/format';
import { ACCOUNT_STATUS, roleLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { Dialog, Empty, ErrorState, Loading, StatusTag, useToast } from '../ui/feedback';
import { Field, Select, TextArea } from '../ui/form';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../api/client';
import { Id, PAGE_SIZE, Pager } from './shared';

type UserRow = Schemas['AdminUserListItem'];
type Status = Schemas['AccountStatus'];

export function Users() {
  const { user: me } = useAuth();
  const [status, setStatus] = useState('');
  const [phone, setPhone] = useState('');
  const [phoneDraft, setPhoneDraft] = useState('');
  const [phoneErr, setPhoneErr] = useState<string>();
  const [offset, setOffset] = useState(0);
  const [target, setTarget] = useState<UserRow>();
  const res = useResource(
    (signal) => api.get<UserRow[]>('/admin/users', { query: { account_status: status || undefined, phone: phone || undefined, limit: PAGE_SIZE, offset }, signal }),
    [status, phone, offset],
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="glass pad row" style={{ alignItems: 'end' }}>
        <div style={{ flex: '1 1 180px' }}>
          <Select label={t('admin.audit.account_status')} value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
            <option value="">{t('discovery.all')}</option>
            {Object.entries(ACCOUNT_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </Select>
        </div>
        <form style={{ flex: '2 1 240px' }} className="row" onSubmit={(e) => {
          e.preventDefault();
          const v = phoneDraft.replace(/[\s()-]/g, '');
          if (v && !/^\+?\d{4,32}$/.test(v)) return setPhoneErr(t('users.phoneErr'));
          setPhoneErr(undefined);
          setOffset(0);
          setPhone(v);
        }}>
          <div style={{ flex: 1 }}><Field label={t('users.phoneSearch')} inputMode="tel" value={phoneDraft} onChange={(e) => setPhoneDraft(e.target.value)} error={phoneErr} hint={t('users.phoneHint')} /></div>
          <button className="btn sm">{t('discovery.search')}</button>
        </form>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title={t('users.none')} /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>ID</th><th>{t('account.phone')}</th><th>{t('account.roles')}</th><th>{t('admin.col.status')}</th><th>{t('common.city')}</th><th>{t('users.registered')}</th><th><span className="sr-only">{t('admin.col.action')}</span></th></tr></thead>
            <tbody>
              {res.data.map((u) => {
                const isAdmin = u.roles.includes('admin');
                const self = u.id === me?.id;
                return (
                  <tr key={u.id}>
                    <td><Id value={u.id} /></td>
                    <td className="mono">{u.phone_masked}</td>
                    <td>{u.roles.map(roleLabel).join(', ') || '—'}</td>
                    <td><StatusTag map={ACCOUNT_STATUS} value={u.account_status} /></td>
                    <td>{u.city ?? '—'}</td>
                    <td>{formatInstant(u.created_at)}</td>
                    <td>
                      {isAdmin || self ? <span className="hint">{self ? t('users.you') : t('users.adminAccount')}</span> : <button className="btn sm ghost" onClick={() => setTarget(u)}>{t('users.change')}</button>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {res.data && <Pager offset={offset} count={res.data.length} onChange={setOffset} />}
      <p className="hint">{t('users.note')}</p>
      {target && <StatusDialog user={target} onClose={() => setTarget(undefined)} onDone={() => { setTarget(undefined); res.reload(); }} />}
    </div>
  );
}

function StatusDialog({ user, onClose, onDone }: { user: UserRow; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [next, setNext] = useState<Status>(user.account_status === 'active' ? 'suspended' : 'active');
  const [reason, setReason] = useState('');
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const short = user.id.slice(0, 8);
  const ready = reason.trim().length >= 8 && typed.trim() === short && next !== user.account_status;
  const submit = async () => {
    setBusy(true);
    setErr(undefined);
    try {
      await api.post(`/admin/users/${user.id}/status`, { status: next, reason: reason.trim() });
      toast.push('ok', t('users.changed', { status: ACCOUNT_STATUS[next]?.label ?? next }));
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t('common.unexpected'));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open title={t('users.dialogTitle')} onClose={busy ? () => {} : onClose}>
      <div className="stack">
        <p>{t('users.userPrefix')}<b className="mono">{short}</b> · {user.phone_masked}{t('users.currentStatus')}<StatusTag map={ACCOUNT_STATUS} value={user.account_status} /></p>
        <Select label={t('users.newStatus')} value={next} onChange={(e) => setNext(e.target.value as Status)}>
          {Object.entries(ACCOUNT_STATUS).map(([k, v]) => <option key={k} value={k} disabled={k === user.account_status}>{v.label}</option>)}
        </Select>
        <TextArea label={t('users.reason')} value={reason} maxLength={2000} onChange={(e) => setReason(e.target.value)} hint={t('users.reasonHint')} />
        <Field label={t('users.typeId', { id: short })} value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        {next !== 'active' && <p className="banner bad">{t('users.blockBanner')}</p>}
        {err && <p className="err" role="alert">{err}</p>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn ghost" onClick={onClose} disabled={busy}>{t('common.cancel')}</button>
          <button className={`btn ${next === 'active' ? '' : 'danger'}`} disabled={!ready || busy} onClick={() => void submit()}>{busy && <span className="spinner" aria-hidden="true" />}{t('users.save')}</button>
        </div>
      </div>
    </Dialog>
  );
}
