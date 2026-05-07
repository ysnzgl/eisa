<script setup>
/**
 * Reklam Yöneticisi — DOOH Idle-Screen Reklam Modülü
 * Modül 3: Reklam oluşturma, hedefleme, sekmeli liste
 */
import { ref, computed, onMounted } from 'vue';
import {
  getCampaigns,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  campaignStatus,
  getPharmaciesForTargeting,
  uploadMedia,
} from '../../services/campaignManager';

//  Veriler 
const allCampaigns   = ref([]);
const allPharmacies  = ref([]);
const loadingList    = ref(true);
const activeTab      = ref('active');   // 'active' | 'upcoming' | 'ended'

//  Drawer (Oluştur/Düzenle) 
const drawerOpen     = ref(false);
const drawerMode     = ref('create');   // 'create' | 'edit'
const editingId      = ref(null);
const drawerStep     = ref(1);          // 1: Temel Bilgi, 2: Medya, 3: Hedefleme
const drawerSaving   = ref(false);
const drawerError    = ref('');

//  Form 
const EMPTY_FORM = () => ({
  name:               '',
  client:             '',
  duration_sec:       15,
  media_url:          '',
  starts_at:          '',
  ends_at:            '',
  broadcast_start:    '08:00',
  broadcast_end:      '22:00',
  target_pharmacy_ids: [],
  is_active:          true,
});
const form = ref(EMPTY_FORM());

//  Hedefleme UI 
const pharmSearch    = ref('');

//  Medya yükleme 
const fileInputRef   = ref(null);
const isDragOver     = ref(false);
const uploading      = ref(false);

function triggerFileInput() { fileInputRef.value?.click(); }

async function handleFileChange(e) {
  const file = e.target.files?.[0];
  if (file) await doUpload(file);
  e.target.value = '';   // allow re-select same file
}

async function handleDrop(e) {
  isDragOver.value = false;
  const file = e.dataTransfer.files?.[0];
  if (file) await doUpload(file);
}

async function doUpload(file) {
  const allowed = ['image/jpeg','image/png','image/gif','image/webp','video/mp4','video/webm'];
  if (!allowed.includes(file.type)) {
    drawerError.value = 'Desteklenmeyen tür. JPEG, PNG, GIF, WebP, MP4 veya WebM yükleyin.';
    return;
  }
  uploading.value = true;
  drawerError.value = '';
  try {
    form.value.media_url = await uploadMedia(file);
  } catch {
    drawerError.value = 'Dosya yüklenemedi. Lütfen tekrar deneyin.';
  } finally {
    uploading.value = false;
  }
}

function isVideo(url) { return /\.(mp4|webm|ogg)(\?|$)/i.test(url); }

//  Silme onay 
const deleteTarget   = ref(null);
const deleting       = ref(false);

//  Computed 
const tabCounts = computed(() => ({
  active:   allCampaigns.value.filter((c) => campaignStatus(c) === 'active').length,
  upcoming: allCampaigns.value.filter((c) => campaignStatus(c) === 'upcoming').length,
  ended:    allCampaigns.value.filter((c) => campaignStatus(c) === 'ended').length,
}));

const visibleCampaigns = computed(() =>
  allCampaigns.value.filter((c) => campaignStatus(c) === activeTab.value)
);

const filteredPharmacies = computed(() =>
  allPharmacies.value.filter((p) =>
    p.name.toLowerCase().includes(pharmSearch.value.toLowerCase()) ||
    (p.province ?? '').toLowerCase().includes(pharmSearch.value.toLowerCase())
  )
);

const stepValid = computed(() => {
  if (drawerStep.value === 1) return form.value.name.trim() && form.value.client.trim() && form.value.duration_sec > 0;
  if (drawerStep.value === 2) return !!form.value.media_url && !uploading.value;
  return true;
});

//  Yükleme 
async function loadCampaigns() {
  loadingList.value = true;
  try { allCampaigns.value = await getCampaigns(); }
  finally { loadingList.value = false; }
}

onMounted(async () => {
  const [, pharms] = await Promise.all([loadCampaigns(), getPharmaciesForTargeting()]);
  allPharmacies.value = pharms;
});

