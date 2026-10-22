import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import type { PointerEvent } from 'react';

/** Decorative glass spheres that drift toward the pointer (parallax). Purely visual. */
export function useParallax() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 60, damping: 18 });
  const sy = useSpring(y, { stiffness: 60, damping: 18 });
  const onPointerMove = (e: PointerEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - r.left) / r.width - 0.5);
    y.set((e.clientY - r.top) / r.height - 0.5);
  };
  return { sx, sy, onPointerMove };
}

export function Orbs({ sx, sy }: { sx: ReturnType<typeof useMotionValue<number>>; sy: ReturnType<typeof useMotionValue<number>> }) {
  const a = { x: useTransform(sx, (v) => v * -46), y: useTransform(sy, (v) => v * -46) };
  const b = { x: useTransform(sx, (v) => v * 70), y: useTransform(sy, (v) => v * 70) };
  const c = { x: useTransform(sx, (v) => v * -24), y: useTransform(sy, (v) => v * 30) };
  return (
    <div className="orbs" aria-hidden="true">
      <motion.span className="orb-glass" style={{ ...a, width: 150, height: 150, right: '6%', top: '-34px' }} />
      <motion.span className="orb-glass" style={{ ...b, width: 84, height: 84, right: '26%', bottom: '14%', animationDelay: '-2s' }} />
      <motion.span className="orb-glass" style={{ ...c, width: 56, height: 56, right: '4%', bottom: '-10px', animationDelay: '-4s' }} />
    </div>
  );
}
