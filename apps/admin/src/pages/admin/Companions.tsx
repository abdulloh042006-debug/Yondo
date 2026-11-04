import { useState } from 'react';
import { api, type Page } from '../../api';
import { formatDate, formatMoney } from '../../format';
import { Badge, Card, DecisionForm, Details, ErrorBox, Loading, PageHeader, Table, useAction, useAsync } from '../../ui';

interface ApplicationItem {
  id: string;
  user_id: string;
  display_name: string | null;
  status: string;
  revision: number;
  statement: string;
  submitted_at: string | null;
}

interface ProfileItem {
  id: string;
  user_id: string;
  display_name: string;
  content_status: string;
  revision: number;
  updated_at: string;
}

interface ContentReview {
  profile: {
    id: string; revision: number; display_name: string; bio: string; languages: string[];
    interests: string[]; content_status: string;
  };
  services: { id: string; service_code: string; description: string; price_minor: number; currency: string; unit_minutes: number }[];
  photos: { id: string; caption: string; width: number; height: number }[];
}

export function CompanionsPage() {
  const [tab, setTab] = useState<'applications' | 'content'>('applications');
  return (
    <div className="stack">
      <PageHeader title="Companion arizalari" subtitle="Ariza va kontent alohida tasdiqlanadi; aktivlashtirish uchun identity ham kerak." />
      <div className="tabs">
        <button className={tab === 'applications' ? 'active' : ''} onClick={() => setTab('applications')}>Arizalar</button>
        <button className={tab === 'content' ? 'active' : ''} onClick={() => setTab('content')}>Profil kontenti</button>
      </div>
      {tab === 'applications' ? <Applications /> : <Content />}
    </div>
  );
}

function Applications() {
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<ApplicationItem>>('/admin/companions/applications', { status: 'submitted', limit: 50 }),
    [],
  );
  const [selected, setSelected] = useState<ApplicationItem | null>(null);
  const action = useAction();
  return (
    <>
      <ErrorBox error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data && (
        <Table rows={data.items} onRow={setSelected} empty="Ko'rib chiqiladigan ariza yo'q" columns={[
          { header: 'Ism', render: (a) => a.display_name ?? a.user_id },
          { header: 'Holat', render: (a) => <Badge value={a.status} /> },
          { header: 'Yuborilgan', render: (a) => formatDate(a.submitted_at) },
          { header: 'Ariza matni', render: (a) => a.statement.slice(0, 80) || '—' },
        ]} />
      )}
      {selected && (
        <Card title={`Ariza: ${selected.display_name ?? selected.user_id}`}>
          <p>{selected.statement || <span className="muted">Matn yo'q</span>}</p>
          <DecisionForm
            busy={action.busy}
            actions={[['approve', 'Tasdiqlash'], ['reject', 'Rad etish']]}
            onSubmit={(decision, note) => void action.run(
              () => api.post(`/companions/admin/applications/${selected.id}/decision`, {
                decision, note, expected_revision: selected.revision,
              }),
              async () => { setSelected(null); await reload(); },
            )}
          />
        </Card>
      )}
    </>
  );
}

function Content() {
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<ProfileItem>>('/admin/companions/profiles', { content_status: 'pending', limit: 50 }),
    [],
  );
  const [selected, setSelected] = useState<ProfileItem | null>(null);
  return (
    <>
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && (
        <Table rows={data.items} onRow={setSelected} empty="Ko'rib chiqiladigan kontent yo'q" columns={[
          { header: 'Profil', render: (p) => p.display_name },
          { header: 'Holat', render: (p) => <Badge value={p.content_status} /> },
          { header: 'Revision', render: (p) => p.revision },
          { header: 'Yangilangan', render: (p) => formatDate(p.updated_at) },
        ]} />
      )}
      {selected && <ContentReviewCard item={selected} onDone={async () => { setSelected(null); await reload(); }} />}
    </>
  );
}

function ContentReviewCard({ item, onDone }: { item: ProfileItem; onDone: () => Promise<void> }) {
  const { data, error } = useAsync(async () => {
    const review = await api.get<ContentReview>(`/companions/admin/users/${item.user_id}/content-review`);
    const urls = await Promise.all(
      review.photos.map((photo) =>
        api.get<{ url: string }>(`/companions/admin/users/${item.user_id}/photos/${photo.id}/download`)
          .then((r) => r.url).catch(() => ''),
      ),
    );
    return { review, urls };
  }, [item.user_id]);
  const action = useAction();
  if (!data) return <><ErrorBox error={error} /><Loading show={!error} /></>;
  const { review, urls } = data;
  return (
    <Card title={`Kontent: ${review.profile.display_name}`}>
      <Details items={[
        ['Bio', review.profile.bio],
        ['Tillar', review.profile.languages.join(', ')],
        ['Qiziqishlar', review.profile.interests.join(', ')],
        ['Revision', review.profile.revision],
      ]} />
      <h2 style={{ marginTop: 14 }}>Xizmatlar</h2>
      <Table rows={review.services} columns={[
        { header: 'Xizmat', render: (s) => s.service_code },
        { header: 'Narx', render: (s) => `${formatMoney(s.price_minor, s.currency)} / ${s.unit_minutes} min` },
        { header: 'Tavsif', render: (s) => s.description || '—' },
      ]} />
      <h2 style={{ marginTop: 14 }}>Rasmlar</h2>
      <div className="photos">{urls.map((url, i) => url && <img key={i} src={url} alt={review.photos[i].caption} />)}</div>
      <ErrorBox error={action.error} />
      <DecisionForm
        busy={action.busy}
        actions={[['approve', 'Tasdiqlash'], ['reject', 'Rad etish']]}
        onSubmit={(decision, note) => void action.run(
          () => api.post(`/companions/admin/profiles/${review.profile.id}/decision`, {
            decision, note, expected_revision: review.profile.revision,
          }),
          onDone,
        )}
      />
    </Card>
  );
}
