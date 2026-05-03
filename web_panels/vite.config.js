import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: { port: 5174 },
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
    setupFiles: [],
  },
});
