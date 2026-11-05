import { Link } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { hasKey, t } from '../i18n';
import { formatInstant } from '../lib/format';
import { useResource } from '../lib/useResource';
import { Empty, ErrorState, Loading, useToast } from '../ui/feedback';

type Notice = Schemas['NotificationRead'];

const kindLabel = (kind: string) => {
  const key = `notif.kind.${kind}`;
  return hasKey(key) ? t(key) : kind;
};

export function Notifications() {
  const res = useResource((signal) => api.get<Notice[]>('/notifications', { query: { limit: 50 }, signal }), []);
  const toast = useToast();
  const unread = (res.data ?? []).filter((n) => !n.read_at).length;
  const markRead = (n: Notice) => {
    if (!n.read_at) void api.post(`/notifications/${n.id}/read`).catch(() => {});
  };
  const readAll = async () => {
    try {
      await api.post('/notifications/read-all');
      res.reload();
    } catch {
      toast.push('bad', t('common.actionFailed'));
    }
  };
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <div className="spread">
        <h1 style={{ margin: 0 }}>{t('nav.notifications')}</h1>
        {unread > 0 && <button className="btn ghost sm" onClick={() => void readAll()}>{t('notif.readAll')}</button>}
      </div>
      {res.loading && !res.data ? (
        <Loading />
      ) : res.error ? (
        <ErrorState error={res.error} onRetry={res.reload} />
      ) : !res.data?.length ? (
        <Empty title={t('notif.empty')} />
      ) : (
        <ul className="plain-list glass pad">
          {res.data.map((n) => (
            <li key={n.id}>
              <div className="spread">
                <span className="stack" style={{ gap: 2 }}>
                  <b>{kindLabel(n.kind)} {!n.read_at && <span className="tag warn">{t('notif.new')}</span>}</b>
                  <span className="hint">{formatInstant(n.created_at)}</span>
                </span>
                {n.booking_id && (
                  <Link className="btn sm ghost" to={`/bookings/${n.booking_id}`} onClick={() => markRead(n)}>{t('notif.open')}</Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
