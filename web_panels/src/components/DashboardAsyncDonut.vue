<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { getAdminDashboard } from '../services/analytics';

const props = defineProps({
  kind: { type: String, required: true, validator: (value) => ['categories', 'pharmacies', 'ingredients', 'recommended-ingredients'].includes(value) },
  eyebrow: { type: String, required: true },
  title: { type: String, required: true },
  filters: { type: Object, default: () => ({}) },
});

const CIRC = 2 * Math.PI * 70;
const COLORS = ['#B1121B', '#0F8F8A', '#7C3AED', '#D97706', '#64748B', '#2563EB', '#DB2777', '#65A30D', '#0891B2', '#92400E'];
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const ready = ref(false);
const loadError = ref(false);

const sourceRows = computed(() => {
  if (props.kind === 'categories') return (data.value?.kategori_dagilim ?? []).filter((row) => row.sayi > 0 && String(row.ad ?? '').trim());
  if (props.kind === 'pharmacies') return data.value?.satis_yapan_eczaneler ?? [];
  if (props.kind === 'recommended-ingredients') return data.value?.onerilen_etken_madde_dagilimi ?? [];
  return data.value?.satilan_etken_madde_dagilimi ?? [];
});
const unit = computed(() => props.kind === 'categories' ? 'oturum' : props.kind === 'pharmacies' ? 'satış' : props.kind === 'recommended-ingredients' ? 'öneri' : 'ürün');
const total = computed(() => sourceRows.value.reduce((sum, row) => sum + row.sayi, 0));
const segments = computed(() => {
  const denominator = total.value || 1;
  let cumulative = 0;
  return sourceRows.value.slice(0, 10).map((row, index) => {
    const pct = Math.round((row.sayi / denominator) * 100);
    const segment = {
      id: row.id ?? row.ad,
      label: row.ad,
      count: row.sayi,
      pct,
      dash: (pct / 100) * CIRC,
      rotate: (cumulative / denominator) * 360,
      color: COLORS[index],
      slug: row.slug ?? null,
    };
    cumulative += row.sayi;
    return segment;
  });
});
function drill(segment) {
  if (props.kind === 'categories') {
    router.push({ path: '/admin/kiosk-activities', query: { tab: 'sessions', ...(segment.slug ? { kategori_slug: segment.slug } : {}) } });
  } else if (props.kind === 'pharmacies') {
    router.push({ path: '/admin/kiosk-activities', query: { tab: 'sales', eczane_id: segment.id } });
  } else if (props.kind === 'recommended-ingredients') {
    router.push({ path: '/admin/kiosk-activities', query: { tab: 'sessions' } });
  } else {
    router.push({ path: '/admin/kiosk-activities', query: { tab: 'sales' } });
  }
}
async function load() {
  loading.value = true;
  loadError.value = false;
  ready.value = false;
  try {
    data.value = (await getAdminDashboard(props.filters)).data;
    await nextTick();
    ready.value = true;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}
watch(() => JSON.stringify(props.filters), load, { immediate: true });
</script>

<template>
  <article class="eisa-panel dash-donut-panel" :class="{ 'dash-donut-panel--ready': ready }">
    <div class="eisa-panel-header"><div><p class="eisa-eyebrow">{{ eyebrow }}</p><h2 class="eisa-panel-title">{{ title }}</h2></div></div>
    <div v-if="loading" class="dash-donut-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor</div>
    <div v-else-if="loadError" class="dash-donut-loading dash-donut-loading--error">Veri yüklenemedi.</div>
    <div v-else class="dash-donut-body">
      <div class="dash-donut-wrap">
        <svg viewBox="0 0 200 200" class="dash-donut-svg">
          <g transform="rotate(-90, 100, 100)">
            <circle
              v-for="(segment, index) in segments"
              :key="segment.id"
              cx="100" cy="100" r="70" fill="none" :stroke="segment.color" stroke-width="30"
              :stroke-dasharray="`${segment.dash.toFixed(2)} ${(CIRC - segment.dash).toFixed(2)}`"
              :transform="`rotate(${segment.rotate}, 100, 100)`"
              class="dash-donut-arc" :style="{ animationDelay: `${index * 90}ms` }" @click="drill(segment)"
            />
          </g>
          <text x="100" y="95" text-anchor="middle" class="dash-donut-big">{{ total > 999 ? `${(total / 1000).toFixed(1)}k` : total }}</text>
          <text x="100" y="111" text-anchor="middle" class="dash-donut-sub">{{ unit }}</text>
        </svg>
      </div>
      <div class="dash-donut-legend">
        <button v-for="segment in segments" :key="segment.id" type="button" class="dash-dl-row dash-dl-button" @click="drill(segment)">
          <span class="dash-dl-dot" :style="{ background: segment.color }"></span><span class="dash-dl-name">{{ segment.label }}</span><span class="dash-dl-pct">{{ kind === 'categories' ? `${segment.pct}%` : segment.count }}</span>
        </button>
        <p v-if="!segments.length" class="dash-donut-empty">Henüz veri yok.</p>
      </div>
    </div>
  </article>
</template>

<style scoped>
.dash-donut-panel { min-width: 0; animation: donut-panel-in .35s ease-out both; }
.dash-donut-loading { min-height: 112px; display: grid; place-items: center; color: #6B7280; font-size: .75rem; font-weight: 700; }
.dash-donut-loading--error { color: var(--eisa-red); }
.dash-donut-body { display: flex; align-items: center; gap: .8rem; padding: 0 1rem .9rem; }
.dash-donut-wrap { flex-shrink: 0; width: 96px; height: 96px; }
.dash-donut-svg { width: 100%; height: 100%; overflow: visible; }
.dash-donut-arc { cursor: pointer; transform-origin: 100px 100px; animation: donut-enter .5s ease-out both; }
.dash-donut-big { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 700; fill: #111827; }
.dash-donut-sub { font-size: 10px; fill: #6B7280; }
.dash-donut-legend { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: .28rem; }
.dash-dl-button { width: 100%; padding: .15rem 0; border: 0; background: transparent; display: flex; align-items: center; gap: .4rem; text-align: left; cursor: pointer; border-radius: 5px; font: inherit; }
.dash-dl-button:hover,.dash-dl-button:focus-visible { outline: none; background: var(--eisa-info-soft, #eef2ff); }
.dash-dl-dot { width: 8px; height: 8px; flex: 0 0 8px; border-radius: 50%; }
.dash-dl-name { min-width: 0; flex: 1; overflow: hidden; color: #374151; font-size: .75rem; text-overflow: ellipsis; white-space: nowrap; }
.dash-dl-pct { color: #111827; font-family: 'DM Mono', monospace; font-size: .72rem; font-weight: 700; }
.dash-donut-empty { margin: 0; color: #9CA3AF; font-size: .72rem; }
@keyframes donut-enter { from { opacity: .15; transform: scale(.88); } to { opacity: 1; transform: scale(1); } }
@keyframes donut-panel-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
</style>
