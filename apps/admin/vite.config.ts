import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// In development the API is proxied, so no CORS configuration is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.YONDO_API_ORIGIN ?? 'http://localhost:8000' },
  },
  test: { environment: 'jsdom' },
} as never);
