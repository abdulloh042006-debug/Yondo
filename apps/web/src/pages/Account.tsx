import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth, type User } from '../auth/AuthContext';
import { t } from '../i18n';
import { formatInstant, prettyPhone } from '../lib/format';
import { roleLabel } from '../lib/labels';
import { useToast } from '../ui/feedback';
import { Field } from '../ui/form';
import { Reveal } from '../ui/motion';
import { DeleteAccount } from './DeleteAccount';

type Role = Schemas['UserRoleType'];

export function Account() {
  const { user } = useAuth();
  if (!user) return null;
  // Remount when the server-side profile changes so the form always starts from saved values.
  return <AccountView key={`${user.age}|${user.gender}|${user.city}`} user={user} />;
}

function MenuLink({ to, title, hint }: { to: string; title: string; hint: string }) {
  return (
    <li>
      <Link to={to} className="menu-item">
        <span className="stack" style={{ gap: 2 }}>
          <b>{title}</b>
          <span className="hint">{hint}</span>
        </span>
        <span aria-hidden="true" className="menu-chevron">›</span>
      </Link>
    </li>
  );
}

function AccountView({ user }: { user: User }) {
  const { reload, logout } = useAuth();
  const toast = useToast();
  const [age, setAge] = useState(user.age?.toString() ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [city, setCity] = useState(user.city ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const [rolesBusy, setRolesBusy] = useState(false);

  const ageNum = age.trim() === '' ? null : Number(age);
  const ageError = ageNum !== null && (!Number.isInteger(ageNum) || ageNum < 18 || ageNum > 120) ? t('account.ageRange') : err?.fields.age;

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (ageError) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.put('/auth/profile', { age: ageNum, gender: gender.trim() || null, city: city.trim() || null });
      await reload();
      toast.push('ok', t('account.saved'));
    } catch (error) {
      setErr(error instanceof ApiError ? error : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  const toggleRole = async (role: 'customer' | 'companion') => {
    // The server replaces the whole non-admin role set, so we resend every other role we know of.
    const current = user.roles.filter((r) => r !== 'admin');
    const next: Role[] = current.includes(role) ? current.filter((r) => r !== role) : [...current, role];
    if (next.length === 0) {
      toast.push('bad', t('account.minRole'));
      return;
    }
    setRolesBusy(true);
    try {
      await api.put('/auth/roles', { roles: next });
      await reload();
      toast.push('ok', t('account.rolesUpdated'));
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : t('common.actionFailed'));
    } finally {
      setRolesBusy(false);
    }
  };

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h1>{t('account.title')}</h1>
      <Reveal>
        <div className="glass pad stack">
          <div className="profile-head">
            <span className="avatar" aria-hidden="true">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0" />
              </svg>
            </span>
            <div className="stack" style={{ gap: 2 }}>
              <h2 style={{ margin: 0 }}>{prettyPhone(user.phone_number)}</h2>
              <span className="muted">{user.roles.map(roleLabel).join(', ') || '—'}</span>
            </div>
          </div>
          <dl className="kv">
            <dt>{t('account.memberSince')}</dt><dd>{formatInstant(user.created_at)}</dd>
          </dl>
          {!user.roles.includes('admin') && (
            <p className="hint">{t('account.statusNote')}</p>
          )}
        </div>
      </Reveal>
      <Reveal delay={0.03}>
        <nav className="glass pad" aria-label={t('account.menu')}>
          <ul className="menu-list">
            <MenuLink to="/bookings" title={t('nav.bookings')} hint={t('account.menu.bookingsHint')} />
            <MenuLink to="/favorites" title={t('nav.favorites')} hint={t('account.menu.favoritesHint')} />
            {user.roles.includes('companion') && <MenuLink to="/studio" title={t('account.studio')} hint={t('account.menu.studioHint')} />}
            <MenuLink to="/help" title={t('help.title')} hint={t('account.menu.helpHint')} />
            <MenuLink to="/settings" title={t('settings.title')} hint={t('account.menu.settingsHint')} />
          </ul>
        </nav>
      </Reveal>
      <Reveal delay={0.05}>
        <form className="glass pad stack" onSubmit={save} noValidate>
          <h2>{t('account.personal')}</h2>
          <div className="bento">
            <Field label={t('account.age')} inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} error={ageError} />
            <Field label={t('account.gender')} value={gender} maxLength={64} onChange={(e) => setGender(e.target.value)} error={err?.fields.gender} />
            <Field label={t('common.city')} value={city} maxLength={128} onChange={(e) => setCity(e.target.value)} error={err?.fields.city} />
          </div>
          {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
          <div><button className="btn" disabled={busy || !!ageError}>{busy && <span className="spinner" aria-hidden="true" />}{t('common.save')}</button></div>
        </form>
      </Reveal>
      <Reveal delay={0.1}>
        <div className="glass pad stack">
          <h2>{t('account.whoAmI')}</h2>
          <p className="muted">{t('account.whoAmIHint')}</p>
          <div className="row">
            {(['customer', 'companion'] as const).map((r) => (
              <button key={r} className="chip" aria-pressed={user.roles.includes(r)} disabled={rolesBusy} onClick={() => void toggleRole(r)}>
                {roleLabel(r)}
              </button>
            ))}
          </div>
          {user.roles.includes('companion') && <Link className="btn" to="/studio" style={{ width: 'fit-content' }}>{t('account.studio')}</Link>}
        </div>
      </Reveal>
      <div><button className="btn ghost" onClick={() => void logout()}>{t('account.logout')}</button></div>
      <Reveal delay={0.12}>
        <DeleteAccount />
      </Reveal>
    </div>
  );
}
