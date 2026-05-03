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
          Türkiye'nin dijital ilaç yönetim platformu
        </p>

        <ul class="brand-features">
          <li>
            <span class="feat-dot" />
            Gerçek zamanlı kampanya yönetimi
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
          <span>· 2026</span>
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
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/>
              </svg>
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

<style scoped>
/* ═══════════════════════════════════════════════
   Root layout
═══════════════════════════════════════════════ */
.lr-root {
  display: flex;
  min-height: 100svh;
  font-family: 'Figtree', system-ui, sans-serif;
}

/* ═══════════════════════════════════════════════
   Brand panel — left
═══════════════════════════════════════════════ */
.lr-brand {
  position: relative;
  flex: 0 0 46%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(150deg, #060E1F 0%, #0B1D3A 38%, #122B56 68%, #1A3C78 100%);
}

/* ── Ambient orbs ── */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  will-change: transform;
}
.orb-a {
  width: 520px; height: 520px;
  top: -160px; right: -120px;
  background: radial-gradient(circle, #2563EB 0%, #1e3a8a 100%);
  opacity: 0.22;
  animation: floatOrb 9s ease-in-out infinite;
}
.orb-b {
  width: 380px; height: 380px;
  bottom: -100px; left: -100px;
  background: radial-gradient(circle, #06B6D4 0%, #0e7490 100%);
  opacity: 0.18;
  animation: floatOrb 13s ease-in-out infinite reverse;
}
.orb-c {
  width: 240px; height: 240px;
  top: 50%; left: 40%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, #3B82F6 0%, transparent 70%);
  opacity: 0.10;
  animation: floatOrb 7s ease-in-out infinite 2s;
}
@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0); }
  50%       { transform: translate(18px, -18px); }
}

/* ── Grid overlay ── */
.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(147, 197, 253, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(147, 197, 253, 0.04) 1px, transparent 1px);
  background-size: 52px 52px;
  pointer-events: none;
}

/* ── Floating crosses ── */
.cross {
  position: absolute;
  pointer-events: none;
  font-weight: 200;
  line-height: 1;
  color: rgba(147, 210, 255, 0.15);
  user-select: none;
}
.cross-1 { font-size: 2.75rem; top: 13%;  left: 9%;   animation: floatY 7s ease-in-out infinite; }
.cross-2 { font-size: 4.5rem;  top: 58%;  right: 8%;  animation: floatY 10s ease-in-out infinite 2.5s; opacity: 0.08; }
.cross-3 { font-size: 1.5rem;  bottom: 18%; left: 24%; animation: floatY 8s ease-in-out infinite 1s; }
.cross-4 { font-size: 1rem;    top: 35%;  left: 65%;  animation: floatY 6s ease-in-out infinite 0.5s; opacity: 0.1; }
@keyframes floatY {
  0%, 100% { transform: translateY(0px); }
  50%       { transform: translateY(-14px); }
}

/* ── Brand body ── */
.brand-body {
  position: relative;
  z-index: 10;
  padding: 3.5rem 3rem;
  max-width: 440px;
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.75s ease 0.1s, transform 0.75s cubic-bezier(0.22,1,0.36,1) 0.1s;
}
.brand-body.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.brand-wordmark {
  display: inline-flex;
  align-items: baseline;
  gap: 0;
  margin-bottom: 2.75rem;
  font-family: 'Lexend Deca', sans-serif;
  font-weight: 700;
  font-size: 1.375rem;
  letter-spacing: -0.01em;
}
.wm-e    { color: #7DD3FC; font-size: 1.625rem; }
.wm-dash { color: rgba(255,255,255,0.5); }
.wm-isa  { color: #ffffff; }

.brand-headline {
  font-family: 'Lexend Deca', sans-serif;
  font-size: clamp(2.25rem, 3.5vw, 3.25rem);
  font-weight: 800;
  line-height: 1.12;
  color: #ffffff;
  letter-spacing: -0.035em;
  margin: 0 0 1rem 0;
}
.brand-headline em {
  font-style: italic;
  font-weight: 300;
  color: #7DD3FC;
}

.brand-tagline {
  font-size: 0.9rem;
  font-weight: 400;
  letter-spacing: 0.025em;
  color: rgba(186, 230, 253, 0.7);
  margin: 0 0 2.5rem 0;
}

/* Feature list */
.brand-features {
  list-style: none;
  margin: 0 0 3rem 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}
.brand-features li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: rgba(186, 230, 253, 0.8);
}
.feat-dot {
  flex-shrink: 0;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #22D3EE;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.6);
}

/* Version */
.brand-version {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.5);
  letter-spacing: 0.06em;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  padding-top: 1.5rem;
}
.version-badge {
  background: rgba(37, 99, 235, 0.25);
  color: #93C5FD;
  border: 1px solid rgba(37, 99, 235, 0.3);
  border-radius: 6px;
  padding: 1px 8px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* ═══════════════════════════════════════════════
   Form panel — right
═══════════════════════════════════════════════ */
.lr-form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F8FAFC;
  padding: 2rem;
}

