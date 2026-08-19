<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { getDashboardSeries } from '../services/analytics';

const props = defineProps({
  period: { type: String, required: true, validator: (value) => ['month', 'week'].includes(value) },
  kind: { type: String, required: true, validator: (value) => ['interactions', 'sales'].includes(value) },
  value: { type: String, required: true },
  filters: { type: Object, default: () => ({}) },
  drillPath: { type: String, default: '/admin/kiosk-activities' },
});

const router = useRouter();
const data = ref(null);
const loading = ref(true);
const ready = ref(false);
const loadError = ref(false);

const key = computed(() => `${props.period}ly_${props.kind}`);
const title = computed(() => `${props.period === 'month' ? 'Aylık' : 'Haftalık'} ${props.kind === 'sales' ? 'Satış' : 'Etkileşim'}`);
const eyebrow = computed(() => props.kind === 'sales' ? 'SATIŞLAR' : 'QR ETKİLEŞİMLERİ');
const isMonthly = computed(() => props.period === 'month');
const metrics = computed(() => props.kind === 'sales'
  ? [
      { key: 'recommended', label: 'Önerilen', colorClass: 'chart-metric--recommended' },
      { key: 'sold', label: 'Satılan', colorClass: 'chart-metric--sold' },
    ]
  : [
      { key: 'pending', label: 'Bekleyen', colorClass: 'chart-metric--pending' },
      { key: 'sold', label: 'Satış Yapılan', colorClass: 'chart-metric--sold' },
      { key: 'not_sold', label: 'Satış Yapılmayan', colorClass: 'chart-metric--not-sold' },
    ]
);
const rows = computed(() => data.value?.[key.value] ?? []);
const maxValue = computed(() => Math.max(1, ...rows.value.flatMap((item) => metrics.value.map((metric) => item[metric.key] ?? 0))));
const total = (metric) => rows.value.reduce((sum, item) => sum + (item[metric.key] ?? 0), 0);
const interactionTotal = computed(() => rows.value.reduce((sum, item) => sum + (item.value ?? 0), 0));

