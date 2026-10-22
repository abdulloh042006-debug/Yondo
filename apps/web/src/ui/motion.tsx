import { animate, motion, useInView, useMotionValue, useReducedMotion, useTransform } from 'motion/react';
import { useEffect, useRef, type ReactNode } from 'react';

const ease = [0.22, 1, 0.36, 1] as const;

/** Fade + rise when scrolled into view. Reduced-motion users get the final state immediately. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '0px 0px -8% 0px' }}
      transition={{ duration: 0.6, delay, ease }}
    >
      {children}
    </motion.div>
  );
}

/** Stagger children by index (use inside lists). */
export function Item({ children, index = 0, className }: { children: ReactNode; index?: number; className?: string }) {
  return (
    <Reveal delay={Math.min(index, 8) * 0.06} className={className}>
      {children}
    </Reveal>
  );
}

export function PageTransition({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14, filter: 'blur(6px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{ duration: 0.5, ease }}
    >
      {children}
    </motion.div>
  );
}

/** Counts up to a real, server-supplied number once visible. */
export function Counter({ value }: { value: number }) {
  const ref = useRef<HTMLElement>(null);
  const visible = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const mv = useMotionValue(reduce ? value : 0);
  const text = useTransform(mv, (n) => Math.round(n).toLocaleString('uz-UZ').replace(/,/g, ' '));
  useEffect(() => {
    if (!visible) return;
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration: 1.1, ease });
    return () => controls.stop();
  }, [visible, value, reduce, mv]);
  return <motion.b ref={ref}>{text}</motion.b>;
}

/** Floating orb used on empty/loading states. */
export function Orb() {
  return <div className="orb" aria-hidden="true" />;
}
