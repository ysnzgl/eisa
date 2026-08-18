<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { http } from '../../services/api';

const router = useRouter();
const alerts = ref([]);
const busy = ref(false);

async function load() {
  const { data } = await http.get('/api/announcements/me/active/', { __silent: true });
  alerts.value = data.filter((item) => item.kind === 'SYSTEM');
}

async function markRead(alert) {
  busy.value = true;
  try {
    await http.post(`/api/announcements/${alert.id}/read/`);
    alerts.value = alerts.value.filter((item) => item.id !== alert.id);
  } finally {
    busy.value = false;
  }
}

async function noDuty(alert) {
  busy.value = true;
  try {
    await http.put('/api/announcements/duty/', {
      month: alert.target_month,
      has_no_duty: true,
      dates: [],
    });
    alerts.value = alerts.value.filter((item) => item.id !== alert.id);
  } finally {
    busy.value = false;
  }
}

function openCalendar(alert) {
  router.push(alert.action_url);
  alerts.value = alerts.value.filter((item) => item.id !== alert.id);
}

onMounted(() => load().catch(() => {}));
</script>

<template>
  <div v-if="alerts.length" class="duty-modal-backdrop">
    <section class="duty-modal" :data-severity="alerts[0].severity" role="dialog" aria-modal="true">
      <div class="duty-modal-icon"><i class="fa-solid fa-calendar-xmark"></i></div>
      <p class="eisa-eyebrow">NÖBET UYARISI</p>
      <h2>{{ alerts[0].title }}</h2>
      <p class="duty-modal-message">{{ alerts[0].message }}</p>
      <div class="duty-modal-actions">
        <button class="eisa-btn eisa-btn-primary" :disabled="busy" @click="openCalendar(alerts[0])">
          <i class="fa-solid fa-calendar-days"></i> {{ alerts[0].action_label || 'Nöbet Günlerini Gir' }}
        </button>
        <button class="eisa-btn eisa-btn-ghost" :disabled="busy" @click="noDuty(alerts[0])">
          Bu Ay Nöbetim Yok
        </button>
        <button class="duty-read-btn" :disabled="busy" @click="markRead(alerts[0])">
          Bugün İçin Okudum
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.duty-modal-backdrop { position:fixed; inset:0; z-index:5000; display:grid; place-items:center; padding:1rem; background:rgba(15,23,42,.58); backdrop-filter:blur(3px); }
.duty-modal { width:min(520px,100%); padding:2rem; border-radius:18px; background:#fff; border-top:5px solid #b1121b; box-shadow:0 24px 70px rgba(15,23,42,.28); text-align:center; }
.duty-modal[data-severity="INFO"] { border-top-color:#2563eb; }
.duty-modal[data-severity="WARNING"] { border-top-color:#d97706; }
.duty-modal-icon { width:58px; height:58px; margin:0 auto 1rem; display:grid; place-items:center; border-radius:50%; background:#fef2f2; color:#b1121b; font-size:1.45rem; }
.duty-modal h2 { margin:.25rem 0 .7rem; color:#111827; font-size:1.35rem; }
.duty-modal-message { color:#4b5563; line-height:1.6; }
.duty-modal-actions { display:flex; flex-direction:column; gap:.65rem; margin-top:1.5rem; }
.duty-modal-actions button { justify-content:center; }
.duty-read-btn { border:0; background:transparent; color:#6b7280; cursor:pointer; padding:.5rem; font-weight:600; }
.duty-read-btn:hover { color:#111827; }
</style>
