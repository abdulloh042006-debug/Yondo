import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Page } from '../../api';
import { formatDate, formatMoney, parseMoney, shortId } from '../../format';
import { Badge, Card, Details, ErrorBox, Field, Loading, PageHeader, Select, Table, useAction, useAsync } from '../../ui';

interface Dispute {
  id: string; booking_id: string; opened_by: string; category: string; description: string;
  status: string; previous_booking_status: string; booking_outcome: string | null;
  refund_minor: number | null; payout_minor: number | null; resolution_note: string | null;
  created_at: string;
  evidence: { id: string; kind: string; note: string; url: string | null; uploaded_by: string; created_at: string }[];
}

export function DisputesPage() {
  const [status, setStatus] = useState('open');
  const { data, error, loading, reload } = useAsync(
    () => api.get<Page<Dispute>>('/admin/disputes', { status, limit: 50 }), [status],
  );
  const [selected, setSelected] = useState<Dispute | null>(null);
  return (
    <div className="stack">
      <PageHeader title="Nizolar (Dispute Center)" subtitle="Nizo ochilganda companion payouti ushlab turiladi." actions={<Select value={status} onChange={setStatus} options={['', 'open', 'under_review', 'resolved']} />} />
      <ErrorBox error={error} />
      <Loading show={loading && !data} />
      {data && <Table rows={data.items} onRow={setSelected} columns={[
        { header: 'Bron', render: (d) => shortId(d.booking_id) },
        { header: 'Kategoriya', render: (d) => d.category },
        { header: 'Avvalgi holat', render: (d) => <Badge value={d.previous_booking_status} /> },
        { header: 'Holat', render: (d) => <Badge value={d.status} /> },
        { header: 'Ochilgan', render: (d) => formatDate(d.created_at) },
      ]} />}
      {selected && <DisputeCard dispute={selected} onDone={async () => { setSelected(null); await reload(); }} />}
    </div>
  );
}

function DisputeCard({ dispute, onDone }: { dispute: Dispute; onDone: () => Promise<void> }) {
  const action = useAction();
  const [outcome, setOutcome] = useState('completed');
  const [refund, setRefund] = useState('0');
  const [payout, setPayout] = useState('0');
  const [note, setNote] = useState('');
  const refundMinor = parseMoney(refund);
  const payoutMinor = parseMoney(payout);
  return (
    <Card title={`Nizo: ${dispute.category}`} actions={<Link to={`/admin/bookings/${dispute.booking_id}`}>Bronni ochish</Link>}>
      <p>{dispute.description}</p>
      <Details items={[
        ['Ochgan', shortId(dispute.opened_by)],
        ['Natija', dispute.booking_outcome],
        ['Refund', formatMoney(dispute.refund_minor)],
        ['Payout', formatMoney(dispute.payout_minor)],
        ['Izoh', dispute.resolution_note],
      ]} />
      <h2 style={{ marginTop: 14 }}>Dalillar</h2>
      <Table rows={dispute.evidence} empty="Dalil yuklanmagan" columns={[
        { header: 'Kim', render: (e) => shortId(e.uploaded_by) },
        { header: 'Dalil', render: (e) => (e.url ? <a href={e.url} target="_blank" rel="noreferrer">Rasmni ochish</a> : e.note) },
        { header: 'Vaqt', render: (e) => formatDate(e.created_at) },
      ]} />
      {dispute.status !== 'resolved' && (
        <>
          {dispute.status === 'open' && (
            <button style={{ marginTop: 10 }} disabled={action.busy}
              onClick={() => void action.run(() => api.post(`/admin/disputes/${dispute.id}/review`), onDone)}>
              Ko'rib chiqishga olish
            </button>
          )}
          <h2 style={{ marginTop: 14 }}>Qaror</h2>
          <div className="form">
            <Field label="Bron natijasi">
              <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                <option value="completed">completed</option>
                <option value="no_show">no_show</option>
                <option value="cancelled">cancelled</option>
              </select>
            </Field>
            <Field label="Mijozga refund (UZS)"><input value={refund} onChange={(e) => setRefund(e.target.value)} /></Field>
            <Field label="Companion payout (UZS)"><input value={payout} onChange={(e) => setPayout(e.target.value)} /></Field>
          </div>
          <textarea placeholder="Qaror izohi" rows={2} value={note} onChange={(e) => setNote(e.target.value)} style={{ marginTop: 10 }} />
          <ErrorBox error={action.error} />
          <button className="primary" style={{ marginTop: 8 }}
            disabled={action.busy || !note.trim() || refundMinor === null || payoutMinor === null}
            onClick={() => void action.run(() => api.post(`/admin/disputes/${dispute.id}/resolve`, {
              outcome, refund_minor: refundMinor, payout_minor: payoutMinor, note,
            }), onDone)}>
            Qarorni saqlash
          </button>
        </>
      )}
    </Card>
  );
}
