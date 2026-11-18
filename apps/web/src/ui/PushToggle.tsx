import { useEffect, useId, useState } from 'react';
import { ApiError } from '../api/client';
import { t } from '../i18n';
import { disablePush, enablePush, pushState, type PushState } from '../lib/push';

const HINT: Record<PushState, Parameters<typeof t>[0]> = {
  on: 'push.state.on',
  off: 'push.state.off',
  denied: 'push.state.denied',
  unsupported: 'push.state.unsupported',
  'ios-install': 'push.state.iosInstall',
  unavailable: 'push.state.unavailable',
};

/** Settings → Bildirishnomalar: the "Push bildirishnomalar" switch. Permission is requested only on a tap. */
export function PushToggle() {
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hintId = useId();

  useEffect(() => {
    let live = true;
    pushState().then((s) => live && setState(s), () => live && setState('off'));
    return () => {
      live = false;
    };
  }, []);

  const on = state === 'on';
  const disabled = busy || state === null || state === 'unsupported' || state === 'ios-install' || state === 'denied';

  const toggle = async () => {
    setBusy(true);
    setError(null);
    try {
      setState(on ? await disablePush() : await enablePush());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('push.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack push-toggle" style={{ gap: 6 }}>
      <label className="row" style={{ justifyContent: 'space-between', gap: 12, cursor: disabled ? 'default' : 'pointer' }}>
        <span className="stack" style={{ gap: 2 }}>
          <b>{t('push.title')}</b>
          <span className="hint" id={hintId} aria-live="polite">
            {state ? t(HINT[state]) : t('common.loading')}
          </span>
        </span>
        <input
          type="checkbox"
          role="switch"
          className="switch"
          checked={on}
          aria-checked={on}
          aria-describedby={hintId}
          disabled={disabled}
          onChange={() => void toggle()}
        />
      </label>
      {error && (
        <p className="hint" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
