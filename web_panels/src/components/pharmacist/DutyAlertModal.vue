<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { http } from '../../services/api';

const router = useRouter();
const announcements = ref([]);
const loading = ref(false);
const busy = ref(false);
const error = ref('');
const current = computed(() => announcements.value[0] || null);
const isSystem = computed(() => current.value?.kind === 'SYSTEM');

async function load() {
  if (loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    const { data } = await http.get('/api/announcements/me/active/', { __silent: true });
    announcements.value = Array.isArray(data) ? data : [];
  } catch {
    announcements.value = [];
  } finally {
    loading.value = false;
  }
}

function advance() {
  announcements.value = announcements.value.slice(1);
  error.value = '';
}

async function markRead() {
  if (!current.value || busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await http.post(`/api/announcements/${current.value.id}/read/`);
    advance();
  } catch (requestError) {
    error.value = requestError?.response?.data?.detail || 'Duyuru okundu olarak kaydedilemedi. Lütfen tekrar deneyin.';
  } finally {
    busy.value = false;
  }
}

async function noDuty() {
  if (!current.value || busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await http.put('/api/announcements/duty/', {
      month: current.value.target_month,
      has_no_duty: true,
      dates: [],
    });
    advance();
  } catch (requestError) {
    error.value = requestError?.response?.data?.detail || 'Nöbet bilgisi kaydedilemedi. Lütfen tekrar deneyin.';
  } finally {
    busy.value = false;
  }
}

function openCalendar() {
  if (!current.value?.action_url) return;
  const target = current.value.action_url;
  advance();
  router.push(target);
}

onMounted(load);
</script>

<template>
  <Teleport to="body">
    <div v-if="current" class="eisa-modal-backdrop announcement-alert-backdrop">
      <section
        class="eisa-modal announcement-alert-modal"
        :data-severity="current.severity"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`announcement-title-${current.id}`"
      >
        <div class="eisa-modal-header announcement-alert-header">
          <div class="announcement-alert-heading">
            <span class="announcement-alert-icon"><i class="fa-solid" :class="isSystem ? 'fa-calendar-xmark' : 'fa-bullhorn'"></i></span>
            <div>
              <span class="eisa-pill" :class="isSystem ? 'eisa-pill-warning' : 'eisa-pill-info'">
                {{ isSystem ? 'Sistem Duyurusu' : 'Genel Duyuru' }}
              </span>
              <h2 :id="`announcement-title-${current.id}`" class="eisa-modal-title">{{ current.title }}</h2>
            </div>
          </div>
        </div>

        <div class="eisa-modal-body announcement-alert-body">
          <p>{{ current.message }}</p>
          <div v-if="error" class="eisa-error-banner" role="alert">
            <i class="fa-solid fa-triangle-exclamation"></i>{{ error }}
          </div>
        </div>

        <div class="eisa-modal-footer announcement-alert-actions">
          <template v-if="isSystem">
            <button class="eisa-btn eisa-btn-cta" :disabled="busy" @click="openCalendar">
              <i class="fa-solid fa-calendar-days"></i>{{ current.action_label || 'Nöbet Günlerini Gir' }}
            </button>
            <button class="eisa-btn eisa-btn-ghost" :disabled="busy" @click="noDuty">Bu Ay Nöbetim Yok</button>
            <button class="eisa-btn eisa-btn-ghost" :disabled="busy" @click="markRead">Bugün İçin Okudum</button>
          </template>
          <button v-else class="eisa-btn eisa-btn-cta" :disabled="busy" @click="markRead">
            <i v-if="busy" class="fa-solid fa-circle-notch fa-spin"></i>
            <i v-else class="fa-solid fa-check"></i>
            {{ busy ? 'Kaydediliyor…' : 'Okudum' }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.announcement-alert-backdrop { z-index:5000; }
.announcement-alert-modal { max-width:560px; border-top:4px solid var(--eisa-info); }
.announcement-alert-modal[data-severity="WARNING"] { border-top-color:#D97706; }
.announcement-alert-modal[data-severity="ACTION_REQUIRED"] { border-top-color:var(--eisa-red); }
.announcement-alert-header { align-items:flex-start; }
.announcement-alert-heading { display:flex; align-items:flex-start; gap:.85rem; }
.announcement-alert-heading h2 { margin-top:.65rem; font-size:1.2rem; }
.announcement-alert-icon { width:42px; height:42px; display:grid; place-items:center; flex:0 0 auto; border-radius:50%; background:var(--eisa-info-soft); color:var(--eisa-info); }
.announcement-alert-body p { margin:0; color:var(--text-secondary); line-height:1.65; white-space:pre-wrap; }
.announcement-alert-body .eisa-error-banner { margin-top:1rem; }
.announcement-alert-actions { flex-wrap:wrap; }
@media(max-width:620px){.announcement-alert-actions{flex-direction:column-reverse}.announcement-alert-actions .eisa-btn{width:100%}}
</style>
