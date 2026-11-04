import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, type Page } from '../../api';
import { formatDate } from '../../format';
import {
  Badge, Card, DecisionForm, Details, ErrorBox, Loading, PageHeader, Pager, Select, Table,
  useAction, useAsync,
} from '../../ui';

interface AdminUser {
  id: string;
  phone_number: string;
  display_name: string | null;
  age: number | null;
  gender: string | null;
  city: string | null;
  account_status: string;
  roles: string[];
  identity_status: string;
  created_at: string;
}

interface UserDetail extends AdminUser {
  bookings_as_customer: number;
  bookings_as_companion: number;
  reports_received: number;
  reports_filed: number;
  history: { id: string; action: string; reason: string; created_at: string }[];
}

const LIMIT = 20;

export function UsersPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [role, setRole] = useState('');
  const [offset, setOffset] = useState(0);
  const { data, error, loading } = useAsync(
    () => api.get<Page<AdminUser>>('/admin/users', { q: search, status, role, offset, limit: LIMIT }),
    [search, status, role, offset],
  );
  return (
    <div className="stack">
      <PageHeader title="Foydalanuvchilar" />
      <form className="row" onSubmit={(e) => { e.preventDefault(); setOffset(0); setSearch(q); }}>
        <input placeholder="Telefon yoki ism" value={q} onChange={(e) => setQ(e.target.value)} />
        <button>Qidirish</button>
        <Select label="Holat" value={status} onChange={(v) => { setStatus(v); setOffset(0); }}
          options={['', 'active', 'verification_pending', 'restricted', 'suspended', 'banned']} />
        <Select label="Rol" value={role} onChange={(v) => { setRole(v); setOffset(0); }}
          options={['', 'customer', 'companion', 'vendor', 'admin']} />
      </form>
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <>
          <Table
            rows={data.items}
            onRow={(row) => navigate(`/admin/users/${row.id}`)}
            columns={[
              { header: 'Ism', render: (u) => u.display_name ?? '—' },
              { header: 'Telefon', render: (u) => u.phone_number },
              { header: 'Rollar', render: (u) => u.roles.join(', ') || '—' },
              { header: 'Holat', render: (u) => <Badge value={u.account_status} /> },
              { header: 'Identity', render: (u) => <Badge value={u.identity_status} /> },
              { header: 'Shahar', render: (u) => u.city ?? '—' },
              { header: "Ro'yxatdan o'tgan", render: (u) => formatDate(u.created_at) },
            ]}
          />
          <Pager offset={offset} nextOffset={data.next_offset} limit={LIMIT} onChange={setOffset} />
        </>
      )}
    </div>
  );
}

export function UserDetailPage() {
  const { userId } = useParams();
  const { data, error, reload } = useAsync(() => api.get<UserDetail>(`/admin/users/${userId}`), [userId]);
  const action = useAction();
  const [role, setRole] = useState('vendor');
  if (!data) return <><ErrorBox error={error} /><Loading show={!error} /></>;
  return (
    <div className="stack">
      <PageHeader title={data.display_name ?? data.phone_number} subtitle={data.id} />
      <ErrorBox error={action.error} />
      <Card title="Ma'lumotlar">
        <Details items={[
          ['Telefon', data.phone_number],
          ['Holat', <Badge value={data.account_status} />],
          ['Identity', <Badge value={data.identity_status} />],
          ['Rollar', data.roles.join(', ') || '—'],
          ['Yosh / jins', `${data.age ?? '—'} / ${data.gender ?? '—'}`],
          ['Shahar', data.city],
          ['Mijoz sifatida bronlar', data.bookings_as_customer],
          ['Companion sifatida bronlar', data.bookings_as_companion],
          ['Unga reportlar', data.reports_received],
          ['U yuborgan reportlar', data.reports_filed],
          ["Ro'yxatdan o'tgan", formatDate(data.created_at)],
        ]} />
      </Card>
      <div className="grid2">
        <Card title="Moderatsiya (TZ §39)">
          <p className="muted">Suspend/ban sessiyalarni bekor qiladi va kelgusi bronlarni to'liq refund bilan bekor qiladi.</p>
          <DecisionForm
            busy={action.busy}
            actions={[['warn', 'Ogohlantirish'], ['restrict', 'Cheklash'], ['suspend', "To'xtatish"], ['ban', 'Bloklash'], ['reinstate', 'Tiklash']]}
            onSubmit={(act, note) => void action.run(() => api.post(`/admin/users/${userId}/moderation`, { action: act, reason: note }), reload)}
          />
        </Card>
        <Card title="Rollar">
          <div className="row">
            <Select value={role} onChange={setRole} options={[['customer', 'customer'], ['companion', 'companion'], ['vendor', 'vendor'], ['admin', 'admin']]} />
            <button className="primary" disabled={action.busy}
              onClick={() => void action.run(() => api.post(`/admin/users/${userId}/roles`, { role, action: 'grant' }), reload)}>Berish</button>
            <button className="danger" disabled={action.busy}
              onClick={() => void action.run(() => api.post(`/admin/users/${userId}/roles`, { role, action: 'revoke' }), reload)}>Olib tashlash</button>
          </div>
        </Card>
      </div>
      <Card title="Tarix">
        <Table rows={data.history} columns={[
          { header: 'Amal', render: (h) => h.action },
          { header: 'Sabab', render: (h) => h.reason || '—' },
          { header: 'Vaqt', render: (h) => formatDate(h.created_at) },
        ]} />
      </Card>
    </div>
  );
}
