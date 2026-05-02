import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: { port: 5174 },
  build: { target: 'es2022' },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: [],
  },
});
