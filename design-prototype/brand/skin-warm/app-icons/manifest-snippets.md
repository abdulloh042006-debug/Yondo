# Manifest / head snippets for ONE variant (kartochka = "Oq kartochka"), files from this folder
Copy the variant's files to `apps/web/public/icons/kartochka/` (not done here).

```html
<link rel="icon" type="image/svg+xml" href="/icons/kartochka/favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="/icons/kartochka/favicon-32.png" />
<link rel="apple-touch-icon" href="/icons/kartochka/180.png" />   <!-- 180x180, full-bleed square: iOS applies its own mask -->
<meta name="theme-color" content="#f5f2ec" />                     <!-- = --c-bg of the active theme (day #f5f2ec / night #111111) -->
<link rel="manifest" href="/manifest.webmanifest" />
```
```json
{ "name": "Yondo", "short_name": "Yondo", "start_url": "/", "display": "standalone",
  "background_color": "#f5f2ec", "theme_color": "#f5f2ec",
  "icons": [
    { "src": "/icons/kartochka/192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icons/kartochka/512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/icons/kartochka/512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/kartochka/mono.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "monochrome" } ] }
```
Masters are full-bleed with all essential art inside the central 80 % circle, so one file serves `any` and `maskable`. Rename `kartochka-512.png` -> `512.png` etc. when copying.

## Dynamic manifest and its limits
- The `<link rel=icon>`, `apple-touch-icon` and `theme-color` tags can be rewritten by JS when the user picks a variant (same pattern as `syncThemeColor` in `theme.tsx`). Tabs, bookmarks and "Add to home screen" taken AFTER the choice use the new icon.
- A manifest can be swapped at runtime (`<link rel=manifest href="/manifest-<id>.webmanifest">`, or a per-variant static file), but browsers read it at install time only. An already-installed PWA / home-screen icon does not change; the user must reinstall. iOS Safari caches the touch icon at "Add to Home Screen".
- Service-worker-generated manifests add complexity for no gain here; prefer 4 static manifests + one JS switch.
- Never claim to the user that the installed icon changed; say "keyingi o'rnatishda" (on next install).
