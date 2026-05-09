<script setup>
/**
 * AdTimelineView — Kiosk + tarih + saat secimi ile 60sn loop'larin
 * Gantt-stili gorsellestirilmesi. Backend: GET /api/campaigns/v2/campaigns/timeline/
 */
import { computed, onMounted, ref, watch } from 'vue';
import { generatePlaylists, getCampaignTimeline, getInventoryAvailability } from '../../services/dooh';
import { getKioskStatus } from '../../services/devices';

const kiosks = ref([]);
const selectedKiosk = ref(null);
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const selectedHour = ref(18);
const loading = ref(false);
const generating = ref(false);
const error = ref('');
const flash = ref('');
const timeline = ref(null);   // { hour, loop_duration_seconds, loops: [{loop_index, items:[{order,asset_type,asset_label,offset,duration,color}]}] }
const availableSec = ref(null);

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const LOOP_SECONDS = 60;

async function loadKiosks() {
  try {
    const items = await getKioskStatus();
    kiosks.value = items.map((k) => ({
      id: k.id,
      label: k.pharmacyName ? `${k.pharmacyName} (#${k.id})` : `Kiosk #${k.id}`,
    }));
    if (!selectedKiosk.value && kiosks.value.length) {
      selectedKiosk.value = kiosks.value[0].id;
    }
  } catch (e) {
    error.value = 'Kiosk listesi yuklenemedi';
  }
}

async function loadTimeline() {
  if (!selectedKiosk.value) return;
  loading.value = true;
  error.value = '';
  try {
    const params = {
      kiosk: selectedKiosk.value,
      date: selectedDate.value,
      hour: selectedHour.value,
    };
    const [tl, av] = await Promise.all([
      getCampaignTimeline(params),
      getInventoryAvailability(params),
    ]);
    timeline.value = tl.data;
    availableSec.value = av.data?.available_seconds ?? null;
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Timeline yuklenemedi';
    timeline.value = null;
  } finally {
    loading.value = false;
  }
}

watch([selectedKiosk, selectedDate, selectedHour], loadTimeline);
onMounted(async () => {
  await loadKiosks();
  await loadTimeline();
});

async function regenerate(allKiosks = false) {
  if (!allKiosks && !selectedKiosk.value) return;
  generating.value = true;
  error.value = '';
  flash.value = '';
  try {
    const payload = { date: selectedDate.value };
    if (!allKiosks) payload.kiosk = selectedKiosk.value;
    const resp = await generatePlaylists(payload);
    const d = resp.data || {};
    flash.value = `${d.kiosk_count} kiosk icin ${d.playlists_generated} playlist uretildi (${d.target_date}).`;
    await loadTimeline();
  } catch (e) {
    error.value = e?.response?.data?.error || e?.response?.data?.detail || 'Playlist uretimi basarisiz';
  } finally {
    generating.value = false;
  }
}

// Loop bazli kullanim ozeti — backend dump flat items list, group by loop index
const loopSummary = computed(() => {
  const tl = timeline.value;
  if (!tl || !Array.isArray(tl.items) || tl.items.length === 0) return [];
  const loopSec = Number(tl.loop_duration_seconds) || LOOP_SECONDS;
  const groups = new Map();
  for (const item of tl.items) {
    const offsetAbs = Number(item.estimated_start_offset_seconds);
    const idx = Math.floor(offsetAbs / loopSec);
    if (!groups.has(idx)) groups.set(idx, []);
    groups.get(idx).push({
      asset_type: item.asset_type,
      asset_label: item.asset_id ? String(item.asset_id).slice(0, 8) : (item.media_url || '').split('/').pop(),
      offset: offsetAbs - idx * loopSec,
      duration: Number(item.duration_seconds) || 0,
      order: item.playback_order,
    });
  }
  return Array.from(groups.entries())
    .sort(([a], [b]) => a - b)
    .map(([loop_index, items]) => {
      const sorted = items.sort((a, b) => a.offset - b.offset);
      const used = sorted.reduce((s, it) => s + it.duration, 0);
      return { loop_index, used, free: Math.max(0, loopSec - used), items: sorted };
    });
});
</script>

