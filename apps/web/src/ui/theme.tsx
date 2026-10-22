import { useEffect, useState } from 'react';

export const THEMES = [
  { id: 'gul', label: 'Gul', swatch: '#8e3140' },
  { id: 'rausch', label: 'Jurnal', swatch: '#de1b5a' },
  { id: 'stone', label: 'Stone', swatch: '#1a2b49' },
] as const;
type ThemeId = (typeof THEMES)[number]['id'];
const KEY = 'yondo.theme';

function initial(): ThemeId {
  try {
    const saved = localStorage.getItem(KEY);
    if (THEMES.some((t) => t.id === saved)) return saved as ThemeId;
  } catch {
    /* storage may be unavailable */
  }
  return 'gul';
}

export function ThemeSwitch() {
  const [theme, setTheme] = useState<ThemeId>(initial);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);
  return (
    <div role="group" aria-label="Mavzu" className="row" style={{ gap: 2, flexWrap: 'nowrap' }}>
      {THEMES.map((t) => (
        <button
          key={t.id}
          aria-label={`${t.label} mavzusi`}
          aria-pressed={theme === t.id}
          onClick={() => setTheme(t.id)}
          style={{
            width: 44,
            height: 44,
            border: 0,
            background: 'transparent',
            cursor: 'pointer',
            display: 'grid',
            placeItems: 'center',
          }}
        >
          <span
            style={{
              width: 22,
              height: 22,
              borderRadius: '50%',
              background: t.swatch,
              outline: theme === t.id ? '2px solid var(--c-fg)' : '2px solid transparent',
              outlineOffset: 3,
              transition: 'outline-color .2s',
            }}
          />
        </button>
      ))}
    </div>
  );
}
