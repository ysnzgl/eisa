<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { getDashboardSeries } from '../services/analytics';
const props = defineProps({ filters: { type: Object, default: () => ({}) } });
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(new Date());
const currentMonth = today.slice(0, 7); const month = ref(currentMonth); const week = ref(today);
const data = ref(null); const loading = ref(false);
const parseDay = value => new Date(`${value}T12:00:00Z`); const iso = value => value.toISOString().slice(0, 10);
function moveMonth(delta) { const [y,m]=month.value.split('-').map(Number); month.value=iso(new Date(Date.UTC(y,m-1+delta,1,12))).slice(0,7); }
function moveWeek(delta) { const d=parseDay(week.value); d.setUTCDate(d.getUTCDate()+delta*7); week.value=iso(d); }
const monday = value => { const d=parseDay(value); const n=d.getUTCDay()||7; d.setUTCDate(d.getUTCDate()-n+1); return iso(d); };
const nextMonthDisabled=computed(()=>month.value>=currentMonth); const nextWeekDisabled=computed(()=>monday(week.value)>=monday(today));
const monthTitle=computed(()=>parseDay(`${month.value}-01`).toLocaleDateString('tr-TR',{month:'long',year:'numeric',timeZone:'Europe/Istanbul'}));
const fmt=value=>parseDay(value).toLocaleDateString('tr-TR',{day:'2-digit',month:'short',timeZone:'Europe/Istanbul'});
const weekTitle=computed(()=>data.value?`${fmt(data.value.week_start)} – ${fmt(data.value.week_end)}`:'');
const maxOf=items=>Math.max(1,...(items||[]).map(item=>item.value));
const label=(item,weekly)=>weekly?parseDay(item.date).toLocaleDateString('tr-TR',{weekday:'short',timeZone:'Europe/Istanbul'}):String(Number(item.date.slice(-2)));
async function load(){loading.value=true;try{data.value=(await getDashboardSeries({...props.filters,month:month.value,week:week.value})).data;}finally{loading.value=false;}}
watch([month,week,()=>props.filters],load,{deep:true}); onMounted(load);
const cards=computed(()=>data.value?[
  {key:'monthly_interactions',title:'Aylık Gün Gün Etkileşim',period:monthTitle.value,rows:data.value.monthly_interactions,weekly:false},
  {key:'monthly_sales',title:'Aylık Gün Gün Satış',period:monthTitle.value,rows:data.value.monthly_sales,weekly:false},
  {key:'weekly_interactions',title:'Haftalık Gün Gün Etkileşim',period:weekTitle.value,rows:data.value.weekly_interactions,weekly:true},
  {key:'weekly_sales',title:'Haftalık Gün Gün Satış',period:weekTitle.value,rows:data.value.weekly_sales,weekly:true},
]:[]);
</script>
<template><section class="period-analytics">
  <div class="period-toolbar"><div><button class="eisa-btn eisa-btn-ghost" @click="moveMonth(-1)">‹ Önceki Ay</button><button class="eisa-btn eisa-btn-ghost" @click="month=currentMonth">Güncel Ay</button><button class="eisa-btn eisa-btn-ghost" :disabled="nextMonthDisabled" @click="moveMonth(1)">Sonraki Ay ›</button></div><div><button class="eisa-btn eisa-btn-ghost" @click="moveWeek(-1)">‹ Önceki Hafta</button><button class="eisa-btn eisa-btn-ghost" @click="week=today">Güncel Hafta</button><button class="eisa-btn eisa-btn-ghost" :disabled="nextWeekDisabled" @click="moveWeek(1)">Sonraki Hafta ›</button></div></div>
  <div v-if="loading&&!data" class="period-loading">Grafikler yükleniyor…</div><div v-else class="period-grid"><article v-for="card in cards" :key="card.key" class="eisa-panel period-card"><header><div><h3>{{card.title}}</h3><p>{{card.period}}</p></div><strong>Toplam {{data.totals[card.key].toLocaleString('tr-TR')}}</strong></header><div class="period-bars" :class="{weekly:card.weekly}"><div v-for="item in card.rows" :key="item.date" class="period-bar-cell" :title="`${item.date}: ${item.value}`"><span>{{item.value}}</span><i :style="{height:`${Math.max(2,item.value/maxOf(card.rows)*100)}%`}"></i><small>{{label(item,card.weekly)}}</small></div></div></article></div>
</section></template>
<style scoped>
.period-analytics{margin-bottom:1.5rem}.period-toolbar{display:flex;justify-content:space-between;gap:1rem;margin-bottom:.75rem}.period-toolbar>div{display:flex;gap:.35rem}.period-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.period-card{padding:1rem;min-width:0}.period-card header{display:flex;justify-content:space-between;gap:1rem;margin-bottom:1rem}.period-card h3{font-size:.92rem;margin:0}.period-card p{font-size:.75rem;color:#6B7280;margin:.2rem 0 0;text-transform:capitalize}.period-card strong{font-size:.78rem;color:#0F8F8A;white-space:nowrap}.period-bars{height:180px;display:grid;grid-template-columns:repeat(31,minmax(5px,1fr));gap:3px;align-items:end}.period-bars.weekly{grid-template-columns:repeat(7,1fr);gap:10px}.period-bar-cell{height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;min-width:0}.period-bar-cell i{display:block;width:100%;max-width:22px;background:linear-gradient(#0F8F8A,#0C7773);border-radius:4px 4px 0 0;min-height:2px}.period-bar-cell span,.period-bar-cell small{font-size:.58rem;color:#6B7280}.period-bar-cell small{margin-top:4px}.period-loading{text-align:center;padding:3rem;color:#6B7280}@media(max-width:900px){.period-grid{grid-template-columns:1fr}.period-toolbar{flex-direction:column}.period-toolbar>div{flex-wrap:wrap}.period-bars{height:150px}}
</style>
