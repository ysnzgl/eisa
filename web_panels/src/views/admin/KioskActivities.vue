<script setup>
/**
 * Admin — Kiosk Hareketleri
 *
 * Tüm eczane ve kioskların QR/oturum hareketleri ile kampanya gösterimleri.
 * Drill-down: ?tab=sessions&durum=EXPIRED&kiosk_id=...&campaign_id=...
 *
 * Eczane/Kiosk seçimi: EisaLookup — "İl / İlçe / Eczane" ve "İl / İlçe / Eczane / Kiosk"
 * birleşik etiketleriyle tek arama kutusundan arama.
 */
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getKioskActivities, getCampaignImpressions, getKioskEvents } from '../../services/analytics';
import { getKioskDayStream } from '../../services/dooh.js';
import { calcKioskRolloutStatus } from '../../composables/useKioskRolloutStatus.js';
import { fmtDT } from '../../composables/useActivityFormatters.js';
import SessionDetailModal from '../../components/SessionDetailModal.vue';
import EczanePicker from '../../components/shared/EczanePicker.vue';
import KioskPicker from '../../components/shared/KioskPicker.vue';
import SessionsPanel from '../../components/kiosk/SessionsPanel.vue';
import SalesPanel from '../../components/kiosk/SalesPanel.vue';
import ImpressionsPanel from '../../components/kiosk/ImpressionsPanel.vue';
import EventsPanel from '../../components/kiosk/EventsPanel.vue';

const route  = useRoute();
const router = useRouter();

// ─── Tab ───────────────────────────────────────────────────────────────────────────────
const TABS = [
  { key: 'sessions',    label: 'QR / Oturum İşlemleri', icon: 'fa-qrcode'   },
  { key: 'sales',       label: 'Satışlar',               icon: 'fa-cart-shopping' },
  { key: 'impressions', label: 'Kampanya Gösterimleri',  icon: 'fa-bullhorn' },
  { key: 'events',      label: 'Kiosk Olayları',          icon: 'fa-triangle-exclamation' },
  { key: 'broadcast',   label: 'Yayın Akışı',              icon: 'fa-tv'       },
];
const activeTab = ref(route.query.tab || 'sessions');

// ─── Filtreler ────────────────────────────────────────────────────────────────
const filters = ref({
  eczane_id:    route.query.eczane_id    || '',
  kiosk_id:     route.query.kiosk_id     || '',
  durum:        route.query.durum        || '',
  oturum_tipi:  route.query.oturum_tipi  || '',
  hassas_akis:  route.query.hassas_akis  || '',
  campaign_id:  route.query.campaign_id  || '',
  kategori_slug: route.query.kategori_slug || '',
  start_date:   route.query.start_date   || '',
  end_date:     route.query.end_date     || '',
});

// ─── Oturum listesi ───────────────────────────────────────────────────────────
const sessions      = ref([]);
const sessionsTotal = ref(0);
const sessionsPage  = ref(Number(route.query.page) || 1);
const sessionsLoad  = ref(false);
const sessionsError = ref('');

// Satışlar sekmesi için ayrı state
const sales      = ref([]);
const salesTotal = ref(0);
const salesPage  = ref(1);
const salesLoad  = ref(false);
const salesError = ref('');

async function loadSessions() {
  sessionsLoad.value  = true;
  sessionsError.value = '';
  try {
    const params = buildSessionParams();
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
    const params = buildSessionParams();
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
    const params = buildImpressionParams();
    params.page = impressionsPage.value;
    const { data } = await getCampaignImpressions(params);
    impressions.value      = data.results ?? data;
    impressionsTotal.value = data.count ?? 0;
  } catch {
    impressionsError.value = 'Gösterimler yüklenemedi.';
  } finally {
    impressionsLoad.value = false;
  }
}

// ─── Param builders ───────────────────────────────────────────────────────────
function buildSessionParams() {
  const p = {};
  ['eczane_id','kiosk_id','durum','oturum_tipi','hassas_akis','kategori_slug','start_date','end_date']
    .forEach((k) => { if (filters.value[k]) p[k] = filters.value[k]; });
  return p;
}

function buildImpressionParams() {
  const p = {};
  ['eczane_id','kiosk_id','campaign_id','start_date','end_date']
    .forEach((k) => { if (filters.value[k]) p[k] = filters.value[k]; });
  return p;
}

