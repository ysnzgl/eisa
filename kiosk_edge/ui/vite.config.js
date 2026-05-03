import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Kiosk UI yalnızca lokal FastAPI ile konuşur (127.0.0.1:8765).
export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8765'
    }
  },
  // DRY-001: Üretim build'inde console.log/debug'ları sök.
  build: {
    target: 'es2022',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: ['log', 'debug', 'info'],
        drop_debugger: true,
      },
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
  },
});
