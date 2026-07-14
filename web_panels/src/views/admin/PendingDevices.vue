<script setup>
/**
 * Onay Bekleyen Cihazlar — SuperAdmin Provisioning Yönetimi
 *
 * Henüz kayıtlı olmayan, fleet key + HMAC ile bootstrap isteği
 * göndermiş kiosk cihazlarının listesi, detayı, onayı ve reddi.
 *
 * Güvenlik: token, secret, hmac, fleet_key hiçbir zaman gösterilmez.
 */
import { ref, computed, onMounted } from 'vue';
import {
  listProvisioningRequests,
  approveProvisioningRequest,
  rejectProvisioningRequest,
  getPharmacies,
} from '../../services/devices';
import EisaLookup from '../../components/shared/EisaLookup.vue';

// ─── Veri ─────────────────────────────────────────────────────────────────────
const requests    = ref([]);
const loading     = ref(true);
const pharmacies  = ref([]);

// ─── Filtreler ─────────────────────────────────────────────────────────────────
const filterStatus = ref('PENDING');
const filterMac    = ref('');

const filtered = computed(() => {
  let list = requests.value;
  if (filterStatus.value) list = list.filter((r) => r.status === filterStatus.value);
  const q = filterMac.value.trim().toLowerCase();
  if (q) list = list.filter((r) => r.mac.toLowerCase().includes(q));
  return list;
});

// ─── Toast ─────────────────────────────────────────────────────────────────────
const toastVisible = ref(false);
const toastMessage = ref('');
const toastType    = ref('success');
let toastTimeout   = null;

function showToast(message, type = 'success') {
  if (toastTimeout) clearTimeout(toastTimeout);
  toastMessage.value = message;
  toastType.value    = type;
  toastVisible.value = true;
  toastTimeout = setTimeout(() => { toastVisible.value = false; }, 3000);
}

// ─── Veri Yükleme ─────────────────────────────────────────────────────────────
async function loadRequests() {
  loading.value = true;
  try {
    requests.value = await listProvisioningRequests();
  } finally {
    loading.value = false;
  }
}

const pharmacyOptions = computed(() =>
  pharmacies.value.map((p) => ({
    id: p.id,
    label: p.name,
    sub: `${p.ilAdi || ''}${p.ilceAdi ? ' / ' + p.ilceAdi : ''}`,
  }))
);

onMounted(async () => {
  const [pharmList] = await Promise.all([getPharmacies(), loadRequests()]);
  pharmacies.value = pharmList;
});

// ─── Detay Modal ───────────────────────────────────────────────────────────────
const detailModalOpen = ref(false);
const detailTarget    = ref(null);

function openDetail(req) {
  detailTarget.value  = req;
  detailModalOpen.value = true;
}
function closeDetail() {
  detailModalOpen.value = false;
  detailTarget.value    = null;
}

// ─── Onay Modal ────────────────────────────────────────────────────────────────
const approveModalOpen  = ref(false);
const approveTarget     = ref(null);
const approveForm       = ref({ eczane_id: '', ad: '' });
const approveError      = ref('');
const approveSaving     = ref(false);

function openApprove(req) {
  approveTarget.value    = req;
  approveForm.value      = { eczane_id: '', ad: '' };
  approveError.value     = '';
  approveModalOpen.value = true;
}
function closeApprove() {
  approveModalOpen.value = false;
  approveTarget.value    = null;
}

async function confirmApprove() {
  const { eczane_id, ad } = approveForm.value;
  if (!eczane_id) { approveError.value = 'Eczane seçimi zorunludur.'; return; }
  if (!ad.trim()) { approveError.value = 'Kiosk adı zorunludur.'; return; }

  approveSaving.value = true;
  approveError.value  = '';
  try {
    await approveProvisioningRequest(approveTarget.value.id, {
      eczane_id: Number(eczane_id),
      ad: ad.trim(),
    });
    await loadRequests();
    closeApprove();
    showToast('Cihaz başarıyla onaylandı ve kiosk kaydı oluşturuldu.');
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Onaylama sırasında hata oluştu.';
    approveError.value = detail;
  } finally {
    approveSaving.value = false;
  }
}

