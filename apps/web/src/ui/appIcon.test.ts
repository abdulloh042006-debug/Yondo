import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { APP_ICONS, applyAppIcon, effectiveAppIcon, savedAppIcon, setAppIcon } from './appIcon';
import { applyTheme } from './theme';

const href = (sel: string) => document.head.querySelector<HTMLLinkElement>(sel)?.getAttribute('href');
let manifests: Blob[] = [];

beforeEach(() => {
  manifests = [];
  let n = 0;
  URL.createObjectURL = vi.fn((b: Blob) => { manifests.push(b); return `blob:test/${n++}`; }) as never;
  URL.revokeObjectURL = vi.fn() as never;
});
afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.head.innerHTML = '';
  vi.restoreAllMocks();
});

describe('app icon', () => {
  it('lists the current icon first plus four variants', () => {
    expect(APP_ICONS.map((i) => i.id)).toEqual(['joriy', 'kartochka', 'siyoh', 'karrot', 'naqsh']);
  });
  it('default follows the skin: classic = current icon, warm = Oq kartochka; an explicit choice wins', () => {
    applyTheme('yondo');
    expect(effectiveAppIcon()).toBe('joriy');
    applyTheme('yondo-warm');
    expect(effectiveAppIcon()).toBe('kartochka');
    expect(href('link[rel="icon"][type="image/svg+xml"]')).toBe('/icons/kartochka/favicon.svg');
    setAppIcon('karrot');
    applyTheme('yondo-warm-tun');
    expect(effectiveAppIcon()).toBe('karrot');
    expect(savedAppIcon()).toBe('karrot');
  });
  it('updates icon, apple-touch-icon and the manifest link; classic icon removes the 32px png', async () => {
    document.head.innerHTML = '<meta name="theme-color" content="#111111"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">';
    setAppIcon('siyoh');
    expect(href('link[rel="icon"][type="image/svg+xml"]')).toBe('/icons/siyoh/favicon.svg');
    expect(href('link[rel="icon"][sizes="32x32"]')).toBe('/icons/siyoh/favicon-32.png');
    expect(href('link[rel="apple-touch-icon"]')).toBe('/icons/siyoh/180.png');
    expect(href('link[rel="manifest"]')).toBe(`blob:test/${manifests.length - 1}`);
    expect(document.head.querySelectorAll('link[rel="manifest"]')).toHaveLength(1);
    const json = JSON.parse(await manifests[manifests.length - 1].text());
    expect(json).toMatchObject({ name: 'Yondo', display: 'standalone', theme_color: '#111111', background_color: '#111111' });
    expect(json.icons[0].src).toBe(`${window.location.origin}/icons/siyoh/192.png`);
    setAppIcon('joriy');
    expect(href('link[rel="icon"][type="image/svg+xml"]')).toBe('/favicon.svg');
    expect(document.head.querySelector('link[rel="icon"][sizes="32x32"]')).toBeNull();
    expect(href('link[rel="apple-touch-icon"]')).toBe('/apple-touch-icon.png');
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });
  it('ignores a stored id that does not exist', () => {
    localStorage.setItem('yondo.appicon', 'bogus');
    expect(savedAppIcon()).toBeNull();
  });
  it('still applies when storage throws (choice just is not persisted)', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    expect(() => setAppIcon('naqsh')).not.toThrow();
    expect(href('link[rel="icon"][type="image/svg+xml"]')).toBe('/icons/naqsh/favicon.svg');
    expect(savedAppIcon()).toBeNull();
  });
  it('works without Blob URL support (no manifest, no crash)', () => {
    (URL as { createObjectURL?: unknown }).createObjectURL = undefined;
    expect(() => applyAppIcon('karrot')).not.toThrow();
    expect(document.head.querySelector('link[rel="manifest"]')).toBeNull();
  });
});
