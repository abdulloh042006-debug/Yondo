import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccessibilityInfo, Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';

import { useReducedMotion } from './brand';
import { t } from './shared';
import { FONT, useTheme } from './theme';
import { Button, ErrorText, Row, TOUCH } from './ui';

/** Hold time (owner, 2026-11-18): exactly 1.5 s of continuous press. */
export const HOLD_MS = 1500;

/**
 * Hold-to-Confirm destructive button: the mobile twin of apps/web/src/ui/HoldToConfirm.tsx
 * (docs/design/redesign-2026-11.md §4.4). Red only here (owner, 2026-11-18).
 * - Press and hold 1.5 s: red fill sweeps left → right (native driver: two counter-moving transforms, no layout),
 *   label "Tasdiqlanmoqda…"; only a full hold calls `onConfirm`, once.
 * - Early release: the fill retracts in 0.25 s and nothing runs.
 * - A press that is not a hold (TalkBack/VoiceOver double-tap, switch control) opens an explicit two-step confirm.
 * - Steps are announced with AccessibilityInfo. Reduced motion: the fill advances in three steps.
 */
export function HoldToConfirm({
  label,
  yesLabel,
  doneLabel,
  onConfirm,
  errorText,
  children,
}: {
  label: string;
  yesLabel: string;
  /** Announced after success. */
  doneLabel?: string;
  onConfirm: () => Promise<void>;
  /** Maps a thrown error to text (by API error code), e.g. `errorText` from ./shared. */
  errorText: (e: unknown) => string;
  children?: ReactNode;
}) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const [width, setWidth] = useState(0);
  const [phase, setPhase] = useState<'idle' | 'holding' | 'busy'>('idle');
  const [twoStep, setTwoStep] = useState(false);
  const [err, setErr] = useState<string>();
  const progress = useRef(new Animated.Value(0)).current;
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const own = useRef(false);
  const clear = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  useEffect(() => clear, []);

  const run = async () => {
    setPhase('busy');
    setErr(undefined);
    progress.setValue(1);
    try {
      await onConfirm();
      if (doneLabel) AccessibilityInfo.announceForAccessibility(doneLabel);
    } catch (e) {
      setErr(errorText(e));
      setPhase('idle');
      Animated.timing(progress, { toValue: 0, duration: 250, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
    }
  };
  const start = () => {
    if (phase !== 'idle') return;
    setTwoStep(false);
    setErr(undefined);
    setPhase('holding');
    AccessibilityInfo.announceForAccessibility(t('hold.started'));
    progress.stopAnimation();
    progress.setValue(0);
    if (reduced) {
      [1, 2].forEach((i) => timers.current.push(setTimeout(() => progress.setValue(i / 3), (HOLD_MS / 3) * i)));
    } else {
      Animated.timing(progress, { toValue: 1, duration: HOLD_MS, easing: Easing.linear, useNativeDriver: true }).start();
    }
    timers.current.push(setTimeout(() => void run(), HOLD_MS));
  };
  const cancel = () => {
    if (phase !== 'holding') return;
    clear();
    progress.stopAnimation();
    setPhase('idle');
    AccessibilityInfo.announceForAccessibility(t('hold.cancelled'));
    if (reduced) progress.setValue(0);
    else Animated.timing(progress, { toValue: 0, duration: 250, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
  };

  const openTwoStep = () => {
    setTwoStep(true);
    AccessibilityInfo.announceForAccessibility(t('hold.twoStep', { action: label }));
  };

  const text = phase === 'idle' ? label : t('hold.confirming');
  // The fill window slides in from the left while its content slides the other way, so the light label stays put.
  const shift = progress.interpolate({ inputRange: [0, 1], outputRange: [-width, 0] });
  const counter = progress.interpolate({ inputRange: [0, 1], outputRange: [width, 0] });
  return (
    <View style={[styles.zone, { backgroundColor: palette.dangerSoft, borderColor: palette.danger }]}>
      {children}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityHint={t('hold.hint')}
        accessibilityState={{ busy: phase === 'busy' }}
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        onPressIn={() => {
          own.current = true;
          start();
        }}
        onPressOut={() => {
          cancel();
          setTimeout(() => (own.current = false), 60);
        }}
        onPress={() => {
          if (own.current || phase !== 'idle') return;
          openTwoStep();
        }}
        // TalkBack / VoiceOver "activate" is never a hold: it opens the explicit two-step confirmation.
        accessibilityActions={[{ name: 'activate' }]}
        onAccessibilityAction={(e) => {
          if (e.nativeEvent.actionName === 'activate' && phase === 'idle') openTwoStep();
        }}
        style={[styles.btn, { borderColor: palette.danger, backgroundColor: palette.surface }]}
      >
        <Text style={[styles.label, { color: palette.danger }]}>{text}</Text>
        <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.clip, { transform: [{ translateX: shift }] }]}>
          <Animated.View style={[StyleSheet.absoluteFill, styles.fill, { backgroundColor: palette.danger, transform: [{ translateX: counter }] }]}>
            <Text style={[styles.label, { color: palette.onDanger }]}>{text}</Text>
          </Animated.View>
        </Animated.View>
      </Pressable>
      <Text style={[styles.hint, { color: palette.muted }]}>{t('hold.hint')}</Text>
      {twoStep && (
        <Row>
          <Button kind="ghost" label={t('hold.no')} onPress={() => { setTwoStep(false); AccessibilityInfo.announceForAccessibility(t('hold.cancelled')); }} />
          <Pressable
            accessibilityRole="button"
            onPress={() => { setTwoStep(false); void run(); }}
            style={[styles.yes, { backgroundColor: palette.danger }]}
          >
            <Text style={[styles.yesText, { color: palette.onDanger }]}>{yesLabel}</Text>
          </Pressable>
        </Row>
      )}
      {err && <ErrorText text={err} />}
    </View>
  );
}

const styles = StyleSheet.create({
  zone: { gap: 10, padding: 14, borderRadius: 20, borderWidth: 1.5 },
  btn: { minHeight: 52, borderRadius: 999, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center', overflow: 'hidden', paddingHorizontal: 20 },
  clip: { overflow: 'hidden', borderRadius: 999 },
  fill: { alignItems: 'center', justifyContent: 'center' },
  label: { fontFamily: FONT.bold, fontSize: 15 },
  hint: { fontFamily: FONT.body, fontSize: 12, textAlign: 'center' },
  yes: { minHeight: TOUCH, borderRadius: 999, paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center' },
  yesText: { fontFamily: FONT.bold, fontSize: 15 },
});
