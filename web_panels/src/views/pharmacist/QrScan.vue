<script setup>
import { nextTick, ref, onMounted } from 'vue';
import { http } from '../../services/api';
import SessionDetailModal from '../../components/SessionDetailModal.vue';
import { useAuthStore } from '../../stores/auth';
import { toast } from 'vue-sonner';

// Legacy 8-char [0-9A-Z] veya yeni 9-char Crockford Base32
const QR_LEGACY_RE = /^[0-9A-Z]{8}$/;
const CROCKFORD_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const CROCKFORD_QR_RE = /^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{9}$/;

function crockfordChecksumValid(code) {
  if (code.length !== 9) return false;
  try {
    let total = 0;
    for (let i = 0; i < 8; i++) {
      const idx = CROCKFORD_ALPHABET.indexOf(code[i]);
      if (idx < 0) return false;
      total += idx * (i + 1);
    }
    return code[8] === CROCKFORD_ALPHABET[total % 32];
  } catch {
    return false;
  }
}

function normalizeQr(raw) {
  return raw.trim().toUpperCase();
}

function validateQr(code) {
  if (QR_LEGACY_RE.test(code)) return { valid: true };
  if (CROCKFORD_QR_RE.test(code)) {
    if (!crockfordChecksumValid(code)) return { valid: false, reason: 'checksum' };
    return { valid: true };
  }
  return { valid: false, reason: 'format' };
}

const qrInput    = ref('');
const qrInputRef = ref(null);
const session    = ref(null);
const loading    = ref(false);
const lookupError = ref('');
const auth = useAuthStore();
const storageKey = `eisa:open-consultation:${auth.pharmacyId || 'none'}:${auth.userId || 'none'}`;

function isFinal(value) { return [2, 3].includes(Number(value?.status)); }

onMounted(async () => {
  focusQrInput();
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    if (saved?.qr) {
      qrInput.value = saved.qr;
      await lookup(true);
    }
  } catch { sessionStorage.removeItem(storageKey); }
});

function focusQrInput() {
  nextTick(() => {
    qrInputRef.value?.focus();
    qrInputRef.value?.select?.();
  });
}

async function lookup(restoring = false) {
  if (loading.value) return;

  if (session.value && !isFinal(session.value)) {
    const message = 'Mevcut danışmanlığı sonuçlandırmadan yeni bir QR kod sorgulayamazsınız.';
    lookupError.value = message;
    toast.warning(message);
    return;
  }

  const raw = normalizeQr(qrInput.value);
  session.value = null;
  lookupError.value = '';

  if (!raw) {
    lookupError.value = 'QR kodu giriniz.';
    focusQrInput();
    return;
  }

  const qrCheck = validateQr(raw);
  if (!qrCheck.valid) {
    lookupError.value = qrCheck.reason === 'checksum'
      ? 'Geçersiz QR kodu (hatalı checksum).'
      : 'Geçersiz QR kodu.';
    focusQrInput();
    return;
  }

  loading.value = true;
  try {
    const res = await http.get('/api/analytics/sessions/', { params: { qr_kodu: raw } });
    const payload = Array.isArray(res.data)
      ? res.data[0]
      : Array.isArray(res.data?.results)
        ? res.data.results[0]
        : res.data;

    if (!payload) {
      lookupError.value = 'QR koduna ait oturum bulunamadı.';
      return;
    }
    session.value = payload;
    if (isFinal(payload)) sessionStorage.removeItem(storageKey);
    else sessionStorage.setItem(storageKey, JSON.stringify({ id: payload.id, qr: payload.qr_kodu || raw }));
    qrInput.value = '';
  } catch (err) {
    if (restoring && [403, 404].includes(err?.response?.status)) sessionStorage.removeItem(storageKey);
    const status = err?.response?.status;
    if (status === 404 || status === 403) {
      lookupError.value = 'QR koduna ait oturum bulunamadı.';
    } else if (status === 400) {
      lookupError.value = err?.response?.data?.detail || 'Geçersiz QR kodu.';
    } else {
      lookupError.value = 'Sunucuya ulaşılamadı. Lütfen tekrar deneyin.';
    }
  } finally {
    loading.value = false;
    focusQrInput();
  }
}

function onEnter() {
  if (!loading.value) lookup();
}

function completed(updated) {
  session.value = updated;
  sessionStorage.removeItem(storageKey);
  session.value = null;
  focusQrInput();
}
</script>

<template>
  <div class="eisa-page pharm-page">

    <!-- Page Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Eczacı / Hasta Sorgulama</p>
        <h1 class="eisa-page-title">QR Okutma</h1>
      </div>
    </div>

    <div class="qr-scan-page">

      <!-- Input Panel -->
      <div class="eisa-panel" style="margin-bottom:1.5rem;">
        <div class="eisa-panel-header">
          <span class="eisa-panel-title">
            <i class="fa-solid fa-qrcode" style="margin-right:0.5rem;color:#0D9488;"></i>
            Hasta QR Kodu
          </span>
        </div>
        <div class="eisa-modal-body" style="padding:1.25rem 1.5rem;">
          <div style="display:flex;gap:0.75rem;margin-bottom:1rem;">
            <input
              ref="qrInputRef"
              id="qr-input"
              name="qr_code"
              v-model="qrInput"
              @keydown.enter.prevent="onEnter"
              placeholder="QR kodu (8 veya 9 karakter, ör. A1B2C3D4 veya 1K7M9QX5C)"
              class="eisa-field"
              style="flex:1;font-family:'DM Mono',monospace;letter-spacing:0.05em;"
              :disabled="loading"
              autocomplete="off"
            />
            <button
              id="qr-lookup-btn"
              class="eisa-btn eisa-btn-cta"
              :disabled="loading || !qrInput.trim()"
              @click="lookup()"
            >
              <i v-if="loading" class="fa-solid fa-circle-notch fa-spin"></i>
              <i v-else class="fa-solid fa-magnifying-glass"></i>
              {{ loading ? '…' : 'Sorgula' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="lookupError" class="eisa-error-banner" style="margin-bottom:1.5rem;">
        <i class="fa-solid fa-triangle-exclamation"></i>
        {{ lookupError }}
      </div>

      <!-- Session Result -->
      <SessionDetailModal
        :session="session"
        mandatory
        @completed="completed"
        @close="session = null"
      />

    </div><!-- /qr-scan-page -->
  </div>
</template>
