<script setup>
/**
 * Admin — Kiosk Hareketleri
 *
 * Tüm eczane ve kioskların QR/oturum hareketleri ile kampanya gösterimleri.
 * Drill-down: ?tab=sessions&durum=EXPIRED&kiosk_id=...&campaign_id=...
 * Bağımlı filtreler: il → ilçe → eczane → kiosk
 */
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getKioskActivities, getCampaignImpressions, getKioskEvents } from '../../services/analytics';
import { getPharmacies, getKioskStatus } from '../../services/devices';
import { getIller, getIlceler } from '../../services/lookups';

const route  = useRoute();
const router = useRouter();

// ─── Tab ─────────────────────────────────────────────────────────────────────
const TABS = [
  { key: 'sessions',    label: 'QR / Oturum İşlemleri', icon: 'fa-qrcode'   },
  { key: 'impressions', label: 'Kampanya Gösterimleri',  icon: 'fa-bullhorn' },
  { key: 'events',      label: 'Kiosk Olayları',          icon: 'fa-triangle-exclamation' },
];
const activeTab = ref(route.query.tab || 'sessions');

// ─── Filtreler ────────────────────────────────────────────────────────────────
const filters = ref({
  il_id:       route.query.il_id       || '',
  ilce_id:     route.query.ilce_id     || '',
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

// ─── Bağımlı lookup listeleri ─────────────────────────────────────────────────
const iller     = ref([]);
const ilceler   = ref([]);
const eczaneler = ref([]);
const kioskler  = ref([]);

async function loadIller() {
  try { iller.value = await getIller(); } catch { /* */ }
}

watch(() => filters.value.il_id, async (ilId) => {
  filters.value.ilce_id = '';
  filters.value.eczane_id = '';
  filters.value.kiosk_id = '';
  ilceler.value = [];
  eczaneler.value = [];
  kioskler.value = [];
  if (!ilId) return;
  try { ilceler.value = await getIlceler(ilId); } catch { /* */ }
});

watch(() => filters.value.ilce_id, async (ilceId) => {
  filters.value.eczane_id = '';
  filters.value.kiosk_id = '';
  eczaneler.value = [];
  kioskler.value = [];
  if (!ilceId) return;
  try {
    const all = await getPharmacies();
    eczaneler.value = all.filter((e) => e.ilce === Number(ilceId));
  } catch { /* */ }
});

watch(() => filters.value.eczane_id, async (eczaneId) => {
  filters.value.kiosk_id = '';
  kioskler.value = [];
  if (!eczaneId) return;
  try { kioskler.value = await getKioskStatus(Number(eczaneId)); } catch { /* */ }
});

// ─── Oturum listesi ───────────────────────────────────────────────────────────
const sessions      = ref([]);
const sessionsTotal = ref(0);
const sessionsPage  = ref(Number(route.query.page) || 1);
const sessionsLoad  = ref(false);
const sessionsError = ref('');

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
  ['il_id','ilce_id','eczane_id','kiosk_id','durum','oturum_tipi','hassas_akis','kategori_slug','start_date','end_date']
    .forEach((k) => { if (filters.value[k]) p[k] = filters.value[k]; });
  return p;
}

function buildImpressionParams() {
  const p = {};
  ['il_id','ilce_id','eczane_id','kiosk_id','campaign_id','start_date','end_date']
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
  syncUrl();
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'impressions') loadImpressions();
  else loadEvents();
}

function clearFilters() {
  filters.value = { il_id:'', ilce_id:'', eczane_id:'', kiosk_id:'', durum:'', oturum_tipi:'', hassas_akis:'', campaign_id:'', kategori_slug:'', start_date:'', end_date:'' };
  applyFilters();
}

function setTab(key) {
  activeTab.value = key;
  syncUrl();
  if (key === 'sessions') loadSessions();
  else if (key === 'impressions') loadImpressions();
  else loadEvents();
}

// ─── Detay drawer ─────────────────────────────────────────────────────────────
const selected = ref(null);
function openDetail(row) { selected.value = row; }
function closeDetail()   { selected.value = null; }

// ─── Formatters ──────────────────────────────────────────────────────────────
const DURUM_LABEL = {
  COMPLETED: { text: 'Tamamlandı',  cls: 'eisa-pill-success' },
  ABANDONED: { text: 'Terk Edildi', cls: 'eisa-pill-warning' },
  EXPIRED:   { text: 'Süresi Doldu',cls: 'eisa-pill-danger'  },
};

function fmtDT(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
}

