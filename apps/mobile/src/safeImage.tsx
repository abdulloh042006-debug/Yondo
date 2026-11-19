import { useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet, View, type ImageStyle, type StyleProp } from 'react-native';

import { BrandMark, useReducedMotion } from './brand';
import { useTheme } from './theme';

/** Give up on a photo that has not loaded after this long. */
export const IMAGE_TIMEOUT_MS = 15000;

/**
 * Photo with the Yondo logo as placeholder (owner, 2026-11-19): the mobile twin of apps/web/src/ui/SafeImage.tsx.
 * While loading, and permanently on failure (error, timeout, or no URL could be obtained: `src === null`), the box
 * shows the official symbol on a calm paper/ink tile; the photo fades in on load (no fade with reduced motion).
 * `src === undefined` = the URL is still being fetched. The box keeps its size, so nothing shifts.
 */
export function SafeImage(props: { src: string | null | undefined; alt: string; style: StyleProp<ImageStyle> }) {
  return <Attempt key={String(props.src)} {...props} />;
}

function Attempt({ src, alt, style }: { src: string | null | undefined; alt: string; style: StyleProp<ImageStyle> }) {
  const { palette } = useTheme();
  const reduced = useReducedMotion();
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>(src === null ? 'error' : 'loading');
  const fade = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!src) return;
    const timer = setTimeout(() => setStatus((s) => (s === 'loading' ? 'error' : s)), IMAGE_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [src]);
  const flat = StyleSheet.flatten(style) ?? {};
  const logoSize = typeof flat.height === 'number' ? Math.min(44, flat.height * 0.4) : 44;
  return (
    <View style={[style, { overflow: 'hidden', backgroundColor: palette.chip }]}>
      {status !== 'loaded' && (
        <View testID="image-fallback" aria-hidden style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center' }]}>
          <View style={{ opacity: 0.7 }}>
            <BrandMark size={logoSize} />
          </View>
        </View>
      )}
      {src && status !== 'error' && (
        <Animated.Image
          source={{ uri: src }}
          alt={alt}
          style={[StyleSheet.absoluteFill, { width: '100%', height: '100%', opacity: status === 'loaded' ? fade : 0 }]}
          onLoad={() => {
            setStatus('loaded');
            if (reduced) fade.setValue(1);
            else Animated.timing(fade, { toValue: 1, duration: 300, useNativeDriver: true }).start();
          }}
          onError={() => setStatus('error')}
        />
      )}
    </View>
  );
}

