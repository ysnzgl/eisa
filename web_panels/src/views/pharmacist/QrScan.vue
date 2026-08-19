<script setup>
import { nextTick, ref, onMounted, computed, watch } from 'vue';
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
const pendingSessions = ref([]);
const pendingLoading = ref(false);
const recentOperations = ref([]);
const operationsLoading = ref(false);
const auth = useAuthStore();
const storageKey = `eisa:open-consultation:${auth.pharmacyId || 'none'}:${auth.userId || 'none'}`;

function isFinal(value) { return [2, 3].includes(Number(value?.status)); }

async function loadPendingSessions() {
  pendingLoading.value = true;
  try {
    const { data } = await http.get('/api/analytics/sessions/', {
      params: {
        danisma_tamamlandi: 'false',
        ordering: '-olusturulma_tarihi',
        page_size: 50,
      },
    });
    const rows = Array.isArray(data) ? data : (data?.results ?? []);
    pendingSessions.value = rows
      .filter(item => !isFinal(item))
      .slice(0, 10);
  } catch {
    pendingSessions.value = [];
  } finally {
    pendingLoading.value = false;
  }
}

async function loadRecentOperations() {
  operationsLoading.value = true;
  try {
    const { data } = await http.get('/api/analytics/sessions/', {
      params: {
        danisma_tamamlandi: 'true',
        ordering: '-danisma_tamamlanma_tarihi',
        page_size: 50,
      },
    });
    const rows = Array.isArray(data) ? data : (data?.results ?? []);
    recentOperations.value = rows
      .filter(item => isFinal(item))
      .slice(0, 10);
  } catch {
    recentOperations.value = [];
  } finally {
    operationsLoading.value = false;
  }
}

const soldOperations = computed(() =>
  recentOperations.value.filter(row => row?.sold === true)
);

const notSoldOperations = computed(() =>
  recentOperations.value.filter(row => row?.sold === false)
);

watch(qrInput, (value) => {
  if (loading.value) return;

  const normalized = normalizeQr(value ?? '');
  if (normalized.length !== 9) return;

  const qrCheck = validateQr(normalized);
  if (!qrCheck.valid) return;

  qrInput.value = normalized;
  lookup();
});

