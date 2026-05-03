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
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">🔍 QR Okutma</h1>

    <div class="bg-white rounded-xl shadow p-5 space-y-4">
      <label class="block text-sm font-medium text-gray-700">
        Hastanın QR Kodunu Girin veya Okutun
      </label>
      <div class="flex gap-2">
        <input
          v-model="qrInput"
          @keyup.enter="lookup"
          placeholder="8 karakterlik QR kod (ör. A1B2C3D4)"
          class="flex-1 border rounded-lg px-4 py-2 text-sm font-mono tracking-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
          :disabled="loading"
        />
        <button
          @click="lookup"
          :disabled="loading || !qrInput.trim()"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium transition"
        >
          {{ loading ? '…' : 'Sorgula' }}
        </button>
      </div>

      <div v-if="cameraSupported" class="flex items-center gap-3">
        <button
          @click="cameraActive ? stopCamera() : startCamera()"
          :class="cameraActive ? 'bg-red-100 text-red-700 border-red-300' : 'bg-gray-100 text-gray-600 border-gray-300'"
          class="border text-sm px-4 py-2 rounded-lg font-medium transition"
        >
          {{ cameraActive ? '📷 Kamerayı Durdur' : '📷 Kamera ile Tara' }}
        </button>
        <span v-if="cameraActive" class="text-xs text-gray-400 animate-pulse">QR bekleniyor…</span>
      </div>

      <div v-if="cameraActive" class="rounded-lg overflow-hidden border border-gray-200">
        <video ref="videoRef" class="w-full max-h-64 object-cover bg-black" muted playsinline />
      </div>
    </div>

    <div v-if="ownershipError" class="bg-red-50 border border-red-300 text-red-800 rounded-xl p-5 text-center">
      <p class="text-3xl mb-2">🚫</p>
      <p class="font-bold text-lg">{{ ownershipError }}</p>
      <p class="text-sm mt-1 text-red-700">Bu QR kod başka bir eczanenin kioskundan üretilmiş.</p>
      <button @click="reset" class="mt-3 text-sm text-blue-600 hover:underline">Yeniden dene</button>
    </div>

    <div v-else-if="apiError" class="bg-red-50 text-red-700 border border-red-200 rounded-lg p-3 text-sm">
      {{ apiError }}
    </div>

    <div v-if="offlineMode" class="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-3 text-xs flex items-center gap-2">
      <span>📴</span>
      <span>Sunucuya ulaşılamadı; veriler QR'dan okundu (offline mod).</span>
    </div>

    <div v-if="notFound" class="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-xl p-5 text-center">
      <p class="text-2xl mb-2">🔎</p>
      <p class="font-semibold">Oturum bulunamadı</p>
      <p class="text-sm mt-1">
        <span class="font-mono font-bold">{{ qrInput.trim() }}</span> koduna ait kayıt yok.
      </p>
      <button @click="reset" class="mt-3 text-sm text-blue-600 hover:underline">Yeniden dene</button>
    </div>

    <div v-if="session && !ownershipError" class="bg-white rounded-xl shadow divide-y divide-gray-100">
      <div class="p-5 flex items-center justify-between">
        <div>
          <h2 class="font-bold text-gray-800 text-lg">Hasta Oturumu</h2>
          <p class="text-xs text-gray-400 mt-0.5">{{ formatDT(session.created_at) }}</p>
        </div>
        <div class="text-right">
          <p class="text-xs text-gray-500">QR Kodu</p>
          <p class="font-mono font-bold text-xl tracking-widest text-gray-800">{{ session.qr_code }}</p>
        </div>
      </div>

      <div v-if="session.is_sensitive_flow" class="px-5 py-3 bg-red-50 flex items-center gap-2">
        <span class="text-red-600 font-bold">⚠️ Hassas Konu</span>
        <span class="text-red-700 text-sm">Hasta bu konuyu kalabalık içinde söylemek istemedi.</span>
      </div>

      <div class="px-5 py-4 grid grid-cols-2 gap-4">
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Yaş Aralığı</p>
          <p class="font-semibold text-gray-800">{{ session.age_range }} yaş</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Cinsiyet</p>
          <p class="font-semibold text-gray-800">{{ GENDER_LABEL[session.gender] ?? session.gender }}</p>
        </div>
        <div class="col-span-2">
          <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Seçilen Kategori</p>
          <p class="font-semibold text-gray-800">
            {{ session.category?.name ?? session.category_name ?? session.category_slug ?? '—' }}
          </p>
        </div>
      </div>

      <div v-if="session.suggested_ingredients?.length" class="px-5 py-4">
        <p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Önerilen Etken Maddeler</p>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="ing in session.suggested_ingredients"
            :key="ing"
            class="bg-blue-50 text-blue-700 text-sm px-3 py-1 rounded-full font-medium"
          >{{ ing }}</span>
        </div>
      </div>

      <div
        v-if="!session.is_sensitive_flow && session.answers_payload && Object.keys(session.answers_payload).length"
        class="px-5 py-4"
      >
        <p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Anket Cevapları</p>
        <table class="w-full text-sm">
          <tbody>
            <tr
              v-for="(val, key) in session.answers_payload"
              :key="key"
              class="border-t border-gray-50"
            >
              <td class="py-1.5 text-gray-500 pr-4">{{ key }}</td>
              <td class="py-1.5 font-medium text-gray-700">{{ val }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="px-5 py-3 bg-gray-50 flex items-center justify-between">
        <span class="text-xs text-gray-500">
          Kiosk:
          <span class="font-medium text-gray-700">
            {{ session.kiosk?.mac_address ?? session.kiosk_mac ?? '—' }}
          </span>
        </span>
        <button @click="reset" class="text-xs text-blue-600 hover:underline">Yeni Sorgulama</button>
      </div>
    </div>
  </div>
</template>
