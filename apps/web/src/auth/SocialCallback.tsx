import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { t } from '../i18n';
import { introReady } from '../ui/Intro';
import { useAuth } from './AuthContext';
import { applyResult, takeTelegramFlow, type SocialResult } from './social';

/** /auth/callback/telegram: oauth.telegram.org sends the user back here with ?code&state. */
export function SocialCallback() {
  const { reload } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<ApiError>();
  const once = useRef(false);

  useEffect(() => {
    introReady();
    if (once.current) return; // StrictMode runs effects twice; the state is single-use
    once.current = true;
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const flow = takeTelegramFlow();
    const exchange =
      !code || !state || !flow
        ? Promise.reject(new ApiError(400, params.get('error') ? 'social_cancelled' : 'social_state_invalid'))
        : api.post<SocialResult>('/auth/social/telegram/exchange', { code, state, flow_token: flow.flow }, { anonymous: true });
    exchange
      .then(async (result) => {
        const next = applyResult(result);
        if (next === 'phone_required') {
          navigate('/login', { replace: true, state: { mode: 'code', notice: t('social.phoneRequired') } });
          return;
        }
        if (next === 'linked') {
          navigate('/settings', { replace: true, state: { notice: t('social.settings.done') } });
          return;
        }
        await reload();
        navigate('/', { replace: true });
      })
      .catch((err) => setError(err instanceof ApiError ? err : new ApiError(0, 'network_error')));
  }, [navigate, reload]);

  return (
    <div className="stack" style={{ maxWidth: 480, margin: '0 auto' }}>
      <h1>{t('social.callback.title')}</h1>
      {error ? (
        <>
          <p className="banner bad" role="alert">{error.message}</p>
          <Link className="btn" to="/login" style={{ width: 'fit-content' }}>{t('social.callback.back')}</Link>
        </>
      ) : (
        <p className="muted" role="status"><span className="spinner" aria-hidden="true" /> {t('common.loading')}</p>
      )}
    </div>
  );
}
