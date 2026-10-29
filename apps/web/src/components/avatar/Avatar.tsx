import { useLayoutEffect } from 'react';
import { t, type Key } from '../../i18n';
import { look, spriteMarkup } from './avatarArt';

const SPRITE_ID = 'yondo-avatar-sprite';

/** The 12 symbols are injected into the document once; every avatar is a tiny <svg><use/></svg>. */
function ensureSprite() {
  if (typeof document === 'undefined' || document.getElementById(SPRITE_ID)) return;
  const holder = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  holder.setAttribute('id', SPRITE_ID);
  holder.setAttribute('width', '0');
  holder.setAttribute('height', '0');
  holder.setAttribute('aria-hidden', 'true');
  holder.setAttribute('focusable', 'false');
  holder.style.position = 'absolute';
  holder.innerHTML = spriteMarkup();
  document.body.appendChild(holder);
}

interface AvatarProps {
  /** Account id (customer) or profile id (companion without a photo). The same seed always draws the same art. */
  seed: string;
  /** 32 (rows, top bar), 44 (cards), 64 (profile header, story ring), 96 (picker). */
  size?: 32 | 44 | 64 | 96;
  /** Standalone use: exposes the art as an image with this accessible name. Omit next to a name (decorative). */
  standalone?: boolean;
  className?: string;
}

export function Avatar({ seed, size = 44, standalone, className }: AvatarProps) {
  useLayoutEffect(ensureSprite, []);
  const a = look(seed);
  const cls = `av av-way-${a.ground}${size < 44 ? ' av-s32' : ''}${className ? ` ${className}` : ''}`;
  const a11y = standalone
    ? { role: 'img' as const, 'aria-label': t('avatar.label', { pattern: t(`avatar.name.${a.id}` as Key) }) }
    : { 'aria-hidden': true as const };
  return (
    <svg className={cls} width={size} height={size} viewBox="0 0 48 48" focusable="false" {...a11y}>
      <use href={`#av-${a.id}`} transform={a.transform || undefined} />
    </svg>
  );
}
