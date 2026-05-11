<script setup>
/**
 * Kampanya Yönetim Sihirbazı (DOOH v2 — İl/İlçe/Eczane ağaç hedefleme)
 * Adımlar:
 *   1) Kampanya bilgileri  (ad, reklamveren, tarih, durum)
 *   2) Medyalar             (creative yükle, süre seç)
 *   3) Frekans & Pacing     (PER_LOOP / PER_HOUR / PER_DAY + impression hedefi)
 *   4) Hedefleme            (İl → İlçe → Eczane ağaç seçimi)
 *   5) Önizle & Kaydet      (özet + fiyat)
 */
import { ref, reactive, computed, onMounted } from 'vue';
import {
  listCampaignsV2, createCampaignV2, updateCampaignV2, deleteCampaignV2,
  bulkActionCampaignsV2,
  getCampaignRules, setCampaignRules, createCreative, uploadMedia,
  getPricingMatrix,
} from '../../services/dooh.js';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import DateRangePicker from '../../components/shared/DateRangePicker.vue';
import { toast } from 'vue-sonner';

const campaigns = ref([]);
const loading   = ref(false);
const saving    = ref(false);
const wizardOpen = ref(false);
const editingId  = ref(null);
const step       = ref(1);
const stepError  = ref('');   // per-step inline error shown below footer

const TOTAL_STEPS = 4;
const STEP_LABELS = ['Bilgiler', 'Medya', 'Frekans', 'Özet & Kaydet'];

const empty = () => ({
  name: '',
  advertiser_name: '',
  start_date: '',
  end_date: '',
  status: 'ACTIVE',
  impression_goal: null,
  creatives: [],
  rule: { frequency_type: 'PER_LOOP', frequency_value: 1, target_hours: null },
});
const form = reactive(empty());

// Pacing mode — purely UI, not sent to backend
const pacingMode = ref('FREQUENCY'); // 'FREQUENCY' | 'GOAL'

const filterStatus = ref('ALL');
const searchQuery  = ref('');
const sortKey      = ref('updated');     // 'name' | 'advertiser' | 'start' | 'updated'
const sortDir      = ref('desc');        // 'asc' | 'desc'
const selectedIds  = ref(new Set());

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey.value = key;
    sortDir.value = 'asc';
  }
}

const filteredCampaigns = computed(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase('tr');
  let rows = campaigns.value.filter((c) => {
    if (filterStatus.value !== 'ALL' && c.status !== filterStatus.value) return false;
    if (!q) return true;
    const hay = `${c.name || ''} ${c.advertiser_name || ''}`.toLocaleLowerCase('tr');
    return hay.includes(q);
  });

  const dir = sortDir.value === 'asc' ? 1 : -1;
  const cmp = (a, b) => {
    let va, vb;
    switch (sortKey.value) {
      case 'name':       va = a.name || ''; vb = b.name || ''; break;
      case 'advertiser': va = a.advertiser_name || ''; vb = b.advertiser_name || ''; break;
      case 'start':      va = a.start_date || ''; vb = b.start_date || ''; break;
      default:           va = a.guncellenme_tarihi || a.olusturulma_tarihi || '';
                         vb = b.guncellenme_tarihi || b.olusturulma_tarihi || '';
    }
    return va < vb ? -1 * dir : va > vb ? 1 * dir : 0;
  };
  return [...rows].sort(cmp);
});

const allVisibleSelected = computed(() =>
  filteredCampaigns.value.length > 0 &&
  filteredCampaigns.value.every((c) => selectedIds.value.has(c.id))
);
const selectionCount = computed(() => selectedIds.value.size);

function toggleSelect(id) {
  const s = new Set(selectedIds.value);
  s.has(id) ? s.delete(id) : s.add(id);
  selectedIds.value = s;
}
function toggleSelectAll() {
  if (allVisibleSelected.value) {
    selectedIds.value = new Set();
  } else {
    selectedIds.value = new Set(filteredCampaigns.value.map((c) => c.id));
  }
}
function clearSelection() { selectedIds.value = new Set(); }

function thumbOf(c) {
  const cr = (c.creatives || []).find((x) => x.media_url);
  return cr?.media_url || '';
}
const stats = computed(() => ({
  total:     campaigns.value.length,
  active:    campaigns.value.filter((c) => c.status === 'ACTIVE').length,
  paused:    campaigns.value.filter((c) => c.status === 'PAUSED').length,
  completed: campaigns.value.filter((c) => c.status === 'COMPLETED').length,
}));

// ── Pricing matrix ─────────────────────────────────────────────────────────────
const pricingMatrix = ref(null);

onMounted(async () => {
  await refresh();
  try { const { data } = await getPricingMatrix(); pricingMatrix.value = data; } catch {}
});

async function refresh() {
  loading.value = true;
  try {
    const { data } = await listCampaignsV2();
    campaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Kampanyalar yüklenemedi.');
  } finally { loading.value = false; }
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, empty());
  step.value = 1; wizardOpen.value = true; stepError.value = '';
}

async function openEdit(c) {
  editingId.value = c.id;
  Object.assign(form, empty(), {
    name: c.name,
    advertiser_name: c.advertiser_name || '',
    start_date: c.start_date?.slice(0, 16) ?? '',
    end_date:   c.end_date?.slice(0, 16) ?? '',
    status: c.status,
    impression_goal: c.impression_goal ?? null,
    creatives: (c.creatives ?? []).map((cr) => ({
      id: cr.id, name: cr.name || 'Mevcut creative',
      duration_seconds: cr.duration_seconds, uploaded_url: cr.media_url,
    })),
  });
  try {
    const { data } = await getCampaignRules(c.id);
    if (data?.frequency_type) {
      form.rule = { id: data.id, frequency_type: data.frequency_type,
                    frequency_value: data.frequency_value, target_hours: data.target_hours };
      // If there's an impression goal, switch to GOAL mode
      if (form.impression_goal) pacingMode.value = 'GOAL';
    }
  } catch { /* keep default */ }
  step.value = 1; wizardOpen.value = true; stepError.value = '';
}