//  Drawer 
function openCreate() {
  form.value    = EMPTY_FORM();
  drawerStep.value = 1;
  drawerMode.value = 'create';
  editingId.value  = null;
  drawerError.value = '';
  drawerOpen.value = true;
}

function openEdit(c) {
  form.value = {
    name:               c.name,
    client:             c.client,
    duration_sec:       c.duration_sec,
    media_url:          c.media_url,
    starts_at:          toDateInput(c.starts_at),
    ends_at:            toDateInput(c.ends_at),
    broadcast_start:    c.broadcast_start ?? '08:00',
    broadcast_end:      c.broadcast_end   ?? '22:00',
    target_pharmacy_ids: [...(c.target_pharmacy_ids ?? [])],
    is_active:          c.is_active,
  };
  drawerStep.value  = 1;
  drawerMode.value  = 'edit';
  editingId.value   = c.id;
  drawerError.value = '';
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
    if (drawerMode.value === 'create') {
      await createCampaign({ ...form.value });
    } else {
      await updateCampaign(editingId.value, { ...form.value });
    }
    await loadCampaigns();
    closeDrawer();
  } catch { drawerError.value = 'Kayıt başarısız. Lütfen tekrar deneyin.'; }
  finally { drawerSaving.value = false; }
}

//  Hedefleme 
function togglePharmacy(id) {
  const idx = form.value.target_pharmacy_ids.indexOf(id);
  if (idx === -1) form.value.target_pharmacy_ids.push(id);
  else form.value.target_pharmacy_ids.splice(idx, 1);
}

//  Silme 
async function confirmDelete() {
  deleting.value = true;
  try {
    await deleteCampaign(deleteTarget.value.id);
    await loadCampaigns();
    deleteTarget.value = null;
  } finally { deleting.value = false; }
}

//  Helpers 
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
  return 'Tüm Eczaneler';
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
  { key: 'upcoming', label: 'Yaklaşan',   dot: 'bg-blue-400'  },
  { key: 'ended',    label: 'Tamamlandı', dot: 'bg-gray-400'  },
];
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap');

/* ─── Root ──────────────────────────────────────────── */
.cm-root {
  background: #F2F1EE;
  color: #111827;
  font-family: 'Syne', system-ui, sans-serif;
}

/* ─── Topbar ─────────────────────────────────────────── */
.cm-topbar {
  background: rgba(255,255,255,0.97);
  backdrop-filter: blur(12px);
}

.eyebrow {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2563EB;
}

/* ─── KPI Cards ──────────────────────────────────────── */
.kpi-card {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 12px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 140px;
}
.kpi-num {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.kpi-sub {
  font-size: 10px;
  color: #9CA3AF;
  margin-top: 1px;
}

/* ─── Tabs ───────────────────────────────────────────── */
.tab-btn {
  color: #9CA3AF;
  position: relative;
}
.tab-active {
  color: #111827;
}
.tab-underline {
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #2563EB;
  border-radius: 2px 2px 0 0;
}
.tab-count {
  font-size: 11px;
  font-weight: 700;
  background: #F3F4F6;
  color: #6B7280;
  border-radius: 9999px;
  padding: 1px 7px;
}
.tab-active .tab-count {
  background: #EFF6FF;
  color: #2563EB;
}

/* ─── Campaign Cards ─────────────────────────────────── */
.camp-card {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  gap: 14px;
  transition: box-shadow 0.15s, transform 0.15s;
  cursor: pointer;
}
.camp-card:hover {
  box-shadow: 0 4px 18px rgba(0,0,0,0.07);
  transform: translateY(-1px);
}
.camp-media-thumb {
  width: 80px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: #F3F4F6;
  flex-shrink: 0;
}
.camp-name {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  line-height: 1.3;
}
.camp-client {
  font-size: 12px;
  color: #6B7280;
  margin-top: 2px;
}

/* ─── Icon Buttons ───────────────────────────────────── */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid #E5E3DF;
  color: #6B7280;
  background: #FFFFFF;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  cursor: pointer;
  font-size: 13px;
}
.icon-btn:hover {
  background: #F3F4F6;
  color: #111827;
  border-color: #D1D5DB;
}
.icon-btn-danger:hover {
  background: #FEE2E2;
  color: #DC2626;
  border-color: #FECACA;
}

