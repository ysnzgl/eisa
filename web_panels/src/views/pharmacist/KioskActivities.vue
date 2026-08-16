<script setup>
/**
 * Eczacı — Kiosk Hareketleri
 *
 * Yalnız oturum açan eczacının eczanesine ait kiosk verilerini gösterir.
 * Backend eczane scope'unu zorunlu kılar; URL manipülasyonuyla başka eczane
 * verisine erişilemez.
 *
 * Sekmeler: QR / Oturum | Satışlar | Kampanya Gösterimleri
 * Kiosk seçimi: EisaLookup — "İl / İlçe / Eczane / Kiosk" birleşik etiketiyle.
 */
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { http } from '../../services/api';
import { getKioskActivities, getCampaignImpressions, getKioskEvents } from '../../services/analytics';
import SessionDetailModal from '../../components/SessionDetailModal.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import SessionsPanel from '../../components/kiosk/SessionsPanel.vue';
import SalesPanel from '../../components/kiosk/SalesPanel.vue';
import ImpressionsPanel from '../../components/kiosk/ImpressionsPanel.vue';
import EventsPanel from '../../components/kiosk/EventsPanel.vue';

// ─── URL senkronizasyonu ──────────────────────────────────────────────────────
const route  = useRoute();
const router = useRouter();

// ─── Tab ─────────────────────────────────────────────────────────────────────
const TABS = [
  { key: 'sessions',     label: 'QR / Oturum İşlemleri',   icon: 'fa-qrcode'   },
  { key: 'sales',        label: 'Satışlar',                 icon: 'fa-cart-shopping' },
  { key: 'impressions',  label: 'Kampanya Gösterimleri',    icon: 'fa-bullhorn' },
  { key: 'events',       label: 'Kiosk Olayları',           icon: 'fa-triangle-exclamation' },
];
const activeTab = ref(route.query.tab || 'sessions');

// ─── Filtreler ────────────────────────────────────────────────────────────────
const filters = ref({
  kiosk_id:     route.query.kiosk_id     || '',
  durum:        route.query.durum        || '',
  oturum_tipi:  route.query.oturum_tipi  || '',
  hassas_akis:  route.query.hassas_akis  || '',
  start_date:   route.query.start_date   || '',
  end_date:     route.query.end_date     || '',
});
const onlyPending = ref(route.query.only_pending !== 'false');

// ─── Kiosk listesi — dashboard'dan eczane kioskları (EisaLookup options) ────
const dashInfo    = ref(null);  // /api/pharmacies/me/dashboard/ yanıtı
const kioskLoader = ref(false);

const kioskOptions = computed(() =>
  (dashInfo.value?.kiosklar ?? []).map((k) => ({ id: k.id, label: k.ad || k.mac_adresi }))
);

async function loadKioskler() {
  kioskLoader.value = true;
  try {
    const { data } = await http.get('/api/pharmacies/me/dashboard/');
    dashInfo.value = data;
  } catch { /* ignore */ }
  finally { kioskLoader.value = false; }
}

// ─── Oturum listesi ───────────────────────────────────────────────────────────
const sessions      = ref([]);
const sessionsTotal = ref(0);
const sessionsPage  = ref(Number(route.query.page) || 1);
const sessionsLoad  = ref(false);
const sessionsError = ref('');

// Satışlar sekmesi
const sales      = ref([]);
const salesTotal = ref(0);
const salesPage  = ref(1);
const salesLoad  = ref(false);
const salesError = ref('');

async function loadSessions() {
  sessionsLoad.value  = true;
  sessionsError.value = '';
  try {
    const params = buildParams();
    params.page = sessionsPage.value;
    const { data } = await getKioskActivities(params);
    sessions.value      = data.results ?? data;
    sessionsTotal.value = data.count ?? 0;
  } catch {
    sessionsError.value = 'Oturumlar yüklenemedi.';
  } finally {
    sessionsLoad.value = false;
  }
}

async function loadSales() {
  salesLoad.value  = true;
  salesError.value = '';
  try {
    const params = buildParams();
    delete params.danisma_tamamlandi;  // sold filtresiyle çakışmasın
    params.sold = 'true';
    params.page = salesPage.value;
    const { data } = await getKioskActivities(params);
    sales.value      = data.results ?? data;
    salesTotal.value = data.count ?? 0;
  } catch {
    salesError.value = 'Satışlar yüklenemedi.';
  } finally {
    salesLoad.value = false;
  }
}

// ─── Gösterim listesi ─────────────────────────────────────────────────────────
const impressions      = ref([]);
const impressionsTotal = ref(0);
const impressionsPage  = ref(1);
const impressionsLoad  = ref(false);
const impressionsError = ref('');

