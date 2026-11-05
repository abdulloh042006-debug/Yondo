import { Link } from 'react-router-dom';
import { api, type Schemas } from '../api/client';
import { t } from '../i18n';
import { useResource } from '../lib/useResource';
import { ErrorState, Loading } from '../ui/feedback';
import { Counter, Item } from '../ui/motion';

type Summary = Schemas['AdminSummary'];
type SafetySummary = { open_reports: number; unacknowledged_sos: number; emergency_dispatch_configured: boolean };

export function Dashboard() {
  const summary = useResource((signal) => api.get<Summary>('/admin/summary', { signal }), []);
  const safety = useResource((signal) => api.get<SafetySummary>('/admin/safety/summary', { signal }), []);
  const apps = useResource((signal) => api.get<Schemas['AdminApplicationSummary'][]>('/companions/admin/applications', { query: { status: 'submitted', limit: 100 }, signal }), []);
  const content = useResource((signal) => api.get<Schemas['AdminApplicationSummary'][]>('/companions/admin/applications', { query: { content_status: 'pending', limit: 100 }, signal }), []);
  const err = summary.error ?? safety.error ?? apps.error ?? content.error;
  if (!summary.data && !err) return <Loading rows={2} />;
  if (err) return <ErrorState error={err} onRetry={() => { summary.reload(); safety.reload(); apps.reload(); content.reload(); }} />;
  const cap = (n: number) => (n >= 100 ? '100+' : null);
  const tiles: { label: string; value: number; to?: string; note?: string | null }[] = [
    { label: t('admin.dash.apps'), value: apps.data?.length ?? 0, to: '/admin/applications?status=submitted', note: cap(apps.data?.length ?? 0) },
    { label: t('admin.dash.content'), value: content.data?.length ?? 0, to: '/admin/applications?content_status=pending', note: cap(content.data?.length ?? 0) },
    { label: t('admin.dash.reports'), value: safety.data?.open_reports ?? summary.data!.open_reports, to: '/admin/safety' },
    { label: t('admin.dash.sos'), value: safety.data?.unacknowledged_sos ?? 0, to: '/admin/safety?tab=sos' },
    { label: t('admin.nav.users'), value: summary.data!.users, to: '/admin/users' },
    { label: t('nav.bookings'), value: summary.data!.bookings, to: '/admin/bookings' },
    { label: t('admin.dash.payments'), value: summary.data!.payments },
  ];
  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="bento">
        {tiles.map((tile, i) => (
          <Item key={tile.label} index={i}>
            <div className="glass stat spot">
              <Counter value={tile.value} />
              <span>{tile.label}{tile.note ? t('admin.dash.listLimit') : ''}</span>
              {tile.to && <Link to={tile.to} style={{ fontWeight: 600 }}>{t('admin.dash.open')}</Link>}
            </div>
          </Item>
        ))}
      </div>
      <div className="banner">
        {t('admin.dash.banner')}
        {safety.data && !safety.data.emergency_dispatch_configured ? t('admin.dash.dispatchOff') : ''}.
      </div>
      <div className="glass pad stack">
        <h2>{t('admin.dash.unconnected')}</h2>
        <p className="muted">{t('admin.dash.unconnectedBody')}</p>
      </div>
    </div>
  );
}
