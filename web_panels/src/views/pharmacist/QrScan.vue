<script setup>
/**
 * QR Scan — Eczacının kiosk QR kodunu okutarak hastanın anket oturumunu görmesi.
 *
 * AKIŞ:
 *  1. QR string'i okunur (kamera veya manuel).
 *  2. Önce LOKAL olarak şifre çözülmeye çalışılır (offline destek).
 *     - Başarılıysa: payload.p (pharmacy_id) eczacının pharmacyId'siyle
 *       eşleşmeli. Eşleşmiyorsa "Bu barkod size ait değil" uyarısı.
 *     - Başarılı + sahip ise: ekranda görüntüle.
 *  3. Online ise opsiyonel olarak backend'den session detayı çekilerek
 *     görünüm zenginleştirilir.
 *
 * Şifreleme: AES-256-GCM, paylaşılan VITE_QR_SECRET (kiosk ile aynı).
 */
import { ref, onMounted, onUnmounted } from 'vue';
import { http } from '../../services/api';
import { useAuthStore } from '../../stores/auth';
import { decodeQrCode, QR_BITPACK_RE } from '../../services/qrBitpack';

const auth = useAuthStore();

const qrInput = ref('');
const session = ref(null);
const loading = ref(false);
const notFound = ref(false);
const apiError = ref('');
const ownershipError = ref('');
const offlineMode = ref(false);

// Kamera desteği
const cameraSupported = ref(false);
const cameraActive = ref(false);
const videoRef = ref(null);
let barcodeDetector = null;
let scanInterval = null;
let stream = null;

onMounted(() => {
  if ('BarcodeDetector' in window) {
    cameraSupported.value = true;
    barcodeDetector = new BarcodeDetector({ formats: ['qr_code'] });
  }
});

onUnmounted(() => stopCamera());

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    cameraActive.value = true;
    setTimeout(() => {
      if (videoRef.value) {
        videoRef.value.srcObject = stream;
        videoRef.value.play();
      }
      scanInterval = setInterval(scanFrame, 500);
    }, 100);
  } catch {
    apiError.value = 'Kameraya erişilemedi. Lütfen tarayıcı izinlerini kontrol edin.';
  }
}

function stopCamera() {
  clearInterval(scanInterval);
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  cameraActive.value = false;
}

async function scanFrame() {
  if (!videoRef.value || !barcodeDetector) return;
  try {
    const barcodes = await barcodeDetector.detect(videoRef.value);
    if (barcodes.length > 0) {
      qrInput.value = barcodes[0].rawValue;
      stopCamera();
      await lookup();
    }
  } catch {
    /* kare okunamadı */
  }
}

function payloadToSession(p) {
  // Bitpack yalnızca 5 integer alan taşır; detaylar online zenginleştirmeyle gelir.
  return {
    pharmacy_id: p.pharmacyId,
    kiosk_id:    p.kioskId,
    category_id: p.categoryId,
    qa_combo:    p.qaCombo,
    product_id:  p.productId,
    _source: 'qr',
  };
}

async function lookup() {
  const raw = qrInput.value.trim();
  if (!raw) return;

  loading.value = true;
  notFound.value = false;
  session.value = null;
  apiError.value = '';
  ownershipError.value = '';
  offlineMode.value = false;

  let decoded = null;
  if (QR_BITPACK_RE.test(raw)) {
    try {
      decoded = decodeQrCode(raw);
    } catch {
      apiError.value =
        'QR çözülemedi. Bu kod e-İSA sisteminden çıkmamış olabilir veya bozulmuş.';
      loading.value = false;
      return;
    }

    // Sahiplik kontrolü
    if (auth.pharmacyId != null && decoded.pharmacyId != null && decoded.pharmacyId !== auth.pharmacyId) {
      ownershipError.value = 'Bu barkod size ait değil.';
      loading.value = false;
      return;
    }

    session.value = payloadToSession(decoded);
  }

  // Online zenginleştirme
  const lookupCode = raw.toUpperCase();
  try {
    const res = await http.get('/api/analytics/sessions/', {
      params: { qr_code: lookupCode },
    });
    const results = Array.isArray(res.data) ? res.data : res.data.results ?? [];
    if (results.length > 0) {
      session.value = { ...(session.value ?? {}), ...results[0], _source: 'server' };
    } else if (!session.value) {
      notFound.value = true;
    }
  } catch (err) {
    if (err?.response?.status === 403) {
      // Backend de sahibi olmadığını söyledi.
      ownershipError.value = 'Bu barkod size ait değil.';
      session.value = null;
    } else if (!session.value) {
      apiError.value = 'Sunucuya ulaşılamadı.';
    } else {
      offlineMode.value = true;
    }
  } finally {
    loading.value = false;
  }
}