async function loadImpressions() {
  impressionsLoad.value  = true;
  impressionsError.value = '';
  try {
    const params = { page: impressionsPage.value };
    if (filters.value.kiosk_id)   params.kiosk_id   = filters.value.kiosk_id;
    if (filters.value.start_date)  params.start_date = filters.value.start_date;
    if (filters.value.end_date)    params.end_date   = filters.value.end_date;
    const { data } = await getCampaignImpressions(params);
    impressions.value      = data.results ?? data;
    impressionsTotal.value = data.count ?? 0;
  } catch {
    impressionsError.value = 'Gösterimler yüklenemedi.';
  } finally {
    impressionsLoad.value = false;
  }
}

// ─── Olaylar listesi (Faz 4) ─────────────────────────────────────────────────
const events      = ref([]);
const eventsTotal = ref(0);
const eventsPage  = ref(1);
const eventsLoad  = ref(false);
const eventsError = ref('');

async function loadEvents() {
  eventsLoad.value  = true;
  eventsError.value = '';
  try {
    const params = { page: eventsPage.value };
    if (filters.value.kiosk_id)   params.kiosk_id   = filters.value.kiosk_id;
    if (filters.value.start_date)  params.start_date = filters.value.start_date;
    if (filters.value.end_date)    params.end_date   = filters.value.end_date;
    const { data } = await getKioskEvents(params);
    events.value      = data.results ?? data;
    eventsTotal.value = data.count ?? 0;
  } catch {
    eventsError.value = 'Olaylar yüklenemedi.';
  } finally {
    eventsLoad.value = false;
  }
}

// ─── Yardımcılar ─────────────────────────────────────────────────────────────
function buildParams() {
  const p = {};
  if (filters.value.kiosk_id)    p.kiosk_id    = filters.value.kiosk_id;
  if (filters.value.durum)       p.durum        = filters.value.durum;
  if (filters.value.oturum_tipi) p.oturum_tipi  = filters.value.oturum_tipi;
  if (filters.value.hassas_akis) p.hassas_akis  = filters.value.hassas_akis;
  if (filters.value.start_date)  p.start_date   = filters.value.start_date;
  if (filters.value.end_date)    p.end_date     = filters.value.end_date;
  if (onlyPending.value)         p.danisma_tamamlandi = 'false';
  return p;
}

function syncUrl() {
  const q = { tab: activeTab.value, page: sessionsPage.value };
  Object.entries(filters.value).forEach(([k, v]) => { if (v) q[k] = v; });
  if (!onlyPending.value) q.only_pending = 'false';
  router.replace({ query: q });
}

function applyFilters() {
  sessionsPage.value = 1;
  salesPage.value = 1;
  syncUrl();
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'sales') loadSales();
  else loadImpressions();
}

function clearFilters() {
  filters.value = { kiosk_id: '', durum: '', oturum_tipi: '', hassas_akis: '', start_date: '', end_date: '' };
  onlyPending.value = true;
  applyFilters();
}

function setTab(key) {
  activeTab.value = key;
  syncUrl();
  if (key === 'sessions') loadSessions();
  else if (key === 'sales') loadSales();
  else if (key === 'impressions') loadImpressions();
  else loadEvents();
}

// ─── Detay drawer ─────────────────────────────────────────────────────────────
const selected  = ref(null);
function openDetail(row) { selected.value = row; }
function closeDetail()   { selected.value = null; }

const totalPages = computed(() => Math.ceil(sessionsTotal.value / 50) || 1);
const salesTotalPages = computed(() => Math.ceil(salesTotal.value / 50) || 1);
const impTotalPages = computed(() => Math.ceil(impressionsTotal.value / 50) || 1);
const eventsTotalPages = computed(() => Math.ceil(eventsTotal.value / 50) || 1);

onMounted(() => {
  loadKioskler();
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'sales') loadSales();
  else if (activeTab.value === 'impressions') loadImpressions();
  else loadEvents();
});
</script>

