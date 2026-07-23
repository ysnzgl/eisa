<script setup>
/**
 * DOOH Kontrol Merkezi — Faz 6
 *
 * Tek ekranda:
 *  - Aktif kampanya özeti
 *  - Generation job listesi + polling
 *  - Kiosk desired/applied/horizon durumu
 *
 * Route: /admin/dooh/control-center (SuperAdmin)
 * Polling: yalnız PENDING/RUNNING joblar için; unmount'ta temizlenir.
 * Kiosk rollout durumu: calcKioskRolloutStatus composable (tek merkezi kaynak).
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { toast } from 'vue-sonner';
import {
  listCampaignsV2, bulkActionCampaignsV2,
  listGenerationJobs, getGenerationJob,
  generatePlaylists,
  getKioskHealth,
} from '../../services/dooh.js';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import { calcKioskRolloutStatus } from '../../composables/useKioskRolloutStatus.js';

// ─── Kampanyalar ──────────────────────────────────────────────────────────────
const campaigns   = ref([]);
const campLoading = ref(false);
const campSearch  = ref('');
const campFilter  = ref('ALL');

// Tek merkezi status badge mapping
const STATUS_MAP = {
  ACTIVE:    { label: 'Aktif',      cls: 'eisa-pill-success' },
  PAUSED:    { label: 'Duraklatıldı', cls: 'eisa-pill-warning' },
  COMPLETED: { label: 'Tamamlandı', cls: 'eisa-pill-muted' },
  DRAFT:     { label: 'Taslak',     cls: 'eisa-pill-muted' },
  CANCELLED: { label: 'İptal',      cls: 'eisa-pill-danger' },
};

function campStatus(c) { return STATUS_MAP[c.status] || { label: c.status, cls: '' }; }

const filteredCampaigns = computed(() => {
  const q = campSearch.value.trim().toLocaleLowerCase('tr');
  return campaigns.value.filter((c) => {
    if (campFilter.value !== 'ALL' && c.status !== campFilter.value) return false;
    if (!q) return true;
    return `${c.name} ${c.advertiser_name || ''}`.toLocaleLowerCase('tr').includes(q);
  });
});

async function loadCampaigns() {
  campLoading.value = true;
  try {
    const { data } = await listCampaignsV2();
    campaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error('Kampanyalar yüklenemedi.');
  } finally { campLoading.value = false; }
}

// ── Campaign actions ──────────────────────────────────────────────────────────
const deleteConfirmOpen  = ref(false);
const deleteTarget       = ref(null);
const deleteLoading      = ref(false);
const actionLoading      = ref(new Set());

function askDelete(c) { deleteTarget.value = c; deleteConfirmOpen.value = true; }
async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleteLoading.value = true;
  try {
    await bulkActionCampaignsV2('delete', [deleteTarget.value.id]);
    deleteConfirmOpen.value = false; deleteTarget.value = null;
    await loadCampaigns(); toast.success('Kampanya silindi.');
  } catch (e) { toast.error(e?.response?.data?.detail || 'Silme başarısız.'); }
  finally { deleteLoading.value = false; }
}

async function campAction(action, campaign) {
  const id = campaign.id;
  const loading = new Set(actionLoading.value); loading.add(id); actionLoading.value = loading;
  try {
    await bulkActionCampaignsV2(action, [id]);
    await loadCampaigns();
    toast.success(action === 'pause' ? 'Kampanya duraklatıldı.' : 'Kampanya aktifleştirildi.');
  } catch (e) {
    toast.error(e?.response?.data?.error || 'İşlem başarısız.');
  } finally {
    const s = new Set(actionLoading.value); s.delete(id); actionLoading.value = s;
  }
}

// ─── Generation Jobs ──────────────────────────────────────────────────────────
const jobs        = ref([]);
const jobsLoading = ref(false);

// Job status mapping
const JOB_STATUS_MAP = {
  PENDING: { label: 'Bekliyor',        cls: 'eisa-pill-warning' },
  RUNNING: { label: 'Çalışıyor',       cls: 'eisa-pill-info'    },
  DONE:    { label: 'Tamamlandı',      cls: 'eisa-pill-success'  },
  FAILED:  { label: 'Başarısız',       cls: 'eisa-pill-danger'   },
  RETRY:   { label: 'Tekrar Deniyor',  cls: 'eisa-pill-warning'  },
};
// Backward compat: eski contract COMPLETED → yeni DONE
function jobStatusLabel(s) { return JOB_STATUS_MAP[s] || JOB_STATUS_MAP[s === 'COMPLETED' ? 'DONE' : s] || { label: s, cls: '' }; }
// job_id veya id backward compat
function jobId(j) { return j.job_id || j.id; }

const activeJobs = computed(() =>
  jobs.value.filter((j) => j.status === 'PENDING' || j.status === 'RUNNING')
);
const hasActiveJobs = computed(() => activeJobs.value.length > 0);

async function loadJobs() {
  jobsLoading.value = true;
  try {
    const { data } = await listGenerationJobs();
    jobs.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch { /* non-critical */ }
  finally { jobsLoading.value = false; }
}

