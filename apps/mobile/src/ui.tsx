import { useCallback, useEffect, useState, type ReactNode } from 'react';
import {
  ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
  type StyleProp, type TextInputProps, type ViewStyle,
} from 'react-native';
import { ApiError } from './api';
import { useNav } from './nav';

export const colors = {
  bg: '#F6F6FB',
  surface: '#FFFFFF',
  text: '#1D1B2E',
  muted: '#6B6880',
  border: '#E4E2EF',
  primary: '#5B4BDB',
  primarySoft: '#EEEBFF',
  danger: '#D33C4A',
  green: '#1F8A5B',
  amber: '#B7791F',
};

export function messageOf(exc: unknown): string {
  if (exc instanceof ApiError) return exc.message;
  return exc instanceof Error ? exc.message : String(exc);
}

export function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await run());
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setLoading(false);
    }
  }, [run]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { data, error, loading, reload, setData };
}

export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async (action: () => Promise<unknown>, after?: () => unknown): Promise<boolean> => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await after?.();
      return true;
    } catch (exc) {
      setError(messageOf(exc));
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, run, setError };
}

export function Screen({ title, children, scroll = true, right, back = true }: {
  title: string;
  children: ReactNode;
  scroll?: boolean;
  right?: ReactNode;
  back?: boolean;
}) {
  const nav = useNav();
  const canGoBack = back && nav.depth > 1;
  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        {canGoBack ? (
          <Pressable onPress={nav.pop} hitSlop={12} accessibilityRole="button" accessibilityLabel="Orqaga">
            <Text style={styles.back}>‹</Text>
          </Pressable>
        ) : null}
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        <View style={{ marginLeft: 'auto' }}>{right}</View>
      </View>
      {scroll ? (
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">{children}</ScrollView>
      ) : (
        <View style={[styles.content, { flex: 1 }]}>{children}</View>
      )}
    </View>
  );
}

export function Card({ children, style, onPress }: { children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void }) {
  const content = <View style={[styles.card, style]}>{children}</View>;
  return onPress ? <Pressable onPress={onPress}>{content}</Pressable> : content;
}

export function Button({ title, onPress, variant = 'primary', disabled, small }: {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  small?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.button,
        small && styles.buttonSmall,
        variant === 'primary' && { backgroundColor: colors.primary, borderColor: colors.primary },
        variant === 'danger' && { backgroundColor: colors.danger, borderColor: colors.danger },
        (disabled || pressed) && { opacity: disabled ? 0.45 : 0.8 },
      ]}
    >
      <Text style={[styles.buttonText, variant !== 'secondary' && { color: '#fff' }]}>{title}</Text>
    </Pressable>
  );
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={{ gap: 4 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput placeholderTextColor={colors.muted} style={[styles.input, props.multiline && { minHeight: 80, textAlignVertical: 'top' }]} {...props} />
    </View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected?: boolean; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, selected && { backgroundColor: colors.primary, borderColor: colors.primary }]}>
      <Text style={[styles.chipText, selected && { color: '#fff' }]}>{label}</Text>
    </Pressable>
  );
}

export function Chips({ options, value, onChange }: { options: [string, string][]; value: string; onChange: (value: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
      {options.map(([key, label]) => <Chip key={key} label={label} selected={value === key} onPress={() => onChange(value === key ? '' : key)} />)}
    </ScrollView>
  );
}

export function Badge({ label, tone = 'primary' }: { label: string; tone?: 'primary' | 'green' | 'amber' | 'danger' | 'muted' }) {
  const color = { primary: colors.primary, green: colors.green, amber: colors.amber, danger: colors.danger, muted: colors.muted }[tone];
  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }, style]}>{children}</View>;
}

export function H2({ children }: { children: ReactNode }) {
  return <Text style={styles.h2}>{children}</Text>;
}

export function Muted({ children }: { children: ReactNode }) {
  return <Text style={styles.muted}>{children}</Text>;
}

export function Body({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.body, style]}>{children}</Text>;
}

export function ErrorText({ error }: { error: string | null | undefined }) {
  return error ? <Text style={styles.error}>{error}</Text> : null;
}

export function Loading({ show }: { show: boolean }) {
  return show ? <ActivityIndicator color={colors.primary} style={{ marginVertical: 24 }} /> : null;
}

export function Empty({ text }: { text: string }) {
  return <Text style={[styles.muted, { textAlign: 'center', marginVertical: 24 }]}>{text}</Text>;
}

export function Photo({ uri, size = 64, radius = 12 }: { uri?: string | null; size?: number; radius?: number }) {
  if (!uri) return <View style={{ width: size, height: size, borderRadius: radius, backgroundColor: colors.primarySoft }} />;
  return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: radius, backgroundColor: colors.border }} />;
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16, paddingTop: 52, paddingBottom: 12, backgroundColor: colors.surface, borderBottomWidth: 1, borderBottomColor: colors.border },
  back: { fontSize: 32, lineHeight: 32, color: colors.primary, marginTop: -4 },
  title: { fontSize: 20, fontWeight: '700', color: colors.text, flexShrink: 1 },
  content: { padding: 16, gap: 12, paddingBottom: 40 },
  card: { backgroundColor: colors.surface, borderRadius: 14, borderWidth: 1, borderColor: colors.border, padding: 14, gap: 8 },
  button: { paddingVertical: 12, paddingHorizontal: 16, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center' },
  buttonSmall: { paddingVertical: 8, paddingHorizontal: 12 },
  buttonText: { fontSize: 15, fontWeight: '600', color: colors.text },
  label: { fontSize: 13, color: colors.muted },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, backgroundColor: colors.surface, color: colors.text },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 999, paddingVertical: 7, paddingHorizontal: 12, backgroundColor: colors.surface },
  chipText: { fontSize: 14, color: colors.text },
  badge: { borderWidth: 1, borderRadius: 999, paddingVertical: 2, paddingHorizontal: 8 },
  badgeText: { fontSize: 12, fontWeight: '600' },
  h2: { fontSize: 17, fontWeight: '700', color: colors.text, marginTop: 6 },
  muted: { fontSize: 13, color: colors.muted },
  body: { fontSize: 15, color: colors.text, lineHeight: 21 },
  error: { color: colors.danger, fontSize: 14 },
});
