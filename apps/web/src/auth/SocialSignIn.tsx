import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import { getLocaleTag, t } from '../i18n';
import { applyResult, loadGoogle, socialConfig, startTelegram, type FlowIntent, type SocialConfig, type SocialResult } from './social';

/** The official Telegram mark (simple-icons, CC0), kept in Telegram's own colour as its brand rules ask. */
export function TelegramMark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="#26A5E4"
        d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
      />
    </svg>
  );
}

/** Google's own rendered button (its brand rules); it only appears when a client ID is configured. */
export function GoogleButton({ clientId, onCredential }: { clientId: string; onCredential: (credential: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const cb = useRef(onCredential);
  useEffect(() => {
    cb.current = onCredential;
  }, [onCredential]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadGoogle()
      .then((gis) => {
        if (!live || !ref.current) return;
        gis.initialize({ client_id: clientId, callback: (r) => cb.current(r.credential), ux_mode: 'popup' });
        gis.renderButton(ref.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          logo_alignment: 'left',
          locale: getLocaleTag().slice(0, 2),
          width: 300,
        });
      })
      .catch(() => live && setFailed(true)); // blocked script: no button rather than a broken one
    return () => {
      live = false;
    };
  }, [clientId]);
  if (failed) return null;
  return <div ref={ref} className="social-google" aria-label={t('social.google')} />;
}

/** Hook: the provider config (null while loading or unknown). */
export function useSocialConfig(): SocialConfig | null {
  const [config, setConfig] = useState<SocialConfig | null>(null);
  useEffect(() => {
    let live = true;
    void socialConfig().then((c) => live && setConfig(c));
    return () => {
      live = false;
    };
  }, []);
  return config;
}

/**
 * "Telegram orqali kiriş" + "Google orqali kiriş" on the sign-in / registration page. Hidden entirely
 * when neither provider is configured.
 */
export function SocialSignIn({
  onSignedIn,
  onPhoneRequired,
}: {
  onSignedIn: () => void | Promise<void>;
  onPhoneRequired: () => void;
}) {
  const config = useSocialConfig();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();
  if (!config || (!config.telegram && !config.google_client_id)) return null;

  const run = async (task: () => Promise<SocialResult | void>) => {
    setBusy(true);
    setError(undefined);
    try {
      const result = await task();
      if (!result) return; // redirected to Telegram
      const next = applyResult(result);
      if (next === 'phone_required') onPhoneRequired();
      else await onSignedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack social-signin" aria-label={t('social.title')} role="group">
      <p className="social-or muted"><span>{t('social.or')}</span></p>
      {config.telegram && (
        <button type="button" className="btn ghost social-btn" disabled={busy} onClick={() => void run(() => startTelegram('login' satisfies FlowIntent))}>
          <TelegramMark />
          {t('social.telegram')}
        </button>
      )}
      {config.google_client_id && (
        <GoogleButton
          clientId={config.google_client_id}
          onCredential={(credential) =>
            void run(() => api.post<SocialResult>('/auth/social/google', { credential }, { anonymous: true }))
          }
        />
      )}
      {error && <p className="banner bad" role="alert">{error.message}</p>}
    </div>
  );
}
