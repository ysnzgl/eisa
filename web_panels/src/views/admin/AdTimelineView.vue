<script setup>
/**
 * AdTimelineView — Eczane/Kiosk için haftalık takvim ısı haritası.
 * - Önce eczane seç (EisaLookup), sonra eczaneye ait kiosk seç (opsiyonel)
 * - 7 gün × 24 saat heatmap; hücreye tıkla → loop slot detayı açılır
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  generatePlaylists, getCampaignTimeline, getCampaignCalendar, getInventoryAvailability,
} from '../../services/dooh';
import { getPharmacies, getKioskStatus } from '../../services/devices';
import EisaLookup from '../../components/shared/EisaLookup.vue';

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const DAYS  = 7;
const LOOP_SECONDS = 60;

// ── Veri ─────────────────────────────────────────────────────────────────────
const pharmacies      = ref([]);
const kiosks          = ref([]);
const selectedPharmacy = ref(null);
const selectedKiosk   = ref(null);
const startDate       = ref(new Date().toISOString().slice(0, 10));
const calendar        = ref(null);
const calendarLoading = ref(false);

const detailHour   = ref(null);
const detailData   = ref(null);
const detailLoading = ref(false);
const availableSec = ref(null);

const generating = ref(false);
const error = ref('');
const flash = ref('');

// ── Lookup options ────────────────────────────────────────────────────────────
const pharmacyOptions = computed(() =>
  pharmacies.value.map((p) => ({
    id: p.id,
    label: p.name,
    sub: `${p.ilAdi || ''}${p.ilceAdi ? ' / ' + p.ilceAdi : ''}`,
    disabled: (p.kioskCount ?? 0) === 0,
    disabledReason: 'Kiosk yok',
  }))
);

const kioskOptions = computed(() =>
  kiosks.value.map((k) => ({
    id: k.id,
    label: k.ad || `Kiosk #${k.id}`,
    sub: k.mac || '',
  }))
);

// ── Renk paleti ───────────────────────────────────────────────────────────────
const PALETTE = ['#6366f1', '#0ea5e9', '#f59e0b', '#10b981', '#ef4444',
                 '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16'];
const colorCache = new Map();
function colorFor(name) {
  if (!name) return '#94a3b8';
  if (!colorCache.has(name)) colorCache.set(name, PALETTE[colorCache.size % PALETTE.length]);
  return colorCache.get(name);
}

// ── Tarih listesi ─────────────────────────────────────────────────────────────
const dateList = computed(() => {
  const out = [];
  const d = new Date(startDate.value);
  for (let i = 0; i < DAYS; i++) {
    const x = new Date(d); x.setDate(d.getDate() + i);
    out.push(x.toISOString().slice(0, 10));
  }
  return out;
});

const DAY_LABELS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
function dayLabel(iso) {
  const d = new Date(iso);
  const idx = (d.getDay() + 6) % 7;
  return `${DAY_LABELS[idx]} ${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}`;
}

// ── Yükleme ───────────────────────────────────────────────────────────────────
async function loadPharmacies() {
  try {
    pharmacies.value = await getPharmacies();
    if (!selectedPharmacy.value && pharmacies.value.length) {
      selectedPharmacy.value = pharmacies.value[0].id;
    }
  } catch {
    error.value = 'Eczane listesi yüklenemedi';
  }
}

async function loadKiosks() {
  kiosks.value = [];
  selectedKiosk.value = null;
  if (!selectedPharmacy.value) return;
  try {
    kiosks.value = await getKioskStatus(selectedPharmacy.value);
    if (kiosks.value.length) selectedKiosk.value = kiosks.value[0].id;
  } catch {
    error.value = 'Kiosk listesi yüklenemedi';
  }
}

async function loadCalendar() {
  if (!selectedKiosk.value) { calendar.value = null; return; }
  calendarLoading.value = true; error.value = '';
  try {
    const { data } = await getCampaignCalendar({
      kiosk: selectedKiosk.value, start: startDate.value, days: DAYS,
    });
    calendar.value = data;
  } catch (e) {
    error.value = e?.response?.data?.error || 'Takvim yüklenemedi';
    calendar.value = null;
  } finally {
    calendarLoading.value = false;
  }
}

function getCell(date, hour) {
  if (!calendar.value?.cells) return null;
  return calendar.value.cells[date]?.[hour] ?? calendar.value.cells[date]?.[String(hour)] ?? null;
}

function cellClass(cell) {
  if (!cell) return 'cell-empty';
  const p = cell.fill_pct;
  if (p === 0)  return 'cell-empty';
  if (p < 25)   return 'cell-low';
  if (p < 60)   return 'cell-med';
  if (p < 90)   return 'cell-high';
  return 'cell-full';
}

// openDetail: iki çağrıyı bağımsız yapıyoruz (inventory fail olsa detay gene görünsün)
async function openDetail(date, hour) {
  if (!selectedKiosk.value) return;
  detailHour.value = { date, hour };
  detailData.value = null;
  availableSec.value = null;
  detailLoading.value = true;
  error.value = '';
  try {
    const params = { kiosk: selectedKiosk.value, date, hour };
    const { data } = await getCampaignTimeline(params);
    detailData.value = data;
    // Inventory opsiyonel — hata olsa bile detayı kapatmıyoruz
    try {
      const av = await getInventoryAvailability(params);
      availableSec.value = av.data?.available_seconds ?? null;
    } catch { /* sessizce geç */ }
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.response?.data?.error || 'Detay yüklenemedi';
  } finally {
    detailLoading.value = false;
  }
}
function closeDetail() { detailHour.value = null; detailData.value = null; }