function reset() {
  qrInput.value = '';
  session.value = null;
  notFound.value = false;
  apiError.value = '';
  ownershipError.value = '';
  offlineMode.value = false;
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
              id="qr-input"
              name="qr_code"
              v-model="qrInput"
              @keyup.enter="lookup"
              placeholder="8 karakterlik QR kod (ör. A1B2C3D4)"
              class="eisa-field"
              style="flex:1;font-family:'DM Mono',monospace;letter-spacing:0.05em;"
              :disabled="loading"
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

          <div v-if="cameraSupported" style="display:flex;align-items:center;gap:0.75rem;">
            <button
              id="camera-toggle-btn"
              class="eisa-btn"
              :class="cameraActive ? 'eisa-btn-danger' : 'eisa-btn-ghost'"
              @click="cameraActive ? stopCamera() : startCamera()"
            >
              <i class="fa-solid fa-camera"></i>
              {{ cameraActive ? 'Kamerayı Durdur' : 'Kamera ile Tara' }}
            </button>
            <span v-if="cameraActive" style="font-size:0.75rem;color:#9CA3AF;animation:pulse 1s infinite;">QR bekleniyor…</span>
          </div>

          <div v-if="cameraActive" class="qr-video-wrap" style="margin-top:1rem;">
            <video ref="videoRef" class="qr-video" muted playsinline />
          </div>
        </div>
      </div>

      <!-- Ownership Error -->
      <div v-if="ownershipError" class="eisa-error-banner" style="margin-bottom:1.5rem;text-align:center;flex-direction:column;gap:0.5rem;padding:1.5rem;">
        <i class="fa-solid fa-ban" style="font-size:1.5rem;"></i>
        <p style="font-weight:700;">{{ ownershipError }}</p>
        <p style="font-size:0.8rem;">Bu QR kod başka bir eczanenin kioskundan üretilmiş.</p>
        <button class="eisa-btn eisa-btn-ghost" style="margin-top:0.5rem;" @click="reset">Yeniden Dene</button>
      </div>

      <!-- API Error -->
      <div v-else-if="apiError" class="eisa-error-banner" style="margin-bottom:1.5rem;">
        <i class="fa-solid fa-triangle-exclamation"></i>
        {{ apiError }}
      </div>

      <!-- Offline Warning -->
      <div v-if="offlineMode" class="eisa-error-banner" style="background:rgba(245,158,11,0.06);border-color:rgba(245,158,11,0.3);color:#92400E;margin-bottom:1.5rem;">
        <i class="fa-solid fa-wifi-slash"></i>
        Sunucuya ulaşılamadı; veriler QR'dan okundu (offline mod).
      </div>

      <!-- Not Found -->
      <div v-if="notFound" style="text-align:center;padding:2rem;color:#6B7280;">
        <i class="fa-solid fa-circle-question" style="font-size:2rem;margin-bottom:0.75rem;display:block;"></i>
        <p style="font-weight:600;margin-bottom:0.3rem;">Oturum bulunamadı</p>
        <p style="font-size:0.8rem;margin-bottom:0.75rem;">
          <code style="font-family:'DM Mono',monospace;font-weight:700;">{{ qrInput.trim() }}</code> koduna ait kayıt yok.
        </p>
        <button class="eisa-btn eisa-btn-ghost" @click="reset">Yeniden Dene</button>
      </div>

      <!-- Session Result -->
      <div v-if="session && !ownershipError" class="qr-result-card">

        <div class="qr-result-header">
          <div>
            <h2 style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:0.2rem;">Hasta Oturumu</h2>
            <p style="font-size:0.72rem;color:#9CA3AF;">{{ formatDT(session.created_at) }}</p>
          </div>
          <div style="text-align:right;">
            <p style="font-size:0.7rem;color:#9CA3AF;margin-bottom:0.2rem;">QR Kodu</p>
            <p style="font-family:'DM Mono',monospace;font-weight:700;font-size:1.25rem;letter-spacing:0.1em;color:#111827;">{{ session.qr_code }}</p>
          </div>
        </div>

        <!-- Sensitive Alert -->
        <div v-if="session.is_sensitive_flow" class="qr-sensitive-bar">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span>Hassas Konu — Hasta bu konuyu kalabalık içinde söylemek istemedi.</span>
        </div>

        <!-- Details Grid -->
        <div class="qr-result-section qr-grid-2">
          <div>
            <p class="qr-detail-label">Yaş Aralığı</p>
            <p class="qr-detail-value">{{ session.age_range }} yaş</p>
          </div>
          <div>
            <p class="qr-detail-label">Cinsiyet</p>
            <p class="qr-detail-value">{{ GENDER_LABEL[session.gender] ?? session.gender }}</p>
          </div>
          <div style="grid-column:1/span 2;">
            <p class="qr-detail-label">Seçilen Kategori</p>
            <p class="qr-detail-value">
              {{ session.category?.name ?? session.category_name ?? session.category_slug ?? '—' }}
            </p>
          </div>
        </div>

        <!-- Suggested Ingredients -->
        <div v-if="session.suggested_ingredients?.length" class="qr-result-section">
          <p class="qr-detail-label" style="margin-bottom:0.5rem;">Önerilen Etken Maddeler</p>
          <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">
            <span
              v-for="ing in session.suggested_ingredients"
              :key="ing"
              class="eisa-pill eisa-pill-info"
            >{{ ing }}</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="qr-result-section" style="display:flex;align-items:center;justify-content:space-between;background:#F9FAFB;border-radius:0 0 0.875rem 0.875rem;margin:-0;padding:0.75rem 1.25rem;">
          <span style="font-size:0.75rem;color:#6B7280;">
            Kiosk: <span style="font-weight:600;color:#374151;">{{ session.kiosk?.mac_address ?? session.kiosk_mac ?? '—' }}</span>
          </span>
          <button class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="reset">Yeni Sorgulama</button>
        </div>
      </div>

    </div><!-- /qr-scan-page -->
  </div>
</template>
