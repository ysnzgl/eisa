<script setup>
/**
 * AdTimelineView — İl → İlçe → Eczane → Kiosk kademeli filtreleme ile haftalık/custom takvim ısı haritası.
 * Hücreye tıkla → loop slot detayı açılır.
 * Playlist Üret butonu en alt seçili kırılıma göre çalışır.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  generatePlaylists, getCampaignTimeline, getCampaignCalendar, getInventoryAvailability,
  getIller, getIlceler, getEczanelerByIlce,
} from '../../services/dooh';
import { getKioskStatus } from '../../services/devices';

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const LOOP_SECONDS = 60;

// ── Kademeli Filtre Verisi ────────────────────────────────────────────────────
const iller       = ref([]);
const ilceler     = ref([]);
const eczaneler   = ref([]);
const kiosks      = ref([]);

const selectedIl      = ref(null);
const selectedIlce    = ref(null);
const selectedEczane  = ref(null);
const selectedKiosk   = ref(null);

// ── Tarih aralığı ─────────────────────────────────────────────────────────────
const startDate       = ref(new Date().toISOString().slice(0, 10));
const endDate         = ref(null);

// ── Takvim ───────────────────────────────────────────────────────────────────────────
const calendar        = ref(null);
const calendarLoading = ref(false);

// ── Detay modalı ──────────────────────────────────────────────────────────────────────────
const detailHour    = ref(null);
const detailData    = ref(null);
const detailLoading = ref(false);
const availableSec  = ref(null);

const generating = ref(false);
const error  = ref('');
const flash  = ref('');

// ── Tarih listesi (max 31 gün) ────────────────────────────────────────────────────────
const dateList = computed(() => {
  const sd = new Date(startDate.value);
  const ed = endDate.value ? new Date(endDate.value) : new Date(sd);
  const out = [];
  for (let d = new Date(sd); d <= ed; d.setDate(d.getDate() + 1)) {
    out.push(new Date(d).toISOString().slice(0, 10));
    if (out.length >= 31) break;
  }
  return out;
});
const dayCount = computed(() => dateList.value.length || 1);

// ── En alt seçili kırılım ─────────────────────────────────────────────────────────────────
const activeFilter = computed(() => {
  if (selectedKiosk.value)   return { key: 'kiosk',    value: selectedKiosk.value };
  if (selectedEczane.value)  return { key: 'pharmacy', value: selectedEczane.value };
  if (selectedIlce.value)    return { key: 'ilce',     value: selectedIlce.value };
  if (selectedIl.value)      return { key: 'il',       value: selectedIl.value };
  return null;
});

// ── Renk paleti ───────────────────────────────────────────────────────────────────────────
const PALETTE = ['#6366f1','#0ea5e9','#f59e0b','#10b981','#ef4444',
                 '#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16'];
const colorCache = new Map();
function colorFor(name) {
  if (!name) return '#94a3b8';
  if (!colorCache.has(name)) colorCache.set(name, PALETTE[colorCache.size % PALETTE.length]);
  return colorCache.get(name);
}

const DAY_LABELS = ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'];
function dayLabel(iso) {
  const d = new Date(iso);
  const idx = (d.getDay() + 6) % 7;
  return `${DAY_LABELS[idx]} ${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}`;
}

// ── Veri yükleme fonksiyonları ────────────────────────────────────────────────────────────
async function loadIller() {
  try {
    const data = await getIller();
    iller.value = Array.isArray(data) ? data : [];
  } catch {
    error.value = 'İller yüklenemedi';
  }
}

async function loadIlceler() {
  ilceler.value = [];
  selectedIlce.value = null;
  selectedEczane.value = null;
  selectedKiosk.value = null;
  eczaneler.value = [];
  kiosks.value = [];
  if (!selectedIl.value) return;
  try {
    const data = await getIlceler(selectedIl.value);
    ilceler.value = Array.isArray(data) ? data : [];
  } catch {
    error.value = 'İlçeler yüklenemedi';
  }
}

async function loadEczaneler() {
  eczaneler.value = [];
  selectedEczane.value = null;
  selectedKiosk.value = null;
  kiosks.value = [];
  if (!selectedIlce.value) return;
  try {
    const data = await getEczanelerByIlce(selectedIlce.value);
    eczaneler.value = Array.isArray(data) ? data : [];
  } catch {
    error.value = 'Eczaneler yüklenemedi';
  }
}

async function loadKiosks() {
  kiosks.value = [];
  selectedKiosk.value = null;
  if (!selectedEczane.value) return;
  try {
    const data = await getKioskStatus(selectedEczane.value);
    kiosks.value = Array.isArray(data) ? data : [];
  } catch {
    error.value = 'Kiosklar yüklenemedi';
  }
}

async function loadCalendar() {
  if (!activeFilter.value) { calendar.value = null; return; }
  calendarLoading.value = true;
  error.value = '';
  try {
    const { data } = await getCampaignCalendar({
      [activeFilter.value.key]: activeFilter.value.value,
      start: startDate.value,
      days: dayCount.value,
    });
    calendar.value = data;
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.response?.data?.error || 'Takvim yüklenemedi';
    calendar.value = null;
  } finally {
    calendarLoading.value = false;
  }
}

// ── Heatmap yardımcıları ──────────────────────────────────────────────────────────────────
function getCell(date, hour) {
  if (!calendar.value?.cells) return null;
  return calendar.value.cells[date]?.[hour] ?? calendar.value.cells[date]?.[String(hour)] ?? null;
}

function cellClass(cell) {
  if (!cell) return 'cell-empty';
  const p = cell.fill_pct;
  if (p === 0) return 'cell-empty';
  if (p < 25)  return 'cell-low';
  if (p < 60)  return 'cell-med';
  if (p < 90)  return 'cell-high';
  return 'cell-full';
}

// ── Detay modal ───────────────────────────────────────────────────────────────────────────
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
  return Array.from(groups.entries()).sort(([a],[b]) => a - b).map(([loop_index, items]) => {
    const sorted = [...items].sort((a,b) => a.offset - b.offset);
    const used = sorted.reduce((s,it) => s + it.duration, 0);
    return { loop_index, used, free: Math.max(0, loopSec - used), items: sorted };
  });
});

// ── Playlist üretimi ──────────────────────────────────────────────────────────────────────────────
async function regenerate() {
  if (!activeFilter.value) return;
  generating.value = true; error.value = ''; flash.value = '';
  try {
    const payload = {
      start: startDate.value,
      days: dayCount.value,
      [activeFilter.value.key]: activeFilter.value.value,
    };
    const resp = await generatePlaylists(payload);
    const d = resp.data || {};
    flash.value = `✓ ${d.kiosk_count ?? '?'} kiosk için ${d.playlists_generated ?? '?'} playlist üretildi.`;
    await loadCalendar();
    if (detailHour.value) await openDetail(detailHour.value.date, detailHour.value.hour);
  } catch (e) {
    error.value = e?.response?.data?.error || e?.response?.data?.detail || 'Playlist üretimi başarısız';
  } finally { generating.value = false; }
}

// ── Watchers ──────────────────────────────────────────────────────────────────────────────────
watch(selectedIl,     loadIlceler);
watch(selectedIlce,   loadEczaneler);
watch(selectedEczane, loadKiosks);
watch([selectedKiosk, selectedEczane, selectedIlce, selectedIl, startDate, endDate], loadCalendar);

// ── Lifecycle ──────────────────────────────────────────────────────────────────────────────────
let _storageListener = null;
onMounted(async () => {
  await loadIller();
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
        <p class="eisa-page-subtitle">İl → İlçe → Eczane → Kiosk kademeli seçimle yayın doluluk haritası</p>
      </div>
    </div>

    <!-- Filtreler -->
    <div class="eisa-panel">
      <div class="ad-timeline-filters">

        <!-- İL -->
        <div class="eisa-field" style="flex:1.5; min-width:160px;">
          <label class="eisa-field-label">İl</label>
          <select v-model="selectedIl" class="eisa-input">
            <option :value="null">— İl seçin —</option>
            <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad || il.name }}</option>
          </select>
        </div>

        <!-- İLÇE -->
        <div class="eisa-field" style="flex:1.5; min-width:160px;">
          <label class="eisa-field-label">İlçe</label>
          <select v-model="selectedIlce" class="eisa-input" :disabled="!selectedIl">
            <option :value="null">— İlçe seçin —</option>
            <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad || ilce.name }}</option>
          </select>
        </div>

        <!-- ECZANE -->
        <div class="eisa-field" style="flex:2; min-width:180px;">
          <label class="eisa-field-label">Eczane</label>
          <select v-model="selectedEczane" class="eisa-input" :disabled="!selectedIlce">
            <option :value="null">— Eczane seçin —</option>
            <option v-for="ec in eczaneler" :key="ec.id" :value="ec.id">{{ ec.ad }}</option>
          </select>
        </div>

        <!-- KIOSK -->
        <div class="eisa-field" style="flex:1.5; min-width:160px;">
          <label class="eisa-field-label">Kiosk</label>
          <select v-model="selectedKiosk" class="eisa-input" :disabled="!selectedEczane">
            <option :value="null">— Tüm kiosklar —</option>
            <option v-for="k in kiosks" :key="k.id" :value="k.id">{{ k.ad || `Kiosk #${k.id}` }}</option>
          </select>
        </div>

        <!-- TARİH ARALIĞI -->
        <div class="eisa-field" style="flex:1; min-width:130px;">
          <label class="eisa-field-label">Başlangıç</label>
          <input type="date" v-model="startDate" class="eisa-input" />
        </div>
        <div class="eisa-field" style="flex:1; min-width:130px;">
          <label class="eisa-field-label">Bitiş</label>
          <input type="date" v-model="endDate" class="eisa-input" />
        </div>

        <!-- AKSİYONLAR -->
        <div class="ad-timeline-actions">
          <button class="eisa-btn eisa-btn-ghost" :disabled="calendarLoading" @click="loadCalendar" title="Yenile">
            <i class="fa-solid fa-rotate" :class="{ 'fa-spin': calendarLoading }"></i>
          </button>
          <button class="eisa-btn eisa-btn-cta" :disabled="generating || !activeFilter" @click="regenerate">
            <i class="fa-solid fa-play"></i>
            {{ generating ? 'Üretiliyor…' : 'Playlist Üret' }}
          </button>
        </div>

      </div>

      <!-- Seçim özeti -->
      <div v-if="activeFilter" style="margin-top:.75rem; font-size:.8rem; color:#64748b;">
        <i class="fa-solid fa-circle-info"></i>
        Playlist
        <strong>{{
          activeFilter.key === 'kiosk'    ? 'kiosk' :
          activeFilter.key === 'pharmacy' ? 'eczane' :
          activeFilter.key === 'ilce'     ? 'ilçe' : 'il'
        }}</strong>
        kırılımında üretilecek.
      </div>
    </div>

    <div v-if="flash" class="eisa-toast-success">{{ flash }}</div>
    <div v-if="error" class="eisa-toast-error">{{ error }}</div>

    <!-- Heatmap -->
    <div class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">
          Doluluk Isı Haritası — {{ dayCount }} gün × 24 saat
          <span v-if="activeFilter" class="muted" style="font-size:.85rem; font-weight:400;">
            ({{
              activeFilter.key === 'kiosk'
                ? (kiosks.find(k => k.id === selectedKiosk)?.ad || `Kiosk #${selectedKiosk}`)
                : activeFilter.key === 'pharmacy'
                  ? (eczaneler.find(e => e.id === selectedEczane)?.ad || 'Eczane')
                  : activeFilter.key === 'ilce'
                    ? (ilceler.find(i => i.id === selectedIlce)?.ad || 'İlçe')
                    : (iller.find(i => i.id === selectedIl)?.ad || 'İl')
            }})
          </span>
        </h2>
        <div class="heatmap-legend">
          <span class="legend-cell cell-empty"></span> Boş
          <span class="legend-cell cell-low"></span> &lt;%25
          <span class="legend-cell cell-med"></span> &lt;%60
          <span class="legend-cell cell-high"></span> &lt;%90
          <span class="legend-cell cell-full"></span> Dolu
        </div>
      </div>

      <div v-if="!activeFilter" class="ad-timeline-empty">
        <div class="empty-icon">📍</div>
        <h3>Filtre seçin</h3>
        <p>Yukarıdan en az bir il seçince takvim yüklenir.</p>
      </div>
      <div v-else-if="calendarLoading" class="ad-timeline-loading">Yükleniyor…</div>
      <div v-else-if="!calendar" class="ad-timeline-empty">
        <div class="empty-icon">📋</div>
        <h3>Takvim verisi yok</h3>
        <p>Henüz playlist üretilmemiş. <strong>Playlist Üret</strong> butonuna tıklayın.</p>
      </div>
      <div v-else-if="!Object.keys(calendar.cells || {}).length" class="ad-timeline-empty">
        <div class="empty-icon">📅</div>
        <h3>Bu tarih aralığında playlist bulunamadı</h3>
        <p>Tarih aralığını değiştirin veya playlist üretin.</p>
      </div>
      <div v-else class="heatmap-wrapper">
        <table class="heatmap">
          <thead>
            <tr>
              <th class="day-row"></th>
              <th v-for="h in HOURS" :key="h" class="hour-col">{{ String(h).padStart(2,'00') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in dateList" :key="d">
              <th class="day-row">{{ dayLabel(d) }}</th>
              <td v-for="h in HOURS" :key="h"
                  class="heat-cell"
                  :class="cellClass(getCell(d, h))"
                  :title="getCell(d, h)
                    ? `${Math.round(getCell(d, h).fill_pct)}% dolu • ${getCell(d, h).campaign_count} kampanya`
                    : 'Boş'"
                  @click="openDetail(d, h)">
                <span v-if="getCell(d, h)" class="heat-pct">{{ Math.round(getCell(d, h).fill_pct) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Saat Detayı (yalnızca kiosk seçiliyken) -->
    <div v-if="detailHour" class="eisa-panel">
      <div class="eisa-panel-header detail-head">
        <h2 class="eisa-panel-title">
          Loop Detayı — {{ dayLabel(detailHour.date) }} {{ String(detailHour.hour).padStart(2,'0') }}:00
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
        <p><strong>Playlist Üret</strong> butonuna tıklayın.</p>
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