const loopSummary = computed(() => {
  const tl = detailData.value;
  if (!tl || !Array.isArray(tl.items) || !tl.items.length) return [];
  const loopSec = Number(tl.loop_duration_seconds) || LOOP_SECONDS;
  const groups = new Map();
  for (const item of tl.items) {
    const offsetAbs = Number(item.estimated_start_offset_seconds);
    const idx = Math.floor(offsetAbs / loopSec);
    if (!groups.has(idx)) groups.set(idx, []);
    const label = item.campaign_name || `Slot #${item.playback_order}`;
    groups.get(idx).push({
      label,
      offset:   offsetAbs - idx * loopSec,
      duration: Number(item.duration_seconds) || 0,
      type:     item.asset_type,
      color:    item.asset_type === 'house_ad' ? '#94a3b8' : colorFor(label),
    });
  }
  return Array.from(groups.entries()).sort(([a], [b]) => a - b).map(([loop_index, items]) => {
    const sorted = [...items].sort((a, b) => a.offset - b.offset);
    const used = sorted.reduce((s, it) => s + it.duration, 0);
    return { loop_index, used, free: Math.max(0, loopSec - used), items: sorted };
  });
});

async function regenerate(scope) {
  // scope: 'kiosk' | 'pharmacy' | 'all'
  if (scope === 'kiosk' && !selectedKiosk.value) return;
  generating.value = true; error.value = ''; flash.value = '';
  try {
    const payload = { date: startDate.value };
    if (scope === 'kiosk') payload.kiosk = selectedKiosk.value;
    const resp = await generatePlaylists(payload);
    const d = resp.data || {};
    flash.value = `✓ ${d.kiosk_count ?? '?' } kiosk için ${d.playlists_generated ?? '?'} playlist üretildi.`;
    await loadCalendar();
    if (detailHour.value) await openDetail(detailHour.value.date, detailHour.value.hour);
  } catch (e) {
    error.value = e?.response?.data?.error || 'Playlist üretimi başarısız';
  } finally { generating.value = false; }
}

// Eczane seçilince kiosk listesini yenile
watch(selectedPharmacy, async () => {
  await loadKiosks();
  await loadCalendar();
});
watch([selectedKiosk, startDate], loadCalendar);

// Auto-refresh: CampaignWizard'da playlist üretilince localStorage key set edilir
let _storageListener = null;
onMounted(async () => {
  await loadPharmacies();
  await loadKiosks();
  await loadCalendar();
  _storageListener = (e) => { if (e.key === 'dooh_playlist_ts') loadCalendar(); };
  window.addEventListener('storage', _storageListener);
});
onBeforeUnmount(() => {
  if (_storageListener) window.removeEventListener('storage', _storageListener);
});
</script>