function close() { wizardOpen.value = false; }

function nextStep() {
  const err = validateStep(step.value);
  if (err) { stepError.value = err; return; }
  stepError.value = '';
  if (step.value < TOTAL_STEPS) step.value += 1;
}
function prev() { stepError.value = ''; if (step.value > 1) step.value -= 1; }

// ── Media helpers ─────────────────────────────────────────────────────────────
async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.creatives.push({ file, name: file.name, duration_seconds: 15, uploaded_url: data.url });
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}
function removeCreative(idx) { form.creatives.splice(idx, 1); }

// ── Frequency helpers ─────────────────────────────────────────────────────────
function toggleHour(rule, h) {
  const arr = Array.isArray(rule.target_hours) ? [...rule.target_hours] : [];
  const i = arr.indexOf(h);
  if (i >= 0) arr.splice(i, 1); else arr.push(h);
  arr.sort((a, b) => a - b);
  rule.target_hours = arr.length ? arr : null;
}

// ── Per-step validation ───────────────────────────────────────────────────────
function validateStep(n) {
  if (n === 1) {
    if (!form.name.trim()) return 'Kampanya adı zorunludur.';
    if (!form.start_date || !form.end_date) return 'Başlangıç ve bitiş tarihi zorunludur.';
    const now = new Date();
    const sd  = new Date(form.start_date);
    const ed  = new Date(form.end_date);
    if (sd < now) return 'Başlangıç tarihi geçmişte olamaz.';
    if (ed <= sd) return 'Bitiş tarihi başlangıçtan sonra olmalıdır.';
  }
  if (n === 2) {
    if (!form.creatives.length) return 'En az bir medya (creative) yüklemelisiniz.';
  }
  if (n === 3) {
    if (pacingMode.value === 'GOAL') {
      const goal = Number(form.impression_goal);
      if (!goal || goal < 1) return 'Gösterim hedefi en az 1 olmalıdır.';
      if (form.start_date && form.end_date) {
        const days = Math.max(1, Math.ceil((new Date(form.end_date) - new Date(form.start_date)) / 86400000));
        if (goal < days) return `Gösterim hedefi (${goal}) tarih aralığı gün sayısından (${days}) az olamaz — en az günde 1 gösterim gereklidir.`;
      }
    } else {
      if (!form.rule?.frequency_type) return 'Frekans tipi seçiniz.';
      const fv = Number(form.rule.frequency_value);
      if (!fv || fv < 1) return 'Frekans değeri en az 1 olmalıdır.';
      const max = maxFrequencyValue.value;
      if (fv > max) {
        const dur = form.creatives[0]?.duration_seconds ?? 15;
        const targetH = form.rule.target_hours ?? Array.from({ length: 24 }, (_, i) => i);
        const hours = targetH.length;
        if (form.rule.frequency_type === 'PER_LOOP')
          return `Loop kapasitesi aşıldı: ${fv} × ${dur} sn = ${fv * dur} sn > 60 sn. Maksimum ${max} kez.`;
        if (form.rule.frequency_type === 'PER_HOUR')
          return `Saatlik kapasite aşıldı: ${fv} × ${dur} sn > 3600 sn. Maksimum ${max} kez.`;
        if (form.rule.frequency_type === 'PER_DAY')
          return `Günlük kapasite aşıldı (${hours} hedef saat). Maksimum ${max} kez.`;
      }
    }
  }
  return null;
}

// ── Pacing helpers ─────────────────────────────────────────────────────────────

function _pacingBase() {
  if (!form.start_date || !form.end_date) return null;
  const sd = new Date(form.start_date);
  const ed = new Date(form.end_date);
  const days = Math.max(1, Math.ceil((ed - sd) / 86400000));
  const targetH = form.rule.target_hours ?? Array.from({ length: 24 }, (_, i) => i);
  const hours = Math.max(1, targetH.length);
  const dur = Number(form.creatives[0]?.duration_seconds ?? 15);
  return { days, hours, dur };
}

// FREQUENCY mode → estimated total impressions from current rule
const estimatedImpressions = computed(() => {
  const b = _pacingBase();
  if (!b) return null;
  const fv = Math.max(1, Number(form.rule.frequency_value ?? 1));
  let showsPerDay = 0;
  if (form.rule.frequency_type === 'PER_LOOP')      showsPerDay = fv * b.hours * 60;
  else if (form.rule.frequency_type === 'PER_HOUR') showsPerDay = fv * b.hours;
  else                                               showsPerDay = fv;
  return { showsPerDay: Math.round(showsPerDay), total: Math.round(showsPerDay * b.days), days: b.days };
});

// GOAL mode → daily distribution info (no frequency picker)
const goalDistribution = computed(() => {
  const goal = Number(form.impression_goal);
  const b = _pacingBase();
  if (!goal || goal < 1 || !b) return null;
  const showsPerDay = Math.ceil(goal / b.days);
  const showsPerHour = (showsPerDay / b.hours).toFixed(1);
  return { goal, days: b.days, showsPerDay, showsPerHour, hours: b.hours };
});