onMounted(async () => {
  focusQrInput();
  window.setTimeout(() => focusQrInput(), 120);

  await Promise.all([loadPendingSessions(), loadRecentOperations()]);
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

async function completed(updated) {
  session.value = updated;
  sessionStorage.removeItem(storageKey);
  session.value = null;
  await Promise.all([loadPendingSessions(), loadRecentOperations()]);
  focusQrInput();
}

function openPendingSession(item) {
  if (!item?.qr_kodu) return;
  qrInput.value = item.qr_kodu;
  lookup();
}
</script>

<template>
  <div class="eisa-page">

    <!-- Page Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Eczacı / Hasta Sorgulama</p>
        <h1 class="eisa-page-title">QR Okutma</h1>
      </div>
    </div>

    <div class="qr-scan-page--split">
      <div class="qr-scan-left">
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

        <div class="eisa-panel qr-pending-panel">
          <div class="eisa-panel-header">
            <span class="eisa-panel-title">
              <i class="fa-solid fa-clock" style="margin-right:0.5rem;color:#F59E0B;"></i>
              Son 10 Bekleyen
            </span>
          </div>

          <div class="qr-pending-body">
            <div v-if="pendingLoading" class="qr-pending-empty">
              <i class="fa-solid fa-circle-notch fa-spin"></i>
              Bekleyenler yükleniyor…
            </div>

            <div v-else-if="!pendingSessions.length" class="qr-pending-empty">
              <i class="fa-solid fa-inbox"></i>
              Şu anda bekleyen oturum yok.
            </div>

            <div v-else class="qr-pending-list">
              <button
                v-for="item in pendingSessions"
                :key="item.id"
                type="button"
                class="qr-pending-item"
                @click="openPendingSession(item)"
              >
                <div class="qr-pending-main">
                  <span class="qr-pending-code">{{ item.qr_kodu || '—' }}</span>
                  <span class="qr-pending-meta">
                    {{ item.kiosk_detay?.ad || item.kiosk_ad || 'Kiosk' }}
                  </span>
                </div>
                <div class="qr-pending-side">
                  <span class="qr-pending-time">{{ item.olusturulma_tarihi ? new Date(item.olusturulma_tarihi).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '—' }}</span>
                  <span class="qr-pending-open">Aç</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="qr-scan-right">
        <div class="eisa-panel qr-operation-panel">
          <div class="eisa-panel-header">
            <span class="eisa-panel-title">
              <i class="fa-solid fa-chart-line" style="margin-right:0.5rem;color:#0D9488;"></i>
              Son 10 İşlem
            </span>
          </div>

          <div class="qr-operation-body">
            <div v-if="operationsLoading" class="qr-pending-empty">
              <i class="fa-solid fa-circle-notch fa-spin"></i>
              İşlemler yükleniyor…
            </div>

            <div v-else class="qr-operation-columns">
              <div class="qr-operation-column">
                <div class="qr-operation-header qr-operation-header--success">
                  <i class="fa-solid fa-circle-check"></i>
                  <span>Satış Yapıldı</span>
                </div>
                <div v-if="!soldOperations.length" class="qr-op-empty">Kayıt yok</div>
                <div v-else class="qr-operation-list">
                  <button v-for="item in soldOperations" :key="`sold-${item.id}`" type="button" class="qr-operation-item qr-operation-item--success" @click="openPendingSession(item)">
                    <span class="qr-op-code">{{ item.qr_kodu || '—' }}</span>
                    <span class="qr-op-meta">{{ item.kiosk_detay?.ad || item.kiosk_ad || 'Kiosk' }}</span>
                    <span class="qr-op-time">{{ item.danisma_tamamlanma_tarihi ? new Date(item.danisma_tamamlanma_tarihi).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '—' }}</span>
                  </button>
                </div>
              </div>

              <div class="qr-operation-column">
                <div class="qr-operation-header qr-operation-header--danger">
                  <i class="fa-solid fa-circle-xmark"></i>
                  <span>Satış Yapılmadı</span>
                </div>
                <div v-if="!notSoldOperations.length" class="qr-op-empty">Kayıt yok</div>
                <div v-else class="qr-operation-list">
                  <button v-for="item in notSoldOperations" :key="`ns-${item.id}`" type="button" class="qr-operation-item qr-operation-item--danger" @click="openPendingSession(item)">
                    <span class="qr-op-code">{{ item.qr_kodu || '—' }}</span>
                    <span class="qr-op-meta">{{ item.kiosk_detay?.ad || item.kiosk_ad || 'Kiosk' }}</span>
                    <span class="qr-op-time">{{ item.danisma_tamamlanma_tarihi ? new Date(item.danisma_tamamlanma_tarihi).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '—' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
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

<style scoped>
.qr-scan-page--split {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}

.qr-scan-left,
.qr-scan-right {
  min-width: 0;
}

.qr-pending-panel {
  margin-bottom: 0;
}

.qr-pending-body,
.qr-operation-body {
  padding: 1rem 1.25rem 1.1rem;
}

.qr-pending-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 4rem;
  color: #6B7280;
  font-size: 0.9rem;
}

.qr-pending-list,
.qr-operation-list {
  display: grid;
  gap: 0.6rem;
}

.qr-pending-item,
.qr-operation-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid #E5E7EB;
  border-radius: 0.8rem;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.qr-pending-item:hover,
.qr-operation-item:hover {
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.qr-pending-main,
.qr-pending-side,
.qr-operation-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.qr-pending-code,
.qr-op-code {
  font-family: 'DM Mono', monospace;
  font-size: 0.96rem;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.05em;
}

.qr-pending-meta,
.qr-pending-time,
.qr-op-meta,
.qr-op-time {
  font-size: 0.74rem;
  color: #6B7280;
}

.qr-pending-open {
  align-self: flex-end;
  font-size: 0.72rem;
  font-weight: 700;
  color: #0D9488;
}

.qr-operation-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}

.qr-operation-column {
  min-width: 0;
}

.qr-operation-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  margin-bottom: 0.65rem;
  border-radius: 0.7rem;
  font-size: 0.8rem;
  font-weight: 700;
}

.qr-operation-header--success {
  background: #ECFDF5;
  color: #065F46;
  border: 1px solid #A7F3D0;
}

.qr-operation-header--danger {
  background: #FEF2F2;
  color: #991B1B;
  border: 1px solid #FECACA;
}

.qr-op-empty {
  padding: 0.8rem;
  border: 1px dashed #D1D5DB;
  border-radius: 0.7rem;
  background: #F9FAFB;
  color: #6B7280;
  text-align: center;
  font-size: 0.75rem;
}

.qr-operation-item--success {
  border-color: #A7F3D0;
  background: #F0FDF4;
}

.qr-operation-item--danger {
  border-color: #FECACA;
  background: #FEF2F2;
}

.qr-operation-item--success .qr-op-code,
.qr-operation-item--success .qr-op-meta,
.qr-operation-item--success .qr-op-time {
  color: #065F46;
}

.qr-operation-item--danger .qr-op-code,
.qr-operation-item--danger .qr-op-meta,
.qr-operation-item--danger .qr-op-time {
  color: #991B1B;
}

@media (max-width: 980px) {
  .qr-scan-page--split {
    grid-template-columns: 1fr;
  }
}
</style>