// ─── Olaylar listesi (Faz 4) ──────────────────────────────────────────────────
const events      = ref([]);
const eventsTotal = ref(0);
const eventsPage  = ref(1);
const eventsLoad  = ref(false);
const eventsError = ref('');

async function loadEvents() {
  eventsLoad.value  = true;
  eventsError.value = '';
  try {
    const p = {};
    ['il_id','eczane_id','kiosk_id','start_date','end_date'].forEach((k) => { if (filters.value[k]) p[k] = filters.value[k]; });
    p.page = eventsPage.value;
    const { data } = await getKioskEvents(p);
    events.value      = data.results ?? data;
    eventsTotal.value = data.count ?? 0;
  } catch {
    eventsError.value = 'Olaylar yüklenemedi.';
  } finally {
    eventsLoad.value = false;
  }
}

function syncUrl() {
  const q = { tab: activeTab.value, page: sessionsPage.value };
  Object.entries(filters.value).forEach(([k, v]) => { if (v) q[k] = v; });
  router.replace({ query: q });
}

function applyFilters() {
  sessionsPage.value = 1;
  impressionsPage.value = 1;
  eventsPage.value = 1;
  salesPage.value = 1;
  syncUrl();
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'sales') loadSales();
  else if (activeTab.value === 'impressions') loadImpressions();
  else loadEvents();
}

function clearFilters() {
  filters.value = { eczane_id:'', kiosk_id:'', durum:'', oturum_tipi:'', hassas_akis:'', campaign_id:'', kategori_slug:'', start_date:'', end_date:'' };
  applyFilters();
}

function setTab(key) {
  activeTab.value = key;
  syncUrl();
  if (key === 'sessions') loadSessions();
  else if (key === 'sales') loadSales();
  else if (key === 'impressions') loadImpressions();
  else if (key === 'events') loadEvents();
  else if (key === 'broadcast') loadDayStream();
}

// ─── Yayın Akışı ──────────────────────────────────────────────────────────────────────
const bcastKioskId  = ref(filters.value.kiosk_id || '');
// Varsayılan gün: yarın (Istanbul)
function _tomorrowIstanbul() {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}
const bcastDate     = ref(_tomorrowIstanbul());
const bcastLoading  = ref(false);
const bcastError    = ref('');
const bcastData     = ref(null);  // API yanıtı
const bcastNow      = ref(Date.now()); // her saniyede değil, item hesabında kullanılır
const bcastLastRefreshed = ref(null);

/** Is a media URL a video? (query string tolerant, case insensitive) */
function isVideoUrlBC(url) {
  if (!url) return false;
  return /\.(mp4|webm|ogg|mov)(\?|$)/i.test(url);
}

async function loadDayStream() {
  if (!bcastKioskId.value) { bcastData.value = null; return; }
  bcastLoading.value = true;
  bcastError.value = '';
  try {
    const { data } = await getKioskDayStream(bcastKioskId.value, bcastDate.value);
    bcastData.value = data;
    bcastLastRefreshed.value = new Date();
    bcastNow.value = Date.now();
  } catch (e) {
    bcastError.value = e?.response?.data?.error || 'Yayın akışı yüklenemedi.';
  } finally {
    bcastLoading.value = false;
  }
}

watch([bcastKioskId, bcastDate], () => {
  if (activeTab.value === 'broadcast') loadDayStream();
});

/**
 * Europe/Istanbul saati ile şu an saatin kaçıncı saniyesindeyiz (0..3599)
 */
function istanbulSecondOfHour() {
  // Tarayıcı yerel saatinden UTC’ya, sonra Istanbul’a (+3h sabit; DST yok 2016’dan beri)
  const now = new Date();
  const istanbul = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  return (istanbul.getMinutes() * 60) + istanbul.getSeconds();
}

function istanbulHour() {
  const now = new Date();
  const istanbul = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
  return istanbul.getHours();
}

/** Playlist items for the current Istanbul hour */
const currentHourItems = computed(() => {
  if (!bcastData.value?.hours?.length) return [];
  const h = istanbulHour();
  const hourPl = bcastData.value.hours.find((x) => x.target_hour === h);
  return hourPl?.items || [];
});

