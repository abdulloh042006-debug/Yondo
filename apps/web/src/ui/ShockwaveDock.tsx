import { useReducedMotion } from 'motion/react';
import { useLayoutEffect, useRef, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

export interface DockItem {
  to: string;
  label: string;
  icon: ReactNode;
  end: boolean;
  extra?: ReactNode;
}

const isActive = (item: DockItem, path: string) =>
  item.end ? path === item.to : path === item.to || path.startsWith(item.to.endsWith('/') ? item.to : `${item.to}/`);

/** Total flight (spec §4.1): shrink 0–23 %, travel 23–62 %, expand 62–100 %; arrival effects start at 62 %. */
const T = 520;
const ARRIVE = T * 0.62;
const PARTICLES = 8;

/**
 * "Quantum Shockwave" bottom navigation (docs/design/redesign-2026-11.md §4.1), in the brand palette:
 * ink pill by day / paper pill at night (--c-primary), carrot orb, ripple and particles (graphic only).
 * The route changes on tap; the animation runs on top. Only transform/opacity are animated, on elements that exist
 * once. Reduced motion: the pill is placed on the target and fades in; nothing travels.
 */
export function ShockwaveDock({ items, label }: { items: DockItem[]; label: string }) {
  const { pathname } = useLocation();
  const reduce = useReducedMotion();
  const nav = useRef<HTMLElement>(null);
  const pill = useRef<HTMLSpanElement>(null);
  const orb = useRef<HTMLSpanElement>(null);
  const ripple = useRef<HTMLSpanElement>(null);
  const parts = useRef<(HTMLSpanElement | null)[]>([]);
  const links = useRef<(HTMLAnchorElement | null)[]>([]);
  const prev = useRef(-1);
  const running = useRef<Animation[]>([]);

  const activeIndex = items.findIndex((i) => isActive(i, pathname));

  useLayoutEffect(() => {
    const n = nav.current;
    const p = pill.current;
    if (!n || !p) return;
    const geo = (i: number) => {
      const a = links.current[i];
      return a ? { x: a.offsetLeft, w: a.offsetWidth, cx: a.offsetLeft + a.offsetWidth / 2 } : null;
    };
    const to = activeIndex >= 0 ? geo(activeIndex) : null;
    const fromIndex = prev.current;
    prev.current = activeIndex;
    running.current.forEach((a) => a.cancel());
    running.current = [];
    if (!to) {
      p.style.opacity = '0';
      return;
    }
    const place = () => {
      p.style.width = `${to.w}px`;
      p.style.transform = `translateX(${to.x}px)`;
      p.style.opacity = '1';
    };
    const from = fromIndex >= 0 && fromIndex !== activeIndex ? geo(fromIndex) : null;
    const canAnimate = typeof p.animate === 'function';
    if (!from || reduce || !canAnimate) {
      place();
      if (from && canAnimate) running.current.push(p.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120 }));
      return;
    }
    const keep = (a: Animation) => running.current.push(a);
    p.style.width = `${from.w}px`;
    keep(p.animate([
      { transform: `translateX(${from.x}px) scale(1, 1)`, opacity: 1, offset: 0 },
      { transform: `translateX(${from.x}px) scale(0.22, 0.15)`, opacity: 0, offset: 0.23 },
      { transform: `translateX(${to.x}px) scale(0.22, 0.15)`, opacity: 0, offset: 0.62 },
      { transform: `translateX(${to.x}px) scale(1.06, 1.04)`, opacity: 1, offset: 0.86, easing: 'cubic-bezier(.34,1.56,.64,1)' },
      { transform: `translateX(${to.x}px) scale(1, 1)`, opacity: 1, offset: 1 },
    ], { duration: T, fill: 'forwards' }));
    if (orb.current) keep(orb.current.animate([
      { transform: `translateX(${from.cx}px) scale(.3)`, opacity: 0, offset: 0 },
      { transform: `translateX(${from.cx}px) scale(1)`, opacity: 1, offset: 0.23 },
      { transform: `translateX(${to.cx}px) scale(1)`, opacity: 1, offset: 0.62, easing: 'cubic-bezier(.65,0,.35,1)' },
      { transform: `translateX(${to.cx}px) scale(1.6)`, opacity: 0, offset: 0.8 },
      { transform: `translateX(${to.cx}px) scale(1.6)`, opacity: 0, offset: 1 },
    ], { duration: T, fill: 'forwards' }));
    if (ripple.current) keep(ripple.current.animate([
      { transform: `translateX(${to.cx}px) scale(.2)`, opacity: 0.9 },
      { transform: `translateX(${to.cx}px) scale(${(n.offsetWidth / 40) * 1.1})`, opacity: 0 },
    ], { duration: 520, delay: ARRIVE, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'backwards' }));
    parts.current.forEach((el, i) => {
      if (!el) return;
      const ang = (i / PARTICLES) * Math.PI * 2 + 0.3;
      const r = 22 + (i % 3) * 5;
      keep(el.animate([
        { transform: `translate(${to.cx}px, 0) scale(1)`, opacity: 1 },
        { transform: `translate(${to.cx + Math.cos(ang) * r}px, ${Math.sin(ang) * r}px) scale(.2)`, opacity: 0 },
      ], { duration: 420, delay: ARRIVE, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'backwards' }));
    });
    const dir = to.cx > from.cx ? 1 : -1;
    // The dock is centred with translateX(-50%); the tilt keeps that offset.
    keep(n.animate([
      { transform: 'translateX(-50%) perspective(600px) rotateY(0deg) rotateX(0deg)' },
      { transform: `translateX(-50%) perspective(600px) rotateY(${4 * dir}deg) rotateX(5deg)`, offset: 0.3 },
      { transform: `translateX(-50%) perspective(600px) rotateY(${-1.5 * dir}deg) rotateX(-1.5deg)`, offset: 0.65 },
      { transform: 'translateX(-50%) perspective(600px) rotateY(0deg) rotateX(0deg)' },
    ], { duration: 460, delay: ARRIVE, easing: 'ease-out' }));
    const icon = links.current[activeIndex]?.querySelector<HTMLElement>('.dock-icon');
    if (icon) keep(icon.animate([
      { transform: 'translateY(0) scale(1)' },
      { transform: 'translateY(-5px) scale(1.22)', offset: 0.35 },
      { transform: 'translateY(1px) scale(.94)', offset: 0.65 },
      { transform: 'translateY(-1px) scale(1.04)', offset: 0.85 },
      { transform: 'translateY(0) scale(1)' },
    ], { duration: 460, delay: ARRIVE, easing: 'ease-out' }));
    const settle = window.setTimeout(place, T + 20);
    return () => window.clearTimeout(settle);
  }, [activeIndex, reduce, items.length]);

  useLayoutEffect(() => {
    // keep the pill on its tab when the dock resizes (rotation, font load)
    const onResize = () => {
      const a = activeIndex >= 0 ? links.current[activeIndex] : null;
      if (a && pill.current) {
        pill.current.style.width = `${a.offsetWidth}px`;
        pill.current.style.transform = `translateX(${a.offsetLeft}px)`;
      }
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [activeIndex]);

  return (
    <nav ref={nav} className="glass-bar dock shockwave" aria-label={label}>
      <span className="dock-clip" aria-hidden="true"><span ref={ripple} className="dock-ripple" /></span>
      <span ref={pill} className="dock-pill" aria-hidden="true" />
      <span ref={orb} className="dock-orb" aria-hidden="true" />
      {Array.from({ length: PARTICLES }, (_, i) => (
        <span key={i} ref={(el) => { parts.current[i] = el; }} className="dock-particle" aria-hidden="true" />
      ))}
      {items.map((i, k) => (
        <NavLink key={i.to} to={i.to} end={i.end} ref={(el) => { links.current[k] = el; }}>
          <span className="dock-icon">{i.icon}</span>
          {i.label}
          {i.extra}
        </NavLink>
      ))}
    </nav>
  );
}
