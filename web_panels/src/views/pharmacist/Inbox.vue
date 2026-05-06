<script setup>
/**
 * Pharmacist Inbox — Hassas durum (Akış Bildirimi) bildirim kutusu.
 * Her 10 saniyede bir merkezi API'yi yoklayarak yeni
 * "is_sensitive_flow=true" oturumları gösterir.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { http } from '../../services/api';

const notifications = ref([]);   // Gelen bildirimler
const readIds = ref(new Set());   // Okundu iaretlenenler (local)
const newIds = ref(new Set());    // Yeni gelen (3sn vurgu)
const connected = ref(true);
const lastSeenId = ref(0);        // En son görülen bildirim ID'si

let pollInterval = null;

//  Veri Çekme Çekme 
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

//  Hesaplanan 
const unreadCount = computed(
  () => notifications.value.filter((n) => !readIds.value.has(n.id)).length
);

function markRead(id) {
  readIds.value.add(id);
}

function markAllRead() {
  notifications.value.forEach((n) => readIds.value.add(n.id));
}

//  Yardmclar 
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
  <div class="eisa-page pharm-page">

    <!-- Page Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Eczacı / Bildirimler</p>
        <h1 class="eisa-page-title">
          Gelen Kutusu
          <span v-if="unreadCount > 0" class="eisa-pill eisa-pill-danger" style="margin-left:0.5rem;">
            {{ unreadCount }}
          </span>
        </h1>
      </div>
      <div class="eisa-header-actions">
        <span class="inbox-badge" :class="connected ? 'inbox-connected' : 'inbox-disconnected'">
          <i :class="connected ? 'fa-solid fa-signal' : 'fa-solid fa-triangle-exclamation'"></i>
          {{ connected ? 'Canlı' : 'Bağlantı kesildi' }}
        </span>
        <button
          v-if="unreadCount > 0"
          class="eisa-btn eisa-btn-ghost"
          @click="markAllRead"
        >
          <i class="fa-solid fa-check-double"></i>
          Tümünü Okundu İşaretle
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="notifications.length === 0" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
      <i class="fa-regular fa-bell" style="font-size:2.5rem;margin-bottom:1rem;opacity:0.3;display:block;"></i>
      <p style="font-size:0.95rem;font-weight:600;margin-bottom:0.35rem;">Henüz bildirim yok</p>
      <p style="font-size:0.8rem;">Kiosk'tan hassas kategori seçildiğinde burada görünecek.</p>
    </div>

    <!-- Notification Cards -->
    <div style="display:flex;flex-direction:column;gap:0.75rem;">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="inbox-card"
        :class="[
          newIds.has(n.id) ? 'inbox-card--new' : readIds.has(n.id) ? 'inbox-card--read' : 'inbox-card--unread'
        ]"
        @click="markRead(n.id)"
      >
        <!-- Alert Icon -->
        <div class="inbox-alert-icon">
          <i class="fa-solid fa-triangle-exclamation"></i>
        </div>

        <!-- Main Content -->
        <div class="inbox-card-meta">
          <p class="inbox-card-title">Hassas Danma</p>
          <div class="inbox-card-details">
            <span class="eisa-pill eisa-pill-muted">
              {{ n.category?.name ?? n.category_id ?? '—' }}
            </span>
            <span><i class="fa-solid fa-person" style="font-size:0.65rem;margin-right:0.2rem;"></i>{{ GENDER_LABEL[n.gender] ?? n.gender }}</span>
            <span><i class="fa-solid fa-calendar-days" style="font-size:0.65rem;margin-right:0.2rem;"></i>{{ n.age_range }} yaş</span>
          </div>
          <p class="inbox-card-time">{{ timeAgo(n.created_at) }}</p>
        </div>

        <!-- QR Code -->
        <div class="inbox-card-qr">
          <p style="font-size:0.7rem;color:#9CA3AF;margin-bottom:0.2rem;">QR Kodu</p>
          <p class="inbox-card-qr-code">{{ n.qr_code }}</p>
          <span v-if="!readIds.has(n.id)" class="inbox-card-badge">Yeni</span>
        </div>
      </div>
    </div>
  </div>
</template>
