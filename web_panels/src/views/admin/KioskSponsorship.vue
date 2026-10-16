<script setup>
/**
 * Kiosk Sponsorluk — cihaz (kiosk) bazlı sponsorluk yönetimi.
 *
 * Sol: aranabilir kiosk listesi (çevrimiçi durumu, sponsorluk sayısı, "Atanmamış" filtresi).
 * Sağ: seçili kiosk için sekmeler:
 *   - Sponsorluklar : düzenlenebilir atama tablosu (pencere/sayım/günler/tarih/aktif)
 *   - Yayın Takvimi : taslak/yayında günlük yayın önizlemesi (ısı haritası + dakika şeridi)
 *   - Simülasyon    : probe + senaryo hesabı
 *   - Kopyala       : takvimi başka kiosklara kopyala (üzerine yazar)
 *
 * Route: /admin/kiosk-sponsorships (SuperAdmin)
 */
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { toast } from 'vue-sonner';
import {
  listSponsorshipKiosks, getKioskSponsorships, putKioskSponsorships,
  previewKioskSponsorships, copyKioskSponsorships, simulateKioskSponsorship,
  getKioskDayStream, listCampaignsV2,
} from '../../services/dooh.js';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import { useConfirm } from '../../composables/useConfirm.js';
import {
  WEEKDAYS, weekdaysText, weekdayLabel,
  hhmmToMinutes, secondToHHMMSS, maxCountHint, validateRow, rowToPayload,
  heatmapColor, hourTimeline, diffCampaignNames, extractCapacityError,
  getIstanbulToday, isVideoUrl,
} from '../../composables/useSponsorship.js';

const { confirm } = useConfirm();

// ─── Kiosk listesi (sol panel) ────────────────────────────────────────────────
const kiosks        = ref([]);
const kiosksLoading = ref(false);
const kioskSearch   = ref('');
const onlyUnassigned = ref(false);
const selectedKioskId = ref(null);

async function loadKiosks() {
  kiosksLoading.value = true;
  try {
    const params = {};
    if (kioskSearch.value.trim()) params.search = kioskSearch.value.trim();
    if (onlyUnassigned.value) params.unassigned = 1;
    const { data } = await listSponsorshipKiosks(params);
    kiosks.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch {
    toast.error('Kiosklar yüklenemedi.');
  } finally { kiosksLoading.value = false; }
}

let _searchTimer = null;
watch([kioskSearch, onlyUnassigned], () => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(loadKiosks, 300);
});

const selectedKiosk = computed(() =>
  kiosks.value.find((k) => String(k.id) === String(selectedKioskId.value)) || kioskSummary.value
);

async function selectKiosk(k) {
  if (dirty.value) {
    const ok = await confirm({
      title: 'Kaydedilmemiş Değişiklik',
      message: 'Bu kioskta kaydedilmemiş değişiklikler var. Devam edilsin mi?',
      confirmLabel: 'Devam Et', variant: 'warning',
    });
    if (!ok) return;
  }
  selectedKioskId.value = k.id;
  activeTab.value = 'sponsorships';
  await loadSponsorships(k.id);
}

// ─── Sekmeler ─────────────────────────────────────────────────────────────────
const activeTab = ref('sponsorships');
const TABS = [
  { key: 'sponsorships', label: 'Sponsorluklar', icon: 'fa-list' },
  { key: 'calendar',     label: 'Yayın Takvimi', icon: 'fa-calendar-day' },
  { key: 'simulate',     label: 'Simülasyon',    icon: 'fa-flask' },
  { key: 'copy',         label: 'Kopyala',       icon: 'fa-copy' },
];

// ─── Sponsorluklar sekmesi ────────────────────────────────────────────────────
const kioskSummary   = ref(null);
const rows           = ref([]);           // düzenlenebilir atamalar
const savedSnapshot  = ref('[]');
const sponLoading    = ref(false);
const saving         = ref(false);
const allCampaigns   = ref([]);
const addCampaignId  = ref(null);
const capacityConflicts = ref([]);
const previewInfo    = ref(null);         // {assignments:[{campaign_id, requested, placed}], ...}

const dirty = computed(() => JSON.stringify(rows.value) !== savedSnapshot.value);

