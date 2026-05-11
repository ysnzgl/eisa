<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { toast } from 'vue-sonner';
import { listCampaignsV2, getCampaignRules, listCreatives } from '../../services/dooh.js';

// ─── Constants ─────────────────────────────────────────────────────────────
const LOOP_SECONDS   = 60;
const SNAP_SECONDS   = 5;
const STORAGE_KEY    = 'eisa_playlists_v1';

const PALETTE = [
  '#3b82f6','#ef4444','#22c55e','#f59e0b',
  '#8b5cf6','#ec4899','#14b8a6','#f97316',
  '#06b6d4','#84cc16','#e11d48','#7c3aed',
];

// ─── State ─────────────────────────────────────────────────────────────────
const playlists      = ref([]);   // all saved playlists
const activeId       = ref(null); // currently selected playlist id

const campaigns      = ref([]);   // fetched from API
const loadingCampaigns = ref(false);
const addingId       = ref(null); // campaign being added

const trackRef       = ref(null); // timeline track DOM ref
const renaming       = ref(false);

// drag state
let drag = null; // { item, offsetSeconds }

// ─── Computed ───────────────────────────────────────────────────────────────
const activePlaylist = computed(() =>
  playlists.value.find(p => p.id === activeId.value) ?? null
);

const items = computed(() => activePlaylist.value?.items ?? []);

const usedSeconds = computed(() =>
  items.value.reduce((s, i) => s + i.duration_seconds, 0)
);

const freeSeconds = computed(() => LOOP_SECONDS - usedSeconds.value);

const capacityPct = computed(() =>
  Math.min(100, (usedSeconds.value / LOOP_SECONDS) * 100)
);

const hasOverlap = computed(() => {
  const sorted = [...items.value].sort((a, b) => a.start_offset - b.start_offset);
  for (let i = 0; i < sorted.length - 1; i++) {
    if (sorted[i].start_offset + sorted[i].duration_seconds > sorted[i + 1].start_offset)
      return true;
  }
  return false;
});

// ─── Persistence ────────────────────────────────────────────────────────────
function loadPlaylists() {
  try {
    playlists.value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    if (playlists.value.length && !activeId.value) {
      activeId.value = playlists.value[0].id;
    }
  } catch { playlists.value = []; }
}

function savePlaylists() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(playlists.value));
}

function saveItems() {
  if (!activePlaylist.value) return;
  savePlaylists();
}

// ─── Playlist CRUD ──────────────────────────────────────────────────────────
function newPlaylist() {
  const id = crypto.randomUUID();
  const pl = {
    id,
    name: `Playlist ${playlists.value.length + 1}`,
    createdAt: new Date().toISOString(),
    items: [],
  };
  playlists.value.push(pl);
  activeId.value = id;
  savePlaylists();
  nextTick(() => { renaming.value = true; });
}

function deletePlaylist(id) {
  if (!confirm('Bu playlist silinsin mi?')) return;
  playlists.value = playlists.value.filter(p => p.id !== id);
  if (activeId.value === id) activeId.value = playlists.value[0]?.id ?? null;
  savePlaylists();
}

function selectPlaylist(id) {
  activeId.value = id;
  renaming.value = false;
}

function renamePlaylist(name) {
  if (!activePlaylist.value || !name.trim()) return;
  activePlaylist.value.name = name.trim();
  savePlaylists();
  renaming.value = false;
}

// ─── Item helpers ────────────────────────────────────────────────────────────
function removeItem(item) {
  if (!activePlaylist.value) return;
  activePlaylist.value.items = activePlaylist.value.items.filter(i => i.id !== item.id);
  saveItems();
}

function clearItems() {
  if (!activePlaylist.value) return;
  if (!confirm('Timeline temizlensin mi?')) return;
  activePlaylist.value.items = [];
  saveItems();
}

/** Find the first free slot of `duration` seconds starting from `from` */
function findFreeSlot(duration, from = 0, existingItems = null) {
  const its = existingItems ?? items.value;
  const sorted = [...its].sort((a, b) => a.start_offset - b.start_offset);
  let candidate = Math.round(from / SNAP_SECONDS) * SNAP_SECONDS;
  while (candidate + duration <= LOOP_SECONDS) {
    const clash = sorted.find(i =>
      candidate < i.start_offset + i.duration_seconds &&
      candidate + duration > i.start_offset
    );
    if (!clash) return candidate;
    candidate = Math.round((clash.start_offset + clash.duration_seconds) / SNAP_SECONDS) * SNAP_SECONDS;
  }
  return null; // no room
}

