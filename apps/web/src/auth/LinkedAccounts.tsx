import { useEffect, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { useAuth } from './AuthContext';
import { startTelegram, type SocialProvider, type SocialResult } from './social';
import { GoogleButton, TelegramMark, useSocialConfig } from './SocialSignIn';

type Identity = Schemas['LinkedIdentity'];

/** Settings → account: link / unlink Telegram and Google. Unlinking needs a password (server rule). */
export function LinkedAccounts() {
  const { user } = useAuth();
  const config = useSocialConfig();
  const location = useLocation();
  const [linked, setLinked] = useState<Identity[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [notice, setNotice] = useState<string | undefined>((location.state as { notice?: string } | null)?.notice);

  const load = () =>
    api
      .get<Identity[]>('/auth/social/identities')
      .then(setLinked)
      .catch(() => setLinked([]));
  useEffect(() => {
    void load();
  }, []);

  if (!user || !config || (!config.telegram && !config.google_client_id)) return null;
  const has = (p: SocialProvider) => !!linked?.some((i) => i.provider === p);

  const act = async (task: () => Promise<unknown>, done?: string) => {
    setBusy(true);
    setError(undefined);
    setNotice(undefined);
    try {
      await task();
      if (done) setNotice(done);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };
  const unlink = (p: SocialProvider) => act(() => api.del(`/auth/social/identities/${p}`), t('social.settings.removed'));

  const row = (p: SocialProvider, label: string, linkControl: ReactNode) => (
    <li className="row social-row" key={p}>
      {p === 'telegram' && <TelegramMark />}
      <strong>{label}</strong>
      <span className="muted">{has(p) ? t('social.settings.linked') : t('social.settings.notLinked')}</span>
      {has(p) ? (
        <button type="button" className="chip" disabled={busy || !user.has_password} onClick={() => void unlink(p)}>
          {t('social.settings.unlink')}
        </button>
      ) : (
        linkControl
      )}
    </li>
  );

  return (
    <div className="stack" aria-labelledby="social-h">
      <h3 id="social-h" style={{ margin: 0 }}>{t('social.settings.title')}</h3>
      <p className="muted">{t('social.settings.hint')}</p>
      {notice && <p className="banner" role="status">{notice}</p>}
      {error && <p className="banner bad" role="alert">{error.message}</p>}
      <ul className="stack social-list">
        {config.telegram &&
          row(
            'telegram',
            t('social.provider.telegram'),
            <button type="button" className="chip" disabled={busy} onClick={() => void act(() => startTelegram('link'))}>
              {t('social.settings.link')}
            </button>,
          )}
        {config.google_client_id &&
          row(
            'google',
            t('social.provider.google'),
            <GoogleButton
              clientId={config.google_client_id}
              onCredential={(credential) =>
                void act(() => api.post<SocialResult>('/auth/social/google/link', { credential }), t('social.settings.done'))
              }
            />,
          )}
      </ul>
    </div>
  );
}
