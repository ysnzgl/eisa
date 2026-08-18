<script setup>
/**
 * Eczacı Ana Sayfa — Kendine ait kiosklar, kategoriler, oturum ve kampanya
 * sayılar + kiosk health durumları.
 *
 * Endpoint: GET /api/pharmacies/me/dashboard/
 */
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { http } from '../../services/api';
import DashboardPeriodCharts from '../../components/DashboardPeriodCharts.vue';

const data    = ref(null);
const loading = ref(true);
const error   = ref('');
const router  = useRouter();
let refreshTimer = null;

// KPI count-up animated values
const kpiValues = ref({ kiosks: '0', categories: '0', sessions: '0', todaySessions: '0', ads: '0' });

function countUp(key, target, duration = 1500) {
  const start = performance.now();
  const tick  = (now) => {
    const t    = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 4);
    kpiValues.value[key] = Math.round(ease * target).toLocaleString('tr-TR');
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// Satış filtresi state
const soldStartDate = ref('');
const soldEndDate   = ref('');
const soldLoading   = ref(false);
const soldData      = ref(null);

async function loadSoldStats() {
  soldLoading.value = true;
  try {
    const params = {};
    if (soldStartDate.value) params.start_date = soldStartDate.value;
    if (soldEndDate.value)   params.end_date   = soldEndDate.value;
    const res = await http.get('/api/pharmacies/me/dashboard/', { params });
    soldData.value = res.data;
  } catch { /* toast by interceptor */ }
  finally { soldLoading.value = false; }
}

watch([soldStartDate, soldEndDate], () => loadSoldStats());

async function load() {
  try {
    const res = await http.get('/api/pharmacies/me/dashboard/');
    data.value  = res.data;
    soldData.value = res.data;
    error.value = '';
    // Trigger count-up animations
    setTimeout(() => countUp('kiosks',        res.data.kiosk_sayisi        ?? 0),   0);
    setTimeout(() => countUp('categories',    res.data.kategori_sayisi     ?? 0), 120);
    setTimeout(() => countUp('sessions',      res.data.oturum_sayisi       ?? 0), 240);
    setTimeout(() => countUp('todaySessions', res.data.oturum_sayisi_bugun ?? 0), 360);
    setTimeout(() => countUp('ads',           res.data.reklam_sayisi       ?? 0), 480);
  } catch (e) {
    error.value = 'Veriler yüklenemedi. Bağlantınızı kontrol edin.';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  refreshTimer = setInterval(load, 30_000);
});
onUnmounted(() => clearInterval(refreshTimer));

const kiosks      = computed(() => data.value?.kiosklar ?? []);
const onlineCount = computed(() => kiosks.value.filter((k) => k.durum === 'online').length);
const offlineCount= computed(() => kiosks.value.filter((k) => k.durum === 'offline').length);

const kpiCards = computed(() => [
  {
    id: 'kiosks',
    label: 'Kiosk Sayısı',
    valueKey: 'kiosks',
    color: '#0D9488',
    icon: 'fa-display',
    sub: () => data.value ? `${onlineCount.value} Çevrimiçi — ${offlineCount.value} Çevrimdışı` : '',
    subClass: offlineCount.value > 0 ? 'dash-kpi-sub--danger' : '',
    drillTo: '/pharmacist/kiosk-activities',
  },
  {
    id: 'categories',
    label: 'Aktif Kategori',
    valueKey: 'categories',
    color: '#7C3AED',
    icon: 'fa-tags',
  },
  {
    id: 'sessions',
    label: 'Toplam İşlem',
    valueKey: 'sessions',
    color: '#2563EB',
    icon: 'fa-arrow-right-arrow-left',
    sub: () => data.value ? `Bugün: ${data.value.oturum_sayisi_bugun}` : '',
    drillTo: '/pharmacist/kiosk-activities',
  },
  {
    id: 'todaySessions',
    label: 'Bugünkü İşlem',
    valueKey: 'todaySessions',
    color: '#D97706',
    icon: 'fa-calendar-day',
  },
  {
    id: 'ads',
    label: 'Yayındaki Kampanya',
    valueKey: 'ads',
    color: '#DB2777',
    icon: 'fa-bullhorn',
  },
]);

function fmtRel(iso) {
  if (!iso) return 'Hiç bağlanmadı';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)    return `${diff} sn önce`;
  if (diff < 3600)  return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  return `${Math.floor(diff / 86400)} gün önce`;
}

