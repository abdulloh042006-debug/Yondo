import { useState } from 'react';
import { t } from '../i18n';

export const THEMES = [
  { id: 'yondo', get label() { return t('theme.yondo.label'); }, get hint() { return t('theme.yondo.hint'); }, swatch: 'linear-gradient(135deg, #f5f2ec 50%, #111111 50%)' },
  { id: 'yondo-tun', get label() { return t('theme.yondo-tun.label'); }, get hint() { return t('theme.yondo-tun.hint'); }, swatch: 'linear-gradient(135deg, #111111 50%, #e8501a 50%)' },
  { id: 'gul', label: 'Gul', get hint() { return t('theme.gul.hint'); }, swatch: '#8e3140' },
  { id: 'rausch', label: 'Jurnal', get hint() { return t('theme.rausch.hint'); }, swatch: '#de1b5a' },
  { id: 'stone', label: 'Stone', get hint() { return t('theme.stone.hint'); }, swatch: '#1a2b49' },
] as const;
export type ThemeId = (typeof THEMES)[number]['id'];
const KEY = 'yondo.theme';

function saved(): ThemeId {
  try {
    const value = localStorage.getItem(KEY);
    if (THEMES.some((t) => t.id === value)) return value as ThemeId;
  } catch {
    /* storage may be unavailable */
  }
  return 'gul';
}

/** Applied once at start-up (main.tsx), so the chosen look is active on every page, not only in Settings. */
export function applySavedTheme() {
  document.documentElement.dataset.theme = saved();
}

function setTheme(id: ThemeId) {
  document.documentElement.dataset.theme = id;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* ignore */
  }
}

/** Theme choice. Lives only on the Settings page. */
export function ThemePicker() {
  const [theme, set] = useState<ThemeId>(() => (document.documentElement.dataset.theme as ThemeId) || saved());
  return (
    <div role="group" aria-label={t('settings.themeGroup')} className="theme-picker">
      {THEMES.map((th) => (
        <button
          key={th.id}
          type="button"
          className="theme-opt"
          aria-label={t('settings.themeAria', { label: th.label })}
          aria-pressed={theme === th.id}
          onClick={() => {
            setTheme(th.id);
            set(th.id);
          }}
        >
          <span className="theme-dot" style={{ background: th.swatch }} aria-hidden="true" />
          <span className="stack" style={{ gap: 0, textAlign: 'left' }}>
            <b>{th.label}</b>
            <span className="hint">{th.hint}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
