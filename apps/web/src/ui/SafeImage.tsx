import { useEffect, useState, type ImgHTMLAttributes } from 'react';

/** Official Yondo symbol (design-prototype/brand/logo): two converging lines, ink + the single carrot node. */
export function LogoMark({ className, size = 30 }: { className?: string; size?: number }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <g stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="9">
        <path d="M16 15 28 34Q31 38 32 40M48 15 36 34Q33 38 32 40M32 40v17" />
      </g>
      <circle cx="16" cy="15" r="9" fill="currentColor" />
      <circle cx="48" cy="15" r="9" fill="#E8501A" />
    </svg>
  );
}

/** A photo that never shows a broken image: give up after this long without a load event. */
export const IMAGE_TIMEOUT_MS = 15000;

type Status = 'loading' | 'loaded' | 'error';

/**
 * Photo with the Yondo logo as placeholder (owner, 2026-11-19): while the picture loads, and permanently when it
 * fails (404, network, decode error, timeout, or no URL could be obtained), the tile shows the official symbol on a
 * calm paper (day) / ink (night) ground. The tile keeps the parent's size, so nothing shifts. The photo fades in when
 * it has loaded (no fade under reduced motion). Alt text stays on the <img>; the logo is decorative.
 * `src === undefined` = the URL is still being fetched; `src === null` = no URL could be obtained.
 */
type Props = { src: string | null | undefined; alt: string } & Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'alt'>;

export function SafeImage(props: Props) {
  // A new URL starts a fresh attempt (state resets through the key).
  return <SafeImageAttempt key={String(props.src)} {...props} />;
}

function SafeImageAttempt({ src, alt, className, ...rest }: Props) {
  const [status, setStatus] = useState<Status>(src === null ? 'error' : 'loading');
  useEffect(() => {
    if (!src) return;
    const timer = window.setTimeout(() => setStatus((s) => (s === 'loading' ? 'error' : s)), IMAGE_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [src]);
  return (
    <span className="safe-img" data-status={status}>
      {status !== 'loaded' && (
        <span className="safe-img-logo" data-testid="image-fallback">
          <LogoMark size={44} />
        </span>
      )}
      {src && status !== 'error' && (
        <img
          {...rest}
          className={`safe-img-photo${className ? ` ${className}` : ''}`}
          src={src}
          alt={alt}
          onLoad={() => setStatus('loaded')}
          onError={() => setStatus('error')}
        />
      )}
    </span>
  );
}
