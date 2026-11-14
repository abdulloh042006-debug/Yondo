import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth, type User } from '../auth/AuthContext';
import { t } from '../i18n';
import { AlphabetPicker, LanguagePicker } from '../i18n/LanguagePicker';
import { Reveal } from '../ui/motion';
import { roleLabel } from '../lib/labels';
import { useResource } from '../lib/useResource';
import { useToast } from '../ui/feedback';
import { ThemePicker } from '../ui/theme';
import { DeleteAccount } from './DeleteAccount';

type Role = Schemas['UserRoleType'];

/** "Men kimman" (roles), the companion studio and sign out: moved here from Profil (owner, 2026-11-14). */
function AccountGroup({ user }: { user: User }) {
  const { reload, logout } = useAuth();
  const toast = useToast();
  const [rolesBusy, setRolesBusy] = useState(false);
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
    <>
      <h3 style={{ margin: 0 }}>{t('account.whoAmI')}</h3>
      <p className="muted">{t('account.whoAmIHint')}</p>
      <div className="row">
        {(['customer', 'companion'] as const).map((r) => (
          <button key={r} className="chip" aria-pressed={user.roles.includes(r)} disabled={rolesBusy} onClick={() => void toggleRole(r)}>
            {roleLabel(r)}
          </button>
        ))}
      </div>
      <div className="row">
        {user.roles.includes('companion') && <Link className="btn" to="/studio">{t('account.studio')}</Link>}
        <button className="btn ghost" onClick={() => void logout()}>{t('account.logout')}</button>
      </div>
    </>
  );
}

/**
 * Grouped like most consumer apps: language first (most needed, and how you recover from a wrong choice),
 * then appearance, notifications, account (roles, companion studio, sign out, deletion), privacy & safety, about.
 * Owner decision 2026-11-14: everything about the app and the account lives here; Profil holds only the person.
 * Language, appearance, safety and about also work signed out.
 */
export function Settings() {
  const { user } = useAuth();
  const unread = useResource((signal) => (user ? api.get<{ unread_count: number }>('/notifications/unread-count', { signal }) : Promise.resolve(null)), [user?.id]);
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h1>{t('settings.title')}</h1>
      <Reveal>
        <section className="glass pad stack" aria-labelledby="lang-h">
          <h2 id="lang-h">{t('settings.language')}</h2>
          <p className="muted">{t('settings.languageHint')}</p>
          <LanguagePicker />
          <p className="hint">{t('settings.languageNote')}</p>
          <h3 id="alpha-h" style={{ marginTop: 8 }}>{t('settings.alphabet')}</h3>
          <p className="muted">{t('settings.alphabetHint')}</p>
          <AlphabetPicker />
        </section>
      </Reveal>
      <Reveal delay={0.03}>
        <section className="glass pad stack" aria-labelledby="look-h">
          <h2 id="look-h">{t('settings.look')}</h2>
          <p className="muted">{t('settings.lookHint')}</p>
          <ThemePicker />
        </section>
      </Reveal>
      {user && (
        <Reveal delay={0.04}>
          <nav className="glass pad" aria-label={t('nav.notifications')}>
            <ul className="menu-list">
              <li>
                <Link to="/notifications" className="menu-item">
                  <span className="stack" style={{ gap: 2 }}>
                    <b>{t('nav.notifications')} {unread.data?.unread_count ? <span className="tag warn">{t('notif.unread', { n: unread.data.unread_count })}</span> : null}</b>
                    <span className="hint">{t('account.menu.notificationsHint')}</span>
                  </span>
                  <span aria-hidden="true" className="menu-chevron">›</span>
                </Link>
              </li>
            </ul>
          </nav>
        </Reveal>
      )}
      <Reveal delay={0.05}>
        <section className="glass pad stack" aria-labelledby="acc-h">
          <h2 id="acc-h">{t('settings.account')}</h2>
          {user ? <AccountGroup user={user} /> : <Link className="btn" to="/login" style={{ width: 'fit-content' }}>{t('nav.login')}</Link>}
        </section>
      </Reveal>
      {user && (
        <Reveal delay={0.06}>
          <DeleteAccount />
        </Reveal>
      )}
      <Reveal delay={0.07}>
        <section className="glass pad stack" aria-labelledby="safe-h">
          <h2 id="safe-h">{t('settings.safety')}</h2>
          <p className="muted">{t('settings.safetyHint')}</p>
          <Link className="btn ghost" to="/help" style={{ width: 'fit-content' }}>{t('help.title')}</Link>
        </section>
      </Reveal>
      <Reveal delay={0.09}>
        <section className="glass pad stack" aria-labelledby="about-h">
          <h2 id="about-h">{t('settings.about')}</h2>
          <p><b>{t('app.title')}</b></p>
          <dl className="kv">
            <dt>{t('settings.version')}</dt><dd>{__APP_VERSION__}</dd>
          </dl>
          <div className="row">
            <Link className="btn ghost sm" to="/terms">{t('legal.terms')}</Link>
            <Link className="btn ghost sm" to="/privacy">{t('legal.privacy')}</Link>
          </div>
          <p className="hint">{t('legal.draftBanner')}</p>
        </section>
      </Reveal>
    </div>
  );
}
