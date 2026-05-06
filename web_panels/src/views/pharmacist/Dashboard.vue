<script setup>
/**
 * Eczacı Ana Sayfa — Kendine ait kiosklar, kategoriler, oturum ve kampanya
 * sayılar + kiosk health durumları.
 *
 * Endpoint: GET /api/pharmacies/me/dashboard/
 */
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { http } from '../../services/api';

const data = ref(null);
const loading = ref(true);
const error = ref('');
let refreshTimer = null;

async function load() {
  try {
    const res = await http.get('/api/pharmacies/me/dashboard/');
    data.value = res.data;
    error.value = '';
  } catch (e) {
    error.value = 'Veriler yüklenemedi. Bağlantınızı kontrol edin.';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  // Kiosk health'in canlı kalması için 30 sn'de bir tazele.
  refreshTimer = setInterval(load, 30_000);
});
onUnmounted(() => clearInterval(refreshTimer));

const kiosks = computed(() => data.value?.kiosklar ?? []);
const onlineCount = computed(() => kiosks.value.filter((k) => k.durum === 'online').length);
const offlineCount = computed(() => kiosks.value.filter((k) => k.durum === 'offline').length);

function fmtRel(iso) {
  if (!iso) return 'Hiç bağlanmadı';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff} sn önce`;
  if (diff < 3600) return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  return `${Math.floor(diff / 86400)} gün önce}`;
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
        <p class="eisa-eyebrow">Eczacı / Ana Sayfa</p>
        <h1 class="eisa-page-title">
          {{ data?.eczane?.ad ?? 'Kontrol Paneli' }}
        </h1>
        <p v-if="data?.eczane" class="eisa-page-subtitle">
          {{ data.eczane.ilce }} / {{ data.eczane.il }}
        </p>
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

      <!-- KPI Stats -->
      <div class="pharm-stats">
        <div class="pharm-stat-card">
          <p class="pharm-stat-label">Kiosk Sayısı</p>
          <p class="pharm-stat-value">{{ data.kiosk_sayisi }}</p>
          <p class="pharm-stat-sub">{{ onlineCount }} Çevrimiçi — {{ offlineCount }} Çevrimdışı</p>
        </div>
        <div class="pharm-stat-card">
          <p class="pharm-stat-label">Aktif Kategori</p>
          <p class="pharm-stat-value">{{ data.kategori_sayisi }}</p>
        </div>
        <div class="pharm-stat-card">
          <p class="pharm-stat-label">Toplam İşlem</p>
          <p class="pharm-stat-value">{{ data.oturum_sayisi?.toLocaleString('tr-TR') }}</p>
          <p class="pharm-stat-sub">Bugün: {{ data.oturum_sayisi_bugun }}</p>
        </div>
        <div class="pharm-stat-card">
          <p class="pharm-stat-label">Bugünkü İşlem</p>
          <p class="pharm-stat-value">{{ data.oturum_sayisi_bugun }}</p>
        </div>
        <div class="pharm-stat-card">
          <p class="pharm-stat-label">Yayındaki Kampanya</p>
          <p class="pharm-stat-value">{{ data.reklam_sayisi }}</p>
        </div>
      </div>

      <!-- Kiosk Health Panel -->
      <div class="eisa-panel">
        <div class="eisa-panel-header">
          <div class="eisa-panel-title-wrap">
            <i class="fa-solid fa-display" style="color:#0D9488;margin-right:0.5rem;"></i>
            <span class="eisa-panel-title">Kiosk Durumları</span>
          </div>
          <button class="eisa-btn eisa-btn-ghost" @click="load">
            <i class="fa-solid fa-rotate-right"></i>
            Yenile
          </button>
        </div>

        <div class="eisa-table-wrap">
          <div v-if="kiosks.length === 0" class="empty-row">
            Bu eczaneye kayıtlı kiosk bulunmuyor.
          </div>
          <table v-else class="eisa-table">
            <thead>
              <tr>
                <th>#</th>
                <th>MAC Adresi</th>
                <th>Durum</th>
                <th>Aktif</th>
                <th>Son Bağlantı</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in kiosks" :key="k.id">
                <td class="cell-muted">{{ k.id }}</td>
                <td style="font-family:'DM Mono',monospace;font-size:0.8rem;">{{ k.mac_adresi }}</td>
                <td>
                  <span
                    class="eisa-kiosk-status"
                    :class="`eisa-kiosk-status--${k.durum}`"
                  >
                    <span class="eisa-kiosk-dot"></span>
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
