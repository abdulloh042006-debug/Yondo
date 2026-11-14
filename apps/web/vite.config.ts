/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';
import { readFileSync } from 'node:fs';
import { introFallbackText } from './src/i18n/introText';

const version: string = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).version;

// The browser only ever talks to its own origin: `/api` is proxied to FastAPI in dev and
// must be routed by the reverse proxy in production. No CORS relaxation is needed.
const target = process.env.YONDO_API_ORIGIN ?? 'http://127.0.0.1:8000';

// index.html shows the opening animation before any app code runs. Its two fallback texts are taken from the
// dictionaries here, so they are never typed into the page by hand. `<` is escaped: the JSON sits inside a <script>.
const introText = (): Plugin => ({
  name: 'yondo-intro-text',
  transformIndexHtml: { order: 'pre', handler: (html) => html.replace('"__YONDO_INTRO_TEXT__"', () => JSON.stringify(introFallbackText()).replace(/</g, '\\u003c')) },
});

export default defineConfig({
  plugins: [react(), introText()],
  define: { __APP_VERSION__: JSON.stringify(version) },
  server: { port: 5173, proxy: { '/api': { target, changeOrigin: false } } },
  preview: { port: 4173, proxy: { '/api': { target, changeOrigin: false } } },
  build: { sourcemap: false },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