// ─── Campaign loading ────────────────────────────────────────────────────────
onMounted(async () => {
  loadPlaylists();
  loadingCampaigns.value = true;
  try {
    const res = await listCampaignsV2({ status: 'Active', page_size: 100 });
    campaigns.value = res.data?.results ?? res.data ?? [];
  } catch {
    campaigns.value = [];
  } finally {
    loadingCampaigns.value = false;
  }
});

// ─── Add campaign to timeline ────────────────────────────────────────────────
async function addCampaign(campaign) {
  if (!activePlaylist.value) {
    toast.warning('Önce bir playlist seçin veya oluşturun.');
    return;
  }
  addingId.value = campaign.id;
  try {
    // Fetch creatives and rules in parallel
    const [crRes, ruleRes] = await Promise.all([
      listCreatives({ campaign: campaign.id }),
      getCampaignRules(campaign.id).catch(() => ({ data: [] })),
    ]);

    const creatives = crRes.data?.results ?? crRes.data ?? [];
    const rules     = ruleRes.data ?? [];

    if (!creatives.length) {
      toast.error(`${campaign.name} kampanyasında creative bulunamadı.`);
      return;
    }

    const creative = creatives[0];
    const duration = creative.duration_seconds ?? 15;

    // Determine frequency from rule
    const rule = rules[0];
    let frequency = 1;
    if (rule) {
      if (rule.frequency_type === 'PER_LOOP') {
        frequency = rule.frequency_value;
      } else if (rule.frequency_type === 'PER_HOUR') {
        // per hour → approximate: place every 60/freq seconds
        frequency = Math.max(1, Math.floor(60 / rule.frequency_value));
        frequency = rule.frequency_value; // treat as per-loop count
      } else {
        frequency = 1; // PER_DAY: just one occurrence in the loop
      }
    }

    // Assign color to this campaign
    const existing = activePlaylist.value.items.find(i => i.campaign_id === campaign.id);
    const color = existing?.color ?? PALETTE[
      [...new Set(activePlaylist.value.items.map(i => i.campaign_id))]
        .indexOf(campaign.id) % PALETTE.length
      ] ?? PALETTE[activePlaylist.value.items.length % PALETTE.length];

    let placed = 0;
    const snapshot = [...activePlaylist.value.items];

    for (let f = 0; f < frequency; f++) {
      const idealStart = (f / frequency) * LOOP_SECONDS;
      const slot = findFreeSlot(duration, idealStart, snapshot);
      if (slot === null) break;
      const newItem = {
        id:              crypto.randomUUID(),
        campaign_id:     campaign.id,
        campaign_name:   campaign.name,
        creative_id:     creative.id,
        creative_name:   creative.name ?? creative.media_url?.split('/').pop() ?? 'Creative',
        duration_seconds: duration,
        start_offset:    slot,
        color,
      };
      snapshot.push(newItem);
      placed++;
    }

    if (!placed) {
      toast.warning(`${campaign.name} için yeterli alan bulunamadı.`);
      return;
    }
    activePlaylist.value.items = snapshot;
    saveItems();
    toast.success(`${campaign.name} → ${placed} blok eklendi.`);
  } catch (e) {
    toast.error('Kampanya eklenirken hata: ' + (e?.message ?? 'Bilinmeyen hata'));
  } finally {
    addingId.value = null;
  }
}

// ─── Drag & Drop ─────────────────────────────────────────────────────────────
function itemStyle(item) {
  const left  = (item.start_offset  / LOOP_SECONDS) * 100;
  const width = (item.duration_seconds / LOOP_SECONDS) * 100;
  return {
    left:             `${left}%`,
    width:            `${width}%`,
    backgroundColor:  item.color,
    '--item-color':   item.color,
  };
}

function startDrag(e, item) {
  if (!trackRef.value) return;
  e.preventDefault();
  const trackRect  = trackRef.value.getBoundingClientRect();
  const itemRect   = e.currentTarget.getBoundingClientRect();
  const clickPxInItem = e.clientX - itemRect.left;
  const pxPerSec  = trackRect.width / LOOP_SECONDS;
  drag = { item, clickOffsetSec: clickPxInItem / pxPerSec, trackRect, pxPerSec };
}

