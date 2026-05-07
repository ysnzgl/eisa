<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const showPassword = ref(false);
const isLoading = ref(false);
const errorMsg = ref('');
const isVisible = ref(false);

const auth = useAuthStore();
const router = useRouter();

onMounted(() => {
  // Staggered entrance animation trigger
  requestAnimationFrame(() => { isVisible.value = true; });
});

async function submit() {
  if (!username.value.trim() || !password.value) return;
  isLoading.value = true;
  errorMsg.value = '';
  try {
    await auth.login(username.value.trim(), password.value);
    router.push(auth.role === 'superadmin' ? '/admin' : '/pharmacist');
  } catch {
    errorMsg.value = 'Kullanıcı adı veya şifre hatalı. Lütfen tekrar deneyin.';
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="lr-root">

    <!-- ══════════════════════════════════════════
         LEFT — Brand Panel
    ══════════════════════════════════════════ -->
    <div class="lr-brand">
      <!-- Ambient glow orbs -->
      <div class="orb orb-a" />
      <div class="orb orb-b" />
      <div class="orb orb-c" />

      <!-- Subtle grid overlay -->
      <div class="grid-overlay" />

      <!-- Floating medical crosses -->
      <span class="cross cross-1">+</span>
      <span class="cross cross-2">+</span>
      <span class="cross cross-3">+</span>
      <span class="cross cross-4">✕</span>

      <!-- Brand content -->
      <div class="brand-body" :class="{ 'is-visible': isVisible }">
        <div class="brand-wordmark">
          <span class="wm-e">e</span><span class="wm-dash">-</span><span class="wm-isa">İSA</span>
        </div>

        <h1 class="brand-headline">
          Akıllı Eczane<br />
          <em>Asistanı</em>
        </h1>

        <p class="brand-tagline">
          Türkiye'nin dijital takviye yönetim platformu
        </p>

        <ul class="brand-features">
          <li>
            <span class="feat-dot" />
            Gerçek zamanlı Reklam yönetimi
          </li>
          <li>
            <span class="feat-dot" />
            Offline-first kiosk entegrasyonu
          </li>
          <li>
            <span class="feat-dot" />
            KVKK uyumlu analitik altyapı
          </li>
        </ul>

        <div class="brand-version">
          <span class="version-badge">v2.0</span>
          <span>e-isa · 2026</span>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════
         RIGHT — Form Panel
    ══════════════════════════════════════════ -->
    <div class="lr-form-panel">
      <div class="lr-form-card" :class="{ 'is-visible': isVisible }">

        <!-- Card header -->
        <header class="fc-header">
          <div class="fc-logo">
            <span class="fcl-e">e</span><span class="fcl-dash">-</span><span class="fcl-isa">İSA</span>
          </div>
          <h2 class="fc-title">Panel Girişi</h2>
          <p class="fc-subtitle">Devam etmek için hesabınıza giriş yapın</p>
        </header>

        <!-- Error banner -->
        <Transition name="shake">
          <div v-if="errorMsg" class="fc-error" role="alert">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            </svg>
            {{ errorMsg }}
          </div>
        </Transition>

        <!-- Login form -->
        <form @submit.prevent="submit" novalidate>
          <!-- Username -->
          <div class="fc-field">
            <label class="fc-label" for="login-username">Kullanıcı Adı</label>
            <div class="fc-input-wrap">
              <svg class="fi-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              <input
                id="login-username"
                v-model="username"
                type="text"
                class="fc-input"
                placeholder="kullanici_adi"
                autocomplete="username"
                :disabled="isLoading"
              />
            </div>
          </div>

          <!-- Password -->
          <div class="fc-field" style="margin-top: 1.125rem;">
            <label class="fc-label" for="login-password">Şifre</label>
            <div class="fc-input-wrap">
              <svg class="fi-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
              </svg>
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="fc-input fc-input--pw"
                placeholder="••••••••"
                autocomplete="current-password"
                :disabled="isLoading"
              />
              <button
                type="button"
                class="fi-pw-toggle"
                :aria-label="showPassword ? 'Şifreyi gizle' : 'Şifreyi göster'"
                @click="showPassword = !showPassword"
              >
                <!-- Eye open -->
                <svg v-if="!showPassword" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <!-- Eye crossed -->
                <svg v-else fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="fc-submit"
            :disabled="isLoading || !username.trim() || !password"
            style="margin-top: 1.75rem;"
          >
            <span v-if="!isLoading" class="fc-submit-label">
              Giriş Yap            
            </span>
            <span v-else class="fc-dots" aria-label="Giriş yapılıyor">
              <span /><span /><span />
            </span>
          </button>
        </form>

        <footer class="fc-footer">
          E-İSA Yönetim Sistemi &nbsp;·&nbsp; Yetkili erişim
        </footer>
      </div>
    </div>

  </div>
</template>
