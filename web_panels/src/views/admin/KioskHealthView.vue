<script setup>
/**
 * Kiosk Sağlık Durumu Panosu
 * Tüm aktif kiosklarin online/offline durumunu, son ping zamanını ve
 * playlist versiyonunu gösterir. Force Regenerate butonu ile seçili kiosk
 * için anında playlist üretimi tetiklenebilir.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { toast } from 'vue-sonner';
import {
  getKioskHealth,
  generatePlaylists,
  listGenerationJobs,
} from '../../services/dooh';

// ─── State ────────────────────────────────────────────────────────────────────
const kiosks      = ref([]);
const jobs        = ref([]);
const loading     = ref(false);
const error       = ref(null);
const search      = ref('');
const filterOnline = ref('all'); // 'all' | 'online' | 'offline'
const regenerating = ref(new Set()); // kiosk id'leri

let _pollInterval = null;

// ─── Computed ─────────────────────────────────────────────────────────────────
const filtered = computed(() => {
  let list = kiosks.value;
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    list = list.filter(
      (k) =>
        k.ad.toLowerCase().includes(q) ||
        k.mac_adresi.toLowerCase().includes(q) ||
        (k.eczane_ad ?? '').toLowerCase().includes(q),
    );
  }
  if (filterOnline.value === 'online') list = list.filter((k) => k.is_online);
  if (filterOnline.value === 'offline') list = list.filter((k) => !k.is_online);
  return list;
});

const onlineCount  = computed(() => kiosks.value.filter((k) => k.is_online).length);
const offlineCount = computed(() => kiosks.value.filter((k) => !k.is_online).length);

const activeJobs = computed(() =>
  jobs.value.filter((j) => j.status === 'PENDING' || j.status === 'RUNNING'),
);

// ─── Fetch ────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  error.value = null;
  try {
    const [healthRes, jobsRes] = await Promise.all([
      getKioskHealth(),
      listGenerationJobs(),
    ]);
    kiosks.value = healthRes.data;
    jobs.value   = jobsRes.data;
  } catch (e) {
    error.value = e?.response?.data?.detail ?? e.message ?? 'Veri alınamadı.';
  } finally {
    loading.value = false;
  }
}

async function forceRegenerate(kiosk) {
  if (regenerating.value.has(kiosk.id)) return;
  regenerating.value = new Set([...regenerating.value, kiosk.id]);
  try {
    await generatePlaylists({ kiosk: kiosk.id });
    await load();
  } catch (e) {
    toast.error(`Playlist üretimi başlatılamadı: ${e?.response?.data?.error ?? e.message}`);
  } finally {
    const s = new Set(regenerating.value);
    s.delete(kiosk.id);
    regenerating.value = s;
  }
}

function timeSince(isoStr) {
  if (!isoStr) return '—';
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (diff < 60)   return `${diff}sn`;
  if (diff < 3600) return `${Math.floor(diff / 60)}dk`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}sa`;
  return `${Math.floor(diff / 86400)}g`;
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  load();
  _pollInterval = setInterval(load, 30_000); // 30sn'de bir otomatik yenile
});

onUnmounted(() => clearInterval(_pollInterval));
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Başlık + Özet kartları -->
    <div class="flex items-center justify-between flex-wrap gap-4">
      <h1 class="text-2xl font-bold text-gray-900">Kiosk Sağlık Durumu</h1>
      <button
        class="btn-secondary text-sm"
        :disabled="loading"
        @click="load"
      >
        <span v-if="loading">⟳ Yükleniyor…</span>
        <span v-else>↺ Yenile</span>
      </button>
    </div>

    <!-- Özet bandı -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="stat-card bg-emerald-50 border-emerald-200">
        <p class="stat-label text-emerald-600">Online</p>
        <p class="stat-value text-emerald-700">{{ onlineCount }}</p>
      </div>
      <div class="stat-card bg-red-50 border-red-200">
        <p class="stat-label text-red-600">Offline</p>
        <p class="stat-value text-red-700">{{ offlineCount }}</p>
      </div>
      <div class="stat-card bg-blue-50 border-blue-200">
        <p class="stat-label text-blue-600">Toplam</p>
        <p class="stat-value text-blue-700">{{ kiosks.length }}</p>
      </div>
      <div class="stat-card" :class="activeJobs.length > 0 ? 'bg-amber-50 border-amber-200' : 'bg-gray-50 border-gray-200'">
        <p class="stat-label" :class="activeJobs.length > 0 ? 'text-amber-600' : 'text-gray-500'">
          Aktif İş
        </p>
        <p class="stat-value" :class="activeJobs.length > 0 ? 'text-amber-700 animate-pulse' : 'text-gray-700'">
          {{ activeJobs.length }}
        </p>
      </div>
    </div>

    <!-- Aktif generation jobs bandı -->
    <div v-if="activeJobs.length" class="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-2">
      <p class="text-sm font-semibold text-amber-700">Devam eden playlist üretim işleri:</p>
      <div v-for="job in activeJobs" :key="job.id" class="flex items-center gap-3">
        <span class="text-xs text-amber-600 font-mono">{{ job.target_date }}</span>
        <div class="flex-1 h-2 bg-amber-200 rounded-full overflow-hidden">
          <div
            class="h-full bg-amber-500 transition-all duration-500"
            :style="`width: ${job.progress_pct}%`"
          />
        </div>
        <span class="text-xs text-amber-700">{{ job.done_kiosks }}/{{ job.total_kiosks }}</span>
        <span class="text-xs px-2 py-0.5 rounded-full font-medium"
          :class="job.status === 'RUNNING' ? 'bg-amber-200 text-amber-800' : 'bg-gray-200 text-gray-600'"
        >{{ job.status }}</span>
      </div>
    </div>

    <!-- Hata -->
    <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
      {{ error }}
    </div>

    <!-- Filtreler -->
    <div class="flex flex-wrap gap-3 items-center">
      <input
        v-model="search"
        type="search"
        placeholder="Kiosk adı, MAC veya eczane ara…"
        class="input-field w-64"
      />
      <div class="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
        <button
          v-for="opt in [['all','Tümü'], ['online','Online'], ['offline','Offline']]"
          :key="opt[0]"
          class="px-3 py-1.5 transition-colors"
          :class="filterOnline === opt[0]
            ? 'bg-indigo-600 text-white'
            : 'bg-white text-gray-600 hover:bg-gray-50'"
          @click="filterOnline = opt[0]"
        >{{ opt[1] }}</button>
      </div>
      <span class="text-xs text-gray-400 ml-auto">Otomatik yenileme: 30sn</span>
    </div>

    <!-- Tablo -->
    <div class="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
          <tr>
            <th class="px-4 py-3 text-left">Durum</th>
            <th class="px-4 py-3 text-left">Kiosk</th>
            <th class="px-4 py-3 text-left">Eczane</th>
            <th class="px-4 py-3 text-left">MAC Adresi</th>
            <th class="px-4 py-3 text-center">Son Ping</th>
            <th class="px-4 py-3 text-center">Playlist Ver.</th>
            <th class="px-4 py-3 text-right">İşlem</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          <tr v-if="loading && kiosks.length === 0">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">Yükleniyor…</td>
          </tr>
          <tr v-else-if="filtered.length === 0">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">Kiosk bulunamadı.</td>
          </tr>
          <tr
            v-for="k in filtered"
            :key="k.id"
            class="hover:bg-gray-50 transition-colors"
          >
            <!-- Durum -->
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold"
                :class="k.is_online
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-red-100 text-red-700'"
              >
                <span
                  class="w-1.5 h-1.5 rounded-full"
                  :class="k.is_online ? 'bg-emerald-500' : 'bg-red-400'"
                />
                {{ k.is_online ? 'Online' : 'Offline' }}
              </span>
            </td>
            <!-- Kiosk adı -->
            <td class="px-4 py-3 font-medium text-gray-900">{{ k.ad }}</td>
            <!-- Eczane -->
            <td class="px-4 py-3 text-gray-600">{{ k.eczane_ad ?? '—' }}</td>
            <!-- MAC -->
            <td class="px-4 py-3 font-mono text-gray-500 text-xs">{{ k.mac_adresi }}</td>
            <!-- Son ping -->
            <td class="px-4 py-3 text-center">
              <span
                class="text-xs"
                :class="k.is_online ? 'text-gray-600' : 'text-red-400'"
                :title="k.son_goruldu ?? 'Hiç ping göndermedi'"
              >
                {{ timeSince(k.son_goruldu) }}
              </span>
            </td>
            <!-- Playlist versiyonu -->
            <td class="px-4 py-3 text-center">
              <span v-if="k.last_playlist_version" class="font-mono text-indigo-600 text-xs">
                v{{ k.last_playlist_version }}
              </span>
              <span v-else class="text-gray-400 text-xs">—</span>
            </td>
            <!-- İşlem -->
            <td class="px-4 py-3 text-right">
              <button
                class="text-xs px-3 py-1.5 rounded-lg border border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition-colors disabled:opacity-50"
                :disabled="regenerating.has(k.id)"
                @click="forceRegenerate(k)"
              >
                <span v-if="regenerating.has(k.id)">⟳ Çalışıyor…</span>
                <span v-else>↺ Yenile</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  @apply rounded-xl border p-4 flex flex-col gap-1;
}
.stat-label {
  @apply text-xs font-medium uppercase tracking-wide;
}
.stat-value {
  @apply text-3xl font-bold;
}
.btn-secondary {
  @apply px-4 py-2 rounded-lg border border-gray-300 bg-white text-gray-700
         hover:bg-gray-50 transition-colors font-medium disabled:opacity-50;
}
.input-field {
  @apply border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none
         focus:ring-2 focus:ring-indigo-300;
}
</style>
