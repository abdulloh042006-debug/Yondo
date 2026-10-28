import warmDark from '../assets/skin/warm-mark-dark.svg';
import warmLight from '../assets/skin/warm-mark-light.svg';
import { type SkinId, useSkin } from './skin';

/**
 * Logo symbol keyed by skin. Classic = the official Yondo symbol (design-prototype/brand/logo), untouched:
 * two converging lines, ink + the single accent node. Warm = girih "Y" on a soft tile (light tile by day, dark by night).
 */
export function BrandMark({ skin }: { skin?: SkinId }) {
  const active = useSkin();
  const which = skin ?? active;
  if (which === 'warm') {
    return (
      <span className="brand-mark brand-tile" data-lockup="warm" aria-hidden="true">
        <img className="tile-light" src={warmLight} alt="" width="32" height="32" />
        <img className="tile-dark" src={warmDark} alt="" width="32" height="32" />
      </span>
    );
  }
  return (
    <svg className="brand-mark" data-lockup="classic" width="30" height="30" viewBox="0 0 64 64" aria-hidden="true">
      <g stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="9">
        <path d="M16 15 28 34Q31 38 32 40M48 15 36 34Q33 38 32 40M32 40v17" />
      </g>
      <circle cx="16" cy="15" r="9" fill="currentColor" />
      <circle cx="48" cy="15" r="9" fill="#E8501A" />
    </svg>
  );
}
