<script setup>
/**
 * Eczacı Ana Sayfa — Kendine ait kiosklar, kategoriler, oturum ve kampanya
 * sayıları + kiosk health durumları.
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

const kiosks = computed(() => data.value?.kiosks ?? []);
const onlineCount = computed(() => kiosks.value.filter((k) => k.health === 'online').length);
const offlineCount = computed(() => kiosks.value.filter((k) => k.health === 'offline').length);

function fmtRel(iso) {
  if (!iso) return 'Hiç bağlanmadı';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff} sn önce`;
  if (diff < 3600) return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  return `${Math.floor(diff / 86400)} gün önce`;
}

const HEALTH_LABEL = {
  online: { text: 'Çevrimiçi', cls: 'bg-green-100 text-green-700', dot: 'bg-green-500' },
  degraded: { text: 'Yavaş', cls: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  offline: { text: 'Çevrimdışı', cls: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
};
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">📊 Ana Sayfa</h1>
      <div v-if="data?.pharmacy" class="text-sm text-gray-500">
        {{ data.pharmacy.name }} — {{ data.pharmacy.district }} / {{ data.pharmacy.city }}
      </div>
    </div>

    <div v-if="loading" class="text-gray-500">Yükleniyor…</div>
    <div v-else-if="error" class="bg-red-50 text-red-700 border border-red-200 rounded-lg p-4">
      {{ error }}
    </div>

    <template v-else-if="data">
      <div v-if="data.warning" class="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-3 text-sm">
        ⚠️ {{ data.warning }}
      </div>

      <!-- KPI kartları -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-white rounded-xl shadow p-5">
          <p class="text-xs text-gray-500 uppercase">Kiosk Sayısı</p>
          <p class="text-3xl font-bold text-teal-600 mt-1">{{ data.kiosk_count }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ onlineCount }} çevrimiçi · {{ offlineCount }} çevrimdışı</p>
        </div>
        <div class="bg-white rounded-xl shadow p-5">
          <p class="text-xs text-gray-500 uppercase">Aktif Kategori</p>
          <p class="text-3xl font-bold text-blue-600 mt-1">{{ data.category_count }}</p>
        </div>
        <div class="bg-white rounded-xl shadow p-5">
          <p class="text-xs text-gray-500 uppercase">Toplam İşlem</p>
          <p class="text-3xl font-bold text-indigo-600 mt-1">{{ data.session_count.toLocaleString('tr-TR') }}</p>
          <p class="text-xs text-gray-400 mt-1">Bugün: {{ data.session_count_today }}</p>
        </div>
        <div class="bg-white rounded-xl shadow p-5">
          <p class="text-xs text-gray-500 uppercase">Bugünkü İşlem</p>
          <p class="text-3xl font-bold text-green-600 mt-1">{{ data.session_count_today }}</p>
        </div>
        <div class="bg-white rounded-xl shadow p-5">
          <p class="text-xs text-gray-500 uppercase">Yayındaki Kampanya</p>
          <p class="text-3xl font-bold text-purple-600 mt-1">{{ data.campaign_count }}</p>
        </div>
      </div>

      <!-- Kiosk health tablosu -->
      <div class="bg-white rounded-xl shadow">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 class="font-semibold text-gray-700">Kiosk Durumları</h2>
          <button @click="load" class="text-xs text-blue-600 hover:underline">Yenile</button>
        </div>
        <div v-if="kiosks.length === 0" class="px-5 py-10 text-center text-gray-400 text-sm">
          Bu eczaneye kayıtlı kiosk bulunmuyor.
        </div>
        <table v-else class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500">
            <tr>
              <th class="text-left px-5 py-2 font-medium">#</th>
              <th class="text-left px-5 py-2 font-medium">MAC</th>
              <th class="text-left px-5 py-2 font-medium">Durum</th>
              <th class="text-left px-5 py-2 font-medium">Aktif</th>
              <th class="text-left px-5 py-2 font-medium">Son Bağlantı</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="k in kiosks"
              :key="k.id"
              class="border-t border-gray-50"
            >
              <td class="px-5 py-3 text-gray-500">{{ k.id }}</td>
              <td class="px-5 py-3 font-mono text-gray-700">{{ k.mac_address }}</td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
                  :class="HEALTH_LABEL[k.health].cls"
                >
                  <span class="w-2 h-2 rounded-full" :class="HEALTH_LABEL[k.health].dot" />
                  {{ HEALTH_LABEL[k.health].text }}
                </span>
              </td>
              <td class="px-5 py-3">
                <span
                  :class="k.is_active ? 'text-green-700' : 'text-gray-400'"
                  class="text-xs"
                >{{ k.is_active ? 'Evet' : 'Hayır' }}</span>
              </td>
              <td class="px-5 py-3 text-gray-500">{{ fmtRel(k.last_seen_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
