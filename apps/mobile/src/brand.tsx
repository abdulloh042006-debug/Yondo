import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccessibilityInfo, Animated, StyleSheet, View } from 'react-native';
import Svg, { Circle, Defs, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';

import { CARROT, useTheme } from './theme';

/**
 * The official Yondo symbol (design-prototype/brand/logo/yondo-symbol-light|dark.svg, owner 2026-11-14: THE logo):
 * the Y-fork with two ink nodes and the carrot node. Ink on paper by day, paper on ink at night.
 */
export function BrandMark({ size = 30 }: { size?: number }) {
  const { palette } = useTheme();
  return (
    <Svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <G stroke={palette.fg} fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth={5}>
        <Path d="M14 12 28 33Q31 37 32 40M50 12 36 33Q33 37 32 40M32 40v12" />
      </G>
      <Circle cx={14} cy={12} r={7} fill={palette.fg} />
      <Circle cx={50} cy={12} r={7} fill={CARROT} />
      <Circle cx={32} cy={55} r={5.5} fill={palette.fg} />
    </Svg>
  );
}

/** Line icons copied from the web dock (apps/web/src/ui/Layout.tsx), same 24px grid and stroke. */
export const ICONS = {
  home: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  heart: 'M12 21s-7-4.4-9.3-9A5.4 5.4 0 0 1 12 6a5.4 5.4 0 0 1 9.3 6C19 16.6 12 21 12 21z',
  cal: 'M7 3v3m10-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0',
  external: 'M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5',
  chevron: 'M9 6l6 6-6 6',
} as const;

export function Icon({ d, size = 22, color, fill }: { d: string; size?: number; color: string; fill?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={fill ?? 'none'} stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <Path d={d} />
    </Svg>
  );
}

/** The web's soft carrot "aurora" behind the page, drawn once as two radial gradients (no blur filter needed). */
export function Aurora() {
  const { palette } = useTheme();
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill} aria-hidden>
      <Svg width="100%" height="100%">
        <Defs>
          <RadialGradient id="g1" cx="85%" cy="4%" r="55%">
            <Stop offset="0" stopColor={CARROT} stopOpacity={palette.glowOpacity} />
            <Stop offset="1" stopColor={CARROT} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="g2" cx="0%" cy="70%" r="50%">
            <Stop offset="0" stopColor={CARROT} stopOpacity={palette.glowOpacity * 0.6} />
            <Stop offset="1" stopColor={CARROT} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#g1)" />
        <Rect width="100%" height="100%" fill="url(#g2)" />
      </Svg>
    </View>
  );
}

/** The OS "reduce motion" setting (Android: remove animations; iOS: Reduce Motion; web: prefers-reduced-motion). */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    let live = true;
    void AccessibilityInfo.isReduceMotionEnabled()
      .then((v) => live && setReduced(v))
      .catch(() => {});
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced);
    return () => {
      live = false;
      sub.remove();
    };
  }, []);
  return reduced;
}

/** Gentle enter animation (fade + 10px rise), as the web's PageTransition/Reveal; off with reduced motion. */
export function Enter({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const reduced = useReducedMotion();
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduced) {
      v.setValue(1);
      return;
    }
    const a = Animated.timing(v, { toValue: 1, duration: 320, delay, useNativeDriver: true });
    a.start();
    return () => a.stop();
  }, [reduced, delay, v]);
  return (
    <Animated.View style={{ opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] }}>
      {children}
    </Animated.View>
  );
}
