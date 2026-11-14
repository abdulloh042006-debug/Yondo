import { useState, type ReactNode } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import { Enter, ICONS, Icon, useReducedMotion } from './brand';
import { t } from './shared';
import { FONT, useTheme } from './theme';

/** Minimum touch target (WCAG 2.5.5 / platform guidelines). */
export const TOUCH = 44;

export function Screen({ children, refresh }: { children: ReactNode; refresh?: ReactNode }) {
  // Transparent: the app shell paints the paper/ink ground and the carrot aurora behind every screen.
  return (
    <ScrollView style={{ backgroundColor: 'transparent' }} contentContainerStyle={styles.screen} keyboardShouldPersistTaps="handled">
      {refresh}
      <Enter>
        <View style={styles.screenInner}>{children}</View>
      </Enter>
    </ScrollView>
  );
}

export function H1({ children }: { children: ReactNode }) {
  const { palette } = useTheme();
  return <Text role="heading" aria-level={1} style={[styles.h1, { color: palette.fg }]}>{children}</Text>;
}

export function H2({ children }: { children: ReactNode }) {
  const { palette } = useTheme();
  return <Text role="heading" aria-level={2} style={[styles.h2, { color: palette.fg }]}>{children}</Text>;
}

export function P({ children, muted, style }: { children: ReactNode; muted?: boolean; style?: TextStyle }) {
  const { palette } = useTheme();
  return <Text style={[styles.p, { color: muted ? palette.muted : palette.fg }, style]}>{children}</Text>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const { palette } = useTheme();
  return <View style={[styles.card, { backgroundColor: palette.glass, borderColor: palette.glassLine }, style]}>{children}</View>;
}

export function Row({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

type Kind = 'primary' | 'ghost' | 'danger';
export function Button({
  label,
  onPress,
  kind = 'primary',
  busy,
  disabled,
  small,
  accessibilityLabel,
}: {
  label: string;
  onPress: () => void;
  kind?: Kind;
  busy?: boolean;
  disabled?: boolean;
  small?: boolean;
  accessibilityLabel?: string;
}) {
  const { palette } = useTheme();
  const bg = kind === 'primary' ? palette.primary : kind === 'danger' ? palette.accent : 'transparent';
  // Danger = carrot fill with INK text (carrot never carries small text on paper).
  const fg = kind === 'primary' ? palette.onPrimary : kind === 'danger' ? '#111111' : palette.fg;
  const off = disabled || busy;
  const reduced = useReducedMotion();
  return (
    <Pressable
      role="button"
      aria-label={accessibilityLabel ?? label}
      aria-disabled={!!off}
      aria-busy={!!busy}
      disabled={off}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        small && styles.buttonSmall,
        { backgroundColor: kind === 'ghost' ? palette.glass : bg, borderColor: kind === 'ghost' ? palette.glassLine : bg, opacity: off ? 0.5 : pressed ? 0.85 : 1 },
        pressed && !reduced && { transform: [{ scale: 0.97 }] },
      ]}
    >
      {busy && <ActivityIndicator color={fg} style={{ marginRight: 8 }} />}
      <Text style={[styles.buttonText, { color: fg }]}>{label}</Text>
    </Pressable>
  );
}

/** Single choice from a few options: radio semantics (role="radio" + aria-checked inside a ChipGroup). */
export function ChipGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <View role="radiogroup" aria-label={label} style={styles.row}>
      {children}
    </View>
  );
}

/** `toggle` = an on/off chip outside a radio group (role checkbox), e.g. the account's roles. */
export function Chip({ label, selected, onPress, toggle }: { label: string; selected: boolean; onPress: () => void; toggle?: boolean }) {
  const { palette } = useTheme();
  return (
    <Pressable
      role={toggle ? 'checkbox' : 'radio'}
      aria-checked={selected}
      aria-label={label}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        pressed && { opacity: 0.85 },
        { backgroundColor: selected ? palette.primary : palette.glass, borderColor: selected ? palette.accent : palette.glassLine },
      ]}
    >
      <Text style={{ color: selected ? palette.onPrimary : palette.fg, fontFamily: FONT.medium }}>{label}</Text>
    </Pressable>
  );
}

export function Field({ label, error, hint, ...input }: TextInputProps & { label: string; error?: string; hint?: string }) {
  const { palette } = useTheme();
  return (
    <View style={{ gap: 4 }}>
      <Text style={[styles.label, { color: palette.fg }]}>{label}</Text>
      <TextInput
        aria-label={label}
        aria-invalid={!!error}
        placeholderTextColor={palette.muted}
        {...input}
        style={[
          styles.input,
          { color: palette.fg, backgroundColor: palette.glass, borderColor: error ? palette.accent : palette.glassLine },
          // Multi-line fields (support message) grow from the top, as a textarea on the web.
          input.multiline && { minHeight: 96, textAlignVertical: 'top', paddingTop: 10 },
        ]}
      />
      {hint && !error && <Text style={{ color: palette.muted, fontSize: 13, fontFamily: FONT.body }}>{hint}</Text>}
      {error && <ErrorText text={error} />}
    </View>
  );
}

/** Errors are ink text with a carrot rule beside them (meaning by words, not hue). */
export function ErrorText({ text }: { text: string }) {
  const { palette } = useTheme();
  return (
    <View role="alert" style={[styles.note, { borderLeftColor: palette.accent }]}>
      <Text style={{ color: palette.fg, fontFamily: FONT.body }}>{text}</Text>
    </View>
  );
}