// Max frequency value per rule type (based on creative duration + target hours)
const maxFrequencyValue = computed(() => {
  const dur = Number(form.creatives[0]?.duration_seconds ?? 15);
  if (dur <= 0) return 999;
  const targetH = form.rule.target_hours ?? Array.from({ length: 24 }, (_, i) => i);
  const hours = targetH.length;
  if (form.rule.frequency_type === 'PER_LOOP') return Math.floor(60 / dur);
  if (form.rule.frequency_type === 'PER_HOUR') return Math.floor(3600 / dur);
  if (form.rule.frequency_type === 'PER_DAY')  return Math.floor(hours * 3600 / dur);
  return 999;
});

// ── Pricing tahmin ─────────────────────────────────────────────────────────────
const pricingEstimate = computed(() => {
  const pm = pricingMatrix.value;
  if (!pm || !form.creatives[0] || !form.start_date || !form.end_date) return null;
  const dur = Number(form.creatives[0]?.duration_seconds ?? 15);
  const targetH = form.rule.target_hours ?? Array.from({ length: 24 }, (_, i) => i);
  const hours = targetH.length;
  const sd = new Date(form.start_date);
  const ed = new Date(form.end_date);
  const days = Math.max(1, Math.ceil((ed - sd) / 86400000));

  let showsPerDay;
  if (pacingMode.value === 'GOAL' && form.impression_goal) {
    showsPerDay = Math.ceil(Number(form.impression_goal) / days);
  } else {
    const freqType = form.rule.frequency_type;
    const freqVal = Number(form.rule.frequency_value ?? 1);
    showsPerDay = freqType === 'PER_LOOP'
      ? freqVal * hours * 60
      : freqType === 'PER_HOUR'
      ? freqVal * hours
      : freqVal;
  }

  const totalShows = showsPerDay * days;
  const primeHours = pm.prime_hours ?? [];
  const primeCount = targetH.filter((h) => primeHours.includes(h)).length;
  const primeCoeff = Number(pm.prime_time_coefficient ?? 1.5);
  const freqMul = Number((pm.frequency_multipliers ?? {})[form.rule.frequency_type] ?? 1.0);
  const base = Number(pm.base_price_per_second ?? 1.0);
  const primeWeight = hours > 0 ? primeCount / hours : 0;
  const avgPrime = 1.0 + primeWeight * (primeCoeff - 1.0);
  const total = base * dur * freqMul * avgPrime * totalShows;

  return { total: total.toFixed(2), currency: pm.currency || 'TRY', totalShows, showsPerDay, days };
});

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  for (let i = 1; i <= TOTAL_STEPS - 1; i++) {
    const err = validateStep(i);
    if (err) { stepError.value = err; step.value = i; return; }
  }
  saving.value = true; stepError.value = '';
  try {
    const payload = {
      name: form.name,
      advertiser_name: form.advertiser_name || '',
      advertiser_id: null,
      start_date: new Date(form.start_date).toISOString(),
      end_date:   new Date(form.end_date).toISOString(),
      status: form.status,
      impression_goal: form.impression_goal || null,
    };
    let campaignId;
    if (editingId.value) {
      const { data } = await updateCampaignV2(editingId.value, payload);
      campaignId = data.id;
    } else {
      const { data } = await createCampaignV2(payload);
      campaignId = data.id;
    }

    for (const cr of form.creatives) {
      if (cr.id) continue;
      await createCreative({
        campaign: campaignId,
        media_url: cr.uploaded_url,
        duration_seconds: Number(cr.duration_seconds),
        name: cr.name?.slice(0, 120) || '',
      });
    }

    // In GOAL mode, auto-compute PER_DAY frequency from the goal
    const freqPayload = pacingMode.value === 'GOAL' && form.impression_goal && form.start_date && form.end_date
      ? (() => {
          const days = Math.max(1, Math.ceil(
            (new Date(form.end_date) - new Date(form.start_date)) / 86400000
          ));
          return {
            frequency_type:  'PER_DAY',
            frequency_value: Math.ceil(Number(form.impression_goal) / days),
            target_hours:    form.rule.target_hours,
          };
        })()
      : {
          frequency_type:  form.rule.frequency_type,
          frequency_value: Number(form.rule.frequency_value),
          target_hours:    form.rule.target_hours,
        };

    await setCampaignRules(campaignId, freqPayload);

    wizardOpen.value = false;
    await refresh();
    toast.success(`Kampanya ${editingId.value ? 'güncellendi' : 'oluşturuldu'}.`);
  } catch (e) {
    const msg = e?.response?.data?.detail || JSON.stringify(e?.response?.data || {}) || 'Kayıt başarısız.';
    toast.error(msg);
  } finally { saving.value = false; }
}

async function remove(c) {
  if (!confirm(`"${c.name}" kampanyası silinsin mi?`)) return;
  try {
    await deleteCampaignV2(c.id);
    await refresh();
    toast.success('Kampanya silindi.');
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Silme başarısız.');
  }
}