// Polling: yalnız aktif joblar için çalışır; terminal durumda durur
let _pollInterval = null;
function startPolling() {
  if (_pollInterval) return;
  _pollInterval = setInterval(async () => {
    if (!hasActiveJobs.value) { stopPolling(); return; }
    await loadJobs();
  }, 8000);
}
function stopPolling() {
  clearInterval(_pollInterval);
  _pollInterval = null;
}

async function triggerGenerate() {
  try {
    const { data } = await generatePlaylists({});
    jobs.value = [data, ...jobs.value];
    toast.success('Playlist üretimi başlatıldı.');
    startPolling();
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Üretim başlatılamadı.');
  }
}

// ─── Kiosk Rollout Durumu ─────────────────────────────────────────────────────
const kiosks         = ref([]);
const kiosksLoading  = ref(false);
const kiosksError    = ref('');
const kioskSearch    = ref('');
const kioskFilter    = ref('all'); // 'all' | 'up_to_date' | 'behind' | 'ack_pending' | 'offline'
const serverHorizonEnd = ref(null);

// Europe/Istanbul bugünü kullan (backend horizon_end ile karşılaştırma)
// Browser timezone'una kör biçimde güvenme
function getIstanbulToday() {
  try {
    const d = new Date();
    const ist = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(d);
    return ist; // YYYY-MM-DD
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

async function loadKiosks() {
  kiosksLoading.value = true; kiosksError.value = '';
  try {
    const { data } = await getKioskHealth();
    kiosks.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    kiosksError.value = 'Kiosk durumu yüklenemedi.';
  } finally { kiosksLoading.value = false; }
}

const istanbulToday = getIstanbulToday();

const kiosksWithStatus = computed(() => {
  const horizonEnd = serverHorizonEnd.value;
  return kiosks.value.map((k) => ({
    ...k,
    rollout: calcKioskRolloutStatus(k, horizonEnd),
  }));
});

const filteredKiosks = computed(() => {
  const q = kioskSearch.value.trim().toLowerCase();
  return kiosksWithStatus.value.filter((k) => {
    if (kioskFilter.value !== 'all' && k.rollout.status !== kioskFilter.value) return false;
    if (!q) return true;
    return `${k.ad || ''} ${k.mac_adresi || ''} ${k.eczane_adi || ''}`.toLowerCase().includes(q);
  });
});

const rolloutCounts = computed(() => {
  const list = kiosksWithStatus.value;
  return {
    total:       list.length,
    upToDate:    list.filter((k) => k.rollout.status === 'up_to_date').length,
    behind:      list.filter((k) => k.rollout.status === 'behind').length,
    ackPending:  list.filter((k) => k.rollout.status === 'ack_pending').length,
    horizonStale:list.filter((k) => k.rollout.status === 'horizon_stale').length,
    offline:     list.filter((k) => k.rollout.status === 'offline').length,
  };
});

const ROLLOUT_ACCENT_MAP = {
  up_to_date:    { cls: 'eisa-pill-success', label: 'Güncel' },
  behind:        { cls: 'eisa-pill-danger',  label: 'Geride' },
  ack_pending:   { cls: 'eisa-pill-warning', label: 'ACK Bekleniyor' },
  horizon_stale: { cls: 'eisa-pill-warning', label: 'Horizon Eksik' },
  offline:       { cls: 'eisa-pill-muted',   label: 'Çevrimdışı' },
  no_publish:    { cls: 'eisa-pill-muted',   label: 'Yayın Yok' },
  unknown:       { cls: '',                  label: 'Bilinmiyor' },
};

function timeSince(iso) {
  if (!iso) return '—';
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (d < 60)    return `${d}sn`;
  if (d < 3600)  return `${Math.floor(d/60)}dk`;
  if (d < 86400) return `${Math.floor(d/3600)}sa`;
  return `${Math.floor(d/86400)}g`;
}

// ─── Özet stats ───────────────────────────────────────────────────────────────
const summaryStats = computed(() => ({
  activeCampaigns: campaigns.value.filter((c) => c.status === 'ACTIVE').length,
  pendingJobs:     jobs.value.filter((j) => j.status === 'PENDING' || j.status === 'RUNNING').length,
  failedJobs:      jobs.value.filter((j) => j.status === 'FAILED').length,
  behindKiosks:    rolloutCounts.value.behind + rolloutCounts.value.ackPending + rolloutCounts.value.horizonStale,
}));

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadCampaigns(), loadJobs(), loadKiosks()]);
  if (hasActiveJobs.value) startPolling();
});

