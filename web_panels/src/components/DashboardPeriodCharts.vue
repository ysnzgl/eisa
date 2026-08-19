<script setup>
import { computed, ref, useSlots } from 'vue';
import DashboardPeriodCard from './DashboardPeriodCard.vue';

const props = defineProps({
  filters: { type: Object, default: () => ({}) },
  drillPath: { type: String, default: '/admin/kiosk-activities' },
});
const slots = useSlots();
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(new Date());
const currentMonth = today.slice(0, 7);
const month = ref(currentMonth);
const week = ref(today);

const parseDay = (value) => new Date(`${value}T12:00:00Z`);
const iso = (value) => value.toISOString().slice(0, 10);
const monday = (value) => {
  const day = parseDay(value);
  const weekday = day.getUTCDay() || 7;
  day.setUTCDate(day.getUTCDate() - weekday + 1);
  return iso(day);
};
const addDays = (value, count) => {
  const day = parseDay(value);
  day.setUTCDate(day.getUTCDate() + count);
  return iso(day);
};
const nextMonthDisabled = computed(() => month.value >= currentMonth);
const nextWeekDisabled = computed(() => monday(week.value) >= monday(today));
const hasAside = computed(() => Boolean(slots.aside));
const monthTitle = computed(() => parseDay(`${month.value}-01`).toLocaleDateString('tr-TR', {
  month: 'long', year: 'numeric', timeZone: 'Europe/Istanbul',
}));
const weekTitle = computed(() => {
  const weekStart = monday(week.value);
  const format = (value) => parseDay(value).toLocaleDateString('tr-TR', {
    day: '2-digit', month: 'short', timeZone: 'Europe/Istanbul',
  });
  return `${format(weekStart)} – ${format(addDays(weekStart, 6))}`;
});

function moveMonth(delta) {
  const [year, monthNumber] = month.value.split('-').map(Number);
  month.value = iso(new Date(Date.UTC(year, monthNumber - 1 + delta, 1, 12))).slice(0, 7);
}
function moveWeek(delta) {
  const day = parseDay(week.value);
  day.setUTCDate(day.getUTCDate() + delta * 7);
  week.value = iso(day);
}
</script>

<template>
  <section class="period-analytics" :class="{ 'period-analytics--with-aside': hasAside }">
    <div class="period-layout">
      <section class="eisa-panel period-column period-column--monthly">
        <header class="eisa-panel-header period-column-header">
          <div><p class="eisa-eyebrow">AYLIK ANALİTİK</p><h2 class="eisa-panel-title">{{ monthTitle }}</h2></div>
          <div class="period-nav" aria-label="Ay seçimi">
            <button class="eisa-btn eisa-btn-ghost" type="button" title="Önceki ay" aria-label="Önceki ay" @click="moveMonth(-1)"><i class="fa-solid fa-chevron-left"></i></button>
            <button class="eisa-btn eisa-btn-ghost period-current" type="button" title="Güncel aya dön" aria-label="Güncel aya dön" @click="month = currentMonth"><i class="fa-solid fa-calendar-day"></i></button>
            <button class="eisa-btn eisa-btn-ghost" type="button" title="Sonraki ay" aria-label="Sonraki ay" :disabled="nextMonthDisabled" @click="moveMonth(1)"><i class="fa-solid fa-chevron-right"></i></button>
          </div>
        </header>
        <DashboardPeriodCard period="month" kind="interactions" :value="month" :filters="filters" :drill-path="drillPath" />
        <DashboardPeriodCard period="month" kind="sales" :value="month" :filters="filters" :drill-path="drillPath" />
      </section>

      <section class="eisa-panel period-column period-column--weekly">
        <header class="eisa-panel-header period-column-header">
          <div><p class="eisa-eyebrow">HAFTALIK ANALİTİK</p><h2 class="eisa-panel-title">{{ weekTitle }}</h2></div>
          <div class="period-nav" aria-label="Hafta seçimi">
            <button class="eisa-btn eisa-btn-ghost" type="button" title="Önceki hafta" aria-label="Önceki hafta" @click="moveWeek(-1)"><i class="fa-solid fa-chevron-left"></i></button>
            <button class="eisa-btn eisa-btn-ghost period-current" type="button" title="Güncel haftaya dön" aria-label="Güncel haftaya dön" @click="week = today"><i class="fa-solid fa-calendar-week"></i></button>
            <button class="eisa-btn eisa-btn-ghost" type="button" title="Sonraki hafta" aria-label="Sonraki hafta" :disabled="nextWeekDisabled" @click="moveWeek(1)"><i class="fa-solid fa-chevron-right"></i></button>
          </div>
        </header>
        <DashboardPeriodCard period="week" kind="interactions" :value="week" :filters="filters" :drill-path="drillPath" />
        <DashboardPeriodCard period="week" kind="sales" :value="week" :filters="filters" :drill-path="drillPath" />
      </section>

      <aside v-if="hasAside" class="period-column period-column--aside"><slot name="aside" /></aside>
    </div>
  </section>
</template>

<style scoped>
.period-analytics { margin-bottom: 1.5rem; }
.period-layout { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; align-items: start; }
.period-analytics--with-aside .period-layout { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.period-analytics--with-aside .period-column--monthly { grid-column: 1 / -1; }
.period-column { display: flex; flex-direction: column; min-width: 0; }
.period-column--monthly,.period-column--weekly { overflow: hidden; }
.period-column--aside { gap: 1rem; }
.period-column-header { min-height: 54px; padding: 1rem; display: flex; align-items: flex-end; justify-content: space-between; gap: .75rem; }
.period-column-header .eisa-eyebrow { margin-bottom: .3rem; }
.period-column-header .eisa-panel-title { font-size: .9rem; text-transform: capitalize; }
.period-nav { display: flex; gap: .3rem; flex-shrink: 0; }
.period-nav .eisa-btn { width: 34px; min-width: 34px; height: 34px; padding: 0; display: inline-grid; place-items: center; font-size: .75rem; }
.period-nav .period-current { color: var(--eisa-red); }
.period-column--weekly .period-column-header { min-width: 0; align-items: center; flex-wrap: nowrap; }
.period-column--weekly .period-column-header > div:first-child { min-width: 0; }
.period-column--weekly .period-column-header .eisa-panel-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.period-column--weekly .period-nav { margin-left: auto; }
@media (max-width: 1450px) {
  .period-column--monthly .period-column-header { min-height: 82px; align-items: flex-start; flex-direction: column; }
}
@media (max-width: 1180px) {
  .period-layout,.period-analytics--with-aside .period-layout { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 760px) {
  .period-layout,.period-analytics--with-aside .period-layout { grid-template-columns: 1fr; }
  .period-analytics--with-aside .period-column--monthly { grid-column: auto; }
  .period-column-header { min-height: 0; }
}
</style>