<template>
  <div class="eisa-page ad-timeline">

    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">DOOH Yönetimi</p>
        <h1 class="eisa-page-title">Reklam Takvimi</h1>
        <p class="eisa-page-subtitle">Eczane bazlı 7 günlük yayın doluluk haritası — hücreye tıkla, loop detayını gör</p>
      </div>
    </div>

    <!-- Kullanım ipucu -->
    <div class="ad-timeline-hint">
      <span class="hint-step">1</span> <span>Kampanya oluştur</span>
      <span class="hint-arrow">→</span>
      <span class="hint-step">2</span> <span>Eczane seç, playlist üret</span>
      <span class="hint-arrow">→</span>
      <span class="hint-step">3</span> <span>Hücreyi tıkla, slot detayını gör</span>
    </div>

    <!-- Filtreler -->
    <div class="eisa-panel">
      <div class="ad-timeline-filters">
        <div class="eisa-field" style="flex:2; min-width:220px;">
          <label class="eisa-field-label">Eczane</label>
          <EisaLookup
            v-model="selectedPharmacy"
            :options="pharmacyOptions"
            placeholder="Eczane ara (ad / il / ilçe)…"
          />
        </div>
        <div class="eisa-field" style="flex:1.5; min-width:180px;">
          <label class="eisa-field-label">Kiosk</label>
          <EisaLookup
            v-model="selectedKiosk"
            :options="kioskOptions"
            placeholder="Kiosk seç…"
            :clearable="false"
          />
        </div>
        <div class="eisa-field">
          <label class="eisa-field-label">Başlangıç tarihi</label>
          <input type="date" v-model="startDate" class="eisa-input" />
        </div>
        <div class="ad-timeline-actions">
          <button class="eisa-btn eisa-btn-ghost" :disabled="calendarLoading" @click="loadCalendar">
            <i class="fa-solid fa-rotate" :class="{ 'fa-spin': calendarLoading }"></i>
          </button>
          <button class="eisa-btn eisa-btn-cta"
                  :disabled="generating || !selectedKiosk" @click="regenerate('kiosk')">
            {{ generating ? 'Üretiliyor…' : 'Bu Kiosk için Üret' }}
          </button>
          <button class="eisa-btn eisa-btn-ghost"
                  :disabled="generating" @click="regenerate('all')">
            Tüm Kiosklar
          </button>
        </div>
      </div>
    </div>

    <div v-if="flash" class="eisa-toast-success">{{ flash }}</div>
    <div v-if="error" class="eisa-toast-error">{{ error }}</div>

    <!-- Heatmap -->
    <div class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">
          Doluluk Isı Haritası — {{ DAYS }} gün × 24 saat
          <span v-if="selectedKiosk && kiosks.length" class="muted" style="font-size:0.85rem; font-weight:400;">
            ({{ kioskOptions.find(k=>k.id===selectedKiosk)?.label || 'Kiosk' }})
          </span>
        </h2>
      </div>

      <div class="heatmap-legend">
        <span class="legend-cell cell-empty"></span> Boş
        <span class="legend-cell cell-low"></span> &lt;%25
        <span class="legend-cell cell-med"></span> &lt;%60
        <span class="legend-cell cell-high"></span> &lt;%90
        <span class="legend-cell cell-full"></span> Dolu
      </div>

      <div v-if="!selectedKiosk" class="ad-timeline-empty">
        <div class="empty-icon">🏥</div>
        <h3>Eczane seçin</h3>
        <p>Yukarıdan bir eczane seçince o eczanenin kiosk takvimi görünür.</p>
      </div>
      <div v-else-if="calendarLoading" class="ad-timeline-loading">Yükleniyor…</div>
      <div v-else-if="!calendar" class="ad-timeline-empty">
        <div class="empty-icon">📋</div>
        <h3>Takvim verisi yüklenemedi</h3>
        <p>Bu kiosk için henüz playlist üretilmemiş olabilir.</p>
        <button class="eisa-btn eisa-btn-cta" :disabled="generating" @click="regenerate('kiosk')">
          <i class="fa-solid fa-play"></i> Bu Kiosk için Playlist Üret
        </button>
      </div>
      <div v-else-if="!Object.keys(calendar.cells || {}).length" class="ad-timeline-empty">
        <div class="empty-icon">📅</div>
        <h3>Playlist bulunamadı</h3>
        <p>Seçilen kiosk için bu tarih aralığında playlist üretilmemiş.</p>
        <button class="eisa-btn eisa-btn-cta" :disabled="generating" @click="regenerate('kiosk')">
          <i class="fa-solid fa-play"></i> Bu Kiosk için Playlist Üret
        </button>
      </div>
      <div v-else class="heatmap-wrapper">
        <table class="heatmap">
          <thead>
            <tr>
              <th></th>
              <th v-for="h in HOURS" :key="h" class="hour-col">{{ String(h).padStart(2, '0') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in dateList" :key="d">
              <th class="day-row">{{ dayLabel(d) }}</th>
              <td v-for="h in HOURS" :key="h"
                  class="heat-cell"
                  :class="cellClass(getCell(d, h))"
                  :title="getCell(d, h)
                    ? `${getCell(d, h).fill_pct}% dolu • ${getCell(d, h).campaign_count} kampanya`
                    : 'Boş — playlist üretilmemiş'"
                  @click="openDetail(d, h)">
                <span v-if="getCell(d, h)" class="heat-pct">{{ Math.round(getCell(d, h).fill_pct) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Saat Detayı -->
    <div v-if="detailHour" class="eisa-panel">
      <div class="eisa-panel-header detail-head">
        <h2 class="eisa-panel-title">
          Loop Detayı: {{ dayLabel(detailHour.date) }} saat {{ String(detailHour.hour).padStart(2, '0') }}:00
        </h2>
        <div class="detail-meta">
          <span v-if="availableSec !== null" class="eisa-pill eisa-pill-info">
            Kalan: <strong>{{ availableSec }}s / loop</strong>
          </span>
          <button class="eisa-btn eisa-btn-ghost" @click="closeDetail">Kapat</button>
        </div>
      </div>

      <div v-if="detailLoading" class="ad-timeline-loading">Yükleniyor…</div>
      <div v-else-if="!loopSummary.length" class="ad-timeline-empty">
        <div class="empty-icon">📋</div>
        <h3>Bu saat için playlist yok</h3>
        <p>Yukarıdaki <strong>"Bu Kiosk için Üret"</strong> butonuna tıklayın.</p>
      </div>

      <div v-else class="ad-timeline-loops">
        <div v-for="loop in loopSummary" :key="loop.loop_index" class="loop-row">
          <div class="loop-row-label">
            <span class="loop-number">Loop #{{ loop.loop_index + 1 }}</span>
            <span class="loop-stats">{{ loop.used }}s dolu / {{ loop.free }}s boş</span>
          </div>
          <div class="gantt-track">
            <div v-for="(item, i) in loop.items" :key="i"
                 class="gantt-bar"
                 :class="item.type === 'house_ad' ? 'gantt-bar--house' : ''"
                 :style="{ left: (item.offset / LOOP_SECONDS * 100) + '%',
                           width: (item.duration / LOOP_SECONDS * 100) + '%',
                           background: item.color }"
                 :title="`${item.label} • ${item.duration}s @ ${item.offset}s`">
              <span>{{ item.label }} ({{ item.duration }}s)</span>
            </div>
            <div v-if="loop.free > 0" class="gantt-bar gantt-bar--free"
                 :style="{ left: ((LOOP_SECONDS - loop.free) / LOOP_SECONDS * 100) + '%',
                           width: (loop.free / LOOP_SECONDS * 100) + '%' }"
                 :title="`Boş: ${loop.free}s`"></div>
          </div>
          <div class="gantt-axis">
            <span v-for="t in [0, 15, 30, 45, 60]" :key="t">{{ t }}s</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
