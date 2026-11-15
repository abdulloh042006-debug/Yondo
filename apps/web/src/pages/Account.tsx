import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth, type User } from '../auth/AuthContext';
import { t } from '../i18n';
import { prettyPhone } from '../lib/format';
import { roleLabel } from '../lib/labels';
import { useToast } from '../ui/feedback';
import { Field } from '../ui/form';
import { useResource } from '../lib/useResource';
import { Reveal } from '../ui/motion';

type CompanionProfile = Schemas['ProfileResponse'];

export function Account() {
  const { user } = useAuth();
  if (!user) return null;
  // Remount when the server-side profile changes so the form always starts from saved values.
  return <AccountView key={`${user.age}|${user.gender}|${user.city}`} user={user} />;
}

function MenuLink({ to, title, hint, badge }: { to: string; title: string; hint: string; badge?: string }) {
  return (
    <li>
      <Link to={to} className="menu-item">
        <span className="stack" style={{ gap: 2 }}>
          <b>{title} {badge && <span className="tag warn">{badge}</span>}</b>
          <span className="hint">{hint}</span>
        </span>
        <span aria-hidden="true" className="menu-chevron">›</span>
      </Link>
    </li>
  );
}

function AccountView({ user }: { user: User }) {
  const { reload } = useAuth();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [age, setAge] = useState(user.age?.toString() ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [city, setCity] = useState(user.city ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  // A companion's public profile gives the name, "about" text; a customer has none, so the phone number stands in.
  const companion = useResource(
    (signal) => (user.roles.includes('companion') ? api.get<CompanionProfile>('/companions/me/profile', { signal }) : Promise.resolve(null)),
    [user.id, user.roles.join(',')],
  );
  const pub = companion.data ?? null;

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

  /* Owner decision 2026-11-14: Profil holds only the person (photo, name, about, personal data + Tahrirlash);
     everything about the app and the account lives in Sozlamalar, which opens from here. */
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
              <h2 style={{ margin: 0 }}>{pub?.display_name || prettyPhone(user.phone_number)}</h2>
              <span className="muted">{user.roles.map(roleLabel).join(', ') || '—'}</span>
            </div>
          </div>
          {pub?.bio && (
            <div className="stack" style={{ gap: 4 }}>
              <h3 style={{ margin: 0 }}>{t('common.description')}</h3>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{pub.bio}</p>
            </div>
          )}
        </div>
      </Reveal>
      <Reveal delay={0.03}>
        {editing ? (
          <form className="glass pad stack" onSubmit={save} noValidate>
            <h2>{t('account.personal')}</h2>
            <div className="bento">
              <Field label={t('account.age')} inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} error={ageError} />
              <Field label={t('account.gender')} value={gender} maxLength={64} onChange={(e) => setGender(e.target.value)} error={err?.fields.gender} />
              <Field label={t('common.city')} value={city} maxLength={128} onChange={(e) => setCity(e.target.value)} error={err?.fields.city} />
            </div>
            {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
            <div className="row">
              <button className="btn" disabled={busy || !!ageError}>{busy && <span className="spinner" aria-hidden="true" />}{t('common.save')}</button>
              <button type="button" className="btn ghost" disabled={busy} onClick={() => setEditing(false)}>{t('common.cancel')}</button>
            </div>
          </form>
        ) : (
          <section className="glass pad stack" aria-labelledby="pers-h">
            <h2 id="pers-h">{t('account.personal')}</h2>
            <dl className="kv">
              {pub?.display_name && (<><dt>{t('account.phone')}</dt><dd>{prettyPhone(user.phone_number)}</dd></>)}
              <dt>{t('account.age')}</dt><dd>{user.age ?? '—'}</dd>
              <dt>{t('account.gender')}</dt><dd>{user.gender || '—'}</dd>
              <dt>{t('common.city')}</dt><dd>{user.city || '—'}</dd>
            </dl>
            <div><button className="btn" onClick={() => setEditing(true)}>{t('common.edit')}</button></div>
          </section>
        )}
      </Reveal>
      <Reveal delay={0.05}>
        <nav className="glass pad" aria-label={t('account.menu')}>
          <ul className="menu-list">
            <MenuLink to="/settings" title={t('settings.title')} hint={t('account.menu.settingsHint')} />
          </ul>
        </nav>
      </Reveal>
    </div>
  );
}
