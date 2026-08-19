<script setup>
import { ref, computed, onMounted } from 'vue';
import { toast } from 'vue-sonner';
import EisaMultiLookup from './shared/EisaMultiLookup.vue';
import { completeSession } from '../services/analytics';
import { http } from '../services/api';

const props = defineProps({
  session:   { type: Object,  required: true },
  readonly:  { type: Boolean, default: false },
  /** Durum, OturumLoguSerializer'da yok; liste satırından geçilir (modal için). */
  durum:     { type: String,  default: null },
  /** true → dış qr-result-card sarıcısı ve footer "Yeni Sorgulama" butonu görünür. */
  showReset: { type: Boolean, default: false },
});
const emit = defineEmits(['completed', 'reset']);

const completionNote    = ref('');
const completionLoading = ref(false);
const completionError   = ref('');
const selectedIngredients = ref([]);
const ingredientCatalog = ref([]);

onMounted(async () => {
  if (props.readonly) return;
  try {
    const { data } = await http.get('/api/products/ingredients/');
    ingredientCatalog.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch { /* global interceptor */ }
});

const GENDER_LABEL = { F: 'Kadın', M: 'Erkek', O: 'Diğer', male: 'Erkek', female: 'Kadın' };
const DURUM_LABEL  = {
  COMPLETED: { text: 'Tamamlandı',   cls: 'eisa-pill-success' },
  ABANDONED: { text: 'Terk Edildi',  cls: 'eisa-pill-warning' },
  EXPIRED:   { text: 'Süresi Doldu', cls: 'eisa-pill-danger'  },
};

function fmtDT(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR');
}

const ingredientList = computed(() => {
  const s = props.session;
  if (s.onerilen_etken_madde_detaylari?.length) {
    return s.onerilen_etken_madde_detaylari.map(item => ({
      ...item,
      source: item.source || 'RECOMMENDED',
    }));
  }
  return (s.onerilen_etken_maddeler || s.suggested_ingredients || [])
    .map(v => ({ id: v?.id ?? v, ad: v?.ad ?? v, source: 'RECOMMENDED' }));
});
const recommendedIngredients = computed(() =>
  ingredientList.value.filter(item => item.source !== 'PHARMACIST_ADDED')
);
const pharmacistAddedIngredients = computed(() =>
  ingredientList.value.filter(item => item.source === 'PHARMACIST_ADDED')
);

function toggleIngredient(key) {
  if (!Number.isInteger(Number(key))) return;
  key = Number(key);
  const idx = selectedIngredients.value.indexOf(key);
  if (idx === -1) selectedIngredients.value.push(key);
  else selectedIngredients.value.splice(idx, 1);
}

function selectAllIngredients() {
  selectedIngredients.value = recommendedIngredients.value.filter(ing => ing.id).map(ing => Number(ing.id));
}

const ingredientOptions = computed(() => {
  const recommendedIds = new Set(
    ingredientList.value.map(item => Number(item.id)).filter(Boolean)
  );

  return ingredientCatalog.value
    .filter(item => item.aktif !== false && !recommendedIds.has(Number(item.id)))
    .map(item => ({
      id: Number(item.id),
      label: item.ad,
      sub: item.kategori_ad || item.kategori || '',
    }))
    .slice(0, 200);
});

function clearAllIngredients() {
  selectedIngredients.value = [];
}

async function handleComplete(saleResult) {
  if (!props.session?.id || completionLoading.value) return;
  
  // Satış yaptım dendiğinde validasyon (sadece şikayet türünde)
  if (saleResult === 'sold' && props.session.oturum_tipi !== 'OZEL_DANISMANLIK') {
    const hasSelection = selectedIngredients.value.length > 0;
    const hasNote = completionNote.value.trim().length > 0;
    
    if (!hasSelection && !hasNote) {
      toast.warning('Lütfen en az bir etken madde seçin veya danışma notu girin.');
      return;
    }
  }
  
  // Satış yapmadım dendiğinde etken madde seçili olamaz
  if (saleResult === 'not_sold' && selectedIngredients.value.length > 0) {
    toast.warning('Etken madde seçili iken "Satış Yapmadım" diyemezsiniz. Lütfen seçimleri temizleyin.');
    return;
  }
  
  completionLoading.value = true;
  completionError.value   = '';
  try {
    const res = await completeSession(
      props.session.id,
      completionNote.value,
      saleResult,
      selectedIngredients.value,
    );
    completionNote.value      = '';
    selectedIngredients.value = [];
    emit('completed', { ...props.session, ...res.data });
  } catch (err) {
    completionError.value =
      err?.response?.data?.detail || 'Danışma tamamlanırken bir hata oluştu.';
  } finally {
    completionLoading.value = false;
  }
}
</script>

<template>
  <div :class="showReset ? 'qr-result-card' : 'qsc-flat'">

    <!-- Header -->
    <div class="qr-result-header">
      <div>
        <h2 class="qsc-title">Hasta Oturumu</h2>
        <p class="qsc-sub">{{ fmtDT(session.olusturulma_tarihi || session.created_at) }}</p>
      </div>
      <div style="text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;">
        <div>
          <p style="font-size:0.7rem;color:#9CA3AF;margin-bottom:0.2rem;">QR Kodu</p>
          <p class="qsc-qr-code">{{ session.qr_kodu || session.qr_code }}</p>
        </div>
        <span
          v-if="durum"
          class="eisa-pill"
          :class="DURUM_LABEL[durum]?.cls || 'eisa-pill-muted'"
          style="font-size:0.7rem;"
        >{{ DURUM_LABEL[durum]?.text || durum }}</span>
      </div>
    </div>

    <!-- Hassas uyarı -->
    <div v-if="session.hassas_akis || session.is_sensitive_flow" class="qr-sensitive-bar">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span>Hassas Konu — Hasta bu konuyu kalabalık içinde söylemek istemedi.</span>
    </div>

    <!-- Demografik + kiosk grid - 3 kolon -->
    <div class="qr-result-section qr-grid-3">
      <div>
        <p class="qr-detail-label">Yaş Aralığı</p>
        <p class="qr-detail-value">{{ session.yas_araligi_detay?.ad || session.yas_araligi_ad || session.yas_araligi_kod || '—' }}</p>
      </div>
      <div>
        <p class="qr-detail-label">Cinsiyet</p>
        <p class="qr-detail-value">{{ session.cinsiyet_detay?.ad || GENDER_LABEL[session.cinsiyet_kod || session.cinsiyet_ad] || session.cinsiyet_ad || '—' }}</p>
      </div>
      <div>
        <p class="qr-detail-label">Şikayet Tipi</p>
        <p class="qr-detail-value">{{ session.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Özel Danışmanlık' : 'Şikayet' }}</p>
      </div>
      <div>
        <p class="qr-detail-label">Eczane</p>
        <p class="qr-detail-value">{{ session.eczane?.ad || session.eczane_adi || '—' }}</p>
      </div>
      <div>
        <p class="qr-detail-label">Kiosk</p>
        <p class="qr-detail-value">{{ session.kiosk_detay?.ad || session.kiosk_ad || session.kiosk_mac || '—' }}</p>
      </div>
      <div>
        <p class="qr-detail-label">Kategori</p>
        <p class="qr-detail-value">
          <template v-if="session.oturum_tipi === 'OZEL_DANISMANLIK'">
            {{ session.danisma_kategorisi_detay?.ad || session.danisma_kategorisi_adi || '—' }}
          </template>
          <template v-else>
            {{ session.kategori_detay?.ad ?? session.kategori_adi ?? session.category?.name ?? '—' }}
          </template>
        </p>
      </div>
    </div>

    <!-- Soru & Cevaplar -->
    <div v-if="session.cevap_detaylari?.length" class="qr-result-section">
      <p class="qr-detail-label" style="margin-bottom:0.5rem;">Soru ve Cevaplar</p>
      <ol style="margin:0;padding-left:1rem;display:grid;gap:0.5rem;">
        <li
          v-for="item in session.cevap_detaylari"
          :key="`${item.soru_id}-${item.cevap_id}-${item.sira}`"
          style="font-size:0.85rem;color:#111827;"
        >
          <strong>{{ item.soru_metni }}</strong>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.25rem;">
            <span>Yanıt:</span>
            <span
              class="eisa-pill"
              :class="{
                'eisa-pill-success': item.cevap_metni?.toLowerCase() === 'evet',
                'eisa-pill-danger': item.cevap_metni?.toLowerCase() === 'hayır' || item.cevap_metni?.toLowerCase() === 'hayir'
              }"
              style="font-size:0.75rem;"
            >{{ item.cevap_metni }}</span>
          </div>
        </li>
      </ol>
    </div>

    <!-- Önerilen Etken Maddeler -->
    <div v-if="recommendedIngredients.length" class="qr-result-section">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">
        <p class="qr-detail-label" style="margin:0;">Kiosk Tarafından Önerilen Etken Maddeler</p>
        <div v-if="!session.danisma_tamamlandi && !readonly" style="display:flex;gap:0.5rem;">
          <button
            type="button"
            class="qsc-batch-btn qsc-batch-btn--success"
            @click="selectAllIngredients"
            :disabled="recommendedIngredients.every(item => !item.id || selectedIngredients.includes(Number(item.id)))"
          >
            <i class="fa-solid fa-check-double" style="font-size:0.7rem;"></i>
            Tümünü Seç
          </button>
          <button
            type="button"
            class="qsc-batch-btn qsc-batch-btn--danger"
            @click="clearAllIngredients"
            :disabled="selectedIngredients.length === 0"
          >
            <i class="fa-solid fa-xmark" style="font-size:0.7rem;"></i>
            Temizle
          </button>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">
        <template v-if="!session.danisma_tamamlandi && !readonly">
          <button
            v-for="ing in recommendedIngredients"
            :key="'sel-' + (ing.id ?? ing.ad)"
            type="button"
            class="qsc-ing-label"
            :disabled="!ing.id"
            :class="{ 'qsc-ing-label--selected': selectedIngredients.includes(Number(ing.id)) }"
            @click="toggleIngredient(ing.id)"
          >
            <i class="fa-solid" :class="selectedIngredients.includes(Number(ing.id)) ? 'fa-square-check' : 'fa-square'"></i>
            <span>{{ ing.ad }}</span>
          </button>
        </template>
        <template v-else>
          <span v-for="ing in recommendedIngredients" :key="'ro-' + (ing.id ?? ing.ad)" class="qsc-source-pill qsc-source-pill--recommended">
            <i v-if="ing.satildi" class="fa-solid fa-check"></i>
            <span>{{ ing.ad }}</span><small>Önerilen</small>
          </span>
        </template>
      </div>
    </div>

    <div v-if="session.danisma_tamamlandi && pharmacistAddedIngredients.length" class="qr-result-section qsc-added-section">
      <p class="qr-detail-label">Eczacı Tarafından Eklenen Etken Maddeler</p>
      <div class="qsc-source-list">
        <span v-for="ing in pharmacistAddedIngredients" :key="'added-' + (ing.id ?? ing.ad)" class="qsc-source-pill qsc-source-pill--added">
          <i v-if="ing.satildi" class="fa-solid fa-check"></i>
          <span>{{ ing.ad }}</span><small>Eczacı Ekledi</small>
        </span>
      </div>
    </div>

    <div v-if="!readonly && !session.danisma_tamamlandi" class="qr-result-section">
      <p class="qr-detail-label" style="margin-bottom:0.5rem;">Diğer Etken Madde Ekle</p>
      <EisaMultiLookup
        v-model="selectedIngredients"
        :options="ingredientOptions"
        placeholder="Etken madde ara…"
      />
    </div>

    <!-- Tamamlandı bilgisi -->
    <div v-if="session.danisma_tamamlandi" class="qr-result-section qsc-complete-info">
      <div class="qsc-complete-header">
        <i class="fa-solid fa-check-circle"></i>
        <span>Danışma Tamamlandı</span>
      </div>
      <p v-if="session.danisma_notu" class="qsc-complete-note">
        <strong>Eczacı Notu:</strong> {{ session.danisma_notu }}
      </p>
      <p class="qsc-complete-meta">
        {{ session.danisma_tamamlayan_eczaci_adi || '—' }} tarafından
        {{ fmtDT(session.danisma_tamamlanma_tarihi) }} tarihinde tamamlandı.
      </p>
      <p v-if="session.sold !== null && session.sold !== undefined" class="qsc-complete-meta" style="padding-left:1.75rem;margin-top:0.3rem;">
        Satış: {{ session.sold ? 'Yapıldı' : 'Yapılmadı' }}
      </p>
    </div>

    <!-- Tamamlama formu -->
    <div
      v-if="!readonly && !session.danisma_tamamlandi && session.tamamlandi"
      class="qr-result-section qsc-complete-action"
    >
      <p class="qr-detail-label" style="margin-bottom:0.5rem;">Danışma Notu (Opsiyonel)</p>
      <textarea
        v-model="completionNote"
        rows="2"
        placeholder="Hastaya verilen tavsiye..."
        class="eisa-field"
        style="margin-bottom:0.75rem;"
      ></textarea>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
        <button
          class="eisa-btn eisa-btn-success"
          :disabled="completionLoading"
          @click="handleComplete('sold')"
          style="font-weight:600;"
        >
          <i v-if="completionLoading" class="fa-solid fa-circle-notch fa-spin"></i>
          <i v-else class="fa-solid fa-check"></i>
          Satış Yaptım
        </button>
        <button
          class="eisa-btn eisa-btn-danger"
          :disabled="completionLoading"
          @click="handleComplete('not_sold')"
          style="font-weight:600;"
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

    <!-- Terk edildi / expired uyarısı -->
    <div
      v-if="!readonly && !session.danisma_tamamlandi && !session.tamamlandi"
      class="qr-result-section qsc-abandoned-bar"
    >
      <i class="fa-solid fa-circle-info" style="margin-right:0.4rem;"></i>
      Hasta oturumu tamamlamadığı için danışma yapılamıyor.
    </div>

    <!-- Footer -->
    <div
      class="qr-result-section"
      style="display:flex;align-items:center;justify-content:space-between;background:#F9FAFB;padding:0.75rem 1.25rem;"
    >
      <span style="font-size:0.75rem;color:#6B7280;">
        Kiosk MAC: <span style="font-weight:600;color:#374151;">{{ session.kiosk_detay?.mac_adresi ?? session.kiosk_mac ?? '—' }}</span>
      </span>
      <button v-if="showReset" class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="emit('reset')">
        Yeni Sorgulama
      </button>
    </div>

  </div>
</template>

<style scoped>
.qsc-flat { display: contents; }

.qsc-title { font-size: 1rem; font-weight: 700; color: #111827; margin-bottom: 0.2rem; }
.qsc-sub   { font-size: 0.72rem; color: #9CA3AF; }
.qsc-qr-code {
  font-family: 'DM Mono', monospace;
  font-weight: 700; font-size: 1.25rem;
  letter-spacing: 0.1em; color: #111827;
}

.qsc-complete-info {
  background: #F0FDF4;
  border: 1px solid #A7F3D0;
  border-radius: 0.75rem;
  padding: 1rem 1.25rem;
  margin: 0.25rem 0.85rem;
}
.qsc-complete-header {
  display: flex; align-items: center; gap: 0.5rem;
  font-weight: 700; color: #065F46; margin-bottom: 0.5rem;
}
.qsc-complete-header i { color: #10B981; }
.qsc-complete-note {
  font-size: 0.875rem; color: #047857;
  margin-bottom: 0.5rem; padding-left: 1.75rem;
}
.qsc-complete-meta {
  font-size: 0.75rem; color: #065F46; padding-left: 1.75rem;
}

.qsc-complete-action {
  background: #F9FAFB;
  border-top: 1px solid #E5E7EB;
}

.qsc-abandoned-bar {
  font-size: 0.82rem; color: #D97706;
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.2);
  border-radius: 6px;
  margin: 0.5rem 1.25rem;
  padding: 0.75rem;
}

.qsc-ing-label {
  display: flex; align-items: center; gap: 0.35rem;
  cursor: pointer; font-size: 0.84rem; color: #374151;
  background: #F3F4F6; padding: 0.3rem 0.65rem;
  border-radius: 999px; border: 1.5px solid transparent;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.qsc-ing-label--selected {
  border-color: #0D9488;
  background: #CCFBF1;
  color: #065F46;
}

.qsc-batch-btn {
  display: flex; align-items: center; gap: 0.3rem;
  font-size: 0.72rem; font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem; border: 1px solid;
  cursor: pointer;
  transition: all 0.15s;
}
.qsc-batch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.qsc-batch-btn--success {
  color: #065F46;
  background: #D1FAE5;
  border-color: #6EE7B7;
}
.qsc-batch-btn--success:hover:not(:disabled) {
  background: #A7F3D0;
  border-color: #34D399;
}
.qsc-batch-btn--danger {
  color: #991B1B;
  background: #FEE2E2;
  border-color: #FCA5A5;
}
.qsc-batch-btn--danger:hover:not(:disabled) {
  background: #FECACA;
  border-color: #F87171;
}
.qsc-ing-label small,
.qsc-source-pill small { font-size:.64rem; font-weight:750; opacity:.82; }
.qsc-ing-label--added {
  border-color: var(--eisa-info-border);
  background: var(--eisa-info-soft);
  color: var(--eisa-info);
}
.qsc-source-list { display:flex; flex-wrap:wrap; gap:.5rem; }
.qsc-selected-other { margin-top:.5rem; }
.qsc-source-pill { display:inline-flex; align-items:center; gap:.38rem; padding:.35rem .7rem; border-radius:999px; font-size:.82rem; border:1px solid; }
.qsc-source-pill--recommended { color:#065F46; background:#ECFDF5; border-color:#A7F3D0; }
.qsc-source-pill--added { color:var(--eisa-info); background:var(--eisa-info-soft); border-color:var(--eisa-info-border); }
.qsc-added-section { background:var(--eisa-info-soft); border-left:3px solid var(--eisa-info); }
.qsc-ingredient-picker {
  position: relative;
  border: 1.5px solid #D1D5DB;
  border-radius: 12px;
  background: #fff;
  padding: 0.5rem 0.7rem 0.6rem;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04);
}
.qsc-picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.45rem;
}
.qsc-picker-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid #C7D2FE;
  background: #EEF2FF;
  color: #4338CA;
  border-radius: 999px;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}
.qsc-picker-chip small {
  opacity: 0.8;
  font-size: 0.62rem;
  letter-spacing: 0.02em;
}
.qsc-picker-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.1rem;
}
.qsc-picker-icon {
  color: #6B7280;
  font-size: 0.78rem;
}
.qsc-picker-input {
  flex: 1;
  border: none;
  background: transparent;
  color: #111827;
  font-size: 0.9rem;
  font-family: inherit;
  outline: none;
  min-width: 0;
}
.qsc-picker-input::placeholder { color: #9CA3AF; }
.qsc-other-options {
  position:absolute;z-index:20;left:0;right:0;top:calc(100% + 0.35rem);background:#fff;border:1px solid #D1D5DB;border-radius:10px;box-shadow:0 12px 28px rgba(15,23,42,0.12);overflow:hidden;
}
.qsc-other-options button {
  display:block;width:100%;padding:.6rem .75rem;text-align:left;background:#fff;border:0;cursor:pointer;font-size:.82rem;color:#374151;
}
.qsc-other-options button:hover { background:#ECFDF5;color:#065F46; }
.qsc-help { margin-top:.4rem;font-size:.75rem;color:#6B7280; }
</style>
