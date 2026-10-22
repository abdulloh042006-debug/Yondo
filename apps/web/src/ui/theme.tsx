import { useState } from 'react';

export const THEMES = [
  { id: 'yondo', label: 'Yondo kunduzgi', hint: 'Oq fon · qora · sabzi rang', swatch: 'linear-gradient(135deg, #f5f2ec 50%, #111111 50%)' },
  { id: 'yondo-tun', label: 'Yondo tungi', hint: 'Qora fon · oq · sabzi rang', swatch: 'linear-gradient(135deg, #111111 50%, #e8501a 50%)' },
  { id: 'gul', label: 'Gul', hint: 'Iliq atirgul-bordo', swatch: '#8e3140' },
  { id: 'rausch', label: 'Jurnal', hint: 'Yorqin atirgul-qizil', swatch: '#de1b5a' },
  { id: 'stone', label: 'Stone', hint: 'Sokin tungi ko‘k', swatch: '#1a2b49' },
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
    <div role="group" aria-label="Mavzu" className="theme-picker">
      {THEMES.map((t) => (
        <button
          key={t.id}
          type="button"
          className="theme-opt"
          aria-label={`${t.label} mavzusi`}
          aria-pressed={theme === t.id}
          onClick={() => {
            setTheme(t.id);
            set(t.id);
          }}
        >
          <span className="theme-dot" style={{ background: t.swatch }} aria-hidden="true" />
          <span className="stack" style={{ gap: 0, textAlign: 'left' }}>
            <b>{t.label}</b>
            <span className="hint">{t.hint}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