async function loadCampaignsOnce() {
  if (allCampaigns.value.length) return;
  try {
    const { data } = await listCampaignsV2();
    allCampaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch { /* non-critical */ }
}

function mapItemToRow(it) {
  return {
    campaign_id: it.campaign_id,
    campaign_name: it.campaign_name,
    advertiser_name: it.advertiser_name || '',
    creative_durations: it.creative_durations || [],
    window_start: it.window_start || '08:00',
    window_end: it.window_end || '19:00',
    count: it.count ?? 1,
    active_weekdays: Array.isArray(it.active_weekdays) ? [...it.active_weekdays] : [],
    start_date: it.start_date || '',
    end_date: it.end_date || '',
    is_active: it.is_active !== false,
  };
}

async function loadSponsorships(kioskId) {
  sponLoading.value = true;
  capacityConflicts.value = [];
  try {
    await loadCampaignsOnce();
    const { data } = await getKioskSponsorships(kioskId);
    kioskSummary.value = data.kiosk || null;
    rows.value = (data.items || []).map(mapItemToRow);
    savedSnapshot.value = JSON.stringify(rows.value);
    addCampaignId.value = null;
    refreshPreview();
  } catch {
    toast.error('Kiosk sponsorlukları yüklenemedi.');
  } finally { sponLoading.value = false; }
}

const availableCampaigns = computed(() => {
  const used = new Set(rows.value.map((r) => String(r.campaign_id)));
  return allCampaigns.value
    .filter((c) => !used.has(String(c.id)))
    .map((c) => ({ id: c.id, label: c.name, sub: c.advertiser_name || '' }));
});

function addRow() {
  if (!addCampaignId.value) return;
  const c = allCampaigns.value.find((x) => String(x.id) === String(addCampaignId.value));
  if (!c) return;
  rows.value.push(mapItemToRow({
    campaign_id: c.id,
    campaign_name: c.name,
    advertiser_name: c.advertiser_name,
    creative_durations: (c.creatives || []).map((cr) => cr.duration_seconds),
    window_start: '08:00', window_end: '19:00', count: 10,
    active_weekdays: [], start_date: '', end_date: '', is_active: true,
  }));
  addCampaignId.value = null;
  refreshPreview();
}

function removeRow(idx) {
  rows.value.splice(idx, 1);
  refreshPreview();
}

function toggleWeekday(row, value) {
  const i = row.active_weekdays.indexOf(value);
  if (i >= 0) row.active_weekdays.splice(i, 1);
  else row.active_weekdays.push(value);
}

function rowMinDuration(row) {
  const ds = (row.creative_durations || []).filter((d) => d > 0);
  return ds.length ? Math.min(...ds) : 15;
}
function rowHint(row) { return maxCountHint(row.window_start, row.window_end, rowMinDuration(row)); }
function rowErrors(row) { return validateRow(row, rowMinDuration(row)).errors; }

const allRowsValid = computed(() => rows.value.every((r) => validateRow(r, rowMinDuration(r)).valid));

// Debounced kapasite önizlemesi (requested vs placed)
let _previewTimer = null;
function refreshPreview() {
  clearTimeout(_previewTimer);
  _previewTimer = setTimeout(doPreview, 450);
}
async function doPreview() {
  if (!selectedKioskId.value || !rows.value.length) { previewInfo.value = null; return; }
  if (!allRowsValid.value) { previewInfo.value = null; return; }
  try {
    const { data } = await previewKioskSponsorships(selectedKioskId.value, {
      date: getIstanbulToday(),
      items: rows.value.map(rowToPayload),
    });
    previewInfo.value = data;
  } catch { previewInfo.value = null; }
}

watch(rows, refreshPreview, { deep: true });

function previewForRow(row) {
  const a = previewInfo.value?.assignments?.find((x) => String(x.campaign_id) === String(row.campaign_id));
  return a || null;
}

const totalUtilization = computed(() => {
  const hrs = previewInfo.value?.hours || [];
  if (!hrs.length) return 0;
  const used = hrs.reduce((s, h) => s + (h.used_seconds || 0), 0);
  const active = hrs.filter((h) => h.item_count > 0).length || 1;
  return used / (active * 3600);
});

async function save() {
  if (!allRowsValid.value) { toast.error('Geçersiz satırlar var, lütfen düzeltin.'); return; }
  saving.value = true;
  capacityConflicts.value = [];
  try {
    const { data } = await putKioskSponsorships(selectedKioskId.value, rows.value.map(rowToPayload));
    kioskSummary.value = data.kiosk || kioskSummary.value;
    rows.value = (data.items || []).map(mapItemToRow);
    savedSnapshot.value = JSON.stringify(rows.value);
    toast.success('Sponsorluklar kaydedildi.');
    loadKiosks();
    refreshPreview();
  } catch (e) {
    const cap = extractCapacityError(e);
    if (cap) {
      capacityConflicts.value = cap.conflicts;
      toast.error(cap.detail);
      // State kirli kalır — kullanıcı düzeltsin.
    } else {
      toast.error(e?.response?.data?.detail || 'Kaydetme başarısız.');
    }
  } finally { saving.value = false; }
}

function discard() {
  rows.value = JSON.parse(savedSnapshot.value);
  capacityConflicts.value = [];
  refreshPreview();
}

// ─── Yayın Takvimi sekmesi ────────────────────────────────────────────────────
const calDate     = ref(getIstanbulToday());
const calMode     = ref('draft');   // 'draft' | 'published'
const calLoading  = ref(false);
const calData     = ref(null);      // {hours:[{hour,used_seconds,item_count,utilization}], items:[...]}
const calSelectedHour = ref(null);

function normalizeStream(raw) {
  // preview şekli: {hours:[{hour,used_seconds,item_count,utilization}], items:[...]}
  if (raw?.items && raw?.hours && raw.hours[0] && 'utilization' in raw.hours[0]) {
    return { hours: raw.hours, items: raw.items };
  }
  // day-stream şekli: {hours:[{target_hour, items:[{estimated_start_offset_seconds, duration_seconds,...}]}]}
  const items = [];
  const hours = Array.from({ length: 24 }, (_, hour) => ({ hour, used_seconds: 0, item_count: 0, utilization: 0 }));
  for (const hp of raw?.hours || []) {
    const hour = hp.target_hour ?? hp.hour ?? 0;
    for (const it of hp.items || []) {
      const offset = it.estimated_start_offset_seconds ?? it.offset ?? 0;
      const duration = it.duration_seconds ?? it.duration ?? 0;
      const startSec = hour * 3600 + offset;
      items.push({
        hour, offset, duration,
        start_second: startSec,
        start: secondToHHMMSS(startSec),
        end: secondToHHMMSS(startSec + duration),
        campaign_name: it.campaign_name || it.name || '—',
        advertiser_name: it.advertiser_name || '',
        creative_name: it.creative_name || it.name || '',
        media_url: it.media_url || '',
        active_media_url: it.active_media_url || '',
      });
      hours[hour].used_seconds += duration;
      hours[hour].item_count += 1;
    }
  }
  for (const h of hours) h.utilization = Math.min(1, h.used_seconds / 3600);
  return { hours, items };
}

async function loadCalendar() {
  if (!selectedKioskId.value) return;
  calLoading.value = true;
  calData.value = null;
  calSelectedHour.value = null;
  try {
    let raw;
    if (calMode.value === 'draft') {
      const { data } = await previewKioskSponsorships(selectedKioskId.value, {
        date: calDate.value,
        items: rows.value.map(rowToPayload),
      });
      raw = data;
    } else {
      const { data } = await getKioskDayStream(selectedKioskId.value, calDate.value);
      raw = data;
    }
    calData.value = normalizeStream(raw);
  } catch (e) {
    const cap = extractCapacityError(e);
    toast.error(cap?.detail || 'Yayın takvimi yüklenemedi.');
  } finally { calLoading.value = false; }
}

watch([calDate, calMode, activeTab], () => {
  if (activeTab.value === 'calendar') loadCalendar();
});

const calHours = computed(() => calData.value?.hours || []);
function hourStyle(h) { return { background: heatmapColor(h.utilization) }; }
function selectHour(h) { calSelectedHour.value = calSelectedHour.value === h.hour ? null : h.hour; }

const selectedHourTimeline = computed(() => {
  if (calSelectedHour.value == null || !calData.value) return [];
  return hourTimeline(calData.value.items, calSelectedHour.value);
});

const isToday = computed(() => calDate.value === getIstanbulToday());
const nowMarker = computed(() => {
  if (!isToday.value || calSelectedHour.value == null) return null;
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  if (now.getHours() !== calSelectedHour.value) return null;
  return ((now.getMinutes() * 60 + now.getSeconds()) / 3600) * 100;
});

// Her sponsorluğa sabit bir renk (dakika şeridi blokları için)
const BLOCK_COLORS = ['#B1121B', '#0F8F8A', '#2563EB', '#D97706', '#7C3AED', '#059669', '#DB2777', '#4B5563'];
const campaignColorMap = computed(() => {
  const map = {};
  let i = 0;
  for (const it of calData.value?.items || []) {
    const key = it.campaign_name;
    if (!(key in map)) map[key] = BLOCK_COLORS[i++ % BLOCK_COLORS.length];
  }
  return map;
});
function blockColor(name) { return campaignColorMap.value[name] || '#6B7280'; }

// ─── Simülasyon sekmesi ───────────────────────────────────────────────────────
const sim = reactive({
  date_from: getIstanbulToday(),
  date_to: getIstanbulToday(),
  include_existing: true,
  duration: 15,
  customDuration: 15,
  window_start: '08:00',
  window_end: '19:00',
  weekdays: [],
});
const simLoading = ref(false);
const simResult  = ref(null);
const scenario   = ref([]);

function toggleSimWeekday(v) {
  const i = sim.weekdays.indexOf(v);
  if (i >= 0) sim.weekdays.splice(i, 1); else sim.weekdays.push(v);
}
function addScenarioLine() {
  scenario.value.push({
    label: `Senaryo ${scenario.value.length + 1}`,
    duration_seconds: 15, count: 50,
    window_start: '08:00', window_end: '19:00', active_weekdays: [],
  });
}
function removeScenarioLine(idx) { scenario.value.splice(idx, 1); }

function simDuration() {
  return sim.duration === 'custom' ? Number(sim.customDuration) : Number(sim.duration);
}

async function runSimulation() {
  if (!selectedKioskId.value) return;
  simLoading.value = true;
  simResult.value = null;
  try {
    const body = {
      date_from: sim.date_from,
      date_to: sim.date_to,
      include_existing: sim.include_existing,
      probe: {
        duration_seconds: simDuration(),
        window_start: sim.window_start,
        window_end: sim.window_end,
        active_weekdays: sim.weekdays.length ? [...sim.weekdays] : null,
      },
      scenario: scenario.value.map((s) => ({
        label: s.label,
        duration_seconds: Number(s.duration_seconds),
        count: Number(s.count),
        window_start: s.window_start,
        window_end: s.window_end,
        active_weekdays: s.active_weekdays.length ? [...s.active_weekdays] : null,
      })),
    };
    const { data } = await simulateKioskSponsorship(selectedKioskId.value, body);
    simResult.value = data;
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Simülasyon başarısız.');
  } finally { simLoading.value = false; }
}

// ─── Kopyala sekmesi ──────────────────────────────────────────────────────────
const copyTargets   = ref([]);        // seçili hedef kiosk id'leri
const copyPreview    = ref(null);     // dry_run yanıtı
const copyLoading    = ref(false);
const copySearch     = ref('');

const copyCandidates = computed(() =>
  kiosks.value.filter((k) => String(k.id) !== String(selectedKioskId.value))
    .filter((k) => {
      const q = copySearch.value.trim().toLocaleLowerCase('tr');
      if (!q) return true;
      return `${k.ad || ''} ${k.eczane_adi || ''}`.toLocaleLowerCase('tr').includes(q);
    })
);
function toggleCopyTarget(id) {
  const i = copyTargets.value.indexOf(id);
  if (i >= 0) copyTargets.value.splice(i, 1); else copyTargets.value.push(id);
}

async function previewCopy() {
  if (!copyTargets.value.length) { toast.warning('En az bir hedef kiosk seçin.'); return; }
  copyLoading.value = true;
  copyPreview.value = null;
  try {
    const { data } = await copyKioskSponsorships(selectedKioskId.value, {
      target_kiosk_ids: copyTargets.value, dry_run: true,
    });
    copyPreview.value = data;
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Önizleme başarısız.');
  } finally { copyLoading.value = false; }
}

async function confirmCopy() {
  const ok = await confirm({
    title: 'Takvim Kopyalama',
    message: `${copyTargets.value.length} kioskun mevcut sponsorluk takvimi tamamen SİLİNİP bu kioskunkiyle değiştirilecek. Onaylıyor musunuz?`,
    confirmLabel: 'Evet, Üzerine Yaz', variant: 'danger',
  });
  if (!ok) return;
  copyLoading.value = true;
  try {
    await copyKioskSponsorships(selectedKioskId.value, {
      target_kiosk_ids: copyTargets.value, dry_run: false,
    });
    toast.success('Takvim kopyalandı.');
    copyPreview.value = null;
    copyTargets.value = [];
    loadKiosks();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Kopyalama başarısız.');
  } finally { copyLoading.value = false; }
}

onMounted(loadKiosks);
</script>

<template>
  <div class="eisa-page kiosk-spon">
    <div class="eisa-page-header">
      <div>
        <h1 class="eisa-page-title">Kiosk Sponsorluk</h1>
        <p class="eisa-page-subtitle">Her kiosk için sponsorluk atamalarını cihaz bazlı yönetin.</p>
      </div>
    </div>

    <div class="ks-layout">
      <!-- Sol: kiosk listesi -->
      <aside class="ks-list eisa-card">
        <div class="ks-list-search">
          <div class="eisa-input-group">
            <i class="fa-solid fa-magnifying-glass" style="padding:0 .6rem;color:#9CA3AF"></i>
            <input v-model="kioskSearch" class="eisa-field" placeholder="Kiosk / eczane ara…" />
          </div>
          <label class="ks-filter">
            <input type="checkbox" v-model="onlyUnassigned" /> Atanmamış
          </label>
        </div>
        <div v-if="kiosksLoading" class="ks-empty">Yükleniyor…</div>
        <div v-else-if="!kiosks.length" class="ks-empty">Kiosk bulunamadı.</div>
        <ul v-else class="ks-kiosks">
          <li
            v-for="k in kiosks"
            :key="k.id"
            class="ks-kiosk"
            :class="{ 'ks-kiosk--active': String(k.id) === String(selectedKioskId) }"
            @click="selectKiosk(k)"
          >
            <span class="ks-dot" :class="k.is_online ? 'ks-dot--on' : 'ks-dot--off'"></span>
            <div class="ks-kiosk-meta">
              <strong>{{ k.ad }}</strong>
              <span class="ks-kiosk-sub">{{ k.eczane_adi }}</span>
              <span class="ks-kiosk-sub ks-kiosk-loc">{{ [k.il_adi, k.ilce_adi].filter(Boolean).join(' / ') }}</span>
            </div>
            <span
              class="ks-count"
              :class="{ 'ks-count--zero': !k.sponsorship_count }"
            >{{ k.sponsorship_count ?? 0 }}</span>
          </li>
        </ul>
      </aside>

      <!-- Sağ: seçili kiosk -->
      <section class="ks-detail eisa-card">
        <div v-if="!selectedKioskId" class="ks-placeholder">
          <i class="fa-solid fa-hand-pointer"></i>
          <p>Yönetmek için soldan bir kiosk seçin.</p>
        </div>

        <template v-else>
          <header class="ks-detail-head">
            <div>
              <h2 class="ks-detail-title">{{ selectedKiosk?.ad }}</h2>
              <p class="ks-detail-sub">
                {{ selectedKiosk?.eczane_adi }}
                <span v-if="selectedKiosk?.il_adi"> · {{ [selectedKiosk?.il_adi, selectedKiosk?.ilce_adi].filter(Boolean).join(' / ') }}</span>
              </p>
            </div>
            <span class="eisa-pill" :class="selectedKiosk?.is_online ? 'eisa-pill-success' : 'eisa-pill-muted'">
              <i class="fa-solid fa-circle" style="font-size:.5rem"></i>
              {{ selectedKiosk?.is_online ? 'Çevrimiçi' : 'Çevrimdışı' }}
            </span>
          </header>

          <nav class="ks-tabs">
            <button
              v-for="t in TABS" :key="t.key"
              class="ks-tab" :class="{ 'ks-tab--active': activeTab === t.key }"
              @click="activeTab = t.key"
            >
              <i class="fa-solid" :class="t.icon"></i> {{ t.label }}
            </button>
          </nav>

          <!-- ══════ Sponsorluklar ══════ -->
          <div v-show="activeTab === 'sponsorships'" class="ks-pane">
            <div v-if="sponLoading" class="ks-empty">Yükleniyor…</div>
            <template v-else>
              <div class="ks-add-row">
                <EisaLookup
                  v-model="addCampaignId"
                  :options="availableCampaigns"
                  placeholder="Sponsorluk ekle (ara)…"
                  style="flex:1"
                />
                <button class="eisa-btn eisa-btn-cta" :disabled="!addCampaignId" @click="addRow">
                  <i class="fa-solid fa-plus"></i> Ekle
                </button>
              </div>

              <div v-if="capacityConflicts.length" class="ks-conflict">
                <strong><i class="fa-solid fa-triangle-exclamation"></i> Kapasite aşıldı</strong>
                <ul>
                  <li v-for="(c, i) in capacityConflicts" :key="i">
                    {{ c.date }} — {{ c.campaign_name }}: istenen {{ c.requested }}, yerleşen {{ c.placed }}
                  </li>
                </ul>
              </div>

              <div v-if="!rows.length" class="ks-empty">
                Bu kioska henüz sponsorluk atanmamış. Yukarıdan ekleyin.
              </div>

              <table v-else class="eisa-table ks-table">
                <thead>
                  <tr>
                    <th>Sponsorluk</th>
                    <th>Pencere</th>
                    <th>Sayı</th>
                    <th>Günler</th>
                    <th>Tarih Aralığı</th>
                    <th>Aktif</th>
                    <th>Kapasite</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in rows" :key="row.campaign_id" :class="{ 'ks-row--invalid': rowErrors(row).length }">
                    <td>
                      <strong>{{ row.campaign_name }}</strong>
                      <span v-if="row.advertiser_name" class="cell-muted">{{ row.advertiser_name }}</span>
                    </td>
                    <td class="ks-window">
                      <input type="time" v-model="row.window_start" class="eisa-field ks-time" />
                      <span>–</span>
                      <input type="time" v-model="row.window_end" class="eisa-field ks-time" />
                    </td>
                    <td>
                      <input type="number" min="1" v-model.number="row.count" class="eisa-field ks-num" />
                      <span v-if="rowHint(row)" class="cell-muted ks-hint">max ~{{ rowHint(row) }}</span>
                    </td>
                    <td>
                      <div class="ks-weekdays">
                        <button
                          v-for="w in WEEKDAYS" :key="w.value"
                          type="button" class="ks-chip"
                          :class="{ 'ks-chip--on': row.active_weekdays.includes(w.value) }"
                          :title="w.full"
                          @click="toggleWeekday(row, w.value)"
                        >{{ w.label }}</button>
                      </div>
                      <span class="cell-muted ks-hint">{{ weekdaysText(row.active_weekdays) }}</span>
                    </td>
                    <td class="ks-dates">
                      <input type="date" v-model="row.start_date" class="eisa-field ks-date" />
                      <input type="date" v-model="row.end_date" class="eisa-field ks-date" />
                    </td>
                    <td>
                      <label class="ks-switch">
                        <input type="checkbox" v-model="row.is_active" />
                        <span class="ks-switch-track"></span>
                      </label>
                    </td>
                    <td class="ks-cap-cell">
                      <template v-if="previewForRow(row)">
                        <span :class="previewForRow(row).unplaced > 0 ? 'eisa-pill eisa-pill-danger' : 'eisa-pill eisa-pill-success'">
                          {{ previewForRow(row).placed }}/{{ previewForRow(row).requested }}
                        </span>
                      </template>
                      <span v-else class="cell-muted">—</span>
                    </td>
                    <td>
                      <button class="eisa-icon-btn danger" title="Kaldır" @click="removeRow(idx)">
                        <i class="fa-solid fa-trash"></i>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div v-if="rows.length" class="ks-util">
                Toplam doluluk: <strong>{{ Math.round(totalUtilization * 100) }}%</strong>
              </div>

              <div v-for="(row, idx) in rows" :key="'err-'+idx">
                <p v-for="(e, ei) in rowErrors(row)" :key="ei" class="ks-row-error">
                  <i class="fa-solid fa-circle-exclamation"></i> {{ row.campaign_name }}: {{ e }}
                </p>
              </div>

              <div class="ks-actions">
                <button class="eisa-btn eisa-btn-ghost" :disabled="!dirty || saving" @click="discard">Vazgeç</button>
                <button class="eisa-btn eisa-btn-cta" :disabled="!dirty || saving || !allRowsValid" @click="save">
                  <i class="fa-solid fa-floppy-disk"></i> {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
                </button>
              </div>
            </template>
          </div>

          <!-- ══════ Yayın Takvimi ══════ -->
          <div v-show="activeTab === 'calendar'" class="ks-pane">
            <div class="ks-cal-controls">
              <input type="date" v-model="calDate" class="eisa-field ks-date" />
              <div class="ks-mode-toggle">
                <button :class="{ 'ks-mode--on': calMode === 'draft' }" @click="calMode = 'draft'">Taslak (kaydedilmemiş)</button>
                <button :class="{ 'ks-mode--on': calMode === 'published' }" @click="calMode = 'published'">Yayında</button>
              </div>
              <button class="eisa-btn" @click="loadCalendar"><i class="fa-solid fa-rotate"></i> Yenile</button>
            </div>

            <div v-if="calLoading" class="ks-empty">Yükleniyor…</div>
            <template v-else-if="calData">
              <div class="ks-heatmap">
                <button
                  v-for="h in calHours" :key="h.hour"
                  class="ks-hour" :class="{ 'ks-hour--active': calSelectedHour === h.hour }"
                  :style="hourStyle(h)"
                  :title="`${String(h.hour).padStart(2,'0')}:00 — %${Math.round((h.utilization||0)*100)} doluluk, ${h.item_count||0} öğe`"
                  @click="selectHour(h)"
                >
                  <span class="ks-hour-label">{{ String(h.hour).padStart(2,'0') }}</span>
                </button>
              </div>

              <div v-if="calSelectedHour != null" class="ks-minute">
                <h4 class="ks-minute-title">{{ String(calSelectedHour).padStart(2,'0') }}:00 — {{ String(calSelectedHour).padStart(2,'0') }}:59</h4>
                <div class="ks-minute-bar">
                  <div
                    v-for="(it, i) in selectedHourTimeline" :key="i"
                    class="ks-block"
                    :style="{ left: it.leftPct + '%', width: it.widthPct + '%', background: blockColor(it.campaign_name) }"
                    :title="`${it.start} – ${it.end} · ${it.campaign_name} · ${it.duration}s`"
                  ></div>
                  <div v-if="nowMarker != null" class="ks-now" :style="{ left: nowMarker + '%' }" title="Şimdi"></div>
                </div>

                <ul class="ks-stream-list">
                  <li v-for="(it, i) in selectedHourTimeline" :key="'s'+i" class="ks-stream-item">
                    <span class="ks-stream-color" :style="{ background: blockColor(it.campaign_name) }"></span>
                    <span class="ks-stream-time">{{ it.start }} – {{ it.end }}</span>
                    <div class="ks-thumb">
                      <video v-if="isVideoUrl(it.media_url)" :src="it.media_url" muted preload="metadata" />
                      <img v-else-if="it.media_url" :src="it.media_url" :alt="it.campaign_name" @error="(e)=>e.target.style.display='none'" />
                      <i v-else class="fa-solid fa-image"></i>
                    </div>
                    <div class="ks-stream-meta">
                      <strong>{{ it.campaign_name }}</strong>
                      <span class="cell-muted">{{ it.duration }}s</span>
                    </div>
                  </li>
                  <li v-if="!selectedHourTimeline.length" class="ks-empty">Bu saatte öğe yok.</li>
                </ul>
              </div>
              <p v-else class="ks-hint-block">Dakika dağılımını görmek için bir saate tıklayın.</p>
            </template>
            <div v-else class="ks-empty">Veri yok.</div>
          </div>

          <!-- ══════ Simülasyon ══════ -->
          <div v-show="activeTab === 'simulate'" class="ks-pane">
            <h4 class="ks-sec-title">Probe — bu kioska kaç gösterim sığar?</h4>
            <div class="ks-sim-form">
              <label class="eisa-field-label">Süre (sn)
                <select v-model="sim.duration" class="eisa-field">
                  <option :value="15">15</option>
                  <option :value="30">30</option>
                  <option :value="45">45</option>
                  <option :value="60">60</option>
                  <option value="custom">Özel</option>
                </select>
              </label>
              <label v-if="sim.duration === 'custom'" class="eisa-field-label">Özel süre
                <input type="number" min="1" max="60" v-model.number="sim.customDuration" class="eisa-field ks-num" />
              </label>
              <label class="eisa-field-label">Başlangıç
                <input type="time" v-model="sim.window_start" class="eisa-field ks-time" />
              </label>
              <label class="eisa-field-label">Bitiş
                <input type="time" v-model="sim.window_end" class="eisa-field ks-time" />
              </label>
              <label class="eisa-field-label">Baş. tarih
                <input type="date" v-model="sim.date_from" class="eisa-field ks-date" />
              </label>
              <label class="eisa-field-label">Bit. tarih
                <input type="date" v-model="sim.date_to" class="eisa-field ks-date" />
              </label>
            </div>
            <div class="ks-weekdays" style="margin:.5rem 0">
              <button
                v-for="w in WEEKDAYS" :key="w.value" type="button" class="ks-chip"
                :class="{ 'ks-chip--on': sim.weekdays.includes(w.value) }"
                @click="toggleSimWeekday(w.value)"
              >{{ w.label }}</button>
            </div>
            <label class="ks-filter">
              <input type="checkbox" v-model="sim.include_existing" /> Mevcut sponsorlukları dahil et
            </label>

            <h4 class="ks-sec-title" style="margin-top:1rem">Senaryo hesaplayıcı</h4>
            <table v-if="scenario.length" class="eisa-table ks-table">
              <thead>
                <tr><th>Etiket</th><th>Süre</th><th>Adet</th><th>Pencere</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="(s, i) in scenario" :key="i">
                  <td><input v-model="s.label" class="eisa-field" /></td>
                  <td><input type="number" min="1" max="60" v-model.number="s.duration_seconds" class="eisa-field ks-num" /></td>
                  <td><input type="number" min="1" v-model.number="s.count" class="eisa-field ks-num" /></td>
                  <td class="ks-window">
                    <input type="time" v-model="s.window_start" class="eisa-field ks-time" />
                    <span>–</span>
                    <input type="time" v-model="s.window_end" class="eisa-field ks-time" />
                  </td>
                  <td><button class="eisa-icon-btn danger" @click="removeScenarioLine(i)"><i class="fa-solid fa-trash"></i></button></td>
                </tr>
              </tbody>
            </table>
            <button class="eisa-btn eisa-btn-ghost" @click="addScenarioLine"><i class="fa-solid fa-plus"></i> Senaryo satırı ekle</button>

            <div class="ks-actions">
              <button class="eisa-btn eisa-btn-cta" :disabled="simLoading" @click="runSimulation">
                <i class="fa-solid fa-flask"></i> {{ simLoading ? 'Hesaplanıyor…' : 'Simüle Et' }}
              </button>
            </div>

            <div v-if="simResult" class="ks-sim-result">
              <div v-if="simResult.probe" class="ks-sim-probe">
                <p class="ks-big">
                  En fazla <strong>{{ simResult.probe.max_shows_min }}</strong> gösterim
                  <span class="cell-muted">({{ simResult.probe.duration_seconds }}s · {{ simResult.probe.window_start }}–{{ simResult.probe.window_end }})</span>
                </p>
                <table class="eisa-table ks-table">
                  <thead><tr><th>Tarih</th><th>Max gösterim</th><th>Boş saniye</th></tr></thead>
                  <tbody>
                    <tr v-for="d in simResult.probe.days" :key="d.date">
                      <td>{{ d.date }}</td><td>{{ d.max_shows }}</td><td>{{ d.free_seconds }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="simResult.scenario" class="ks-sim-scenario">
                <p>
                  <span class="eisa-pill" :class="simResult.scenario.feasible ? 'eisa-pill-success' : 'eisa-pill-danger'">
                    {{ simResult.scenario.feasible ? 'Uygulanabilir' : 'Uygulanamaz' }}
                  </span>
                </p>
                <table class="eisa-table ks-table">
                  <thead><tr><th>Satır</th><th>İstenen</th><th>Yerleşen (min)</th><th>Yerleşmeyen (max)</th></tr></thead>
                  <tbody>
                    <tr v-for="(l, i) in simResult.scenario.lines" :key="i">
                      <td>{{ l.label }}</td><td>{{ l.requested }}</td><td>{{ l.placed_min }}</td><td>{{ l.unplaced_max }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- ══════ Kopyala ══════ -->
          <div v-show="activeTab === 'copy'" class="ks-pane">
            <div class="ks-warn">
              <i class="fa-solid fa-triangle-exclamation"></i>
              Hedef kioskların mevcut sponsorluk takvimi tamamen <strong>SİLİNİP üzerine yazılır</strong>.
            </div>
            <div class="eisa-input-group" style="margin:.75rem 0">
              <i class="fa-solid fa-magnifying-glass" style="padding:0 .6rem;color:#9CA3AF"></i>
              <input v-model="copySearch" class="eisa-field" placeholder="Hedef kiosk ara…" />
            </div>
            <ul class="ks-copy-list">
              <li v-for="k in copyCandidates" :key="k.id" class="ks-copy-item">
                <label>
                  <input type="checkbox" :checked="copyTargets.includes(k.id)" @change="toggleCopyTarget(k.id)" />
                  <strong>{{ k.ad }}</strong> <span class="cell-muted">{{ k.eczane_adi }}</span>
                </label>
              </li>
            </ul>

            <div class="ks-actions">
              <button class="eisa-btn" :disabled="!copyTargets.length || copyLoading" @click="previewCopy">
                <i class="fa-solid fa-eye"></i> Önizle
              </button>
              <button class="eisa-btn eisa-btn-danger" :disabled="!copyPreview || copyLoading" @click="confirmCopy">
                <i class="fa-solid fa-copy"></i> Kopyala (Üzerine Yaz)
              </button>
            </div>

            <div v-if="copyPreview" class="ks-copy-preview">
              <p class="cell-muted">Kaynakta {{ copyPreview.item_count }} sponsorluk var.</p>
              <div v-for="t in copyPreview.targets" :key="t.kiosk_id" class="ks-copy-diff">
                <strong>{{ t.kiosk_name }}</strong>
                <span v-if="t.added?.length" class="diff diff-add">+ {{ t.added.join(', ') }}</span>
                <span v-if="t.removed?.length" class="diff diff-rem">− {{ t.removed.join(', ') }}</span>
                <span v-if="t.kept?.length" class="diff diff-keep">= {{ t.kept.join(', ') }}</span>
              </div>
            </div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ks-layout { display: grid; grid-template-columns: 320px 1fr; gap: 1rem; align-items: start; }
.ks-list { padding: .75rem; max-height: calc(100vh - 180px); display: flex; flex-direction: column; }
.ks-list-search { display: flex; flex-direction: column; gap: .5rem; margin-bottom: .5rem; }
.ks-filter { display: inline-flex; align-items: center; gap: .4rem; font-size: .8rem; color: #4B5563; cursor: pointer; }
.ks-kiosks { list-style: none; margin: 0; padding: 0; overflow-y: auto; }
.ks-kiosk { display: flex; align-items: center; gap: .6rem; padding: .55rem .5rem; border-radius: 10px; cursor: pointer; }
.ks-kiosk:hover { background: #F8FAFC; }
.ks-kiosk--active { background: #FFF5F5; box-shadow: inset 0 0 0 1.5px #F3C6C9; }
.ks-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ks-dot--on { background: #10B981; } .ks-dot--off { background: #D1D5DB; }
.ks-kiosk-meta { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.ks-kiosk-meta strong { font-size: .85rem; }
.ks-kiosk-sub { font-size: .72rem; color: #6B7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ks-count { background: #B1121B; color: #fff; border-radius: 999px; min-width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: .72rem; font-weight: 700; padding: 0 .35rem; }
.ks-count--zero { background: #E5E7EB; color: #9CA3AF; }
.ks-empty { padding: 1rem; text-align: center; color: #6B7280; font-size: .85rem; }

.ks-detail { padding: 1rem 1.25rem; min-height: 400px; }
.ks-placeholder { text-align: center; color: #9CA3AF; padding: 4rem 1rem; }
.ks-placeholder i { font-size: 2rem; margin-bottom: .75rem; display: block; }
.ks-detail-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: .75rem; }
.ks-detail-title { font-size: 1.1rem; font-weight: 700; margin: 0; }
.ks-detail-sub { font-size: .8rem; color: #6B7280; margin: .2rem 0 0; }

.ks-tabs { display: flex; gap: .25rem; border-bottom: 1px solid #E5E7EB; margin-bottom: 1rem; flex-wrap: wrap; }
.ks-tab { background: none; border: none; padding: .55rem .85rem; font-size: .85rem; color: #6B7280; cursor: pointer; border-bottom: 2px solid transparent; }
.ks-tab--active { color: #B1121B; border-bottom-color: #B1121B; font-weight: 600; }

.ks-add-row { display: flex; gap: .5rem; margin-bottom: .75rem; }
.ks-table { font-size: .82rem; }
.ks-table td { vertical-align: top; }
.ks-window { display: flex; align-items: center; gap: .25rem; }
.ks-time { width: 92px; padding: .3rem; }
.ks-num { width: 70px; padding: .3rem; }
.ks-date { width: 135px; padding: .3rem; }
.ks-dates { display: flex; flex-direction: column; gap: .25rem; }
.ks-hint { display: block; font-size: .68rem; color: #9CA3AF; }
.ks-weekdays { display: flex; flex-wrap: wrap; gap: .2rem; }
.ks-chip { border: 1px solid #D1D5DB; background: #fff; border-radius: 6px; padding: .12rem .3rem; font-size: .66rem; cursor: pointer; color: #6B7280; }
.ks-chip--on { background: #B1121B; color: #fff; border-color: #B1121B; }
.ks-switch { position: relative; display: inline-block; width: 36px; height: 20px; }
.ks-switch input { opacity: 0; width: 0; height: 0; }
.ks-switch-track { position: absolute; inset: 0; background: #D1D5DB; border-radius: 999px; transition: .2s; }
.ks-switch-track::before { content: ''; position: absolute; width: 14px; height: 14px; left: 3px; top: 3px; background: #fff; border-radius: 50%; transition: .2s; }
.ks-switch input:checked + .ks-switch-track { background: #10B981; }
.ks-switch input:checked + .ks-switch-track::before { transform: translateX(16px); }
.ks-cap-cell { white-space: nowrap; }
.ks-row--invalid td { background: #FFF7F7; }
.ks-row-error { color: #B91C1C; font-size: .75rem; margin: .2rem 0; }
.ks-util { margin: .5rem 0; font-size: .85rem; color: #374151; }
.ks-actions { display: flex; justify-content: flex-end; gap: .5rem; margin-top: 1rem; }
.ks-conflict { background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px; padding: .75rem; margin-bottom: .75rem; font-size: .82rem; color: #991B1B; }
.ks-conflict ul { margin: .35rem 0 0; padding-left: 1.1rem; }

.ks-cal-controls { display: flex; align-items: center; gap: .6rem; margin-bottom: .75rem; flex-wrap: wrap; }
.ks-mode-toggle { display: inline-flex; border: 1px solid #D1D5DB; border-radius: 8px; overflow: hidden; }
.ks-mode-toggle button { background: #fff; border: none; padding: .4rem .7rem; font-size: .78rem; cursor: pointer; color: #6B7280; }
.ks-mode--on { background: #B1121B; color: #fff !important; }
.ks-heatmap { display: grid; grid-template-columns: repeat(24, 1fr); gap: 3px; }
.ks-hour { border: none; height: 44px; border-radius: 4px; cursor: pointer; position: relative; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 2px; }
.ks-hour--active { outline: 2px solid #111827; }
.ks-hour-label { font-size: .6rem; color: #374151; font-weight: 600; }
.ks-minute { margin-top: 1rem; }
.ks-minute-title { font-size: .9rem; margin: 0 0 .5rem; }
.ks-minute-bar { position: relative; height: 28px; background: #F3F4F6; border-radius: 6px; overflow: hidden; }
.ks-block { position: absolute; top: 0; bottom: 0; min-width: 2px; border-radius: 2px; }
.ks-now { position: absolute; top: -3px; bottom: -3px; width: 2px; background: #111827; }
.ks-stream-list { list-style: none; margin: .75rem 0 0; padding: 0; }
.ks-stream-item { display: flex; align-items: center; gap: .6rem; padding: .4rem 0; border-bottom: 1px solid #F3F4F6; }
.ks-stream-color { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.ks-stream-time { font-family: monospace; font-size: .78rem; width: 150px; }
.ks-thumb { width: 44px; height: 44px; border-radius: 6px; overflow: hidden; background: #F3F4F6; display: flex; align-items: center; justify-content: center; color: #9CA3AF; flex-shrink: 0; }
.ks-thumb img, .ks-thumb video { width: 100%; height: 100%; object-fit: cover; }
.ks-stream-meta { display: flex; flex-direction: column; font-size: .82rem; }
.ks-hint-block { color: #6B7280; font-size: .82rem; margin-top: .75rem; }

.ks-sec-title { font-size: .9rem; margin: .5rem 0; }
.ks-sim-form { display: flex; flex-wrap: wrap; gap: .75rem; align-items: end; }
.ks-sim-form label { font-size: .75rem; color: #4B5563; display: flex; flex-direction: column; gap: .2rem; }
.ks-big { font-size: 1rem; }
.ks-sim-result { margin-top: 1rem; }

.ks-warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; padding: .7rem; border-radius: 10px; font-size: .82rem; }
.ks-copy-list { list-style: none; margin: 0; padding: 0; max-height: 240px; overflow-y: auto; }
.ks-copy-item { padding: .35rem 0; font-size: .85rem; }
.ks-copy-item label { display: flex; align-items: center; gap: .5rem; cursor: pointer; }
.ks-copy-preview { margin-top: 1rem; }
.ks-copy-diff { padding: .4rem 0; border-bottom: 1px solid #F3F4F6; font-size: .8rem; display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.diff { font-size: .72rem; }
.diff-add { color: #059669; } .diff-rem { color: #B91C1C; } .diff-keep { color: #6B7280; }

@media (max-width: 900px) { .ks-layout { grid-template-columns: 1fr; } }
</style>
