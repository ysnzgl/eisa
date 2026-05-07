<script setup>
/**
 * Eczacı Ana Sayfa — Kendine ait kiosklar, kategoriler, oturum ve kampanya
 * sayılar + kiosk health durumları.
 *
 * Endpoint: GET /api/pharmacies/me/dashboard/
 */
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { http } from '../../services/api';

const data    = ref(null);
const loading = ref(true);
const error   = ref('');
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

async function load() {
  try {
    const res = await http.get('/api/pharmacies/me/dashboard/');
    data.value  = res.data;
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
            <div class="dash-kpi-number">{{ kpiValues[kpi.valueKey] }}</div>
            <div v-if="kpi.sub" class="dash-kpi-sub" :class="kpi.subClass">
              {{ kpi.sub() }}
            </div>
          </div>
        </div>
      </div>

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
