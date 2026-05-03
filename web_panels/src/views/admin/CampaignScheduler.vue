<template>
  <div class="scheduler-root">
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Azeret+Mono:wght@300;400;500;600;700&family=Figtree:wght@300;400;500;600&display=swap"
      rel="stylesheet"
    />

    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <div class="header-eyebrow">KAMPANYA KONTROL MERKEZİ</div>
        <h1 class="header-title">Kiosk Zaman Çizelgesi</h1>
        <div class="header-sub">{{ currentDate }}</div>
      </div>
      <div class="header-controls">
        <div class="view-toggle">
          <button
            v-for="v in views"
            :key="v.key"
            :class="['toggle-btn', { active: activeView === v.key }]"
            @click="activeView = v.key"
          >{{ v.label }}</button>
        </div>
        <button class="btn-add" @click="openAssignModal()">
          <span class="btn-icon">+</span> Kampanya Ata
        </button>
      </div>
    </div>

    <!-- Legend -->
    <div class="legend">
      <div class="legend-item" v-for="camp in campaigns" :key="camp.id">
        <div class="legend-dot" :style="{ background: camp.color }"></div>
        <span>{{ camp.name }}</span>
      </div>
      <div class="legend-separator"></div>
      <div class="legend-item">
        <div class="legend-dot conflict"></div>
        <span>Çakışma / Doluluk Aşımı</span>
      </div>
      <div class="legend-item">
        <div class="legend-dot empty"></div>
        <span>Boş Slot</span>
      </div>
    </div>

    <!-- Scheduler Grid -->
    <div class="scheduler-wrapper" ref="scrollWrapper">
      <!-- Time axis -->
      <div class="time-axis-spacer"></div>
      <div class="time-axis">
        <div
          v-for="hour in timeLabels"
          :key="hour"
          class="time-label"
          :style="{ width: cellWidth + 'px' }"
        >{{ hour }}</div>
      </div>

      <!-- Rows -->
      <div class="rows-container">
        <div
          v-for="pharmacy in pharmacies"
          :key="pharmacy.id"
          class="pharmacy-group"
        >
          <!-- Pharmacy header row -->
          <div class="pharmacy-label-row">
            <div class="pharmacy-name-cell">
              <div class="pharmacy-icon">⬡</div>
              <div>
                <div class="pharmacy-name">{{ pharmacy.name }}</div>
                <div class="pharmacy-meta">{{ pharmacy.kiosks.length }} kiosk</div>
              </div>
            </div>
            <div class="pharmacy-timeline-row">
              <div
                v-for="(hour, hIdx) in hours"
                :key="hIdx"
                class="pharmacy-hour-cell"
                :style="{ width: cellWidth + 'px' }"
              ></div>
            </div>
          </div>

          <!-- Kiosk rows -->
          <div
            v-for="kiosk in pharmacy.kiosks"
            :key="kiosk.id"
            class="kiosk-row"
          >
            <div class="kiosk-label-cell">
              <span class="kiosk-status-dot" :class="kiosk.online ? 'online' : 'offline'"></span>
              <span class="kiosk-name">{{ kiosk.name }}</span>
            </div>
            <div class="kiosk-timeline" :style="{ width: timelineWidth + 'px' }">
              <!-- Hour cells (background grid) -->
              <div
                v-for="(hour, hIdx) in hours"
                :key="hIdx"
                class="hour-cell"
                :style="{ width: cellWidth + 'px' }"
                :class="{
                  'conflict-cell': hasConflict(kiosk.id, hIdx),
                  'now-cell': isCurrentHour(hIdx)
                }"
                @click="openAssignModal(kiosk, hIdx)"
              >
                <span v-if="hasConflict(kiosk.id, hIdx)" class="conflict-pulse"></span>
              </div>

              <!-- Campaign blocks -->
              <div
                v-for="block in getKioskBlocks(kiosk.id)"
                :key="block.id"
                class="campaign-block"
                :style="{
                  left: block.startPx + 'px',
                  width: block.widthPx + 'px',
                  background: block.color,
                  boxShadow: `0 0 12px ${block.color}66, 0 0 24px ${block.color}22`
                }"
                @mouseenter="hoveredBlock = block.id"
                @mouseleave="hoveredBlock = null"
                @click.stop="selectBlock(block)"
              >
                <div class="block-inner">
                  <span class="block-name">{{ block.name }}</span>
                  <span class="block-time">{{ formatHour(block.start) }}–{{ formatHour(block.end) }}</span>
                </div>
                <!-- Tooltip -->
                <div v-if="hoveredBlock === block.id" class="block-tooltip">
                  <div class="tt-title">{{ block.name }}</div>
                  <div class="tt-row"><span>Süre</span><span>{{ formatHour(block.start) }} – {{ formatHour(block.end) }}</span></div>
                  <div class="tt-row"><span>Müşteri</span><span>{{ block.client }}</span></div>
                  <div class="tt-row"><span>Medya</span><span>{{ block.mediaType }}</span></div>
                </div>
              </div>

              <!-- Now indicator -->
              <div v-if="isCurrentKioskVisible(kiosk.id)" class="now-line" :style="{ left: nowLinePx + 'px' }">
                <div class="now-pip"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats bar -->
    <div class="stats-bar">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- Block detail panel (right drawer) -->
    <transition name="drawer">
      <div v-if="selectedBlock" class="block-detail-panel">
        <button class="panel-close" @click="selectedBlock = null">✕</button>
        <div class="panel-eyebrow">KAMPANYA DETAYI</div>
        <h2 class="panel-title">{{ selectedBlock.name }}</h2>
        <div class="panel-color-bar" :style="{ background: selectedBlock.color }"></div>
        <div class="panel-rows">
          <div class="panel-row">
            <span>Müşteri</span><span>{{ selectedBlock.client }}</span>
          </div>
          <div class="panel-row">
            <span>Zaman</span><span>{{ formatHour(selectedBlock.start) }} – {{ formatHour(selectedBlock.end) }}</span>
          </div>
          <div class="panel-row">
            <span>Medya</span><span>{{ selectedBlock.mediaType }}</span>
          </div>
          <div class="panel-row">
            <span>Öncelik</span><span>{{ selectedBlock.priority }}</span>
          </div>
        </div>
        <div class="panel-actions">
          <button class="panel-btn edit">Düzenle</button>
          <button class="panel-btn delete" @click="removeBlock(selectedBlock)">Kaldır</button>
        </div>
      </div>
    </transition>

    <!-- Assign Modal -->
    <transition name="modal">
      <div v-if="showAssignModal" class="modal-overlay" @click.self="showAssignModal = false">
        <div class="modal-box">
          <div class="modal-eyebrow">YENİ ATAMA</div>
          <h3 class="modal-title">Kampanya Ata</h3>

          <div class="form-group">
            <label>Kampanya</label>
            <select v-model="assignForm.campaignId" class="form-select">
              <option value="">— Seç —</option>
              <option v-for="c in campaigns" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Kiosk</label>
            <select v-model="assignForm.kioskId" class="form-select">
              <option value="">— Seç —</option>
              <option v-for="k in allKiosks" :key="k.id" :value="k.id">{{ k.pharmacyName }} / {{ k.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Başlangıç (saat)</label>
              <input type="number" v-model.number="assignForm.start" min="0" max="23" class="form-input" />
            </div>
            <div class="form-group">
              <label>Bitiş (saat)</label>
              <input type="number" v-model.number="assignForm.end" min="1" max="24" class="form-input" />
            </div>
          </div>

          <div class="modal-actions">
            <button class="modal-btn cancel" @click="showAssignModal = false">İptal</button>
            <button class="modal-btn confirm" @click="confirmAssign">Ata</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// --- CONFIG ---
const cellWidth = 52   // px per hour
const hours = Array.from({ length: 24 }, (_, i) => i)
const timeLabels = hours.map(h => `${String(h).padStart(2, '0')}:00`)
const timelineWidth = computed(() => cellWidth * 24)

// --- STATE ---
const activeView = ref('today')
const views = [
  { key: 'today', label: 'Bugün' },
  { key: 'week', label: 'Hafta' },
]
const hoveredBlock = ref(null)
const selectedBlock = ref(null)
const showAssignModal = ref(false)
const assignForm = ref({ campaignId: '', kioskId: '', start: 8, end: 12 })

// --- DATA ---
const campaigns = ref([
  { id: 1, name: 'X Vitamin Reklamı', color: '#22d3ee', client: 'Bayer AG', mediaType: 'Video 30s', priority: 'Yüksek' },
  { id: 2, name: 'Güneş Kremi Kampanyası', color: '#f59e0b', client: 'L\'Oréal', mediaType: 'Carousel', priority: 'Normal' },
  { id: 3, name: 'Ağrı Kesici Promosyon', color: '#a78bfa', client: 'Novartis', mediaType: 'Video 15s', priority: 'Yüksek' },
  { id: 4, name: 'Bebek Bakım', color: '#34d399', client: 'Johnsons', mediaType: 'Statik Görsel', priority: 'Düşük' },
  { id: 5, name: 'Allerji Sezonu', color: '#fb7185', client: 'UCB Pharma', mediaType: 'Video 20s', priority: 'Normal' },
])

const pharmacies = ref([
  {
    id: 1, name: 'Merkez Eczanesi',
    kiosks: [
      { id: 'k1', name: 'Kiosk-01', online: true },
      { id: 'k2', name: 'Kiosk-02', online: true },
    ]
  },
  {
    id: 2, name: 'Sağlık Eczanesi',
    kiosks: [
      { id: 'k3', name: 'Kiosk-01', online: false },
      { id: 'k4', name: 'Kiosk-02', online: true },
    ]
  },
  {
    id: 3, name: 'Hayat Eczanesi',
    kiosks: [
      { id: 'k5', name: 'Kiosk-01', online: true },
    ]
  },
])

// blocks: { id, kioskId, campaignId, name, color, start, end (hours), client, mediaType, priority }
const blocks = ref([
  { id: 'b1', kioskId: 'k1', campaignId: 1, name: 'X Vitamin Reklamı', color: '#22d3ee', start: 8, end: 12, client: 'Bayer AG', mediaType: 'Video 30s', priority: 'Yüksek' },
  { id: 'b2', kioskId: 'k1', campaignId: 2, name: 'Güneş Kremi Kampanyası', color: '#f59e0b', start: 12, end: 16, client: 'L\'Oréal', mediaType: 'Carousel', priority: 'Normal' },
  { id: 'b3', kioskId: 'k1', campaignId: 3, name: 'Ağrı Kesici Promosyon', color: '#a78bfa', start: 10, end: 14, client: 'Novartis', mediaType: 'Video 15s', priority: 'Yüksek' },
  { id: 'b4', kioskId: 'k2', campaignId: 4, name: 'Bebek Bakım', color: '#34d399', start: 9, end: 13, client: 'Johnsons', mediaType: 'Statik Görsel', priority: 'Düşük' },
  { id: 'b5', kioskId: 'k3', campaignId: 5, name: 'Allerji Sezonu', color: '#fb7185', start: 7, end: 19, client: 'UCB Pharma', mediaType: 'Video 20s', priority: 'Normal' },
  { id: 'b6', kioskId: 'k4', campaignId: 1, name: 'X Vitamin Reklamı', color: '#22d3ee', start: 6, end: 10, client: 'Bayer AG', mediaType: 'Video 30s', priority: 'Yüksek' },
  { id: 'b7', kioskId: 'k4', campaignId: 2, name: 'Güneş Kremi Kampanyası', color: '#f59e0b', start: 14, end: 20, client: 'L\'Oréal', mediaType: 'Carousel', priority: 'Normal' },
  { id: 'b8', kioskId: 'k5', campaignId: 3, name: 'Ağrı Kesici Promosyon', color: '#a78bfa', start: 8, end: 20, client: 'Novartis', mediaType: 'Video 15s', priority: 'Yüksek' },
  { id: 'b9', kioskId: 'k5', campaignId: 5, name: 'Allerji Sezonu', color: '#fb7185', start: 10, end: 18, client: 'UCB Pharma', mediaType: 'Video 20s', priority: 'Normal' },
])

// --- COMPUTED ---
const allKiosks = computed(() => {
  const result = []
  pharmacies.value.forEach(p => {
    p.kiosks.forEach(k => result.push({ ...k, pharmacyName: p.name }))
  })
  return result
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
})

const nowHour = computed(() => new Date().getHours() + new Date().getMinutes() / 60)
const nowLinePx = computed(() => nowHour.value * cellWidth)

const stats = computed(() => {
  const activeBlocks = blocks.value.filter(b => b.start <= nowHour.value && b.end > nowHour.value)
  const conflictKiosks = new Set()
  allKiosks.value.forEach(k => {
    for (let h = 0; h < 24; h++) {
      if (hasConflict(k.id, h)) { conflictKiosks.add(k.id); break }
    }
  })
  return [
    { label: 'Aktif Kampanya', value: activeBlocks.length },
    { label: 'Toplam Atama', value: blocks.value.length },
    { label: 'Çakışma Olan Kiosk', value: conflictKiosks.size },
    { label: 'Toplam Kiosk', value: allKiosks.value.length },
    { label: 'Kampanya', value: campaigns.value.length },
  ]
})

// --- HELPERS ---
function getKioskBlocks(kioskId) {
  return blocks.value
    .filter(b => b.kioskId === kioskId)
    .map(b => ({
      ...b,
      startPx: b.start * cellWidth,
      widthPx: (b.end - b.start) * cellWidth,
    }))
}

function hasConflict(kioskId, hourIdx) {
  const kioskBlocks = blocks.value.filter(b => b.kioskId === kioskId)
  const overlapping = kioskBlocks.filter(b => b.start <= hourIdx && b.end > hourIdx)
  return overlapping.length > 1
}

function isCurrentHour(hIdx) {
  return Math.floor(nowHour.value) === hIdx
}

function isCurrentKioskVisible(_kioskId) {
  return true
}

function formatHour(h) {
  return `${String(h).padStart(2, '0')}:00`
}

function selectBlock(block) {
  selectedBlock.value = selectedBlock.value?.id === block.id ? null : block
}

function removeBlock(block) {
  blocks.value = blocks.value.filter(b => b.id !== block.id)
  selectedBlock.value = null
}

function openAssignModal(kiosk = null, hourIdx = null) {
  assignForm.value = {
    campaignId: '',
    kioskId: kiosk?.id ?? '',
    start: hourIdx ?? 8,
    end: (hourIdx ?? 8) + 4,
  }
  showAssignModal.value = true
}

function confirmAssign() {
  const camp = campaigns.value.find(c => c.id === parseInt(assignForm.value.campaignId))
  if (!camp || !assignForm.value.kioskId || assignForm.value.start >= assignForm.value.end) return

  const newBlock = {
    id: 'b' + Date.now(),
    kioskId: assignForm.value.kioskId,
    campaignId: camp.id,
    name: camp.name,
    color: camp.color,
    start: assignForm.value.start,
    end: assignForm.value.end,
    client: camp.client,
    mediaType: camp.mediaType,
    priority: camp.priority,
  }
  blocks.value.push(newBlock)
  showAssignModal.value = false
}
</script>

<style scoped>
/* ── Root ── */
.scheduler-root {
  min-height: 100vh;
  background: #0a0c0f;
  color: #e2e8f0;
  font-family: 'Figtree', sans-serif;
  padding: 2rem 2rem 4rem;
  position: relative;
  overflow-x: hidden;
}

/* subtle grid texture */
.scheduler-root::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(34, 211, 238, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 211, 238, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

* { box-sizing: border-box; }

/* ── Header ── */
.header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(34, 211, 238, 0.12);
}
.header-eyebrow {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.25em;
  color: #22d3ee;
  margin-bottom: 0.35rem;
}
.header-title {
  font-family: 'Azeret Mono', monospace;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #f8fafc;
  margin: 0 0 0.25rem;
}
.header-sub {
  font-size: 0.8rem;
  color: #64748b;
  font-family: 'Azeret Mono', monospace;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.view-toggle {
  display: flex;
  background: #131820;
  border: 1px solid #1e293b;
  border-radius: 6px;
  overflow: hidden;
}
.toggle-btn {
  padding: 0.45rem 1.1rem;
  font-size: 0.78rem;
  font-family: 'Azeret Mono', monospace;
  color: #64748b;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}
.toggle-btn.active {
  background: #22d3ee;
  color: #0a0c0f;
  font-weight: 600;
}
.btn-add {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1.25rem;
  background: #22d3ee;
  color: #0a0c0f;
  border: none;
  border-radius: 6px;
  font-family: 'Figtree', sans-serif;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
}
.btn-add:hover {
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
  transform: translateY(-1px);
}
.btn-icon { font-size: 1.1rem; line-height: 1; }

/* ── Legend ── */
.legend {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: #94a3b8;
  font-family: 'Azeret Mono', monospace;
}
.legend-dot {
  width: 10px; height: 10px;
  border-radius: 2px;
}
.legend-dot.conflict {
  background: #ef4444;
  box-shadow: 0 0 6px #ef444499;
  animation: pulse-red 1.5s infinite;
}
.legend-dot.empty {
  background: #1e293b;
  border: 1px solid #334155;
}
.legend-separator {
  width: 1px; height: 16px;
  background: #1e293b;
  margin: 0 0.25rem;
}

/* ── Scheduler Wrapper ── */
.scheduler-wrapper {
  position: relative;
  z-index: 1;
  background: #0d1117;
  border: 1px solid #1e293b;
  border-radius: 12px;
  overflow-x: auto;
  overflow-y: visible;
  scrollbar-width: thin;
  scrollbar-color: #22d3ee22 transparent;
}
.scheduler-wrapper::-webkit-scrollbar { height: 4px; }
.scheduler-wrapper::-webkit-scrollbar-thumb { background: #22d3ee33; border-radius: 2px; }

/* ── Time Axis ── */
.time-axis-spacer {
  display: inline-block;
  width: 220px;
  flex-shrink: 0;
}
.time-axis {
  display: flex;
  padding-left: 220px;
  border-bottom: 1px solid #1e293b;
  position: sticky;
  top: 0;
  background: #0d1117;
  z-index: 10;
}
.time-label {
  flex-shrink: 0;
  font-family: 'Azeret Mono', monospace;
  font-size: 0.65rem;
  color: #475569;
  padding: 0.6rem 0 0.4rem;
  text-align: center;
  border-right: 1px solid #1e2433;
}

/* ── Rows ── */
.rows-container { display: block; }

.pharmacy-group { border-bottom: 1px solid #1e293b; }

.pharmacy-label-row {
  display: flex;
  align-items: stretch;
  background: #111827;
}
.pharmacy-name-cell {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 1rem;
  border-right: 1px solid #1e293b;
}
.pharmacy-icon {
  color: #22d3ee;
  font-size: 1.1rem;
  opacity: 0.7;
}
.pharmacy-name {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.78rem;
  font-weight: 600;
  color: #e2e8f0;
}
.pharmacy-meta {
  font-size: 0.65rem;
  color: #475569;
  font-family: 'Azeret Mono', monospace;
}
.pharmacy-timeline-row {
  display: flex;
  flex: 1;
}
.pharmacy-hour-cell {
  flex-shrink: 0;
  border-right: 1px solid #1e2433;
  background: #111827;
}

/* ── Kiosk Row ── */
.kiosk-row {
  display: flex;
  align-items: stretch;
  border-top: 1px solid #1a2030;
  min-height: 48px;
}
.kiosk-label-cell {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1rem 0 2rem;
  border-right: 1px solid #1e293b;
  background: #0d1117;
}
.kiosk-status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.kiosk-status-dot.online { background: #22d3ee; box-shadow: 0 0 6px #22d3ee; }
.kiosk-status-dot.offline { background: #475569; }
.kiosk-name {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.72rem;
  color: #94a3b8;
}

/* ── Timeline ── */
.kiosk-timeline {
  position: relative;
  display: flex;
  align-items: stretch;
  flex-shrink: 0;
}
.hour-cell {
  flex-shrink: 0;
  border-right: 1px solid #151c28;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
  overflow: visible;
}
.hour-cell:hover { background: rgba(34, 211, 238, 0.04); }

.conflict-cell {
  background: rgba(239, 68, 68, 0.08) !important;
  border-right-color: rgba(239, 68, 68, 0.2);
}
.now-cell {
  background: rgba(34, 211, 238, 0.05) !important;
}

.conflict-pulse {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 4px,
    rgba(239, 68, 68, 0.1) 4px,
    rgba(239, 68, 68, 0.1) 8px
  );
  pointer-events: none;
}

/* ── Campaign Blocks ── */
.campaign-block {
  position: absolute;
  top: 6px;
  bottom: 6px;
  border-radius: 4px;
  cursor: pointer;
  z-index: 5;
  transition: filter 0.15s, transform 0.15s;
  overflow: visible;
}
.campaign-block:hover {
  filter: brightness(1.2);
  transform: scaleY(1.04);
  z-index: 20;
}
.block-inner {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  padding: 0 0.5rem;
  overflow: hidden;
}
.block-name {
  font-size: 0.65rem;
  font-weight: 600;
  color: #0a0c0f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'Figtree', sans-serif;
}
.block-time {
  font-size: 0.58rem;
  color: rgba(0,0,0,0.6);
  font-family: 'Azeret Mono', monospace;
}

/* ── Tooltip ── */
.block-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 180px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0.75rem;
  z-index: 100;
  pointer-events: none;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}
.tt-title {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 0.5rem;
}
.tt-row {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.68rem;
  color: #94a3b8;
  margin-bottom: 0.25rem;
  font-family: 'Figtree', sans-serif;
}

/* ── Now Line ── */
.now-line {
  position: absolute;
  top: 0; bottom: 0;
  width: 2px;
  background: #22d3ee;
  box-shadow: 0 0 8px #22d3ee;
  z-index: 15;
  pointer-events: none;
}
.now-pip {
  width: 8px; height: 8px;
  background: #22d3ee;
  border-radius: 50%;
  position: absolute;
  top: -4px;
  left: -3px;
  box-shadow: 0 0 10px #22d3ee;
}

/* ── Stats Bar ── */
.stats-bar {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 1rem;
  margin-top: 1.25rem;
  flex-wrap: wrap;
}
.stat-card {
  flex: 1;
  min-width: 100px;
  background: #0d1117;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  text-align: center;
}
.stat-value {
  font-family: 'Azeret Mono', monospace;
  font-size: 1.6rem;
  font-weight: 700;
  color: #22d3ee;
}
.stat-label {
  font-size: 0.7rem;
  color: #475569;
  margin-top: 0.2rem;
  font-family: 'Azeret Mono', monospace;
  letter-spacing: 0.05em;
}

/* ── Block Detail Panel ── */
.block-detail-panel {
  position: fixed;
  top: 0; right: 0;
  width: 280px;
  height: 100vh;
  background: #0d1117;
  border-left: 1px solid #1e293b;
  padding: 2rem 1.5rem;
  z-index: 50;
  box-shadow: -8px 0 40px rgba(0,0,0,0.6);
}
.panel-close {
  position: absolute;
  top: 1.25rem; right: 1.25rem;
  background: transparent;
  border: none;
  color: #475569;
  font-size: 1rem;
  cursor: pointer;
  transition: color 0.15s;
}
.panel-close:hover { color: #e2e8f0; }
.panel-eyebrow {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.2em;
  color: #475569;
  margin-bottom: 0.5rem;
}
.panel-title {
  font-family: 'Azeret Mono', monospace;
  font-size: 1rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 1rem;
  line-height: 1.3;
}
.panel-color-bar {
  height: 3px;
  border-radius: 2px;
  margin-bottom: 1.5rem;
}
.panel-rows { display: flex; flex-direction: column; gap: 0.75rem; }
.panel-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #1e293b;
}
.panel-row span:first-child { color: #475569; font-family: 'Azeret Mono', monospace; }
.panel-row span:last-child { color: #e2e8f0; font-weight: 500; }
.panel-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 2rem;
}
.panel-btn {
  flex: 1;
  padding: 0.6rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-family: 'Figtree', sans-serif;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}
.panel-btn.edit {
  background: #1e293b;
  color: #e2e8f0;
}
.panel-btn.edit:hover { background: #334155; }
.panel-btn.delete {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.25);
}
.panel-btn.delete:hover { background: rgba(239, 68, 68, 0.25); }

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-box {
  background: #0d1117;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 2rem;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 24px 60px rgba(0,0,0,0.7);
}
.modal-eyebrow {
  font-family: 'Azeret Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.2em;
  color: #22d3ee;
  margin-bottom: 0.4rem;
}
.modal-title {
  font-family: 'Azeret Mono', monospace;
  font-size: 1.1rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 1.5rem;
}
.form-group {
  margin-bottom: 1rem;
  flex: 1;
}
.form-row {
  display: flex;
  gap: 1rem;
}
.form-group label {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  font-family: 'Azeret Mono', monospace;
  margin-bottom: 0.35rem;
  letter-spacing: 0.05em;
}
.form-select,
.form-input {
  width: 100%;
  background: #131820;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #e2e8f0;
  padding: 0.55rem 0.75rem;
  font-size: 0.82rem;
  font-family: 'Figtree', sans-serif;
  outline: none;
  transition: border-color 0.15s;
}
.form-select:focus,
.form-input:focus { border-color: #22d3ee; }
.form-select option { background: #131820; }
.modal-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
.modal-btn {
  flex: 1;
  padding: 0.65rem;
  border-radius: 6px;
  font-family: 'Figtree', sans-serif;
  font-weight: 600;
  font-size: 0.85rem;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}
.modal-btn.cancel {
  background: #1e293b;
  color: #94a3b8;
}
.modal-btn.cancel:hover { background: #334155; }
.modal-btn.confirm {
  background: #22d3ee;
  color: #0a0c0f;
}
.modal-btn.confirm:hover { box-shadow: 0 0 20px rgba(34, 211, 238, 0.4); }

/* ── Animations ── */
@keyframes pulse-red {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px #ef444499; }
  50% { opacity: 0.5; box-shadow: 0 0 12px #ef4444cc; }
}

.drawer-enter-active, .drawer-leave-active { transition: transform 0.3s cubic-bezier(0.4,0,0.2,1); }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .modal-box, .modal-leave-active .modal-box { transition: transform 0.2s; }
.modal-enter-from .modal-box, .modal-leave-to .modal-box { transform: scale(0.95); }
</style>