function onMouseMove(e) {
  if (!drag) return;
  const rawOffset = (e.clientX - drag.trackRect.left - drag.clickOffsetSec * drag.pxPerSec) / drag.pxPerSec;
  const snapped   = Math.round(rawOffset / SNAP_SECONDS) * SNAP_SECONDS;
  const maxOffset = LOOP_SECONDS - drag.item.duration_seconds;
  drag.item.start_offset = Math.max(0, Math.min(snapped, maxOffset));
}

function onMouseUp() {
  if (!drag) return;
  drag = null;
  saveItems();
}

function onMouseLeave() {
  if (drag) { drag = null; saveItems(); }
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onMouseMove);
  document.removeEventListener('mouseup', onMouseUp);
});

// Attach global listeners so drag works outside track boundaries
function attachGlobalDrag() {
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup',   onMouseUp);
}
attachGlobalDrag();

// ─── Timeline grid ───────────────────────────────────────────────────────────
const gridTicks = Array.from({ length: LOOP_SECONDS / SNAP_SECONDS + 1 }, (_, i) => i * SNAP_SECONDS);

// ─── Overlap color helper ────────────────────────────────────────────────────
function isOverlapping(item) {
  return items.value.some(other => {
    if (other.id === item.id) return false;
    return item.start_offset < other.start_offset + other.duration_seconds &&
           item.start_offset + item.duration_seconds > other.start_offset;
  });
}

// ─── Campaign color lookup ───────────────────────────────────────────────────
function campaignColor(campaignId) {
  const found = items.value.find(i => i.campaign_id === campaignId);
  return found?.color ?? '#94a3b8';
}
</script>