export function Banner({ text }: { text: string }) {
  const { palette } = useTheme();
  return (
    <View role="status" style={[styles.note, { borderLeftColor: palette.accent, backgroundColor: palette.glass }]}>
      <Text style={{ color: palette.fg, fontFamily: FONT.body }}>{text}</Text>
    </View>
  );
}

export function Tag({ text, attention }: { text: string; attention?: boolean }) {
  const { palette } = useTheme();
  return (
    <View style={[styles.tag, { backgroundColor: palette.chip, borderColor: attention ? palette.accent : palette.line }]}>
      <Text style={{ color: palette.fg, fontSize: 13, fontFamily: FONT.medium }}>{text}</Text>
    </View>
  );
}

export function Loading() {
  const { palette } = useTheme();
  return (
    <View role="progressbar" aria-label={t('common.loading')} aria-busy style={{ padding: 24, alignItems: 'center' }}>
      <ActivityIndicator color={palette.fg} />
    </View>
  );
}

export function Sheet({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  const { palette } = useTheme();
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.scrim}>
        <View role="dialog" aria-modal aria-label={title} style={[styles.sheet, { backgroundColor: palette.bg, borderColor: palette.line }]}>
          <ScrollView contentContainerStyle={{ gap: 12 }} keyboardShouldPersistTaps="handled">
            <H2>{title}</H2>
            {children}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

/** A confirmation step for actions that change a booking. */
export function useConfirm() {
  const [pending, setPending] = useState<{ title: string; body: string; confirm: string; run: () => Promise<void> }>();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const element = pending ? (
    <Sheet open title={pending.title} onClose={() => !busy && setPending(undefined)}>
      <P>{pending.body}</P>
      {err && <ErrorText text={err} />}
      <Row>
        <Button label={t('common.cancel')} kind="ghost" disabled={busy} onPress={() => setPending(undefined)} />
        <Button
          label={pending.confirm}
          busy={busy}
          onPress={() => {
            setBusy(true);
            setErr(undefined);
            pending
              .run()
              .then(() => setPending(undefined))
              .catch((e: Error) => setErr(e.message || t('common.actionFailed')))
              .finally(() => setBusy(false));
          }}
        />
      </Row>
    </Sheet>
  ) : null;
  return { ask: setPending, element };
}

/**
 * One row of the Profil hub menu (the web's .menu-item). `web` marks a row that opens the web app in the browser:
 * it says so in words and shows the external-link icon, so it is never mistaken for a native screen.
 */
export function MenuRow({ title, hint, badge, web, onPress }: { title: string; hint?: string; badge?: string; web?: boolean; onPress: () => void }) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const label = [title, badge, hint, web ? t('mobile.opensInWeb') : null].filter(Boolean).join('. ');
  return (
    <Pressable
      role={web ? 'link' : 'button'}
      aria-label={label}
      onPress={onPress}
      style={({ pressed }) => [styles.menuRow, { borderColor: palette.glassLine }, pressed && { backgroundColor: palette.pill }, pressed && !reduced && { transform: [{ scale: 0.99 }] }]}
    >
      <View style={{ flex: 1, gap: 2 }}>
        <View style={styles.row}>
          <Text style={{ color: palette.fg, fontSize: 16, fontFamily: FONT.bold }}>{title}</Text>
          {badge && <Tag text={badge} attention />}
        </View>
        {hint && <Text style={{ color: palette.muted, fontSize: 14, fontFamily: FONT.body }}>{hint}</Text>}
        {web && <Text style={{ color: palette.muted, fontSize: 13, fontFamily: FONT.medium }}>{t('mobile.opensInWeb')}</Text>}
      </View>
      <Icon d={web ? ICONS.external : ICONS.chevron} size={20} color={palette.muted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { padding: 16, paddingBottom: 32 },
  screenInner: { gap: 14 },
  h1: { fontSize: 30, lineHeight: 34, fontFamily: FONT.display, letterSpacing: -0.3 },
  h2: { fontSize: 21, lineHeight: 26, fontFamily: FONT.display },
  p: { fontSize: 16, lineHeight: 23, fontFamily: FONT.body },
  card: { borderWidth: 1, borderRadius: 22, padding: 16, gap: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  button: {
    minHeight: TOUCH,
    paddingHorizontal: 18,
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonSmall: { paddingHorizontal: 14 },
  buttonText: { fontSize: 16, fontFamily: FONT.bold },
  chip: { minHeight: TOUCH, paddingHorizontal: 14, borderRadius: 999, borderWidth: 1, justifyContent: 'center' },
  label: { fontSize: 15, fontFamily: FONT.medium },
  input: { minHeight: TOUCH, borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, fontSize: 16, fontFamily: FONT.body },
  note: { borderLeftWidth: 4, paddingVertical: 8, paddingHorizontal: 10, borderRadius: 6 },
  menuRow: { minHeight: 56, flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, paddingHorizontal: 8, borderRadius: 14, borderBottomWidth: StyleSheet.hairlineWidth },
  tag: { alignSelf: 'flex-start', borderWidth: 1.5, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  scrim: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(17,17,17,0.55)' },
  sheet: { maxHeight: '88%', borderTopLeftRadius: 20, borderTopRightRadius: 20, borderWidth: 1, padding: 16 },
});
