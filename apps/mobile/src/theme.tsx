import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import { getItem, setItem } from './storage';

/**
 * Owner rule (2026-10-22): the Yondo themes use only paper #F5F2EC, ink #111111 and carrot #E8501A; greys are
 * ink/paper mixes. Carrot never carries small text (3.36:1 on paper): it is used for borders, dots and fills
 * with ink text. Status meaning is carried by words, not hue.
 */
export const INK = '#111111';
export const PAPER = '#F5F2EC';
export const CARROT = '#E8501A';

function mix(a: string, b: string, share: number): string {
  const ch = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
  const out = [0, 1, 2].map((i) => Math.round(ch(a, i) * share + ch(b, i) * (1 - share)));
  return `#${out.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
}

export type ThemeId = 'yondo' | 'yondo-tun';
export interface Palette {
  id: ThemeId;
  dark: boolean;
  bg: string;
  fg: string;
  muted: string;
  surface: string;
  primary: string;
  onPrimary: string;
  line: string;
  chip: string;
  accent: string;
  /** Glass surfaces (apps/web .glass / .glass-bar in the Yondo themes): translucent fill + hairline border. */
  glass: string;
  glassLine: string;
  bar: string;
  /** Active tab / chip pill: carrot at low opacity (glow, never text). */
  pill: string;
  glowOpacity: number;
}

/** Fonts of the web's Yondo themes (styles.css): Space Grotesk for headings, Manrope for text (both SIL OFL). */
export const FONT = {
  display: 'SpaceGrotesk_600SemiBold',
  body: 'Manrope_400Regular',
  medium: 'Manrope_600SemiBold',
  bold: 'Manrope_700Bold',
} as const;

export const PALETTES: Record<ThemeId, Palette> = {
  yondo: {
    id: 'yondo',
    dark: false,
    bg: PAPER,
    fg: INK,
    muted: mix(INK, PAPER, 0.72),
    surface: '#FFFFFF',
    primary: INK,
    onPrimary: PAPER,
    line: mix(INK, PAPER, 0.14),
    chip: mix(INK, PAPER, 0.06),
    accent: CARROT,
    glass: 'rgba(255,255,255,0.72)',
    glassLine: 'rgba(17,17,17,0.09)',
    bar: 'rgba(245,242,236,0.9)',
    pill: 'rgba(232,80,26,0.16)',
    glowOpacity: 0.2,
  },
  'yondo-tun': {
    id: 'yondo-tun',
    dark: true,
    bg: INK,
    fg: PAPER,
    muted: mix(PAPER, INK, 0.72),
    surface: mix(PAPER, INK, 0.07),
    primary: PAPER,
    onPrimary: INK,
    line: mix(PAPER, INK, 0.16),
    chip: mix(PAPER, INK, 0.1),
    accent: CARROT,
    glass: 'rgba(245,242,236,0.07)',
    glassLine: 'rgba(245,242,236,0.14)',
    bar: 'rgba(17,17,17,0.88)',
    pill: 'rgba(232,80,26,0.22)',
    glowOpacity: 0.22,
  },
};

/** 'system' follows the phone's light/dark setting. */
export type ThemeChoice = ThemeId | 'system';
const KEY = 'yondo.theme';

interface ThemeApi {
  palette: Palette;
  choice: ThemeChoice;
  setChoice: (next: ThemeChoice) => void;
}
const Ctx = createContext<ThemeApi | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const [choice, setChoiceState] = useState<ThemeChoice>('system');
  useEffect(() => {
    void getItem(KEY, 'pref').then((saved) => {
      if (saved === 'yondo' || saved === 'yondo-tun' || saved === 'system') setChoiceState(saved);
    });
  }, []);
  const value = useMemo<ThemeApi>(() => {
    const id: ThemeId = choice === 'system' ? (scheme === 'dark' ? 'yondo-tun' : 'yondo') : choice;
    return {
      palette: PALETTES[id],
      choice,
      setChoice: (next) => {
        setChoiceState(next);
        void setItem(KEY, next, 'pref');
      },
    };
  }, [choice, scheme]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