<template>
  <div class="playlist-editor">

    <!-- ═══ LEFT SIDEBAR: Playlist list ═══════════════════════════════════ -->
    <aside class="pl-sidebar">
      <div class="pl-sidebar-header">
        <span class="pl-sidebar-title"><i class="fa-solid fa-list-ol"></i> Playlistler</span>
        <button class="eisa-btn eisa-btn-cta sm" @click="newPlaylist">
          <i class="fa-solid fa-plus"></i> Yeni
        </button>
      </div>

      <div class="pl-list">
        <div v-if="!playlists.length" class="pl-empty-hint">
          Henüz playlist yok. "Yeni" butonuna tıklayın.
        </div>
        <div
          v-for="pl in playlists"
          :key="pl.id"
          class="pl-list-item"
          :class="{ active: pl.id === activeId }"
          @click="selectPlaylist(pl.id)"
        >
          <i class="fa-solid fa-film"></i>
          <span class="pl-list-name">{{ pl.name }}</span>
          <button
            class="pl-delete-btn"
            title="Sil"
            @click.stop="deletePlaylist(pl.id)"
          >
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </div>
    </aside>

    <!-- ═══ CENTER: Timeline editor ═══════════════════════════════════════ -->
    <main class="pl-main">

      <!-- Empty state -->
      <div v-if="!activePlaylist" class="pl-no-playlist">
        <i class="fa-solid fa-film fa-3x"></i>
        <p>Sol panelden bir playlist seçin ya da <strong>Yeni</strong> oluşturun.</p>
      </div>

      <template v-else>
        <!-- Header -->
        <div class="pl-main-header">
          <div class="pl-name-row">
            <template v-if="renaming">
              <input
                class="eisa-field pl-name-input"
                :value="activePlaylist.name"
                @keyup.enter="e => renamePlaylist(e.target.value)"
                @blur="e => renamePlaylist(e.target.value)"
                autofocus
              />
            </template>
            <template v-else>
              <h2 class="pl-name" @dblclick="renaming = true">{{ activePlaylist.name }}</h2>
              <button class="icon-btn" title="Yeniden adlandır" @click="renaming = true">
                <i class="fa-solid fa-pencil"></i>
              </button>
            </template>
            <span class="pl-hint muted small">Çift tıklayarak yeniden adlandırın</span>
          </div>

          <div class="pl-main-actions">
            <span
              class="capacity-badge"
              :class="{ warn: usedSeconds > 50, full: usedSeconds >= 60 }"
            >
              <i class="fa-solid fa-clock"></i>
              {{ usedSeconds }}s / {{ LOOP_SECONDS }}s
            </span>
            <button
              v-if="items.length"
              class="eisa-btn eisa-btn-ghost sm"
              @click="clearItems"
            >
              <i class="fa-solid fa-broom"></i> Temizle
            </button>
          </div>
        </div>

        <!-- Capacity bar -->
        <div class="capacity-bar-wrap">
          <div
            class="capacity-bar-fill"
            :class="{ warn: usedSeconds > 45, full: usedSeconds >= 60 }"
            :style="{ width: capacityPct + '%' }"
          ></div>
          <span class="capacity-bar-label">
            {{ freeSeconds >= 0 ? freeSeconds + 's boş' : Math.abs(freeSeconds) + 's taşma' }}
          </span>
        </div>

        <!-- Overlap warning -->
        <div v-if="hasOverlap" class="overlap-warn">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Çakışan bloklar var — kırmızı çerçeveli öğeleri sürükleyerek düzeltin.
        </div>

        <!-- ── Timeline track ──────────────────────────────────────────── -->
        <div class="timeline-wrap">
          <!-- Tick labels -->
          <div class="tick-labels">
            <span
              v-for="t in gridTicks"
              :key="t"
              class="tick-label"
              :style="{ left: (t / LOOP_SECONDS * 100) + '%' }"
            >{{ t }}s</span>
          </div>

          <!-- Track -->
          <div
            ref="trackRef"
            class="timeline-track"
            @mouseleave="onMouseLeave"
          >
            <!-- Grid lines -->
            <div
              v-for="t in gridTicks"
              :key="'g' + t"
              class="grid-line"
              :style="{ left: (t / LOOP_SECONDS * 100) + '%' }"
            ></div>

            <!-- Items -->
            <div
              v-for="item in items"
              :key="item.id"
              class="timeline-item"
              :class="{ overlapping: isOverlapping(item) }"
              :style="itemStyle(item)"
              :title="`${item.campaign_name} — ${item.duration_seconds}s @ ${item.start_offset}s`"
              @mousedown.prevent="startDrag($event, item)"
              @dblclick.stop="removeItem(item)"
            >
              <span class="item-label">{{ item.campaign_name }}</span>
              <span class="item-dur">{{ item.duration_seconds }}s</span>
              <button
                class="item-remove"
                title="Kaldır"
                @mousedown.stop
                @click.stop="removeItem(item)"
              >×</button>
            </div>
          </div>

          <p class="track-hint muted small">
            Sürükle → taşı &nbsp;|&nbsp; Çift tıkla ya da <i class="fa-solid fa-xmark"></i> → kaldır
          </p>
        </div>

        <!-- ── Items list (below track) ───────────────────────────────── -->
        <div v-if="items.length" class="items-legend">
          <div
            v-for="item in [...items].sort((a, b) => a.start_offset - b.start_offset)"
            :key="item.id"
            class="legend-row"
          >
            <span class="legend-dot" :style="{ background: item.color }"></span>
            <span class="legend-offset">{{ item.start_offset }}s</span>
            <span class="legend-name">{{ item.campaign_name }}</span>
            <span class="legend-dur muted">{{ item.duration_seconds }}s</span>
          </div>
        </div>
        <div v-else class="pl-empty-hint" style="margin-top:2rem">
          Sağ panelden kampanya ekleyin ya da sürükleyin.
        </div>
      </template>
    </main>

    <!-- ═══ RIGHT PANEL: Campaign selector ════════════════════════════════ -->
    <aside class="pl-campaigns">
      <div class="pl-sidebar-header">
        <span class="pl-sidebar-title"><i class="fa-solid fa-bullhorn"></i> Kampanyalar</span>
      </div>

      <div v-if="loadingCampaigns" class="pl-loading">
        <i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor…
      </div>

      <div v-else-if="!campaigns.length" class="pl-empty-hint">
        Aktif kampanya bulunamadı.
      </div>

      <div v-else class="campaign-list">
        <div
          v-for="c in campaigns"
          :key="c.id"
          class="campaign-card"
        >
          <div class="campaign-card-dot"
               :style="{ background: campaignColor(c.id) }"></div>
          <div class="campaign-card-info">
            <div class="campaign-card-name">{{ c.name }}</div>
            <div class="campaign-card-meta muted small">
              {{ c.status }} · {{ c.start_date?.slice(0,10) }} →  {{ c.end_date?.slice(0,10) }}
            </div>
          </div>
          <button
            class="eisa-btn eisa-btn-cta sm"
            :disabled="!activePlaylist || addingId === c.id"
            @click="addCampaign(c)"
          >
            <i class="fa-solid" :class="addingId === c.id ? 'fa-circle-notch fa-spin' : 'fa-plus'"></i>
            Ekle
          </button>
        </div>
      </div>
    </aside>

  </div>
