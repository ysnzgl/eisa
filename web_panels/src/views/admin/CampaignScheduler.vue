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
              <div class="pharmacy-name-info">
                <div class="pharmacy-name">{{ pharmacy.name }}</div>
                <div class="pharmacy-meta">
                  {{ pharmacy.kiosks.length }} kiosk · ortalama doluluk
                  <strong>{{ Math.round(pharmacy.kiosks.reduce((s, k) => s + fillRate(k.id), 0) / Math.max(1, pharmacy.kiosks.length)) }}%</strong>
                </div>
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
              <span
                class="fill-badge"
                :class="{
                  high: fillRate(kiosk.id) >= 70,
                  mid:  fillRate(kiosk.id) >= 30 && fillRate(kiosk.id) < 70,
                  low:  fillRate(kiosk.id) < 30,
                }"
                :title="`Reklam doluluk oranı: ${fillRate(kiosk.id)}%`"
              >
                {{ fillRate(kiosk.id) }}%
              </span>
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
import { getPharmacies, getKioskStatus } from '../../services/devices'
import { getCampaigns } from '../../services/campaignManager'

// --- CONFIG ---
const cellWidth = 52   // px per hour
const hours = Array.from({ length: 24 }, (_, i) => i)
const timeLabels = hours.map(h => `${String(h).padStart(2, '0')}:00`)
const timelineWidth = computed(() => cellWidth * 24)

// --- Fixed campaign palette ---
const CAMP_COLORS = [
  '#2563EB', '#7C3AED', '#059669', '#DC2626', '#EA580C',
  '#0891B2', '#DB2777', '#65A30D', '#9333EA', '#0EA5E9',
]
function colorFor(id) { return CAMP_COLORS[(Number(id) || 0) % CAMP_COLORS.length] }

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
const loading = ref(false)

// --- DATA loaded from API ---
const campaigns = ref([])    // [{ id, name, color, client, mediaType, priority }]
const pharmacies = ref([])   // [{ id, name, kiosks: [{id, name, online}] }]
// Local-only campaign blocks (backend henüz scheduler persist endpoint'i sunmuyor)
const blocks = ref([])

async function loadData() {
  loading.value = true
  try {
    const [camps, pharms, kiosks] = await Promise.all([
      getCampaigns().catch(() => []),
      getPharmacies().catch(() => []),
      getKioskStatus().catch(() => []),
    ])

    // Campaign mapping: campaignManager service'i { id, name, client, ... } döndürür
    campaigns.value = (camps || []).filter(c => c.is_active !== false).map(c => ({
      id: c.id,
      name: c.name,
      color: colorFor(c.id),
      client: c.client || '—',
      mediaType: c.duration_sec ? `Video ${c.duration_sec}s` : 'Medya',
      priority: c.priority || 'Normal',
      starts_at: c.starts_at,
      ends_at: c.ends_at,
      broadcast_start: c.broadcast_start || '08:00',
      broadcast_end: c.broadcast_end || '22:00',
      target_pharmacy_ids: c.target_pharmacy_ids || [],
    }))

    // Pharmacy + kiosk grupla
    const kioskByPharmacy = {}
    ;(kiosks || []).forEach(k => {
      const pid = k.pharmacyId ?? k.pharmacy_id ?? k.eczane ?? k.eczane_id ?? null
      if (!pid) return
      if (!kioskByPharmacy[pid]) kioskByPharmacy[pid] = []
      kioskByPharmacy[pid].push({
        id: k.id,
        name: k.name || k.kod || `Kiosk-${k.id}`,
        online: !!(k.online ?? k.is_online ?? (k.lastPing && (Date.now() - new Date(k.lastPing).getTime() < 5 * 60 * 1000))),
      })
    })
    pharmacies.value = (pharms || []).map(p => ({
      id: p.id,
      name: p.name,
      kiosks: kioskByPharmacy[p.id] || [],
    })).filter(p => p.kiosks.length > 0)

    // Mevcut kampanyalardan otomatik blok seed et: yayın saatleri × hedef eczane kiosk'ları
    blocks.value = []
    campaigns.value.forEach(c => {
      const [sH] = (c.broadcast_start || '08:00').split(':').map(Number)
      const [eH] = (c.broadcast_end || '22:00').split(':').map(Number)
      const targetIds = (c.target_pharmacy_ids?.length ? c.target_pharmacy_ids : pharmacies.value.map(p => p.id))
      pharmacies.value.forEach(p => {
        if (!targetIds.includes(p.id)) return
        p.kiosks.forEach(k => {
          blocks.value.push({
            id: `seed-${c.id}-${k.id}`,
            kioskId: k.id,
            campaignId: c.id,
            name: c.name,
            color: c.color,
            start: sH,
            end: eH,
            client: c.client,
            mediaType: c.mediaType,
            priority: c.priority,
          })
        })
      })
    })
  } finally {
    loading.value = false
  }
}

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

