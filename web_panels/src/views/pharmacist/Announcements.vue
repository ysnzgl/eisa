<script setup>
import { computed, onMounted, ref } from 'vue';
import { http } from '../../services/api';

const items = ref([]);
const loading = ref(true);
const general = computed(() => items.value.filter((item) => item.kind === 'GENERAL'));
const severity = { INFO:'Bilgilendirme', WARNING:'Uyarı', ACTION_REQUIRED:'İşlem gerekli' };

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get('/api/announcements/me/active/', { params:{ include_read:true } });
    items.value = data;
  } finally { loading.value = false; }
}
async function markRead(item) {
  await http.post(`/api/announcements/${item.id}/read/`);
  item.is_read = true;
}
onMounted(load);
</script>

<template>
  <div class="eisa-page pharm-page">
    <div class="eisa-page-header"><div><p class="eisa-eyebrow">ECZACI / DUYURULAR</p><h1 class="eisa-page-title">Genel Duyurular</h1><p class="eisa-page-subtitle">Bugün eczaneniz için geçerli duyurular.</p></div><button class="eisa-btn eisa-btn-ghost" @click="load"><i class="fa-solid fa-rotate-right"></i> Yenile</button></div>
    <div v-if="loading" class="announcement-empty"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
    <div v-else-if="!general.length" class="eisa-panel announcement-empty"><i class="fa-regular fa-bell"></i><p>Bugün için genel duyuru yok.</p></div>
    <div v-else class="announcement-list">
      <article v-for="item in general" :key="`${item.id}-${item.occurrence_date}`" class="eisa-panel announcement-card" :class="[`severity-${item.severity}`, { read:item.is_read }]">
        <div class="announcement-icon"><i class="fa-solid" :class="item.severity === 'INFO' ? 'fa-circle-info' : 'fa-triangle-exclamation'"></i></div>
        <div class="announcement-copy"><div class="announcement-meta"><span>{{ severity[item.severity] }}</span><span>{{ item.occurrence_date }}</span><span v-if="item.is_read"><i class="fa-solid fa-check"></i> Okundu</span></div><h2>{{ item.title }}</h2><p>{{ item.message }}</p></div>
        <button v-if="!item.is_read" class="eisa-btn eisa-btn-ghost" @click="markRead(item)">Okudum</button>
      </article>
    </div>
  </div>
</template>

<style scoped>
.announcement-list{display:flex;flex-direction:column;gap:.8rem}.announcement-card{display:flex;gap:1rem;align-items:center;padding:1.2rem;border-left:4px solid #2563eb}.announcement-card.severity-WARNING{border-left-color:#d97706}.announcement-card.severity-ACTION_REQUIRED{border-left-color:#b1121b}.announcement-card.read{opacity:.62}.announcement-icon{font-size:1.3rem;color:#2563eb}.severity-WARNING .announcement-icon{color:#d97706}.severity-ACTION_REQUIRED .announcement-icon{color:#b1121b}.announcement-copy{flex:1}.announcement-copy h2{font-size:1rem;margin:.3rem 0}.announcement-copy p{color:#4b5563;line-height:1.5}.announcement-meta{display:flex;gap:.7rem;color:#6b7280;font-size:.7rem;font-weight:700;text-transform:uppercase}.announcement-empty{text-align:center;padding:3rem;color:#6b7280}.announcement-empty i{font-size:1.8rem;margin-bottom:.6rem}
</style>