/** Şu an yayında olan playlist item (saat-mutlak offset mantığı) */
const currentItem = computed(() => {
  const items = currentHourItems.value;
  if (!items.length) return null;
  const pos = istanbulSecondOfHour();
  // offset <= pos olan son öğe aktif
  let active = items[0];
  for (const item of items) {
    if (item.estimated_start_offset_seconds <= pos) active = item;
    else break;
  }
  return active;
});

/** Kiosk senkronizasyon durumu — canonical calcKioskRolloutStatus ile aynı sözleşme */
const kioskSyncStatus = computed(() => {
  const d = bcastData.value;
  if (!d) return null;
  // calcKioskRolloutStatus applied_playlist_version bekler; day-stream applied_version döner
  const kioskLike = {
    is_online: d.is_online,
    son_goruldu: d.son_goruldu,
    last_playlist_version: d.last_playlist_version,
    applied_playlist_version: d.applied_version,
    applied_horizon_end: d.applied_horizon_end,
  };
  const { status } = calcKioskRolloutStatus(kioskLike, null);
  // up_to_date → 'synced'; diğer tüm durumlar "doğrulanamadı" grubunda
  if (status === 'up_to_date') return 'synced';
  if (status === 'offline') return 'offline';
  if (status === 'behind') return 'behind';
  if (status === 'ack_pending') return 'ack_pending';
  if (status === 'no_publish') return 'no_publish';
  return status;
});

const bcastRefreshLabel = computed(() => {
  if (!bcastLastRefreshed.value) return null;
  return bcastLastRefreshed.value.toLocaleTimeString('tr-TR');
});

// ─── Detay drawer ─────────────────────────────────────────────────────────────
const selected = ref(null);
function openDetail(row) { selected.value = row; }
function closeDetail()   { selected.value = null; }

const totalPages = computed(() => Math.ceil(sessionsTotal.value / 50) || 1);
const impTotalPages = computed(() => Math.ceil(impressionsTotal.value / 50) || 1);
const salesTotalPages = computed(() => Math.ceil(salesTotal.value / 50) || 1);
const eventsTotalPages = computed(() => Math.ceil(eventsTotal.value / 50) || 1);

onMounted(() => {
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'sales') loadSales();
  else if (activeTab.value === 'impressions') loadImpressions();
  else if (activeTab.value === 'events') loadEvents();
  else if (activeTab.value === 'broadcast') loadDayStream();
});
</script>

