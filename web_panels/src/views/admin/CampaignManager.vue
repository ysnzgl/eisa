<script setup>
/**
 * Kampanya Yöneticisi — DOOH Idle-Screen Reklam Modülü
 * Modul 3: Kampanya oluşturma, hedefleme, sekmeli liste
 */
import { ref, computed, onMounted } from 'vue';
import {
  getCampaigns,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  uploadMedia,
  campaignStatus,
  TR_PROVINCES,
  MOCK_PHARMACIES,
} from '../../services/campaignManager';

// ─── Veriler ──────────────────────────────────────────────────────────────────
const allCampaigns   = ref([]);
const loadingList    = ref(true);
const activeTab      = ref('active');   // 'active' | 'upcoming' | 'ended'

// ─── Drawer (Oluştur/Düzenle) ────────────────────────────────────────────────
const drawerOpen     = ref(false);
const drawerMode     = ref('create');   // 'create' | 'edit'
const editingId      = ref(null);
const drawerStep     = ref(1);          // 1: Temel Bilgi, 2: Medya, 3: Hedefleme
const drawerSaving   = ref(false);
const drawerError    = ref('');

// ─── Form ─────────────────────────────────────────────────────────────────────
const EMPTY_FORM = () => ({
  name:               '',
  client:             '',
  duration_sec:       15,
  media_url:          '',
  media_type:         'image',
  starts_at:          '',
  ends_at:            '',
  broadcast_start:    '08:00',
  broadcast_end:      '22:00',
  target_provinces:   [],
  target_pharmacy_ids: [],
  is_active:          true,
});
const form = ref(EMPTY_FORM());

// ─── Medya Yükleme ────────────────────────────────────────────────────────────
const uploadState    = ref('idle');     // 'idle' | 'uploading' | 'done' | 'error'
const uploadProgress = ref(0);
const dragOver       = ref(false);
const fileInputRef   = ref(null);
const previewUrl     = ref('');
const previewType    = ref('image');

// ─── Hedefleme UI ─────────────────────────────────────────────────────────────
const targetMode     = ref('province'); // 'province' | 'pharmacy'
const provSearch     = ref('');
const pharmSearch    = ref('');

// ─── Silme onayı ─────────────────────────────────────────────────────────────
const deleteTarget   = ref(null);
const deleting       = ref(false);

// ─── Computed ─────────────────────────────────────────────────────────────────
const tabCounts = computed(() => ({
  active:   allCampaigns.value.filter((c) => campaignStatus(c) === 'active').length,
  upcoming: allCampaigns.value.filter((c) => campaignStatus(c) === 'upcoming').length,
  ended:    allCampaigns.value.filter((c) => campaignStatus(c) === 'ended').length,
}));

const visibleCampaigns = computed(() =>
  allCampaigns.value.filter((c) => campaignStatus(c) === activeTab.value)
);

const filteredProvinces = computed(() =>
  TR_PROVINCES.filter((p) => p.toLowerCase().includes(provSearch.value.toLowerCase()))
);

const filteredPharmacies = computed(() =>
  MOCK_PHARMACIES.filter((p) =>
    p.name.toLowerCase().includes(pharmSearch.value.toLowerCase()) ||
    p.province.toLowerCase().includes(pharmSearch.value.toLowerCase())
  )
);

const stepValid = computed(() => {
  if (drawerStep.value === 1) return form.value.name.trim() && form.value.client.trim() && form.value.duration_sec > 0;
  if (drawerStep.value === 2) return !!form.value.media_url;
  return true;
});

// ─── Yükleme ─────────────────────────────────────────────────────────────────
async function loadCampaigns() {
  loadingList.value = true;
  try { allCampaigns.value = await getCampaigns(); }
  finally { loadingList.value = false; }
}
onMounted(loadCampaigns);

// ─── Drawer ──────────────────────────────────────────────────────────────────
function openCreate() {
  form.value    = EMPTY_FORM();
  previewUrl.value = '';
  previewType.value = 'image';
  uploadState.value = 'idle';
  uploadProgress.value = 0;
  drawerStep.value = 1;
  drawerMode.value = 'create';
  editingId.value  = null;
  drawerError.value = '';
  targetMode.value = 'province';
  drawerOpen.value = true;
}

function openEdit(c) {
  form.value = {
    name:               c.name,
    client:             c.client,
    duration_sec:       c.duration_sec,
    media_url:          c.media_url,
    media_type:         c.media_type,
    starts_at:          toDateInput(c.starts_at),
    ends_at:            toDateInput(c.ends_at),
    broadcast_start:    c.broadcast_start,
    broadcast_end:      c.broadcast_end,
    target_provinces:   [...(c.target_provinces  ?? [])],
    target_pharmacy_ids: [...(c.target_pharmacy_ids ?? [])],
    is_active:          c.is_active,
  };
  previewUrl.value  = c.media_url;
  previewType.value = c.media_type;
  uploadState.value = 'done';
  drawerStep.value  = 1;
  drawerMode.value  = 'edit';
  editingId.value   = c.id;
  drawerError.value = '';
  targetMode.value  = c.target_pharmacy_ids?.length ? 'pharmacy' : 'province';
  drawerOpen.value  = true;
}

