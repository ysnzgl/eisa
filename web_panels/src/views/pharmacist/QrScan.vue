<script setup>
import { nextTick, ref, onMounted } from 'vue';
import { http } from '../../services/api';
import { completeSession } from '../../services/analytics';

const QR_PATTERN = /^[0-9A-Z]{8}$/;

const qrInput = ref('');
const qrInputRef = ref(null);
const session = ref(null);
const loading = ref(false);
const lookupError = ref('');
const completionNote = ref('');
const completionLoading = ref(false);
const completionError = ref('');

onMounted(() => {
  focusQrInput();
});

function focusQrInput() {
  nextTick(() => {
    qrInputRef.value?.focus();
    qrInputRef.value?.select?.();
  });
}

async function lookup() {
  if (loading.value) return;

  const raw = qrInput.value.trim();
  session.value = null;
  lookupError.value = '';
  completionError.value = '';

  if (!raw) {
    lookupError.value = 'QR kodu giriniz.';
    focusQrInput();
    return;
  }

  if (!QR_PATTERN.test(raw)) {
    lookupError.value = 'Geçersiz QR kodu.';
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
    qrInput.value = '';
  } catch (err) {
    const status = err?.response?.status;
    if (status === 404) {
      lookupError.value = 'QR koduna ait oturum bulunamadı.';
    } else if (status === 403) {
      lookupError.value = 'Bu QR kodu eczanenize ait değildir.';
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

async function handleCompleteSession(saleResult) {
  if (!session.value?.id || completionLoading.value) return;

  completionLoading.value = true;
  completionError.value = '';
  try {
    const res = await completeSession(session.value.id, completionNote.value, saleResult);
    session.value = { ...session.value, ...res.data };
  } catch (err) {
    completionError.value =
      err?.response?.data?.detail || 'Danışma tamamlanırken bir hata oluştu.';
  } finally {
    completionLoading.value = false;
    focusQrInput();
  }
}

function reset() {
  qrInput.value = '';
  session.value = null;
  lookupError.value = '';
  completionNote.value = '';
  completionLoading.value = false;
  completionError.value = '';
  focusQrInput();
}

const GENDER_LABEL = { F: 'Kadın', M: 'Erkek', O: 'Diğer', male: 'Erkek', female: 'Kadın' };

function formatDT(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR');
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
              placeholder="8 karakterlik QR kod (ör. A1B2C3D4)"
              class="eisa-field"
              style="flex:1;font-family:'DM Mono',monospace;letter-spacing:0.05em;"
              :disabled="loading"
              autocomplete="off"
            />
            <button
              id="qr-lookup-btn"
              class="eisa-btn eisa-btn-cta"
              :disabled="loading || !qrInput.trim()"
              @click="lookup"
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
      <div v-if="session" class="qr-result-card">

        <div class="qr-result-header">
          <div>
            <h2 style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:0.2rem;">Hasta Oturumu</h2>
            <p style="font-size:0.72rem;color:#9CA3AF;">{{ formatDT(session.olusturulma_tarihi || session.created_at) }}</p>
          </div>
          <div style="text-align:right;">
            <p style="font-size:0.7rem;color:#9CA3AF;margin-bottom:0.2rem;">QR Kodu</p>
            <p style="font-family:'DM Mono',monospace;font-weight:700;font-size:1.25rem;letter-spacing:0.1em;color:#111827;">{{ session.qr_kodu || session.qr_code }}</p>
          </div>
        </div>

        <!-- Sensitive Alert -->
        <div v-if="session.hassas_akis || session.is_sensitive_flow" class="qr-sensitive-bar">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span>Hassas Konu — Hasta bu konuyu kalabalık içinde söylemek istemedi.</span>
        </div>

        <!-- Details Grid -->
        <div class="qr-result-section qr-grid-2">
          <div>
            <p class="qr-detail-label">Yaş Aralığı</p>
            <p class="qr-detail-value">{{ session.yas_araligi_detay?.ad || session.age_range || session.yas_araligi_kod || '—' }}</p>
          </div>
          <div>
            <p class="qr-detail-label">Cinsiyet</p>
            <p class="qr-detail-value">{{ session.cinsiyet_detay?.ad || (GENDER_LABEL[session.gender || session.cinsiyet_kod] ?? (session.gender || session.cinsiyet_kod)) }}</p>
          </div>
          <div>
            <p class="qr-detail-label">Oturum Tipi</p>
            <p class="qr-detail-value">
              {{ session.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Ozel Danismanlik' : 'Sikayet' }}
            </p>
          </div>
          <div style="grid-column:1/span 2;">
            <p class="qr-detail-label">Kategori</p>
            <p class="qr-detail-value">
              <template v-if="session.oturum_tipi === 'OZEL_DANISMANLIK'">
                {{ session.danisma_kategorisi_detay?.ad
                   || session.danisma_kategorisi_adi
                   || '—' }}
              </template>
              <template v-else>
                {{ session.kategori_detay?.ad
                   ?? session.kategori_adi
                   ?? session.category?.name
                   ?? '—' }}
              </template>
            </p>
          </div>
          <div>
            <p class="qr-detail-label">Kiosk</p>
            <p class="qr-detail-value">{{ session.kiosk_detay?.ad || session.kiosk_mac || '—' }}</p>
          </div>
          <div>
            <p class="qr-detail-label">Eczane</p>
            <p class="qr-detail-value">{{ session.eczane?.ad || session.eczane_adi || '—' }}</p>
          </div>
        </div>

        <div class="qr-result-section" v-if="session.cevap_detaylari?.length">
          <p class="qr-detail-label" style="margin-bottom:0.5rem;">Soru ve Cevaplar</p>
          <ol style="margin:0;padding-left:1rem;display:grid;gap:0.5rem;">
            <li v-for="item in session.cevap_detaylari" :key="`${item.soru_id}-${item.cevap_id}-${item.sira}`" style="font-size:0.85rem;color:#111827;">
              <strong>{{ item.soru_metni }}</strong>
              <div style="color:#4B5563;">Yanıt: {{ item.cevap_metni }}</div>
            </li>
          </ol>
        </div>

        <!-- Suggested Ingredients -->
        <div
          v-if="session.onerilen_etken_madde_detaylari?.length || session.onerilen_etken_maddeler?.length || session.suggested_ingredients?.length"
          class="qr-result-section"
        >
          <p class="qr-detail-label" style="margin-bottom:0.5rem;">Önerilen Etken Maddeler</p>
          <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">
            <span
              v-for="ing in (session.onerilen_etken_madde_detaylari?.length
                ? session.onerilen_etken_madde_detaylari
                : (session.onerilen_etken_maddeler || session.suggested_ingredients || []).map((v) => ({ id: v?.id || v, ad: v?.ad || v })))"
              :key="ing.id || ing.ad"
              class="eisa-pill eisa-pill-info"
            >{{ ing.ad }}</span>
          </div>
        </div>

        <!-- Completion Info (if completed) -->
        <div v-if="session.danisma_tamamlandi" class="qr-result-section qr-completion-info">
          <div class="qr-completion-header">
            <i class="fa-solid fa-check-circle"></i>
            <span>Danışma Tamamlandı</span>
          </div>
          <p v-if="session.danisma_notu" class="qr-completion-note">
            <strong>Eczacı Notu:</strong> {{ session.danisma_notu }}
          </p>
          <p class="qr-completion-meta">
            {{ session.danisma_tamamlayan_eczaci_adi }} tarafından
            {{ formatDT(session.danisma_tamamlanma_tarihi) }} tarihinde tamamlandı.
          </p>
          <p class="qr-completion-meta" style="padding-left:1.75rem; margin-top:0.4rem;">
            Satış sonucu: {{ session.satis_sonucu || 'Mevcut şemada kayıtlı değil' }}
          </p>
        </div>

        <!-- Completion Action (if not completed) -->
        <div v-if="!session.danisma_tamamlandi" class="qr-result-section qr-completion-action">
          <p class="qr-detail-label" style="margin-bottom:0.5rem;">Danışma Notu (Opsiyonel)</p>
          <textarea
            v-model="completionNote"
            rows="2"
            placeholder="Hastaya verilen tavsiye veya onerilen etken maddeler..."
            class="eisa-field"
            style="margin-bottom:0.75rem;"
          ></textarea>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
            <button
              class="eisa-btn eisa-btn-success"
              :disabled="completionLoading"
              @click="handleCompleteSession('sold')"
            >
              <i v-if="completionLoading" class="fa-solid fa-circle-notch fa-spin"></i>
              <i v-else class="fa-solid fa-check"></i>
              Satış Yaptım
            </button>
            <button
              class="eisa-btn eisa-btn-ghost"
              :disabled="completionLoading"
              @click="handleCompleteSession('not_sold')"
            >
              <i v-if="completionLoading" class="fa-solid fa-circle-notch fa-spin"></i>
              <i v-else class="fa-solid fa-xmark"></i>
              Satış Yapmadım
            </button>
          </div>
          <p v-if="completionError" class="eisa-error-text" style="margin-top:0.5rem;text-align:center;">
            {{ completionError }}
          </p>
        </div>

        <!-- Footer -->
        <div class="qr-result-section" style="display:flex;align-items:center;justify-content:space-between;background:#F9FAFB;border-radius:0 0 0.875rem 0.875rem;margin:-0;padding:0.75rem 1.25rem;">
          <span style="font-size:0.75rem;color:#6B7280;">
            Kiosk MAC: <span style="font-weight:600;color:#374151;">{{ session.kiosk_detay?.mac_adresi ?? session.kiosk?.mac_address ?? session.kiosk_mac ?? '—' }}</span>
          </span>
          <button class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="reset">Yeni Sorgulama</button>
        </div>
      </div>

    </div><!-- /qr-scan-page -->
  </div>
</template>

<style scoped>
.qr-completion-info {
  background: #F0FDF4;
  border: 1px solid #A7F3D0;
  border-radius: 0.75rem;
  padding: 1rem 1.25rem;
}
.qr-completion-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  color: #065F46;
  margin-bottom: 0.5rem;
}
.qr-completion-header i {
  color: #10B981;
}
.qr-completion-note {
  font-size: 0.875rem;
  color: #047857;
  margin-bottom: 0.5rem;
  padding-left: 1.75rem;
}
.qr-completion-meta {
  font-size: 0.75rem;
  color: #065F46;
  padding-left: 1.75rem;
}
.qr-completion-action {
  background: #F9FAFB;
  padding: 1.25rem;
  border-top: 1px solid #E5E7EB;
}
</style>
