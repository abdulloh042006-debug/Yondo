import type { CSSProperties } from 'react';
import { WARM_ICONS } from './warmIcons';
import { type SkinId, useSkin } from './skin';

export type IconName = 'home' | 'heart' | 'cal' | 'user' | 'shield' | 'check';

/** Classic icon set: exactly the paths the app used before skins existed. */
const CLASSIC: Record<IconName, { d: string; strokeWidth: number }> = {
  home: { d: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z', strokeWidth: 1.8 },
  heart: { d: 'M12 21s-7-4.4-9.3-9A5.4 5.4 0 0 1 12 6a5.4 5.4 0 0 1 9.3 6C19 16.6 12 21 12 21z', strokeWidth: 1.8 },
  cal: { d: 'M7 3v3m10-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', strokeWidth: 1.8 },
  user: { d: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0', strokeWidth: 1.8 },
  shield: { d: 'M12 3l8 3v6c0 4.5-3.2 8.2-8 9-4.8-.8-8-4.5-8-9V6z', strokeWidth: 1.8 },
  check: { d: 'M5 12.5l4.5 4.5L19 7.5', strokeWidth: 2.6 },
};

interface IconProps {
  name: IconName;
  size?: number;
  /** Stroke colour (default currentColor). */
  color?: string;
  /** Filled shape (the "on" state of the favourites heart). */
  filled?: boolean;
  className?: string;
  style?: CSSProperties;
  /** Force a set (used by the skin preview tiles); default = the active skin's set. */
  set?: SkinId;
}

/** THE icon component: the active skin picks the set. Icons are decorative; the label or aria-label lives on the parent. */
export function Icon({ name, size = 22, color = 'currentColor', filled, className, style, set }: IconProps) {
  const active = useSkin();
  const skin = set ?? active;
  const common = { width: size, height: size, viewBox: '0 0 24 24', 'aria-hidden': true as const, className, style, 'data-icon': name, 'data-icon-set': skin };
  const fill = filled ? 'var(--c-primary)' : 'none';
  const stroke = filled ? 'var(--c-primary)' : color;
  if (skin === 'warm') {
    const w = WARM_ICONS[name];
    return (
      <svg {...common} fill="none" stroke={stroke} strokeWidth={w.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
        <path d={w.stroke} fill={fill} />
        {w.accent && <path d={w.accent} fill="currentColor" stroke="none" />}
      </svg>
    );
  }
  const c = CLASSIC[name];
  return (
    <svg {...common} fill={fill} stroke={stroke} strokeWidth={c.strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d={c.d} />
    </svg>
  );
}
