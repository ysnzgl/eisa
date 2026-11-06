<script setup>
/**
 * Sponsorluk Tanımları — DOOH sponsorlukların (campaign) tanım ekranı.
 *
 * Basitleştirilmiş 3 adımlı drawer:
 *   1) Bilgiler : ad, reklam veren, başlangıç/bitiş, durum
 *   2) Medya    : creative yükle (bekleme + işlem ekranı medyası, süre)
 *   3) Kiosklar : atanmış kioskların salt-okunur listesi + "Kiosklara Ata"
 *
 * Hedefleme / frekans / simülasyon / aktivasyon adımları kaldırıldı; atama artık
 * cihaz (kiosk) bazlıdır (bkz. Kiosk Sponsorluk ekranı).
 *
 * Route: /admin/campaigns (SuperAdmin)
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  listCampaignsV2, createCampaignV2, updateCampaignV2,
  bulkActionCampaignsV2, createCreative, uploadMedia,
  getCampaignKiosks, assignKiosksToCampaign, listSponsorshipKiosks,
} from '../../services/dooh.js';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import EisaMultiLookup from '../../components/shared/EisaMultiLookup.vue';
import DateRangePicker from '../../components/shared/DateRangePicker.vue';
import { useConfirm } from '../../composables/useConfirm.js';
import {
  WEEKDAYS, weekdaysText, isVideoUrl, extractCapacityError,
} from '../../composables/useSponsorship.js';

const { confirm } = useConfirm();

const STATUS_MAP = {
  ACTIVE:    { label: 'Aktif',        cls: 'eisa-pill-success' },
  PAUSED:    { label: 'Duraklatıldı', cls: 'eisa-pill-warning' },
  COMPLETED: { label: 'Tamamlandı',   cls: 'eisa-pill-muted' },
};
function campStatus(c) { return STATUS_MAP[c.status] || { label: c.status, cls: '' }; }

const STATUS_FILTERS = [
  { value: 'ALL', label: 'Tümü' },
  { value: 'ACTIVE', label: 'Aktif' },
  { value: 'PAUSED', label: 'Duraklatıldı' },
  { value: 'COMPLETED', label: 'Tamamlandı' },
];
const STEP_ICONS = ['fa-circle-info', 'fa-photo-film', 'fa-display'];

function fmtDate(v) {
  if (!v) return '—';
  const d = new Date(v);
  return isNaN(d) ? String(v).slice(0, 10) : d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' });
}
function thumbOf(c) {
  const cr = (c.creatives || [])[0];
  return cr ? (cr.media_url || '') : '';
}

// ─── Liste ────────────────────────────────────────────────────────────────────
const campaigns = ref([]);
const loading   = ref(false);
const search    = ref('');
const statusFilter = ref('ALL');

async function refresh() {
  loading.value = true;
  try {
    const { data } = await listCampaignsV2();
    campaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch {
    toast.error('Sponsorluklar yüklenemedi.');
  } finally { loading.value = false; }
}

const filtered = computed(() => {
  const q = search.value.trim().toLocaleLowerCase('tr');
  return campaigns.value.filter((c) => {
    if (statusFilter.value !== 'ALL' && c.status !== statusFilter.value) return false;
    if (!q) return true;
    return `${c.name} ${c.advertiser_name || ''}`.toLocaleLowerCase('tr').includes(q);
  });
});

const stats = computed(() => ({
  total: campaigns.value.length,
  active: campaigns.value.filter((c) => c.status === 'ACTIVE').length,
  paused: campaigns.value.filter((c) => c.status === 'PAUSED').length,
  kiosks: campaigns.value.reduce((sum, c) => sum + (Number(c.assigned_kiosk_count) || 0), 0),
}));

// ─── Drawer / form ────────────────────────────────────────────────────────────
const drawerOpen = ref(false);
const editingId  = ref(null);
const step       = ref(1);
const STEP_LABELS = ['Bilgiler', 'Medya', 'Kiosklar'];
const saving     = ref(false);
const stepError  = ref('');

const _defaultStart = () => new Date().toISOString().slice(0, 16);
const _defaultEnd = () => { const d = new Date(); d.setMonth(d.getMonth() + 1); return d.toISOString().slice(0, 16); };

const emptyForm = () => ({
  name: '', advertiser_name: '',
  start_date: _defaultStart(), end_date: _defaultEnd(),
  status: 'ACTIVE',
  creatives: [],
});
const form = reactive(emptyForm());

function openCreate() {
  editingId.value = null;
  Object.assign(form, emptyForm());
  assignedKiosks.value = [];
  step.value = 1; stepError.value = ''; drawerOpen.value = true;
}

async function openEdit(c) {
  editingId.value = c.id;
  Object.assign(form, emptyForm(), {
    name: c.name,
    advertiser_name: c.advertiser_name || '',
    start_date: c.start_date?.slice(0, 16) ?? '',
    end_date: c.end_date?.slice(0, 16) ?? '',
    status: c.status,
    creatives: (c.creatives ?? []).map((cr) => ({
      id: cr.id, name: cr.name || 'Mevcut medya',
      duration_seconds: cr.duration_seconds,
      media_url: cr.media_url, uploaded_url: cr.media_url,
      object_key: cr.object_key || '',
      active_media_url: cr.active_media_url || '',
      active_object_key: cr.active_object_key || '',
    })),
  });
  step.value = 1; stepError.value = ''; drawerOpen.value = true;
  loadAssignedKiosks(c.id);
}

async function close() {
  drawerOpen.value = false;
}

function validateStep(n) {
  if (n === 1) {
    if (!form.name.trim()) return 'Sponsorluk adı zorunlu.';
    if (!form.start_date || !form.end_date) return 'Başlangıç ve bitiş tarihi zorunlu.';
    if (new Date(form.end_date) <= new Date(form.start_date)) return 'Bitiş tarihi başlangıçtan sonra olmalı.';
  }
  if (n === 2 && !form.creatives.length) return 'En az bir medya yükleyin.';
  return null;
}

function nextStep() {
  const err = validateStep(step.value);
  if (err) { stepError.value = err; return; }
  stepError.value = '';
  if (step.value < 3) step.value += 1;
}
function prevStep() { stepError.value = ''; if (step.value > 1) step.value -= 1; }
function goStep(n) { if (n < step.value) { stepError.value = ''; step.value = n; } }

// ─── Medya upload (CampaignWizard davranışı korunur) ──────────────────────────
async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.creatives.push({
      file, name: file.name, duration_seconds: 15,
      media_url: data.media_url ?? data.url ?? '',
      object_key: data.object_key ?? '',
      checksum: data.checksum ?? '',
      active_media_url: '',
      uploaded_url: data.media_url ?? data.url ?? '',
    });
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}

async function onPickActiveFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  if (!form.creatives.length) { toast.warning('Önce bekleme ekranı görselini yükleyin.'); ev.target.value = ''; return; }
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.creatives[0].active_media_url = data.media_url ?? data.url ?? '';
    form.creatives[0].active_object_key = data.object_key ?? '';
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}
function removeActiveMedia() { if (form.creatives.length) form.creatives[0].active_media_url = ''; }
function removeCreative(idx) { form.creatives.splice(idx, 1); }

function buildCampaignPayload() {
  return {
    name: form.name,
    advertiser_name: form.advertiser_name || '',
    start_date: new Date(form.start_date).toISOString(),
    end_date: new Date(form.end_date).toISOString(),
    status: form.status,
  };
}

async function save() {
  for (let n = 1; n <= 2; n++) { const e = validateStep(n); if (e) { stepError.value = e; step.value = n; return; } }
  saving.value = true; stepError.value = '';
  try {
    const payload = buildCampaignPayload();
    let cId;
    if (editingId.value) {
      await updateCampaignV2(editingId.value, payload);
      cId = editingId.value;
    } else {
      const { data } = await createCampaignV2(payload);
      cId = data.id;
      editingId.value = cId;
    }
    for (const cr of form.creatives) {
      if (cr.id) continue;
      const { data: created } = await createCreative({
        campaign: cId,
        media_url: cr.media_url || cr.uploaded_url || '',
        active_media_url: cr.active_media_url || '',
        object_key: cr.object_key || undefined,
        active_object_key: cr.active_object_key || undefined,
        checksum: cr.checksum || undefined,
        duration_seconds: Number(cr.duration_seconds),
        name: cr.name?.slice(0, 120) || '',
      });
      // Aynı modalda tekrar "Kaydet" aynı medyayı yeniden oluşturmasın.
      cr.id = created?.id ?? true;
    }
    toast.success('Sponsorluk kaydedildi.');
    await refresh();
    if (editingId.value) loadAssignedKiosks(editingId.value);
  } catch (e) {
    const cap = extractCapacityError(e);
    stepError.value = cap?.detail || e?.response?.data?.detail || 'Kayıt başarısız.';
  } finally { saving.value = false; }
}

// ─── Silme ────────────────────────────────────────────────────────────────────
const deleteOpen = ref(false);
const deleteTarget = ref(null);
const deleteLoading = ref(false);
function askDelete(c) { deleteTarget.value = c; deleteOpen.value = true; }
async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleteLoading.value = true;
  try {
    await bulkActionCampaignsV2('delete', [deleteTarget.value.id]);
    deleteOpen.value = false; deleteTarget.value = null;
    await refresh(); toast.success('Sponsorluk silindi.');
  } catch (e) {
    const cap = extractCapacityError(e);
    toast.error(cap?.detail || e?.response?.data?.detail || 'Silme başarısız.');
  } finally { deleteLoading.value = false; }
}

// ─── Kiosklar sekmesi (atama özeti) ───────────────────────────────────────────
const assignedKiosks = ref([]);
const assignedLoading = ref(false);
async function loadAssignedKiosks(id) {
  assignedLoading.value = true;
  try {
    const { data } = await getCampaignKiosks(id);
    assignedKiosks.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch { assignedKiosks.value = []; } finally { assignedLoading.value = false; }
}

// Kiosklara Ata modalı
const assignOpen = ref(false);
const assignKiosksList = ref([]);
const assign = reactive({
  kiosk_ids: [],
  window_start: '08:00', window_end: '19:00', count: 10,
  weekdays: [], start_date: '', end_date: '',
});
const assignPreview = ref(null);
const assignLoading = ref(false);

const assignKioskOptions = computed(() =>
  assignKiosksList.value.map((k) => ({
    id: k.id,
    label: k.ad,
    sub: [k.eczane_adi, k.il_adi, k.ilce_adi].filter(Boolean).join(' / '),
  }))
);

async function openAssign() {
  assign.kiosk_ids = []; assign.weekdays = [];
  assign.window_start = '08:00'; assign.window_end = '19:00'; assign.count = 10;
  assign.start_date = ''; assign.end_date = '';
  assignPreview.value = null;
  assignOpen.value = true;
  if (!assignKiosksList.value.length) {
    try {
      const { data } = await listSponsorshipKiosks();
      assignKiosksList.value = Array.isArray(data) ? data : (data?.results ?? []);
    } catch { /* non-critical */ }
  }
}

