<script setup>
/**
 * Cihaz Yönetimi — Eczane Listesi + Kiosk İzleme Paneli
 * Modül 1: Süper Admin Device Management
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import {
  getPharmacies,
  createPharmacy,
  updatePharmacy,
  deletePharmacy,
  getKioskStatus,
  getKiosk,
  listProvisioningRequests,
  createKiosk,
  updateKiosk,
  deleteKiosk,
  resetKioskDeviceId,
  transferKiosk,
  listKioskAudioLibrary,
  previewKioskAudio,
  deleteKioskLibraryAudio,
  uploadKioskAudioLibrary,
  setKioskIdleAudios,
} from '../../services/devices';
import { toast } from 'vue-sonner';
import { getIller, getIlceler } from '../../services/lookups';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';

// ─── Lookups ──────────────────────────────────────────────────────────────────
const iller   = ref([]);
const ilceler = ref([]);
const ilcelerYukleniyor = ref(false);

async function loadIlceler(ilId) {
  if (!ilId) { ilceler.value = []; return; }
  ilcelerYukleniyor.value = true;
  try   { ilceler.value = await getIlceler(ilId); }
  finally { ilcelerYukleniyor.value = false; }
}

// ─── Veri ────────────────────────────────────────────────────────────────────
const pharmacies    = ref([]);
const kiosks        = ref([]);
const provisioningRequests = ref([]);
const loadingPharm  = ref(true);
const loadingKiosk  = ref(true);
const loadingProvisioning = ref(true);
const pharmacySearch = ref('');

// ─── Eczane Modal ─────────────────────────────────────────────────────────────
const modalOpen    = ref(false);
const modalMode    = ref('add');        // 'add' | 'edit'
const modalTarget  = ref(null);

const EMPTY_FORM = () => ({
  name: '', il: '', ilce: '', adres: '', owner: '',
  telefon: '', eczaneKodu: '', isActive: true,
});
const form      = ref(EMPTY_FORM());
const formError = ref('');
const saving    = ref(false);

// İl değişince ilçeleri yeniden yükle
watch(() => form.value.il, (ilId) => {
  form.value.ilce = '';
  loadIlceler(ilId);
});

// ─── Kiosk Ekleme Modal ───────────────────────────────────────────────────────
const kioskModalOpen   = ref(false);
const kioskModalPharm  = ref(null);     // hangi eczaneye kiosk ekleniyor
const kioskForm        = ref({ mac: '' });
const kioskFormError   = ref('');
const kioskSaving      = ref(false);

// ─── Kiosk Düzenleme ──────────────────────────────────────────────────────────
const kioskEditModalOpen = ref(false);
const kioskEditTarget    = ref(null);
const kioskEditForm      = ref({
  ad: '', mac: '', isActive: true,
  interactionTimeoutSeconds: 20,
  idleContentMinSeconds: 10,
  idleContentMaxSeconds: 12,
  idleContentRefreshSeconds: 300,
  idleAudioDelayMinutes: 20,
  idleAudioRepeatMinutes: 5,
  interactionTimeoutUnit: 'seconds',
  idleContentMinUnit: 'seconds',
  idleContentMaxUnit: 'seconds',
  idleContentRefreshUnit: 'seconds',
  idleAudioDelayUnit: 'minutes',
  idleAudioRepeatUnit: 'minutes',
  idleAudioScheduleMode: 'ALL_DAY',
  idleAudioPlayOnDuty: false,
  idleAudioEnabled: false,
});
const kioskAudioFiles      = ref([]);
const audioUploading = ref(false);
const audioDeleteTarget = ref(null);
const audioDeleting = ref(false);
async function deleteLibraryAudio() {
  if (!audioDeleteTarget.value || audioDeleting.value) return;
  audioDeleting.value = true;
  const id = audioDeleteTarget.value.id;
  try {
    await deleteKioskLibraryAudio(id);
    stopAudioPreview();
    kioskAudioLibrary.value = kioskAudioLibrary.value.filter(asset => asset.id !== id);
    selectedKioskAudioIds.value = selectedKioskAudioIds.value.filter(assetId => assetId !== id);
    if (!selectedKioskAudioIds.value.length) kioskEditForm.value.idleAudioEnabled = false;
    audioDeleteTarget.value = null;
    toast.success('Ses kütüphaneden ve bağlı kiosklardan kaldırıldı.');
    await loadKiosks();
  } catch { toast.error('Ses silinemedi. Tekrar deneyin.'); }
  finally { audioDeleting.value = false; }
}
const audioPreviewUrl = ref('');
const audioPreviewName = ref('');
const audioPreviewLoading = ref(false);
let audioPreviewRequest = 0;
function stopAudioPreview() {
  audioPreviewRequest += 1;
  if (audioPreviewUrl.value) URL.revokeObjectURL(audioPreviewUrl.value);
  audioPreviewUrl.value = '';
  audioPreviewLoading.value = false;
}
onBeforeUnmount(stopAudioPreview);
async function listenToAudio(asset) {
  stopAudioPreview();
  const request = audioPreviewRequest;
  audioPreviewLoading.value = true;
  try {
    const url = await previewKioskAudio(asset.id);
    if (request !== audioPreviewRequest) { URL.revokeObjectURL(url); return; }
    audioPreviewName.value = asset.originalName;
    audioPreviewUrl.value = url;
  } catch {
    if (request === audioPreviewRequest) toast.error('Ses önizlemesi yüklenemedi.');
  } finally {
    if (request === audioPreviewRequest) audioPreviewLoading.value = false;
  }
}
async function uploadAudioToLibrary() {
  if (!kioskAudioFiles.value.length || audioUploading.value) return;
  audioUploading.value = true;
  try {
    const added = await uploadKioskAudioLibrary(kioskAudioFiles.value);
    kioskAudioLibrary.value.push(...added);
    kioskAudioFiles.value = [];
    kioskAudioInputKey.value += 1;
    toast.success('Sesler kütüphaneye eklendi. Kioska atamak için listeden seçin.');
  } catch {
    toast.error('Sesler yüklenemedi. Tekrar deneyin.');
  } finally {
    audioUploading.value = false;
  }
}
const kioskAudioInputKey   = ref(0);
const kioskAudioLibrary    = ref([]);
const kioskAudioLibraryLoading = ref(false);
const selectedKioskAudioIds = ref([]);
const kioskEditLoading = ref(false);
const kioskEditLoaded = ref(false);
let kioskEditRequest = 0;
const allAudioSelected = computed(() => kioskAudioLibrary.value.length > 0 && kioskAudioLibrary.value.every(asset => selectedKioskAudioIds.value.includes(asset.id)));
function toggleAllAudio() {
  selectedKioskAudioIds.value = allAudioSelected.value ? [] : [...new Set([...selectedKioskAudioIds.value, ...kioskAudioLibrary.value.map(asset => asset.id)])];
}
const kioskEditSaving    = ref(false);
const kioskEditError     = ref('');

const kioskDetailOpen   = ref(false);
const kioskDetailTarget = ref(null);
const transferOpen = ref(false);
const transferTarget = ref(null);
const transferForm = ref({ pharmacyId: '', reason: '' });
const transferError = ref('');
const transferSaving = ref(false);

const pendingDetailOpen   = ref(false);
const pendingDetailTarget = ref(null);

// ─── Kiosk Tab Filtering ──────────────────────────────────────────────────────
const activeKioskTab = ref('all'); // 'all' | 'online' | 'offline' | 'pending'

// ─── Pending Device Approval ──────────────────────────────────────────────────
const approveModalOpen  = ref(false);
const approveTarget     = ref(null);
const approveForm       = ref({ eczane_id: '', ad: '' });
const approveError      = ref('');
const approveSaving     = ref(false);

const rejectModalOpen  = ref(false);
const rejectTarget     = ref(null);
const rejectReason     = ref('');
const rejectError      = ref('');
const rejectSaving     = ref(false);

// ─── Toast Notification ───────────────────────────────────────────────────────
const toastVisible = ref(false);
const toastMessage = ref('');
let toastTimeout = null;

function showToast(message) { toast.success(message); }

// ─── Kiosk Silme ──────────────────────────────────────────────────────────────
const kioskDeleteTarget = ref(null);
const kioskDeleteOpen   = ref(false);
const kioskDeleting     = ref(false);

// ─── Eczane Silme Modal ───────────────────────────────────────────────────────
const deleteModalOpen   = ref(false);
const deleteTarget      = ref(null);
const deleting          = ref(false);

// ─── Computed ─────────────────────────────────────────────────────────────────
const filteredPharmacies = computed(() => {
  const q = pharmacySearch.value.trim().toLowerCase();
  if (!q) return pharmacies.value;
  return pharmacies.value.filter((p) =>
    p.name.toLowerCase().includes(q)      ||
    p.ilAdi.toLowerCase().includes(q)     ||
    p.ilceAdi.toLowerCase().includes(q)   ||
    p.owner.toLowerCase().includes(q)
  );
});

const onlineKiosks  = computed(() => kiosks.value.filter(isOnline));
const offlineKiosks = computed(() => kiosks.value.filter((k) => !isOnline(k)));
const pendingProvisioningRequests = computed(() =>
  provisioningRequests.value.filter((request) => request.status === 'PENDING')
);

const filteredKiosksForTab = computed(() => {
  if (activeKioskTab.value === 'online') return onlineKiosks.value;
  if (activeKioskTab.value === 'offline') return offlineKiosks.value;
  if (activeKioskTab.value === 'pending') return [];
  return kiosks.value;
});

const pharmacyOptions = computed(() =>
  pharmacies.value.map((p) => ({
    id: p.id,
    label: p.name,
    sub: `${p.ilAdi || ''}${p.ilceAdi ? ' / ' + p.ilceAdi : ''}`,
  }))
);
const selectedTransferPharmacy = computed(() =>
  pharmacyOptions.value.find((pharmacy) => String(pharmacy.id) === String(transferForm.value.pharmacyId)) || null
);

function provisioningHistoryForKiosk(kioskId) {
  return provisioningRequests.value
    .filter((request) => request.kioskId === kioskId)
    .slice()
    .sort((a, b) => new Date(b.firstSeenAt || b.approvedAt || b.rejectedAt || 0) - new Date(a.firstSeenAt || a.approvedAt || a.rejectedAt || 0));
}

function getKioskHostname(kiosk) {
  const history = provisioningHistoryForKiosk(kiosk.id);
  if (history.length > 0 && history[0].hostname) {
    return history[0].hostname;
  }
  return '—';
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function isOnline(kiosk) {
  if (!kiosk.lastPing) return false;
  const diffMin = (Date.now() - new Date(kiosk.lastPing).getTime()) / 60000;
  return diffMin <= 10;
}

function formatPing(iso) {
  if (!iso) return 'Hiç bağlanmadı';
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (diffMin < 1)  return 'Az önce';
  if (diffMin < 60) return `${diffMin} dk önce`;
  const h = Math.floor(diffMin / 60);
  if (h < 24) return `${h} sa önce`;
  return `${Math.floor(h / 24)} gün önce`;
}

// ─── Veri Yükleme ─────────────────────────────────────────────────────────────
async function loadPharmacies() {
  loadingPharm.value = true;
  try   { pharmacies.value = await getPharmacies(); }
  finally { loadingPharm.value = false; }
}

async function loadKiosks() {
  loadingKiosk.value = true;
  try   { kiosks.value = await getKioskStatus(); }
  finally { loadingKiosk.value = false; }
}

async function loadProvisioning() {
  loadingProvisioning.value = true;
  try   { provisioningRequests.value = await listProvisioningRequests(); }
  finally { loadingProvisioning.value = false; }
}

async function refreshDeviceData() {
  await Promise.all([loadKiosks(), loadProvisioning()]);
}

function handleProvisioningRefresh() {
  refreshDeviceData();
}

onMounted(async () => {
  const [ils] = await Promise.all([getIller(), loadPharmacies(), loadKiosks(), loadProvisioning()]);
  iller.value = ils;
  window.addEventListener('eisa-provisioning-refresh', handleProvisioningRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener('eisa-provisioning-refresh', handleProvisioningRefresh);
});

// ─── Eczane CRUD Modal ────────────────────────────────────────────────────────
function openAdd() {
  form.value      = EMPTY_FORM();
  formError.value = '';
  modalMode.value   = 'add';
  modalTarget.value = null;
  ilceler.value     = [];
  modalOpen.value   = true;
}

async function openEdit(pharmacy) {
  form.value = {
    name:       pharmacy.name,
    il:         pharmacy.il,
    ilce:       pharmacy.ilce,
    adres:      pharmacy.adres,
    owner:      pharmacy.owner,
    telefon:    pharmacy.telefon,
    eczaneKodu: pharmacy.eczaneKodu,
    isActive:   pharmacy.isActive,
  };
  formError.value   = '';
  modalMode.value   = 'edit';
  modalTarget.value = pharmacy;
  loadIlceler(pharmacy.il);
  modalOpen.value   = true;
  // watch fires on il change and resets ilce; restore it on next tick
  await nextTick();
  form.value.ilce = pharmacy.ilce;
}

function closeModal() { modalOpen.value = false; }

async function saveForm() {
  const { name, il, ilce, owner } = form.value;
  if (!name.trim() || !il || !ilce || !owner.trim()) {
    formError.value = 'Eczane adı, il, ilçe ve eczacı zorunludur.';
    return;
  }
  saving.value    = true;
  formError.value = '';
  try {
    if (modalMode.value === 'add') {
      await createPharmacy({ ...form.value });
    } else {
      await updatePharmacy(modalTarget.value.id, { ...form.value });
    }
    await loadPharmacies();
    closeModal();
  } catch {
    formError.value = 'İşlem sırasında hata oluştu.';
  } finally {
    saving.value = false;
  }
}

// ─── Eczane Silme Modal ───────────────────────────────────────────────────────
function openDelete(pharmacy) {
  deleteTarget.value     = pharmacy;
  deleteModalOpen.value  = true;
}

function closeDelete() {
  deleteModalOpen.value = false;
  deleteTarget.value    = null;
}

async function confirmDelete() {
  deleting.value = true;
  try {
    await deletePharmacy(deleteTarget.value.id);
    await loadPharmacies();
    closeDelete();
  } finally {
    deleting.value = false;
  }
}

function openAddKiosk(pharmacy) {
  kioskModalPharm.value = pharmacy;
  kioskForm.value       = { mac: '' };
  kioskFormError.value  = '';
  kioskModalOpen.value  = true;
}

function closeKioskModal() { kioskModalOpen.value = false; }

async function saveKiosk() {
  const mac = kioskForm.value.mac.trim();
  const ad = kioskForm.value.ad.trim();
  if (!mac) { kioskFormError.value = 'MAC adresi zorunludur.'; return; }
  // Basic MAC validation
  if (!/^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/.test(mac)) {
    kioskFormError.value = 'Geçerli bir MAC adresi girin (örn: AA:BB:CC:DD:EE:FF).';
    return;
  }
  if (!ad) { kioskFormError.value = 'Kiosk adı zorunludur.'; return; }
  kioskSaving.value    = true;
  kioskFormError.value = '';
  try {
    await createKiosk({ pharmacyId: kioskModalPharm.value.id, mac,ad });
    await Promise.all([loadKiosks(), loadPharmacies()]);
    closeKioskModal();
  } catch {
    kioskFormError.value = 'Kiosk eklenemedi. MAC adresi zaten kayıtlı olabilir.';
  } finally {
    kioskSaving.value = false;
  }
}

function openDeleteKiosk(kiosk) {
  kioskDeleteTarget.value = kiosk;
  kioskDeleteOpen.value   = true;
}

async function resetDeviceId(kiosk) {
  if (!confirm(`"${kiosk.ad}" kiosk'unun Device ID'si sıfırlanacak. Kiosk bir sonraki bağlantıda yeniden bağlanır. Devam?`)) return;
  try {
    await resetKioskDeviceId(kiosk.id);
    showToast('Device ID sıfırlandı. Kiosk kendi kendine yeniden bağlanacak.');
    await loadKiosks();
  } catch {
    showToast('Device ID sıfırlanamadı.');
  }
}

function closeDeleteKiosk() {
  kioskDeleteOpen.value   = false;
  kioskDeleteTarget.value = null;
}

async function confirmDeleteKiosk() {
  kioskDeleting.value = true;
  try {
    await deleteKiosk(kioskDeleteTarget.value.id);
    await Promise.all([loadKiosks(), loadPharmacies()]);
    closeDeleteKiosk();
  } finally {
    kioskDeleting.value = false;
  }
}

function openKioskDetail(kiosk) {
  kioskDetailTarget.value = kiosk;
  kioskDetailOpen.value = true;
}

function openTransfer(kiosk = kioskDetailTarget.value) {
  if (!kiosk) return;
  transferTarget.value = kiosk;
  transferForm.value = { pharmacyId: '', reason: '' };
  transferError.value = '';
  transferOpen.value = true;
}

function closeTransfer() {
  transferOpen.value = false;
  transferTarget.value = null;
  transferForm.value = { pharmacyId: '', reason: '' };
  transferError.value = '';
}

async function confirmTransfer() {
  if (!transferForm.value.pharmacyId) { transferError.value = 'Yeni eczane seçimi zorunludur.'; return; }
  if (String(transferForm.value.pharmacyId) === String(transferTarget.value?.pharmacyId)) {
    transferError.value = 'Cihaz zaten seçilen eczaneye bağlı.';
    return;
  }
  transferSaving.value = true;
  transferError.value = '';
  try {
    const updated = await transferKiosk(transferTarget.value.id, transferForm.value.pharmacyId, transferForm.value.reason);
    if (kioskDetailTarget.value?.id === updated.id) kioskDetailTarget.value = updated;
    closeTransfer();
    await Promise.all([loadKiosks(), loadPharmacies()]);
    toast.success('Cihaz yeni eczaneye taşındı.');
  } catch (error) {
    const response = error?.response?.data;
    transferError.value = response?.detail || response?.target_pharmacy?.[0] || 'Cihaz taşınamadı.';
  } finally { transferSaving.value = false; }
}

function closeKioskDetail() {
  kioskDetailOpen.value = false;
  kioskDetailTarget.value = null;
}

function openPendingDetail(req) {
  pendingDetailTarget.value = req;
  pendingDetailOpen.value = true;
}

function closePendingDetail() {
  pendingDetailOpen.value = false;
  pendingDetailTarget.value = null;
}

function statusLabelForProvisioning(status) {
  if (status === 'PENDING') return 'Onay Bekliyor';
  if (status === 'APPROVED') return 'Onaylandı';
  if (status === 'REJECTED') return 'Reddedildi';
  return status;
}

function statusClassForProvisioning(status) {
  if (status === 'PENDING') return 'badge-pending';
  if (status === 'APPROVED') return 'badge-approved';
  if (status === 'REJECTED') return 'badge-rejected';
  return '';
}

function applyKioskEdit(kiosk) {
  kioskEditTarget.value = kiosk;
  kioskEditForm.value = {
    ad: kiosk.ad || '',
    mac: kiosk.mac || '',
    isActive: kiosk.isActive !== false,
    interactionTimeoutSeconds: kiosk.interactionTimeoutSeconds ?? 20,
    idleContentMinSeconds: kiosk.idleContentMinSeconds ?? 10,
    idleContentMaxSeconds: kiosk.idleContentMaxSeconds ?? 12,
    idleContentRefreshSeconds: kiosk.idleContentRefreshSeconds ?? 300,
    idleAudioDelayMinutes: (kiosk.idleAudioDelaySeconds ?? 1200) / 60,
    idleAudioRepeatMinutes: (kiosk.idleAudioRepeatSeconds ?? 300) / 60,
    interactionTimeoutUnit: 'seconds', idleContentMinUnit: 'seconds',
    idleContentMaxUnit: 'seconds', idleContentRefreshUnit: 'seconds',
    idleAudioDelayUnit: 'minutes', idleAudioRepeatUnit: 'minutes',
    idleAudioScheduleMode: kiosk.idleAudioScheduleMode ?? 'ALL_DAY',
    idleAudioPlayOnDuty: kiosk.idleAudioPlayOnDuty === true,
    idleAudioEnabled: kiosk.idleAudioEnabled === true,
  };
  selectedKioskAudioIds.value = (kiosk.idleAudioFiles || []).map(file => file.assetId || file.id).filter(Boolean);
  for (const [secondsKey, valueKey, unitKey] of [['idleAudioDelaySeconds', 'idleAudioDelayMinutes', 'idleAudioDelayUnit'], ['idleAudioRepeatSeconds', 'idleAudioRepeatMinutes', 'idleAudioRepeatUnit']]) {
    if (kiosk[secondsKey] % 60) {
      kioskEditForm.value[valueKey] = kiosk[secondsKey];
      kioskEditForm.value[unitKey] = 'seconds';
    }
  }
}
async function openEditKiosk(kiosk) {
  const request = ++kioskEditRequest;
  applyKioskEdit(kiosk);
  kioskEditLoading.value = true;
  kioskEditLoaded.value = false;
  kioskAudioFiles.value = [];
  kioskAudioInputKey.value += 1;
  kioskEditError.value = '';
  kioskEditModalOpen.value = true;
  loadKioskAudioLibrary();
  try {
    const latest = await getKiosk(kiosk.id);
    if (request !== kioskEditRequest) return;
    applyKioskEdit(latest);
    kioskEditLoaded.value = true;
  } catch {
    if (request === kioskEditRequest) kioskEditError.value = 'Kayıtlı cihaz ayarları alınamadı. Ekranı yeniden açın.';
  } finally {
    if (request === kioskEditRequest) kioskEditLoading.value = false;
  }
}

function closeEditKiosk() {
  if (audioUploading.value || kioskEditSaving.value || audioDeleting.value) return;
  audioDeleteTarget.value = null;
  stopAudioPreview();
  kioskEditRequest += 1;
  kioskEditModalOpen.value = false;
  kioskEditTarget.value = null;
  kioskAudioFiles.value = [];
  selectedKioskAudioIds.value = [];
  kioskEditError.value = '';
}

function durationToSeconds(value, unit) {
  return Number(value) * (unit === 'minutes' ? 60 : 1);
}

async function loadKioskAudioLibrary() {
  kioskAudioLibraryLoading.value = true;
  try {
    kioskAudioLibrary.value = await listKioskAudioLibrary();
  } catch (error) {
    kioskEditError.value = error?.response?.data?.detail || 'Ses kütüphanesi yüklenemedi.';
  } finally {
    kioskAudioLibraryLoading.value = false;
  }
}

function toggleKioskAudio(assetId) {
  const index = selectedKioskAudioIds.value.indexOf(assetId);
  if (index >= 0) selectedKioskAudioIds.value.splice(index, 1);
  else selectedKioskAudioIds.value.push(assetId);
}

async function saveEditKiosk() {
  if (kioskEditSaving.value || !kioskEditLoaded.value) return;
  const ad = kioskEditForm.value.ad.trim();
  const mac = kioskEditForm.value.mac.trim();
  if (!ad.trim()) {
    kioskEditError.value = 'Kiosk adı zorunludur.';
    return;
  }
  if (!mac.trim()) {
    kioskEditError.value = 'MAC adresi zorunludur.';
    return;
  }
  if (!/^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/.test(mac)) {
    kioskEditError.value = 'Geçerli bir MAC adresi girin (örn: AA:BB:CC:DD:EE:FF).';
    return;
  }
  const seconds = {
    interactionTimeoutSeconds: durationToSeconds(kioskEditForm.value.interactionTimeoutSeconds, kioskEditForm.value.interactionTimeoutUnit),
    idleContentMinSeconds: durationToSeconds(kioskEditForm.value.idleContentMinSeconds, kioskEditForm.value.idleContentMinUnit),
    idleContentMaxSeconds: durationToSeconds(kioskEditForm.value.idleContentMaxSeconds, kioskEditForm.value.idleContentMaxUnit),
    idleContentRefreshSeconds: durationToSeconds(kioskEditForm.value.idleContentRefreshSeconds, kioskEditForm.value.idleContentRefreshUnit),
    idleAudioDelaySeconds: durationToSeconds(kioskEditForm.value.idleAudioDelayMinutes, kioskEditForm.value.idleAudioDelayUnit),
    idleAudioRepeatSeconds: durationToSeconds(kioskEditForm.value.idleAudioRepeatMinutes, kioskEditForm.value.idleAudioRepeatUnit),
  };
  const numericFields = [
    ['İşlemsizlik süresi', seconds.interactionTimeoutSeconds, 5, 3600],
    ['Idle içerik minimum süresi', seconds.idleContentMinSeconds, 5, 300],
    ['Idle içerik maksimum süresi', seconds.idleContentMaxSeconds, 5, 300],
    ['Idle içerik yenileme süresi', seconds.idleContentRefreshSeconds, 30, 3600],
    ['İlk ses bekleme süresi', seconds.idleAudioDelaySeconds, 60, 86400],
    ['Ses tekrar aralığı', seconds.idleAudioRepeatSeconds, 60, 86400],
  ];
  for (const [label, value, min, max] of numericFields) {
    if (!Number.isInteger(Number(value)) || Number(value) < min || Number(value) > max) {
      kioskEditError.value = `${label} ${min}–${max} saniye arasında olmalıdır. Dk/Sn birimini kontrol edin.`;
      return;
    }
  }
  if (seconds.idleContentMinSeconds > seconds.idleContentMaxSeconds) {
    kioskEditError.value = 'Idle içerik maksimum süresi minimum süreden küçük olamaz.';
    return;
  }
  kioskEditSaving.value = true;
  kioskEditError.value = '';
  try {
    const desiredAudioEnabled = kioskEditForm.value.idleAudioEnabled;
    await updateKiosk(kioskEditTarget.value.id, {
      ad, mac, isActive: kioskEditForm.value.isActive, ...seconds,
      idleAudioScheduleMode: kioskEditForm.value.idleAudioScheduleMode,
      idleAudioPlayOnDuty: kioskEditForm.value.idleAudioPlayOnDuty,
      idleAudioEnabled: undefined,
    });
    await setKioskIdleAudios(kioskEditTarget.value.id, selectedKioskAudioIds.value);
    if (selectedKioskAudioIds.value.length && !desiredAudioEnabled) {
      await updateKiosk(kioskEditTarget.value.id, { idleAudioEnabled: false });
    }
    await Promise.all([loadKiosks(), loadPharmacies()]);
    kioskEditSaving.value = false;
    closeEditKiosk();
  } catch (error) {
    kioskEditError.value = error?.response?.data?.detail || 'Kiosk güncellenemedi. Bilgileri ve ses dosyasını kontrol edin.';
  } finally {
    kioskEditSaving.value = false;
  }
}

function onKioskAudioSelected(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) { kioskAudioFiles.value = []; return; }
  const allowed = new Set(['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/wave', 'audio/vnd.wave', 'audio/ogg', 'application/ogg']);
  for (const file of files) {
    if (!allowed.has(file.type)) {
      kioskEditError.value = `${file.name}: yalnızca MP3, WAV veya OGG ses dosyası seçebilirsiniz.`;
      event.target.value = '';
      kioskAudioFiles.value = [];
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      kioskEditError.value = `${file.name}: ses dosyası 20 MB'dan büyük olamaz.`;
      event.target.value = '';
      kioskAudioFiles.value = [];
      return;
    }
  }
  kioskEditError.value = '';
  kioskAudioFiles.value = files;
}


function formatProvisioningDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function refreshAllDeviceViews() {
  refreshDeviceData();
}

function formatProvisioningMetadata(metadata) {
  if (!metadata || typeof metadata !== 'object') return [];
  const BLOCKED = new Set(['token', 'secret', 'hmac', 'authorization', 'app_key', 'iot_token']);
  const LABELS = {
    hostname: 'Makine Adı',
    os_type: 'İşletim Sistemi',
    os_platform: 'Platform',
    os_release: 'OS Sürümü',
    arch: 'Mimari',
    cpu_model: 'İşlemci',
    cpu_cores: 'Çekirdek Sayısı',
    total_memory_mb: 'Toplam RAM (MB)',
    node_version: 'Node.js Sürümü',
    uptime_seconds: 'Çalışma Süresi',
  };
  return Object.entries(metadata)
    .filter(([k]) => !BLOCKED.has(k.toLowerCase()) && k !== 'ip_addresses')
    .map(([k, v]) => ({
      key: k,
      label: LABELS[k] || k,
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

function openApprove(req) {
  approveTarget.value = req;
  approveForm.value = { eczane_id: '', ad: '' };
  approveError.value = '';
  approveModalOpen.value = true;
}

function closeApprove() {
  approveModalOpen.value = false;
  approveTarget.value = null;
}

async function confirmApprove() {
  const { eczane_id, ad } = approveForm.value;
  if (!eczane_id) { approveError.value = 'Eczane seçimi zorunludur.'; return; }
  if (!ad.trim()) { approveError.value = 'Kiosk adı zorunludur.'; return; }

  approveSaving.value = true;
  approveError.value = '';
  try {
    const { approveProvisioningRequest } = await import('../../services/devices');
    await approveProvisioningRequest(approveTarget.value.id, {
      eczane_id: Number(eczane_id),
      ad: ad.trim(),
    });
    await refreshDeviceData();
    window.dispatchEvent(new Event('eisa-nav-badges-refresh'));
    closeApprove();
    showToast('Cihaz başarıyla onaylandı ve kiosk kaydı oluşturuldu.');
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Onaylama sırasında hata oluştu.';
    approveError.value = detail;
  } finally {
    approveSaving.value = false;
  }
}

function openReject(req) {
  rejectTarget.value = req;
  rejectReason.value = '';
  rejectError.value = '';
  rejectModalOpen.value = true;
}

function closeReject() {
  rejectModalOpen.value = false;
  rejectTarget.value = null;
}

async function confirmReject() {
  rejectSaving.value = true;
  rejectError.value = '';
  try {
    const { rejectProvisioningRequest } = await import('../../services/devices');
    await rejectProvisioningRequest(rejectTarget.value.id, {
      rejection_reason: rejectReason.value.trim(),
    });
    await refreshDeviceData();
    window.dispatchEvent(new Event('eisa-nav-badges-refresh'));
    closeReject();
    showToast('Cihaz reddedildi.');
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Red işlemi sırasında hata oluştu.';
    rejectError.value = detail;
  } finally {
    rejectSaving.value = false;
  }
}

async function copyAppKey() {
  const appKey = kioskEditTarget.value?.appKey;
  if (!appKey || appKey === '—') return;
  try {
    await navigator.clipboard.writeText(appKey);
    showToast('Kopyalandı!');
  } catch {
    showToast('Kopyalanamadı');
  }
}
</script>

<template>
  <div class="eisa-page">

    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Süper Admin / Cihaz Yönetimi</p>
        <h1 class="eisa-page-title">Eczane &amp; Kiosk Yönetimi</h1>
        <p class="eisa-page-subtitle">Eczaneleri yönetin ve kioskların anlık durumunu izleyin.</p>
      </div>
      <div class="eisa-header-actions">
        <button
          class="eisa-btn eisa-btn-ghost"
          @click="refreshAllDeviceViews"
        >
          <i class="fa-solid fa-rotate-right"></i>
          Yenile
        </button>
      </div>
    </div>

   <div class="eisa-panel">
      <div class="eisa-panel-header">
        <div>
          <h2 class="eisa-panel-title">
            <i class="fa-solid fa-hospital" style="color:#B1121B;margin-right:0.4rem;"></i>
            Eczane Listesi
          </h2>
          <p class="eisa-stat-sub" style="margin-top:0.15rem;">
            {{ loadingPharm ? '…' : `${pharmacies.length} eczane kayıtlı` }}
          </p>
        </div>
        <div class="eisa-header-actions">
          <div class="eisa-search-wrap" style="min-width:200px;">
            <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
            <input
              id="pharmacy-search"
              name="pharmacySearch"
              v-model="pharmacySearch"
              type="search"
              placeholder="Eczane ara…"
              class="eisa-field eisa-search-field"
            />
          </div>
          <button class="eisa-btn eisa-btn-cta" @click="openAdd">
            <i class="fa-solid fa-plus"></i>
            Yeni Eczane
          </button>
        </div>
      </div>

      <div class="eisa-panel-body" style="padding:0;">
        <div style="overflow-x:auto;">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>Eczane Adı</th>
                <th>İl</th>
                <th>İlçe</th>
                <th>Eczacı</th>
                <th>Telefon</th>
                <th style="text-align:center;">Kiosk</th>
                <th class="actions-col">İşlemler</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loadingPharm">
                <td colspan="7" class="empty-row">
                  <i class="fa-solid fa-circle-notch fa-spin" style="margin-right:0.5rem;color:#B1121B;"></i>
                  Yükleniyor…
                </td>
              </tr>
              <tr v-else-if="filteredPharmacies.length === 0">
                <td colspan="7" class="empty-row">
                  <i class="fa-regular fa-face-frown" style="display:block;font-size:1.75rem;margin-bottom:0.4rem;color:#D1D5DB;"></i>
                  Sonuç bulunamadı.
                </td>
              </tr>
              <tr v-else v-for="ph in filteredPharmacies" :key="ph.id">
                <td style="font-weight:600;">{{ ph.name }}</td>
                <td class="cell-muted">{{ ph.ilAdi }}</td>
                <td class="cell-muted">{{ ph.ilceAdi }}</td>
                <td class="cell-muted">{{ ph.owner }}</td>
                <td class="cell-muted">{{ ph.telefon || '—' }}</td>
                <td style="text-align:center;">
                  <span class="eisa-pill eisa-pill-info">{{ ph.kioskCount }}</span>
                </td>
                <td>
                  <div class="cell-actions">
                    <button
                      class="eisa-icon-btn"
                      title="Kiosk Ekle"
                      @click="openAddKiosk(ph)"
                    >
                      <i class="fa-solid fa-display"></i>
                    </button>
                    <button
                      class="eisa-icon-btn"
                      title="Düzenle"
                      @click="openEdit(ph)"
                    >
                      <i class="fa-solid fa-pen"></i>
                    </button>
                    <button
                      class="eisa-icon-btn"
                      title="Sil"
                      @click="openDelete(ph)"
                    >
                      <i class="fa-solid fa-trash" style="color:#EF4444;"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="!loadingPharm && filteredPharmacies.length > 0" class="eisa-panel-footer">
        <span>{{ filteredPharmacies.length }} / {{ pharmacies.length }} eczane gösteriliyor</span>
        <span v-if="pharmacySearch">· Filtre: "{{ pharmacySearch }}"</span>
      </div>
    </div>

  <div class="eisa-panel">
      <div class="eisa-panel-header">
        <div>
          <h2 class="eisa-panel-title">
            <i class="fa-solid fa-tv" style="color:#059669;margin-right:0.4rem;"></i>
            Kiosk İzleme
          </h2>
          <p class="eisa-stat-sub" style="margin-top:0.15rem;">
            {{ loadingKiosk ? '…' : `${kiosks.length} cihaz` }}
          </p>
        </div>
        <div v-if="!loadingKiosk" class="kiosk-tabs">
          <button
            class="kiosk-tab"
            :class="{ 'kiosk-tab--active': activeKioskTab === 'all' }"
            @click="activeKioskTab = 'all'"
          >
            <i class="fa-solid fa-display"></i>
            Tümü ({{ kiosks.length }})
          </button>
          <button
            class="kiosk-tab"
            :class="{ 'kiosk-tab--active': activeKioskTab === 'online' }"
            @click="activeKioskTab = 'online'"
          >
            <span class="eisa-kiosk-dot eisa-kiosk-dot--online" style="width:8px;height:8px;"></span>
            Online ({{ onlineKiosks.length }})
          </button>
          <button
            class="kiosk-tab"
            :class="{ 'kiosk-tab--active': activeKioskTab === 'offline' }"
            @click="activeKioskTab = 'offline'"
          >
            <span class="eisa-kiosk-dot eisa-kiosk-dot--offline" style="width:8px;height:8px;"></span>
            Offline ({{ offlineKiosks.length }})
          </button>
          <button
            class="kiosk-tab"
            :class="{ 'kiosk-tab--active': activeKioskTab === 'pending' }"
            @click="activeKioskTab = 'pending'"
          >
            <span class="eisa-kiosk-dot eisa-kiosk-dot--pending" style="width:8px;height:8px;"></span>
            Onay Bekleyen ({{ pendingProvisioningRequests.length }})
          </button>
        </div>
      </div>

      <div class="eisa-panel-body">
        <div v-if="loadingKiosk || loadingProvisioning" style="display:flex;align-items:center;gap:0.5rem;padding:3rem 0;justify-content:center;color:#6B7280;">
          <i class="fa-solid fa-circle-notch fa-spin" style="color:#059669;"></i>
          {{ loadingKiosk ? 'Kiosk durumları alınıyor…' : 'Provisioning verileri yükleniyor…' }}
        </div>

        <!-- All Device Cards (Approved Kiosks + Pending Requests) -->
        <div v-else class="dm-kiosk-grid" style="padding:0;">
          <!-- Approved Kiosk Cards -->
          <template v-if="activeKioskTab !== 'pending'">
            <div
              v-for="kiosk in filteredKiosksForTab"
              :key="kiosk.id"
              class="eisa-kiosk-card"
              :class="isOnline(kiosk) ? 'eisa-kiosk-card--online' : 'eisa-kiosk-card--offline'"
            >
              <div
                class="eisa-kiosk-card-stripe"
                :class="isOnline(kiosk) ? 'eisa-kiosk-card-stripe--online' : 'eisa-kiosk-card-stripe--offline'"
              ></div>
              <div class="eisa-kiosk-card-body">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:0.6rem;">
                  <span style="font-family:'DM Mono',monospace;font-size:0.8rem;font-weight:700;color:#111827;">{{ kiosk.ad }}</span>
                  <span
                    class="eisa-kiosk-status"
                    :class="isOnline(kiosk) ? 'eisa-kiosk-status--online' : 'eisa-kiosk-status--offline'"
                  >
                    <span
                      class="eisa-kiosk-dot"
                      :class="isOnline(kiosk) ? 'eisa-kiosk-dot--online' : 'eisa-kiosk-dot--offline'"
                    ></span>
                    {{ isOnline(kiosk) ? 'Online' : 'Offline' }}
                  </span>
                </div>
                <p style="font-size:0.78rem;color:#6B7280;min-height:2rem;line-height:1.4;">
                  <i class="fa-solid fa-hospital" style="margin-right:0.35rem;color:#9CA3AF;font-size:0.7rem;"></i>
                  {{ kiosk.pharmacyName }}
                </p>
                <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid #E5E7EB;display:flex;flex-direction:column;gap:0.5rem;">
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">Hostname</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;word-break:break-all;">{{ getKioskHostname(kiosk) }}</p>
                  </div>
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">MAC Adresi</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;word-break:break-all;">{{ kiosk.mac || '—' }}</p>
                  </div>
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">IP Adresi</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;word-break:break-all;">{{ kiosk.lastIp || '—' }}</p>
                  </div>
                </div>
              </div>
              <div class="eisa-kiosk-card-footer">
                <div>
                  <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.1rem;">Son Ping</p>
                  <p
                    style="font-size:0.78rem;font-weight:600;"
                    :style="{ color: isOnline(kiosk) ? '#059669' : '#EF4444' }"
                  >{{ formatPing(kiosk.lastPing) }}</p>
                </div>
                <div style="display:flex;gap:0.25rem;">
                   <button
                     class="eisa-icon-btn"
                     title="Detay"
                     @click="openKioskDetail(kiosk)"
                   >
                     <i class="fa-solid fa-circle-info" style="color:#059669;"></i>
                   </button>
                  <button
                    class="eisa-icon-btn"
                    title="Düzenle"
                    @click="openEditKiosk(kiosk)"
                  >
                    <i class="fa-solid fa-pen-to-square" style="color:#7C3AED;"></i>
                  </button>
                  <button
                    class="eisa-icon-btn"
                    title="Device ID Sıfırla (bağlantı sorunu için)"
                    @click="resetDeviceId(kiosk)"
                  >
                    <i class="fa-solid fa-fingerprint" style="color:#D97706;"></i>
                  </button>
                  <button
                    class="eisa-icon-btn"
                    title="Kiosk'u Kaldır"
                    @click="openDeleteKiosk(kiosk)"
                  >
                    <i class="fa-solid fa-trash" style="color:#EF4444;"></i>
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- Pending Provisioning Request Cards -->
          <template v-if="activeKioskTab === 'all' || activeKioskTab === 'pending'">
            <div v-if="activeKioskTab === 'pending' && pendingProvisioningRequests.length === 0" class="eisa-empty-inline" style="grid-column:1/-1;text-align:center;padding:2rem;">
              <i class="fa-regular fa-circle-check" style="font-size:2rem;display:block;margin-bottom:0.5rem;color:#10B981;"></i>
              Onay bekleyen cihaz bulunmuyor.
            </div>
            <div
              v-for="req in pendingProvisioningRequests"
              :key="'pending-' + req.id"
              class="eisa-kiosk-card eisa-kiosk-card--pending"
            >
              <div class="eisa-kiosk-card-stripe eisa-kiosk-card-stripe--pending"></div>
              <div class="eisa-kiosk-card-body">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:0.6rem;">
                  <span style="font-family:'DM Mono',monospace;font-size:0.8rem;font-weight:700;color:#111827;">{{ req.hostname || 'Bilinmeyen Cihaz' }}</span>
                  <span class="badge badge-pending">Onay Bekliyor</span>
                </div>
                <p style="font-size:0.78rem;color:#6B7280;min-height:2rem;line-height:1.4;">
                  <i class="fa-solid fa-clock" style="margin-right:0.35rem;color:#D97706;font-size:0.7rem;"></i>
                  İlk Görülme: {{ formatProvisioningDate(req.firstSeenAt) }}
                </p>
                <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid #F3F4F6;display:flex;flex-direction:column;gap:0.5rem;">
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">Hostname</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;word-break:break-all;">{{ req.hostname || '—' }}</p>
                  </div>
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">MAC Adresi</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;word-break:break-all;">{{ req.mac }}</p>
                  </div>
                  <div>
                    <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.15rem;">Başvuru Sayısı</p>
                     <p style="font-size:0.75rem;font-family:'DM Mono',monospace;color:#374151;font-weight:500;">{{ req.requestCount }}</p>
                  </div>
                </div>
              </div>
              <div class="eisa-kiosk-card-footer">
                <div>
                  <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.1rem;">Durum</p>
                  <p style="font-size:0.78rem;font-weight:600;color:#D97706;">Beklemede</p>
                </div>
                <div style="display:flex;gap:0.5rem;">
                  <button
                    class="eisa-icon-btn"
                    title="Detay"
                    @click="openPendingDetail(req)"
                  >
                    <i class="fa-solid fa-circle-info" style="color:#059669;"></i>
                  </button>
                  <button
                    class="eisa-icon-btn"
                    title="Onayla"
                    @click="openApprove(req)"
                  >
                    <i class="fa-solid fa-check" style="color:#10B981;"></i>
                  </button>
                  <button
                    class="eisa-icon-btn"
                    title="Reddet"
                    @click="openReject(req)"
                  >
                    <i class="fa-solid fa-times" style="color:#EF4444;"></i>
                  </button>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div v-if="!loadingKiosk && !loadingProvisioning" class="eisa-panel-footer">
        <span>Son güncelleme: az önce</span>
        <span>10 dakikadan eski ping → Offline</span>
      </div>
    </div>

  </div><!-- /eisa-page -->

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- CRUD Modal: Eczane Ekle / Düzenle                                      -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="modalOpen"
        id="pharmacy-modal-backdrop"
        class="eisa-modal-backdrop"
        @click.self="closeModal"
      >
        <Transition name="modal" appear>
          <div
            v-if="modalOpen"
            id="pharmacy-modal"
            class="eisa-modal"
            :class="{ 'eisa-modal--big': modalMode === 'add' }"
            :style="modalMode === 'edit' ? { maxWidth: '760px' } : {}"
          >
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">
                {{ modalMode === 'add' ? 'Yeni Eczane Ekle' : 'Eczane Düzenle' }}
              </h3>
              <button class="eisa-modal-close" @click="closeModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body">
              <div v-if="formError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ formError }}
              </div>

              <div class="eisa-form-grid">
                <!-- Eczane Adı -->
                <div class="eisa-form-row eisa-form-row-full">
                  <label for="ph-name" class="eisa-field-label">Eczane Adı <span style="color:#EF4444;">*</span></label>
                  <input
                    id="ph-name"
                    name="name"
                    v-model="form.name"
                    type="text"
                    placeholder="Örn: Merkez Eczanesi"
                    class="eisa-field"
                  />
                </div>

                <!-- İl -->
                <div class="eisa-form-row">
                  <label for="ph-il" class="eisa-field-label">İl <span style="color:#EF4444;">*</span></label>
                  <select id="ph-il" name="il" v-model="form.il" class="eisa-field">
                    <option value="">Seçiniz…</option>
                    <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad }}</option>
                  </select>
                </div>

                <!-- İlçe -->
                <div class="eisa-form-row">
                  <label for="ph-ilce" class="eisa-field-label">İlçe <span style="color:#EF4444;">*</span></label>
                  <select
                    id="ph-ilce"
                    name="ilce"
                    v-model="form.ilce"
                    :disabled="!form.il || ilcelerYukleniyor"
                    class="eisa-field"
                  >
                    <option value="">{{ ilcelerYukleniyor ? 'Yükleniyor…' : 'Seçiniz…' }}</option>
                    <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad }}</option>
                  </select>
                </div>

                <!-- Adres -->
                <div class="eisa-form-row eisa-form-row-full">
                  <label for="ph-adres" class="eisa-field-label">Adres</label>
                  <textarea
                    id="ph-adres"
                    name="adres"
                    v-model="form.adres"
                    rows="2"
                    placeholder="Sokak, mahalle, bina no…"
                    class="eisa-field"
                    style="resize:none;"
                  ></textarea>
                </div>

                <!-- Eczacı -->
                <div class="eisa-form-row">
                  <label for="ph-owner" class="eisa-field-label">Eczacı <span style="color:#EF4444;">*</span></label>
                  <input id="ph-owner" name="owner" v-model="form.owner" type="text" placeholder="Ad Soyad" class="eisa-field" />
                </div>

                <!-- Telefon -->
                <div class="eisa-form-row">
                  <label for="ph-telefon" class="eisa-field-label">Telefon</label>
                  <input id="ph-telefon" name="telefon" v-model="form.telefon" type="tel" placeholder="05xx xxx xx xx" class="eisa-field" />
                </div>

                <!-- Eczane Kodu -->
                <div class="eisa-form-row">
                  <label for="ph-kod" class="eisa-field-label">Eczane Kodu</label>
                  <input id="ph-kod" name="eczaneKodu" v-model="form.eczaneKodu" type="text" placeholder="ECZ-001" class="eisa-field" />
                </div>

                <!-- Aktif -->
                <div class="eisa-form-row eisa-toggle-row" style="justify-content:flex-end;padding-bottom:0.25rem;">
                  <label class="eisa-toggle">
                    <input id="ph-aktif" name="isActive" type="checkbox" v-model="form.isActive" />
                    Aktif
                  </label>
                </div>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="closeModal">İptal</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="saveForm">
                <i v-if="saving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-check"></i>
                {{ saving ? 'Kaydediliyor…' : (modalMode === 'add' ? 'Ekle' : 'Güncelle') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Kiosk Ekle Modal                                                        -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="kioskModalOpen"
        id="kiosk-modal-backdrop"
        class="eisa-modal-backdrop"
        @click.self="closeKioskModal"
      >
        <Transition name="modal" appear>
          <div v-if="kioskModalOpen" id="kiosk-modal" class="eisa-modal" style="max-width:420px;">
            <div class="eisa-modal-header">
              <div>
                <h3 class="eisa-modal-title">Kiosk Ekle</h3>
                <p class="eisa-stat-sub">{{ kioskModalPharm?.name }}</p>
              </div>
              <button class="eisa-modal-close" @click="closeKioskModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body">
              <div v-if="kioskFormError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ kioskFormError }}
              </div>
              <div class="eisa-form-row">
                <label for="kiosk-mac" class="eisa-field-label">
                  MAC Adresi <span style="color:#EF4444;">*</span>
                </label>
                <input
                  id="kiosk-mac"
                  name="mac"
                  v-model="kioskForm.mac"
                  type="text"
                  placeholder="AA:BB:CC:DD:EE:FF"
                  class="eisa-field"
                  style="font-family:'DM Mono',monospace;"
                />
                <p style="margin-top:0.35rem;font-size:0.75rem;color:#6B7280;">Kiosk cihazının fiziksel MAC adresi</p>
              </div>
                <div class="eisa-form-row">
                <label for="kiosk-ad" class="eisa-field-label">
                  Kiosk Adı <span style="color:#EF4444;">*</span>
                </label>
                <input
                  id="kiosk-ad"
                  name="ad"
                  v-model="kioskForm.ad"
                  type="text"
                  placeholder="Eczane Önü Kiosk"
                  class="eisa-field"
                  style="font-family:'DM Mono',monospace;"
                />
                <p style="margin-top:0.35rem;font-size:0.75rem;color:#6B7280;">Kiosk cihazının fiziksel MAC adresi</p>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" :disabled="kioskSaving" @click="closeKioskModal">İptal</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="kioskSaving" @click="saveKiosk">
                <i v-if="kioskSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-plus"></i>
                {{ kioskSaving ? 'Ekleniyor…' : 'Kiosk Ekle' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Kiosk Düzenle Modal                                                     -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="kioskEditModalOpen"
        id="kiosk-edit-modal-backdrop"
        class="eisa-modal-backdrop"
        @click.self="closeEditKiosk"
      >
        <Transition name="modal" appear>
          <div v-if="kioskEditModalOpen" id="kiosk-edit-modal" class="eisa-modal" style="max-width:680px;">
            <div class="eisa-modal-header">
              <div>
                <h3 class="eisa-modal-title">Kiosk Düzenle</h3>
                <p class="eisa-stat-sub">{{ kioskEditTarget?.pharmacyName }}</p>
              </div>
              <button class="eisa-modal-close" @click="closeEditKiosk">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body">
              <div v-if="kioskEditError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ kioskEditError }}
              </div>

              <div class="eisa-form-row">
                <label for="kiosk-edit-ad" class="eisa-field-label">
                  Kiosk Adı <span style="color:#EF4444;">*</span>
                </label>
                <input
                  id="kiosk-edit-ad"
                  v-model="kioskEditForm.ad"
                  type="text"
                  placeholder="Kiosk 1"
                  class="eisa-field"
                />
              </div>

              <div class="eisa-form-row">
                <label for="kiosk-edit-mac" class="eisa-field-label">
                  MAC Adresi <span style="color:#EF4444;">*</span>
                </label>
                <input
                  id="kiosk-edit-mac"
                  v-model="kioskEditForm.mac"
                  type="text"
                  placeholder="AA:BB:CC:DD:EE:FF"
                  class="eisa-field"
                  style="font-family:'DM Mono',monospace;"
                />
              </div>

              <div class="eisa-form-row">
                <label for="kiosk-edit-appkey" class="eisa-field-label">
                  Uygulama Anahtarı (Salt Okunur)
                </label>
                <div style="display:flex;gap:0.5rem;align-items:stretch;">
                  <input
                    id="kiosk-edit-appkey"
                    :value="kioskEditTarget?.appKey || '—'"
                    type="text"
                    readonly
                    class="eisa-field"
                    style="flex:1;font-family:'DM Mono',monospace;background:#F1F5F9;cursor:not-allowed;"
                    title="Uygulama anahtarı backend tarafından otomatik üretilir"
                  />
                  <button
                    type="button"
                    class="eisa-icon-btn"
                    style="padding:0.5rem 0.75rem;background:#7C3AED;color:white;border-radius:0.375rem;transition:all 0.15s;"
                    :disabled="!kioskEditTarget?.appKey || kioskEditTarget?.appKey === '—'"
                    @click="copyAppKey"
                    title="Kopyala"
                  >
                    <i class="fa-solid fa-copy"></i>
                  </button>
                </div>
                <p style="margin-top:0.35rem;font-size:0.75rem;color:#6B7280;">Backend tarafından otomatik üretilir, değiştirilemez</p>
              </div>

              <div class="eisa-form-row eisa-toggle-row">
                <label class="eisa-toggle">
                  <input type="checkbox" v-model="kioskEditForm.isActive" />
                  Aktif
                </label>
              </div>

              <div style="height:1px;background:#E5E7EB;margin:1.1rem 0;"></div>
              <div style="display:flex;align-items:center;gap:0.55rem;margin-bottom:0.9rem;">
                <i class="fa-solid fa-clock" style="color:#B1121B;"></i>
                <div>
                  <p class="eisa-field-label" style="margin:0;">Cihaz Zamanlamaları</p>
                  <p style="margin:0.15rem 0 0;font-size:0.75rem;color:#6B7280;">Ayarlar yalnızca bu kiosk için uygulanır.</p>
                </div>
              </div>

              <div class="dm-settings-grid">
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">İşlemden Ana Ekrana Dönüş</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.interactionTimeoutSeconds" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.interactionTimeoutUnit" class="eisa-field"><option value="seconds">Sn</option><option value="minutes">Dk</option></select></div>
                </div>
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">Idle İçerik Yenileme</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.idleContentRefreshSeconds" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.idleContentRefreshUnit" class="eisa-field"><option value="seconds">Sn</option><option value="minutes">Dk</option></select></div>
                </div>
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">Idle İçerik Min. Gösterim</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.idleContentMinSeconds" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.idleContentMinUnit" class="eisa-field"><option value="seconds">Sn</option><option value="minutes">Dk</option></select></div>
                </div>
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">Idle İçerik Maks. Gösterim</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.idleContentMaxSeconds" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.idleContentMaxUnit" class="eisa-field"><option value="seconds">Sn</option><option value="minutes">Dk</option></select></div>
                </div>
              </div>

              <div style="height:1px;background:#E5E7EB;margin:1.1rem 0;"></div>
              <div style="display:flex;align-items:center;gap:0.55rem;margin-bottom:0.9rem;">
                <i class="fa-solid fa-volume-high" style="color:#B1121B;"></i>
                <div>
                  <p class="eisa-field-label" style="margin:0;">Idle Ses</p>
                  <p style="margin:0.15rem 0 0;font-size:0.75rem;color:#6B7280;">Seçilen sesler sırayla çalar; her etkileşim bu sayacı sıfırlar.</p>
                </div>
              </div>

              <div class="eisa-form-row">
                <div class="audio-library-heading"><span class="audio-library-symbol"><i class="fa-solid fa-music"></i></span><div><h3>Ses Kütüphanesi</h3><p>Dinle, seç ve cihazına ekle.</p></div><span class="audio-count">{{ selectedKioskAudioIds.length }} seçili</span></div>
                <button type="button" class="audio-listen-button" style="margin-bottom:10px;" :disabled="!kioskAudioLibrary.length || kioskEditLoading" @click="toggleAllAudio"><i class="fa-solid fa-check-double"></i> {{ allAudioSelected ? 'Seçimi Temizle' : 'Tümünü Seç' }}</button>
                <div v-if="kioskAudioLibraryLoading" style="font-size:0.75rem;color:#6B7280;">Ses kütüphanesi yükleniyor…</div>
                <div v-else-if="kioskAudioLibrary.length" class="audio-library-list">
                  <div v-for="asset in kioskAudioLibrary" :key="asset.id" class="audio-library-item" :class="{ 'audio-library-item--selected': selectedKioskAudioIds.includes(asset.id) }">
                    <input type="checkbox" :aria-label="`${asset.originalName} kioska ata`" :checked="selectedKioskAudioIds.includes(asset.id)" @change="toggleKioskAudio(asset.id)" />
                    <span class="audio-file-icon"><i class="fa-solid fa-file-audio"></i></span><span class="audio-file-name" :title="asset.originalName">{{ asset.originalName }}</span>
                    <span v-if="selectedKioskAudioIds.includes(asset.id)" style="margin-left:auto;color:#6B7280;">{{ selectedKioskAudioIds.indexOf(asset.id) + 1 }}.</span>
                    <button type="button" class="audio-listen-button" :disabled="audioPreviewLoading" @click="listenToAudio(asset)"><i class="fa-solid fa-play"></i> Dinle</button>
                    <button type="button" class="audio-delete-button" :aria-label="`${asset.originalName} sil`" title="Kütüphaneden sil" :disabled="audioDeleting || kioskEditSaving" @click="audioDeleteTarget = asset"><i class="fa-solid fa-trash-can"></i></button>
                  </div>
                </div>
                <div v-else-if="!kioskAudioLibraryLoading" class="audio-empty"><i class="fa-solid fa-headphones"></i><strong>İlk sesinizi ekleyin</strong><span>Yüklediğiniz sesler burada listelenecek.</span></div>
                <div v-if="audioPreviewUrl" class="audio-preview">
                  <p>{{ audioPreviewName }}</p>
                  <audio :key="audioPreviewUrl" :src="audioPreviewUrl" controls autoplay style="width:100%;" @error="toast.error('Ses oynatılamadı.')"></audio>
                </div>
                <div class="audio-upload-panel">
                <label class="audio-upload-picker">
                  <input :key="kioskAudioInputKey" type="file" multiple accept="audio/mpeg,audio/wav,audio/ogg,.mp3,.wav,.ogg" :disabled="audioUploading" @change="onKioskAudioSelected" />
                  <span class="audio-upload-icon"><i class="fa-solid fa-cloud-arrow-up"></i></span>
                  <strong>{{ kioskAudioFiles.length ? `${kioskAudioFiles.length} dosya seçildi` : 'Yeni ses dosyası seç' }}</strong>
                  <span>MP3, WAV veya OGG · Dosya başına en fazla 20 MB</span>
                </label>
                <div v-if="kioskAudioFiles.length" style="margin-top:0.4rem;display:grid;gap:0.25rem;">
                  <p v-for="file in kioskAudioFiles" :key="`${file.name}-${file.size}`" style="margin:0;font-size:0.75rem;color:#059669;">
                    <i class="fa-solid fa-circle-check"></i> {{ file.name }} kütüphaneye yüklenecek.
                  </p>
                </div>
                <button type="button" class="audio-upload-button" :disabled="!kioskAudioFiles.length || audioUploading || kioskEditSaving" @click="uploadAudioToLibrary"><i :class="audioUploading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-plus'"></i> {{ audioUploading ? 'Yükleniyor…' : 'Kütüphaneye Ekle' }}</button>
                </div>
                <p class="audio-library-hint"><i class="fa-solid fa-circle-info"></i> Sesleri seçtikten sonra Güncelle ile cihazınıza atayın. Seçim sırası, çalma sırasıdır.</p>
              </div>

              <div class="dm-settings-grid">
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">İlk Ses İçin Idle Bekleme</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.idleAudioDelayMinutes" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.idleAudioDelayUnit" class="eisa-field"><option value="minutes">Dk</option><option value="seconds">Sn</option></select></div>
                </div>
                <div class="eisa-form-row" style="margin:0;">
                  <label class="eisa-field-label">Sonraki Sesler Arası Bekleme</label>
                  <div class="dm-duration-input"><input v-model.number="kioskEditForm.idleAudioRepeatMinutes" type="number" min="1" class="eisa-field" /><select v-model="kioskEditForm.idleAudioRepeatUnit" class="eisa-field"><option value="minutes">Dk</option><option value="seconds">Sn</option></select></div>
                </div>
              </div>
              <div class="eisa-form-row" style="margin-top:0.8rem;">
                <label class="eisa-field-label">Ses Çalma Zamanı</label>
                <select v-model="kioskEditForm.idleAudioScheduleMode" class="eisa-field">
                  <option value="BUSINESS_HOURS">Mesai içi (08:00–19:00)</option>
                  <option value="ALL_DAY">Mesai dışı / 24 saat</option>
                </select>
                <label class="eisa-toggle" style="min-height:38px;margin-top:0.45rem;">
                  <input type="checkbox" v-model="kioskEditForm.idleAudioPlayOnDuty" />
                  Nöbet günlerinde çal (nöbet günü 24 saat)
                </label>
              </div>
              <label class="eisa-toggle" style="min-height:42px;margin-top:0.8rem;">
                <input type="checkbox" v-model="kioskEditForm.idleAudioEnabled" :disabled="!selectedKioskAudioIds.length && !kioskAudioFiles.length" />
                Ses Aktif
              </label>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" :disabled="kioskEditSaving" @click="closeEditKiosk">İptal</button>
              <div v-if="kioskEditError" role="alert" style="color:#b1121b;font-size:12px;flex:1;">{{ kioskEditError }}</div>
              <span v-if="kioskEditLoading">Kayıtlı ayarlar yükleniyor…</span>
              <button type="button" class="eisa-btn eisa-btn-cta" :disabled="kioskEditSaving || audioUploading || !kioskEditLoaded || audioDeleting" @click="saveEditKiosk">
                <i v-if="kioskEditSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-check"></i>
                {{ kioskEditSaving ? 'Kaydediliyor…' : 'Güncelle' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Kiosk Detay Modal                                                       -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="kioskDetailOpen"
        class="eisa-modal-backdrop"
        @click.self="closeKioskDetail"
      >
        <Transition name="modal" appear>
          <div v-if="kioskDetailOpen" class="eisa-modal" style="max-width:760px;">
            <div class="eisa-modal-header">
              <div>
                <h3 class="eisa-modal-title">Kiosk Detayı</h3>
                <p class="eisa-stat-sub">{{ kioskDetailTarget?.pharmacyName }}</p>
              </div>
              <button class="eisa-modal-close" @click="closeKioskDetail">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body" v-if="kioskDetailTarget">
              <div class="eisa-detail-grid">
                <div class="eisa-detail-row"><span>Kiosk Adı:</span><strong>{{ kioskDetailTarget.ad || '—' }}</strong></div>
                <div class="eisa-detail-row"><span>Durum:</span><span class="badge" :class="isOnline(kioskDetailTarget) ? 'badge-approved' : 'badge-rejected'">{{ isOnline(kioskDetailTarget) ? 'Online' : 'Offline' }}</span></div>
                <div class="eisa-detail-row"><span>MAC Adresi:</span><code>{{ kioskDetailTarget.mac || '—' }}</code></div>
                <div class="eisa-detail-row"><span>IP Adresi:</span><code>{{ kioskDetailTarget.lastIp || '—' }}</code></div>
                <div class="eisa-detail-row"><span>Son Ping:</span>{{ formatPing(kioskDetailTarget.lastPing) }}</div>
                <div class="eisa-detail-row"><span>Uygulama Anahtarı:</span><code>{{ kioskDetailTarget.appKey || '—' }}</code></div>
              </div>

              <div class="detail-section-title">Cihaz Bilgileri</div>
              <div v-if="provisioningHistoryForKiosk(kioskDetailTarget.id).length && provisioningHistoryForKiosk(kioskDetailTarget.id)[0].deviceMetadata">
                <div v-if="formatProvisioningMetadata(provisioningHistoryForKiosk(kioskDetailTarget.id)[0].deviceMetadata).length" class="eisa-detail-grid" style="margin-bottom:1rem;">
                  <div
                    v-for="entry in formatProvisioningMetadata(provisioningHistoryForKiosk(kioskDetailTarget.id)[0].deviceMetadata)"
                    :key="entry.key"
                    class="eisa-detail-row"
                  >
                    <span>{{ entry.label }}:</span>
                    <span class="detail-value">{{ entry.value }}</span>
                  </div>
                  <template v-if="provisioningHistoryForKiosk(kioskDetailTarget.id)[0].deviceMetadata?.ip_addresses?.length">
                    <div class="eisa-detail-row" style="grid-column:1/-1;">
                      <span>IP Adresleri:</span>
                      <div class="ip-list">
                        <span
                          v-for="ip in provisioningHistoryForKiosk(kioskDetailTarget.id)[0].deviceMetadata.ip_addresses"
                          :key="ip.address"
                          class="ip-badge"
                        >
                          <code>{{ ip.address }}</code>
                          <em>{{ ip.iface }}</em>
                        </span>
                      </div>
                    </div>
                  </template>
                </div>
                <div v-else class="eisa-empty-inline">Cihaz metadata bilgisi bulunmuyor.</div>
              </div>
              <div v-else class="eisa-empty-inline">Bu kiosk için cihaz bilgisi bulunamadı.</div>

              <div class="detail-section-title">Provisioning Geçmişi</div>
              <div v-if="provisioningHistoryForKiosk(kioskDetailTarget.id).length" class="eisa-provisioning-list">
                <div
                  v-for="request in provisioningHistoryForKiosk(kioskDetailTarget.id)"
                  :key="request.id"
                  class="eisa-provisioning-item"
                >
                  <div class="eisa-provisioning-item__head">
                    <span class="badge" :class="statusClassForProvisioning(request.status)">{{ statusLabelForProvisioning(request.status) }}</span>
                    <span class="eisa-stat-sub">{{ formatProvisioningDate(request.firstSeenAt) }}</span>
                  </div>
                  <div class="eisa-detail-row"><span>Hostname:</span>{{ request.hostname || '—' }}</div>
                  <div class="eisa-detail-row"><span>MAC:</span><code>{{ request.mac }}</code></div>
                  <div class="eisa-detail-row"><span>Başvuru Sayısı:</span>{{ request.requestCount }}</div>
                  <div v-if="request.approvedAt" class="eisa-detail-row"><span>Onay Tarihi:</span>{{ formatProvisioningDate(request.approvedAt) }}</div>
                  <div v-if="request.rejectedAt" class="eisa-detail-row"><span>Red Tarihi:</span>{{ formatProvisioningDate(request.rejectedAt) }}</div>
                  <div v-if="request.rejectionReason" class="eisa-detail-row"><span>Red Nedeni:</span>{{ request.rejectionReason }}</div>
                </div>
              </div>
              <div v-else class="eisa-empty-inline">Bu kioska bağlı provisioning kaydı bulunamadı.</div>

              <div class="detail-section-title">Eczane Atama Geçmişi</div>
              <div v-if="kioskDetailTarget.assignments?.length" class="eisa-provisioning-list">
                <div v-for="assignment in kioskDetailTarget.assignments" :key="assignment.id" class="eisa-provisioning-item">
                  <div class="eisa-provisioning-item__head">
                    <strong>{{ assignment.pharmacyName }}</strong>
                    <span class="badge" :class="assignment.endedAt ? 'badge-rejected' : 'badge-approved'">{{ assignment.endedAt ? 'Sona erdi' : 'Aktif' }}</span>
                  </div>
                  <div class="eisa-detail-row"><span>Başlangıç:</span>{{ formatProvisioningDate(assignment.startedAt) }}</div>
                  <div class="eisa-detail-row"><span>Bitiş:</span>{{ assignment.endedAt ? formatProvisioningDate(assignment.endedAt) : '—' }}</div>
                  <div v-if="assignment.reason" class="eisa-detail-row"><span>Neden:</span>{{ assignment.reason }}</div>
                  <div v-if="assignment.movedBy" class="eisa-detail-row"><span>Taşıyan:</span>{{ assignment.movedBy }}</div>
                </div>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-cta" @click="openTransfer(kioskDetailTarget)">Eczaneye Taşı</button>
              <button class="eisa-btn eisa-btn-ghost" @click="closeKioskDetail">Kapat</button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <div v-if="transferOpen" class="eisa-modal-backdrop" @click.self="closeTransfer">
      <div class="eisa-modal eisa-modal--transfer" role="dialog" aria-modal="true">
        <div class="eisa-modal-header"><h3 class="eisa-modal-title">Cihazı Başka Eczaneye Taşı</h3><button class="eisa-modal-close" title="Kapat" @click="closeTransfer"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="eisa-modal-body">
          <div class="transfer-current">
            <span>Mevcut Eczane</span>
            <strong>{{ transferTarget?.pharmacyName || '—' }}</strong>
          </div>
          <div class="eisa-form-row">
            <label class="eisa-field-label">Hedef Eczane <span class="required">*</span></label>
            <EisaLookup v-model="transferForm.pharmacyId" :options="pharmacyOptions.filter(item => String(item.id) !== String(transferTarget?.pharmacyId))" placeholder="Eczane adıyla ara…" />
          </div>
          <div class="eisa-form-row">
            <label class="eisa-field-label">Taşıma Nedeni (Opsiyonel)</label>
            <textarea v-model="transferForm.reason" class="eisa-field" maxlength="250" rows="3" placeholder="Atama geçmişinde görünecek kısa açıklama"></textarea>
          </div>
          <div v-if="selectedTransferPharmacy" class="transfer-summary">
            <i class="fa-solid fa-arrow-right-arrow-left"></i>
            <div><span>{{ transferTarget?.ad }}</span><strong>{{ transferTarget?.pharmacyName }} → {{ selectedTransferPharmacy.label }}</strong></div>
          </div>
          <div v-if="transferError" class="eisa-error-banner"><i class="fa-solid fa-triangle-exclamation"></i>{{ transferError }}</div>
        </div>
        <div class="eisa-modal-footer"><button class="eisa-btn eisa-btn-ghost" :disabled="transferSaving" @click="closeTransfer">İptal</button><button class="eisa-btn eisa-btn-cta" :disabled="transferSaving || !transferForm.pharmacyId" @click="confirmTransfer"><i :class="transferSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-arrow-right-arrow-left'"></i>{{ transferSaving ? 'Taşınıyor…' : 'Taşı' }}</button></div>
      </div>
    </div>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Pending Request Detay Modal                                             -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="pendingDetailOpen"
        class="eisa-modal-backdrop"
        @click.self="closePendingDetail"
      >
        <Transition name="modal" appear>
          <div v-if="pendingDetailOpen" class="eisa-modal" style="max-width:760px;">
            <div class="eisa-modal-header">
              <div>
                <h3 class="eisa-modal-title">Onay Bekleyen Cihaz Detayı</h3>
                <p class="eisa-stat-sub">{{ pendingDetailTarget?.hostname || 'Bilinmeyen Cihaz' }}</p>
              </div>
              <button class="eisa-modal-close" @click="closePendingDetail">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body" v-if="pendingDetailTarget">
              <div class="eisa-detail-grid">
                <div class="eisa-detail-row"><span>Hostname:</span><strong>{{ pendingDetailTarget.hostname || '—' }}</strong></div>
                <div class="eisa-detail-row"><span>Durum:</span><span class="badge badge-pending">Onay Bekliyor</span></div>
                <div class="eisa-detail-row"><span>MAC Adresi:</span><code>{{ pendingDetailTarget.mac }}</code></div>
                <div class="eisa-detail-row"><span>Başvuru Sayısı:</span>{{ pendingDetailTarget.requestCount }}</div>
                <div class="eisa-detail-row"><span>İlk Görülme:</span>{{ formatProvisioningDate(pendingDetailTarget.firstSeenAt) }}</div>
                <div class="eisa-detail-row"><span>Son Görülme:</span>{{ formatProvisioningDate(pendingDetailTarget.lastSeenAt) }}</div>
              </div>

              <div class="detail-section-title">Cihaz Bilgileri</div>
              <div v-if="pendingDetailTarget.deviceMetadata && Object.keys(pendingDetailTarget.deviceMetadata).length">
                <div v-if="formatProvisioningMetadata(pendingDetailTarget.deviceMetadata).length" class="eisa-detail-grid" style="margin-bottom:1rem;">
                  <div
                    v-for="entry in formatProvisioningMetadata(pendingDetailTarget.deviceMetadata)"
                    :key="entry.key"
                    class="eisa-detail-row"
                  >
                    <span>{{ entry.label }}:</span>
                    <span class="detail-value">{{ entry.value }}</span>
                  </div>
                  <template v-if="pendingDetailTarget.deviceMetadata?.ip_addresses?.length">
                    <div class="eisa-detail-row" style="grid-column:1/-1;">
                      <span>IP Adresleri:</span>
                      <div class="ip-list">
                        <span
                          v-for="ip in pendingDetailTarget.deviceMetadata.ip_addresses"
                          :key="ip.address"
                          class="ip-badge"
                        >
                          <code>{{ ip.address }}</code>
                          <em>{{ ip.iface }}</em>
                        </span>
                      </div>
                    </div>
                  </template>
                </div>
                <div v-else class="eisa-empty-inline">Cihaz metadata bilgisi bulunmuyor.</div>
              </div>
              <div v-else class="eisa-empty-inline">Bu cihaz için metadata bilgisi bulunamadı.</div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" @click="closePendingDetail">Kapat</button>
              <button class="eisa-btn eisa-btn-cta" @click="closePendingDetail(); openApprove(pendingDetailTarget);">
                <i class="fa-solid fa-check"></i>
                Onayla
              </button>
              <button class="eisa-btn eisa-btn-danger" @click="closePendingDetail(); openReject(pendingDetailTarget);">
                <i class="fa-solid fa-times"></i>
                Reddet
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Provisioning Onay Modal                                                 -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="approveModalOpen"
        class="eisa-modal-backdrop"
        @click.self="closeApprove"
      >
        <Transition name="modal" appear>
          <div v-if="approveModalOpen" class="eisa-modal" style="max-width:520px;">
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">Cihazı Onayla</h3>
              <button class="eisa-modal-close" @click="closeApprove">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body" v-if="approveTarget">
              <p class="modal-info">
                <strong>{{ approveTarget.mac }}</strong> MAC adresli cihazı onaylıyorsunuz.
                Bir eczane seçin ve kiosk adı belirleyin.
              </p>
              <div v-if="approveError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ approveError }}
              </div>
              <div class="eisa-form-row">
                <label class="eisa-field-label">Eczane <span style="color:#EF4444;">*</span></label>
                <EisaLookup
                  v-model="approveForm.eczane_id"
                  :options="pharmacyOptions"
                  placeholder="Eczane adı, il veya ilçe ile ara…"
                  :clearable="true"
                />
              </div>
              <div class="eisa-form-row">
                <label class="eisa-field-label">Kiosk Adı <span style="color:#EF4444;">*</span></label>
                <input
                  v-model="approveForm.ad"
                  type="text"
                  class="eisa-field"
                  placeholder="Örn: Kiosk 1"
                  maxlength="50"
                />
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" @click="closeApprove" :disabled="approveSaving">
                İptal
              </button>
              <button
                class="eisa-btn eisa-btn-cta"
                @click="confirmApprove"
                :disabled="approveSaving"
              >
                <i v-if="approveSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-check"></i>
                {{ approveSaving ? 'Onaylanıyor…' : 'Onayla' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Provisioning Red Modal                                                  -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="rejectModalOpen"
        class="eisa-modal-backdrop"
        @click.self="closeReject"
      >
        <Transition name="modal" appear>
          <div v-if="rejectModalOpen" class="eisa-modal" style="max-width:520px;">
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">Cihazı Reddet</h3>
              <button class="eisa-modal-close" @click="closeReject">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body" v-if="rejectTarget">
              <p class="modal-info">
                <strong>{{ rejectTarget.mac }}</strong> MAC adresli cihazı reddediyorsunuz.
              </p>
              <div v-if="rejectError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ rejectError }}
              </div>
              <div class="eisa-form-row">
                <label class="eisa-field-label">Red Nedeni (opsiyonel)</label>
                <textarea
                  v-model="rejectReason"
                  class="eisa-field"
                  rows="3"
                  maxlength="500"
                  placeholder="Red nedeni (opsiyonel)…"
                  style="resize:none;"
                ></textarea>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" @click="closeReject" :disabled="rejectSaving">
                İptal
              </button>
              <button
                class="eisa-btn eisa-btn-danger"
                @click="confirmReject"
                :disabled="rejectSaving"
              >
                <i v-if="rejectSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-times"></i>
                {{ rejectSaving ? 'Reddediliyor…' : 'Reddet' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- Kiosk Sil -->
  <EisaDeleteConfirm
    :open="kioskDeleteOpen"
    title="Kiosk'u Kaldır"
    :message="`${kioskDeleteTarget?.mac} MAC adresli kiosku kaldırmak istediğinizden emin misiniz?`"
    confirm-label="Evet, Kaldır"
    :loading="kioskDeleting"
    @confirm="confirmDeleteKiosk"
    @cancel="closeDeleteKiosk"
  />

  <!-- Eczane Sil -->
  <EisaDeleteConfirm
    :open="deleteModalOpen"
    title="Eczane Sil"
    :message="`${deleteTarget?.name} eczanesini kalıcı olarak silmek istediğinizden emin misiniz?`"
    confirm-label="Evet, Sil"
    :loading="deleting"
    @confirm="confirmDelete"
    @cancel="closeDelete"
  />

<EisaDeleteConfirm
  :open="!!audioDeleteTarget"
  title="Sesi kütüphaneden sil"
  :message="`“${audioDeleteTarget?.originalName || ''}” kütüphaneden ve bağlı olduğu tüm kiosklardan kaldırılacak. Cihazlara sonraki senkronizasyonda uygulanır. Devam edilsin mi?`"
  :loading="audioDeleting"
  @confirm="deleteLibraryAudio"
  @cancel="!audioDeleting && (audioDeleteTarget = null)"
/>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(1rem);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}

:deep(.kiosk-summary-pill--pending) {
  background: rgba(217, 119, 6, 0.12);
  color: #92400e;
}

:deep(.eisa-kiosk-dot--pending) {
  background: #d97706;
  box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.14);
}

.eisa-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1rem;
}

.eisa-detail-row {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  font-size: 0.88rem;
  color: #374151;
}

.eisa-detail-row > span:first-child {
  min-width: 140px;
  color: #6b7280;
  font-weight: 600;
}

.eisa-detail-row code {
  word-break: break-all;
}

.eisa-provisioning-list {
  display: grid;
  gap: 0.75rem;
}

.eisa-provisioning-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  background: #f8fafc;
}

.eisa-provisioning-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.eisa-empty-inline {
  padding: 0.9rem 1rem;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  color: #6b7280;
  background: #fafafa;
}

:deep(.pending-devices-embed .pending-devices) {
  padding: 0;
  max-width: none;
}

:deep(.pending-devices-embed .page-header) {
  display: none;
}

:deep(.pending-devices-embed .filter-bar) {
  margin-top: 0;
}

:deep(.pending-devices-embed .loading-state),
:deep(.pending-devices-embed .empty-state) {
  padding-top: 2rem;
  padding-bottom: 2rem;
}

.kiosk-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.kiosk-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
}

.kiosk-tab:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.kiosk-tab--active {
  border-color: #B1121B;
  background: rgba(177, 18, 27, 0.05);
  color: #B1121B;
}

.eisa-kiosk-card--pending {
  border-color: #FDE68A;
  background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
}

.eisa-kiosk-card-stripe--pending {
  background: linear-gradient(180deg, #F59E0B 0%, #D97706 100%);
}

.modal-info {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  color: #4b5563;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.badge-approved {
  background: #d1fae5;
  color: #065f46;
}

.badge-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.font-mono {
  font-family: 'DM Mono', monospace;
}

.dm-transfer-button {
  min-height: 32px;
  padding: 0.35rem 0.65rem;
  color: var(--eisa-info, #4338ca);
  border-color: var(--eisa-info-border, #c7d2fe);
  white-space: nowrap;
}

.dm-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.dm-duration-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 5rem;
  gap: 0.4rem;
}

.eisa-modal--transfer { max-width: 560px; }
.transfer-current,
.transfer-summary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem;
  border: 1px solid var(--eisa-info-border, #c7d2fe);
  border-radius: 10px;
  background: var(--eisa-info-soft, #eef2ff);
  color: var(--eisa-info, #4338ca);
}
.transfer-current { justify-content: space-between; margin-bottom: 1rem; }
.transfer-current span,
.transfer-summary span { font-size: 0.72rem; color: #6b7280; }
.transfer-summary { margin-top: 1rem; }
.transfer-summary div { display: flex; flex-direction: column; gap: 0.15rem; }
.eisa-modal--transfer .eisa-form-row { margin-top: 1rem; }
.required { color: #dc2626; }

@media (max-width: 720px) {
  .dm-transfer-button { font-size: 0; padding: 0.45rem; }
  .dm-transfer-button i { font-size: 0.8rem; }
  .dm-settings-grid { grid-template-columns: 1fr; }
}

.detail-value {
  font-family: monospace;
  font-size: 0.82rem;
  word-break: break-all;
}

.ip-list {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ip-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
}

.ip-badge code {
  background: #f1f5f9;
  border-radius: 4px;
  padding: 0.1rem 0.4rem;
  font-size: 0.8rem;
}

.ip-badge em {
  color: #6b7280;
  font-style: normal;
  font-size: 0.75rem;
}
</style>
<style scoped>
.audio-library-heading { display:flex; align-items:center; gap:12px; margin:16px 0; }
.audio-library-heading h3 { margin:0; font-size:15px; font-weight:750; color:#1f2937; }
.audio-library-heading p { margin:3px 0 0; font-size:12px; color:#6b7280; }
.audio-library-symbol,.audio-file-icon,.audio-upload-icon { display:grid; place-items:center; flex-shrink:0; color:#b1121b; background:#fff1f2; border-radius:12px; width:42px; height:42px; }
.audio-count { margin-left:auto; padding:5px 10px; border-radius:20px; color:#b1121b; background:#fff1f2; font-size:11px; font-weight:700; white-space:nowrap; }
.audio-library-list { max-height:240px; overflow:auto; display:grid; gap:8px; padding:2px; }
.audio-library-item { display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid #e5e7eb; border-radius:12px; background:white; transition:background .15s,border-color .15s; }
.audio-library-item--selected { border-color:#e8a5aa; background:#fff7f7; }
.audio-library-item input { width:17px; height:17px; accent-color:#b1121b; cursor:pointer; flex-shrink:0; }
.audio-file-icon { width:32px; height:36px; border-radius:8px; }
.audio-file-name { min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12px; font-weight:600; color:#374151; }
.audio-listen-button { display:inline-flex; align-items:center; gap:6px; padding:8px 12px; border:1px solid #e5e7eb; border-radius:8px; background:white; color:#374151; font:inherit; font-size:12px; font-weight:650; cursor:pointer; }
.audio-listen-button i { font-size:10px; color:#b1121b; }
.audio-listen-button:hover { background:#fff1f2; border-color:#e8a5aa; }
.audio-empty { display:grid; justify-items:center; gap:8px; padding:24px 12px; background:#f9fafb; border-radius:12px; color:#9ca3af; }
.audio-empty i { font-size:24px; }.audio-empty strong { font-size:13px; color:#4b5563; }.audio-empty span { font-size:12px; }
.audio-upload-panel { margin-top:16px; padding:14px; border:1px solid #e5e7eb; border-radius:14px; background:#fafafa; }
.audio-upload-picker { position:relative; display:grid; justify-items:center; gap:7px; padding:18px 12px; border:1px dashed #d1d5db; border-radius:10px; background:white; cursor:pointer; text-align:center; }
.audio-upload-picker:hover,.audio-upload-picker:focus-within { border-color:#b1121b; background:#fffafa; }
.audio-upload-picker input { position:absolute; inset:0; width:100%; height:100%; opacity:0; cursor:pointer; }
.audio-upload-picker strong { font-size:13px; color:#374151; }.audio-upload-picker>span:last-child { font-size:11px; color:#6b7280; }
.audio-upload-button { display:flex; justify-content:center; align-items:center; gap:8px; width:100%; margin-top:12px; padding:12px 16px; border:0; border-radius:9px; background:#b1121b; color:white; font:inherit; font-size:13px; font-weight:700; cursor:pointer; box-shadow:0 3px 8px #b1121b20; }
.audio-upload-button:hover:not(:disabled) { background:#941019; }
.audio-upload-button:disabled { background:#e5e7eb; color:#9ca3af; box-shadow:none; cursor:not-allowed; }
.audio-listen-button:disabled { opacity:.5; cursor:wait; }
.audio-delete-button { display:grid; place-items:center; width:34px; height:34px; flex-shrink:0; border:1px solid #fecdd3; border-radius:8px; color:#b1121b; background:#fff1f2; cursor:pointer; }
.audio-delete-button:hover { background:#ffe4e6; }
.audio-delete-button:focus-visible { outline:2px solid #b1121b; outline-offset:2px; }
.audio-delete-button:disabled { opacity:.5; cursor:not-allowed; }
.audio-library-hint { display:flex; gap:7px; margin:12px 0 18px; color:#6b7280; font-size:11px; line-height:1.6; }.audio-library-hint i { margin-top:3px; }
.audio-preview { margin-top:12px; padding:12px; border-radius:12px; background:#f3f4f6; }.audio-preview p { margin:0 0 8px; overflow-wrap:anywhere; font-size:12px; font-weight:600; color:#374151; }
.audio-listen-button:focus-visible,.audio-upload-button:focus-visible { outline:2px solid #b1121b; outline-offset:3px; }
@media(max-width:480px) { .audio-library-item { gap:6px; padding:8px; }.audio-file-icon { display:none; }.audio-listen-button { padding:8px; } }
</style>