// ─── Red Modal ─────────────────────────────────────────────────────────────────
const rejectModalOpen  = ref(false);
const rejectTarget     = ref(null);
const rejectReason     = ref('');
const rejectError      = ref('');
const rejectSaving     = ref(false);

function openReject(req) {
  rejectTarget.value    = req;
  rejectReason.value    = '';
  rejectError.value     = '';
  rejectModalOpen.value = true;
}
function closeReject() {
  rejectModalOpen.value = false;
  rejectTarget.value    = null;
}

async function confirmReject() {
  rejectSaving.value = true;
  rejectError.value  = '';
  try {
    await rejectProvisioningRequest(rejectTarget.value.id, {
      rejection_reason: rejectReason.value.trim(),
    });
    await loadRequests();
    closeReject();
    showToast('Cihaz reddedildi.', 'warning');
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Red işlemi sırasında hata oluştu.';
    rejectError.value = detail;
  } finally {
    rejectSaving.value = false;
  }
}

// ─── Yardımcılar ──────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function statusLabel(s) {
  if (s === 'PENDING')  return 'Onay Bekliyor';
  if (s === 'APPROVED') return 'Onaylandı';
  if (s === 'REJECTED') return 'Reddedildi';
  return s;
}

function statusClass(s) {
  if (s === 'PENDING')  return 'badge-pending';
  if (s === 'APPROVED') return 'badge-approved';
  if (s === 'REJECTED') return 'badge-rejected';
  return '';
}

// Metadata label map — kullanıcı dostu alan adları
const METADATA_LABELS = {
  hostname:         'Makine Adı',
  os_type:          'İşletim Sistemi',
  os_platform:      'Platform',
  os_release:       'OS Sürümü',
  arch:             'Mimari',
  cpu_model:        'İşlemci',
  cpu_cores:        'Çekirdek Sayısı',
  total_memory_mb:  'Toplam RAM (MB)',
  node_version:     'Node.js Sürümü',
  uptime_seconds:   'Çalışma Süresi',
};

// Güvenli metadata alanlarını sıralı dizi olarak döndürür
function safeMetadataEntries(metadata) {
  if (!metadata || typeof metadata !== 'object') return [];
  const BLOCKED = new Set(['token', 'secret', 'hmac', 'authorization', 'app_key', 'iot_token']);
  return Object.entries(metadata)
    .filter(([k]) => !BLOCKED.has(k.toLowerCase()) && k !== 'ip_addresses')
    .map(([k, v]) => ({
      key: k,
      label: METADATA_LABELS[k] || k,
      value: k === 'uptime_seconds' ? formatUptime(v) : String(v),
    }));
}

