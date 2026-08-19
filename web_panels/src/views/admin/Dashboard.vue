<script setup>
/**
 * Admin Dashboard — Genel Bakış Ekranı.
 * Gerçek veriler: GET /api/analytics/admin-dashboard/
 */
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { http } from '../../services/api';
import { listProvisioningRequests } from '../../services/devices';
import EczanePicker from '../../components/shared/EczanePicker.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import { usePharmacyLookups } from '../../composables/usePharmacyLookups.js';
import DashboardPeriodCharts from '../../components/DashboardPeriodCharts.vue';
import DashboardAsyncDonut from '../../components/DashboardAsyncDonut.vue';

const router = useRouter();

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
    color: '#B1121B',
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
    drillTo: '/admin/kiosk-activities',
  },
  {
    id: 'ads',
    label: 'Yayındaki İlan',
    valueKey: 'activeAds',
    color: '#7C3AED',
    icon: 'fa-bullhorn',
    drillTo: '/admin/kiosk-activities',
    drillQuery: { tab: 'impressions' },
  },
  {
    id: 'qr',
    label: 'Bugünkü Etkileşim',
    valueKey: 'todayQR',
    color: '#D97706',
    icon: 'fa-qrcode',
    drillTo: '/admin/kiosk-activities',
    drillQuery: { tab: 'sessions', start_date: new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(new Date()) },
  },
];

//  Pending Devices 
const pendingCount = ref(0);

async function loadPendingCount() {
  try {
    const list = await listProvisioningRequests({ status: 'PENDING' });
    pendingCount.value = list.length;
  } catch { /* ignore */ }
}

//  Analytics pharmacy filter 
const provinces = ref([]);
const selectedProvince = ref(null);
const selectedPharmacy = ref(null);
const { pharmacies, ensureLoaded: ensurePharmaciesLoaded } = usePharmacyLookups();
const provinceOptions = computed(() => {
  const availableProvinceIds = new Set(pharmacies.value.map((pharmacy) => String(pharmacy.il)));
  return provinces.value.filter((province) => availableProvinceIds.has(String(province.id)));
});
const analyticsFilters = computed(() => ({
  ...(selectedProvince.value ? { il_id: selectedProvince.value } : {}),
  ...(selectedPharmacy.value ? { eczane_id: selectedPharmacy.value } : {}),
}));

watch(selectedProvince, () => {
  selectedPharmacy.value = null;
});

async function loadProvinces() {
  await ensurePharmaciesLoaded();
  provinces.value = [...new Map(
    pharmacies.value
      .filter((pharmacy) => pharmacy.il && pharmacy.ilAdi)
      .map((pharmacy) => [String(pharmacy.il), { id: pharmacy.il, label: pharmacy.ilAdi }])
  ).values()];
}

//  Data Loading 
let dashboardRequestId = 0;
async function loadDashboard() {
  const requestId = ++dashboardRequestId;
  loading.value = true;
  try {
    const { data } = await http.get('/api/analytics/admin-dashboard/', { params: analyticsFilters.value });
    if (requestId !== dashboardRequestId) return;
    dashData.value = data;
    // Trigger count-up animations
    setTimeout(() => countUp('pharmacies', data.toplam_eczane ?? 0), 0);
    setTimeout(() => countUp('kiosks',     data.aktif_kiosk  ?? 0), 160);
    setTimeout(() => countUp('activeAds',  data.aktif_reklam ?? 0), 320);
    setTimeout(() => countUp('todayQR',    data.bugunki_oturum ?? 0), 480);
  } catch {
    // errors handled by api interceptor toast
  } finally {
    if (requestId === dashboardRequestId) loading.value = false;
  }
}

watch(analyticsFilters, loadDashboard, { immediate: true });

