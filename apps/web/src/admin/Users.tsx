import { useState } from 'react';
import { api, type Schemas } from '../api/client';
import { formatInstant } from '../lib/format';
import { ACCOUNT_STATUS } from '../lib/labels';
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
          <Select label="Hisob holati" value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
            <option value="">Hammasi</option>
            {Object.entries(ACCOUNT_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </Select>
        </div>
        <form style={{ flex: '2 1 240px' }} className="row" onSubmit={(e) => {
          e.preventDefault();
          const v = phoneDraft.replace(/[\s()-]/g, '');
          if (v && !/^\+?\d{4,32}$/.test(v)) return setPhoneErr('Telefon bo‘lagini raqam bilan kiriting (kamida 4 ta raqam).');
          setPhoneErr(undefined);
          setOffset(0);
          setPhone(v);
        }}>
          <div style={{ flex: 1 }}><Field label="Telefon bo‘yicha qidirish" inputMode="tel" value={phoneDraft} onChange={(e) => setPhoneDraft(e.target.value)} error={phoneErr} hint="Raqamning bir qismi" /></div>
          <button className="btn sm">Qidirish</button>
        </form>
      </div>
      {res.loading && !res.data ? <Loading /> : res.error ? <ErrorState error={res.error} onRetry={res.reload} /> : !res.data?.length ? <Empty title="Foydalanuvchi topilmadi" /> : (
        <div className="glass table-wrap">
          <table className="data">
            <thead><tr><th>ID</th><th>Telefon</th><th>Rollar</th><th>Holat</th><th>Shahar</th><th>Ro‘yxatdan o‘tgan</th><th><span className="sr-only">Amal</span></th></tr></thead>
            <tbody>
              {res.data.map((u) => {
                const isAdmin = u.roles.includes('admin');
                const self = u.id === me?.id;
                return (
                  <tr key={u.id}>
                    <td><Id value={u.id} /></td>
                    <td className="mono">{u.phone_masked}</td>
                    <td>{u.roles.join(', ') || '—'}</td>
                    <td><StatusTag map={ACCOUNT_STATUS} value={u.account_status} /></td>
                    <td>{u.city ?? '—'}</td>
                    <td>{formatInstant(u.created_at)}</td>
                    <td>
                      {isAdmin || self ? <span className="hint">{self ? 'Siz' : 'Admin hisobi'}</span> : <button className="btn sm ghost" onClick={() => setTarget(u)}>Holatni o‘zgartirish</button>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {res.data && <Pager offset={offset} count={res.data.length} onChange={setOffset} />}
      <p className="hint">Telefon raqamlari maxfiylik uchun qisman yashirilgan. Administrator hisoblariga bu yerdan ta’sir qilib bo‘lmaydi.</p>
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
      toast.push('ok', `Hisob holati o‘zgartirildi: ${ACCOUNT_STATUS[next]?.label ?? next}.`);
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Kutilmagan xatolik yuz berdi.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open title="Hisob holatini o‘zgartirish" onClose={busy ? () => {} : onClose}>
      <div className="stack">
        <p>Foydalanuvchi: <b className="mono">{short}</b> · {user.phone_masked} · hozirgi holat: <StatusTag map={ACCOUNT_STATUS} value={user.account_status} /></p>
        <Select label="Yangi holat" value={next} onChange={(e) => setNext(e.target.value as Status)}>
          {Object.entries(ACCOUNT_STATUS).map(([k, v]) => <option key={k} value={k} disabled={k === user.account_status}>{v.label}</option>)}
        </Select>
        <TextArea label="Sabab (audit jurnaliga yoziladi)" value={reason} maxLength={2000} onChange={(e) => setReason(e.target.value)} hint="Kamida 8 belgi." />
        <Field label={`Tasdiqlash uchun ID boshini kiriting: ${short}`} value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        {next !== 'active' && <p className="banner bad">To‘xtatilgan yoki bloklangan hisob tizimga kira olmaydi va yangi amallarni bajara olmaydi.</p>}
        {err && <p className="err" role="alert">{err}</p>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn ghost" onClick={onClose} disabled={busy}>Bekor qilish</button>
          <button className={`btn ${next === 'active' ? '' : 'danger'}`} disabled={!ready || busy} onClick={() => void submit()}>{busy && <span className="spinner" aria-hidden="true" />}Holatni saqlash</button>
        </div>
      </div>
    </Dialog>
  );
}
