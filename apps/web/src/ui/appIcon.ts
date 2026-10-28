import { type AppIconId, currentSkin, safeStorage, SKINS } from './skin';

/**
 * Optional app-icon choice. Web only: it rewrites <link rel=icon>, <link rel=apple-touch-icon> and a generated web-app
 * manifest. An already installed home-screen app keeps the icon it was installed with (the manifest is read at install
 * time); real alternate icons need the native app. Stored locally (no server, no personal data).
 */
export interface AppIconDef {
  id: AppIconId;
  svg: string;
  png32?: string;
  touch: string;
  manifestIcons: { src: string; sizes: string; type: string; purpose?: string }[];
}

const variant = (id: Exclude<AppIconId, 'joriy'>): AppIconDef => ({
  id,
  svg: `/icons/${id}/favicon.svg`,
  png32: `/icons/${id}/favicon-32.png`,
  touch: `/icons/${id}/180.png`,
  manifestIcons: [
    { src: `/icons/${id}/192.png`, sizes: '192x192', type: 'image/png', purpose: 'any' },
    { src: `/icons/${id}/512.png`, sizes: '512x512', type: 'image/png', purpose: 'any' },
    { src: `/icons/${id}/512.png`, sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    { src: `/icons/${id}/mono.svg`, sizes: 'any', type: 'image/svg+xml', purpose: 'monochrome' },
  ],
});

export const APP_ICONS: AppIconDef[] = [
  {
    id: 'joriy',
    svg: '/favicon.svg',
    touch: '/apple-touch-icon.png',
    manifestIcons: [
      { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
    ],
  },
  variant('kartochka'),
  variant('siyoh'),
  variant('karrot'),
  variant('naqsh'),
];

const KEY = 'yondo.appicon';

export function savedAppIcon(): AppIconId | null {
  const v = safeStorage.get(KEY);
  return APP_ICONS.some((i) => i.id === v) ? (v as AppIconId) : null;
}

/** Saved choice, else the active skin's default (classic: the current icon; warm: "Oq kartochka"). */
export function effectiveAppIcon(): AppIconId {
  return savedAppIcon() ?? SKINS[currentSkin()].appIconDefault;
}

function link(rel: string, match: string, create: () => HTMLLinkElement): HTMLLinkElement {
  let el = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]${match}`);
  if (!el) {
    el = create();
    document.head.appendChild(el);
  }
  return el;
}
const mkLink = (rel: string, attrs: Record<string, string> = {}) => () => {
  const el = document.createElement('link');
  el.rel = rel;
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

let manifestUrl: string | null = null;

function syncManifest(def: AppIconDef) {
  if (typeof URL.createObjectURL !== 'function') return;
  const chrome = document.head.querySelector<HTMLMetaElement>('meta[name="theme-color"]')?.content || '#f5f2ec';
  const origin = window.location.origin;
  const manifest = {
    name: 'Yondo',
    short_name: 'Yondo',
    start_url: `${origin}/`,
    scope: `${origin}/`,
    display: 'standalone',
    background_color: chrome,
    theme_color: chrome,
    icons: def.manifestIcons.map((i) => ({ ...i, src: origin + i.src })),
  };
  const next = URL.createObjectURL(new Blob([JSON.stringify(manifest)], { type: 'application/manifest+json' }));
  link('manifest', '', mkLink('manifest')).href = next;
  if (manifestUrl) URL.revokeObjectURL(manifestUrl);
  manifestUrl = next;
}

/** Point the head tags at the given icon. Safe to call repeatedly. */
export function applyAppIcon(id: AppIconId = effectiveAppIcon()) {
  const def = APP_ICONS.find((i) => i.id === id) ?? APP_ICONS[0];
  link('icon', '[type="image/svg+xml"]', mkLink('icon', { type: 'image/svg+xml' })).href = def.svg;
  const png = document.head.querySelector<HTMLLinkElement>('link[rel="icon"][sizes="32x32"]');
  if (def.png32) {
    (png ?? link('icon', '[sizes="32x32"]', mkLink('icon', { type: 'image/png', sizes: '32x32' }))).href = def.png32;
  } else {
    png?.remove();
  }
  link('apple-touch-icon', '', mkLink('apple-touch-icon')).href = def.touch;
  try {
    syncManifest(def);
  } catch {
    /* manifest is a nicety */
  }
}

export function setAppIcon(id: AppIconId) {
  safeStorage.set(KEY, id);
  applyAppIcon(id);
}