function toggleAssignWeekday(v) {
  const i = assign.weekdays.indexOf(v);
  if (i >= 0) assign.weekdays.splice(i, 1); else assign.weekdays.push(v);
}

function buildAssignBody(dryRun) {
  return {
    kiosk_ids: assign.kiosk_ids.map(Number),
    window_start: assign.window_start,
    window_end: assign.window_end,
    count: Number(assign.count),
    active_weekdays: assign.weekdays.length ? [...assign.weekdays] : null,
    start_date: assign.start_date || null,
    end_date: assign.end_date || null,
    dry_run: dryRun,
  };
}

async function previewAssign() {
  if (!assign.kiosk_ids.length) { toast.warning('En az bir kiosk seçin.'); return; }
  assignLoading.value = true; assignPreview.value = null;
  try {
    const { data } = await assignKiosksToCampaign(editingId.value, buildAssignBody(true));
    assignPreview.value = data;
  } catch (e) {
    const cap = extractCapacityError(e);
    if (cap) assignPreview.value = { rejected: cap.rejected, skipped_already_assigned: cap.skipped, assigned: [], dry_run: true };
    else toast.error(e?.response?.data?.detail || 'Önizleme başarısız.');
  } finally { assignLoading.value = false; }
}

async function confirmAssign() {
  if (!assign.kiosk_ids.length) return;
  assignLoading.value = true;
  try {
    const { data } = await assignKiosksToCampaign(editingId.value, buildAssignBody(false));
    const n = (data.assigned || []).length;
    toast.success(`${n} kioska atandı.`);
    assignOpen.value = false;
    loadAssignedKiosks(editingId.value);
    await refresh();
  } catch (e) {
    const cap = extractCapacityError(e);
    if (cap) {
      assignPreview.value = { rejected: cap.rejected, skipped_already_assigned: cap.skipped, assigned: [], dry_run: false };
      toast.error(cap.detail);
    } else {
      toast.error(e?.response?.data?.detail || 'Atama başarısız.');
    }
  } finally { assignLoading.value = false; }
}

