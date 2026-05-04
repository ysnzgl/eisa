import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      // Tüm /api/* isteklerini Django backend'e yönlendir.
      // Böylece browser aynı origin (localhost:5174) görür →
      // SameSite=Strict cookie'ler sorunsuz gönderilir.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost',
      },
    },
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
    setupFiles: [],
  },
});