onMounted(async () => {
  await loadProvinces();
  loadPendingCount();
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

    <section class="eisa-panel dash-analytics-filter">
      <div class="dash-analytics-filter-label"><i class="fa-solid fa-filter"></i><span>Analitik Filtresi</span></div>
      <div class="dash-analytics-filter-fields">
        <EisaLookup v-model="selectedProvince" :options="provinceOptions" placeholder="İl seçin…" :clearable="true" />
        <EczanePicker v-model="selectedPharmacy" :province-id="selectedProvince" placeholder="İl / İlçe / Eczane ara…" />
      </div>
    </section>

    <!--  Pending Devices Alert  -->
    <div v-if="pendingCount > 0" class="dash-pending-alert">
      <i class="fa-solid fa-clock dash-pending-icon"></i>
      <span><strong>{{ pendingCount }}</strong> cihaz yönetici onayı bekliyor</span>
      <router-link to="/admin/devices" class="dash-pending-link">Görüntüle →</router-link>
    </div>

    <div class="dash-kpi-grid">
      <div
        v-for="(kpi, i) in kpiCards"
        :key="kpi.id"
        class="dash-kpi-card"
        :class="{ 'dash-kpi-card--clickable': !!kpi.drillTo }"
        :style="{ '--kpi-c': kpi.color, animationDelay: (i * 90) + 'ms' }"
        @click="kpi.drillTo && router.push({ path: kpi.drillTo, query: kpi.drillQuery })"
      >
        <div class="dash-kpi-accent"></div>
        <div class="dash-kpi-body">
          <div class="dash-kpi-top">
            <span class="dash-kpi-label">{{ kpi.label }}</span>
            <span class="dash-kpi-icon" :style="{ color: kpi.color }"><i class="fa-solid" :class="kpi.icon"></i></span>
          </div>
          <div class="dash-kpi-number">{{ loading ? '…' : kpiValues[kpi.valueKey] }}</div>
          <div v-if="kpi.subFn" class="dash-kpi-sub" :class="kpi.subClass">{{ kpi.subFn() }}</div>
        </div>
      </div>
    </div>

    <div class="dash-donut-grid">
      <DashboardAsyncDonut kind="categories" eyebrow="KATEGORİ DAĞILIMI" title="Kategori Dağılımı" :filters="analyticsFilters" />
      <DashboardAsyncDonut kind="pharmacies" eyebrow="SATIŞ ECZANE DAĞILIMI" title="Satış Eczane Dağılımı" :filters="analyticsFilters" />
      <DashboardAsyncDonut kind="ingredients" eyebrow="SATILAN ETKEN MADDE" title="Satılan Etken Madde Dağılımı" :filters="analyticsFilters" />
      <DashboardAsyncDonut kind="recommended-ingredients" eyebrow="ÖNERİLEN ETKEN MADDE" title="Önerilen Etken Madde Dağılımı" :filters="analyticsFilters" />
    </div>

    <DashboardPeriodCharts :filters="analyticsFilters">
      <template #aside>
        <div class="dash-bottom-grid dash-bottom-grid--stacked">

      <!-- Son Reklamlar -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">SON EKLENENLER</p>
            <h2 class="eisa-panel-title">İlanlar</h2>
          </div>
          <router-link to="/admin/campaigns" class="dash-see-all">Tümünü Gör →</router-link>
        </div>
        <div class="eisa-table-wrap">
          <div v-if="loading" class="empty-row">Yükleniyor…</div>
          <div v-else-if="!recentAds.length" class="empty-row">Henüz ilan yok.</div>
          <table v-else class="eisa-table">
            <thead>
              <tr>
                <th>İlan Adı</th>
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
      </template>
    </DashboardPeriodCharts>

  </div>

</template>

<style scoped>
.dash-donut-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.dash-bottom-grid--stacked { grid-template-columns: 1fr; gap: 1rem; margin: 0; }
.dash-analytics-filter { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .75rem 1rem; margin-bottom: 1.25rem; }
.dash-analytics-filter-label { display: inline-flex; align-items: center; gap: .5rem; color: #475569; font-size: .78rem; font-weight: 800; white-space: nowrap; }
.dash-analytics-filter-label i { color: var(--eisa-red); }
.dash-analytics-filter-fields { display: grid; grid-template-columns: repeat(2, minmax(220px, 280px)); gap: .65rem; width: min(100%, 580px); }
.dash-kpi-card--clickable {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.dash-kpi-card--clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(0,0,0,0.18);
}
.dash-pending-alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #fefce8;
  border: 1px solid #fde047;
  border-left: 4px solid #f59e0b;
  border-radius: 8px;
  padding: 0.75rem 1.1rem;
  margin-bottom: 1.25rem;
  font-size: 0.9rem;
  color: #78350f;
}
.dash-pending-icon { font-size: 1rem; color: #f59e0b; flex-shrink: 0; }
.dash-pending-link {
  margin-left: auto;
  font-weight: 600;
  color: #b45309;
  text-decoration: none;
  white-space: nowrap;
}
.dash-pending-link:hover { text-decoration: underline; }
.dash-donut-arc { cursor: pointer; }
.dash-dl-button {
  width: 100%;
  padding: 0.15rem 0;
  border: 0;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: 5px;
}
.dash-dl-button:hover,
.dash-dl-button:focus-visible { background: var(--eisa-info-soft, #eef2ff); outline: none; }
.dash-donut-empty { margin: 0; font-size: 0.72rem; color: #9ca3af; }
@media (max-width: 1180px) { .dash-donut-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) {
  .dash-donut-grid { grid-template-columns: 1fr; }
  .dash-analytics-filter { align-items: stretch; flex-direction: column; }
  .dash-analytics-filter-fields { grid-template-columns: 1fr; width: 100%; }
}
</style>
