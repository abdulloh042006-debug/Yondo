import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View, type LayoutRectangle } from 'react-native';

import { Icon, useReducedMotion } from './brand';
import { t } from './shared';
import { CARROT, FONT, useTheme } from './theme';
import { TOUCH } from './ui';

export interface DockTab<Id extends string> {
  id: Id;
  label: string;
  icon: string;
  dot?: boolean;
}

const T = 520; // flight: shrink 0–23 %, travel 23–62 %, expand 62–100 % (docs/design/redesign-2026-11.md §4.1)
const ARRIVE = Math.round(T * 0.62);
const PARTICLES = 8;

/**
 * "Quantum Shockwave" dock: the mobile twin of apps/web/src/ui/ShockwaveDock.tsx. Pill = palette.primary (ink by day,
 * paper at night) with onPrimary label; orb, ripple and particles are carrot (graphic only). Everything runs on the
 * native driver (transform + opacity). Reduced motion: the pill jumps to the tab; nothing travels or bounces.
 */
export function ShockwaveDock<Id extends string>({
  tabs,
  active,
  onSelect,
  bottom,
  height,
}: {
  tabs: DockTab<Id>[];
  active: Id;
  onSelect: (id: Id) => void;
  bottom: number;
  height: number;
}) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const [boxes, setBoxes] = useState<Record<string, LayoutRectangle>>({});
  const [dockW, setDockW] = useState(0);
  const phase = useRef(new Animated.Value(1)).current;
  const arrive = useRef(new Animated.Value(1)).current;
  const [flight, setFlight] = useState<{ from: LayoutRectangle; to: LayoutRectangle; dir: number } | null>(null);
  const prev = useRef<Id>(active);

  useEffect(() => {
    const from = boxes[prev.current];
    const to = boxes[active];
    const changed = prev.current !== active;
    prev.current = active;
    if (!changed || !from || !to || reduced) {
      phase.setValue(1);
      arrive.setValue(1);
      setFlight(null);
      return;
    }
    setFlight({ from, to, dir: to.x > from.x ? 1 : -1 });
    phase.setValue(0);
    arrive.setValue(0);
    const a = Animated.parallel([
      Animated.timing(phase, { toValue: 1, duration: T, easing: Easing.linear, useNativeDriver: true }),
      Animated.sequence([
        Animated.delay(ARRIVE),
        Animated.timing(arrive, { toValue: 1, duration: 480, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
      ]),
    ]);
    a.start(() => setFlight(null));
    return () => a.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, reduced]);

  const to = boxes[active];
  const cx = (b?: LayoutRectangle) => (b ? b.x + b.width / 2 : 0);
  const pillW = to?.width ?? 0;
  const f = flight;
  const pillTx = f
    ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 1], outputRange: [cx(f.from) - pillW / 2, cx(f.from) - pillW / 2, cx(f.to) - pillW / 2, cx(f.to) - pillW / 2] })
    : cx(to) - pillW / 2;
  const startSx = f && pillW ? f.from.width / pillW : 1;
  const pillSx = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 0.86, 1], outputRange: [startSx, 0.22, 0.22, 1.06, 1] }) : 1;
  const pillSy = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 0.86, 1], outputRange: [1, 0.15, 0.15, 1.04, 1] }) : 1;
  const pillOp = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 0.7, 1], outputRange: [1, 0, 0, 1, 1] }) : to ? 1 : 0;
  const orbTx = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 1], outputRange: [cx(f.from), cx(f.from), cx(f.to), cx(f.to)] }) : 0;
  const orbOp = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 0.8, 1], outputRange: [0, 1, 1, 0, 0] }) : 0;
  const orbSc = f ? phase.interpolate({ inputRange: [0, 0.23, 0.62, 0.8, 1], outputRange: [0.3, 1, 1, 1.6, 1.6] }) : 1;
  const ripSc = arrive.interpolate({ inputRange: [0, 1], outputRange: [0.2, Math.max(1, (dockW / 40) * 1.1)] });
  const ripOp = f ? arrive.interpolate({ inputRange: [0, 0.05, 1], outputRange: [0, 0.9, 0] }) : 0;
  const tiltY = f ? arrive.interpolate({ inputRange: [0, 0.3, 0.65, 1], outputRange: ['0deg', `${4 * f.dir}deg`, `${-1.5 * f.dir}deg`, '0deg'] }) : '0deg';
  const tiltX = f ? arrive.interpolate({ inputRange: [0, 0.3, 0.65, 1], outputRange: ['0deg', '5deg', '-1.5deg', '0deg'] }) : '0deg';
  const bounceY = f ? arrive.interpolate({ inputRange: [0, 0.35, 0.65, 0.85, 1], outputRange: [0, -5, 1, -1, 0] }) : 0;
  const bounceS = f ? arrive.interpolate({ inputRange: [0, 0.35, 0.65, 0.85, 1], outputRange: [1, 1.22, 0.94, 1.04, 1] }) : 1;

  return (
    <Animated.View
      role="tablist"
      aria-label={t('nav.mobile')}
      onLayout={(e) => setDockW(e.nativeEvent.layout.width)}
      style={[
        styles.dock,
        { bottom, height, backgroundColor: palette.bar, borderColor: palette.glassLine },
        { transform: [{ perspective: 600 }, { rotateY: tiltY }, { rotateX: tiltX }] },
      ]}
    >
      <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.clip]}>
        <Animated.View style={[styles.ripple, { top: height / 2 - 20, opacity: ripOp, transform: [{ translateX: f ? cx(f.to) - 20 : 0 }, { scale: ripSc }] }]} />
      </View>
      <Animated.View
        pointerEvents="none"
        style={[styles.pill, { width: pillW, backgroundColor: palette.primary, opacity: pillOp, transform: [{ translateX: pillTx }, { scaleX: pillSx }, { scaleY: pillSy }] }]}
      />
      <Animated.View pointerEvents="none" style={[styles.orb, { top: height / 2 - 9, opacity: orbOp, transform: [{ translateX: Animated.subtract(orbTx, 9) }, { scale: orbSc }] }]} />
      {f &&
        Array.from({ length: PARTICLES }, (_, i) => {
          const ang = (i / PARTICLES) * Math.PI * 2 + 0.3;
          const r = 22 + (i % 3) * 5;
          return (
            <Animated.View
              key={i}
              pointerEvents="none"
              style={[
                styles.particle,
                {
                  top: height / 2 - 2.5,
                  opacity: arrive.interpolate({ inputRange: [0, 0.02, 0.85, 1], outputRange: [0, 1, 0, 0] }),
                  transform: [
                    { translateX: arrive.interpolate({ inputRange: [0, 1], outputRange: [cx(f.to) - 2.5, cx(f.to) - 2.5 + Math.cos(ang) * r] }) },
                    { translateY: arrive.interpolate({ inputRange: [0, 1], outputRange: [0, Math.sin(ang) * r] }) },
                    { scale: arrive.interpolate({ inputRange: [0, 1], outputRange: [1, 0.2] }) },
                  ],
                },
              ]}
            />
          );
        })}
      {tabs.map((tab) => {
        const on = tab.id === active;
        return (
          <Pressable
            key={tab.id}
            role="tab"
            aria-selected={on}
            aria-label={tab.label}
            accessibilityHint={tab.dot ? t('nav.unread') : undefined}
            onPress={() => onSelect(tab.id)}
            onLayout={(e) => {
              const box = e.nativeEvent.layout;
              setBoxes((b) => ({ ...b, [tab.id]: box }));
            }}
            style={({ pressed }) => [styles.item, pressed && !reduced && { transform: [{ scale: 0.92 }] }]}
          >
            <Animated.View style={on ? { transform: [{ translateY: bounceY }, { scale: bounceS }] } : undefined}>
              <Icon d={tab.icon} color={on ? palette.onPrimary : palette.muted} />
            </Animated.View>
            {tab.dot && <View testID="unread-dot" aria-hidden style={styles.dot} />}
            <Text numberOfLines={1} style={{ color: on ? palette.onPrimary : palette.muted, fontSize: 12, fontFamily: on ? FONT.bold : FONT.medium }}>
              {tab.label}
            </Text>
          </Pressable>
        );
      })}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  dock: {
    position: 'absolute',
    left: 12,
    right: 12,
    flexDirection: 'row',
    padding: 6,
    borderRadius: 999,
    borderWidth: 1,
    shadowColor: '#000000',
    shadowOpacity: 0.18,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
  clip: { borderRadius: 999, overflow: 'hidden' },
  item: { flex: 1, minHeight: TOUCH, borderRadius: 999, alignItems: 'center', justifyContent: 'center', gap: 2, zIndex: 2 },
  pill: { position: 'absolute', top: 6, bottom: 6, left: 0, borderRadius: 999 },
  orb: {
    position: 'absolute', left: 0, width: 18, height: 18, borderRadius: 9, backgroundColor: CARROT,
    shadowColor: CARROT, shadowOpacity: 0.7, shadowRadius: 10, shadowOffset: { width: 0, height: 0 },
  },
  particle: { position: 'absolute', left: 0, width: 5, height: 5, borderRadius: 3, backgroundColor: CARROT, zIndex: 3 },
  ripple: { position: 'absolute', left: 0, width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: CARROT },
  dot: { position: 'absolute', top: 6, right: '30%', width: 9, height: 9, borderRadius: 5, backgroundColor: CARROT },
});