const totalPages = computed(() => Math.ceil(sessionsTotal.value / 50) || 1);
const impTotalPages = computed(() => Math.ceil(impressionsTotal.value / 50) || 1);

onMounted(() => {
  loadIller();
  if (activeTab.value === 'sessions') loadSessions();
  else if (activeTab.value === 'impressions') loadImpressions();
  else loadEvents();
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

    <!-- Filtreler — bağımlı zincir: il → ilçe → eczane → kiosk -->
    <div class="eisa-panel" style="margin-bottom:1.25rem;">
      <div class="eisa-panel-header">
        <span class="eisa-panel-title"><i class="fa-solid fa-filter" style="margin-right:0.4rem;"></i>Filtreler</span>
        <button class="eisa-btn eisa-btn-ghost" style="font-size:0.78rem;" @click="clearFilters">Temizle</button>
      </div>
      <div style="padding:1rem 1.25rem;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-end;">

        <!-- İl -->
        <div style="flex:1;min-width:120px;">
          <label class="eisa-label">İl</label>
          <select v-model="filters.il_id" class="eisa-field">
            <option value="">Tümü</option>
            <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad }}</option>
          </select>
        </div>

        <!-- İlçe (il seçilince dolar) -->
        <div style="flex:1;min-width:120px;">
          <label class="eisa-label">İlçe</label>
          <select v-model="filters.ilce_id" :disabled="!ilceler.length" class="eisa-field">
            <option value="">Tümü</option>
            <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad }}</option>
          </select>
        </div>

        <!-- Eczane (ilçe seçilince dolar) -->
        <div style="flex:1;min-width:140px;">
          <label class="eisa-label">Eczane</label>
          <select v-model="filters.eczane_id" :disabled="!eczaneler.length" class="eisa-field">
            <option value="">Tümü</option>
            <option v-for="e in eczaneler" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
        </div>

        <!-- Kiosk (eczane seçilince dolar) -->
        <div style="flex:1;min-width:140px;">
          <label class="eisa-label">Kiosk</label>
          <select v-model="filters.kiosk_id" :disabled="!kioskler.length" class="eisa-field">
            <option value="">Tümü</option>
            <option v-for="k in kioskler" :key="k.id" :value="k.id">{{ k.ad || k.mac }}</option>
          </select>
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
          <!-- Oturum tipi -->
          <div style="flex:1;min-width:150px;">
            <label class="eisa-label">İşlem Türü</label>
            <select v-model="filters.oturum_tipi" class="eisa-field">
              <option value="">Tümü</option>
              <option value="SIKAYET">Şikayet</option>
              <option value="OZEL_DANISMANLIK">Özel Danışmanlık</option>
            </select>
          </div>
          <!-- Hassas -->
          <div style="flex:0 0 110px;">
            <label class="eisa-label">Hassas</label>
            <select v-model="filters.hassas_akis" class="eisa-field">
              <option value="">Tümü</option>
              <option value="true">Evet</option>
              <option value="false">Hayır</option>
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
      <!-- Kategori drill-down banner -->
      <div v-if="filters.kategori_slug" style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem;padding:0.5rem 0.75rem;background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.25);border-radius:6px;font-size:0.82rem;color:#a78bfa;">
        <i class="fa-solid fa-filter"></i>
        Kategori filtresi aktif: <strong>{{ filters.kategori_slug }}</strong>
        <button class="eisa-btn eisa-btn-ghost" style="font-size:0.72rem;padding:0.15rem 0.4rem;margin-left:auto;" @click="filters.kategori_slug=''; applyFilters()">Kaldır</button>
      </div>
      <div v-if="sessionsLoad" style="padding:3rem;text-align:center;color:#6B7280;">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
      </div>
      <div v-else-if="sessionsError" class="eisa-error-banner" style="margin-bottom:1rem;">
        <i class="fa-solid fa-triangle-exclamation"></i> {{ sessionsError }}
      </div>
      <template v-else>
        <div v-if="sessions.length === 0" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
          <i class="fa-regular fa-folder-open" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.75rem;"></i>
          <p>Bu filtreye ait kayıt bulunamadı.</p>
        </div>
        <div v-else class="eisa-panel">
          <div style="overflow-x:auto;">
            <table class="eisa-table">
              <thead>
                <tr>
                  <th>QR</th>
                  <th>Eczane</th>
                  <th>Kiosk</th>
                  <th>Tür</th>
                  <th>Durum</th>
                  <th>Hassas</th>
                  <th>Danışma</th>
                  <th>Tarih</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sessions" :key="row.id">
                  <td style="font-family:'DM Mono',monospace;font-size:0.82rem;font-weight:700;">{{ row.qr_kodu }}</td>
                  <td style="font-size:0.82rem;">{{ row.eczane_adi || '—' }}</td>
                  <td style="font-size:0.82rem;">{{ row.kiosk_ad || '—' }}</td>
                  <td>
                    <span class="eisa-pill eisa-pill-muted" style="font-size:0.7rem;">
                      {{ row.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Danışmanlık' : 'Şikayet' }}
                    </span>
                  </td>
                  <td>
                    <span class="eisa-pill" :class="DURUM_LABEL[row.durum]?.cls || 'eisa-pill-muted'" style="font-size:0.7rem;">
                      {{ DURUM_LABEL[row.durum]?.text || row.durum }}
                    </span>
                  </td>
                  <td>
                    <i v-if="row.hassas_akis" class="fa-solid fa-triangle-exclamation" style="color:#F59E0B;"></i>
                    <span v-else style="color:#6B7280;">—</span>
                  </td>
                  <td>
                    <i v-if="row.danisma_tamamlandi" class="fa-solid fa-check-circle" style="color:#10B981;"></i>
                    <span v-else style="color:#6B7280;">Bekliyor</span>
                  </td>
                  <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.olusturulma_tarihi) }}</td>
                  <td>
                    <button class="eisa-btn eisa-btn-ghost" style="font-size:0.75rem;padding:0.25rem 0.5rem;" @click="openDetail(row)">
                      Detay
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Pagination -->
          <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
            <span style="font-size:0.8rem;color:#9CA3AF;">{{ sessionsTotal }} kayıt</span>
            <div style="display:flex;gap:0.5rem;">
              <button class="eisa-btn eisa-btn-ghost" :disabled="sessionsPage <= 1"
                @click="sessionsPage--; syncUrl(); loadSessions()"><i class="fa-solid fa-chevron-left"></i></button>
              <span style="font-size:0.8rem;padding:0.4rem 0.6rem;">{{ sessionsPage }} / {{ totalPages }}</span>
              <button class="eisa-btn eisa-btn-ghost" :disabled="sessionsPage >= totalPages"
                @click="sessionsPage++; syncUrl(); loadSessions()"><i class="fa-solid fa-chevron-right"></i></button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- ── Gösterim Listesi ───────────────────────────────────────────────── -->
    <template v-if="activeTab === 'impressions'">
      <div v-if="impressionsLoad" style="padding:3rem;text-align:center;color:#6B7280;">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
      </div>
      <div v-else-if="impressionsError" class="eisa-error-banner">
        <i class="fa-solid fa-triangle-exclamation"></i> {{ impressionsError }}
      </div>
      <template v-else>
        <div v-if="impressions.length === 0" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
          <i class="fa-regular fa-folder-open" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.75rem;"></i>
          <p>Bu filtreye ait gösterim bulunamadı.</p>
        </div>
        <div v-else class="eisa-panel">
          <div style="overflow-x:auto;">
            <table class="eisa-table">
              <thead>
                <tr>
                  <th>Kampanya</th>
                  <th>Eczane</th>
                  <th>Kiosk</th>
                  <th>Süre</th>
                  <th>Tarih</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in impressions" :key="row.id">
                  <td>{{ row.campaign_adi || row.house_ad_adi || '—' }}</td>
                  <td style="font-size:0.82rem;">{{ row.eczane_adi || '—' }}</td>
                  <td style="font-size:0.82rem;">{{ row.kiosk_ad || '—' }}</td>
                  <td>{{ row.duration_played }}sn</td>
                  <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.played_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
            <span style="font-size:0.8rem;color:#9CA3AF;">{{ impressionsTotal }} gösterim</span>
            <div style="display:flex;gap:0.5rem;">
              <button class="eisa-btn eisa-btn-ghost" :disabled="impressionsPage <= 1"
                @click="impressionsPage--; loadImpressions()"><i class="fa-solid fa-chevron-left"></i></button>
              <span style="font-size:0.8rem;padding:0.4rem 0.6rem;">{{ impressionsPage }} / {{ impTotalPages }}</span>
              <button class="eisa-btn eisa-btn-ghost" :disabled="impressionsPage >= impTotalPages"
                @click="impressionsPage++; loadImpressions()"><i class="fa-solid fa-chevron-right"></i></button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- ── Olaylar Listesi (Faz 4) ───────────────────────────────────────── -->
    <template v-if="activeTab === 'events'">
      <div v-if="eventsLoad" style="padding:3rem;text-align:center;color:#6B7280;">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
      </div>
      <div v-else-if="eventsError" class="eisa-error-banner">
        <i class="fa-solid fa-triangle-exclamation"></i> {{ eventsError }}
      </div>
      <template v-else>
        <div v-if="events.length === 0" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
          <i class="fa-regular fa-folder-open" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.75rem;"></i>
          <p>Bu filtreye ait kiosk olayı bulunamadı.</p>
        </div>
        <div v-else class="eisa-panel">
          <div style="overflow-x:auto;">
            <table class="eisa-table">
              <thead>
                <tr><th>Eczane</th><th>Kiosk</th><th>Olay Türü</th><th>Önem</th><th>Mesaj</th><th>Tarih</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in events" :key="row.id">
                  <td style="font-size:0.82rem;">{{ row.eczane_adi || '—' }}</td>
                  <td style="font-size:0.82rem;">{{ row.kiosk_ad || '—' }}</td>
                  <td><span class="eisa-pill eisa-pill-muted" style="font-size:0.7rem;">{{ row.event_type }}</span></td>
                  <td>
                    <span class="eisa-pill" :class="row.severity === 'ERROR' || row.severity === 'CRITICAL' ? 'eisa-pill-danger' : row.severity === 'WARNING' ? 'eisa-pill-warning' : 'eisa-pill-muted'" style="font-size:0.7rem;">
                      {{ row.severity }}
                    </span>
                  </td>
                  <td style="font-size:0.82rem;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ row.message || '—' }}</td>
                  <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.olusturulma_tarihi) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
            <span style="font-size:0.8rem;color:#9CA3AF;">{{ eventsTotal }} olay</span>
            <div style="display:flex;gap:0.5rem;">
              <button class="eisa-btn eisa-btn-ghost" :disabled="eventsPage <= 1"
                @click="eventsPage--; loadEvents()"><i class="fa-solid fa-chevron-left"></i></button>
              <span style="font-size:0.8rem;padding:0.4rem 0.6rem;">{{ eventsPage }}</span>
              <button class="eisa-btn eisa-btn-ghost" :disabled="events.length < 50"
                @click="eventsPage++; loadEvents()"><i class="fa-solid fa-chevron-right"></i></button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- ── Detay Drawer ────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="selected" class="eisa-modal-overlay" @click.self="closeDetail">
        <div class="eisa-modal" style="max-width:520px;">
          <div class="eisa-modal-header">
            <h3>Oturum Detayı</h3>
            <button class="eisa-modal-close" @click="closeDetail"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body" style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem 1.25rem;">
            <div><p style="font-size:0.7rem;color:#9CA3AF;">QR Kodu</p><p style="font-family:'DM Mono',monospace;font-weight:700;">{{ selected.qr_kodu }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Durum</p>
              <span class="eisa-pill" :class="DURUM_LABEL[selected.durum]?.cls || 'eisa-pill-muted'">{{ DURUM_LABEL[selected.durum]?.text || selected.durum }}</span>
            </div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Eczane</p><p>{{ selected.eczane_adi || '—' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Kiosk</p><p>{{ selected.kiosk_ad || '—' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">İşlem Türü</p><p>{{ selected.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Özel Danışmanlık' : 'Şikayet' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Kategori</p><p>{{ selected.kategori_adi || selected.danisma_kategorisi_adi || '—' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Yaş / Cinsiyet</p><p>{{ selected.yas_araligi_ad || '—' }} / {{ selected.cinsiyet_ad || '—' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Hassas</p><p>{{ selected.hassas_akis ? 'Evet' : 'Hayır' }}</p></div>
            <div style="grid-column:1/span 2;"><p style="font-size:0.7rem;color:#9CA3AF;">Oluşturulma (Sunucu)</p><p>{{ fmtDT(selected.olusturulma_tarihi) }}</p></div>
            <div v-if="selected.cihaz_zamani" style="grid-column:1/span 2;"><p style="font-size:0.7rem;color:#9CA3AF;">Kiosk Saati</p><p>{{ fmtDT(selected.cihaz_zamani) }}</p></div>
            <div v-if="selected.danisma_tamamlandi" style="grid-column:1/span 2;"><p style="font-size:0.7rem;color:#9CA3AF;">Danışma Tamamlanma</p><p>{{ fmtDT(selected.danisma_tamamlanma_tarihi) }}</p></div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="closeDetail">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>
