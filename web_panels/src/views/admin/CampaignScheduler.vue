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
