<script setup>
/**
 * Pharmacist Inbox — Hassas durum (Akış B) bildirim kutusu.
 * Her 10 saniyede bir merkezi API'yi yoklayarak yeni
 * "is_sensitive_flow=true" oturumlarını gösterir.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { http } from '../../services/api';

const notifications = ref([]);   // Gelen bildirimler
const readIds = ref(new Set());   // Okundu işaretlenenler (local)
const newIds = ref(new Set());    // Yeni gelen (3sn vurgu)
const connected = ref(true);
const lastSeenId = ref(0);        // En son görülen bildirim ID'si

let pollInterval = null;

// ── Veri çekme ──────────────────────────────────────────────
async function fetchInbox() {
  try {
    const res = await http.get('/api/analytics/sessions/', {
      params: { is_sensitive_flow: true, ordering: '-created_at', page_size: 50 },
    });
    const items = Array.isArray(res.data) ? res.data : res.data.results ?? [];

    // Yeni gelenleri tespit et
    items.forEach((item) => {
      if (item.id > lastSeenId.value) {
        newIds.value.add(item.id);
        setTimeout(() => newIds.value.delete(item.id), 3000);
      }
    });

    if (items.length > 0) lastSeenId.value = items[0].id;
    notifications.value = items;
    connected.value = true;
  } catch {
    connected.value = false;
  }
}

onMounted(() => {
  fetchInbox();
  pollInterval = setInterval(fetchInbox, 10_000);
});

onUnmounted(() => clearInterval(pollInterval));

// ── Hesaplanan ───────────────────────────────────────────────
const unreadCount = computed(
  () => notifications.value.filter((n) => !readIds.value.has(n.id)).length
);

function markRead(id) {
  readIds.value.add(id);
}

function markAllRead() {
  notifications.value.forEach((n) => readIds.value.add(n.id));
}

// ── Yardımcılar ──────────────────────────────────────────────
const GENDER_LABEL = { F: 'Kadın', M: 'Erkek', O: 'Diğer' };

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff} saniye önce`;
  if (diff < 3600) return `${Math.floor(diff / 60)} dakika önce`;
  return `${Math.floor(diff / 3600)} saat önce`;
}
</script>

<template>
  <div class="p-6 space-y-5">
    <!-- Başlık & durum -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">
        🔔 Gelen Kutusu
        <span
          v-if="unreadCount > 0"
          class="ml-2 bg-red-500 text-white text-sm px-2 py-0.5 rounded-full"
        >{{ unreadCount }}</span>
      </h1>
      <div class="flex items-center gap-3">
        <span
          :class="connected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
          class="text-xs px-3 py-1 rounded-full font-semibold"
        >
          {{ connected ? '● Canlı' : '✕ Bağlantı kesildi' }}
        </span>
        <button
          v-if="unreadCount > 0"
          @click="markAllRead"
          class="text-sm text-blue-600 hover:underline"
        >Tümünü okundu işaretle</button>
      </div>
    </div>

    <!-- Boş durum -->
    <div v-if="notifications.length === 0" class="bg-white rounded-xl shadow p-10 text-center text-gray-400">
      <p class="text-4xl mb-3">📭</p>
      <p>Henüz bildirim yok.</p>
      <p class="text-sm mt-1">Kiosk'tan hassas kategori seçildiğinde burada görünecek.</p>
    </div>

    <!-- Bildirim Kartları -->
    <div class="space-y-3">
      <div
        v-for="n in notifications"
        :key="n.id"
        @click="markRead(n.id)"
        :class="[
          'bg-white rounded-xl shadow p-4 flex items-start gap-4 cursor-pointer transition border-l-4',
          newIds.has(n.id) ? 'border-red-500 animate-pulse' : readIds.has(n.id) ? 'border-gray-200 opacity-70' : 'border-red-400',
        ]"
      >
        <!-- İkon -->
        <div class="text-3xl select-none">🔴</div>

        <!-- İçerik -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-semibold text-red-700 text-sm">Hassas Danışma</span>
            <span class="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
              {{ n.category?.name ?? n.category_id ?? '—' }}
            </span>
          </div>
          <div class="text-gray-700 mt-1 text-sm flex gap-4 flex-wrap">
            <span>👤 {{ GENDER_LABEL[n.gender] ?? n.gender }}</span>
            <span>📅 {{ n.age_range }} yaş</span>
          </div>
          <div class="text-xs text-gray-400 mt-1">{{ timeAgo(n.created_at) }}</div>
        </div>

        <!-- QR Kodu -->
        <div class="text-right flex-shrink-0">
          <p class="text-xs text-gray-400 mb-1">QR Kodu</p>
          <p class="font-mono font-bold text-lg text-gray-800 tracking-widest">{{ n.qr_code }}</p>
          <span
            v-if="!readIds.has(n.id)"
            class="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full"
          >Yeni</span>
        </div>
      </div>
    </div>
  </div>
</template>