/* ─── Progress Bar ───────────────────────────────────── */
.progress-track {
  height: 4px;
  background: #E5E7EB;
  border-radius: 2px;
  overflow: hidden;
  flex: 1;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563EB, #3B82F6);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* ─── Drawer ─────────────────────────────────────────── */
.cm-drawer {
  width: 420px;
  background: #FFFFFF;
  border-left: 1px solid #E5E3DF;
  box-shadow: -6px 0 32px rgba(0,0,0,0.08);
}
.drawer-head {
  padding: 20px 24px 16px;
  border-bottom: 1px solid #E5E3DF;
  background: #FAFAF9;
}
.drawer-footer {
  padding: 16px 24px;
  border-top: 1px solid #E5E3DF;
  background: #FAFAF9;
}

/* ─── Error Banner ───────────────────────────────────── */
.error-banner {
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: #DC2626;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}

/* ─── Form Fields ────────────────────────────────────── */
.field-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6B7280;
  margin-bottom: 6px;
}
.field-input {
  width: 100%;
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 8px;
  color: #111827;
  font-size: 13px;
  padding: 9px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
  outline: none;
}
.field-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.10);
}
.req {
  color: #DC2626;
  margin-left: 2px;
}

/* ─── Upload Zone ────────────────────────────────────── */
.upload-zone {
  border: 2px dashed #D1D5DB;
  border-radius: 12px;
  padding: 32px 24px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: #FAFAFA;
}
.upload-zone:hover,
.upload-zone-over {
  border-color: #2563EB;
  background: #EFF6FF;
}
.upload-zone-done {
  border-color: #10B981;
  background: #ECFDF5;
}

/* ─── Pharmacy Rows ──────────────────────────────────── */
.pharmacy-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
  border: 1px solid transparent;
}
.pharmacy-row:hover {
  background: #F3F4F6;
}
.pharmacy-row-selected {
  background: #EFF6FF;
  border-color: #BFDBFE;
}

/* ─── Action Buttons ─────────────────────────────────── */
.next-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.next-btn:hover { opacity: 0.9; }
.save-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.save-btn:hover { opacity: 0.9; }
.save-btn:disabled, .next-btn:disabled { opacity: 0.45; cursor: not-allowed; }

/* ─── Delete Modal ───────────────────────────────────── */
.delete-modal {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
}

/* ─── Page Title & CTA ───────────────────────────────── */
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
  margin: 0;
}
.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 18px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.cta-btn:hover { opacity: 0.9; }

/* ─── KPI Value / Skeleton ───────────────────────────── */
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
  margin-top: 2px;
}
.kpi-skeleton {
  display: block;
  width: 40px;
  height: 22px;
  background: #E5E7EB;
  border-radius: 4px;
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ─── Duration Badge & Display ───────────────────────── */
.duration-badge {
  font-size: 11px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  background: #EFF6FF;
  color: #2563EB;
  border-radius: 6px;
  padding: 2px 7px;
  border: 1px solid #BFDBFE;
  flex-shrink: 0;
}
.duration-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 8px;
  padding: 6px 10px;
}

/* ─── Preview Media ──────────────────────────────────── */
.preview-media {
  max-width: 100%;
  max-height: 160px;
  border-radius: 8px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}

/* ─── Check Circle ───────────────────────────────────── */
.check-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid #D1D5DB;
  background: #FFFFFF;
  flex-shrink: 0;
  transition: border-color 0.15s, background 0.15s;
}
.check-circle-on {
  border-color: #2563EB;
  background: #2563EB;
}

/* ─── Transitions ────────────────────────────────────── */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>