function formatUptime(seconds) {
  const s = Number(seconds);
  if (!s) return '—';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h} sa ${m} dk`;
  return `${m} dk`;
}

// Sadece safeMetadataDisplay eski çağrıları için (geriye dönük)
function safeMetadataDisplay(metadata) {
  const entries = safeMetadataEntries(metadata);
  if (!entries.length) return '—';
  return entries.map((e) => `${e.label}: ${e.value}`).join(' · ');
}
</script>

<template>
  <div class="pending-devices">
    <div class="page-header">
      <h1>Onay Bekleyen Cihazlar</h1>
      <p class="page-subtitle">
        Fleet key + HMAC kimlik doğrulamasından geçmiş, henüz kayıtlı olmayan kiosk cihazları.
        Admin onayı ile gerçek Kiosk kaydına dönüştürülür.
      </p>
    </div>

    <!-- Filtreler -->
    <div class="filter-bar">
      <select v-model="filterStatus" class="filter-select">
        <option value="">Tümü</option>
        <option value="PENDING">Onay Bekliyor</option>
        <option value="APPROVED">Onaylandı</option>
        <option value="REJECTED">Reddedildi</option>
      </select>
      <input
        v-model="filterMac"
        type="text"
        class="filter-input"
        placeholder="MAC adresine göre ara…"
      />
      <button class="btn btn-secondary" @click="loadRequests" :disabled="loading">
        <i class="fa-solid fa-rotate-right"></i> Yenile
      </button>
    </div>

    <!-- Yükleniyor -->
    <div v-if="loading" class="loading-state">
      <i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor…
    </div>

    <!-- Boş durum -->
    <div v-else-if="!filtered.length" class="empty-state">
      <p>Gösterilecek cihaz talebi bulunamadı.</p>
    </div>

    <!-- Tablo -->
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Durum</th>
          <th>MAC Adresi</th>
          <th>Hostname</th>
          <th>İlk Görülme</th>
          <th>Son Görülme</th>
          <th>Başvuru Sayısı</th>
          <th>İşlemler</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="req in filtered" :key="req.id">
          <td>
            <span class="badge" :class="statusClass(req.status)">
              {{ statusLabel(req.status) }}
            </span>
          </td>
          <td class="font-mono">{{ req.mac }}</td>
          <td>{{ req.hostname || '—' }}</td>
          <td>{{ formatDate(req.firstSeenAt) }}</td>
          <td>{{ formatDate(req.lastSeenAt) }}</td>
          <td>{{ req.requestCount }}</td>
          <td>
            <div class="action-buttons">
              <button class="btn btn-sm btn-info" @click="openDetail(req)" title="Detay">
                <i class="fa-solid fa-eye"></i>
              </button>
              <button
                v-if="req.status === 'PENDING'"
                class="btn btn-sm btn-success"
                @click="openApprove(req)"
                title="Onayla"
              >
                <i class="fa-solid fa-check"></i> Onayla
              </button>
              <button
                v-if="req.status === 'PENDING'"
                class="btn btn-sm btn-danger"
                @click="openReject(req)"
                title="Reddet"
              >
                <i class="fa-solid fa-times"></i> Reddet
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Detay Modal -->
    <div v-if="detailModalOpen" class="modal-overlay" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-header">
          <h2>Cihaz Detayı</h2>
          <button class="modal-close" @click="closeDetail">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="modal-body" v-if="detailTarget">
          <div class="detail-row"><span>Durum:</span>
            <span class="badge" :class="statusClass(detailTarget.status)">
              {{ statusLabel(detailTarget.status) }}
            </span>
          </div>
          <div class="detail-row"><span>MAC Adresi:</span><code>{{ detailTarget.mac }}</code></div>
          <div class="detail-row"><span>Hostname:</span>{{ detailTarget.hostname || '—' }}</div>
          <div class="detail-row"><span>İlk Görülme:</span>{{ formatDate(detailTarget.firstSeenAt) }}</div>
          <div class="detail-row"><span>Son Görülme:</span>{{ formatDate(detailTarget.lastSeenAt) }}</div>
          <div class="detail-row"><span>Başvuru Sayısı:</span>{{ detailTarget.requestCount }}</div>
          <!-- Cihaz donanım / yazılım bilgileri -->
          <div class="detail-section-title">Cihaz Bilgileri</div>
          <template v-if="safeMetadataEntries(detailTarget.deviceMetadata).length">
            <div
              v-for="entry in safeMetadataEntries(detailTarget.deviceMetadata)"
              :key="entry.key"
              class="detail-row"
            >
              <span>{{ entry.label }}:</span>
              <span class="detail-value">{{ entry.value }}</span>
            </div>
            <!-- IP adresleri ayrı listele -->
            <template v-if="detailTarget.deviceMetadata?.ip_addresses?.length">
              <div class="detail-row">
                <span>IP Adresleri:</span>
                <div class="ip-list">
                  <span
                    v-for="ip in detailTarget.deviceMetadata.ip_addresses"
                    :key="ip.address"
                    class="ip-badge"
                  >
                    <code>{{ ip.address }}</code>
                    <em>{{ ip.iface }}</em>
                  </span>
                </div>
              </div>
            </template>
          </template>
          <div v-else class="detail-row"><span>Cihaz Bilgileri:</span><span>—</span></div>
          <template v-if="detailTarget.status === 'APPROVED'">
            <div class="detail-row"><span>Onaylayan:</span>{{ detailTarget.approvedBy || '—' }}</div>
            <div class="detail-row"><span>Onay Tarihi:</span>{{ formatDate(detailTarget.approvedAt) }}</div>
            <div class="detail-row"><span>Kiosk Adı:</span>{{ detailTarget.kioskAd || '—' }}</div>
          </template>
          <template v-if="detailTarget.status === 'REJECTED'">
            <div class="detail-row"><span>Reddeden:</span>{{ detailTarget.rejectedBy || '—' }}</div>
            <div class="detail-row"><span>Red Tarihi:</span>{{ formatDate(detailTarget.rejectedAt) }}</div>
            <div class="detail-row"><span>Red Nedeni:</span>{{ detailTarget.rejectionReason || '—' }}</div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeDetail">Kapat</button>
        </div>
      </div>
    </div>

    <!-- Onay Modal -->
    <div v-if="approveModalOpen" class="modal-overlay" @click.self="closeApprove">
      <div class="modal">
        <div class="modal-header">
          <h2>Cihazı Onayla</h2>
          <button class="modal-close" @click="closeApprove">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="modal-body" v-if="approveTarget">
          <p class="modal-info">
            <strong>{{ approveTarget.mac }}</strong> MAC adresli cihazı onaylıyorsunuz.
            Bir eczane seçin ve kiosk adı belirleyin.
          </p>
          <div v-if="approveError" class="form-error">{{ approveError }}</div>
          <div class="form-group">
            <label>Eczane <span class="required">*</span></label>
            <EisaLookup
              v-model="approveForm.eczane_id"
              :options="pharmacyOptions"
              placeholder="Eczane adı, il veya ilçe ile ara…"
              :clearable="true"
            />
          </div>
          <div class="form-group">
            <label>Kiosk Adı <span class="required">*</span></label>
            <input
              v-model="approveForm.ad"
              type="text"
              class="form-control"
              placeholder="Örn: Kiosk 1"
              maxlength="50"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeApprove" :disabled="approveSaving">
            İptal
          </button>
          <button
            class="btn btn-success"
            @click="confirmApprove"
            :disabled="approveSaving"
          >
            <i v-if="approveSaving" class="fa-solid fa-circle-notch fa-spin"></i>
            <span>{{ approveSaving ? 'Onaylanıyor…' : 'Onayla' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Red Modal -->
    <div v-if="rejectModalOpen" class="modal-overlay" @click.self="closeReject">
      <div class="modal">
        <div class="modal-header">
          <h2>Cihazı Reddet</h2>
          <button class="modal-close" @click="closeReject">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="modal-body" v-if="rejectTarget">
          <p class="modal-info">
            <strong>{{ rejectTarget.mac }}</strong> MAC adresli cihazı reddediyorsunuz.
          </p>
          <div v-if="rejectError" class="form-error">{{ rejectError }}</div>
          <div class="form-group">
            <label>Red Nedeni (opsiyonel)</label>
            <textarea
              v-model="rejectReason"
              class="form-control"
              rows="3"
              maxlength="500"
              placeholder="Red nedeni (opsiyonel)…"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeReject" :disabled="rejectSaving">
            İptal
          </button>
          <button
            class="btn btn-danger"
            @click="confirmReject"
            :disabled="rejectSaving"
          >
            <i v-if="rejectSaving" class="fa-solid fa-circle-notch fa-spin"></i>
            <span>{{ rejectSaving ? 'Reddediliyor…' : 'Reddet' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toastVisible" class="toast" :class="`toast-${toastType}`">
      {{ toastMessage }}
    </div>
  </div>
</template>

<style scoped>
.pending-devices { padding: 1.5rem; max-width: 1200px; }

.page-header { margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.5rem; font-weight: 600; margin: 0 0 0.25rem; }
.page-subtitle { color: var(--color-text-muted, #6b7280); font-size: 0.875rem; margin: 0; }

.filter-bar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.filter-select,
.filter-input {
  padding: 0.4rem 0.75rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 6px;
  font-size: 0.875rem;
  background: var(--color-surface, #fff);
}
.filter-input { flex: 1; min-width: 200px; }

.loading-state,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-muted, #6b7280);
}
.loading-state i,
.empty-state i { font-size: 2rem; margin-bottom: 0.5rem; display: block; }

.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th,
.data-table td {
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  text-align: left;
}
.data-table th { font-weight: 600; background: var(--color-surface-raised, #f9fafb); }
.data-table tr:hover td { background: var(--color-surface-hover, #f3f4f6); }
.font-mono { font-family: monospace; font-size: 0.8rem; }

.badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-pending  { background: #fef3c7; color: #92400e; }
.badge-approved { background: #d1fae5; color: #065f46; }
.badge-rejected { background: #fee2e2; color: #991b1b; }

.action-buttons { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.4rem 0.75rem;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500;
  transition: opacity 0.15s; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-sm { padding: 0.3rem 0.55rem; font-size: 0.8rem; }
.btn-secondary { background: var(--color-surface-raised, #f3f4f6); color: var(--color-text, #111); }
.btn-secondary:hover:not(:disabled) { background: var(--color-surface-hover, #e5e7eb); }
.btn-success  { background: #059669; color: #fff; }
.btn-success:hover:not(:disabled) { background: #047857; }
.btn-danger   { background: #dc2626; color: #fff; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; }
.btn-info     { background: #0ea5e9; color: #fff; }
.btn-info:hover:not(:disabled) { background: #0284c7; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: var(--color-surface, #fff);
  border-radius: 10px; width: 480px; max-width: 95vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem; border-bottom: 1px solid var(--color-border, #e5e7eb);
}
.modal-header h2 { margin: 0; font-size: 1.1rem; font-weight: 600; }
.modal-close { background: none; border: none; cursor: pointer; font-size: 1.1rem;
  color: var(--color-text-muted, #6b7280); }
.modal-body { padding: 1.25rem; }
.modal-footer {
  display: flex; gap: 0.5rem; justify-content: flex-end;
  padding: 0.75rem 1.25rem; border-top: 1px solid var(--color-border, #e5e7eb);
}

.modal-info { margin: 0 0 1rem; font-size: 0.9rem; color: var(--color-text-muted, #4b5563); }
.detail-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.875rem; }
.detail-row > span:first-child { font-weight: 500; min-width: 130px; }
.required { color: #dc2626; }

.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.3rem; }
.form-control {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border, #d1d5db); border-radius: 6px;
  font-size: 0.875rem; background: var(--color-surface, #fff);
}
.form-error {
  background: #fee2e2; color: #991b1b; border-radius: 6px;
  padding: 0.5rem 0.75rem; font-size: 0.85rem; margin-bottom: 0.75rem;
}

/* Toast */
.toast {
  position: fixed; bottom: 1.5rem; right: 1.5rem;
  padding: 0.75rem 1.25rem; border-radius: 8px;
  font-size: 0.9rem; font-weight: 500; z-index: 200;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.toast-success { background: #059669; color: #fff; }
.toast-warning { background: #d97706; color: #fff; }
.toast-error   { background: #dc2626; color: #fff; }

/* Metadata */
.detail-section-title {
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--color-text-muted, #6b7280);
  margin: 0.75rem 0 0.35rem; padding-top: 0.5rem;
  border-top: 1px solid var(--color-border, #e5e7eb);
}
.detail-value { font-family: monospace; font-size: 0.82rem; word-break: break-all; }
.ip-list { display: flex; flex-direction: column; gap: 0.2rem; }
.ip-badge {
  display: inline-flex; align-items: center; gap: 0.35rem;
  font-size: 0.8rem;
}
.ip-badge code { background: #f1f5f9; border-radius: 4px; padding: 0.1rem 0.4rem; font-size: 0.8rem; }
.ip-badge em { color: var(--color-text-muted, #6b7280); font-style: normal; font-size: 0.75rem; }
</style>