.lr-form-card {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  border-radius: 20px;
  padding: 2.75rem 2.5rem 2rem;
  box-shadow: 0 4px 24px -2px rgba(11,29,58,0.10), 0 1px 4px rgba(11,29,58,0.06);
  opacity: 0;
  transform: translateY(20px) scale(0.985);
  transition: opacity 0.6s ease 0.3s, transform 0.6s cubic-bezier(0.22,1,0.36,1) 0.3s;
}
.lr-form-card.is-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ── Card header ── */
.fc-header {
  margin-bottom: 2rem;
}
.fc-logo {
  display: inline-flex;
  align-items: baseline;
  margin-bottom: 1.625rem;
  font-family: 'Lexend Deca', sans-serif;
  font-weight: 700;
}
.fcl-e   { color: #2563EB; font-size: 1.5rem; }
.fcl-dash{ color: #94A3B8; font-size: 1.25rem; }
.fcl-isa { color: #0B1D3A; font-size: 1.25rem; }

.fc-title {
  font-family: 'Lexend Deca', sans-serif;
  font-size: 1.65rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.03em;
  line-height: 1.2;
  margin: 0 0 0.4rem 0;
}
.fc-subtitle {
  font-size: 0.875rem;
  color: #64748B;
  margin: 0;
}

/* ── Error banner ── */
.fc-error {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
  background: #FEF2F2;
  border: 1.5px solid #FECACA;
  color: #DC2626;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font-size: 0.8375rem;
  margin-bottom: 1.25rem;
  line-height: 1.45;
}
.fc-error svg { flex-shrink: 0; margin-top: 1px; }

/* Shake transition */
.shake-enter-active { animation: shake 0.4s ease; }
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%      { transform: translateX(-6px); }
  40%      { transform: translateX(6px); }
  60%      { transform: translateX(-4px); }
  80%      { transform: translateX(4px); }
}

/* ── Field ── */
.fc-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.fc-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #374151;
  letter-spacing: 0.015em;
}
.fc-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.fi-icon {
  position: absolute;
  left: 0.9rem;
  width: 18px; height: 18px;
  color: #94A3B8;
  pointer-events: none;
  flex-shrink: 0;
}
.fc-input {
  width: 100%;
  padding: 0.78rem 1rem 0.78rem 2.75rem;
  border: 1.5px solid #E2E8F0;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-family: 'Figtree', system-ui, sans-serif;
  color: #0F172A;
  background: #F8FAFC;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.fc-input::placeholder { color: #CBD5E1; }
.fc-input:focus {
  border-color: #2563EB;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
.fc-input:disabled { opacity: 0.6; cursor: not-allowed; }

/* Password right padding for toggle button */
.fc-input--pw { padding-right: 2.75rem; }

.fi-pw-toggle {
  position: absolute;
  right: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  background: none;
  border: none;
  cursor: pointer;
  color: #94A3B8;
  padding: 0;
  transition: color 0.15s ease;
}
.fi-pw-toggle:hover { color: #475569; }
.fi-pw-toggle svg { width: 18px; height: 18px; }

/* ── Submit button ── */
.fc-submit {
  width: 100%;
  padding: 0.9rem;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 700;
  font-family: 'Figtree', system-ui, sans-serif;
  cursor: pointer;
  letter-spacing: 0.01em;
  position: relative;
  overflow: hidden;
  transition: transform 0.15s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  box-shadow: 0 4px 14px rgba(37,99,235,0.35);
}
.fc-submit::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, transparent 60%);
  pointer-events: none;
}
.fc-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 7px 22px rgba(37,99,235,0.45);
}
.fc-submit:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(37,99,235,0.3);
}
.fc-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.fc-submit-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
.fc-submit-label svg {
  width: 16px; height: 16px;
  transition: transform 0.2s ease;
}
.fc-submit:hover:not(:disabled) .fc-submit-label svg {
  transform: translateX(3px);
}

/* Loading dots */
.fc-dots {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.fc-dots span {
  display: block;
  width: 6px; height: 6px;
  background: white;
  border-radius: 50%;
  animation: dotBounce 1.2s ease-in-out infinite;
}
.fc-dots span:nth-child(2) { animation-delay: 0.18s; }
.fc-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.65); opacity: 0.5; }
  40%           { transform: scale(1);    opacity: 1;   }
}

/* ── Card footer ── */
.fc-footer {
  text-align: center;
  margin-top: 1.625rem;
  font-size: 0.72rem;
  color: #94A3B8;
  letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════════
   Responsive
═══════════════════════════════════════════════ */
@media (max-width: 860px) {
  .lr-root { flex-direction: column; }

  .lr-brand {
    flex: 0 0 auto;
    min-height: 240px;
    padding: 2.5rem 2rem;
  }
  .brand-headline { font-size: 2.25rem; }
  .brand-features { display: none; }
  .brand-version  { display: none; }

  .lr-form-panel  { padding: 1.5rem 1rem; }
  .lr-form-card   { padding: 2rem 1.5rem 1.5rem; }
}
</style>

