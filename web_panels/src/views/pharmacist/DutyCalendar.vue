<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { http } from '../../services/api';

const route = useRoute();
const router = useRouter();
const now = new Date();
const fallbackMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const month = ref(/^\d{4}-\d{2}$/.test(route.query.month || '') ? route.query.month : fallbackMonth);
const selected = ref(new Set());
const noDuty = ref(false);
const loading = ref(true);
const saving = ref(false);

const monthDate = computed(() => new Date(`${month.value}-01T12:00:00`));
const monthLabel = computed(() => monthDate.value.toLocaleDateString('tr-TR', { month:'long', year:'numeric' }));
const days = computed(() => {
  const year = monthDate.value.getFullYear();
  const mon = monthDate.value.getMonth();
  const count = new Date(year, mon + 1, 0).getDate();
  const offset = (new Date(year, mon, 1).getDay() + 6) % 7;
  return [
    ...Array.from({ length:offset }, (_, i) => ({ key:`empty-${i}`, empty:true })),
    ...Array.from({ length:count }, (_, i) => {
      const day = i + 1;
      const iso = `${month.value}-${String(day).padStart(2, '0')}`;
      return { key:iso, day, iso };
    }),
  ];
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get('/api/announcements/duty/', { params:{ month:month.value } });
    selected.value = new Set(data.dates);
    noDuty.value = data.has_no_duty;
  } finally { loading.value = false; }
}

function toggle(iso) {
  if (noDuty.value) return;
  const next = new Set(selected.value);
  next.has(iso) ? next.delete(iso) : next.add(iso);
  selected.value = next;
}

function toggleNoDuty() {
  noDuty.value = !noDuty.value;
  if (noDuty.value) selected.value = new Set();
}

async function save() {
  saving.value = true;
  try {
    await http.put('/api/announcements/duty/', {
      month:month.value, has_no_duty:noDuty.value, dates:[...selected.value].sort(),
    });
    toast.success('Nöbet bilgisi kaydedildi.');
  } finally { saving.value = false; }
}

watch(month, async () => {
  await router.replace({ query:{ month:month.value } });
  await load();
});
onMounted(load);
</script>

<template>
  <div class="eisa-page pharm-page duty-page">
    <div class="eisa-page-header">
      <div><p class="eisa-eyebrow">ECZACI / NÖBET TAKVİMİ</p><h1 class="eisa-page-title">Nöbet Günleri</h1><p class="eisa-page-subtitle">Nöbet günlerinizi seçin veya bu ay nöbetiniz olmadığını belirtin.</p></div>
      <div class="eisa-header-actions"><input v-model="month" type="month" class="drawer-input"><button class="eisa-btn eisa-btn-primary" :disabled="saving" @click="save"><i class="fa-solid fa-floppy-disk"></i> Kaydet</button></div>
    </div>
    <div class="eisa-panel duty-panel">
      <div class="duty-panel-head"><h2>{{ monthLabel }}</h2><button class="no-duty-toggle" :class="{ active:noDuty }" @click="toggleNoDuty"><i class="fa-solid" :class="noDuty ? 'fa-square-check' : 'fa-square'"></i> Bu Ay Nöbetim Yok</button></div>
      <div v-if="loading" class="duty-loading"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
      <template v-else>
        <div class="weekday-row"><span v-for="label in ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz']" :key="label">{{ label }}</span></div>
        <div class="calendar-grid">
          <button v-for="item in days" :key="item.key" :disabled="item.empty || noDuty" :class="['calendar-day', { empty:item.empty, selected:selected.has(item.iso) }]" @click="toggle(item.iso)"><template v-if="!item.empty"><span>{{ item.day }}</span><small v-if="selected.has(item.iso)">Nöbet</small></template></button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.duty-panel { max-width:850px; margin:auto; padding:1.5rem; }
.duty-panel-head { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.duty-panel-head h2 { text-transform:capitalize; }
.no-duty-toggle { border:1px solid #d1d5db; border-radius:9px; padding:.65rem .85rem; background:#fff; color:#4b5563; cursor:pointer; font-weight:650; }
.no-duty-toggle.active { color:#fff; background:#334155; border-color:#334155; }
.weekday-row,.calendar-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:.45rem; }
.weekday-row span { text-align:center; color:#6b7280; font-size:.75rem; font-weight:700; padding:.5rem; }
.calendar-day { min-height:82px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; color:#111827; cursor:pointer; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.3rem; }
.calendar-day:hover:not(:disabled) { border-color:#b1121b; background:#fef2f2; }
.calendar-day.selected { background:#b1121b; border-color:#b1121b; color:#fff; }
.calendar-day small { font-size:.65rem; font-weight:700; }
.calendar-day.empty { visibility:hidden; }
.calendar-day:disabled:not(.empty) { opacity:.4; cursor:not-allowed; }
.duty-loading { padding:4rem; text-align:center; }
@media(max-width:650px){.calendar-day{min-height:58px}.duty-panel-head{align-items:stretch;flex-direction:column}}
</style>