<template>
  <div class="cm-root min-h-screen">

    <!--  -->
    <!-- ÜST: Sayfa Bal + CTA                                             -->
    <!--  -->
    <div class="cm-topbar px-8 py-6 flex items-start justify-between border-b border-gray-200">
      <div>
        <p class="eyebrow mb-1">Kiosk Yayın Sistemi</p>
        <h1 class="page-title">Reklam Yöneticisi</h1>
        <p class="text-sm text-gray-500 mt-1 font-light tracking-wide">Idle-screen reklam içeriklerini planlayın, hedefleyin ve izleyin.</p>
      </div>
      <button @click="openCreate" class="cta-btn flex items-center gap-2.5">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        <span>Yeni Reklam</span>
      </button>
    </div>

    <!--  -->
    <!-- ÖZET KPI BANDI                                                        -->
    <!--  -->
    <div class="px-8 py-5 grid grid-cols-3 gap-4 border-b border-gray-200">
      <div v-for="tab in TAB_CONFIG" :key="tab.key" class="kpi-card">
        <div class="flex items-center gap-2 mb-1">
          <span class="w-2 h-2 rounded-full flex-shrink-0" :class="tab.dot"></span>
          <span class="kpi-label">{{ tab.label }}</span>
        </div>
        <div class="kpi-value">
          <span v-if="loadingList" class="kpi-skeleton"></span>
          <span v-else>{{ tabCounts[tab.key] }}</span>
        </div>
        <p class="kpi-sub">REKLAM</p>
      </div>
    </div>

    <!--  -->
    <!-- SEKME + LISTE                                                          -->
    <!--  -->
    <div class="px-8 pt-6 pb-10">
      <!-- Sekmeler -->
      <div class="flex items-center gap-1 mb-6 border-b border-gray-200 pb-0">
        <button
          v-for="tab in TAB_CONFIG"
          :key="tab.key"
          @click="activeTab = tab.key"
          class="tab-btn relative flex items-center gap-2 px-4 py-2.5 text-sm font-semibold transition-colors duration-150"
          :class="activeTab === tab.key ? 'tab-active' : 'text-gray-400 hover:text-gray-700'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="tab.dot"></span>
          {{ tab.label }}
          <span class="tab-count">{{ tabCounts[tab.key] }}</span>
          <span v-if="activeTab === tab.key" class="tab-underline"></span>
        </button>
      </div>

      <!-- Yükleniyor -->
      <div v-if="loadingList" class="space-y-3">
        <div v-for="n in 3" :key="n" class="h-28 bg-gray-200 rounded-2xl animate-pulse"></div>
      </div>

      <!-- Bo durum -->
      <div v-else-if="visibleCampaigns.length === 0"
        class="flex flex-col items-center justify-center py-20 text-gray-400"
      >
        <svg class="w-14 h-14 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.854V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2h14a2 2 0 002-2v-1.854a1 1 0 00-.553-.894L15 14M15 10v4"/>
        </svg>
        <p class="text-sm font-medium">Bu sekme için reklam bulunamadı.</p>
        <button v-if="activeTab !== 'ended'" @click="openCreate" class="mt-3 text-blue-600 text-sm hover:text-blue-700 underline underline-offset-2">İlk Reklamı Oluştur</button>
      </div>

      <!-- Reklam Kartlar -->
      <div v-else class="space-y-4">
        <div
          v-for="(c, ci) in visibleCampaigns"
          :key="c.id"
          class="camp-card group"
          :style="{ animationDelay: ci * 50 + 'ms' }"
        >
          <!-- Media önizleme eridi -->
          <div class="camp-media-thumb flex-shrink-0">
            <img
              v-if="c.media_type === 'image'"
              :src="c.media_url"
              alt=""
              class="w-full h-full object-cover"
              @error="$event.target.src='https://placehold.co/100x180/1e293b/334155?text='"
            />
            <div v-else class="w-full h-full flex items-center justify-center bg-gray-100">
              <svg class="w-6 h-6 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>

          <!-- Ana İçerik -->
          <div class="flex-1 min-w-0 py-4 pr-4">
            <!-- Balk satr -->
            <div class="flex items-start justify-between gap-4 mb-2">
              <div>
                <h3 class="camp-name">{{ c.name }}</h3>
                <p class="camp-client">{{ c.client }}</p>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0 pt-0.5">
                <!-- Yayn süresi badge -->
                <span class="duration-badge">{{ c.duration_sec }}s</span>
                <!-- Aksiyon butonlar -->
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
            <div class="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-gray-500 mb-3">
              <!-- Tarih aral -->
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                {{ fmtDateShort(c.starts_at) }} — {{ fmtDateShort(c.ends_at) }}
              </span>
              <!-- Yayn saatleri -->
              <span class="flex items-center gap-1 font-mono">
                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                {{ c.broadcast_start }} — {{ c.broadcast_end }}
              </span>
              <!-- Hedefleme -->
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                {{ targetSummary(c) }}
              </span>
            </div>

            <!-- lerleme çubuğu (aktif REKLAMlar) -->
            <template v-if="campaignStatus(c) === 'active'">
              <div class="flex items-center gap-3">
                <div class="flex-1 progress-track">
                  <div class="progress-fill" :style="{ width: progressDays(c) + '%' }"></div>
                </div>
                <span class="text-xs text-blue-600 font-mono flex-shrink-0">{{ daysLeft(c) }}</span>
              </div>
            </template>
            <!-- Yaklaan REKLAMlar -->
            <template v-else-if="campaignStatus(c) === 'upcoming'">
              <span class="text-xs text-blue-600 font-mono">{{ daysUntil(c) }}</span>
            </template>
            <!-- Biten REKLAMlar -->
            <template v-else>
              <span class="text-xs text-gray-500 font-mono">{{ fmtDate(c.ends_at) }} tarihinde tamamlandı</span>
            </template>
          </div>
        </div>
      </div>
    </div>

  </div><!-- /cm-root -->


  <!--  -->
  <!-- Reklam DRAWER                                                        -->
  <!--  -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div v-if="drawerOpen" class="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm" @click="closeDrawer"></div>
    </Transition>
    <Transition name="drawer">
      <aside v-if="drawerOpen" class="cm-drawer fixed right-0 top-0 h-full z-50 flex flex-col">

        <!-- Drawer Balk + Admlar -->
        <div class="drawer-head flex-shrink-0">
          <div class="flex items-center justify-between mb-4">
            <div>
              <p class="eyebrow text-xs">{{ drawerMode === 'create' ? 'Yeni Reklam' : 'Reklam Düzenle' }}</p>
              <h2 class="text-base font-bold text-gray-900 tracking-tight">
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
            <div class="flex-1 h-px bg-gray-200 mx-1"></div>
            <span class="text-xs text-gray-400">{{ drawerStep }}/3</span>
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

          <!--  Adm 1: Temel Bilgiler  -->
          <template v-if="drawerStep === 1">
            <div>
              <label class="field-label">Reklam Adı <span class="req">*</span></label>
              <input v-model="form.name" type="text" placeholder="Bahar Vitamin Reklamı" class="field-input"/>
            </div>
            <div>
              <label class="field-label">Müşteri / Firma Adı <span class="req">*</span></label>
              <input v-model="form.client" type="text" placeholder="Eczacıbaşı Sağlık A.Ş." class="field-input"/>
            </div>
            <div>
              <label class="field-label">Ekranda Kalma Süresi <span class="req">*</span></label>
              <p class="text-xs text-gray-500 mb-2">Her dönüşte kaç saniye gösterilecek</p>
              <div class="flex items-center gap-4">
                <input
                  v-model.number="form.duration_sec"
                  type="range" min="5" max="60" step="1"
                  class="flex-1 accent-blue-600 cursor-pointer"
                />
                <div class="duration-display">
                  <span class="text-2xl font-black text-blue-600 leading-none">{{ form.duration_sec }}</span>
                  <span class="text-xs text-gray-500 leading-none">sn</span>
                </div>
              </div>
              <div class="flex justify-between text-[10px] text-gray-500 mt-1 font-mono">
                <span>5s</span><span>15s</span><span>30s</span><span>45s</span><span>60s</span>
              </div>
            </div>

            <!-- Aktif olarak yaynla toggle -->
            <div class="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
              <div>
                <p class="text-sm font-semibold text-gray-800">Aktif Olarak Yayınla</p>
                <p class="text-xs text-gray-500">Kapalıysa taslak olarak kaydedilir</p>
              </div>
              <button
                @click="form.is_active = !form.is_active"
                class="relative inline-flex items-center w-11 h-6 rounded-full transition-colors duration-200 flex-shrink-0"
                :class="form.is_active ? 'bg-blue-600' : 'bg-gray-300'"
              >
                <span class="inline-block w-4 h-4 bg-white rounded-full shadow transition-transform duration-200" :class="form.is_active ? 'translate-x-6' : 'translate-x-1'"></span>
              </button>
            </div>
          </template>

          <!--  Adım 2: Medya Yükle  -->
          <template v-if="drawerStep === 2">
            <!-- Hidden file input -->
            <input
              ref="fileInputRef"
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/webm"
              class="hidden"
              @change="handleFileChange"
            />

            <!-- Upload zone -->
            <div
              class="upload-zone"
              :class="{
                'upload-zone-over': isDragOver,
                'upload-zone-done': form.media_url && !uploading,
              }"
              @click="triggerFileInput"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
            >
              <!-- Uploading state -->
              <template v-if="uploading">
                <svg class="animate-spin w-8 h-8 text-blue-600 mb-3" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                <p class="text-sm font-semibold text-gray-500">Yükleniyor…</p>
                <p class="text-xs text-gray-400 mt-1">Lütfen bekleyin</p>
              </template>

              <!-- Uploaded state -->
              <template v-else-if="form.media_url">
                <video
                  v-if="isVideo(form.media_url)"
                  :src="form.media_url"
                  class="preview-media mb-2"
                  muted playsinline loop autoplay
                ></video>
                <img
                  v-else
                  :src="form.media_url"
                  alt="önizleme"
                  class="preview-media mb-2"
                  @error="$event.target.style.display='none'"
                />
                <p class="text-xs font-semibold text-emerald-600"> Dosya yüklendi</p>
                <p class="text-xs text-gray-400 mt-0.5">Değiştirmek için tıkla veya sürükle</p>
              </template>

              <!-- Empty state -->
              <template v-else>
                <svg class="w-10 h-10 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
                </svg>
                <p class="text-sm font-semibold text-gray-600">Dosya seç veya sürükle bırak</p>
                <p class="text-xs text-gray-400 mt-1.5">JPEG • PNG • WebP • GIF • MP4 • WebM</p>
                <p class="text-xs text-gray-400">Maksimum dosya boyutu: 100 MB</p>
              </template>
            </div>
          </template>

          <!--  Adm 3: Hedefleme & Zamanlama  -->
          <template v-if="drawerStep === 3">

            <!-- Tarih Aral -->
            <div>
              <label class="field-label">Yayın Tarihi Aralığı <span class="req">*</span></label>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <p class="text-[11px] text-gray-500 mb-1 font-medium">Başlangıç</p>
                  <input v-model="form.starts_at" type="datetime-local" class="field-input"/>
                </div>
                <div>
                  <p class="text-[11px] text-gray-500 mb-1 font-medium">Bitiş</p>
                  <input v-model="form.ends_at" type="datetime-local" class="field-input"/>
                </div>
              </div>
            </div>

          <!-- Gün İçi Saatler -->
            <div>
              <label class="field-label">Günlük Yayın Saatleri</label>
              <p class="text-xs text-gray-500 mb-2">Kiosk'larda hangi saatler arası gösterilecek</p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <p class="text-[11px] text-gray-500 mb-1 font-medium">Başlangıç Saati</p>
                  <input v-model="form.broadcast_start" type="time" class="field-input font-mono"/>
                </div>
                <div>
                  <p class="text-[11px] text-gray-500 mb-1 font-medium">Bitiş Saati</p>
                  <input v-model="form.broadcast_end" type="time" class="field-input font-mono"/>
                </div>
              </div>
              <!-- Zaman görsel bandı -->
              <div class="mt-2 relative h-6 bg-gray-100 rounded overflow-hidden border border-gray-200">
                <div
                  class="absolute top-0 h-full bg-blue-500/30 border-x border-blue-500/50"
                  :style="{
                    left: (parseInt(form.broadcast_start) / 24 * 100) + '%',
                    width: Math.max(0, (parseInt(form.broadcast_end) - parseInt(form.broadcast_start)) / 24 * 100) + '%'
                  }"
                >
                  <div class="h-full flex items-center justify-center text-[10px] font-mono text-blue-700 whitespace-nowrap overflow-hidden px-1">
                    {{ form.broadcast_start }} — {{ form.broadcast_end }}
                  </div>
                </div>
                <div class="absolute inset-0 flex pointer-events-none">
                  <div v-for="h in [0,6,12,18,24]" :key="h" class="absolute text-[8px] text-gray-500 font-mono" :style="{ left: (h/24*100) + '%', top: '50%', transform: 'translateY(-50%) translateX(-50%)' }">{{ h.toString().padStart(2,'0') }}</div>
                </div>
              </div>
            </div>

            <!-- Eczane Seçimi -->
            <div>
              <label class="field-label">Hedef Eczaneler</label>
              <div class="flex items-center justify-between mb-2">
                <p class="text-xs text-gray-500">
                  <span v-if="form.target_pharmacy_ids.length === 0" class="text-gray-500">Seçim yok — Tüm eczanelerde yayınlanır</span>
                  <span v-else class="text-blue-600 font-semibold">{{ form.target_pharmacy_ids.length }} eczane seçildi</span>
                </p>
                <button v-if="form.target_pharmacy_ids.length > 0" @click="form.target_pharmacy_ids = []" class="text-[10px] text-gray-500 hover:text-rose-500 transition">Temizle</button>
              </div>
              <input v-model="pharmSearch" type="text" placeholder="Eczane ara…" class="field-input mb-2"/>
              <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                <div v-if="allPharmacies.length === 0" class="text-xs text-gray-500 py-4 text-center">Eczaneler yükleniyor…</div>
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
                  <span class="text-xs text-gray-500">{{ ph.province }}</span>
                </button>
              </div>
            </div>
          </template>
        </div>

        <!-- Drawer Footer: Navigasyon -->
        <div class="drawer-footer flex-shrink-0 flex items-center gap-3">
          <button
            v-if="drawerStep > 1"
            @click="prevStep"
            class="flex items-center gap-1 px-4 py-2.5 text-sm text-gray-500 hover:text-gray-800 border border-gray-200 hover:border-gray-400 rounded-lg transition"
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
            {{ drawerSaving ? 'Kaydediliyor…' : (drawerMode === 'create' ? 'Reklam Oluştur' : 'Güncelle') }}
          </button>
        </div>
      </aside>
    </Transition>
  </Teleport>

  <!--  -->
  <!-- SLME ONAY MODAL                                                       -->
  <!--  -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div v-if="deleteTarget" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" @click.self="deleteTarget = null">
        <Transition name="modal" appear>
          <div v-if="deleteTarget" class="delete-modal w-full max-w-sm">
            <div class="p-6 text-center">
              <div class="w-12 h-12 rounded-full bg-rose-100 border border-rose-200 flex items-center justify-center mx-auto mb-4">
                <svg class="w-6 h-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </div>
              <h3 class="text-sm font-bold text-gray-800 mb-1">Reklamı Sil</h3>
              <p class="text-xs text-gray-500 leading-relaxed">
                <span class="text-gray-700 font-semibold">"{{ deleteTarget?.name }}"</span> reklamı kalıcı olarak silinecek.
              </p>
            </div>
            <div class="px-6 pb-5 flex gap-2.5">
              <button @click="deleteTarget = null" :disabled="deleting" class="flex-1 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:border-gray-400 transition disabled:opacity-50">Vazgeç</button>
              <button @click="confirmDelete" :disabled="deleting" class="flex-1 flex items-center justify-center gap-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-gray-300 disabled:text-gray-400 text-white text-sm font-bold py-2 rounded-lg transition">
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