function kioskNameById(id) {
  const k = assignKiosksList.value.find((x) => String(x.id) === String(id));
  return k ? k.ad : `#${id}`;
}

onMounted(refresh);
</script>

<template>
  <div class="eisa-page">
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">DOOH · Sponsorluk</p>
        <h1 class="eisa-page-title">Sponsorluk Tanımları</h1>
        <p class="eisa-page-subtitle">Sponsorluk kampanyalarını ve medyalarını tanımlayın; kiosklara buradan atayın.</p>
      </div>
      <button class="eisa-btn eisa-btn-cta" @click="openCreate">
        <i class="fa-solid fa-plus fa-fw"></i><span>Yeni Sponsorluk</span>
      </button>
    </div>

    <div class="sd-kpis">
      <div class="sd-kpi">
        <span class="sd-kpi-icon sd-kpi-icon--brand"><i class="fa-solid fa-bullhorn"></i></span>
        <div class="sd-kpi-text"><span class="sd-kpi-label">Toplam</span><strong class="sd-kpi-value">{{ stats.total }}</strong></div>
      </div>
      <div class="sd-kpi">
        <span class="sd-kpi-icon sd-kpi-icon--success"><i class="fa-solid fa-circle-play"></i></span>
        <div class="sd-kpi-text"><span class="sd-kpi-label">Aktif</span><strong class="sd-kpi-value">{{ stats.active }}</strong></div>
      </div>
      <div class="sd-kpi">
        <span class="sd-kpi-icon sd-kpi-icon--warning"><i class="fa-solid fa-circle-pause"></i></span>
        <div class="sd-kpi-text"><span class="sd-kpi-label">Duraklatıldı</span><strong class="sd-kpi-value">{{ stats.paused }}</strong></div>
      </div>
      <div class="sd-kpi">
        <span class="sd-kpi-icon sd-kpi-icon--info"><i class="fa-solid fa-display"></i></span>
        <div class="sd-kpi-text"><span class="sd-kpi-label">Kiosk Ataması</span><strong class="sd-kpi-value">{{ stats.kiosks }}</strong></div>
      </div>
    </div>

    <div class="eisa-panel sd-panel">
      <div class="sd-toolbar">
        <div class="eisa-search-wrap sd-search">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input v-model="search" class="eisa-field eisa-search-field" placeholder="Ad / reklam veren ara…" />
        </div>
        <div class="sd-segment" role="tablist" aria-label="Durum filtresi">
          <button v-for="f in STATUS_FILTERS" :key="f.value" type="button" role="tab"
            class="sd-segment-btn" :class="{ 'sd-segment-btn--on': statusFilter === f.value }"
            :aria-selected="statusFilter === f.value" @click="statusFilter = f.value">{{ f.label }}</button>
        </div>
      </div>

      <div v-if="loading" class="sd-empty">
        <i class="fa-solid fa-spinner fa-spin"></i><span>Yükleniyor…</span>
      </div>
      <div v-else class="eisa-table-wrap sd-table-wrap">
        <table class="eisa-table sd-table">
          <thead>
            <tr>
              <th>Sponsorluk</th><th>Tarih Aralığı</th>
              <th class="sd-col-num">Medya</th><th class="sd-col-num">Kiosk</th><th>Durum</th><th class="sd-col-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in filtered" :key="c.id" class="sd-row">
              <td>
                <div class="sd-name-cell">
                  <span class="sd-thumb">
                    <i v-if="!thumbOf(c)" class="fa-regular fa-image"></i>
                    <i v-else-if="isVideoUrl(thumbOf(c))" class="fa-solid fa-film"></i>
                    <img v-else :src="thumbOf(c)" alt="" loading="lazy" @error="(e)=>e.target.style.display='none'" />
                  </span>
                  <div class="sd-name-meta">
                    <strong class="sd-name">{{ c.name }}</strong>
                    <span class="sd-sub"><i class="fa-regular fa-building fa-fw"></i>{{ c.advertiser_name || 'Reklam veren yok' }}</span>
                  </div>
                </div>
              </td>
              <td>
                <span class="sd-date"><i class="fa-regular fa-calendar fa-fw"></i>{{ fmtDate(c.start_date) }}<i class="fa-solid fa-arrow-right-long sd-date-arrow"></i>{{ fmtDate(c.end_date) }}</span>
              </td>
              <td class="sd-col-num"><span class="sd-count"><i class="fa-solid fa-photo-film fa-fw"></i>{{ (c.creatives || []).length }}</span></td>
              <td class="sd-col-num"><span class="sd-count"><i class="fa-solid fa-display fa-fw"></i>{{ c.assigned_kiosk_count ?? 0 }}</span></td>
              <td><span class="eisa-pill" :class="campStatus(c).cls"><span class="sd-dot"></span>{{ campStatus(c).label }}</span></td>
              <td class="sd-col-actions">
                <div class="sd-actions">
                  <button class="eisa-icon-btn" title="Düzenle" aria-label="Düzenle" @click="openEdit(c)"><i class="fa-solid fa-pen"></i></button>
                  <button class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="askDelete(c)"><i class="fa-solid fa-trash"></i></button>
                </div>
              </td>
            </tr>
            <tr v-if="!filtered.length">
              <td colspan="6">
                <div class="sd-empty">
                  <i class="fa-solid fa-bullhorn"></i>
                  <span>{{ campaigns.length ? 'Filtreye uyan sponsorluk bulunamadı.' : 'Henüz sponsorluk tanımlanmamış.' }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Drawer -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div v-if="drawerOpen" class="eisa-modal-backdrop" @click.self="close">
          <div class="eisa-modal eisa-modal--medium sd-drawer">
            <div class="eisa-modal-header">
              <div class="sd-modal-head">
                <span class="sd-modal-icon"><i class="fa-solid fa-bullhorn"></i></span>
                <div>
                  <h3 class="eisa-modal-title">{{ editingId ? 'Sponsorluğu Düzenle' : 'Yeni Sponsorluk' }}</h3>
                  <p v-if="editingId && form.name" class="sd-modal-sub">{{ form.name }}</p>
                </div>
              </div>
              <button class="eisa-modal-close" aria-label="Kapat" @click="close"><i class="fa-solid fa-xmark"></i></button>
            </div>

            <ol class="sd-steps">
              <li v-for="(l, i) in STEP_LABELS" :key="i"
                class="sd-step" :class="{ 'sd-step--active': step === i+1, 'sd-step--done': step > i+1 }"
                @click="goStep(i+1)">
                <span class="sd-step-dot">
                  <i v-if="step > i+1" class="fa-solid fa-check"></i>
                  <i v-else :class="['fa-solid', STEP_ICONS[i]]"></i>
                </span>
                <span class="sd-step-text"><small>Adım {{ i+1 }}</small>{{ l }}</span>
              </li>
            </ol>

            <div class="eisa-modal-body">
              <!-- 1. Bilgiler -->
              <section v-if="step === 1" class="eisa-form-grid">
                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">Sponsorluk adı *</label>
                  <input v-model="form.name" class="eisa-field" placeholder="Örn. Bayer Yaz Kampanyası" />
                </div>
                <div class="eisa-form-row">
                  <label class="eisa-field-label">Reklam veren</label>
                  <input v-model="form.advertiser_name" class="eisa-field" placeholder="Örn. Bayer İlaç" />
                </div>
                <div class="eisa-form-row">
                  <label class="eisa-field-label">Durum</label>
                  <select v-model="form.status" class="eisa-field">
                    <option value="ACTIVE">Aktif</option>
                    <option value="PAUSED">Duraklatıldı</option>
                    <option value="COMPLETED">Tamamlandı</option>
                  </select>
                </div>
                <div class="eisa-form-row eisa-form-row-full">
                  <DateRangePicker
                    :start="form.start_date" :end="form.end_date"
                    @update:start="(v) => form.start_date = v"
                    @update:end="(v) => form.end_date = v"
                  />
                </div>
              </section>

              <!-- 2. Medya -->
              <section v-if="step === 2" class="sd-media-grid">
                <div class="sd-media-slot">
                  <div class="sd-media-head">
                    <span class="sd-media-icon"><i class="fa-solid fa-mobile-screen"></i></span>
                    <div class="sd-media-titles">
                      <span class="sd-media-label">Bekleme Ekranı Medyası *</span>
                      <span class="sd-media-hint">Önerilen 1080×1920 (9:16) · görsel veya video</span>
                    </div>
                  </div>
                  <label v-if="!form.creatives.length" class="sd-upload sd-upload--portrait" :class="{ 'sd-upload--busy': saving }">
                    <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickFile" :disabled="saving" />
                    <i class="fa-solid fa-cloud-arrow-up sd-upload-icon"></i>
                    <span class="sd-upload-title">Dosya seç</span>
                    <span class="sd-upload-hint">JPG, PNG, WEBP, MP4, WEBM · max 100 MB</span>
                  </label>
                  <div v-else class="sd-creative">
                    <div class="sd-preview sd-preview--portrait">
                      <video v-if="isVideoUrl(form.creatives[0].media_url || form.creatives[0].uploaded_url)"
                        :src="form.creatives[0].media_url || form.creatives[0].uploaded_url" muted controls preload="metadata" />
                      <img v-else :src="form.creatives[0].media_url || form.creatives[0].uploaded_url"
                        alt="Bekleme medyası" @error="(e)=>e.target.style.display='none'" />
                    </div>
                    <div class="sd-cmeta">
                      <strong class="sd-cname" :title="form.creatives[0].name">{{ form.creatives[0].name }}</strong>
                      <label class="eisa-field-label">Ekran süresi</label>
                      <select v-model.number="form.creatives[0].duration_seconds" class="eisa-field" :disabled="!!form.creatives[0].id">
                        <option :value="5">5 sn</option><option :value="10">10 sn</option>
                        <option :value="15">15 sn</option><option :value="30">30 sn</option><option :value="60">60 sn</option>
                      </select>
                      <button v-if="!form.creatives[0].id" type="button" class="eisa-btn eisa-btn-ghost sd-remove" @click="removeCreative(0)">
                        <i class="fa-solid fa-trash fa-fw"></i><span>Kaldır</span>
                      </button>
                    </div>
                  </div>
                </div>

                <div class="sd-media-slot">
                  <div class="sd-media-head">
                    <span class="sd-media-icon"><i class="fa-solid fa-tv"></i></span>
                    <div class="sd-media-titles">
                      <span class="sd-media-label">İşlem Ekranı Medyası</span>
                      <span class="sd-media-hint">Önerilen 1080×768 (yatay) · opsiyonel</span>
                    </div>
                  </div>
                  <p class="sd-note"><i class="fa-solid fa-circle-info fa-fw"></i><span>Kiosk kullanılırken alt şeritte gösterilir. Yüklenmezse bekleme görseli kullanılır.</span></p>
                  <div v-if="form.creatives[0]?.active_media_url" class="sd-creative sd-creative--stack">
                    <div class="sd-preview sd-preview--landscape">
                      <video v-if="isVideoUrl(form.creatives[0].active_media_url)" :src="form.creatives[0].active_media_url" muted controls preload="metadata" />
                      <img v-else :src="form.creatives[0].active_media_url" alt="İşlem medyası" @error="(e)=>e.target.style.display='none'" />
                    </div>
                    <button type="button" class="eisa-btn eisa-btn-ghost sd-remove" @click="removeActiveMedia">
                      <i class="fa-solid fa-trash fa-fw"></i><span>Kaldır</span>
                    </button>
                  </div>
                  <label v-else class="sd-upload sd-upload--landscape" :class="{ 'sd-upload--disabled': !form.creatives.length, 'sd-upload--busy': saving }">
                    <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickActiveFile" :disabled="saving || !form.creatives.length" />
                    <i class="fa-solid fa-cloud-arrow-up sd-upload-icon"></i>
                    <span class="sd-upload-title">Dosya seç (yatay)</span>
                    <span class="sd-upload-hint">{{ form.creatives.length ? 'Görsel veya video' : 'Önce bekleme medyasını yükleyin' }}</span>
                  </label>
                </div>
                <p v-if="saving" class="sd-uploading"><i class="fa-solid fa-spinner fa-spin fa-fw"></i><span>Yükleniyor…</span></p>
              </section>

              <!-- 3. Kiosklar -->
              <section v-if="step === 3">
                <div class="sd-kiosk-head">
                  <div>
                    <h4 class="sd-section-title">Atanmış Kiosklar</h4>
                    <p class="sd-section-sub">{{ editingId ? `${assignedKiosks.length} kiosk atanmış` : 'Atama için önce sponsorluğu kaydedin.' }}</p>
                  </div>
                  <button class="eisa-btn eisa-btn-cta" :disabled="!editingId" @click="openAssign">
                    <i class="fa-solid fa-plus fa-fw"></i><span>Kiosklara Ata</span>
                  </button>
                </div>
                <div v-if="!editingId" class="sd-empty sd-empty--boxed">
                  <i class="fa-solid fa-floppy-disk"></i><span>Önce sponsorluğu kaydedin.</span>
                </div>
                <div v-else-if="assignedLoading" class="sd-empty"><i class="fa-solid fa-spinner fa-spin"></i><span>Yükleniyor…</span></div>
                <div v-else-if="assignedKiosks.length" class="eisa-table-wrap sd-assigned-wrap">
                  <table class="eisa-table sd-assigned">
                    <thead><tr><th>Kiosk</th><th>Pencere</th><th class="sd-col-num">Sayı</th><th>Günler</th><th>Aktif</th></tr></thead>
                    <tbody>
                      <tr v-for="a in assignedKiosks" :key="a.id">
                        <td>
                          <div class="sd-name-meta">
                            <strong class="sd-name">{{ a.kiosk_name }}</strong>
                            <span class="sd-sub"><i class="fa-solid fa-prescription-bottle-medical fa-fw"></i>{{ [a.eczane_adi, a.il_adi, a.ilce_adi].filter(Boolean).join(' · ') || '—' }}</span>
                          </div>
                        </td>
                        <td><span class="sd-date"><i class="fa-regular fa-clock fa-fw"></i>{{ a.window_start }}–{{ a.window_end }}</span></td>
                        <td class="sd-col-num"><strong>{{ a.count }}</strong></td>
                        <td class="sd-nowrap">{{ weekdaysText(a.active_weekdays) }}</td>
                        <td><span class="eisa-pill" :class="a.is_active ? 'eisa-pill-success' : 'eisa-pill-muted'"><span class="sd-dot"></span>{{ a.is_active ? 'Evet' : 'Hayır' }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="sd-empty sd-empty--boxed">
                  <i class="fa-solid fa-display"></i><span>Bu sponsorluk henüz hiçbir kioska atanmamış.</span>
                </div>
              </section>

              <p v-if="stepError" class="sd-error"><i class="fa-solid fa-circle-exclamation fa-fw"></i><span>{{ stepError }}</span></p>
            </div>

            <div class="eisa-modal-footer sd-footer">
              <span class="sd-footer-step">Adım {{ step }} / {{ STEP_LABELS.length }}</span>
              <div class="sd-footer-actions">
                <button v-if="step > 1" class="eisa-btn eisa-btn-ghost" @click="prevStep"><i class="fa-solid fa-arrow-left fa-fw"></i><span>Geri</span></button>
                <button v-if="step < 3" class="eisa-btn" @click="nextStep"><span>İleri</span><i class="fa-solid fa-arrow-right fa-fw"></i></button>
                <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="save">
                  <i class="fa-solid fa-fw" :class="saving ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i><span>{{ saving ? 'Kaydediliyor…' : 'Kaydet' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Kiosklara Ata modalı -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div v-if="assignOpen" class="eisa-modal-backdrop" @click.self="assignOpen = false">
          <div class="eisa-modal eisa-modal--medium sd-assign-modal">
            <div class="eisa-modal-header">
              <div class="sd-modal-head">
                <span class="sd-modal-icon"><i class="fa-solid fa-display"></i></span>
                <div>
                  <h3 class="eisa-modal-title">Kiosklara Ata</h3>
                  <p v-if="form.name" class="sd-modal-sub">{{ form.name }}</p>
                </div>
              </div>
              <button class="eisa-modal-close" aria-label="Kapat" @click="assignOpen = false"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="eisa-modal-body">
              <div class="sd-fieldset">
                <label class="eisa-field-label">Kiosklar *</label>
                <EisaMultiLookup v-model="assign.kiosk_ids" :options="assignKioskOptions" placeholder="Kiosk ara / seç…" />
              </div>

              <div class="sd-fieldset">
                <span class="sd-fieldset-title"><i class="fa-regular fa-clock fa-fw"></i>Yayın penceresi</span>
                <div class="sd-assign-row">
                  <label class="sd-assign-field"><span class="eisa-field-label">Başlangıç</span>
                    <input type="time" v-model="assign.window_start" class="eisa-field" />
                  </label>
                  <label class="sd-assign-field"><span class="eisa-field-label">Bitiş</span>
                    <input type="time" v-model="assign.window_end" class="eisa-field" />
                  </label>
                  <label class="sd-assign-field"><span class="eisa-field-label">Günlük gösterim</span>
                    <input type="number" min="1" v-model.number="assign.count" class="eisa-field" />
                  </label>
                </div>
              </div>

              <div class="sd-fieldset">
                <span class="sd-fieldset-title"><i class="fa-regular fa-calendar-check fa-fw"></i>Günler <small>(boş = her gün)</small></span>
                <div class="ks-weekdays">
                  <button v-for="w in WEEKDAYS" :key="w.value" type="button" class="ks-chip" :title="w.full"
                    :class="{ 'ks-chip--on': assign.weekdays.includes(w.value) }" @click="toggleAssignWeekday(w.value)">{{ w.label }}</button>
                </div>
              </div>

              <div class="sd-fieldset">
                <span class="sd-fieldset-title"><i class="fa-regular fa-calendar fa-fw"></i>Geçerlilik <small>(opsiyonel)</small></span>
                <div class="sd-assign-row">
                  <label class="sd-assign-field"><span class="eisa-field-label">Başlangıç tarihi</span>
                    <input type="date" v-model="assign.start_date" class="eisa-field" />
                  </label>
                  <label class="sd-assign-field"><span class="eisa-field-label">Bitiş tarihi</span>
                    <input type="date" v-model="assign.end_date" class="eisa-field" />
                  </label>
                </div>
              </div>

              <div v-if="assignPreview" class="sd-assign-preview">
                <div v-if="assignPreview.assigned?.length" class="sd-assign-grp sd-assign-grp--add">
                  <strong><i class="fa-solid fa-circle-check fa-fw"></i>Atanacak ({{ assignPreview.assigned.length }})</strong>
                  <span>{{ assignPreview.assigned.map(kioskNameById).join(', ') }}</span>
                </div>
                <div v-if="assignPreview.skipped_already_assigned?.length" class="sd-assign-grp sd-assign-grp--keep">
                  <strong><i class="fa-solid fa-circle-minus fa-fw"></i>Zaten atanmış, atlanacak</strong>
                  <span>{{ assignPreview.skipped_already_assigned.map(kioskNameById).join(', ') }}</span>
                </div>
                <div v-if="assignPreview.rejected?.length" class="sd-assign-grp sd-assign-grp--rem">
                  <strong><i class="fa-solid fa-circle-xmark fa-fw"></i>Reddedilen (kapasite)</strong>
                  <ul>
                    <li v-for="r in assignPreview.rejected" :key="r.kiosk_id">
                      {{ r.kiosk_name || kioskNameById(r.kiosk_id) }}
                      <span v-if="r.conflicts?.length" class="sd-muted">
                        — {{ r.conflicts.map(c => `${c.date}: ${c.placed}/${c.requested}`).join('; ') }}
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="eisa-modal-footer">
              <button class="eisa-btn" :disabled="assignLoading || !assign.kiosk_ids.length" @click="previewAssign">
                <i class="fa-solid fa-eye fa-fw"></i><span>Önizle</span>
              </button>
              <button class="eisa-btn eisa-btn-cta" :disabled="assignLoading || !assign.kiosk_ids.length" @click="confirmAssign">
                <i class="fa-solid fa-fw" :class="assignLoading ? 'fa-spinner fa-spin' : 'fa-check'"></i><span>Ata</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <EisaDeleteConfirm
      :open="deleteOpen"
      :loading="deleteLoading"
      title="Sponsorluğu Sil"
      :message="`'${deleteTarget?.name}' silinecek. Emin misiniz?`"
      @confirm="confirmDelete"
      @cancel="deleteOpen = false"
    />
  </div>
</template>

<style scoped>
/* ── KPI kartları ─────────────────────────────────────────────── */
.sd-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.sd-kpi { display: flex; align-items: center; gap: .85rem; background: #fff; border: 1px solid #D9E1EA; border-radius: 14px; padding: .95rem 1.1rem; box-shadow: 0 1px 3px rgba(17,24,39,.04); }
.sd-kpi-icon { width: 42px; height: 42px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 1.05rem; flex-shrink: 0; line-height: 1; }
.sd-kpi-icon--brand   { background: #FEF2F2; color: #B1121B; }
.sd-kpi-icon--success { background: #ECFDF5; color: #059669; }
.sd-kpi-icon--warning { background: #FFFBEB; color: #B45309; }
.sd-kpi-icon--info    { background: #EEF2FF; color: #4338CA; }
.sd-kpi-text { display: flex; flex-direction: column; min-width: 0; }
.sd-kpi-label { font-size: .68rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6B7280; }
.sd-kpi-value { font-family: 'Syne', sans-serif; font-size: 1.55rem; line-height: 1.15; color: #111827; }

/* ── Liste paneli ─────────────────────────────────────────────── */
.sd-panel { overflow: hidden; }
.sd-toolbar { display: flex; align-items: center; justify-content: space-between; gap: .75rem; padding: .85rem 1rem; border-bottom: 1px solid #E5EBF1; flex-wrap: wrap; }
.sd-search { max-width: 340px; }
.sd-segment { display: inline-flex; padding: 3px; background: #EEF2F6; border-radius: 10px; gap: 2px; flex-wrap: wrap; }
.sd-segment-btn { border: none; background: transparent; padding: .4rem .8rem; border-radius: 8px; font: inherit; font-size: .8rem; font-weight: 600; color: #6B7280; cursor: pointer; transition: background .15s, color .15s, box-shadow .15s; }
.sd-segment-btn:hover { color: #111827; }
.sd-segment-btn--on { background: #fff; color: #B1121B; box-shadow: 0 1px 3px rgba(17,24,39,.12); }

.sd-table-wrap { min-height: 0; }
.sd-table tbody td { vertical-align: middle; }
.sd-table tbody tr:last-child td { border-bottom: none; }
.sd-col-num { text-align: center; width: 90px; }
.sd-col-actions { width: 96px; }
.sd-actions { display: flex; justify-content: flex-end; gap: .35rem; }
.sd-nowrap { white-space: nowrap; }

.sd-name-cell { display: flex; align-items: center; gap: .75rem; min-width: 0; }
.sd-thumb { width: 40px; height: 52px; border-radius: 8px; background: #F3F4F6; border: 1px solid #E5E7EB; overflow: hidden; display: inline-flex; align-items: center; justify-content: center; color: #9CA3AF; font-size: .95rem; flex-shrink: 0; }
.sd-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.sd-name-meta { display: flex; flex-direction: column; gap: .15rem; min-width: 0; }
.sd-name { font-weight: 700; color: #111827; line-height: 1.3; }
.sd-sub { display: inline-flex; align-items: flex-start; gap: .3rem; font-size: .76rem; color: #6B7280; line-height: 1.35; }
.sd-sub i { color: #9CA3AF; font-size: .72rem; margin-top: .16rem; }

.sd-date { display: inline-flex; align-items: center; gap: .35rem; font-size: .82rem; color: #374151; white-space: nowrap; }
.sd-date > i:first-child { color: #9CA3AF; font-size: .78rem; }
.sd-date-arrow { color: #CBD5E1; font-size: .72rem; margin: 0 .1rem; }

.sd-count { display: inline-flex; align-items: center; gap: .3rem; padding: .2rem .55rem; border-radius: 999px; background: #F1F5F9; color: #334155; font-size: .78rem; font-weight: 700; line-height: 1.2; }
.sd-count i { font-size: .7rem; color: #64748B; }

.sd-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; flex-shrink: 0; }

.sd-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .5rem; padding: 2.5rem 1rem; color: #6B7280; font-size: .875rem; text-align: center; }
.sd-empty > i { font-size: 1.6rem; color: #CBD5E1; }
.sd-empty--boxed { border: 1px dashed #D9E1EA; border-radius: 12px; background: #FAFBFC; padding: 1.75rem 1rem; }

/* ── Drawer / modal ───────────────────────────────────────────── */
/* Teleport ile body'ye taşınan modallar .eisa-page token'larını miras almaz. */
.sd-drawer, .sd-assign-modal {
  --border: #D9E1EA; --surface: #FFFFFF; --faint: #F8FAFC; --text: #111827; --muted: #6B7280; --accent: #B1121B;
}
.sd-drawer { max-width: 760px; width: 95%; max-height: 90vh; }
.sd-modal-head { display: flex; align-items: center; gap: .75rem; min-width: 0; }
.sd-modal-icon { width: 36px; height: 36px; border-radius: 10px; background: #FEF2F2; color: #B1121B; display: inline-flex; align-items: center; justify-content: center; font-size: .95rem; flex-shrink: 0; }
.sd-modal-sub { margin: .1rem 0 0; font-size: .76rem; color: #6B7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 480px; }

.sd-steps { list-style: none; margin: 0; padding: .85rem 1.25rem; display: flex; align-items: center; gap: .5rem; border-bottom: 1px solid #E5EBF1; background: #FAFBFC; }
.sd-step { display: flex; align-items: center; gap: .55rem; flex: 1; min-width: 0; color: #9CA3AF; position: relative; }
.sd-step:not(:last-child)::after { content: ''; flex: 1; height: 2px; background: #E5E7EB; border-radius: 2px; margin-left: .25rem; }
.sd-step--done:not(:last-child)::after { background: #6EE7B7; }
.sd-step--done { cursor: pointer; color: #059669; }
.sd-step--active { color: #B1121B; }
.sd-step-dot { width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: .78rem; background: #fff; border: 2px solid #E5E7EB; color: #9CA3AF; flex-shrink: 0; line-height: 1; transition: all .15s; }
.sd-step--active .sd-step-dot { border-color: #B1121B; background: #B1121B; color: #fff; box-shadow: 0 0 0 4px rgba(177,18,27,.12); }
.sd-step--done .sd-step-dot { border-color: #10B981; background: #ECFDF5; color: #059669; }
.sd-step-text { display: flex; flex-direction: column; font-size: .82rem; font-weight: 700; line-height: 1.2; white-space: nowrap; }
.sd-step-text small { font-size: .62rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; opacity: .75; }

.sd-error { display: flex; align-items: flex-start; gap: .4rem; color: #B91C1C; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px; padding: .6rem .75rem; font-size: .82rem; margin: 1rem 0 0; }
.sd-error i { margin-top: .15rem; }

.sd-footer { justify-content: space-between; align-items: center; }
.sd-footer-step { font-size: .76rem; font-weight: 600; color: #6B7280; }
.sd-footer-actions { display: flex; gap: .5rem; }

/* ── Medya adımı ──────────────────────────────────────────────── */
.sd-media-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: start; }
.sd-media-slot { border: 1px solid #E5EBF1; border-radius: 14px; padding: 1rem; background: #fff; display: flex; flex-direction: column; gap: .75rem; }
.sd-media-head { display: flex; align-items: center; gap: .65rem; }
.sd-media-icon { width: 32px; height: 32px; border-radius: 9px; background: #F1F5F9; color: #475569; display: inline-flex; align-items: center; justify-content: center; font-size: .85rem; flex-shrink: 0; }
.sd-media-titles { display: flex; flex-direction: column; min-width: 0; }
.sd-media-label { font-weight: 700; font-size: .86rem; color: #111827; }
.sd-media-hint { font-size: .72rem; color: #9CA3AF; }
.sd-note { display: flex; align-items: flex-start; gap: .4rem; margin: 0; font-size: .76rem; color: #6B7280; line-height: 1.4; }
.sd-note i { color: #94A3B8; margin-top: .12rem; }

.sd-upload { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .3rem; border: 2px dashed #D1D5DB; border-radius: 12px; padding: 1.25rem; cursor: pointer; color: #6B7280; text-align: center; background: #FAFBFC; transition: border-color .15s, background .15s, color .15s; }
.sd-upload:hover { border-color: #B1121B; background: #FFF7F7; color: #B1121B; }
.sd-upload input { display: none; }
.sd-upload--portrait { min-height: 220px; }
.sd-upload--landscape { min-height: 150px; }
.sd-upload--disabled { opacity: .5; pointer-events: none; }
.sd-upload--busy { opacity: .7; pointer-events: none; }
.sd-upload-icon { font-size: 1.6rem; line-height: 1; }
.sd-upload-title { font-weight: 700; font-size: .86rem; }
.sd-upload-hint { font-size: .72rem; color: #9CA3AF; }

.sd-creative { display: flex; gap: .9rem; align-items: flex-start; }
.sd-creative--stack { flex-direction: column; align-items: stretch; }
.sd-preview { border-radius: 10px; overflow: hidden; background: #0F172A; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid #E5E7EB; }
.sd-preview--portrait { width: 124px; aspect-ratio: 9 / 16; }
.sd-preview--landscape { width: 100%; aspect-ratio: 1080 / 768; }
.sd-preview img, .sd-preview video { width: 100%; height: 100%; object-fit: contain; display: block; }
.sd-cmeta { flex: 1; display: flex; flex-direction: column; gap: .35rem; min-width: 0; }
.sd-cmeta .eisa-field-label { margin: .35rem 0 0; }
.sd-cname { font-size: .82rem; color: #111827; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sd-remove { align-self: flex-start; margin-top: .35rem; padding: .4rem .75rem; font-size: .78rem; }
.sd-remove:hover:not(:disabled) { color: #B91C1C; border-color: #FCA5A5; background: #FEF2F2; }
.sd-uploading { grid-column: 1 / -1; display: inline-flex; align-items: center; gap: .4rem; margin: 0; font-size: .8rem; color: #6B7280; }

/* ── Kiosklar adımı ───────────────────────────────────────────── */
.sd-kiosk-head { display: flex; justify-content: space-between; align-items: center; gap: .75rem; margin-bottom: .85rem; }
.sd-section-title { margin: 0; font-size: .95rem; font-weight: 700; color: #111827; }
.sd-section-sub { margin: .15rem 0 0; font-size: .76rem; color: #6B7280; }
.sd-assigned-wrap { min-height: 0; border: 1px solid #E5EBF1; border-radius: 12px; }
.sd-assigned { font-size: .82rem; }
.sd-assigned tbody tr:last-child td { border-bottom: none; }

/* ── Kiosklara Ata modalı ─────────────────────────────────────── */
.sd-fieldset { margin-bottom: 1rem; }
.sd-fieldset-title { display: flex; align-items: center; gap: .35rem; font-size: .8rem; font-weight: 700; color: #374151; margin-bottom: .5rem; }
.sd-fieldset-title i { color: #94A3B8; }
.sd-fieldset-title small { font-weight: 500; color: #9CA3AF; }
.sd-assign-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .75rem; }
.sd-assign-field { display: flex; flex-direction: column; }
.sd-assign-preview { display: flex; flex-direction: column; gap: .5rem; margin-top: .25rem; font-size: .82rem; }
.sd-assign-grp { border-radius: 10px; padding: .6rem .75rem; border: 1px solid; display: flex; flex-direction: column; gap: .2rem; }
.sd-assign-grp strong { display: inline-flex; align-items: center; gap: .3rem; }
.sd-assign-grp ul { margin: .15rem 0 0; padding-left: 1.1rem; }
.sd-assign-grp--add  { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
.sd-assign-grp--keep { background: #F8FAFC; border-color: #E2E8F0; color: #475569; }
.sd-assign-grp--rem  { background: #FEF2F2; border-color: #FECACA; color: #991B1B; }
.sd-muted { color: #6B7280; }

.ks-weekdays { display: flex; flex-wrap: wrap; gap: .35rem; }
.ks-chip { min-width: 46px; border: 1px solid #D1D5DB; background: #fff; border-radius: 8px; padding: .4rem .6rem; font: inherit; font-size: .78rem; font-weight: 600; cursor: pointer; color: #4B5563; transition: all .15s; }
.ks-chip:hover { border-color: #B1121B; color: #B1121B; }
.ks-chip--on, .ks-chip--on:hover { background: #B1121B; color: #fff; border-color: #B1121B; }

@media (max-width: 720px) {
  .sd-media-grid { grid-template-columns: 1fr; }
  .sd-step-text small { display: none; }
  .sd-step-text { font-size: .74rem; }
  .sd-search { max-width: none; flex: 1 1 100%; }
  .sd-segment { width: 100%; }
  .sd-segment-btn { flex: 1 1 auto; }
  .sd-footer { flex-wrap: wrap; gap: .5rem; }
  .sd-footer-actions { flex: 1 1 100%; flex-wrap: wrap; justify-content: flex-end; }
  .sd-kiosk-head { flex-wrap: wrap; }
  .sd-modal-head { flex: 1; }
  .sd-modal-head > div { min-width: 0; }
  .sd-modal-sub { max-width: 100%; }
}
@media (max-width: 480px) {
  .sd-steps { padding: .7rem .85rem; }
  .sd-step:not(.sd-step--active) .sd-step-text { display: none; }
  .sd-kpis { grid-template-columns: 1fr 1fr; gap: .6rem; }
  .sd-kpi { padding: .75rem; gap: .6rem; }
  .sd-kpi-icon { width: 34px; height: 34px; font-size: .9rem; }
  .sd-creative { flex-direction: column; align-items: stretch; }
  .sd-preview--portrait { width: 140px; align-self: center; }
}
</style>