<template>
  <div class="eisa-page pharm-page">

    <!-- Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Eczacı / Kiosk</p>
        <h1 class="eisa-page-title">Kiosk Hareketleri</h1>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn eisa-btn-ghost" @click="applyFilters">
          <i class="fa-solid fa-rotate-right"></i> Yenile
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div style="display:flex;gap:0.5rem;margin-bottom:1.25rem;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:0;">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        class="eisa-btn"
        :class="activeTab === tab.key ? 'eisa-btn-cta' : 'eisa-btn-ghost'"
        style="border-radius:4px 4px 0 0;"
        @click="setTab(tab.key)"
      >
        <i class="fa-solid" :class="tab.icon"></i>
        {{ tab.label }}
      </button>
    </div>

    <!-- Filtreler -->
    <div class="eisa-panel" style="margin-bottom:1.25rem;">
      <div class="eisa-panel-header">
        <span class="eisa-panel-title"><i class="fa-solid fa-filter" style="margin-right:0.4rem;"></i>Filtreler</span>
        <button class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="clearFilters">Temizle</button>
      </div>
      <div style="padding:1rem 1.25rem;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-end;">

        <!-- Kiosk — EisaLookup -->
        <div style="flex:1;min-width:220px;">
          <label class="eisa-label">Kiosk</label>
          <EisaLookup
            v-model="filters.kiosk_id"
            :options="kioskOptions"
            :loading="kioskLoader"
            placeholder="Kiosk ara (ad, eczane, il…)"
            :clearable="true"
          />
        </div>

        <!-- Durum (yalnız oturum sekmesi) -->
        <div v-if="activeTab === 'sessions'" style="flex:1;min-width:140px;">
          <label class="eisa-label">Durum</label>
          <select v-model="filters.durum" class="eisa-field">
            <option value="">Tümü</option>
            <option value="COMPLETED">Tamamlandı</option>
            <option value="ABANDONED">Terk Edildi</option>
            <option value="EXPIRED">Süresi Doldu</option>
          </select>
        </div>

        <!-- Oturum tipi -->
        <div v-if="activeTab === 'sessions'" style="flex:1;min-width:160px;">
          <label class="eisa-label">İşlem Türü</label>
          <select v-model="filters.oturum_tipi" class="eisa-field">
            <option value="">Tümü</option>
            <option value="SIKAYET">Şikayet</option>
            <option value="OZEL_DANISMANLIK">Özel Danışmanlık</option>
          </select>
        </div>

        <!-- Hassas -->
        <div v-if="activeTab === 'sessions'" style="flex:1;min-width:130px;">
          <label class="eisa-label">Hassas Konu</label>
          <select v-model="filters.hassas_akis" class="eisa-field">
            <option value="">Tümü</option>
            <option value="true">Evet</option>
            <option value="false">Hayır</option>
          </select>
        </div>

        <!-- Tarih aralığı -->
        <div style="flex:1;min-width:140px;">
          <label class="eisa-label">Başlangıç</label>
          <input v-model="filters.start_date" type="date" class="eisa-field" />
        </div>
        <div style="flex:1;min-width:140px;">
          <label class="eisa-label">Bitiş</label>
          <input v-model="filters.end_date" type="date" class="eisa-field" />
        </div>

        <button class="eisa-btn eisa-btn-cta" @click="applyFilters" style="flex:0 0 auto;">
          <i class="fa-solid fa-magnifying-glass"></i> Filtrele
        </button>

        <!-- Sadece bekleyenler -->
        <label v-if="activeTab === 'sessions'" style="flex:0 0 auto;display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.85rem;color:#374151;padding-bottom:2px;">
          <input type="checkbox" v-model="onlyPending" @change="applyFilters" style="accent-color:#0D9488;width:1rem;height:1rem;" />
          Sadece bekleyenler
        </label>
      </div>
    </div>

    <!-- ── Oturum Listesi ─────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'sessions'">
      <SessionsPanel
        :rows="sessions" :loading="sessionsLoad" :error="sessionsError"
        :total="sessionsTotal" :page="sessionsPage" :total-pages="totalPages"
        :show-kiosk="true" :show-hassas="true"
        @change-page="(p) => { sessionsPage = p; syncUrl(); loadSessions(); }"
        @open-detail="openDetail"
      />
    </template>

    <!-- ── Satışlar Listesi ──────────────────────────────────────────────── -->
    <template v-if="activeTab === 'sales'">
      <SalesPanel
        :rows="sales" :loading="salesLoad" :error="salesError"
        :total="salesTotal" :page="salesPage" :total-pages="salesTotalPages"
        @change-page="(p) => { salesPage = p; loadSales(); }"
        @open-detail="openDetail"
      />
    </template>

    <!-- ── Gösterim Listesi ───────────────────────────────────────────────── -->
    <template v-if="activeTab === 'impressions'">
      <ImpressionsPanel
        :rows="impressions" :loading="impressionsLoad" :error="impressionsError"
        :total="impressionsTotal" :page="impressionsPage" :total-pages="impTotalPages"
        @change-page="(p) => { impressionsPage = p; loadImpressions(); }"
      />
    </template>

    <!-- ── Olaylar Listesi (Faz 4) ──────────────────────────────────────── -->
    <template v-if="activeTab === 'events'">
      <EventsPanel
        :rows="events" :loading="eventsLoad" :error="eventsError"
        :total="eventsTotal" :page="eventsPage" :total-pages="eventsTotalPages"
        @change-page="(p) => { eventsPage = p; loadEvents(); }"
      />
    </template>

    <!-- ── Oturum Detay Modal ─────────────────────────────────────────────── -->
    <SessionDetailModal
      :session="selected"
      :readonly="false"
      @close="closeDetail"
      @completed="(updated) => { const row = sessions.find(s => s.id === updated.id); if (row) row.danisma_tamamlandi = updated.danisma_tamamlandi; closeDetail(); }"
    />

  </div>
</template>
