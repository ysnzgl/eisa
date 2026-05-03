<script setup>
/**
 * Admin Dashboard — Genel bakış ekranı (Modül 5).
 * Mock verilerle KPI kartları, haftalık bar chart (SVG), kategori donut chart (SVG),
 * son kampanyalar tablosu ve sistem uyarıları gösterir.
 */
import { ref, computed, onMounted } from 'vue';

// ── Constants ──────────────────────────────────────────────────
const CIRC = 2 * Math.PI * 70   // donut circumference ≈ 439.82
const CHART_BOTTOM = 168
const CHART_H = 153              // bar chart usable height (px in viewBox)
const MAX_BAR = 13000

// ── KPI Cards ──────────────────────────────────────────────────
const kpiCards = [
  {
    id: 'pharmacies',
    label: 'Toplam Eczane',
    target: 1204,
    color: '#2563EB',
    iconSvg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  },
  {
    id: 'kiosks',
    label: 'Aktif Kiosk',
    target: 3450,
    outOf: '3.500',
    color: '#059669',
    iconSvg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
    sub: '50 Cihaz Çevrimdışı',
    subClass: 'danger-sub',
  },
  {
    id: 'campaigns',
    label: 'Yayındaki Kampanya',
    target: 42,
    color: '#7C3AED',
    iconSvg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
  },
  {
    id: 'qr',
    label: 'Bugün Üretilen QR',
    target: 12840,
    color: '#D97706',
    iconSvg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="3" height="3"/><rect x="18" y="18" width="3" height="3"/></svg>`,
    sub: '▲ %15 artış (dünden)',
    subClass: 'success-sub',
  },
]

const displayValues = ref(kpiCards.map(() => '0'))

function countUp(index, target, duration = 1500) {
  const start = performance.now()
  const tick = (now) => {
    const t = Math.min((now - start) / duration, 1)
    const ease = 1 - Math.pow(1 - t, 4)
    displayValues.value[index] = Math.round(ease * target).toLocaleString('tr-TR')
    if (t < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => {
  kpiCards.forEach((kpi, i) => {
    setTimeout(() => countUp(i, kpi.target), i * 160 + 400)
  })
})

// ── Date ───────────────────────────────────────────────────────
const currentDate = computed(() =>
  new Date().toLocaleDateString('tr-TR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })
)

// ── Bar Chart ──────────────────────────────────────────────────
const weeklyData = [
  { day: 'Pts', value: 8420 },
  { day: 'Sal', value: 9340 },
  { day: 'Çar', value: 7890 },
  { day: 'Per', value: 10250 },
  { day: 'Cum', value: 11800 },
  { day: 'Cmt', value: 6340 },
  { day: 'Paz', value: 12840 },
]

const totalWeekly = computed(() => weeklyData.reduce((s, d) => s + d.value, 0))

function barH(val) { return (val / MAX_BAR) * CHART_H }
function barY(val) { return CHART_BOTTOM - barH(val) }
function barX(i)   { return 66 + i * 74 }

const yGrid = [
  { label: '3k',  y: CHART_BOTTOM - (3000  / MAX_BAR) * CHART_H },
  { label: '6k',  y: CHART_BOTTOM - (6000  / MAX_BAR) * CHART_H },
  { label: '9k',  y: CHART_BOTTOM - (9000  / MAX_BAR) * CHART_H },
  { label: '12k', y: CHART_BOTTOM - (12000 / MAX_BAR) * CHART_H },
]

// ── Donut Chart ────────────────────────────────────────────────
const categoryData = [
  { label: 'Enerji',        pct: 28, color: '#2563EB' },
  { label: 'Uyku',          pct: 22, color: '#7C3AED' },
  { label: 'Kadın Sağlığı', pct: 18, color: '#DB2777' },
  { label: 'Bağışıklık',    pct: 17, color: '#059669' },
  { label: 'Diğer',         pct: 15, color: '#F59E0B' },
]

const donutSegments = computed(() => {
  let cum = 0
  return categoryData.map(cat => {
    const dash = (cat.pct / 100) * CIRC
    const rotate = cum * 3.6
    cum += cat.pct
    return { ...cat, dash, rotate }
  })
})

const totalSessions = 87340

// ── Recent Campaigns ───────────────────────────────────────────
const recentCampaigns = [
  { id: 1, name: 'X Vitamin Reklamı',       client: 'Bayer AG',    kiosks: 24, color: '#22d3ee', status: 'active',    statusLabel: 'Yayında'   },
  { id: 2, name: 'Güneş Kremi',             client: "L'Oréal",     kiosks: 18, color: '#f59e0b', status: 'active',    statusLabel: 'Yayında'   },
  { id: 3, name: 'Ağrı Kesici Promosyon',   client: 'Novartis',    kiosks: 31, color: '#a78bfa', status: 'active',    statusLabel: 'Yayında'   },
  { id: 4, name: 'Bebek Bakım',             client: 'Johnsons',    kiosks: 12, color: '#34d399', status: 'scheduled', statusLabel: 'Planlandı' },
  { id: 5, name: 'Allerji Sezonu',          client: 'UCB Pharma',  kiosks: 45, color: '#fb7185', status: 'ended',     statusLabel: 'Bitti'     },
]

// ── System Alerts ──────────────────────────────────────────────
const alerts = [
  { id: 1, level: 'error',   message: 'Ankara Merkez Eczanesi Kiosk-2 bağlantısı koptu',   time: '14:32 · Bugün' },
  { id: 2, level: 'error',   message: 'İstanbul Kadıköy Eczanesi Kiosk-1 çevrimdışı',      time: '13:17 · Bugün' },
  { id: 3, level: 'warning', message: 'İzmir Bornova Eczanesi yazıcı kağıt azaldı',        time: '12:05 · Bugün' },
  { id: 4, level: 'error',   message: 'Bursa Merkez Kiosk-3 güncelleme başarısız',         time: '10:44 · Bugün' },
  { id: 5, level: 'warning', message: 'Antalya Lara Eczanesi internet yavaş',              time: '09:21 · Bugün' },
  { id: 6, level: 'info',    message: 'Sistem güncellemesi tamamlandı (v2.4.1)',            time: '08:00 · Bugün' },
]


</script>

<template>
  <div class="dash">

    <!-- ── Header ───────────────────────────────────────────── -->
    <header class="dash-header">
      <div>
        <p class="eyebrow">SÜPERADMİN · GENEL BAKIŞ</p>
        <h1 class="page-title">Dashboard</h1>
      </div>
      <div class="header-right">
        <div class="live-badge">
          <span class="pulse-dot"></span> Canlı
        </div>
        <time class="date-chip">{{ currentDate }}</time>
      </div>
    </header>

    <!-- ── KPI Cards ─────────────────────────────────────────── -->
    <div class="kpi-grid">
      <div
        v-for="(kpi, i) in kpiCards"
        :key="kpi.id"
        class="kpi-card"
        :style="{ '--c': kpi.color, animationDelay: (i * 90) + 'ms' }"
      >
        <div class="kpi-accent"></div>
        <div class="kpi-body">
          <div class="kpi-row-top">
            <span class="kpi-label">{{ kpi.label }}</span>
            <span class="kpi-icon" :style="{ color: kpi.color }" v-html="kpi.iconSvg"></span>
          </div>
          <div class="kpi-number-row">
            <span class="kpi-number">{{ displayValues[i] }}</span>
            <span v-if="kpi.outOf" class="kpi-outof">/ {{ kpi.outOf }}</span>
          </div>
          <div v-if="kpi.sub" class="kpi-sub" :class="kpi.subClass">
            {{ kpi.sub }}
          </div>
        </div>
      </div>
    </div>

    <!-- ── Charts ────────────────────────────────────────────── -->
    <div class="charts-grid">

      <!-- Bar Chart -->
      <div class="chart-panel">
        <div class="panel-header">
          <div>
            <p class="panel-eyebrow">HAFTALIK TREND</p>
            <h2 class="panel-title">Kiosk Etkileşimleri</h2>
          </div>
          <span class="panel-badge">{{ totalWeekly.toLocaleString('tr-TR') }} bu hafta</span>
        </div>
        <svg viewBox="0 0 580 200" class="bar-svg" preserveAspectRatio="xMidYMid meet">
          <!-- Grid lines + Y labels -->
          <line v-for="g in yGrid" :key="g.label"
                x1="52" :y1="g.y" x2="558" :y2="g.y" class="svg-grid" />
          <text v-for="g in yGrid" :key="'yl'+g.label"
                x="46" :y="g.y + 4" text-anchor="end" class="svg-y-label">{{ g.label }}</text>
          <!-- X axis -->
          <line x1="52" :y1="CHART_BOTTOM" x2="558" :y2="CHART_BOTTOM" class="svg-axis" />
          <!-- Bars -->
          <g v-for="(d, i) in weeklyData" :key="d.day">
            <rect
              :x="barX(i)"
              :y="barY(d.value)"
              :width="46"
              :height="barH(d.value)"
              rx="5"
              :class="['bar-rect', i === 6 ? 'bar-today' : 'bar-normal']"
              :style="{ animationDelay: (i * 70 + 300) + 'ms' }"
            />
            <text :x="barX(i) + 23" :y="CHART_BOTTOM + 16"
                  text-anchor="middle" class="svg-x-label">{{ d.day }}</text>
            <text :x="barX(i) + 23" :y="barY(d.value) - 5"
                  text-anchor="middle" class="svg-val-label"
                  :class="i === 6 ? 'val-today' : ''">
              {{ (d.value / 1000).toFixed(1) }}k
            </text>
          </g>
        </svg>
      </div>

      <!-- Donut Chart -->
      <div class="chart-panel donut-panel">
        <div class="panel-header">
          <div>
            <p class="panel-eyebrow">KATEGORİ DAĞILIMI</p>
            <h2 class="panel-title">En Çok Kullanılanlar</h2>
          </div>
        </div>
        <div class="donut-body">
          <div class="donut-wrap">
            <svg viewBox="0 0 200 200" class="donut-svg">
              <!-- Segments: outer group rotates -90° to start at 12 o'clock -->
              <g transform="rotate(-90, 100, 100)">
                <circle
                  v-for="(seg, i) in donutSegments"
                  :key="i"
                  cx="100" cy="100" r="70"
                  fill="none"
                  :stroke="seg.color"
                  stroke-width="30"
                  :stroke-dasharray="`${seg.dash.toFixed(2)} ${(CIRC - seg.dash).toFixed(2)}`"
                  stroke-dashoffset="0"
                  :transform="`rotate(${seg.rotate}, 100, 100)`"
                  class="donut-arc"
                  :style="{ animationDelay: (i * 100) + 'ms' }"
                />
              </g>
              <!-- Center label (not rotated) -->
              <text x="100" y="95" text-anchor="middle" class="donut-big">
                {{ totalSessions.toLocaleString('tr-TR') }}
              </text>
              <text x="100" y="111" text-anchor="middle" class="donut-sub">oturum</text>
            </svg>
          </div>
          <div class="donut-legend">
            <div v-for="seg in donutSegments" :key="seg.label" class="dl-row">
              <span class="dl-dot" :style="{ background: seg.color }"></span>
              <span class="dl-name">{{ seg.label }}</span>
              <span class="dl-pct">{{ seg.pct }}%</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Bottom Row ─────────────────────────────────────────── -->
    <div class="bottom-grid">

      <!-- Recent Campaigns table -->
      <div class="data-panel">
        <div class="panel-header">
          <div>
            <p class="panel-eyebrow">SON EKLENENLER</p>
            <h2 class="panel-title">Kampanyalar</h2>
          </div>
          <router-link to="/admin/campaign-manager" class="see-all">Tümünü Gör →</router-link>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Kampanya</th>
              <th>Müşteri</th>
              <th>Kiosk</th>
              <th>Durum</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in recentCampaigns" :key="row.id">
              <td>
                <div class="camp-cell">
                  <span class="camp-dot" :style="{ background: row.color }"></span>
                  {{ row.name }}
                </div>
              </td>
              <td class="td-muted">{{ row.client }}</td>
              <td class="td-muted">{{ row.kiosks }}</td>
              <td>
                <span class="status-pill" :class="row.status">{{ row.statusLabel }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- System Alerts -->
      <div class="data-panel">
        <div class="panel-header">
          <div>
            <p class="panel-eyebrow">SİSTEM</p>
            <h2 class="panel-title">Uyarılar</h2>
          </div>
          <span class="critical-badge">
            {{ alerts.filter(a => a.level === 'error').length }} kritik
          </span>
        </div>
        <div class="alerts-list">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-row"
            :class="alert.level"
          >
            <div class="alert-dot"></div>
            <div class="alert-body">
              <p class="alert-msg">{{ alert.message }}</p>
              <p class="alert-time">{{ alert.time }}</p>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
</style>

<style scoped>
/* ── Root ───────────────────────────────────────────────────── */
.dash {
  --bg:      #F2F1EE;
  --surface: #FFFFFF;
  --border:  #E5E3DF;
  --text:    #111827;
  --muted:   #6B7280;
  --faint:   #F9F8F6;

  background: var(--bg);
  min-height: 100vh;
  padding: 2rem 2.5rem 4rem;
  font-family: 'Plus Jakarta Sans', sans-serif;
  color: var(--text);
  position: relative;
}

/* ── Header ── */
.dash-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
}
.eyebrow {
  font-family: 'Syne', sans-serif;
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: var(--muted);
  margin: 0 0 0.4rem;
  text-transform: uppercase;
}
.page-title {
  font-family: 'Syne', sans-serif;
  font-size: 2rem;
  font-weight: 800;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.03em;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.live-badge {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-family: 'Syne', sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  color: #059669;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  padding: 0.3rem 0.8rem;
  border-radius: 100px;
}
.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #059669;
  animation: pulseGreen 2s ease-in-out infinite;
}
@keyframes pulseGreen {
  0%, 100% { box-shadow: 0 0 0 0 #05996950; }
  50%       { box-shadow: 0 0 0 6px transparent; }
}
.date-chip {
  font-size: 0.78rem;
  color: var(--muted);
}

/* ── KPI Grid ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 14px rgba(0,0,0,0.04);
  animation: slideUp 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(22px); }
  to   { opacity: 1; transform: translateY(0); }
}
.kpi-accent {
  height: 4px;
  background: var(--c);
}
.kpi-body {
  padding: 1.25rem 1.4rem;
}
.kpi-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.kpi-label {
  font-family: 'Syne', sans-serif;
  font-size: 0.7rem;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.kpi-icon { display: flex; }
.kpi-number-row {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  margin-bottom: 0.3rem;
}
.kpi-number {
  font-family: 'Syne', sans-serif;
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.04em;
  line-height: 1;
}
.kpi-outof {
  font-size: 0.85rem;
  color: var(--muted);
  font-weight: 500;
}
.kpi-sub {
  font-size: 0.72rem;
  font-weight: 500;
  margin-top: 0.1rem;
}
.danger-sub  { color: #EF4444; }
.success-sub { color: #059669; }

/* ── Charts Grid ── */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
.chart-panel {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 14px rgba(0,0,0,0.04);
}
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}
.panel-eyebrow {
  font-family: 'Syne', sans-serif;
  font-size: 0.6rem;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin: 0 0 0.25rem;
}
.panel-title {
  font-family: 'Syne', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}
.panel-badge {
  font-size: 0.72rem;
  color: var(--muted);
  background: var(--faint);
  border: 1px solid var(--border);
  padding: 0.28rem 0.75rem;
  border-radius: 100px;
  white-space: nowrap;
  font-family: 'Syne', sans-serif;
  font-weight: 600;
}

/* Bar SVG */
.bar-svg {
  width: 100%;
  height: auto;
  overflow: visible;
  display: block;
}
.svg-grid  { stroke: #EEE; stroke-width: 1; }
.svg-axis  { stroke: #D1D5DB; stroke-width: 1.5; }
.svg-y-label {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 9px;
  fill: #9CA3AF;
}
.svg-x-label {
  font-family: 'Syne', sans-serif;
  font-size: 10px;
  fill: #9CA3AF;
  font-weight: 600;
}
.svg-val-label {
  font-family: 'Syne', sans-serif;
  font-size: 9px;
  fill: #9CA3AF;
  font-weight: 600;
}
.val-today { fill: #2563EB; }

.bar-rect {
  transform-box: fill-box;
  transform-origin: bottom;
  animation: barGrow 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes barGrow {
  from { transform: scaleY(0); }
  to   { transform: scaleY(1); }
}
.bar-normal { fill: #DBEAFE; }
.bar-today  { fill: #2563EB; }

/* Donut */
.donut-panel {}
.donut-body {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.donut-wrap { flex-shrink: 0; }
.donut-svg  { width: 160px; height: 160px; display: block; }

.donut-arc {
  opacity: 0;
  animation: fadeIn 0.45s ease forwards;
}
@keyframes fadeIn {
  to { opacity: 1; }
}

.donut-big {
  font-family: 'Syne', sans-serif;
  font-size: 17px;
  font-weight: 800;
  fill: #111827;
}
.donut-sub {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 8px;
  fill: #9CA3AF;
}
.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.dl-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
}
.dl-dot {
  width: 10px; height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.dl-name {
  flex: 1;
  color: var(--text);
  font-weight: 500;
}
.dl-pct {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 0.75rem;
  color: var(--muted);
}

/* ── Bottom Grid ── */
.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}
.data-panel {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 14px rgba(0,0,0,0.04);
}
.see-all {
  font-size: 0.75rem;
  color: #2563EB;
  text-decoration: none;
  font-weight: 600;
  font-family: 'Syne', sans-serif;
  white-space: nowrap;
}
.see-all:hover { text-decoration: underline; }

/* Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}
.data-table th {
  text-align: left;
  font-family: 'Syne', sans-serif;
  font-size: 0.65rem;
  letter-spacing: 0.08em;
  color: var(--muted);
  padding: 0 0 0.6rem;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  text-transform: uppercase;
}
.data-table td {
  padding: 0.7rem 0.5rem 0.7rem 0;
  border-bottom: 1px solid #F3F4F6;
  vertical-align: middle;
}
.data-table tr:last-child td { border-bottom: none; }
.td-muted { color: var(--muted); font-size: 0.78rem; }

.camp-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: var(--text);
}
.camp-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-pill {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 100px;
  font-size: 0.68rem;
  font-weight: 700;
  font-family: 'Syne', sans-serif;
  letter-spacing: 0.03em;
}
.status-pill.active    { background: #ECFDF5; color: #059669; }
.status-pill.scheduled { background: #EFF6FF; color: #2563EB; }
.status-pill.ended     { background: #F3F4F6; color: #6B7280; }

/* Alerts */
.critical-badge {
  font-family: 'Syne', sans-serif;
  font-size: 0.68rem;
  font-weight: 700;
  color: #EF4444;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  padding: 0.22rem 0.65rem;
  border-radius: 100px;
}
.alerts-list {
  display: flex;
  flex-direction: column;
}
.alert-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.8rem 0;
  border-bottom: 1px solid #F3F4F6;
}
.alert-row:last-child { border-bottom: none; }
.alert-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}
.alert-row.error   .alert-dot { background: #EF4444; box-shadow: 0 0 6px #EF444460; }
.alert-row.warning .alert-dot { background: #F59E0B; box-shadow: 0 0 6px #F59E0B60; }
.alert-row.info    .alert-dot { background: #3B82F6; }
.alert-msg {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text);
  margin: 0 0 0.15rem;
  line-height: 1.45;
}
.alert-time {
  font-size: 0.68rem;
  color: var(--muted);
  margin: 0;
}

/* ── Responsive ── */
@media (max-width: 1100px) {
  .kpi-grid    { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .bottom-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .dash     { padding: 1rem 1rem 3rem; }
  .kpi-grid { grid-template-columns: 1fr 1fr; }
  .kpi-number { font-size: 1.75rem; }
  .page-title { font-size: 1.5rem; }
}
</style>
