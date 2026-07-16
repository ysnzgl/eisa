import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { http } from './services/api';
import { installGlobalHandlers, initLogger } from './lib/logger';
import '@fortawesome/fontawesome-free/css/all.min.css';
import '@fontsource/figtree/300.css';
import '@fontsource/figtree/400.css';
import '@fontsource/figtree/500.css';
import '@fontsource/figtree/600.css';
import '@fontsource/figtree/700.css';
import '@fontsource/figtree/800.css';
import '@fontsource/figtree/900.css';
import '@fontsource/lexend-deca/300.css';
import '@fontsource/lexend-deca/400.css';
import '@fontsource/lexend-deca/500.css';
import '@fontsource/lexend-deca/600.css';
import '@fontsource/lexend-deca/700.css';
import '@fontsource/lexend-deca/800.css';
import '@fontsource/lexend-deca/900.css';
import '@fontsource/plus-jakarta-sans/300.css';
import '@fontsource/plus-jakarta-sans/400.css';
import '@fontsource/plus-jakarta-sans/500.css';
import '@fontsource/plus-jakarta-sans/600.css';
import '@fontsource/plus-jakarta-sans/700.css';
import '@fontsource/plus-jakarta-sans/800.css';
import '@fontsource/syne/500.css';
import '@fontsource/syne/600.css';
import '@fontsource/syne/700.css';
import '@fontsource/syne/800.css';
import '@fontsource/dm-mono/400.css';
import '@fontsource/dm-mono/500.css';
import 'vue-sonner/style.css';
import './styles.css';

const app = createApp(App).use(createPinia()).use(router);

// Merkezi frontend logger — production'da INFO/DEBUG bastirilir.
initLogger({
  appVersion: import.meta.env.VITE_APP_VERSION || 'dev',
  apiClient: http,
  correlationSource: () => window.__EISA_LAST_CORRELATION_ID__ ?? null,
});
installGlobalHandlers(app);

app.mount('#app');
