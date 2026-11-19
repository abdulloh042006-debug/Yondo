import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { t } from '../i18n';

/**
 * Compact App Bar (docs/design/redesign-2026-11.md §3.2): a 44 px back button, the page title as the page's one
 * <h1>, and up to two icon actions. Replaces the "← Orqaga" / "← Bronlar" pills and links. Back goes to the previous
 * in-app page when there is one, otherwise to `back`.
 */
export function AppBar({ title, back, actions }: { title?: ReactNode; back?: string; actions?: ReactNode }) {
  const navigate = useNavigate();
  const goBack = () => {
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (idx > 0) navigate(-1);
    else if (back) navigate(back);
  };
  return (
    <div className="appbar">
      {back && (
        <button type="button" className="icon-btn" aria-label={t('nav.back')} onClick={goBack}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
      )}
      {title ? <h1 className="appbar-title">{title}</h1> : <span className="appbar-title" />}
      {actions && <div className="appbar-actions">{actions}</div>}
    </div>
  );
}

/** Icon-only action for the App Bar (gear, pencil…): the visible icon, the name for screen readers. */
export const GEAR = 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z';
