<script setup>
/**
 * Admin Dashboard — Genel Bakış Ekranı.
 * Gerçek veriler: GET /api/analytics/admin-dashboard/
 */
import { ref, computed, onMounted, watch } from 'vue';
import { http } from '../../services/api';
import { getPharmacies, getKioskStatus } from '../../services/devices';
import EisaLookup from '../../components/shared/EisaLookup.vue';

//  Constants 
const CIRC        = 2 * Math.PI * 70
const CHART_BOTTOM = 168
const CHART_H     = 153

//  State 
const loading   = ref(true);
const dashData  = ref(null);

//  KPI display values (count-up animation) 
const kpiValues = ref({ pharmacies: '0', kiosks: '0', activeAds: '0', todayQR: '0' });

function countUp(key, target, duration = 1500) {
  const start = performance.now();
  const tick = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 4);
    kpiValues.value[key] = Math.round(ease * target).toLocaleString('tr-TR');
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

//  Date 
const currentDate = computed(() =>
  new Date().toLocaleDateString('tr-TR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })
);

//  Bar Chart 
const DAY_LABELS = ['Paz', 'Pts', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt'];
const weeklyData = computed(() => {
  const raw = dashData.value?.haftalik_trend ?? [];
  // Fill last 7 days (oldestnewest)
  const map = {};
  raw.forEach(({ tarih, sayi }) => { map[tarih] = sayi; });
  const result = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const dayLabel = DAY_LABELS[d.getDay()];
    result.push({ day: dayLabel, value: map[key] ?? 0, isToday: i === 0 });
  }
  return result;
});

const MAX_BAR = computed(() => Math.max(...weeklyData.value.map((d) => d.value), 1000));
const totalWeekly = computed(() => weeklyData.value.reduce((s, d) => s + d.value, 0));

function barH(val) { return (val / MAX_BAR.value) * CHART_H; }
function barY(val) { return CHART_BOTTOM - barH(val); }
function barX(i)   { return 66 + i * 74; }

const yGrid = computed(() => {
  const max = MAX_BAR.value;
  const step = Math.ceil(max / 4 / 1000) * 1000 || 1000;
  return [1, 2, 3, 4].map((n) => ({
    label: `${(n * step / 1000).toFixed(0)}k`,
    y: CHART_BOTTOM - (n * step / max) * CHART_H,
  }));
});

//  Donut Chart 
const DONUT_COLORS = ['#2563EB', '#7C3AED', '#DB2777', '#059669', '#F59E0B', '#0891B2'];

const donutSegments = computed(() => {
  const cats = dashData.value?.kategori_dagilim ?? [];
  if (!cats.length) return [];
  const total = cats.reduce((s, c) => s + c.sayi, 0) || 1;
  let cum = 0;
  return cats.slice(0, 5).map((cat, i) => {
    const pct = Math.round((cat.sayi / total) * 100);
    const dash = (pct / 100) * CIRC;
    const rotate = (cum / total) * 360;
    cum += cat.sayi;
    return { label: cat.ad, pct, dash, rotate, color: DONUT_COLORS[i] };
  });
});

const totalSessions = computed(() => {
  const cats = dashData.value?.kategori_dagilim ?? [];
  return cats.reduce((s, c) => s + c.sayi, 0);
});

//  Recent Ads 
const AD_COLORS = ['#22d3ee', '#f59e0b', '#a78bfa', '#34d399', '#fb7185'];

const recentAds = computed(() =>
  (dashData.value?.son_reklamlar ?? []).map((r, i) => ({
    id: r.id,
    name: r.ad,
    client: r.musteri || '—',
    color: AD_COLORS[i % AD_COLORS.length],
    status: adStatus(r),
    statusLabel: adStatusLabel(r),
  }))
);

function adStatus(r) {
  const now = Date.now();
  const start = new Date(r.baslangic_tarihi).getTime();
  const end   = new Date(r.bitis_tarihi).getTime();
  if (now < start) return 'scheduled';
  if (now > end)   return 'ended';
  return 'active';
}
function adStatusLabel(r) {
  const s = adStatus(r);
  return s === 'active' ? 'Yayında' : s === 'scheduled' ? 'Planlandı' : 'Bitti';
}

//  KPI Cards definition 
const kpiCards = [
  {
    id: 'pharmacies',
    label: 'Toplam Eczane',
    valueKey: 'pharmacies',
    color: '#2563EB',
    icon: 'fa-house-medical',
  },
  {
    id: 'kiosks',
    label: 'Aktif Kiosk',
    valueKey: 'kiosks',
    color: '#059669',
    icon: 'fa-display',
    subFn: () => dashData.value ? `${dashData.value.cevrimdisi_kiosk} Cihaz Çevrimdışı` : '',
    subClass: 'dash-kpi-sub--danger',
  },
  {
    id: 'ads',
    label: 'Yayındaki Reklam',
    valueKey: 'activeAds',
    color: '#7C3AED',
    icon: 'fa-bullhorn',
  },
  {
    id: 'qr',
    label: 'Bugün Üretilen QR',
    valueKey: 'todayQR',
    color: '#D97706',
    icon: 'fa-qrcode',
  },
];

//  Pharmacy Filter + Kiosk List 
const pharmacies      = ref([]);
const selectedPharmacy = ref(null);
const filteredKiosks  = ref([]);
const kiosksLoading   = ref(false);

const pharmacyOptions = computed(() =>
  pharmacies.value.map((p) => ({
    id: p.id,
    label: p.name,
    sub: `${p.ilAdi || ''}${p.ilceAdi ? ' / ' + p.ilceAdi : ''}`,
  }))
);

watch(selectedPharmacy, async (val) => {
  filteredKiosks.value = [];
  if (!val) return;
  kiosksLoading.value = true;
  try { filteredKiosks.value = await getKioskStatus(val); }
  catch { /* ignore */ }
  finally { kiosksLoading.value = false; }
});

async function loadPharmacies() {
  try { pharmacies.value = await getPharmacies(); } catch { /* ignore */ }
}

//  Data Loading 
onMounted(async () => {
  try {
    const { data } = await http.get('/api/analytics/admin-dashboard/');
    dashData.value = data;
    // Trigger count-up animations
    setTimeout(() => countUp('pharmacies', data.toplam_eczane ?? 0), 0);
    setTimeout(() => countUp('kiosks',     data.aktif_kiosk  ?? 0), 160);
    setTimeout(() => countUp('activeAds',  data.aktif_reklam ?? 0), 320);
    setTimeout(() => countUp('todayQR',    data.bugunki_oturum ?? 0), 480);
  } catch {
    // errors handled by api interceptor toast
  } finally {
    loading.value = false;
  }
  await loadPharmacies();
});
</script>

<template>
  <div class="eisa-page">

    <!--  Header  -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">SÜPERADMİN — GENEL BAKIŞ</p>
        <h1 class="eisa-page-title">Dashboard</h1>
      </div>
      <div class="eisa-header-actions">
        <div class="dash-live-badge">
          <span class="dash-pulse-dot"></span> Canlı
        </div>
          <time class="dash-date-chip">{{ currentDate }}</time>
      </div>
    </div>  <!-- eisa-page-header -->

    <!--  KPI Cards  -->
    <div class="dash-kpi-grid">
      <div
        v-for="(kpi, i) in kpiCards"
        :key="kpi.id"
        class="dash-kpi-card"
        :style="{ '--kpi-c': kpi.color, animationDelay: (i * 90) + 'ms' }"
      >
        <div class="dash-kpi-accent"></div>
        <div class="dash-kpi-body">
          <div class="dash-kpi-top">
            <span class="dash-kpi-label">{{ kpi.label }}</span>
            <span class="dash-kpi-icon" :style="{ color: kpi.color }">
              <i class="fa-solid" :class="kpi.icon"></i>
            </span>
          </div>
          <div class="dash-kpi-number">{{ loading ? '…' : kpiValues[kpi.valueKey] }}</div>
          <div v-if="kpi.subFn" class="dash-kpi-sub" :class="kpi.subClass">
            {{ kpi.subFn() }}
          </div>
        </div>
      </div>
    </div>

    <!--  Charts  -->
    <div class="dash-charts-grid">

      <!-- Bar Chart -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">HAFTALIK TREND</p>
            <h2 class="eisa-panel-title">Kiosk Etkileşimleri</h2>
          </div>
          <span class="dash-panel-badge">{{ totalWeekly.toLocaleString('tr-TR') }} bu hafta</span>
        </div>
        <div style="padding:0 1.25rem 1.25rem;">
          <svg viewBox="0 0 580 200" class="dash-bar-svg" preserveAspectRatio="xMidYMid meet">
            <!-- Grid lines + Y labels -->
            <line v-for="g in yGrid" :key="g.label"
                  x1="52" :y1="g.y" x2="558" :y2="g.y" class="dash-svg-grid" />
            <text v-for="g in yGrid" :key="'yl'+g.label"
                  x="46" :y="g.y + 4" text-anchor="end" class="dash-svg-y-label">{{ g.label }}</text>
            <!-- X axis -->
            <line x1="52" :y1="CHART_BOTTOM" x2="558" :y2="CHART_BOTTOM" class="dash-svg-axis" />
            <!-- Bars -->
            <g v-for="(d, i) in weeklyData" :key="d.day">
              <rect
                :x="barX(i)"
                :y="barY(d.value)"
                :width="46"
                :height="barH(d.value)"
                rx="5"
                :class="['dash-bar-rect', d.isToday ? 'dash-bar--today' : 'dash-bar--normal']"
                :style="{ animationDelay: (i * 70 + 300) + 'ms' }"
              />
              <text :x="barX(i) + 23" :y="CHART_BOTTOM + 16"
                    text-anchor="middle" class="dash-svg-x-label">{{ d.day }}</text>
              <text :x="barX(i) + 23" :y="barY(d.value) - 5"
                    text-anchor="middle" class="dash-svg-val-label"
                    :class="d.isToday ? 'dash-val--today' : ''">
                {{ d.value > 999 ? (d.value / 1000).toFixed(1) + 'k' : d.value }}
              </text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Donut Chart -->
      <div class="eisa-panel dash-donut-panel">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">KATEGORİ DAĞILIMI</p>
            <h2 class="eisa-panel-title">En Çok Kullananlar</h2>
          </div>
        </div>
        <div class="dash-donut-body">
          <div class="dash-donut-wrap">
            <svg viewBox="0 0 200 200" class="dash-donut-svg">
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
                  class="dash-donut-arc"
                  :style="{ animationDelay: (i * 100) + 'ms' }"
                />
              </g>
              <text x="100" y="95" text-anchor="middle" class="dash-donut-big">
                {{ totalSessions > 999 ? (totalSessions/1000).toFixed(1)+'k' : totalSessions }}
              </text>
              <text x="100" y="111" text-anchor="middle" class="dash-donut-sub">oturum</text>
            </svg>
          </div>
          <div class="dash-donut-legend">
            <div v-for="seg in donutSegments" :key="seg.label" class="dash-dl-row">
              <span class="dash-dl-dot" :style="{ background: seg.color }"></span>
              <span class="dash-dl-name">{{ seg.label }}</span>
              <span class="dash-dl-pct">{{ seg.pct }}%</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Alt Satır -->
    <div class="dash-bottom-grid">

      <!-- Son Reklamlar -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">SON EKLENENLER</p>
            <h2 class="eisa-panel-title">Reklamlar</h2>
          </div>
          <router-link to="/admin/campaigns" class="dash-see-all">Tümünü Gör →</router-link>
        </div>
        <div class="eisa-table-wrap">
          <div v-if="loading" class="empty-row">Yükleniyor…</div>
          <div v-else-if="!recentAds.length" class="empty-row">Henüz reklam yok.</div>
          <table v-else class="eisa-table">
            <thead>
              <tr>
                <th>Reklam Adı</th>
                <th>Müşteri</th>
                <th>Durum</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in recentAds" :key="row.id">
                <td>
                  <div class="dash-camp-cell">
                    <span class="dash-camp-dot" :style="{ background: row.color }"></span>
                    {{ row.name }}
                  </div>
                </td>
                <td class="cell-muted">{{ row.client }}</td>
                <td>
                  <span
                    class="eisa-pill"
                    :class="row.status === 'active' ? 'eisa-pill-success' : row.status === 'scheduled' ? 'eisa-pill-info' : 'eisa-pill-muted'"
                  >{{ row.statusLabel }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Kiosk Özeti -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">SİSTEM DURUMU</p>
            <h2 class="eisa-panel-title">Kiosk Özeti</h2>
          </div>
          <span v-if="dashData" class="eisa-pill eisa-pill-danger">
            {{ dashData.cevrimdisi_kiosk }} Çevrimdışı
          </span>
        </div>
        <div v-if="loading" class="empty-row">Yükleniyor…</div>
        <div v-else-if="dashData" class="dash-alerts-list">
          <div class="dash-alert-row dash-alert--info">
            <div class="dash-alert-dot"></div>
            <div class="dash-alert-body">
              <p class="dash-alert-msg">Toplam eczane: {{ dashData.toplam_eczane }}</p>
              <p class="dash-alert-time">Aktif kayıtlar</p>
            </div>
          </div>
          <div class="dash-alert-row"
               :class="dashData.cevrimdisi_kiosk > 0 ? 'dash-alert--error' : 'dash-alert--info'">
            <div class="dash-alert-dot"></div>
            <div class="dash-alert-body">
              <p class="dash-alert-msg">Çevrimiçi kiosk: {{ dashData.aktif_kiosk }} / {{ dashData.toplam_kiosk }}</p>
              <p class="dash-alert-time">Son 15 dakika içinde aktif</p>
            </div>
          </div>
          <div class="dash-alert-row dash-alert--info">
            <div class="dash-alert-dot"></div>
            <div class="dash-alert-body">
              <p class="dash-alert-msg">Bugünkü oturum: {{ dashData.bugunki_oturum.toLocaleString('tr-TR') }}</p>
              <p class="dash-alert-time">Güncel sayaç</p>
            </div>
          </div>
        </div>
      </div>

    </div>
    <!-- /dash-bottom-grid -->

    <!-- Eczane Kiosk Filtresi -->
    <div class="eisa-panel" style="margin-top:1.5rem;">
      <div class="eisa-panel-header">
        <div>
          <p class="eisa-eyebrow" style="font-size:0.65rem;">ECZANE FİLTRESİ</p>
          <h2 class="eisa-panel-title">Eczane Kiosklarını Görüntüle</h2>
        </div>
      </div>
      <div style="padding:0 1.25rem 0.75rem; max-width:360px;">
        <EisaLookup
          v-model="selectedPharmacy"
          :options="pharmacyOptions"
          placeholder="Eczane ara (ad / il / ilçe)…"
        />
      </div>
      <div v-if="kiosksLoading" class="empty-row">Yükleniyor…</div>
      <div v-else-if="selectedPharmacy && !filteredKiosks.length" class="empty-row">
        Bu eczaneye ait kiosk bulunamadı.
      </div>
      <div v-else-if="filteredKiosks.length" class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr><th>Kiosk</th><th>MAC</th><th>Durum</th><th>Son Görülme</th></tr>
          </thead>
          <tbody>
            <tr v-for="k in filteredKiosks" :key="k.id">
              <td>{{ k.ad || `#${k.id}` }}</td>
              <td class="cell-muted">{{ k.mac || '—' }}</td>
              <td>
                <span class="eisa-pill" :class="k.isActive ? 'eisa-pill-success' : 'eisa-pill-danger'">
                  {{ k.isActive ? 'Aktif' : 'Pasif' }}
                </span>
              </td>
              <td class="cell-muted">
                {{ k.lastPing ? new Date(k.lastPing).toLocaleString('tr-TR') : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-row" style="color:#94a3b8;">Eczane seçin</div>
    </div>

  </div>

</template>
