import { useState } from 'react';
import { t } from '../i18n';

/**
 * `chrome` = the colour of the browser UI (address bar, status bar) for that theme: always the theme's `--c-bg`
 * (theme.test.tsx checks it against styles.css), so the page and the browser chrome never disagree.
 */
export const THEMES = [
  { id: 'yondo', get label() { return t('theme.yondo.label'); }, get hint() { return t('theme.yondo.hint'); }, swatch: 'linear-gradient(135deg, #f5f2ec 50%, #111111 50%)', chrome: '#f5f2ec' },
  { id: 'yondo-tun', get label() { return t('theme.yondo-tun.label'); }, get hint() { return t('theme.yondo-tun.hint'); }, swatch: 'linear-gradient(135deg, #111111 50%, #e8501a 50%)', chrome: '#111111' },
  { id: 'gul', label: 'Gul', get hint() { return t('theme.gul.hint'); }, swatch: '#8e3140', chrome: '#f3ebdf' },
  { id: 'rausch', label: 'Jurnal', get hint() { return t('theme.rausch.hint'); }, swatch: '#de1b5a', chrome: '#ffffff' },
  { id: 'stone', label: 'Stone', get hint() { return t('theme.stone.hint'); }, swatch: '#1a2b49', chrome: '#f3f5f8' },
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

/** Keep <meta name="theme-color"> in step with the theme (it is static in index.html, which only knows the default). */
function syncThemeColor(id: ThemeId) {
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'theme-color';
    document.head.appendChild(meta);
  }
  meta.content = THEMES.find((th) => th.id === id)!.chrome;
}

/**
 * Switch the look. The new theme's styles are computed once with transitions switched off
 * (`[data-theme-switching]` in styles.css), so no element animates from the previous theme's colours: otherwise
 * `.btn`, `.lang-opt` etc. spend 0.2 s showing e.g. a light foreground on the new dark ground.
 */
export function applyTheme(id: ThemeId) {
  const root = document.documentElement;
  root.dataset.themeSwitching = '';
  root.dataset.theme = id;
  void root.offsetWidth; // force the style recalculation while transitions are off
  delete root.dataset.themeSwitching;
  syncThemeColor(id);
}

/** Applied once at start-up (main.tsx), so the chosen look is active on every page, not only in Settings. */
export function applySavedTheme() {
  applyTheme(saved());
}

export function setTheme(id: ThemeId) {
  applyTheme(id);
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