// Doluluk: kiosk başına atanan saat / 24 (overlap'ler birleştirilerek)
function fillRate(kioskId) {
  const kBlocks = blocks.value.filter(b => b.kioskId === kioskId)
  if (!kBlocks.length) return 0
  // Saat hücrelerini boolean olarak topla; overlap çakışma sayar ama doluluğa tek katkı yapar
  const occupied = new Array(24).fill(false)
  kBlocks.forEach(b => {
    for (let h = Math.max(0, b.start); h < Math.min(24, b.end); h++) occupied[h] = true
  })
  return Math.round((occupied.filter(Boolean).length / 24) * 100)
}

const stats = computed(() => {
  const activeBlocks = blocks.value.filter(b => b.start <= nowHour.value && b.end > nowHour.value)
  const conflictKiosks = new Set()
  allKiosks.value.forEach(k => {
    for (let h = 0; h < 24; h++) {
      if (hasConflict(k.id, h)) { conflictKiosks.add(k.id); break }
    }
  })
  const totalFill = allKiosks.value.length
    ? Math.round(allKiosks.value.reduce((s, k) => s + fillRate(k.id), 0) / allKiosks.value.length)
    : 0
  return [
    { label: 'Aktif Kampanya', value: activeBlocks.length },
    { label: 'Ortalama Doluluk', value: `${totalFill}%` },
    { label: 'Çakışmalı Kiosk', value: conflictKiosks.size },
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

function isCurrentKioskVisible(_kioskId) { return true }
function formatHour(h) { return `${String(h).padStart(2, '0')}:00` }

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

  blocks.value.push({
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
  })
  showAssignModal.value = false
}


onMounted(loadData)
</script>

<style scoped>
/* ─── Root ──────────────────────────────────────────── */
.scheduler-root {
  background: #F2F1EE;
  color: #111827;
  font-family: 'Figtree', system-ui, sans-serif;
  min-height: 100vh;
  position: relative;
}

/* ─── Header ─────────────────────────────────────────── */
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: rgba(255,255,255,0.97);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #E5E3DF;
  position: sticky;
  top: 0;
  z-index: 20;
}
.header-left { flex: 1; }
.header-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 4px;
  font-family: 'Azeret Mono', monospace;
}
.header-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
  margin: 0 0 2px;
}
.header-sub {
  font-size: 12px;
  color: #6B7280;
  font-weight: 400;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ─── View Toggle ────────────────────────────────────── */
.view-toggle {
  display: flex;
  background: #F3F4F6;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.toggle-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #6B7280;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.toggle-btn.active {
  background: #FFFFFF;
  color: #111827;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

/* ─── Add Button ─────────────────────────────────────── */
.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 14px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-add:hover { opacity: 0.9; }
.btn-icon { font-size: 16px; font-weight: 400; line-height: 1; }

/* ─── Legend ─────────────────────────────────────────── */
.legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 20px;
  padding: 10px 28px;
  background: #FFFFFF;
  border-bottom: 1px solid #E5E3DF;
  font-size: 12px;
  color: #374151;
}
.legend-separator {
  width: 1px;
  height: 16px;
  background: #E5E3DF;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-dot.conflict { background: #EF4444; }
.legend-dot.empty { background: #D1D5DB; border: 1px solid #9CA3AF; }

/* ─── Scheduler Wrapper ──────────────────────────────── */
.scheduler-wrapper {
  overflow-x: auto;
  overflow-y: visible;
  padding-bottom: 8px;
}

/* ─── Time Axis ──────────────────────────────────────── */
.time-axis {
  display: flex;
  padding-left: 200px;
  border-bottom: 1px solid #E5E3DF;
  background: #FAFAF9;
  position: sticky;
  top: 74px;
  z-index: 10;
}
.time-label {
  font-size: 10px;
  font-weight: 600;
  color: #9CA3AF;
  text-align: center;
  padding: 4px 0;
  border-right: 1px solid #F3F4F6;
  font-family: 'Azeret Mono', monospace;
  flex-shrink: 0;
}
.time-axis-spacer {
  display: none; /* padding-left on time-axis handles offset */
}

/* ─── Rows Container ─────────────────────────────────── */
.rows-container { background: #FFFFFF; }

/* ─── Pharmacy Group ─────────────────────────────────── */
.pharmacy-group { border-bottom: 2px solid #E5E7EB; }
.pharmacy-label-row {
  display: flex;
  align-items: stretch;
  background: #F8FAFC;
  border-bottom: 1px solid #E5E3DF;
}
.pharmacy-name-cell {
  width: 200px;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-right: 1px solid #E5E3DF;
  position: sticky;
  left: 0;
  background: #F8FAFC;
  z-index: 5;
  flex-shrink: 0;
}
.pharmacy-icon { font-size: 18px; color: #2563EB; flex-shrink: 0; }
.pharmacy-name-info { min-width: 0; }
.pharmacy-name {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pharmacy-meta { font-size: 10px; color: #6B7280; margin-top: 1px; }
.pharmacy-timeline-row { display: flex; flex: 1; }
.pharmacy-hour-cell {
  border-right: 1px solid #F0F0EF;
  background: #F8FAFC;
  flex-shrink: 0;
}

/* ─── Kiosk Row ──────────────────────────────────────── */
.kiosk-row {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid #F3F4F6;
  min-height: 42px;
}
.kiosk-label-cell {
  width: 200px;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border-right: 1px solid #E5E3DF;
  position: sticky;
  left: 0;
  background: #FFFFFF;
  z-index: 5;
  flex-shrink: 0;
}
.kiosk-status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.kiosk-status-dot.online  { background: #10B981; }
.kiosk-status-dot.offline { background: #D1D5DB; }
.kiosk-name {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ─── Fill Badge ─────────────────────────────────────── */
.fill-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'Azeret Mono', monospace;
  flex-shrink: 0;
}
.fill-badge.high { background: #FEF2F2; color: #DC2626; }
.fill-badge.mid  { background: #FFF7ED; color: #D97706; }
.fill-badge.low  { background: #F0FDF4; color: #059669; }

/* ─── Kiosk Timeline ─────────────────────────────────── */
.kiosk-timeline {
  position: relative;
  display: flex;
  flex-shrink: 0;
  overflow: visible;
}
.hour-cell {
  border-right: 1px solid #F0F0EF;
  flex-shrink: 0;
  cursor: pointer;
  position: relative;
  transition: background 0.12s;
  min-height: 42px;
}
.hour-cell:hover { background: #EFF6FF; }
.conflict-cell { background: #FEE2E2 !important; }
.now-cell { background: #EFF6FF; }

/* ─── Conflict Pulse ─────────────────────────────────── */
.conflict-pulse {
  position: absolute;
  inset: 0;
  background: rgba(239, 68, 68, 0.15);
  animation: conflict-blink 1.4s ease-in-out infinite;
}
@keyframes conflict-blink {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.5; }
}

/* ─── Campaign Block ─────────────────────────────────── */
.campaign-block {
  position: absolute;
  top: 4px;
  bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  overflow: visible;
  z-index: 4;
  transition: filter 0.15s, transform 0.15s;
}
.campaign-block:hover { filter: brightness(1.08); transform: scaleY(1.05); z-index: 6; }
.block-inner {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 3px 6px;
  height: 100%;
  overflow: hidden;
}
.block-name {
  font-size: 10px;
  font-weight: 700;
  color: rgba(255,255,255,0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.block-time {
  font-size: 9px;
  font-family: 'Azeret Mono', monospace;
  color: rgba(255,255,255,0.75);
  white-space: nowrap;
}

/* ─── Block Tooltip ──────────────────────────────────── */
.block-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  min-width: 180px;
  background: #1F2937;
  border-radius: 8px;
  padding: 10px 12px;
  z-index: 30;
  box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  pointer-events: none;
}
.tt-title {
  font-size: 12px;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 4px;
}
.tt-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #D1D5DB;
  margin-top: 3px;
  gap: 8px;
}
.tt-row span:last-child { color: #F9FAFB; font-weight: 600; }

/* ─── Now Line ───────────────────────────────────────── */
.now-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #EF4444;
  z-index: 8;
  pointer-events: none;
}
.now-pip {
  position: absolute;
  top: -3px;
  left: -4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #EF4444;
  box-shadow: 0 0 6px #EF4444;
}

/* ─── Stats Bar ──────────────────────────────────────── */
.stats-bar {
  display: flex;
  gap: 12px;
  padding: 16px 28px;
  background: #FFFFFF;
  border-top: 1px solid #E5E3DF;
  overflow-x: auto;
}
.stat-card {
  background: #F9FAFB;
  border: 1px solid #E5E3DF;
  border-radius: 10px;
  padding: 12px 18px;
  min-width: 110px;
  flex-shrink: 0;
  text-align: center;
}
.stat-value {
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  line-height: 1;
  font-family: 'Azeret Mono', monospace;
}
.stat-label {
  font-size: 10px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 4px;
}

/* ─── Block Detail Panel ─────────────────────────────── */
.block-detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  height: 100%;
  width: 300px;
  background: #FFFFFF;
  border-left: 1px solid #E5E3DF;
  box-shadow: -6px 0 32px rgba(0,0,0,0.10);
  z-index: 50;
  padding: 24px 20px;
  overflow-y: auto;
}
.panel-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid #E5E3DF;
  background: #F9FAFB;
  font-size: 12px;
  color: #6B7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.panel-close:hover { background: #F3F4F6; color: #111827; }
.panel-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 4px;
}
.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 12px;
}
.panel-color-bar { height: 4px; border-radius: 2px; margin-bottom: 16px; }
.panel-rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.panel-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #F3F4F6;
}
.panel-row span:first-child { color: #6B7280; }
.panel-row span:last-child { color: #111827; font-weight: 600; }
.panel-actions { display: flex; gap: 8px; }
.panel-btn {
  flex: 1;
  padding: 8px;
  font-size: 12px;
  font-weight: 700;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}
.panel-btn.edit  { background: #EFF6FF; color: #2563EB; }
.panel-btn.edit:hover { background: #DBEAFE; }
.panel-btn.delete { background: #FEF2F2; color: #DC2626; }
.panel-btn.delete:hover { background: #FEE2E2; }

/* ─── Modal ──────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(4px);
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal-box {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.15);
}
.modal-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 4px;
}
.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 16px;
}
.form-group { margin-bottom: 14px; }
.form-group label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin-bottom: 5px;
}
.form-select,
.form-input {
  width: 100%;
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 8px;
  color: #111827;
  font-size: 13px;
  padding: 8px 10px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-select:focus,
.form-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.10);
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.modal-actions { display: flex; gap: 8px; margin-top: 20px; }
.modal-btn {
  flex: 1;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 700;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.modal-btn.cancel { background: #F3F4F6; color: #374151; }
.modal-btn.cancel:hover { background: #E5E7EB; }
.modal-btn.confirm {
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
}
.modal-btn.confirm:hover { opacity: 0.9; }

/* ─── Transitions ────────────────────────────────────── */
.drawer-enter-active,
.drawer-leave-active { transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-enter-from,
.drawer-leave-to { transform: translateX(100%); }
.modal-enter-active,
.modal-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; transform: scale(0.96); }
</style>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap');

/* ─── Root ──────────────────────────────────────────── */
.scheduler-root {
  background: #F2F1EE;
  color: #111827;
  font-family: 'Syne', system-ui, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ─── Header ─────────────────────────────────────────── */
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: rgba(255,255,255,0.97);
  border-bottom: 1px solid #E5E3DF;
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.header-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 4px;
}
.header-title {
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  line-height: 1.1;
}
.header-sub {
  font-size: 12px;
  color: #9CA3AF;
  margin-top: 4px;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

/* ─── View Toggle ────────────────────────────────────── */
.view-toggle {
  display: flex;
  background: #F3F4F6;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.toggle-btn {
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.toggle-btn.active {
  background: #FFFFFF;
  color: #111827;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

/* ─── Add Button ─────────────────────────────────────── */
.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(37,99,235,0.25);
  transition: opacity 0.15s;
}
.btn-add:hover { opacity: 0.9; }
.btn-icon {
  font-size: 16px;
  line-height: 1;
  font-weight: 300;
}

/* ─── Legend ─────────────────────────────────────────── */
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 28px;
  background: #FAFAF9;
  border-bottom: 1px solid #E5E3DF;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #6B7280;
  font-weight: 500;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-dot.conflict {
  background: repeating-linear-gradient(
    45deg,
    #DC2626,
    #DC2626 2px,
    #FEE2E2 2px,
    #FEE2E2 5px
  );
}
.legend-dot.empty {
  background: #E5E7EB;
  border: 1px solid #D1D5DB;
}
.legend-separator {
  width: 1px;
  height: 14px;
  background: #E5E3DF;
  margin: 0 4px;
}

/* ─── Scheduler Wrapper ──────────────────────────────── */
.scheduler-wrapper {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
  position: relative;
}

/* ─── Time Axis ──────────────────────────────────────── */
.time-axis-spacer {
  display: inline-block;
  width: 220px;
  flex-shrink: 0;
}
.time-axis {
  display: flex;
  padding-left: 220px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: #FFFFFF;
  border-bottom: 1px solid #E5E3DF;
}
.time-label {
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  color: #9CA3AF;
  padding: 4px 0;
  text-align: center;
  border-right: 1px solid #F3F4F6;
  flex-shrink: 0;
}

/* ─── Rows Container ─────────────────────────────────── */
.rows-container {
  min-width: max-content;
}

/* ─── Pharmacy Group ─────────────────────────────────── */
.pharmacy-group {
  border-bottom: 2px solid #E5E3DF;
}
.pharmacy-label-row {
  display: flex;
  background: #F9F8F6;
  border-bottom: 1px solid #E5E3DF;
}
.pharmacy-name-cell {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-right: 1px solid #E5E3DF;
  position: sticky;
  left: 0;
  background: #F9F8F6;
  z-index: 5;
}
.pharmacy-icon {
  font-size: 18px;
  color: #2563EB;
  flex-shrink: 0;
}
.pharmacy-name {
  font-size: 12px;
  font-weight: 700;
  color: #111827;
}
.pharmacy-meta {
  font-size: 10px;
  color: #9CA3AF;
  margin-top: 1px;
}
.pharmacy-timeline-row {
  display: flex;
}
.pharmacy-hour-cell {
  border-right: 1px solid #F3F4F6;
  height: 32px;
  flex-shrink: 0;
  background: #F9F8F6;
}

/* ─── Kiosk Row ──────────────────────────────────────── */
.kiosk-row {
  display: flex;
  border-bottom: 1px solid #F3F4F6;
}
.kiosk-row:hover .kiosk-label-cell {
  background: #F3F4F6;
}
.kiosk-label-cell {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-right: 1px solid #E5E3DF;
  position: sticky;
  left: 0;
  background: #FFFFFF;
  z-index: 5;
  transition: background 0.1s;
}
.kiosk-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.kiosk-status-dot.online  { background: #10B981; box-shadow: 0 0 0 2px rgba(16,185,129,0.2); }
.kiosk-status-dot.offline { background: #D1D5DB; }
.kiosk-name {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fill-badge {
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 9999px;
  flex-shrink: 0;
}
.fill-badge.high { background: #DCFCE7; color: #16A34A; }
.fill-badge.mid  { background: #FEF9C3; color: #CA8A04; }
.fill-badge.low  { background: #F3F4F6; color: #9CA3AF; }

/* ─── Timeline ───────────────────────────────────────── */
.kiosk-timeline {
  position: relative;
  display: flex;
  height: 36px;
}
.hour-cell {
  border-right: 1px solid #F3F4F6;
  height: 100%;
  flex-shrink: 0;
  cursor: pointer;
  transition: background 0.1s;
  position: relative;
}
.hour-cell:hover { background: rgba(37,99,235,0.04); }
.hour-cell.now-cell { background: rgba(37,99,235,0.06); }
.hour-cell.conflict-cell { background: rgba(220,38,38,0.08); }

/* ─── Conflict Pulse ─────────────────────────────────── */
.conflict-pulse {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(220,38,38,0.4);
  border-radius: 2px;
  animation: conflict-blink 1.4s ease-in-out infinite;
}
@keyframes conflict-blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}

/* ─── Campaign Block ─────────────────────────────────── */
.campaign-block {
  position: absolute;
  top: 4px;
  height: 28px;
  border-radius: 5px;
  overflow: hidden;
  cursor: pointer;
  z-index: 2;
  transition: filter 0.12s, transform 0.12s;
}
.campaign-block:hover {
  filter: brightness(1.08);
  transform: scaleY(1.06);
  z-index: 3;
}
.block-inner {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  white-space: nowrap;
  overflow: hidden;
}
.block-name {
  font-size: 11px;
  font-weight: 700;
  color: #FFFFFF;
  overflow: hidden;
  text-overflow: ellipsis;
}
.block-time {
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  color: rgba(255,255,255,0.8);
  flex-shrink: 0;
}

/* ─── Block Tooltip ──────────────────────────────────── */
.block-tooltip {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 180px;
  background: #1F2937;
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  z-index: 20;
  pointer-events: none;
}
.tt-title {
  font-size: 12px;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 6px;
}
.tt-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 11px;
  color: #9CA3AF;
  padding: 2px 0;
}
.tt-row span:last-child { color: #E5E7EB; }

/* ─── Now Line ───────────────────────────────────────── */
.now-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #2563EB;
  z-index: 4;
  pointer-events: none;
}
.now-pip {
  position: absolute;
  top: -4px;
  left: -4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2563EB;
}

/* ─── Stats Bar ──────────────────────────────────────── */
.stats-bar {
  display: flex;
  gap: 1px;
  background: #E5E3DF;
  border-top: 1px solid #E5E3DF;
  flex-shrink: 0;
}
.stat-card {
  flex: 1;
  background: #FFFFFF;
  padding: 10px 16px;
  text-align: center;
}
.stat-value {
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  line-height: 1;
}
.stat-label {
  font-size: 10px;
  color: #9CA3AF;
  margin-top: 3px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

/* ─── Block Detail Panel ─────────────────────────────── */
.block-detail-panel {
  position: fixed;
  right: 0;
  top: 0;
  height: 100%;
  width: 280px;
  background: #FFFFFF;
  border-left: 1px solid #E5E3DF;
  box-shadow: -6px 0 28px rgba(0,0,0,0.08);
  padding: 24px 20px;
  z-index: 30;
  overflow-y: auto;
}
.panel-close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid #E5E3DF;
  background: #F9F8F6;
  color: #6B7280;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s;
}
.panel-close:hover { background: #F3F4F6; color: #111827; }
.panel-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 6px;
}
.panel-title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 10px;
  line-height: 1.2;
}
.panel-color-bar {
  height: 4px;
  border-radius: 2px;
  margin-bottom: 16px;
}
.panel-rows { display: flex; flex-direction: column; gap: 8px; }
.panel-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 12px;
}
.panel-row span:first-child { color: #9CA3AF; font-weight: 500; }
.panel-row span:last-child  { color: #111827; font-weight: 600; }
.panel-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
}
.panel-btn {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #E5E3DF;
  cursor: pointer;
  transition: background 0.12s;
}
.panel-btn.edit  { background: #F3F4F6; color: #111827; }
.panel-btn.edit:hover { background: #E5E7EB; }
.panel-btn.delete { background: #FEE2E2; color: #DC2626; border-color: #FECACA; }
.panel-btn.delete:hover { background: #FECACA; }

/* ─── Modal ──────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.45);
  backdrop-filter: blur(5px);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal-box {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 16px;
  padding: 28px 24px 20px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
}
.modal-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 4px;
}
.modal-title {
  font-size: 18px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 16px;
}
.form-group {
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6B7280;
  margin-bottom: 6px;
}
.form-select,
.form-input {
  width: 100%;
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 8px;
  color: #111827;
  font-size: 13px;
  padding: 8px 12px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-select:focus,
.form-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.10);
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}
.modal-btn {
  flex: 1;
  padding: 9px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.12s;
  border: none;
}
.modal-btn.cancel  {
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #E5E3DF;
}
.modal-btn.cancel:hover { background: #E5E7EB; }
.modal-btn.confirm {
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #FFFFFF;
  box-shadow: 0 3px 10px rgba(37,99,235,0.25);
}
.modal-btn.confirm:hover { opacity: 0.9; }

/* ─── Transitions ────────────────────────────────────── */
.drawer-enter-active, .drawer-leave-active {
  transition: transform 0.25s cubic-bezier(0.4,0,0.2,1);
}
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }

.modal-enter-active, .modal-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