async function bulkRun(action) {
  const ids = Array.from(selectedIds.value);
  if (!ids.length) return;
  const verb = action === 'delete' ? 'silinsin'
            : action === 'pause'  ? 'duraklatılsın'
            : 'aktifleştirilsin';
  if (!confirm(`${ids.length} kampanya ${verb} mi?`)) return;
  try {
    const { data } = await bulkActionCampaignsV2(action, ids);
    clearSelection();
    await refresh();
    toast.success(`${data?.updated ?? ids.length} kampanya güncellendi.`);
  } catch (e) {
    toast.error(e?.response?.data?.error || e?.response?.data?.detail || 'Toplu işlem başarısız.');
  }
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const FREQ_TYPES = [
  { value: 'PER_LOOP', label: "Her loop'ta (60 sn)", help: "Değer=2 → her 60 saniyelik loop'ta 2 kez oynar." },
  { value: 'PER_HOUR', label: 'Saatte N kez',        help: 'Değer=4 → hedef saatlerde her saatte 4 kez oynar.' },
  { value: 'PER_DAY',  label: 'Günde N kez',         help: 'Değer=10 → gün boyunca toplam 10 kez oynar (rastgele dağıtılır).' },
];
const STATUS_LABELS = { ACTIVE: 'Aktif', PAUSED: 'Duraklatıldı', COMPLETED: 'Tamamlandı' };
</script>

<template>
  <div class="eisa-page campaign-wizard">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Reklam</p>
        <h1 class="eisa-page-title">Kampanyalar</h1>
        <p class="eisa-page-subtitle">DOOH reklam kampanyalarını oluştur ve frekansını ayarla.</p>
      </div>
      <div class="header-actions">
        <button class="eisa-btn" @click="refresh" :disabled="loading">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i> Yenile
        </button>
        <button class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni Kampanya
        </button>
      </div>
    </header>

    <section class="stats">
      <div class="stat-card"><span class="stat-label">Toplam</span><span class="stat-value">{{ stats.total }}</span></div>
      <div class="stat-card"><span class="stat-label">Aktif</span><span class="stat-value">{{ stats.active }}</span></div>
      <div class="stat-card"><span class="stat-label">Duraklatıldı</span><span class="stat-value">{{ stats.paused }}</span></div>
      <div class="stat-card"><span class="stat-label">Tamamlandı</span><span class="stat-value">{{ stats.completed }}</span></div>
    </section>

    <section class="eisa-panel toolbar-panel">
      <div class="toolbar" style="display:flex;flex-wrap:wrap;gap:.75rem;align-items:center">
        <div class="eisa-search" style="flex:1;min-width:240px;position:relative">
          <i class="fa-solid fa-magnifying-glass" style="position:absolute;left:.75rem;top:50%;transform:translateY(-50%);color:#94a3b8"></i>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Kampanya adı veya reklamveren ara…"
            class="eisa-field"
            style="padding-left:2.25rem;width:100%"
          />
        </div>
        <select v-model="filterStatus" class="eisa-field filter">
          <option value="ALL">Tüm Durumlar</option>
          <option value="ACTIVE">Aktif</option>
          <option value="PAUSED">Duraklatıldı</option>
          <option value="COMPLETED">Tamamlandı</option>
        </select>
      </div>
      <div
        v-if="selectionCount > 0"
        class="bulk-bar"
        style="display:flex;align-items:center;gap:.75rem;padding:.6rem .9rem;margin-top:.6rem;background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px"
      >
        <strong>{{ selectionCount }} kampanya seçildi</strong>
        <span style="flex:1"></span>
        <button class="eisa-btn eisa-btn-success"  @click="bulkRun('activate')"><i class="fa-solid fa-play"></i> Aktifleştir</button>
        <button class="eisa-btn eisa-btn-warning"  @click="bulkRun('pause')"><i class="fa-solid fa-pause"></i> Duraklat</button>
        <button class="eisa-btn eisa-btn-danger"   @click="bulkRun('delete')"><i class="fa-solid fa-trash"></i> Sil</button>
        <button class="eisa-btn eisa-btn-ghost"    @click="clearSelection">Vazgeç</button>
      </div>
    </section>

    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Kampanyalar ({{ filteredCampaigns.length }})</h2>
      </div>
      <div class="eisa-panel-body">
        <div class="table-wrap">
          <table class="eisa-table">
            <thead>
              <tr>
                <th style="width:36px">
                  <input
                    type="checkbox"
                    :checked="allVisibleSelected"
                    :indeterminate.prop="selectionCount > 0 && !allVisibleSelected"
                    @change="toggleSelectAll"
                    aria-label="Hepsini seç"
                  />
                </th>
                <th style="width:48px"></th>
                <th class="sortable" @click="toggleSort('name')" style="cursor:pointer">
                  Ad
                  <i v-if="sortKey==='name'" :class="sortDir==='asc' ? 'fa-solid fa-caret-up' : 'fa-solid fa-caret-down'"></i>
                </th>
                <th class="sortable" @click="toggleSort('advertiser')" style="cursor:pointer">
                  Reklamveren
                  <i v-if="sortKey==='advertiser'" :class="sortDir==='asc' ? 'fa-solid fa-caret-up' : 'fa-solid fa-caret-down'"></i>
                </th>
                <th class="sortable" @click="toggleSort('start')" style="cursor:pointer">
                  Tarihler
                  <i v-if="sortKey==='start'" :class="sortDir==='asc' ? 'fa-solid fa-caret-up' : 'fa-solid fa-caret-down'"></i>
                </th>
                <th>Durum</th>
                <th>Creative</th>
                <th>Hedef</th>
                <th class="actions-col">İşlem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="9" class="empty-row">Yükleniyor…</td></tr>
              <tr v-else-if="!filteredCampaigns.length">
                <td colspan="9" class="empty-row">
                  <template v-if="searchQuery || filterStatus !== 'ALL'">
                    Filtreyle eşleşen kampanya yok.
                    <button class="link-btn" @click="searchQuery=''; filterStatus='ALL'">Filtreleri temizle</button>
                  </template>
                  <template v-else>
                    Henüz kampanya yok.
                    <button class="link-btn" @click="openCreate">Hemen oluştur →</button>
                  </template>
                </td>
              </tr>
              <tr v-for="c in filteredCampaigns" :key="c.id" v-else :class="{ 'row-selected': selectedIds.has(c.id) }">
                <td>
                  <input
                    type="checkbox"
                    :checked="selectedIds.has(c.id)"
                    @change="toggleSelect(c.id)"
                    :aria-label="`Seç: ${c.name}`"
                  />
                </td>
                <td>
                  <div class="thumb">
                    <img v-if="thumbOf(c)" :src="thumbOf(c)" :alt="c.name" loading="lazy" />
                    <i v-else class="fa-regular fa-image muted"></i>
                  </div>
                </td>
                <td><strong>{{ c.name }}</strong></td>
                <td class="muted">{{ c.advertiser_name || '—' }}</td>
                <td class="muted">{{ c.start_date?.slice(0,10) }} → {{ c.end_date?.slice(0,10) }}</td>
                <td>
                  <span class="eisa-pill" :class="{
                    'eisa-pill-success': c.status === 'ACTIVE',
                    'eisa-pill-warning': c.status === 'PAUSED',
                    'eisa-pill-muted':   c.status === 'COMPLETED',
                  }">{{ STATUS_LABELS[c.status] || c.status }}</span>
                </td>
                <td>{{ c.creatives?.length ?? 0 }}</td>
                <td class="muted">
                  <span v-if="c.targets?.length">{{ c.targets.length }} hedef</span>
                  <span v-else>Tüm eczaneler</span>
                </td>
                <td class="actions">
                  <button class="icon-btn" title="Düzenle" @click="openEdit(c)"><i class="fa-solid fa-pen"></i></button>
                  <button class="icon-btn danger" title="Sil" @click="remove(c)"><i class="fa-solid fa-trash"></i></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Wizard Modal -->
    <div v-if="wizardOpen" class="eisa-modal-backdrop" @click.self="close">
      <div class="eisa-modal" style="max-width:920px">
        <div class="eisa-modal-header">
          <div class="steps">
            <span v-for="i in TOTAL_STEPS" :key="i" class="step" :class="{ active: i === step, done: i < step }">
              <b>{{ i }}</b> {{ STEP_LABELS[i-1] }}
            </span>
          </div>
          <button class="icon-btn" @click="close"><i class="fa-solid fa-xmark"></i></button>
        </div>

        <div class="eisa-modal-body">

          <!-- Step 1: Bilgiler -->
          <section v-if="step === 1" class="step-pane">
            <h3 class="step-title">Kampanya bilgileri</h3>
            <p class="step-help">Reklamveren adı, kampanyanın yayında olacağı tarih aralığı ve durumu.</p>
            <div class="form-grid">
              <div class="form-row form-row-full">
                <label class="eisa-field-label">Kampanya adı *</label>
                <input v-model="form.name" class="eisa-field" placeholder="Örn. Aspirin Yaz Kampanyası" />
              </div>
              <div class="form-row form-row-full">
                <label class="eisa-field-label">Reklamveren adı</label>
                <input v-model="form.advertiser_name" class="eisa-field" placeholder="Örn. Bayer İlaç" />
              </div>

              <!-- Compact single-row date + duration picker -->
              <div class="form-row form-row-full">
                <DateRangePicker
                  :start="form.start_date"
                  :end="form.end_date"
                  @update:start="(v) => form.start_date = v"
                  @update:end="(v) => form.end_date = v"
                />
              </div>

              <div class="form-row form-row-full">
                <label class="eisa-field-label">Durum</label>
                <select v-model="form.status" class="eisa-field">
                  <option value="ACTIVE">Aktif</option>
                  <option value="PAUSED">Duraklatıldı</option>
                  <option value="COMPLETED">Tamamlandı</option>
                </select>
              </div>
            </div>
          </section>

          <!-- Step 2: Medya -->
          <section v-if="step === 2" class="step-pane">
            <h3 class="step-title">Medya (Creative)</h3>
            <p class="step-help">
              Ekranda gösterilecek <strong>tek</strong> görsel veya video yükleyin.
              Süre: 5 / 10 / 15 / 30 / 60 saniye seçeneklerinden birini belirleyin.
            </p>
            <label v-if="!form.creatives.length" class="upload">
              <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickFile" :disabled="saving" />
              <span><i class="fa-solid fa-cloud-arrow-up"></i> Dosya seç (max 100 MB)</span>
            </label>
            <div v-if="form.creatives.length" class="creatives">
              <div v-for="(c, idx) in form.creatives" :key="idx" class="creative">
                <div class="thumb">
                  <video v-if="/\.(mp4|webm)$/i.test(c.uploaded_url)" :src="c.uploaded_url" muted />
                  <img   v-else :src="c.uploaded_url" alt="" />
                </div>
                <div class="cmeta">
                  <strong>{{ c.name }}</strong>
                  <div class="form-row">
                    <label class="eisa-field-label">Ekran süresi</label>
                    <select v-model.number="c.duration_seconds" class="eisa-field" :disabled="!!c.id">
                      <option :value="5">5 sn</option>
                      <option :value="10">10 sn</option>
                      <option :value="15">15 sn</option>
                      <option :value="30">30 sn</option>
                      <option :value="60">60 sn</option>
                    </select>
                  </div>
                </div>
                <button v-if="!c.id" class="icon-btn danger" title="Kaldır" @click="removeCreative(idx)">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </div>
            </div>
            <p v-if="saving" class="muted small">Yükleniyor…</p>
          </section>

          <!-- Step 3: Frekans & Pacing -->
          <section v-if="step === 3" class="step-pane">
            <h3 class="step-title">Planlama yöntemi</h3>

            <!-- Mode toggle -->
            <div class="pacing-tabs" style="display:flex;gap:.5rem;margin-bottom:1.25rem">
              <button type="button" class="pacing-tab" :class="{ active: pacingMode === 'FREQUENCY' }"
                      @click="pacingMode = 'FREQUENCY'">
                <i class="fa-solid fa-sliders"></i> Frekans ile planla
              </button>
              <button type="button" class="pacing-tab" :class="{ active: pacingMode === 'GOAL' }"
                      @click="pacingMode = 'GOAL'">
                <i class="fa-solid fa-bullseye"></i> Gösterim hedefiyle planla
              </button>
            </div>

            <!-- ─── FREQUENCY MODE ─────────────────────────────────────── -->
            <template v-if="pacingMode === 'FREQUENCY'">
              <p class="step-help">
                Bir kampanyaya <strong>yalnızca tek</strong> kural atanır
                (PER_LOOP / PER_HOUR / PER_DAY birbirinin alternatifidir).
              </p>
              <div class="rule-card">
                <div class="rule-grid">
                  <div class="form-row">
                    <label class="eisa-field-label">Tip</label>
                    <select v-model="form.rule.frequency_type" class="eisa-field">
                      <option v-for="t in FREQ_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                    </select>
                  </div>
                  <div class="form-row">
                    <label class="eisa-field-label">Değer (kaç kez?)</label>
                    <input v-model.number="form.rule.frequency_value"
                           type="number" min="1" class="eisa-field" />
                  </div>
                </div>
                <p class="muted small">{{ FREQ_TYPES.find(t => t.value === form.rule.frequency_type)?.help }}</p>

                <!-- Live estimated impressions callout -->
                <div v-if="estimatedImpressions" class="pacing-callout">
                  <i class="fa-solid fa-chart-line"></i>
                  <div>
                    <strong>Tahmini toplam gösterim: {{ estimatedImpressions.total.toLocaleString('tr-TR') }} kez</strong>
                    <span class="muted small"> ({{ estimatedImpressions.showsPerDay.toLocaleString('tr-TR') }} kez/gün × {{ estimatedImpressions.days }} gün, hedef eczaneler genelinde)</span>
                  </div>
                </div>
                <div v-else class="pacing-callout muted small">
                  <i class="fa-solid fa-circle-info"></i>
                  Gösterim tahmini için kampanya tarihlerini (Adım 1) girin.
                </div>

                <div class="hours">
                  <span class="muted small">
                    Hedef saatler ({{ form.rule.target_hours?.length ? form.rule.target_hours.join(', ') : 'tüm gün' }}):
                  </span>
                  <div class="hour-grid">
                    <button v-for="h in HOURS" :key="h" type="button" class="hr"
                            :class="{ active: form.rule.target_hours?.includes(h) }"
                            @click="toggleHour(form.rule, h)">{{ String(h).padStart(2,'0') }}</button>
                  </div>
                </div>
              </div>
            </template>

            <!-- ─── GOAL MODE ──────────────────────────────────────────── -->
            <template v-else>
              <p class="step-help">
                Kampanya süresince <strong>kaç kez gösterilsin</strong> istediğinizi girin.
                Sistem, tarih aralığına göre gösterimleri günlere eşit dağıtır.
                <strong>Minimum: tarih aralığındaki gün sayısı</strong> (en az günde 1 kez).
              </p>

              <div v-if="!form.start_date || !form.end_date" class="pacing-callout pacing-warn">
                <i class="fa-solid fa-triangle-exclamation"></i>
                Gösterim hesabı için önce <strong>Adım 1'de tarih aralığını</strong> girin.
              </div>

              <div class="form-row" style="max-width:360px">
                <label class="eisa-field-label">Toplam gösterim hedefi *</label>
                <input v-model.number="form.impression_goal" type="number" min="1" class="eisa-field"
                       placeholder="Örn. 5000" />
              </div>

              <div v-if="goalDistribution" class="pacing-callout" style="margin-top:.75rem">
                <i class="fa-solid fa-chart-bar"></i>
                <div>
                  <strong>{{ goalDistribution.goal.toLocaleString('tr-TR') }} gösterim</strong>
                  <span class="muted"> — </span>
                  <strong>~{{ goalDistribution.showsPerDay }} kez/gün</strong>
                  <span class="muted small"> ({{ goalDistribution.days }} gün × ~{{ goalDistribution.showsPerHour }} kez/saat)</span>
                </div>
              </div>

              <div class="rule-card" style="margin-top:1rem">
                <div class="hours">
                  <span class="muted small">
                    Hedef saatler ({{ form.rule.target_hours?.length ? form.rule.target_hours.join(', ') : 'tüm gün' }}):
                  </span>
                  <div class="hour-grid">
                    <button v-for="h in HOURS" :key="h" type="button" class="hr"
                            :class="{ active: form.rule.target_hours?.includes(h) }"
                            @click="toggleHour(form.rule, h)">{{ String(h).padStart(2,'0') }}</button>
                  </div>
                </div>
              </div>
            </template>
          </section>

          <!-- Step 4: Özet & Kaydet -->
          <section v-if="step === 4" class="step-pane">
            <h3 class="step-title">Özet & Kaydet</h3>
            <p class="step-help">Tüm bilgiler doğruysa kaydedin. Playlist yönetimi için Playlist Editörü ekranını kullanın.</p>

            <div class="summary-box">
              <h4>Özet</h4>
              <ul>
                <li><strong>Kampanya:</strong> {{ form.name || '—' }}</li>
                <li><strong>Tarih:</strong> {{ form.start_date?.slice(0,10) ?? '—' }} → {{ form.end_date?.slice(0,10) ?? '—' }}</li>
                <li><strong>Medya:</strong> {{ form.creatives.length }} adet ({{ form.creatives[0]?.duration_seconds ?? '?' }} sn)</li>
                <li v-if="pacingMode === 'GOAL'">
                  <strong>Gösterim hedefi:</strong> {{ form.impression_goal?.toLocaleString('tr-TR') }} kez
                  <span v-if="goalDistribution" class="muted"> (~{{ goalDistribution.showsPerDay }} kez/gün)</span>
                </li>
                <li v-else>
                  <strong>Frekans:</strong>
                  {{ FREQ_TYPES.find(t => t.value === form.rule.frequency_type)?.label ?? form.rule.frequency_type }}
                  = {{ form.rule.frequency_value }} kez
                  {{ form.rule.target_hours?.length ? `(saatler: ${form.rule.target_hours.join(', ')})` : '' }}
                </li>
                <li v-if="estimatedImpressions && pacingMode === 'FREQUENCY'">
                  <strong>Tahmini toplam gösterim:</strong>
                  {{ estimatedImpressions.total.toLocaleString('tr-TR') }} kez
                  <span class="muted">({{ estimatedImpressions.showsPerDay.toLocaleString('tr-TR') }}/gün × {{ estimatedImpressions.days }} gün)</span>
                </li>
              </ul>
            </div>

            <div v-if="pricingEstimate" class="pricing-estimate">
              <h4>💰 Maliyet</h4>
              <div class="pricing-grid">
                <div class="pricing-item"><span class="pricing-label">Kampanya süresi</span><span class="pricing-value">{{ pricingEstimate.days }} gün</span></div>
                <div class="pricing-item"><span class="pricing-label">Günlük gösterim</span><span class="pricing-value">{{ pricingEstimate.showsPerDay.toLocaleString('tr-TR') }} kez</span></div>
                <div class="pricing-item"><span class="pricing-label">Toplam gösterim</span><span class="pricing-value">{{ pricingEstimate.totalShows.toLocaleString('tr-TR') }} kez</span></div>
                <div class="pricing-item pricing-total"><span class="pricing-label">Toplam maliyet</span><span class="pricing-value">{{ Number(pricingEstimate.total).toLocaleString('tr-TR', { style: 'currency', currency: pricingEstimate.currency }) }}</span></div>
              </div>
            </div>
            <div v-else class="pacing-callout muted small">
              <i class="fa-solid fa-circle-info"></i>
              Maliyet hesabı için fiyatlandırma matrisi gereklidir (Ayarlar ekranından tanımlayın).
            </div>
          </section>

        </div><!-- /modal-body -->

        <div v-if="stepError" class="step-error-bar">
          <i class="fa-solid fa-triangle-exclamation"></i> {{ stepError }}
        </div>

        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" :disabled="step === 1" @click="prev">
            <i class="fa-solid fa-chevron-left"></i> Geri
          </button>
          <span style="flex:1"></span>
          <button v-if="step < TOTAL_STEPS" class="eisa-btn eisa-btn-cta" @click="nextStep">
            Devam <i class="fa-solid fa-chevron-right"></i>
          </button>
          <button v-else class="eisa-btn eisa-btn-cta" :disabled="saving" @click="save">
            <i class="fa-solid fa-floppy-disk" :class="{ 'fa-spin': saving }"></i>
            {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Pacing mode tabs */
.pacing-tabs { display:flex; gap:.5rem; }
.pacing-tab {
  display:flex; align-items:center; gap:.4rem;
  padding:.5rem 1rem; border-radius:999px; font-size:.875rem; font-weight:500; cursor:pointer;
  border:1px solid var(--c-border,#e2e8f0); background:#fff; color:var(--c-text-muted,#64748b);
  transition:all .15s;
}
.pacing-tab.active {
  background:var(--c-accent,#6366f1); color:#fff; border-color:var(--c-accent,#6366f1);
}
.pacing-callout {
  display:flex; align-items:flex-start; gap:.6rem;
  padding:.6rem .9rem; border-radius:8px; margin:.75rem 0;
  background:#f0f9ff; border:1px solid #bae6fd; font-size:.875rem;
}
.pacing-callout.pacing-warn { background:#fffbeb; border-color:#fcd34d; }
.pacing-callout strong { color:var(--c-text,#0f172a); }

/* Goal option cards */
.goal-cards { display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; }
.goal-card {
  border:2px solid var(--c-border,#e2e8f0); border-radius:10px; padding:1rem;
  cursor:pointer; transition:all .15s; background:#fff;
}
.goal-card:hover:not(.disabled) { border-color:var(--c-accent,#6366f1); background:#eef2ff; }
.goal-card.selected { border-color:var(--c-accent,#6366f1); background:#eef2ff; }
.goal-card.disabled { opacity:.5; cursor:not-allowed; }
.goal-card-label { font-size:.75rem; color:var(--c-text-muted,#64748b); margin-bottom:.35rem; text-transform:uppercase; letter-spacing:.05em; }
.goal-card-value { font-size:1rem; font-weight:600; color:var(--c-text,#0f172a); }
.goal-card-warn  { font-size:.75rem; color:#dc2626; margin-top:.4rem; }
.goal-card-hint  { margin-top:.4rem; font-size:.75rem; }

/* Campaign list — thumbnail + selection */
.thumb {
  width:42px; height:42px; border-radius:6px; overflow:hidden;
  background:#f1f5f9; display:flex; align-items:center; justify-content:center;
  border:1px solid var(--c-border,#e2e8f0);
}
.thumb img { width:100%; height:100%; object-fit:cover; }
.thumb .muted { font-size:1rem; color:#94a3b8; }
.row-selected { background:#eef2ff !important; }
.eisa-table th.sortable:hover { color:var(--c-accent,#6366f1); }

/* Tree-select */
.location-tree { margin-top:.75rem; max-height:380px; overflow-y:auto;
  border:1px solid var(--c-border,#e2e8f0); border-radius:var(--radius,8px); }
.tree-loading  { padding:1rem; color:var(--c-text-muted,#64748b); font-size:.875rem; }

.tree-il       { border-bottom:1px solid var(--c-border,#e2e8f0); }
.tree-il:last-child { border-bottom:none; }
.tree-il-row,.tree-ilce-row,.tree-eczane-row {
  display:flex; align-items:center; gap:.5rem; padding:.45rem .75rem; transition:background .15s; }
.tree-il-row   { background:var(--c-bg-subtle,#f8fafc); font-weight:600; }
.tree-il-row:hover,.tree-ilce-row:hover,.tree-eczane-row:hover { background:var(--c-hover,#f1f5f9); }
.tree-il-row.covered   { background:#f0fdf4; }
.tree-ilce-row.covered { background:#eff6ff; }
.tree-ilce-list { background:var(--c-bg,#fff); padding-left:.5rem; }
.tree-ilce      { border-top:1px solid var(--c-border,#e2e8f0); }
.tree-eczane-list { background:#fafafa; padding-left:.75rem; }
.tree-eczane-row  { font-size:.825rem; }
.tree-expand { background:none; border:none; cursor:pointer; color:var(--c-text-muted,#64748b); padding:0 .25rem; }
.tree-label  { flex:1; font-size:.875rem; }
.tree-add-btn {
  display:inline-flex; align-items:center; gap:.3rem; padding:.2rem .6rem; font-size:.75rem;
  border-radius:999px; cursor:pointer; border:1px solid var(--c-border,#e2e8f0);
  background:white; color:var(--c-text-muted,#64748b); transition:all .15s; }
.tree-add-btn:hover,.tree-add-btn.active {
  background:var(--c-accent,#6366f1); color:#fff; border-color:var(--c-accent,#6366f1); }
.tree-add-btn.sm { padding:.15rem .4rem; }

/* Target chips */
.target-chips { display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:.75rem; }
.target-chip  { display:inline-flex; align-items:center; gap:.35rem; cursor:default; }
.chip-il     { background:#eff6ff; color:#1d4ed8; }
.chip-ilce   { background:#f0fdf4; color:#166534; }
.chip-eczane { background:#faf5ff; color:#7c3aed; }
.chip-remove { background:none; border:none; cursor:pointer; padding:0 .1rem; color:inherit; opacity:.7; line-height:1; }
.chip-remove:hover { opacity:1; }

/* Preview */
.preview-controls { display:flex; flex-wrap:wrap; align-items:flex-end; gap:.75rem; margin:1rem 0; }
.preview-table-wrap { overflow-x:auto; }
.preview-table .conflict-row { background:#fef2f2; }
.cap-bar { position:relative; background:#e2e8f0; border-radius:4px; height:20px; overflow:hidden; min-width:80px; }
.cap-fill { position:absolute; left:0; top:0; bottom:0; background:#22c55e; border-radius:4px; transition:width .3s; }
.cap-fill.danger { background:#ef4444; }
.cap-bar.danger  { background:#fee2e2; }
.cap-bar span    { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  font-size:.7rem; font-weight:700; color:#334155; white-space:nowrap; }

/* Summary */
.summary-box { background:var(--c-bg-subtle,#f8fafc); border:1px solid var(--c-border,#e2e8f0);
  border-radius:var(--radius,8px); padding:1rem 1.25rem; margin-bottom:1rem; }
.summary-box h4 { margin:0 0 .5rem; font-size:.875rem; text-transform:uppercase;
  letter-spacing:.05em; color:var(--c-text-muted,#64748b); }
.summary-box ul { margin:0; padding-left:1rem; font-size:.875rem; }
.summary-box li { margin-bottom:.25rem; }
.pricing-estimate {
  background: #f0fdf4; border: 1px solid #bbf7d0;
  border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
}
.pricing-estimate h4 { margin: 0 0 12px; font-size: 0.95rem; color: #15803d; }
.pricing-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.pricing-item { display: flex; flex-direction: column; gap: 4px; }
.pricing-label { font-size: 0.75rem; color: #64748b; }
.pricing-value { font-size: 0.95rem; font-weight: 700; color: #0f172a; }
.pricing-total .pricing-value { font-size: 1.1rem; color: #15803d; }
.preview-error {
  background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;
  border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-size: 0.875rem;
}
.preview-note { padding: 8px 0; }
.muted { color: #94a3b8; }
.small { font-size: 0.75rem; }

/* Misc */
.step-subtitle { font-size:.9rem; font-weight:600; color:var(--c-text,#1e293b); margin:0 0 .5rem; }
.field-hint    { display:block; font-size:.75rem; color:var(--c-text-muted,#64748b); margin-top:.2rem; }

/* Per-step validation error bar */
.step-error-bar {
  display:flex; align-items:center; gap:.5rem;
  padding:.6rem 1rem; background:#fef2f2; border-top:1px solid #fecaca;
  color:#dc2626; font-size:.875rem;
}
</style>