function closeDrawer() { drawerOpen.value = false; }

function nextStep() { if (stepValid.value) drawerStep.value++; }
function prevStep() { drawerStep.value--; }

async function saveForm() {
  if (!form.value.starts_at || !form.value.ends_at) {
    drawerError.value = 'Başlangıç ve bitiş tarihi zorunludur.';
    return;
  }
  if (new Date(form.value.starts_at) >= new Date(form.value.ends_at)) {
    drawerError.value = 'Bitiş tarihi başlangıçtan sonra olmalıdır.';
    return;
  }
  drawerSaving.value = true;
  drawerError.value  = '';
  try {
    const payload = { ...form.value };
    if (targetMode.value === 'province') payload.target_pharmacy_ids = [];
    else payload.target_provinces = [];
    if (drawerMode.value === 'create') {
      await createCampaign(payload);
    } else {
      await updateCampaign(editingId.value, payload);
    }
    await loadCampaigns();
    closeDrawer();
  } catch { drawerError.value = 'Kayıt başarısız. Lütfen tekrar deneyin.'; }
  finally { drawerSaving.value = false; }
}

// ─── Medya Yükleme ────────────────────────────────────────────────────────────
function onDrop(e) {
  dragOver.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFile(file);
}

function onFileChange(e) {
  const file = e.target.files?.[0];
  if (file) handleFile(file);
}

async function handleFile(file) {
  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'video/mp4', 'video/webm'];
  if (!allowed.includes(file.type)) {
    uploadState.value = 'error';
    return;
  }
  uploadState.value    = 'uploading';
  uploadProgress.value = 0;
  const ticker = setInterval(() => {
    uploadProgress.value = Math.min(uploadProgress.value + Math.random() * 18, 92);
  }, 120);
  try {
    const { url, type } = await uploadMedia(file);
    clearInterval(ticker);
    uploadProgress.value = 100;
    uploadState.value    = 'done';
    form.value.media_url  = url;
    form.value.media_type = type;
    previewUrl.value  = url;
    previewType.value = type;
  } catch {
    clearInterval(ticker);
    uploadState.value = 'error';
  }
}

function clearMedia() {
  form.value.media_url  = '';
  form.value.media_type = 'image';
  previewUrl.value  = '';
  uploadState.value = 'idle';
  uploadProgress.value = 0;
  if (fileInputRef.value) fileInputRef.value.value = '';
}

// ─── Hedefleme ────────────────────────────────────────────────────────────────
function toggleProvince(p) {
  const idx = form.value.target_provinces.indexOf(p);
  if (idx === -1) form.value.target_provinces.push(p);
  else form.value.target_provinces.splice(idx, 1);
}

function togglePharmacy(id) {
  const idx = form.value.target_pharmacy_ids.indexOf(id);
  if (idx === -1) form.value.target_pharmacy_ids.push(id);
  else form.value.target_pharmacy_ids.splice(idx, 1);
}

// ─── Silme ───────────────────────────────────────────────────────────────────
async function confirmDelete() {
  deleting.value = true;
  try {
    await deleteCampaign(deleteTarget.value.id);
    await loadCampaigns();
    deleteTarget.value = null;
  } finally { deleting.value = false; }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function toDateInput(iso) {
  if (!iso) return '';
  return iso.slice(0, 16); // "YYYY-MM-DDTHH:mm"
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtDateShort(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' });
}

function targetSummary(c) {
  if (c.target_pharmacy_ids?.length) return `${c.target_pharmacy_ids.length} eczane`;
  if (c.target_provinces?.length)    return c.target_provinces.slice(0, 2).join(', ') + (c.target_provinces.length > 2 ? ` +${c.target_provinces.length - 2}` : '');
  return 'Tüm Türkiye';
}

function progressDays(c) {
  const start = new Date(c.starts_at).getTime();
  const end   = new Date(c.ends_at).getTime();
  const now   = Date.now();
  const pct   = Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100));
  return Math.round(pct);
}

function daysLeft(c) {
  const diff = new Date(c.ends_at).getTime() - Date.now();
  const d    = Math.ceil(diff / 86400000);
  if (d < 0) return 'Bitti';
  if (d === 0) return 'Bugün bitiyor';
  return `${d} gün kaldı`;
}

function daysUntil(c) {
  const diff = new Date(c.starts_at).getTime() - Date.now();
  const d    = Math.ceil(diff / 86400000);
  return d <= 0 ? 'Başladı' : `${d} gün sonra başlıyor`;
}

const TAB_CONFIG = [
  { key: 'active',   label: 'Aktif',     dot: 'bg-emerald-400' },
  { key: 'upcoming', label: 'Yaklaşan',  dot: 'bg-amber-400'   },
  { key: 'ended',    label: 'Tamamlandı',dot: 'bg-zinc-500'    },
];
</script>