const HEALTH_LABEL = {
  online:   { text: 'Çevrimiçi' },
  degraded: { text: 'Yavaş' },
  offline:  { text: 'Çevrimdışı' },
};
</script>

<template>
  <div class="eisa-page pharm-page">

    <!-- Page Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">ECZACI / ANA SAYFA</p>
        <h1 class="eisa-page-title">
          {{ data?.eczane?.ad ?? 'Kontrol Paneli' }}
        </h1>
        <p v-if="data?.eczane" class="eisa-page-subtitle">
          {{ data.eczane.ilce }} / {{ data.eczane.il }}
        </p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn eisa-btn-ghost" @click="load">
          <i class="fa-solid fa-rotate-right"></i>
          Yenile
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" style="padding:3rem;text-align:center;color:#6B7280;">
      <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="eisa-error-banner" style="margin-bottom:1.5rem;">
      <i class="fa-solid fa-triangle-exclamation"></i>
      {{ error }}
    </div>

    <template v-else-if="data">
      <!-- Warning -->
      <div v-if="data.uyari" class="eisa-error-banner" style="margin-bottom:1.5rem;background:rgba(245,158,11,0.08);border-color:rgba(245,158,11,0.3);color:#92400E;">
        <i class="fa-solid fa-triangle-exclamation"></i>
        {{ data.uyari }}
      </div>

      <!-- KPI Cards — same structure as admin dashboard -->
      <div class="dash-kpi-grid" style="grid-template-columns:repeat(5,1fr);">
        <div
          v-for="(kpi, i) in kpiCards"
          :key="kpi.id"
          class="dash-kpi-card"
          :class="{ 'dash-kpi-card--clickable': !!kpi.drillTo }"
          :style="{ '--kpi-c': kpi.color, animationDelay: (i * 90) + 'ms', cursor: kpi.drillTo ? 'pointer' : 'default' }"
          @click="kpi.drillTo && router.push({ path: kpi.drillTo, query: kpi.drillQuery })"
        >
          <div class="dash-kpi-accent"></div>
          <div class="dash-kpi-body">
            <div class="dash-kpi-top">
              <span class="dash-kpi-label">{{ kpi.label }}</span>
              <span class="dash-kpi-icon" :style="{ color: kpi.color }">
                <i class="fa-solid" :class="kpi.icon"></i>
              </span>
            </div>
            <div class="dash-kpi-number">{{ kpiValues[kpi.valueKey] }}</div>
            <div v-if="kpi.sub" class="dash-kpi-sub" :class="kpi.subClass">
              {{ kpi.sub() }}
            </div>
          </div>
        </div>
      </div>

      <!-- Satış İstatistikleri -->
      <div class="eisa-panel" style="margin-bottom:1.5rem;">
        <div class="eisa-panel-header">
          <div>
            <p class="eisa-eyebrow" style="font-size:0.65rem;">SATIŞ ANALİTİĞİ</p>
            <h2 class="eisa-panel-title">Satış Özeti</h2>
          </div>
          <div style="display:flex;gap:0.5rem;align-items:center;">
            <div>
              <label class="eisa-label" style="font-size:0.7rem;">Başlangıç</label>
              <input v-model="soldStartDate" type="date" class="eisa-field" style="font-size:0.8rem;padding:0.3rem 0.5rem;" />
            </div>
            <div>
              <label class="eisa-label" style="font-size:0.7rem;">Bitiş</label>
              <input v-model="soldEndDate" type="date" class="eisa-field" style="font-size:0.8rem;padding:0.3rem 0.5rem;" />
            </div>
          </div>
        </div>
        <div style="padding:1rem 1.25rem;display:flex;flex-wrap:wrap;gap:1rem;">
          <div class="dash-kpi-card" style="--kpi-c:#10B981;flex:1;min-width:200px;">
            <div class="dash-kpi-accent"></div>
            <div class="dash-kpi-body">
              <div class="dash-kpi-top">
                <span class="dash-kpi-label">Satış Sayısı</span>
                <span class="dash-kpi-icon" style="color:#10B981;"><i class="fa-solid fa-cart-shopping"></i></span>
              </div>
              <div class="dash-kpi-number">
                <span v-if="soldLoading"><i class="fa-solid fa-circle-notch fa-spin"></i></span>
                <span v-else>{{ (soldData?.satis_sayisi ?? 0).toLocaleString('tr-TR') }}</span>
              </div>
              <div class="dash-kpi-sub">
                <router-link
                  :to="{ path: '/pharmacist/kiosk-activities', query: { tab: 'sessions', sold: 'true', ...(soldStartDate ? { start_date: soldStartDate } : {}), ...(soldEndDate ? { end_date: soldEndDate } : {}) } }"
                  style="color:inherit;text-decoration:none;opacity:0.8;font-size:0.75rem;"
                >Satış listesini gör →</router-link>
              </div>
            </div>
          </div>
          <div class="dash-kpi-card" style="--kpi-c:#0891B2;flex:1;min-width:200px;">
            <div class="dash-kpi-accent"></div>
            <div class="dash-kpi-body">
              <div class="dash-kpi-top">
                <span class="dash-kpi-label">En Çok Satılan Etken Madde</span>
                <span class="dash-kpi-icon" style="color:#0891B2;"><i class="fa-solid fa-flask"></i></span>
              </div>
              <div v-if="soldLoading" class="dash-kpi-number"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
              <template v-else-if="soldData?.en_cok_satilan_etken_madde">
                <div class="dash-kpi-number" style="font-size:1.1rem;word-break:break-word;">
                  {{ soldData.en_cok_satilan_etken_madde.ad }}
                </div>
                <div class="dash-kpi-sub">{{ soldData.en_cok_satilan_etken_madde.sayi }} satış</div>
              </template>
              <div v-else class="dash-kpi-number" style="font-size:1rem;color:#6B7280;">—</div>
            </div>
          </div>
        </div>
      </div>

      <DashboardPeriodCharts />

      <!-- Kiosk Health Panel -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div class="eisa-panel-title-wrap">
            <i class="fa-solid fa-display" style="color:#0D9488;margin-right:0.5rem;"></i>
            <span class="eisa-panel-title">Kiosk Durumları</span>
          </div>
        </div>

        <div class="eisa-table-wrap">
          <div v-if="kiosks.length === 0" class="empty-row">
            Bu eczaneye kayıtlı kiosk bulunmuyor.
          </div>
          <table v-else class="eisa-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Kiosk Adı</th>
                <th>MAC Adresi</th>
                <th>Durum</th>
                <th>Aktif</th>
                <th>Son Bağlantı</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in kiosks" :key="k.id">
                <td class="cell-muted">{{ k.id }}</td>
                <td style="font-family:'DM Mono',monospace;font-size:0.8rem;">{{ k.ad }}</td>
                <td style="font-family:'DM Mono',monospace;font-size:0.8rem;">{{ k.mac_adresi }}</td>
                <td>
                  <span
                    class="eisa-kiosk-status"
                    :class="`eisa-kiosk-status--${k.durum}`"
                  >
                    {{ HEALTH_LABEL[k.durum]?.text ?? k.durum }}
                  </span>
                </td>
                <td>
                  <span class="eisa-pill" :class="k.aktif ? 'eisa-pill-success' : 'eisa-pill-muted'">
                    {{ k.aktif ? 'Aktif' : 'Pasif' }}
                  </span>
                </td>
                <td class="cell-muted">{{ fmtRel(k.son_goruldu) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
