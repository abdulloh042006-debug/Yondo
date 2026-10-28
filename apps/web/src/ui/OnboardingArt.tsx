import { motion, useReducedMotion } from 'motion/react';
import { ease } from './motion';

export type ArtKind = 'discover' | 'book' | 'safe';

/**
 * The picture on an onboarding card. This file is the single replacement point: the Uzbek-ornament illustrations
 * drop in here (same props, same square-ish box), nothing else in the onboarding depends on how it is drawn.
 *
 * Plain line art, brand colours only: strokes are `currentColor` (ink on day themes, paper on night themes) and the
 * accent is the carrot (`--c-glow`, falling back to the logo's #E8501A). No people, no hearts, no shield or lock.
 */
export function OnboardingArt({ kind }: { kind: ArtKind }) {
  const reduce = useReducedMotion();
  // Each stroke draws itself in; reduced motion renders the finished picture at once.
  const draw = (delay: number) => ({
    initial: reduce ? false : ({ pathLength: 0, opacity: 0 } as const),
    animate: { pathLength: 1, opacity: 1 },
    transition: { duration: 0.6, delay, ease },
  });
  return (
    <svg className="guide-art" viewBox="0 0 160 116" fill="none" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <g stroke="currentColor">
        {kind === 'discover' && (
          <>
            <motion.circle cx="62" cy="50" r="28" {...draw(0)} />
            <motion.rect x="106" y="22" width="40" height="9" rx="4.5" {...draw(0.15)} />
            <motion.rect x="106" y="42" width="40" height="9" rx="4.5" {...draw(0.25)} />
            <motion.rect x="106" y="62" width="40" height="9" rx="4.5" {...draw(0.35)} />
          </>
        )}
        {kind === 'book' && (
          <>
            <motion.rect x="32" y="24" width="96" height="76" rx="12" {...draw(0)} />
            <motion.path d="M32 46h96M56 16v16M104 16v16" {...draw(0.15)} />
          </>
        )}
        {kind === 'safe' && (
          <>
            <motion.path d="M80 10c-14 0-24 10-24 23 0 17 24 37 24 37s24-20 24-37c0-13-10-23-24-23z" {...draw(0)} />
            <motion.ellipse cx="80" cy="90" rx="36" ry="8" {...draw(0.2)} />
            <motion.path d="M80 98v10M62 108h36" {...draw(0.3)} />
          </>
        )}
      </g>
      <g stroke="var(--c-glow, #e8501a)" strokeWidth="4.5">
        {kind === 'discover' && <motion.path d="M82 70l22 24" {...draw(0.1)} />}
        {kind === 'book' && <motion.path d="M58 72l14 14 30-32" {...draw(0.4)} />}
        {kind === 'safe' && <motion.circle cx="80" cy="33" r="8" {...draw(0.45)} />}
      </g>
    </svg>
  );
}