<template>
  <div class="eisa-page">

    <!-- Header -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Admin / Kiosk</p>
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
      <button v-for="tab in TABS" :key="tab.key" class="eisa-btn"
        :class="activeTab === tab.key ? 'eisa-btn-cta' : 'eisa-btn-ghost'"
        style="border-radius:4px 4px 0 0;" @click="setTab(tab.key)">
        <i class="fa-solid" :class="tab.icon"></i> {{ tab.label }}
      </button>
    </div>

    <!-- Filtreler — sadece broadcast dışındaki sekmelerde göster -->
    <div v-if="activeTab !== 'broadcast'" class="eisa-panel" style="margin-bottom:1.25rem;">
      <div class="eisa-panel-header">
        <span class="eisa-panel-title"><i class="fa-solid fa-filter" style="margin-right:0.4rem;"></i>Filtreler</span>
        <button class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="clearFilters">Temizle</button>
      </div>
      <div style="padding:1rem 1.25rem;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-end;">

        <!-- Eczane AutoComplete -->
        <div style="flex:2;min-width:220px;">
          <label class="eisa-label">Eczane</label>
          <EczanePicker v-model="filters.eczane_id" />
        </div>

        <!-- Kiosk AutoComplete -->
        <div style="flex:2;min-width:220px;">
          <label class="eisa-label">Kiosk</label>
          <KioskPicker v-model="filters.kiosk_id" :eczane-id="filters.eczane_id" />
        </div>

        <template v-if="activeTab === 'sessions'">
          <!-- Durum -->
          <div style="flex:1;min-width:130px;">
            <label class="eisa-label">Durum</label>
            <select v-model="filters.durum" class="eisa-field">
              <option value="">Tümü</option>
              <option value="COMPLETED">Tamamlandı</option>
              <option value="ABANDONED">Terk Edildi</option>
              <option value="EXPIRED">Süresi Doldu</option>
            </select>
          </div>
          <!-- İşlem Türü -->
          <div style="flex:1;min-width:150px;">
            <label class="eisa-label">İşlem Türü</label>
            <select v-model="filters.oturum_tipi" class="eisa-field">
              <option value="">Tümü</option>
              <option value="SIKAYET">Şikayet</option>
              <option value="OZEL_DANISMANLIK">Özel Danışmanlık</option>
            </select>
          </div>
        </template>

        <!-- Tarih -->
        <div style="flex:1;min-width:130px;">
          <label class="eisa-label">Başlangıç</label>
          <input v-model="filters.start_date" type="date" class="eisa-field" />
        </div>
        <div style="flex:1;min-width:130px;">
          <label class="eisa-label">Bitiş</label>
          <input v-model="filters.end_date" type="date" class="eisa-field" />
        </div>

        <button class="eisa-btn eisa-btn-cta" @click="applyFilters" style="flex:0 0 auto;">
          <i class="fa-solid fa-magnifying-glass"></i> Filtrele
        </button>
      </div>
    </div>

    <!-- ── Oturum Listesi ─────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'sessions'">
      <div v-if="filters.kategori_slug" style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem;padding:0.5rem 0.75rem;background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.25);border-radius:6px;font-size:0.82rem;color:#a78bfa;">
        <i class="fa-solid fa-filter"></i>
        Kategori filtresi aktif: <strong>{{ filters.kategori_slug }}</strong>
        <button class="eisa-btn eisa-btn-ghost" style="font-size:0.72rem;padding:0.15rem 0.4rem;margin-left:auto;" @click="filters.kategori_slug=''; applyFilters()">Kaldır</button>
      </div>
      <SessionsPanel
        :rows="sessions" :loading="sessionsLoad" :error="sessionsError"
        :total="sessionsTotal" :page="sessionsPage" :total-pages="totalPages"
        :show-eczane="true" :warn-danismanlik="true"
        @change-page="(p) => { sessionsPage = p; syncUrl(); loadSessions(); }"
        @open-detail="openDetail"
      />
    </template>

    <!-- ── Satışlar Listesi ──────────────────────────────────────────────── -->
    <template v-if="activeTab === 'sales'">
      <SalesPanel
        :rows="sales" :loading="salesLoad" :error="salesError"
        :total="salesTotal" :page="salesPage" :total-pages="salesTotalPages"
        :show-eczane="true"
        @change-page="(p) => { salesPage = p; loadSales(); }"
        @open-detail="openDetail"
      />
    </template>

    <!-- ── Gösterim Listesi ───────────────────────────────────────────────── -->
    <template v-if="activeTab === 'impressions'">
      <ImpressionsPanel
        :rows="impressions" :loading="impressionsLoad" :error="impressionsError"
        :total="impressionsTotal" :page="impressionsPage" :total-pages="impTotalPages"
        :show-eczane="true"
        @change-page="(p) => { impressionsPage = p; loadImpressions(); }"
      />
    </template>

    <!-- ── Olaylar Listesi (Faz 4) ───────────────────────────────────────── -->
    <template v-if="activeTab === 'events'">
      <EventsPanel
        :rows="events" :loading="eventsLoad" :error="eventsError"
        :total="eventsTotal" :page="eventsPage" :total-pages="eventsTotalPages"
        :show-eczane="true"
        @change-page="(p) => { eventsPage = p; loadEvents(); }"
      />
    </template>

    <!-- ── Yayın Akışı ──────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'broadcast'">
      <!-- Üst kontrol çubuğu -->
      <div class="eisa-panel" style="margin-bottom:1rem;padding:1rem 1.25rem;">
        <div style="display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-end;">
          <div style="flex:2;min-width:220px;">
            <label class="eisa-label">Kiosk</label>
            <KioskPicker v-model="bcastKioskId" />
          </div>
          <div style="flex:0 0 160px;">
            <label class="eisa-label">Tarih</label>
            <input v-model="bcastDate" type="date" class="eisa-field" />
          </div>
          <button class="eisa-btn eisa-btn-cta" @click="loadDayStream" :disabled="!bcastKioskId || bcastLoading">
            <i class="fa-solid" :class="bcastLoading ? 'fa-circle-notch fa-spin' : 'fa-rotate-right'"></i>
            Yenile
          </button>
          <span v-if="bcastRefreshLabel" style="font-size:0.78rem;color:#9CA3AF;align-self:center;">
            Son: {{ bcastRefreshLabel }}
          </span>
        </div>

        <!-- Kiosk durum özeti -->
        <div v-if="bcastData" style="display:flex;flex-wrap:wrap;gap:0.75rem;margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid rgba(255,255,255,0.08);">
          <div style="flex:0 0 auto;">
            <span class="eisa-pill" :class="bcastData.is_online ? 'eisa-pill-success' : 'eisa-pill-danger'">
              <i class="fa-solid" :class="bcastData.is_online ? 'fa-circle' : 'fa-circle-xmark'"></i>
              {{ bcastData.is_online ? 'Çevrimiçi' : 'Çevrimdışı' }}
            </span>
          </div>
          <div style="font-size:0.8rem;color:#94a3b8;align-self:center;">
            Son görülme: {{ bcastData.son_goruldu ? fmtDT(bcastData.son_goruldu) : '—' }}
          </div>
          <div style="font-size:0.8rem;color:#94a3b8;align-self:center;">
            Desired (backend): v{{ bcastData.desired_version ?? '—' }}
            <template v-if="bcastData.applied_version != null">
              → Applied (kiosk ACK): v{{ bcastData.applied_version }}
            </template>
            <template v-else>
              → Applied (kiosk ACK): yok
            </template>
          </div>

          <!-- Senkronizasyon uyarısı -->
          <div v-if="kioskSyncStatus === 'offline'" style="font-size:0.8rem;color:#f59e0b;display:flex;align-items:center;gap:0.3rem;">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Kiosk çevrimdışı — planlanan yayın, doğrulanamadı.
          </div>
          <div v-else-if="kioskSyncStatus === 'behind'" style="font-size:0.8rem;color:#f59e0b;display:flex;align-items:center;gap:0.3rem;">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Kiosk geride — applied &lt; desired; kiosktaki içerik farklı olabilir.
          </div>
          <div v-else-if="kioskSyncStatus === 'ack_pending'" style="font-size:0.8rem;color:#f59e0b;display:flex;align-items:center;gap:0.3rem;">
            <i class="fa-solid fa-triangle-exclamation"></i>
            ACK bekleniyor — kiosk henüz uygulama onayı göndermedi.
          </div>
          <div v-else-if="kioskSyncStatus === 'no_publish'" style="font-size:0.8rem;color:#94a3b8;display:flex;align-items:center;gap:0.3rem;">
            <i class="fa-solid fa-circle-info"></i>
            Henüz yayın üretilmemiş (desired version yok).
          </div>
          <div v-else-if="kioskSyncStatus === 'synced'" style="font-size:0.8rem;color:#10b981;display:flex;align-items:center;gap:0.3rem;">
            <i class="fa-solid fa-circle-check"></i>
            Kiosk güncel — aşağıdaki içerik şu an gösterilmesi bekleniyor.
          </div>
        </div>
      </div>

      <div v-if="bcastLoading" style="padding:3rem;text-align:center;color:#6B7280;">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
      </div>
      <div v-else-if="bcastError" class="eisa-error-banner" style="margin-bottom:1rem;">
        <i class="fa-solid fa-triangle-exclamation"></i> {{ bcastError }}
      </div>
      <div v-else-if="!bcastData && !bcastKioskId" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
        <i class="fa-solid fa-tv" style="font-size:2rem;opacity:0.25;display:block;margin-bottom:0.75rem;"></i>
        <p>Yayın akışını görmek için bir kiosk ve tarih seçin.</p>
      </div>
      <template v-else-if="bcastData">

        <!-- Şu an yayında -->
        <div class="eisa-panel" style="margin-bottom:1rem;">
          <div class="eisa-panel-header">
            <span class="eisa-panel-title"><i class="fa-solid fa-circle-play" style="color:#10b981;margin-right:0.4rem;"></i>Şu An Yayında</span>
          </div>
          <div v-if="!currentItem" style="padding:1.5rem;text-align:center;color:#6B7280;">
            <template v-if="!bcastData.hours?.length">
              <i class="fa-solid fa-rectangle-ad" style="font-size:1.5rem;opacity:0.3;display:block;margin-bottom:0.5rem;"></i>
              <p style="font-weight:600;">Playlist bulunamadı</p>
              <p class="muted small">Bu kiosk için {{ bcastDate }} tarihinde üretilmiş playlist yok. Reklam yerine "Bu Alana Reklam Verebilirsiniz" (AdPromo) gösterilir.</p>
            </template>
            <template v-else>
              <p class="muted">Bu saatte gösterim yok.</p>
            </template>
          </div>
          <div v-else style="padding:1.25rem;display:flex;flex-wrap:wrap;gap:1.5rem;">
            <!-- Bekleme ekranı preview -->
            <div style="flex:1;min-width:160px;">
              <p style="font-size:0.7rem;color:#94a3b8;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em;">Bekleme Ekranı (IdleScreen)</p>
              <div style="width:100%;max-width:180px;aspect-ratio:9/16;background:#0f172a;border-radius:8px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden;position:relative;">
                <template v-if="isVideoUrlBC(currentItem.media_url)">
                  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem;color:#60a5fa;">
                    <i class="fa-solid fa-circle-play" style="font-size:2rem;"></i>
                    <span style="font-size:0.75rem;">Video</span>
                  </div>
                </template>
                <img v-else-if="currentItem.media_url" :src="currentItem.media_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy" :alt="currentItem.name" />
                <div v-else style="color:#64748b;font-size:0.75rem;">Görsel yok</div>
              </div>
            </div>
            <!-- İşlem ekranı preview -->
            <div style="flex:1;min-width:160px;">
              <p style="font-size:0.7rem;color:#94a3b8;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em;">İşlem Ekranı (AdStrip)</p>
              <div style="width:100%;max-width:220px;aspect-ratio:7/5;background:#0f172a;border-radius:8px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden;">
                <template v-if="isVideoUrlBC(currentItem.active_media_url || currentItem.media_url)">
                  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem;color:#60a5fa;">
                    <i class="fa-solid fa-circle-play" style="font-size:2rem;"></i>
                    <span style="font-size:0.75rem;">Video</span>
                    <span v-if="!currentItem.active_media_url" style="font-size:0.65rem;color:#94a3b8;">Fallback (bekleme görseli)</span>
                  </div>
                </template>
                <img v-else-if="currentItem.active_media_url || currentItem.media_url"
                  :src="currentItem.active_media_url || currentItem.media_url"
                  style="width:100%;height:100%;object-fit:cover;" loading="lazy" :alt="currentItem.name" />
                <div v-else style="color:#64748b;font-size:0.75rem;">Görsel yok</div>
                <span v-if="!currentItem.active_media_url" style="position:absolute;bottom:4px;right:4px;font-size:0.6rem;background:rgba(0,0,0,0.7);color:#94a3b8;padding:1px 4px;border-radius:4px;">Fallback</span>
              </div>
            </div>
            <!-- Detay -->
            <div style="flex:2;min-width:200px;">
              <p style="font-weight:600;margin-bottom:0.25rem;">{{ currentItem.name || '—' }}</p>
              <p style="font-size:0.8rem;color:#94a3b8;">
                <span class="eisa-pill eisa-pill-muted" style="font-size:0.7rem;">{{ currentItem.asset_type === 'creative' ? 'Kampanya' : 'HouseAd' }}</span>
              </p>
              <div style="margin-top:0.75rem;display:grid;grid-template-columns:1fr 1fr;gap:0.4rem 1rem;font-size:0.8rem;">
                <div><span style="color:#94a3b8;">Süre:</span> {{ currentItem.duration_seconds }}sn</div>
                <div><span style="color:#94a3b8;">Saat offset:</span> {{ currentItem.estimated_start_offset_seconds }}sn</div>
                <div v-if="!currentItem.active_media_url"><span style="color:#f59e0b;">⚠ Alt alan:</span> Fallback (bekleme görseli)</div>
              </div>

              <!-- Güvenilirlik uyarısı -->
              <div v-if="kioskSyncStatus !== 'synced'" style="margin-top:0.75rem;padding:0.5rem 0.75rem;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:6px;font-size:0.78rem;color:#f59e0b;">
                <i class="fa-solid fa-triangle-exclamation"></i>
                Planlanan yayın — kiosk güncelliği doğrulanamadı
              </div>
            </div>
          </div>
        </div>

        <!-- Günün yayın akışı -->
        <div class="eisa-panel">
          <div class="eisa-panel-header">
            <span class="eisa-panel-title"><i class="fa-solid fa-timeline" style="margin-right:0.4rem;"></i>Günün Yayın Akışı — {{ bcastDate }}</span>
          </div>
          <div v-if="!bcastData.hours?.length" style="padding:2rem;text-align:center;color:#6B7280;">
            <p>Bu tarih için playlist üretilmemiş.</p>
          </div>
          <div v-else style="padding:1rem 1.25rem;">
            <div v-for="hourPl in bcastData.hours" :key="hourPl.target_hour" style="margin-bottom:1.25rem;">
              <h4 style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.4rem;">
                <i class="fa-regular fa-clock"></i>
                {{ String(hourPl.target_hour).padStart(2,'0') }}:00 — {{ String(hourPl.target_hour).padStart(2,'0') }}:59
                <span class="eisa-pill eisa-pill-muted" style="font-size:0.65rem;">v{{ hourPl.version }}</span>
              </h4>
              <div v-if="!hourPl.items?.length" style="font-size:0.8rem;color:#64748b;font-style:italic;">Bu saatte playlist öğesi yok.</div>
              <div v-else style="display:flex;flex-wrap:wrap;gap:0.5rem;">
                <div v-for="item in hourPl.items" :key="item.id"
                  :class="currentItem?.id === item.id ? 'broadcast-card broadcast-card--active' : 'broadcast-card'"
                  :title="`${item.name} | ${item.asset_type} | ${item.estimated_start_offset_seconds}s | ${item.duration_seconds}s`"
                >
                  <!-- Medya preview -->
                  <div class="broadcast-thumb">
                    <template v-if="isVideoUrlBC(item.media_url)">
                      <div class="video-thumb-bc"><i class="fa-solid fa-circle-play"></i></div>
                    </template>
                    <img v-else-if="item.media_url" :src="item.media_url" loading="lazy" :alt="item.name" style="width:100%;height:100%;object-fit:cover;" />
                    <div v-else style="color:#64748b;font-size:0.7rem;">—</div>
                  </div>
                  <!-- Info -->
                  <div class="broadcast-info">
                    <p class="broadcast-name">{{ item.name || '—' }}</p>
                    <p class="broadcast-meta">
                      <span class="eisa-pill eisa-pill-muted" style="font-size:0.6rem;">{{ item.asset_type === 'creative' ? 'Kampanya' : 'HouseAd' }}</span>
                      {{ String(hourPl.target_hour).padStart(2,'0') }}:{{ String(Math.floor(item.estimated_start_offset_seconds / 60)).padStart(2,'0') }}
                    </p>
                    <p class="broadcast-meta">{{ item.duration_seconds }}sn</p>
                  </div>
                  <div v-if="currentItem?.id === item.id" class="broadcast-now-badge">
                    <i class="fa-solid fa-circle-play"></i> Şu an
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- ── Oturum Detay Modal ─────────────────────────────────────────────── -->
    <SessionDetailModal
      :session="selected"
      :readonly="true"
      @close="closeDetail"
    />

  </div>
</template>

<style scoped>
.broadcast-card {
  position: relative;
  width: 110px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #1e293b;
  overflow: hidden;
  cursor: default;
  transition: border-color 0.15s;
}
.broadcast-card:hover { border-color: rgba(255,255,255,0.2); }
.broadcast-card--active {
  border-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16,185,129,0.3);
}
.broadcast-thumb {
  width: 100%;
  aspect-ratio: 16/9;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.video-thumb-bc {
  color: #60a5fa;
  font-size: 1.5rem;
}
.broadcast-info {
  padding: 0.35rem 0.4rem;
}
.broadcast-name {
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0 0 0.15rem;
  color: #e2e8f0;
}
.broadcast-meta {
  font-size: 0.65rem;
  color: #64748b;
  margin: 0;
}
.broadcast-now-badge {
  position: absolute;
  top: 3px;
  right: 3px;
  background: #10b981;
  color: #fff;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  gap: 2px;
}
</style>