<template>
  <section class="timeline-view">
    <header class="page-head">
      <div>
        <h1>Reklam Zaman Cizelgesi</h1>
        <p class="muted">60 sn'lik loop'lar icindeki slot dolulugu (Gantt gorunumu).</p>
      </div>
      <div v-if="availableSec !== null" class="avail-pill">
        Bu saat icin musait: <strong>{{ availableSec }}s</strong> / loop
      </div>
    </header>

    <div class="filters">
      <label>
        Kiosk
        <select v-model="selectedKiosk">
          <option v-for="k in kiosks" :key="k.id" :value="k.id">{{ k.label }}</option>
        </select>
      </label>
      <label>
        Tarih
        <input type="date" v-model="selectedDate" />
      </label>
      <label>
        Saat
        <select v-model.number="selectedHour">
          <option v-for="h in HOURS" :key="h" :value="h">{{ h.toString().padStart(2, '0') }}:00</option>
        </select>
      </label>
      <button class="btn" :disabled="loading" @click="loadTimeline">Yenile</button>
      <button class="btn btn-primary" :disabled="generating || !selectedKiosk" @click="regenerate(false)">
        {{ generating ? 'Uretiliyor...' : 'Bu Kiosk icin Playlist Uret' }}
      </button>
      <button class="btn btn-ghost" :disabled="generating" @click="regenerate(true)">
        Tum Kiosklar icin Uret
      </button>
    </div>

    <div v-if="flash" class="alert alert-success">{{ flash }}</div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-else-if="loading" class="muted">Yukleniyor...</div>
    <div v-else-if="!timeline || !loopSummary.length" class="muted">
      Bu zaman dilimi icin uretilmis bir playlist bulunamadi. Once
      <code>manage.py generate_playlists</code> komutunu calistirin.
    </div>

    <div v-else class="loops-grid">
      <article
        v-for="loop in loopSummary"
        :key="loop.loop_index"
        class="loop-card"
      >
        <header class="loop-head">
          <span class="loop-idx">Loop #{{ loop.loop_index + 1 }}</span>
          <span class="loop-meta">
            Kullanim: <strong>{{ loop.used }}s</strong>
            / Bos: <strong>{{ loop.free }}s</strong>
          </span>
        </header>

        <div class="gantt">
          <div class="gantt-axis">
            <span v-for="t in [0, 15, 30, 45, 60]" :key="t" :style="{ left: (t / 60 * 100) + '%' }">
              {{ t }}s
            </span>
          </div>
          <div class="gantt-track">
            <div
              v-for="(item, i) in loop.items"
              :key="i"
              class="gantt-bar"
              :class="'bar-' + (item.asset_type || 'creative')"
              :style="{
                left: (item.offset / 60 * 100) + '%',
                width: (item.duration / 60 * 100) + '%',
                background: item.color || undefined,
              }"
              :title="`${item.asset_label} • ${item.duration}s @ ${item.offset}s`"
            >
              <span>{{ item.asset_label }} ({{ item.duration }}s)</span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.timeline-view { padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }
.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; flex-wrap: wrap; }
.page-head h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
.muted { color: #6b7280; }
.avail-pill { background: #ecfeff; color: #075985; padding: .5rem .9rem; border-radius: 999px; font-size: .9rem; }

.filters { display: flex; gap: .9rem; align-items: end; flex-wrap: wrap; padding: .75rem 1rem; background: #f8fafc; border-radius: 12px; }
.filters label { display: flex; flex-direction: column; gap: .25rem; font-size: .8rem; color: #475569; }
.filters select, .filters input { padding: .4rem .6rem; border: 1px solid #cbd5e1; border-radius: 6px; background: white; }
.btn { padding: .5rem 1rem; background: #2563eb; color: white; border: 0; border-radius: 6px; cursor: pointer; }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.btn-primary { background: #16a34a; }
.btn-ghost { background: transparent; color: #2563eb; border: 1px solid #2563eb; }

.alert-error { background: #fee2e2; color: #991b1b; padding: .75rem 1rem; border-radius: 8px; }
.alert-success { background: #dcfce7; color: #166534; padding: .75rem 1rem; border-radius: 8px; }

.loops-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 1rem; }
.loop-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: .9rem; background: white; }
.loop-head { display: flex; justify-content: space-between; margin-bottom: .6rem; font-size: .9rem; }
.loop-idx { font-weight: 600; color: #1f2937; }
.loop-meta { color: #475569; }

.gantt { position: relative; }
.gantt-axis { position: relative; height: 18px; font-size: .7rem; color: #94a3b8; }
.gantt-axis span { position: absolute; transform: translateX(-50%); }
.gantt-track { position: relative; height: 36px; background: #f1f5f9; border-radius: 6px; overflow: hidden; }
.gantt-bar {
  position: absolute; top: 2px; bottom: 2px;
  background: #6366f1; color: white; font-size: .72rem;
  display: flex; align-items: center; justify-content: center;
  border-radius: 4px; padding: 0 4px; overflow: hidden; white-space: nowrap;
}
.gantt-bar.bar-house_ad { background: #94a3b8; }
.gantt-bar span { text-overflow: ellipsis; overflow: hidden; }
</style>