</template>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────────────── */
.playlist-editor {
  display: grid;
  grid-template-columns: 220px 1fr 260px;
  height: calc(100vh - 64px);
  background: var(--color-bg, #f8fafc);
  overflow: hidden;
}

/* ── Sidebars ────────────────────────────────────────────────────────────── */
.pl-sidebar,
.pl-campaigns {
  background: var(--color-surface, #fff);
  border-right: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pl-campaigns {
  border-right: none;
  border-left: 1px solid var(--color-border, #e2e8f0);
}

.pl-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .75rem 1rem;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  flex-shrink: 0;
}
.pl-sidebar-title {
  font-weight: 600;
  font-size: .875rem;
  display: flex;
  align-items: center;
  gap: .4rem;
}

.pl-list {
  overflow-y: auto;
  flex: 1;
  padding: .5rem;
}
.pl-list-item {
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .5rem .75rem;
  border-radius: .5rem;
  cursor: pointer;
  font-size: .875rem;
  transition: background .15s;
}
.pl-list-item:hover       { background: var(--color-hover, #f1f5f9); }
.pl-list-item.active      { background: var(--color-primary-10, #eff6ff); color: var(--color-primary, #3b82f6); font-weight: 600; }
.pl-list-name             { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pl-delete-btn            { background: none; border: none; cursor: pointer; color: var(--color-muted, #94a3b8); padding: .15rem .3rem; border-radius: .25rem; }
.pl-delete-btn:hover      { color: var(--color-danger, #ef4444); background: #fee2e2; }
.pl-empty-hint            { color: var(--color-muted, #94a3b8); font-size: .8125rem; padding: 1rem; text-align: center; }

/* ── Main area ────────────────────────────────────────────────────────────── */
.pl-main {
  overflow-y: auto;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.pl-no-playlist {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 1rem;
  color: var(--color-muted, #94a3b8);
  text-align: center;
  margin-top: 4rem;
}

/* ── Header row ────────────────────────────────────────────────────────────── */
.pl-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: .75rem;
}
.pl-name-row {
  display: flex;
  align-items: center;
  gap: .5rem;
}
.pl-name {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  cursor: default;
}
.pl-name-input {
  font-size: 1.1rem;
  font-weight: 700;
  padding: .25rem .5rem;
  max-width: 260px;
}
.pl-hint { font-size: .75rem; }
.pl-main-actions {
  display: flex;
  align-items: center;
  gap: .75rem;
}
.capacity-badge {
  display: flex;
  align-items: center;
  gap: .35rem;
  font-size: .8125rem;
  font-weight: 600;
  padding: .3rem .65rem;
  border-radius: 1rem;
  background: #dcfce7;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}
.capacity-badge.warn { background: #fef9c3; color: #ca8a04; border-color: #fde047; }
.capacity-badge.full { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }

/* ── Capacity bar ──────────────────────────────────────────────────────────── */
.capacity-bar-wrap {
  position: relative;
  height: 8px;
  background: var(--color-border, #e2e8f0);
  border-radius: 4px;
  overflow: visible;
}
.capacity-bar-fill {
  height: 100%;
  border-radius: 4px;
  background: #22c55e;
  transition: width .2s, background .2s;
}
.capacity-bar-fill.warn { background: #f59e0b; }
.capacity-bar-fill.full { background: #ef4444; }
.capacity-bar-label {
  position: absolute;
  right: 0;
  top: 11px;
  font-size: .7rem;
  color: var(--color-muted, #94a3b8);
}

/* ── Overlap warning ────────────────────────────────────────────────────────── */
.overlap-warn {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #92400e;
  border-radius: .5rem;
  padding: .5rem .75rem;
  font-size: .8125rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}

/* ── Timeline ────────────────────────────────────────────────────────────────── */
.timeline-wrap {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: .75rem;
  padding: .75rem 1rem 1rem;
}

.tick-labels {
  position: relative;
  height: 18px;
  margin-bottom: 4px;
  user-select: none;
}
.tick-label {
  position: absolute;
  transform: translateX(-50%);
  font-size: .65rem;
  color: var(--color-muted, #94a3b8);
  white-space: nowrap;
}

.timeline-track {
  position: relative;
  height: 60px;
  background: var(--color-bg, #f8fafc);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: .5rem;
  overflow: visible;
  user-select: none;
  cursor: default;
}
.grid-line {
  position: absolute;
  top: 0;
  height: 100%;
  width: 1px;
  background: var(--color-border, #e2e8f0);
  pointer-events: none;
}

.timeline-item {
  position: absolute;
  top: 6px;
  height: calc(100% - 12px);
  border-radius: .35rem;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 .4rem;
  box-sizing: border-box;
  overflow: hidden;
  border: 2px solid transparent;
  transition: box-shadow .1s, border-color .1s;
  box-shadow: 0 1px 4px rgba(0,0,0,.18);
}
.timeline-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,.28);
  z-index: 10;
}
.timeline-item:active { cursor: grabbing; z-index: 20; }
.timeline-item.overlapping { border-color: #dc2626; }

.item-label {
  font-size: .65rem;
  font-weight: 700;
  color: #fff;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex: 1;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0,0,0,.3);
}
.item-dur {
  font-size: .6rem;
  color: rgba(255,255,255,.85);
  white-space: nowrap;
  pointer-events: none;
  margin-left: .25rem;
}
.item-remove {
  background: rgba(0,0,0,.25);
  border: none;
  color: #fff;
  border-radius: .25rem;
  width: 16px;
  height: 16px;
  font-size: .7rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: .2rem;
  padding: 0;
}
.item-remove:hover { background: rgba(220,38,38,.7); }

.track-hint {
  margin-top: .5rem;
  font-size: .7rem;
}

/* ── Items legend ────────────────────────────────────────────────────────────── */
.items-legend {
  display: flex;
  flex-direction: column;
  gap: .35rem;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: .6rem;
  font-size: .8125rem;
}
.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: .2rem;
  flex-shrink: 0;
}
.legend-offset {
  font-variant-numeric: tabular-nums;
  color: var(--color-muted, #94a3b8);
  min-width: 30px;
  font-size: .75rem;
}
.legend-name { flex: 1; font-weight: 500; }
.legend-dur  { font-size: .75rem; }

/* ── Campaign panel ────────────────────────────────────────────────────────── */
.pl-loading {
  padding: 1rem;
  color: var(--color-muted, #94a3b8);
  font-size: .875rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}
.campaign-list {
  overflow-y: auto;
  flex: 1;
  padding: .5rem;
  display: flex;
  flex-direction: column;
  gap: .4rem;
}
.campaign-card {
  display: flex;
  align-items: center;
  gap: .6rem;
  padding: .6rem .75rem;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: .5rem;
  background: var(--color-surface, #fff);
  transition: box-shadow .15s;
}
.campaign-card:hover { box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.campaign-card-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.campaign-card-info { flex: 1; min-width: 0; }
.campaign-card-name {
  font-size: .8125rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.campaign-card-meta { font-size: .7rem; }

/* ── Shared ────────────────────────────────────────────────────────────────── */
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-muted, #94a3b8);
  padding: .2rem .35rem;
  border-radius: .3rem;
  transition: color .15s;
}
.icon-btn:hover { color: var(--color-text, #1e293b); }

.sm { padding: .3rem .6rem !important; font-size: .8125rem !important; }
.muted  { color: var(--color-muted, #94a3b8); }
.small  { font-size: .8125rem; }
.eisa-field {
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: .4rem;
  padding: .35rem .6rem;
  font-size: .875rem;
  outline: none;
  transition: border-color .15s;
}
.eisa-field:focus { border-color: var(--color-primary, #3b82f6); }
.eisa-btn {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  padding: .45rem .9rem;
  border: none;
  border-radius: .4rem;
  font-size: .875rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity .15s, box-shadow .15s;
}
.eisa-btn:disabled { opacity: .5; cursor: not-allowed; }
.eisa-btn-cta  { background: var(--color-primary, #3b82f6); color: #fff; }
.eisa-btn-cta:hover:not(:disabled) { opacity: .9; }
.eisa-btn-ghost { background: var(--color-border, #e2e8f0); color: var(--color-text, #1e293b); }
.eisa-btn-ghost:hover:not(:disabled) { background: var(--color-hover, #cbd5e1); }
</style>