<template>
  <div class="cm-root min-h-screen">

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- ÜSTÜ: Sayfa Başlığı + CTA                                             -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="cm-topbar px-8 py-6 flex items-start justify-between border-b border-slate-800/60">
      <div>
        <p class="eyebrow mb-1">Kiosk Yayın Sistemi</p>
        <h1 class="page-title">Kampanya Yöneticisi</h1>
        <p class="text-sm text-slate-400 mt-1 font-light tracking-wide">Idle-screen reklam içeriklerini planlayın, hedefleyin ve izleyin.</p>
      </div>
      <button @click="openCreate" class="cta-btn flex items-center gap-2.5">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        <span>Yeni Kampanya</span>
      </button>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- ÖZET KPI BANDI                                                        -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="px-8 py-5 grid grid-cols-3 gap-4 border-b border-slate-800/60">
      <div v-for="tab in TAB_CONFIG" :key="tab.key" class="kpi-card">
        <div class="flex items-center gap-2 mb-1">
          <span class="w-2 h-2 rounded-full flex-shrink-0" :class="tab.dot"></span>
          <span class="kpi-label">{{ tab.label }}</span>
        </div>
        <div class="kpi-value">
          <span v-if="loadingList" class="kpi-skeleton"></span>
          <span v-else>{{ tabCounts[tab.key] }}</span>
        </div>
        <p class="kpi-sub">kampanya</p>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SEKME + LISTE                                                          -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="px-8 pt-6 pb-10">
      <!-- Sekmeler -->
      <div class="flex items-center gap-1 mb-6 border-b border-slate-800/60 pb-0">
        <button
          v-for="tab in TAB_CONFIG"
          :key="tab.key"
          @click="activeTab = tab.key"
          class="tab-btn relative flex items-center gap-2 px-4 py-2.5 text-sm font-semibold transition-colors duration-150"
          :class="activeTab === tab.key ? 'tab-active' : 'text-slate-500 hover:text-slate-300'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="tab.dot"></span>
          {{ tab.label }}
          <span class="tab-count">{{ tabCounts[tab.key] }}</span>
          <span v-if="activeTab === tab.key" class="tab-underline"></span>
        </button>
      </div>

      <!-- Yükleniyor -->
      <div v-if="loadingList" class="space-y-3">
        <div v-for="n in 3" :key="n" class="h-28 bg-slate-800/40 rounded-2xl animate-pulse"></div>
      </div>

      <!-- Boş durum -->
      <div
        v-else-if="visibleCampaigns.length === 0"
        class="flex flex-col items-center justify-center py-20 text-slate-600"
      >
        <svg class="w-14 h-14 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.854V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2h14a2 2 0 002-2v-1.854a1 1 0 00-.553-.894L15 14M15 10v4"/>
        </svg>
        <p class="text-sm font-medium">Bu sekme için kampanya bulunamadı.</p>
        <button v-if="activeTab !== 'ended'" @click="openCreate" class="mt-3 text-orange-400 text-sm hover:text-orange-300 underline underline-offset-2">İlk kampanyayı oluştur →</button>
      </div>

      <!-- Kampanya Kartları -->
      <div v-else class="space-y-4">
        <div
          v-for="(c, ci) in visibleCampaigns"
          :key="c.id"
          class="camp-card group"
          :style="{ animationDelay: ci * 50 + 'ms' }"
        >
          <!-- Media Önizleme Şeridi -->
          <div class="camp-media-thumb flex-shrink-0">
            <img
              v-if="c.media_type === 'image'"
              :src="c.media_url"
              alt=""
              class="w-full h-full object-cover"
              @error="$event.target.src='https://placehold.co/100x180/1e293b/334155?text=📺'"
            />
            <div v-else class="w-full h-full flex items-center justify-center bg-slate-800">
              <svg class="w-6 h-6 text-orange-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>

          <!-- Ana İçerik -->
          <div class="flex-1 min-w-0 py-4 pr-4">
            <!-- Başlık satırı -->
            <div class="flex items-start justify-between gap-4 mb-2">
              <div>
                <h3 class="camp-name">{{ c.name }}</h3>
                <p class="camp-client">{{ c.client }}</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0 pt-0.5">
                <!-- Yayın süresi badge -->
                <span class="duration-badge">{{ c.duration_sec }}s</span>
                <!-- Aksiyon butonları -->
                <button @click="openEdit(c)" class="icon-btn" title="Düzenle">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button @click="deleteTarget = c" class="icon-btn icon-btn-danger" title="Sil">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Meta bilgiler -->
            <div class="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-400 mb-3">
              <!-- Tarih aralığı -->
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                {{ fmtDateShort(c.starts_at) }} — {{ fmtDateShort(c.ends_at) }}
              </span>
              <!-- Yayın saatleri -->
              <span class="flex items-center gap-1 font-mono">
                <svg class="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                {{ c.broadcast_start }} – {{ c.broadcast_end }}
              </span>
              <!-- Hedefleme -->
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                {{ targetSummary(c) }}
              </span>
            </div>

            <!-- İlerleme çubuğu (aktif kampanyalar) -->
            <template v-if="campaignStatus(c) === 'active'">
              <div class="flex items-center gap-3">
                <div class="flex-1 progress-track">
                  <div class="progress-fill" :style="{ width: progressDays(c) + '%' }"></div>
                </div>
                <span class="text-xs text-orange-300 font-mono flex-shrink-0">{{ daysLeft(c) }}</span>
              </div>
            </template>
            <!-- Yaklaşan kampanyalar -->
            <template v-else-if="campaignStatus(c) === 'upcoming'">
              <span class="text-xs text-amber-300 font-mono">{{ daysUntil(c) }}</span>
            </template>
            <!-- Biten kampanyalar -->
            <template v-else>
              <span class="text-xs text-slate-600 font-mono">{{ fmtDate(c.ends_at) }} tarihinde tamamlandı</span>
            </template>
          </div>
        </div>
      </div>
    </div>

  </div><!-- /cm-root -->


  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!-- KAMPANYA DRAWER                                                        -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div v-if="drawerOpen" class="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm" @click="closeDrawer"></div>
    </Transition>
    <Transition name="drawer">
      <aside v-if="drawerOpen" class="cm-drawer fixed right-0 top-0 h-full z-50 flex flex-col">

        <!-- Drawer Başlık + Adımlar -->
        <div class="drawer-head flex-shrink-0">
          <div class="flex items-center justify-between mb-4">
            <div>
              <p class="eyebrow text-xs">{{ drawerMode === 'create' ? 'Yeni Kampanya' : 'Kampanyayı Düzenle' }}</p>
              <h2 class="text-base font-bold text-slate-100 tracking-tight">
                {{ drawerStep === 1 ? 'Temel Bilgiler' : drawerStep === 2 ? 'Medya Yükleme' : 'Hedefleme & Zamanlama' }}
              </h2>
            </div>
            <button @click="closeDrawer" class="icon-btn">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <!-- Step Dots -->
          <div class="flex items-center gap-2">
            <div
              v-for="n in 3" :key="n"
              class="step-dot transition-all duration-200"
              :class="n === drawerStep ? 'step-dot-active' : n < drawerStep ? 'step-dot-done' : 'step-dot-idle'"
            >
              <span class="text-[10px] font-bold">{{ n }}</span>
            </div>
            <div class="flex-1 h-px bg-slate-700 mx-1"></div>
            <span class="text-xs text-slate-500">{{ drawerStep }}/3</span>
          </div>
        </div>

        <!-- Form İçeriği -->
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">

          <!-- Hata -->
          <div v-if="drawerError" class="error-banner">
            <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            {{ drawerError }}
          </div>

          <!-- ─ Adım 1: Temel Bilgiler ────────────────────────────────── -->
          <template v-if="drawerStep === 1">
            <div>
              <label class="field-label">Kampanya Adı <span class="req">*</span></label>
              <input v-model="form.name" type="text" placeholder="Bahar Vitamin Kampanyası" class="field-input"/>
            </div>
            <div>
              <label class="field-label">Müşteri / Firma Adı <span class="req">*</span></label>
              <input v-model="form.client" type="text" placeholder="Eczacıbaşı Sağlık A.Ş." class="field-input"/>
            </div>
            <div>
              <label class="field-label">Ekranda Kalma Süresi <span class="req">*</span></label>
              <p class="text-xs text-slate-500 mb-2">Her dönüşte kaç saniye gösterilecek</p>
              <div class="flex items-center gap-4">
                <input
                  v-model.number="form.duration_sec"
                  type="range" min="5" max="60" step="1"
                  class="flex-1 accent-orange-500 cursor-pointer"
                />
                <div class="duration-display">
                  <span class="text-2xl font-black text-orange-400 leading-none">{{ form.duration_sec }}</span>
                  <span class="text-xs text-slate-500 leading-none">sn</span>
                </div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-600 mt-1 font-mono">
                <span>5s</span><span>15s</span><span>30s</span><span>45s</span><span>60s</span>
              </div>
            </div>

            <!-- is_active toggle -->
            <div class="flex items-center justify-between bg-slate-800/40 border border-slate-700/40 rounded-xl px-4 py-3">
              <div>
                <p class="text-sm font-semibold text-slate-200">Aktif Olarak Yayınla</p>
                <p class="text-xs text-slate-500">Kapalıysa taslak olarak kaydedilir</p>
              </div>
              <button
                @click="form.is_active = !form.is_active"
                class="relative inline-flex items-center w-11 h-6 rounded-full transition-colors duration-200 flex-shrink-0"
                :class="form.is_active ? 'bg-orange-500' : 'bg-slate-700'"
              >
                <span class="inline-block w-4 h-4 bg-white rounded-full shadow transition-transform duration-200" :class="form.is_active ? 'translate-x-6' : 'translate-x-1'"></span>
              </button>
            </div>
          </template>

          <!-- ─ Adım 2: Medya Yükleme ────────────────────────────────── -->
          <template v-if="drawerStep === 2">
            <!-- Sürükle-bırak alanı -->
            <div
              v-if="uploadState === 'idle' || uploadState === 'error'"
              class="drop-zone"
              :class="dragOver ? 'drop-zone-active' : ''"
              @dragover.prevent="dragOver = true"
              @dragleave="dragOver = false"
              @drop.prevent="onDrop"
              @click="fileInputRef?.click()"
            >
              <input ref="fileInputRef" type="file" class="hidden" accept="image/*,video/mp4,video/webm" @change="onFileChange"/>
              <div class="drop-icon">
                <svg class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                </svg>
              </div>
              <p class="text-sm font-semibold text-slate-300 mt-3">Sürükle & bırak veya tıkla</p>
              <p class="text-xs text-slate-500 mt-1">JPG, PNG, WebP, GIF, MP4, WebM</p>
              <p v-if="uploadState === 'error'" class="text-xs text-rose-400 mt-2 font-medium">Desteklenmeyen dosya türü.</p>
            </div>

            <!-- Yükleniyor -->
            <div v-else-if="uploadState === 'uploading'" class="upload-progress-box">
              <div class="flex items-center gap-3 mb-3">
                <svg class="animate-spin w-5 h-5 text-orange-400" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                <span class="text-sm font-semibold text-slate-200">Yükleniyor…</span>
                <span class="ml-auto text-xs font-mono text-orange-400">{{ Math.round(uploadProgress) }}%</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill-upload" :style="{ width: uploadProgress + '%' }"></div>
              </div>
            </div>

            <!-- Önizleme -->
            <div v-else-if="uploadState === 'done'" class="upload-preview-box">
              <div class="preview-thumb">
                <img v-if="previewType === 'image'" :src="previewUrl" alt="Önizleme" class="preview-img"/>
                <video v-else :src="previewUrl" class="preview-img" muted playsinline loop autoplay></video>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-slate-200">Medya Yüklendi</p>
                <p class="text-xs text-slate-500 truncate mt-0.5">{{ form.media_url?.split('/').pop()?.slice(0, 40) || 'Dosya' }}</p>
                <span class="text-[10px] uppercase tracking-wider font-bold mt-1 inline-block" :class="previewType === 'video' ? 'text-sky-400' : 'text-emerald-400'">{{ previewType }}</span>
              </div>
              <button @click="clearMedia" class="icon-btn icon-btn-danger flex-shrink-0" title="Kaldır">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </template>

          <!-- ─ Adım 3: Hedefleme & Zamanlama ──────────────────────── -->
          <template v-if="drawerStep === 3">

            <!-- Tarih Aralığı -->
            <div>
              <label class="field-label">Yayın Tarihi Aralığı <span class="req">*</span></label>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <p class="text-[11px] text-slate-500 mb-1 font-medium">Başlangıç</p>
                  <input v-model="form.starts_at" type="datetime-local" class="field-input"/>
                </div>
                <div>
                  <p class="text-[11px] text-slate-500 mb-1 font-medium">Bitiş</p>
                  <input v-model="form.ends_at" type="datetime-local" class="field-input"/>
                </div>
              </div>
            </div>

            <!-- Gün İçi Saatler -->
            <div>
              <label class="field-label">Günlük Yayın Saatleri</label>
              <p class="text-xs text-slate-500 mb-2">Kiosk'larda hangi saatler arası gösterilecek</p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <p class="text-[11px] text-slate-500 mb-1 font-medium">Başlangıç Saati</p>
                  <input v-model="form.broadcast_start" type="time" class="field-input font-mono"/>
                </div>
                <div>
                  <p class="text-[11px] text-slate-500 mb-1 font-medium">Bitiş Saati</p>
                  <input v-model="form.broadcast_end" type="time" class="field-input font-mono"/>
                </div>
              </div>
              <!-- Zaman görsel bandı -->
              <div class="mt-2 relative h-6 bg-slate-800 rounded overflow-hidden border border-slate-700/40">
                <div
                  class="absolute top-0 h-full bg-orange-500/30 border-x border-orange-500/50"
                  :style="{
                    left: (parseInt(form.broadcast_start) / 24 * 100) + '%',
                    width: Math.max(0, (parseInt(form.broadcast_end) - parseInt(form.broadcast_start)) / 24 * 100) + '%'
                  }"
                >
                  <div class="h-full flex items-center justify-center text-[10px] font-mono text-orange-300 whitespace-nowrap overflow-hidden px-1">
                    {{ form.broadcast_start }} – {{ form.broadcast_end }}
                  </div>
                </div>
                <div class="absolute inset-0 flex pointer-events-none">
                  <div v-for="h in [0,6,12,18,24]" :key="h" class="absolute text-[8px] text-slate-600 font-mono" :style="{ left: (h/24*100) + '%', top: '50%', transform: 'translateY(-50%) translateX(-50%)' }">{{ h.toString().padStart(2,'0') }}</div>
                </div>
              </div>
            </div>

            <!-- Hedefleme Modu -->
            <div>
              <label class="field-label">Hedef Kitlesi</label>
              <div class="flex gap-2 mt-2 mb-4">
                <button
                  @click="targetMode = 'province'"
                  class="target-mode-btn flex-1"
                  :class="targetMode === 'province' ? 'target-mode-active' : 'target-mode-idle'"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
                  </svg>
                  İl Bazlı
                </button>
                <button
                  @click="targetMode = 'pharmacy'"
                  class="target-mode-btn flex-1"
                  :class="targetMode === 'pharmacy' ? 'target-mode-active' : 'target-mode-idle'"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                  </svg>
                  Eczane Bazlı
                </button>
              </div>

              <!-- İl Seçimi -->
              <div v-if="targetMode === 'province'">
                <div class="flex items-center justify-between mb-2">
                  <p class="text-xs text-slate-400">
                    <span v-if="form.target_provinces.length === 0" class="text-slate-500">Seçim yok → Tüm Türkiye'de yayınlanır</span>
                    <span v-else class="text-orange-300 font-semibold">{{ form.target_provinces.length }} il seçildi</span>
                  </p>
                  <button v-if="form.target_provinces.length > 0" @click="form.target_provinces = []" class="text-[10px] text-slate-500 hover:text-rose-400 transition">Temizle</button>
                </div>
                <input v-model="provSearch" type="text" placeholder="İl ara…" class="field-input mb-2"/>
                <div class="province-grid">
                  <button
                    v-for="prov in filteredProvinces.slice(0, 40)"
                    :key="prov"
                    @click="toggleProvince(prov)"
                    class="province-chip"
                    :class="form.target_provinces.includes(prov) ? 'province-chip-selected' : ''"
                  >{{ prov }}</button>
                </div>
                <p v-if="filteredProvinces.length > 40" class="text-[10px] text-slate-600 mt-1">+{{ filteredProvinces.length - 40 }} daha…</p>
              </div>

              <!-- Eczane Seçimi -->
              <div v-if="targetMode === 'pharmacy'">
                <div class="flex items-center justify-between mb-2">
                  <p class="text-xs text-slate-400">
                    <span v-if="form.target_pharmacy_ids.length === 0" class="text-slate-500">Eczane seçilmedi</span>
                    <span v-else class="text-orange-300 font-semibold">{{ form.target_pharmacy_ids.length }} eczane seçildi</span>
                  </p>
                  <button v-if="form.target_pharmacy_ids.length > 0" @click="form.target_pharmacy_ids = []" class="text-[10px] text-slate-500 hover:text-rose-400 transition">Temizle</button>
                </div>
                <input v-model="pharmSearch" type="text" placeholder="Eczane ara…" class="field-input mb-2"/>
                <div class="space-y-1.5">
                  <button
                    v-for="ph in filteredPharmacies"
                    :key="ph.id"
                    @click="togglePharmacy(ph.id)"
                    class="pharmacy-row"
                    :class="form.target_pharmacy_ids.includes(ph.id) ? 'pharmacy-row-selected' : ''"
                  >
                    <span class="check-circle" :class="form.target_pharmacy_ids.includes(ph.id) ? 'check-circle-on' : ''">
                      <svg v-if="form.target_pharmacy_ids.includes(ph.id)" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                      </svg>
                    </span>
                    <span class="flex-1 text-left text-sm">{{ ph.name }}</span>
                    <span class="text-xs text-slate-500">{{ ph.province }}</span>
                  </button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Drawer Footer: Navigasyon -->
        <div class="drawer-footer flex-shrink-0 flex items-center gap-3">
          <button
            v-if="drawerStep > 1"
            @click="prevStep"
            class="flex items-center gap-1 px-4 py-2.5 text-sm text-slate-400 hover:text-slate-200 border border-slate-700 hover:border-slate-500 rounded-lg transition"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
            </svg>
            Geri
          </button>
          <button v-if="drawerStep < 3" @click="nextStep" :disabled="!stepValid" class="flex-1 next-btn" :class="!stepValid ? 'opacity-40 cursor-not-allowed' : ''">
            İleri
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
          <button v-else @click="saveForm" :disabled="drawerSaving" class="flex-1 save-btn">
            <svg v-if="drawerSaving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
            {{ drawerSaving ? 'Kaydediliyor…' : (drawerMode === 'create' ? 'Kampanyayı Oluştur' : 'Güncelle') }}
          </button>
        </div>
      </aside>
    </Transition>
  </Teleport>

  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!-- SİLME ONAY MODAL                                                       -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div v-if="deleteTarget" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" @click.self="deleteTarget = null">
        <Transition name="modal" appear>
          <div v-if="deleteTarget" class="delete-modal w-full max-w-sm">
            <div class="p-6 text-center">
              <div class="w-12 h-12 rounded-full bg-rose-900/40 border border-rose-700/30 flex items-center justify-center mx-auto mb-4">
                <svg class="w-6 h-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </div>
              <h3 class="text-sm font-bold text-slate-100 mb-1">Kampanyayı Sil</h3>
              <p class="text-xs text-slate-400 leading-relaxed">
                <span class="text-slate-200 font-semibold">"{{ deleteTarget?.name }}"</span> kampanyası kalıcı olarak silinecek.
              </p>
            </div>
            <div class="px-6 pb-5 flex gap-2.5">
              <button @click="deleteTarget = null" :disabled="deleting" class="flex-1 py-2 text-sm text-slate-400 border border-slate-700 rounded-lg hover:border-slate-500 transition disabled:opacity-50">Vazgeç</button>
              <button @click="confirmDelete" :disabled="deleting" class="flex-1 flex items-center justify-center gap-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-bold py-2 rounded-lg transition">
                <svg v-if="deleting" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                {{ deleting ? 'Siliniyor…' : 'Sil' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@600;700&family=Fira+Code:wght@400;500&display=swap');

/* ══ Root ════════════════════════════════════════════════════════════════════ */
.cm-root {
  background: #0b0f18;
  color: #cbd5e1;
  font-family: 'Barlow', system-ui, sans-serif;
}

/* ══ Typography ══════════════════════════════════════════════════════════════ */
.eyebrow {
  font-family: 'Barlow Condensed', sans-serif;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  font-size: 11px;
  color: #f97316;
}

.page-title {
  font-family: 'Playfair Display', serif;
  font-weight: 800;
  font-size: 1.75rem;
  color: #f1f5f9;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

/* ══ Top Bar ═════════════════════════════════════════════════════════════════ */
.cm-topbar {
  background: linear-gradient(180deg, #0d1120 0%, #0b0f18 100%);
}

/* ══ CTA Button ══════════════════════════════════════════════════════════════ */
.cta-btn {
  background: #f97316;
  color: #0b0f18;
  font-family: 'Barlow', sans-serif;
  font-weight: 700;
  font-size: 13px;
  padding: 10px 18px;
  border-radius: 10px;
  transition: background 0.15s, transform 0.1s;
  box-shadow: 0 4px 20px rgba(249, 115, 22, 0.3);
  letter-spacing: 0.01em;
}
.cta-btn:hover { background: #fb923c; transform: translateY(-1px); }
.cta-btn:active { transform: translateY(0); }

/* ══ KPI Cards ═══════════════════════════════════════════════════════════════ */
.kpi-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 14px;
  padding: 16px 20px;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.kpi-value {
  font-family: 'Playfair Display', serif;
  font-size: 2.2rem;
  font-weight: 800;
  color: #f1f5f9;
  line-height: 1;
  margin: 4px 0 2px;
}
.kpi-sub { font-size: 11px; color: #475569; }
.kpi-skeleton { display: inline-block; width: 40px; height: 32px; background: rgba(51, 65, 85, 0.5); border-radius: 4px; animation: pulse 1.5s ease infinite; }

/* ══ Tabs ════════════════════════════════════════════════════════════════════ */
.tab-btn { padding-bottom: 12px; }
.tab-active { color: #f1f5f9; }
.tab-underline {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #f97316;
  border-radius: 1px 1px 0 0;
}
.tab-count {
  background: rgba(51, 65, 85, 0.6);
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
}

/* ══ Campaign Card ═══════════════════════════════════════════════════════════ */
.camp-card {
  display: flex;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 16px;
  overflow: hidden;
  animation: card-in 0.3s ease both;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.camp-card:hover {
  border-color: rgba(249, 115, 22, 0.25);
  box-shadow: 0 4px 24px rgba(249, 115, 22, 0.06);
}
@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.camp-media-thumb {
  width: 80px;
  background: #0f172a;
  flex-shrink: 0;
}

.camp-name {
  font-family: 'Barlow', sans-serif;
  font-weight: 700;
  font-size: 15px;
  color: #f1f5f9;
  line-height: 1.2;
}
.camp-client {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.duration-badge {
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #f97316;
  background: rgba(249, 115, 22, 0.12);
  border: 1px solid rgba(249, 115, 22, 0.25);
  padding: 2px 8px;
  border-radius: 999px;
}

/* ══ Progress ════════════════════════════════════════════════════════════════ */
.progress-track {
  height: 4px;
  background: rgba(51, 65, 85, 0.6);
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f97316, #fb923c);
  border-radius: 2px;
  transition: width 0.5s ease;
}
.progress-fill-upload {
  height: 100%;
  background: linear-gradient(90deg, #f97316, #fb923c);
  border-radius: 2px;
  transition: width 0.1s linear;
}

/* ══ Icon Buttons ════════════════════════════════════════════════════════════ */
.icon-btn {
  padding: 6px;
  color: #475569;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.icon-btn:hover { color: #94a3b8; background: rgba(51, 65, 85, 0.5); }
.icon-btn-danger:hover { color: #f87171; background: rgba(239, 68, 68, 0.1); }

/* ══ Drawer ══════════════════════════════════════════════════════════════════ */
.cm-drawer {
  width: 460px;
  background: #0d1120;
  border-left: 1px solid rgba(51, 65, 85, 0.5);
}

.drawer-head {
  padding: 24px 24px 20px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  background: rgba(13, 17, 32, 0.9);
  backdrop-filter: blur(12px);
}

.drawer-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(51, 65, 85, 0.4);
  background: rgba(13, 17, 32, 0.9);
}

/* ══ Step Dots ═══════════════════════════════════════════════════════════════ */
.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-dot-active  { background: #f97316; color: white; }
.step-dot-done    { background: rgba(249, 115, 22, 0.25); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4); }
.step-dot-idle    { background: rgba(51, 65, 85, 0.5); color: #475569; }

/* ══ Form Fields ═════════════════════════════════════════════════════════════ */
.field-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 6px;
}
.req { color: #f87171; }
.field-input {
  width: 100%;
  background: #131b2e;
  border: 1px solid rgba(51, 65, 85, 0.7);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 13px;
  padding: 9px 12px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: 'Barlow', sans-serif;
}
.field-input:focus {
  border-color: rgba(249, 115, 22, 0.5);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.08);
}
.field-input[type="time"],
.field-input[type="datetime-local"] {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  color-scheme: dark;
}

/* ══ Duration Display ════════════════════════════════════════════════════════ */
.duration-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 52px;
  background: rgba(249, 115, 22, 0.1);
  border: 1px solid rgba(249, 115, 22, 0.2);
  border-radius: 8px;
  padding: 6px 10px;
}

/* ══ Drop Zone ═══════════════════════════════════════════════════════════════ */
.drop-zone {
  border: 2px dashed rgba(51, 65, 85, 0.7);
  border-radius: 16px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  background: rgba(13, 17, 32, 0.5);
}
.drop-zone:hover, .drop-zone-active {
  border-color: rgba(249, 115, 22, 0.5);
  background: rgba(249, 115, 22, 0.04);
}
.drop-icon {
  width: 56px;
  height: 56px;
  background: rgba(51, 65, 85, 0.4);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}

.upload-progress-box {
  background: #131b2e;
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 12px;
  padding: 16px;
}

.upload-preview-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #131b2e;
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 12px;
  padding: 12px;
}
.preview-thumb {
  width: 60px;
  height: 90px;
  border-radius: 6px;
  overflow: hidden;
  background: #0b0f18;
  flex-shrink: 0;
}
.preview-img { width: 100%; height: 100%; object-fit: cover; }

/* ══ Error Banner ════════════════════════════════════════════════════════════ */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(153, 27, 27, 0.2);
  border: 1px solid rgba(248, 113, 113, 0.25);
  color: #fca5a5;
  font-size: 13px;
  padding: 10px 12px;
  border-radius: 8px;
}

/* ══ Target Mode Buttons ═════════════════════════════════════════════════════ */
.target-mode-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.15s;
}
.target-mode-active {
  background: rgba(249, 115, 22, 0.15);
  border: 1px solid rgba(249, 115, 22, 0.4);
  color: #f97316;
}
.target-mode-idle {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(51, 65, 85, 0.5);
  color: #64748b;
}
.target-mode-idle:hover { border-color: rgba(100, 116, 139, 0.6); color: #94a3b8; }

/* ══ Province Grid ═══════════════════════════════════════════════════════════ */
.province-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  padding: 2px;
}
.province-chip {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(51, 65, 85, 0.5);
  background: rgba(30, 41, 59, 0.5);
  color: #64748b;
  transition: all 0.12s;
  cursor: pointer;
  white-space: nowrap;
}
.province-chip:hover { border-color: rgba(100, 116, 139, 0.6); color: #94a3b8; }
.province-chip-selected {
  background: rgba(249, 115, 22, 0.15) !important;
  border-color: rgba(249, 115, 22, 0.45) !important;
  color: #f97316 !important;
}

/* ══ Pharmacy Rows ═══════════════════════════════════════════════════════════ */
.pharmacy-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid rgba(51, 65, 85, 0.4);
  background: rgba(30, 41, 59, 0.3);
  color: #64748b;
  transition: all 0.12s;
  cursor: pointer;
}
.pharmacy-row:hover { border-color: rgba(100, 116, 139, 0.5); color: #94a3b8; }
.pharmacy-row-selected {
  background: rgba(249, 115, 22, 0.08) !important;
  border-color: rgba(249, 115, 22, 0.35) !important;
  color: #e2e8f0 !important;
}
.check-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid rgba(51, 65, 85, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.12s;
}
.check-circle-on {
  background: #f97316;
  border-color: #f97316;
  color: white;
}

/* ══ Footer Buttons ══════════════════════════════════════════════════════════ */
.next-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  background: rgba(249, 115, 22, 0.15);
  border: 1px solid rgba(249, 115, 22, 0.35);
  color: #f97316;
  font-weight: 700;
  font-size: 13px;
  border-radius: 10px;
  transition: all 0.15s;
}
.next-btn:hover { background: rgba(249, 115, 22, 0.22); }

.save-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  background: #f97316;
  color: #0b0f18;
  font-weight: 800;
  font-size: 13px;
  border-radius: 10px;
  transition: background 0.15s;
  box-shadow: 0 4px 16px rgba(249, 115, 22, 0.3);
}
.save-btn:hover { background: #fb923c; }
.save-btn:disabled { background: #1e293b; color: #475569; box-shadow: none; }

/* ══ Delete Modal ════════════════════════════════════════════════════════════ */
.delete-modal {
  background: #0d1120;
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 20px;
  overflow: hidden;
}

/* ══ Transitions ═════════════════════════════════════════════════════════════ */
.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.2s ease; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }

.drawer-enter-active, .drawer-leave-active { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }

.modal-enter-active { transition: opacity 0.2s ease, transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.93) translateY(10px); }

/* ══ Misc ════════════════════════════════════════════════════════════════════ */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(51, 65, 85, 0.5); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(249, 115, 22, 0.4); }
</style>