onUnmounted(() => stopPolling());

async function refreshAll() {
  await Promise.all([loadCampaigns(), loadJobs(), loadKiosks()]);
  if (hasActiveJobs.value) startPolling();
  else stopPolling();
}
</script>

<template>
  <div class="eisa-page dooh-control-center">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">DOOH</p>
        <h1 class="eisa-page-title">Kontrol Merkezi</h1>
        <p class="eisa-page-subtitle">Kampanya, playlist üretimi ve kiosk dağıtım durumunu izle.</p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn" @click="refreshAll">
          <i class="fa-solid fa-rotate"></i> Yenile
        </button>
        <button class="eisa-btn eisa-btn-cta" @click="triggerGenerate">
          <i class="fa-solid fa-play"></i> Playlist Üret
        </button>
      </div>
    </header>

    <!-- Özet kartlar -->
    <section class="eisa-stats" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr))">
      <div class="eisa-stat-card">
        <span class="eisa-stat-label">Aktif Kampanya</span>
        <span class="eisa-stat-value">{{ summaryStats.activeCampaigns }}</span>
      </div>
      <div class="eisa-stat-card" :class="summaryStats.pendingJobs > 0 ? 'eisa-stat-card--amber' : ''">
        <span class="eisa-stat-label">Bekleyen İş</span>
        <span class="eisa-stat-value">{{ summaryStats.pendingJobs }}</span>
      </div>
      <div class="eisa-stat-card" :class="summaryStats.failedJobs > 0 ? 'eisa-stat-card--red' : ''">
        <span class="eisa-stat-label">Başarısız İş</span>
        <span class="eisa-stat-value">{{ summaryStats.failedJobs }}</span>
      </div>
      <div class="eisa-stat-card" :class="summaryStats.behindKiosks > 0 ? 'eisa-stat-card--red' : ''">
        <span class="eisa-stat-label">Geride Kiosk</span>
        <span class="eisa-stat-value">{{ summaryStats.behindKiosks }}</span>
      </div>
      <div class="eisa-stat-card eisa-stat-card--green">
        <span class="eisa-stat-label">Güncel Kiosk</span>
        <span class="eisa-stat-value">{{ rolloutCounts.upToDate }}</span>
      </div>
    </section>

    <!-- Kampanya Listesi -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Kampanyalar</h2>
        <div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
          <input v-model="campSearch" type="search" class="eisa-field" placeholder="Ara…" style="width:200px" />
          <select v-model="campFilter" class="eisa-field" style="width:150px">
            <option value="ALL">Tüm Durumlar</option>
            <option value="ACTIVE">Aktif</option>
            <option value="PAUSED">Duraklatıldı</option>
            <option value="COMPLETED">Tamamlandı</option>
          </select>
        </div>
      </div>
      <div class="eisa-panel-body">
        <div v-if="campLoading" class="empty-row">Yükleniyor…</div>
        <div v-else-if="!filteredCampaigns.length" class="empty-row">
          {{ campSearch || campFilter !== 'ALL' ? 'Filtre ile eşleşen kampanya yok.' : 'Kampanya bulunamadı.' }}
        </div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>Kampanya</th>
                <th>İlan Veren</th>
                <th>Tarih</th>
                <th>Durum</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in filteredCampaigns" :key="c.id">
                <td><strong>{{ c.name }}</strong></td>
                <td class="cell-muted">{{ c.advertiser_name || '—' }}</td>
                <td class="cell-muted">{{ c.start_date?.slice(0,10) }} → {{ c.end_date?.slice(0,10) }}</td>
                <td>
                  <span class="eisa-pill" :class="campStatus(c).cls">{{ campStatus(c).label }}</span>
                </td>
                <td class="cell-actions">
                  <button v-if="c.status === 'ACTIVE'" class="eisa-icon-btn" title="Duraklat"
                          :disabled="actionLoading.has(c.id)" @click="campAction('pause', c)">
                    <i class="fa-solid fa-pause"></i>
                  </button>
                  <button v-else-if="c.status === 'PAUSED'" class="eisa-icon-btn" title="Aktifleştir"
                          :disabled="actionLoading.has(c.id)" @click="campAction('activate', c)">
                    <i class="fa-solid fa-play"></i>
                  </button>
                  <button class="eisa-icon-btn danger" title="Sil" @click="askDelete(c)">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Generation Jobs -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">
          Playlist Üretim İşleri
          <span v-if="hasActiveJobs" style="font-size:.75rem;color:#f59e0b;margin-left:.5rem">
            <i class="fa-solid fa-circle-notch fa-spin"></i> İş devam ediyor…
          </span>
        </h2>
        <button class="eisa-btn" @click="loadJobs">
          <i class="fa-solid fa-rotate"></i> Yenile
        </button>
      </div>
      <div class="eisa-panel-body">
        <div v-if="jobsLoading" class="empty-row">Yükleniyor…</div>
        <div v-else-if="!jobs.length" class="empty-row">Henüz üretim işi yok.</div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>İş ID</th>
                <th>Tür</th>
                <th>Tarih</th>
                <th>Durum</th>
                <th>İlerleme</th>
                <th>Başlangıç</th>
                <th>Bitiş</th>
                <th>Hata</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="j in jobs.slice(0, 30)" :key="jobId(j)">
                <td class="cell-muted" style="font-family:monospace;font-size:.75rem">{{ jobId(j)?.slice(0,8) }}…</td>
                <td class="cell-muted">{{ j.triggered_by || '—' }}</td>
                <td class="cell-muted">{{ j.target_date || '—' }}</td>
                <td>
                  <span class="eisa-pill" :class="jobStatusLabel(j.status).cls">{{ jobStatusLabel(j.status).label }}</span>
                </td>
                <td class="cell-muted">
                  <span v-if="j.total_kiosks">{{ j.done_kiosks }}/{{ j.total_kiosks }}</span>
                  <span v-else>—</span>
                </td>
                <td class="cell-muted">{{ j.started_at ? timeSince(j.started_at) + ' önce' : '—' }}</td>
                <td class="cell-muted">{{ j.finished_at ? timeSince(j.finished_at) + ' önce' : '—' }}</td>
                <td class="cell-muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="j.error_detail">
                  {{ j.error_detail ? j.error_detail.slice(0,80) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Kiosk Rollout Durumu -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Kiosk Dağıtım Durumu</h2>
        <div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
          <input v-model="kioskSearch" type="search" class="eisa-field" placeholder="Kiosk/eczane ara…" style="width:200px" />
          <select v-model="kioskFilter" class="eisa-field" style="width:170px">
            <option value="all">Tüm Durumlar</option>
            <option value="up_to_date">Güncel</option>
            <option value="behind">Geride</option>
            <option value="ack_pending">ACK Bekleniyor</option>
            <option value="horizon_stale">Horizon Eksik</option>
            <option value="offline">Çevrimdışı</option>
          </select>
          <button class="eisa-btn" @click="loadKiosks">
            <i class="fa-solid fa-rotate"></i>
          </button>
        </div>
      </div>

      <!-- Rollout özet bar -->
      <div v-if="kiosks.length" style="display:flex;gap:.5rem;flex-wrap:wrap;padding:.75rem 1.25rem;border-bottom:1px solid #f1f0ec">
        <span class="eisa-pill eisa-pill-success">Güncel: {{ rolloutCounts.upToDate }}</span>
        <span class="eisa-pill eisa-pill-danger">Geride: {{ rolloutCounts.behind }}</span>
        <span class="eisa-pill eisa-pill-warning">ACK Bekleniyor: {{ rolloutCounts.ackPending }}</span>
        <span class="eisa-pill eisa-pill-warning">Horizon Eksik: {{ rolloutCounts.horizonStale }}</span>
        <span class="eisa-pill eisa-pill-muted">Çevrimdışı: {{ rolloutCounts.offline }}</span>
      </div>

      <div class="eisa-panel-body">
        <div v-if="kiosksLoading" class="empty-row">Yükleniyor…</div>
        <div v-else-if="kiosksError" class="empty-row" style="color:#dc2626">{{ kiosksError }}</div>
        <div v-else-if="!filteredKiosks.length" class="empty-row">
          {{ kioskSearch || kioskFilter !== 'all' ? 'Filtre ile eşleşen kiosk yok.' : 'Kiosk bulunamadı.' }}
        </div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>Kiosk</th>
                <th>Eczane</th>
                <th>Son Görülme</th>
                <th>Desired</th>
                <th>Applied</th>
                <th>Applied Zaman</th>
                <th>Horizon</th>
                <th>Durum</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in filteredKiosks" :key="k.id">
                <td>
                  <strong>{{ k.ad }}</strong>
                  <div class="cell-muted" style="font-size:.75rem;font-family:monospace">{{ k.mac_adresi }}</div>
                </td>
                <td class="cell-muted">{{ k.eczane_adi || '—' }}</td>
                <td class="cell-muted">{{ timeSince(k.son_goruldu) }}</td>
                <td style="font-family:monospace;font-size:.85rem">{{ k.last_playlist_version ?? '—' }}</td>
                <td style="font-family:monospace;font-size:.85rem">
                  <!-- applied null = eski kiosk / ACK vermemiş; hata değil -->
                  <span :style="k.applied_playlist_version == null ? 'color:#94a3b8' : ''">
                    {{ k.applied_playlist_version ?? 'null' }}
                  </span>
                </td>
                <td class="cell-muted">{{ timeSince(k.playlist_applied_at) }}</td>
                <td class="cell-muted" style="font-size:.75rem">
                  {{ k.applied_horizon_start || '—' }} → {{ k.applied_horizon_end || '—' }}
                </td>
                <td>
                  <span class="eisa-pill" :class="(ROLLOUT_ACCENT_MAP[k.rollout.status] || {}).cls">
                    {{ k.rollout.label }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Silme onay modal -->
    <EisaDeleteConfirm
      :open="deleteConfirmOpen"
      title="Kampanyayı Sil"
      :message="deleteTarget ? `'${deleteTarget.name}' kampanyası kalıcı olarak silinecek.` : ''"
      confirm-label="Evet, Sil"
      :loading="deleteLoading"
      @confirm="confirmDelete"
      @cancel="deleteConfirmOpen = false; deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.eisa-stat-card--amber { border-left: 3px solid #f59e0b; }
.eisa-stat-card--red   { border-left: 3px solid #dc2626; }
.eisa-stat-card--green { border-left: 3px solid #16a34a; }
</style>