function parseDay(value) { return new Date(`${value}T12:00:00Z`); }
function itemLabel(item) {
  return isMonthly.value
    ? String(Number(item.date.slice(-2)))
    : parseDay(item.date).toLocaleDateString('tr-TR', { weekday: 'short', timeZone: 'Europe/Istanbul' });
}
function openDrill(item) {
  router.push({
    path: props.drillPath,
    query: {
      tab: props.kind === 'sales' ? 'sales' : 'sessions',
      start_date: item.date,
      end_date: item.date,
      ...props.filters,
    },
  });
}
async function load() {
  loading.value = true;
  loadError.value = false;
  ready.value = false;
  try {
    const params = { ...props.filters, [props.period]: props.value };
    data.value = (await getDashboardSeries(params)).data;
    await nextTick();
    ready.value = true;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

watch(() => [props.period, props.kind, props.value, JSON.stringify(props.filters)], load, { immediate: true });
</script>

<template>
  <article class="period-card" :class="[`period-card--${period}`, { 'period-card--ready': ready }]">
    <header class="eisa-panel-header period-card-header">
      <div><p class="eisa-eyebrow">{{ eyebrow }}</p><h3 class="eisa-panel-title">{{ title }}</h3></div>
      <div class="period-summary" :class="`period-summary--${kind}`">
        <span v-if="kind === 'interactions'" class="period-total-badge">Toplam {{ interactionTotal.toLocaleString('tr-TR') }}</span>
        <span v-for="metric in metrics" :key="metric.key"><i class="period-legend-dot" :class="metric.colorClass"></i>{{ total(metric).toLocaleString('tr-TR') }} {{ metric.label }}</span>
      </div>
    </header>

    <div v-if="loading && !data" class="period-card-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor</div>
    <div v-else-if="loadError && !data" class="period-card-loading period-card-loading--error">Veri yüklenemedi.</div>
    <div v-else class="period-bars" :class="{ 'period-bars--monthly': isMonthly, 'period-bars--weekly': !isMonthly }">
      <span v-if="loading" class="period-refreshing" title="Veriler güncelleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></span>
      <button
        v-for="item in rows"
        :key="item.date"
        type="button"
        class="period-bar-cell"
        :class="{ 'period-bar-cell--multi': metrics.length > 1 }"
        :title="`${item.date}: ${metrics.map((metric) => `${item[metric.key] ?? 0} ${metric.label}`).join(', ')} — detaya git`"
        @click="openDrill(item)"
      >
        <strong class="period-bar-values" :class="{ 'period-bar-values--empty': !metrics.some((metric) => item[metric.key]) }">
          <template v-if="metrics.some((metric) => item[metric.key])">
            <span v-for="metric in metrics" :key="metric.key" :class="metric.colorClass">{{ item[metric.key] ?? 0 }}</span>
          </template>
          <span v-else class="period-zero-value">—</span>
        </strong>
        <span class="period-bar-track">
          <template v-for="metric in metrics" :key="metric.key">
            <i
              v-if="item[metric.key]"
              class="period-bar"
              :class="metric.colorClass"
              :style="{ height: `${Math.max(2, ((item[metric.key] ?? 0) / maxValue) * 100)}%` }"
            ></i>
          </template>
        </span>
        <small>{{ itemLabel(item) }}</small>
      </button>
    </div>
  </article>
</template>

<style scoped>
.period-card { min-width: 0; overflow: hidden; border-top: 1px solid #E5E3DF; }
.period-card:first-child { border-top: 0; }
.period-card-header { padding: .8rem 1rem .45rem; border: 0; gap: .5rem; }
.period-card-header .eisa-eyebrow { font-size: .61rem; margin-bottom: .22rem; }
.period-card-header .eisa-panel-title { font-size: .9rem; font-weight: 800; }
.period-summary { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .3rem .55rem; color: #374151; font-size: .64rem; font-weight: 800; }
.period-summary span { display: inline-flex; align-items: center; gap: .25rem; white-space: nowrap; }
.period-summary .period-total-badge { color: #fff; background: var(--eisa-red); border-radius: 999px; padding: .18rem .45rem; }
.period-legend-dot { width: 7px; height: 7px; border-radius: 50%; }
.chart-metric--recommended { color: #D97706; background-color: #D97706; }
.chart-metric--sold { color: var(--eisa-turquoise); background-color: var(--eisa-turquoise); }
.chart-metric--pending { color: #D97706; background-color: #D97706; }
.chart-metric--not-sold { color: var(--eisa-red); background-color: var(--eisa-red) }
.period-summary .chart-metric--recommended,
.period-summary .chart-metric--sold,
.period-summary .chart-metric--pending,
.period-summary .chart-metric--not-sold { flex: 0 0 auto; }
.period-card-loading { min-height: 170px; display: grid; place-items: center; gap: .5rem; color: #6B7280; font-size: .75rem; font-weight: 700; }
.period-card-loading--error { color: var(--eisa-red); }
.period-bars { position: relative; display: grid; align-items: stretch; height: 180px; padding: .25rem .8rem .85rem; }
.period-refreshing { position: absolute; right: .9rem; bottom: .75rem; color: #94A3B8; font-size: .72rem; }
.period-bars--monthly { grid-template-columns: repeat(31, minmax(5px, 1fr)); gap: 2px; }
.period-bars--weekly { grid-template-columns: repeat(7, minmax(22px, 1fr)); gap: 7px; }
.period-bar-cell { min-width: 0; padding: 2px 0 0; border: 0; background: transparent; display: grid; grid-template-rows: 22px minmax(0, 1fr) 16px; align-items: stretch; font: inherit; cursor: pointer; border-radius: 4px; transition: background .15s; }
.period-bar-cell:hover,.period-bar-cell:focus-visible { outline: none; background: var(--eisa-info-soft, #eef2ff); }
.period-bar-values { display: flex; align-items: center; justify-content: center; gap: 2px; min-width: 0; color: #111827; font-family: 'DM Mono', monospace; font-size: .7rem; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.period-bar-values span { background: transparent; }
.period-bar-values--empty { color: #CBD5E1; font-size: .62rem; }
.period-zero-value { color: #CBD5E1; }
.period-bar-cell--multi .period-bar-values span + span::before { content: '/'; margin-right: 2px; color: #94A3B8; font-weight: 700; }
.period-bar-track { min-height: 0; display: flex; align-items: flex-end; justify-content: center; gap: 1px; padding: 0 1px; }
.period-bar { display: block; width: 100%; max-width: 8px; min-height: 2px; border-radius: 4px 4px 0 0; transform-origin: bottom; animation: bar-rise .45s ease-out both; }
.period-bars--weekly .period-bar { max-width: 15px; }
.period-card--ready .period-bar:nth-child(1) { animation-delay: .02s; }
.period-bar-cell:hover .period-bar { filter: brightness(.82); }
.period-bar-cell small { margin-top: 3px; color: #374151; font-size: .63rem; font-weight: 800; line-height: 1; }
.period-bars--weekly .period-bar-values { font-size: .78rem; }
.period-bars--weekly .period-bar-cell small { font-size: .7rem; }
@keyframes bar-rise { from { transform: scaleY(.05); opacity: .2; } to { transform: scaleY(1); opacity: 1; } }
@media (max-width: 760px) { .period-bars { height: 150px; } }
</style>
