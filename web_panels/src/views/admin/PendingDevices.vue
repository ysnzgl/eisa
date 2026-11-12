<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { toast } from 'vue-sonner';
import DefinitionPage from '../../components/shared/DefinitionPage.vue';
import DefinitionDialog from '../../components/shared/DefinitionDialog.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import { listProvisioningRequests, approveProvisioningRequest, rejectProvisioningRequest, getPharmacies } from '../../services/devices';
import { listPhysicalDevices } from '../../services/inventory';
import { humanError } from '../../services/api';

const records = ref([]), pharmacies = ref([]), devices = ref([]), loading = ref(false), error = ref(''), search = ref(''), state = ref('PENDING');
const target = ref(null), operation = ref(''), saving = ref(false), formError = ref('');
const form = reactive({ eczane_id: '', ad: '', fiziksel_cihaz_id: '', rejection_reason: '' });
const filtered = computed(() => records.value.filter(row => (!state.value || row.status === state.value) && `${row.mac} ${row.hostname}`.toLocaleLowerCase('tr').includes(search.value.toLocaleLowerCase('tr'))));
const pharmacyOptions = computed(() => pharmacies.value.map(row => ({ id: row.id, label: row.name, sub: `${row.ilAdi} / ${row.ilceAdi}` })));
const available = computed(() => devices.value.filter(row => !row.kiosk && row.aktif && (!row.eczane || row.eczane === Number(form.eczane_id))));
const label = status => ({ PENDING: 'Onay bekliyor', APPROVED: 'Onaylandı', REJECTED: 'Reddedildi' }[status] || status);
const date = value => value ? new Date(value).toLocaleString('tr-TR') : '—';
watch(() => form.eczane_id, () => { form.fiziksel_cihaz_id = ''; });
async function load() { loading.value = true; error.value = ''; try { records.value = await listProvisioningRequests(); } catch (e) { error.value = humanError(e); } finally { loading.value = false; } }
async function open(row, action) {
  target.value = row; operation.value = action; formError.value = '';
  Object.assign(form, { eczane_id: '', ad: row.hostname || 'Kiosk', fiziksel_cihaz_id: '', rejection_reason: '' });
  if (action === 'approve') {
    try { const [p, d] = await Promise.all([getPharmacies(), listPhysicalDevices({ eslesmemis: true })]); pharmacies.value = p; devices.value = Array.isArray(d.data) ? d.data : d.data.results || []; } catch (e) { formError.value = humanError(e); }
  }
}
async function save() {
  if (operation.value === 'detail') { target.value = null; return; }
  if (operation.value === 'approve' && (!form.eczane_id || !form.fiziksel_cihaz_id || !form.ad.trim())) { formError.value = 'Eczane, fiziksel cihaz ve kiosk adı gerekli.'; return; }
  saving.value = true; formError.value = '';
  try {
    if (operation.value === 'approve') await approveProvisioningRequest(target.value.id, { eczane_id: Number(form.eczane_id), ad: form.ad.trim(), fiziksel_cihaz_id: Number(form.fiziksel_cihaz_id) });
    else await rejectProvisioningRequest(target.value.id, { rejection_reason: form.rejection_reason });
    target.value = null; await load(); window.dispatchEvent(new Event('eisa-nav-badges-refresh')); window.dispatchEvent(new Event('eisa-provisioning-refresh'));
    toast.success(operation.value === 'approve' ? 'Cihaz onaylandı ve seri numarasıyla eşleştirildi.' : 'Provizyon talebi reddedildi.');
  } catch (e) { formError.value = humanError(e); } finally { saving.value = false; }
}
onMounted(load);
</script>
<template>
  <DefinitionPage v-model:search="search" title="Provizyon Talepleri" eyebrow="ECZANE & KİOSK / CİHAZ EŞLEŞTİRME" description="Bağlantı isteyen kiosku kayıtlı fiziksel cihaz ve eczane ile eşleştirin." :count="filtered.length" :loading="loading" :error="error" @refresh="load">
    <template #filters><select v-model="state" class="eisa-field eisa-filter" aria-label="Talep durumu"><option value="PENDING">Onay bekleyenler</option><option value="APPROVED">Onaylananlar</option><option value="REJECTED">Reddedilenler</option><option value="">Tüm talepler</option></select><RouterLink to="/admin/device-inventory" class="eisa-btn eisa-btn-ghost"><i class="fa-solid fa-boxes-stacked"></i>Cihaz Tanımları</RouterLink></template>
    <div v-if="filtered.length" class="eisa-table-wrap"><table class="eisa-table"><thead><tr><th>MAC / Cihaz adı</th><th>İlk bağlantı</th><th>Son bağlantı</th><th>Durum</th><th>İşlemler</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id"><td><span class="eisa-record-name">{{ row.mac }}</span><span class="eisa-record-detail">{{ row.hostname || 'Makine adı bildirilmedi' }}</span></td><td>{{ date(row.firstSeenAt) }}</td><td>{{ date(row.lastSeenAt) }}</td><td><span class="eisa-pill" :class="row.status === 'APPROVED' ? 'eisa-pill-success' : row.status === 'REJECTED' ? 'eisa-pill-muted' : 'eisa-pill-warning'">{{ label(row.status) }}</span></td><td><div class="eisa-table-actions"><button v-if="row.status === 'PENDING'" class="eisa-btn eisa-btn-cta eisa-btn--sm" @click="open(row, 'approve')"><i class="fa-solid fa-link"></i>Eşleştir ve Onayla</button><button v-if="row.status === 'PENDING'" class="eisa-icon-btn" aria-label="Talebi reddet" title="Talebi reddet" @click="open(row, 'reject')"><i class="fa-solid fa-xmark"></i></button><button class="eisa-icon-btn" aria-label="Talep ayrıntısı" title="Talep ayrıntısı" @click="open(row, 'detail')"><i class="fa-solid fa-circle-info"></i></button></div></td></tr></tbody></table></div>
    <div v-else class="eisa-definition-empty"><i class="fa-solid fa-satellite-dish"></i><strong>Bu durumda provizyon talebi yok</strong><span>Yeni kiosk bağlantı istediğinde bu listede görünecek.</span></div>
    <template #dialogs><DefinitionDialog :open="!!target" :title="operation === 'approve' ? 'Cihazı Eşleştir ve Onayla' : operation === 'reject' ? 'Provizyon Talebini Reddet' : 'Provizyon Ayrıntısı'" :busy="saving" :error="formError" :save-label="operation === 'approve' ? 'Eşleştir ve Onayla' : operation === 'reject' ? 'Reddet' : 'Kapat'" @close="target = null" @save="save">
      <p class="eisa-reset-info">MAC adresi: <strong>{{ target?.mac }}</strong></p>
      <div v-if="operation === 'approve'" class="eisa-form-grid">
        <div class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Eczane *</span><EisaLookup v-model="form.eczane_id" :options="pharmacyOptions" placeholder="Eczane seçin…" /></div>
        <label class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Kayıtlı fiziksel cihaz / seri numarası *</span><select v-model="form.fiziksel_cihaz_id" class="eisa-field" :disabled="!form.eczane_id" required><option value="">Seri numarasını seçin</option><option v-for="device in available" :key="device.id" :value="device.id">{{ device.seri_no }} — {{ device.marka }} {{ device.model }}</option></select></label>
        <label class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Kiosk adı *</span><input v-model.trim="form.ad" class="eisa-field" required maxlength="50" /></label>
        <span class="eisa-form-note eisa-form-row-full">Seri numarası listede yoksa önce Cihaz Tanımları ekranından fiziksel cihazı kaydedin.</span>
      </div>
      <label v-else-if="operation === 'reject'" class="eisa-form-row"><span class="eisa-field-label">Red nedeni</span><textarea v-model="form.rejection_reason" class="eisa-field" rows="3" maxlength="500"></textarea></label>
      <div v-else><p class="eisa-reset-info">Makine adı: <strong>{{ target?.hostname || '—' }}</strong></p><p class="eisa-reset-info">Durum: {{ label(target?.status) }}</p><p class="eisa-reset-info">İstek sayısı: {{ target?.requestCount }}</p><p v-if="target?.rejectionReason" class="eisa-reset-info">Red nedeni: {{ target.rejectionReason }}</p><p v-if="target?.kioskAd" class="eisa-reset-info">Eşleşen kiosk: {{ target.kioskAd }}</p></div>
    </DefinitionDialog></template>
  </DefinitionPage>
</template>
