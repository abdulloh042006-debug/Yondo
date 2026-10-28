import { useSyncExternalStore } from 'react';

/**
 * A skin = a look that bundles themes (day/night), an icon set, a logo lockup and a default app icon.
 * `classic` is today's default look (themes yondo / yondo-tun; the legacy Gul/Jurnal/Stone themes also render it).
 * `warm` ("Yondo · iliq") is the optional second skin (design-prototype/brand/skin-warm/SPEC.md).
 * The skin is derived from the active theme id, so there is exactly one source of truth: `data-theme` on <html>.
 */
export type SkinId = 'classic' | 'warm';
export type AppIconId = 'joriy' | 'kartochka' | 'siyoh' | 'karrot' | 'naqsh';

export const SKINS = {
  classic: { id: 'classic', themes: { day: 'yondo', night: 'yondo-tun' }, iconSet: 'classic', lockup: 'classic', appIconDefault: 'joriy' },
  warm: { id: 'warm', themes: { day: 'yondo-warm', night: 'yondo-warm-tun' }, iconSet: 'warm', lockup: 'warm', appIconDefault: 'kartochka' },
} as const satisfies Record<SkinId, { id: SkinId; themes: { day: string; night: string }; iconSet: SkinId; lockup: SkinId; appIconDefault: AppIconId }>;

export function skinOfTheme(themeId: string | undefined | null): SkinId {
  return themeId === SKINS.warm.themes.day || themeId === SKINS.warm.themes.night ? 'warm' : 'classic';
}

export const isNightTheme = (themeId: string | undefined | null) => !!themeId && themeId.endsWith('-tun');

export function currentSkin(): SkinId {
  return skinOfTheme(typeof document === 'undefined' ? undefined : document.documentElement.dataset.theme);
}

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  return () => observer.disconnect();
}

/** The active theme id (`data-theme` on <html>); re-renders on change. */
export function useThemeAttr(): string | undefined {
  return useSyncExternalStore(subscribe, () => document.documentElement.dataset.theme, () => undefined);
}

/** The skin of the active theme; re-renders when `data-theme` changes. */
export function useSkin(): SkinId {
  return useSyncExternalStore(subscribe, currentSkin, () => 'classic');
}

/** localStorage that never throws (private mode, blocked storage, previews). */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* ignore */
    }
  },
  remove(key: string) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};
