<script setup>
/**
 * Admin Dashboard — Merkezi istatistik ekranı.
 * GET /api/analytics/sessions/stats/ ve /api/campaigns/ endpoint'lerinden
 * veri çekerek KPI kartları ve dağılım grafikleri gösterir.
 */
import { ref, onMounted, computed } from 'vue';
import { http } from '../../services/api';

const loading = ref(true);
const error = ref('');

// İstatistik verileri
const stats = ref({
  total_sessions: 0,
  by_age_range: {},
  by_gender: {},
  by_category: [],
  by_date: [],
});
const activeCampaignCount = ref(0);

// ── Veri çekme ──────────────────────────────────────────────
onMounted(async () => {
  try {
    const [statsRes, campRes] = await Promise.all([
      http.get('/api/analytics/sessions/stats/'),
      http.get('/api/campaigns/', { params: { is_active: true } }),
    ]);
    stats.value = statsRes.data;
    // Sayfalı veya liste döndürebilir
    const campData = campRes.data;
    activeCampaignCount.value = Array.isArray(campData)
      ? campData.length
      : campData.count ?? 0;
  } catch (e) {
    error.value = 'Veriler yüklenemedi. API bağlantısını kontrol edin.';
  } finally {
    loading.value = false;
  }
});

// ── Hesaplanan değerler ──────────────────────────────────────
const todaySessions = computed(() => {
  const dates = stats.value.by_date;
  if (!dates || dates.length === 0) return 0;
  return dates[dates.length - 1]?.count ?? 0;
});

const topCategory = computed(() => {
  const cats = stats.value.by_category;
  return cats && cats.length > 0 ? cats[0].name : '—';
});

// Yüzde hesaplamak için toplam
const totalGender = computed(() => {
  const g = stats.value.by_gender;
  return Object.values(g).reduce((a, b) => a + b, 0) || 1;
});

const genderLabel = { F: 'Kadın', M: 'Erkek', O: 'Diğer' };

// Yaş aralığı sıralama için toplam
const totalAge = computed(() => {
  const a = stats.value.by_age_range;
  return Object.values(a).reduce((a, b) => a + b, 0) || 1;
});

const sortedCategories = computed(() =>
  [...(stats.value.by_category || [])].slice(0, 5)
);
const maxCatCount = computed(() =>
  sortedCategories.value.reduce((m, c) => Math.max(m, c.count), 1)
);
</script>

<template>
  <div class="p-6 space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">📊 Genel İstatistikler</h1>

    <!-- Yükleniyor -->
    <div v-if="loading" class="flex items-center gap-3 text-gray-500">
      <svg class="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      <span>Veriler yükleniyor…</span>
    </div>

    <!-- Hata -->
    <div v-else-if="error" class="bg-red-50 text-red-700 border border-red-200 rounded-lg p-4">
      {{ error }}
    </div>

    <template v-else>
      <!-- ── KPI Kartları ──────────────────────────────────────── -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
          <span class="text-xs text-gray-500 uppercase tracking-wide">Toplam Oturum</span>
          <span class="text-3xl font-bold text-blue-600">{{ stats.total_sessions.toLocaleString('tr-TR') }}</span>
        </div>
        <div class="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
          <span class="text-xs text-gray-500 uppercase tracking-wide">Bugün</span>
          <span class="text-3xl font-bold text-green-600">{{ todaySessions.toLocaleString('tr-TR') }}</span>
        </div>
        <div class="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
          <span class="text-xs text-gray-500 uppercase tracking-wide">Öne Çıkan Kategori</span>
          <span class="text-xl font-semibold text-gray-800 truncate">{{ topCategory }}</span>
        </div>
        <div class="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
          <span class="text-xs text-gray-500 uppercase tracking-wide">Aktif Kampanya</span>
          <span class="text-3xl font-bold text-purple-600">{{ activeCampaignCount }}</span>
        </div>
      </div>

      <!-- ── Cinsiyet & Yaş Dağılımı ─────────────────────────── -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Cinsiyet -->
        <div class="bg-white rounded-xl shadow p-5">
          <h2 class="font-semibold text-gray-700 mb-4">Cinsiyet Dağılımı</h2>
          <div v-if="Object.keys(stats.by_gender).length === 0" class="text-gray-400 text-sm">Veri yok</div>
          <div v-else class="space-y-3">
            <div v-for="(count, key) in stats.by_gender" :key="key" class="flex items-center gap-3">
              <span class="w-14 text-sm text-gray-600">{{ genderLabel[key] ?? key }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="key === 'F' ? 'bg-pink-400' : key === 'M' ? 'bg-blue-400' : 'bg-gray-400'"
                  :style="{ width: (count / totalGender * 100).toFixed(1) + '%' }"
                />
              </div>
              <span class="w-12 text-right text-sm font-medium text-gray-700">
                {{ (count / totalGender * 100).toFixed(0) }}%
              </span>
            </div>
          </div>
        </div>

        <!-- Yaş Aralığı -->
        <div class="bg-white rounded-xl shadow p-5">
          <h2 class="font-semibold text-gray-700 mb-4">Yaş Aralığı Dağılımı</h2>
          <div v-if="Object.keys(stats.by_age_range).length === 0" class="text-gray-400 text-sm">Veri yok</div>
          <div v-else class="space-y-3">
            <div v-for="(count, range) in stats.by_age_range" :key="range" class="flex items-center gap-3">
              <span class="w-14 text-sm text-gray-600">{{ range }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                <div
                  class="h-full bg-blue-500 rounded-full transition-all"
                  :style="{ width: (count / totalAge * 100).toFixed(1) + '%' }"
                />
              </div>
              <span class="w-12 text-right text-sm font-medium text-gray-700">{{ count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Üst 5 Kategori ──────────────────────────────────── -->
      <div class="bg-white rounded-xl shadow p-5">
        <h2 class="font-semibold text-gray-700 mb-4">En Çok Seçilen Kategoriler (Top 5)</h2>
        <div v-if="sortedCategories.length === 0" class="text-gray-400 text-sm">Veri yok</div>
        <div v-else class="space-y-3">
          <div v-for="cat in sortedCategories" :key="cat.name" class="flex items-center gap-3">
            <span class="w-40 text-sm text-gray-700 truncate">{{ cat.name }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
              <div
                class="h-full bg-green-500 rounded-full transition-all"
                :style="{ width: (cat.count / maxCatCount * 100).toFixed(1) + '%' }"
              />
            </div>
            <span class="w-12 text-right text-sm font-medium text-gray-700">{{ cat.count }}</span>
          </div>
        </div>
      </div>

      <!-- ── Son 30 Gün Aktivitesi ───────────────────────────── -->
      <div class="bg-white rounded-xl shadow p-5">
        <h2 class="font-semibold text-gray-700 mb-4">Son 30 Gün Aktivitesi</h2>
        <div v-if="!stats.by_date || stats.by_date.length === 0" class="text-gray-400 text-sm">Veri yok</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="px-4 py-2">Tarih</th>
                <th class="px-4 py-2 text-right">Oturum Sayısı</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in [...stats.by_date].reverse().slice(0, 14)"
                :key="row.date"
                class="border-t border-gray-100 hover:bg-gray-50"
              >
                <td class="px-4 py-2 text-gray-700">{{ row.date }}</td>
                <td class="px-4 py-2 text-right font-medium text-blue-600">{{ row.count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
