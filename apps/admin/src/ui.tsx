import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { ApiError } from './api';

export function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await run());
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setLoading(false);
    }
  }, [run]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { data, error, loading, reload, setData };
}

export function messageOf(exc: unknown): string {
  if (exc instanceof ApiError) return `${exc.message} (${exc.code})`;
  return exc instanceof Error ? exc.message : String(exc);
}

/** Run a mutation, then refresh; returns an error message for inline display. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async (action: () => Promise<unknown>, after?: () => unknown) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await after?.();
      return true;
    } catch (exc) {
      setError(messageOf(exc));
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, run, setError };
}

export function PageHeader({ title, actions, subtitle }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null | undefined }) {
  return error ? (
    <div className="error" role="alert">
      {error}
    </div>
  ) : null;
}

export function Loading({ show }: { show: boolean }) {
  return show ? <div className="muted">Yuklanmoqda…</div> : null;
}

const TONES: Record<string, string> = {
  active: 'green', approved: 'green', verified: 'green', succeeded: 'green', completed: 'green',
  delivered: 'green', paid: 'green', published: 'green', resolved: 'green', confirmed: 'green',
  pending: 'amber', submitted: 'amber', open: 'amber', held: 'amber', scheduled: 'blue',
  accepted: 'blue', in_review: 'amber', under_review: 'amber', new: 'blue', preparing: 'blue',
  courier_assigned: 'blue', delivering: 'blue', verification_pending: 'amber', acknowledged: 'blue',
  restricted: 'amber', draft: 'gray', rejected: 'red', cancelled: 'red', failed: 'red',
  suspended: 'red', banned: 'red', disputed: 'red', no_show: 'red', hidden: 'gray',
  refunded: 'gray', partially_refunded: 'gray', dismissed: 'gray', withdrawn: 'gray',
};

export function Badge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="muted">—</span>;
  return <span className={`badge ${TONES[value] ?? 'gray'}`}>{value.replace(/_/g, ' ')}</span>;
}

export interface Column<T> {
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
}

export function Table<T>({ rows, columns, onRow, empty = 'Ma’lumot yo‘q' }: {
  rows: T[];
  columns: Column<T>[];
  onRow?: (row: T) => void;
  empty?: string;
}) {
  if (!rows.length) return <div className="empty">{empty}</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column, columnIndex) => (
              <th key={columnIndex} style={{ width: column.width }}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} onClick={onRow ? () => onRow(row) : undefined} className={onRow ? 'clickable' : ''}>
              {columns.map((column, columnIndex) => (
                <td key={columnIndex}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({ offset, nextOffset, limit, onChange }: {
  offset: number;
  nextOffset: number | null;
  limit: number;
  onChange: (offset: number) => void;
}) {
  return (
    <div className="pager">
      <button disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        ← Oldingi
      </button>
      <button disabled={nextOffset === null} onClick={() => nextOffset !== null && onChange(nextOffset)}>
        Keyingi →
      </button>
    </div>
  );
}

export function Select({ value, onChange, options, label }: {
  value: string;
  onChange: (value: string) => void;
  options: (string | [string, string])[];
  label?: string;
}) {
  return (
    <label className="inline">
      {label && <span>{label}</span>}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => {
          const [key, text] = Array.isArray(option) ? option : [option, option || 'Hammasi'];
          return (
            <option key={key} value={key}>
              {text}
            </option>
          );
        })}
      </select>
    </label>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Details({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="details">
      {items.map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

/** A compact "decision with note" form used by approval queues. */
export function DecisionForm({ actions, onSubmit, noteRequired = true, busy }: {
  actions: [string, string][];
  onSubmit: (action: string, note: string) => void;
  noteRequired?: boolean;
  busy?: boolean;
}) {
  const [note, setNote] = useState('');
  return (
    <div className="decision">
      <textarea placeholder="Izoh (sabab)" value={note} onChange={(event) => setNote(event.target.value)} rows={2} />
      <div className="row">
        {actions.map(([action, text]) => (
          <button
            key={action}
            className={action.includes('reject') || action.includes('ban') || action === 'hide' ? 'danger' : 'primary'}
            disabled={busy || (noteRequired && !note.trim())}
            onClick={() => onSubmit(action, note.trim())}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
