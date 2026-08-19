<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { http } from '../../services/api';

const items = ref([]);
const provinces = ref([]);
const districts = ref([]);
const pharmacies = ref([]);
const selected = ref(null);
const formOpen = ref(false);
const districtProvince = ref('');
const loading = ref(true);
const saving = ref(false);

const emptyGeneral = () => ({
  title: '', message: '', action_label: '', severity: 'INFO', active: true,
  recurrence: 'ONCE', start_date: new Date().toISOString().slice(0, 10), end_date: null,
  weekdays: [], monthly_mode: 'SPECIFIC_DAY', monthly_day_start: 1,
  monthly_day_end: null, monthly_day_count: null, target_scope: 'ALL',
  target_province: null, target_district: null, target_pharmacy: null,
});
const form = reactive(emptyGeneral());
const isSystem = computed(() => selected.value?.kind === 'SYSTEM');
const systemItems = computed(() => items.value.filter((item) => item.kind === 'SYSTEM'));
const generalItems = computed(() => items.value.filter((item) => item.kind === 'GENERAL'));
const weekdayLabels = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
const recurrenceLabels = { ONCE: 'Tek seferlik', DAILY: 'Günlük', WEEKLY: 'Haftalık', MONTHLY: 'Aylık' };

async function load() {
  loading.value = true;
  try {
    const [{ data: announcements }, { data: provinceData }, { data: pharmacyData }] = await Promise.all([
      http.get('/api/announcements/admin/'), http.get('/api/lookups/iller/'), http.get('/api/pharmacies/'),
    ]);
    items.value = Array.isArray(announcements) ? announcements : announcements.results || [];
    provinces.value = provinceData;
    pharmacies.value = Array.isArray(pharmacyData) ? pharmacyData : pharmacyData.results || [];
  } finally { loading.value = false; }
}

function resetForm() {
  selected.value = null;
  districtProvince.value = '';
  districts.value = [];
  Object.assign(form, emptyGeneral());
}
function newGeneral() { resetForm(); formOpen.value = true; }
function closeForm() { formOpen.value = false; resetForm(); }

async function edit(item) {
  selected.value = item;
  Object.assign(form, emptyGeneral(), item);
  districtProvince.value = item.target_district
    ? String(pharmacies.value.find((pharmacy) => pharmacy.ilce === item.target_district)?.il || '') : '';
  if (districtProvince.value) await loadDistricts();
  formOpen.value = true;
}
async function loadDistricts() {
  if (!districtProvince.value) { districts.value = []; return; }
  const { data } = await http.get('/api/lookups/ilceler/', { params: { il: districtProvince.value } });
  districts.value = data;
}
watch(districtProvince, loadDistricts);

function toggleWeekday(day) {
  const days = new Set(form.weekdays);
  days.has(day) ? days.delete(day) : days.add(day);
  form.weekdays = [...days].sort();
}
function generalPayload() {
  const payload = { ...form };
  ['id', 'kind', 'system_key', 'target_label', 'olusturulma_tarihi', 'guncellenme_tarihi', 'surum'].forEach((key) => delete payload[key]);
  payload.target_province = form.target_scope === 'PROVINCE' ? form.target_province : null;
  payload.target_district = form.target_scope === 'DISTRICT' ? form.target_district : null;
  payload.target_pharmacy = form.target_scope === 'PHARMACY' ? form.target_pharmacy : null;
  payload.end_date ||= null;
  if (form.recurrence !== 'WEEKLY') payload.weekdays = [];
  if (form.recurrence !== 'MONTHLY') {
    payload.monthly_mode = ''; payload.monthly_day_start = null;
    payload.monthly_day_end = null; payload.monthly_day_count = null;
  }
  return payload;
}
async function save() {
  saving.value = true;
  try {
    if (isSystem.value) {
      await http.patch(`/api/announcements/admin/${selected.value.id}/`, {
        title: form.title, message: form.message, action_label: form.action_label,
        severity: form.severity, active: form.active,
      });
    } else if (selected.value) {
      await http.patch(`/api/announcements/admin/${selected.value.id}/`, generalPayload());
    } else {
      await http.post('/api/announcements/admin/', generalPayload());
    }
    toast.success('Duyuru kaydedildi.');
    await load();
    closeForm();
  } catch (error) {
    toast.error(error?.response?.data?.detail || 'Duyuru kaydedilemedi.');
  } finally { saving.value = false; }
}
async function remove(item) {
  if (!confirm(`“${item.title}” duyurusu silinsin mi?`)) return;
  await http.delete(`/api/announcements/admin/${item.id}/`);
  toast.success('Duyuru silindi.');
  await load();
}
onMounted(load);
</script>

<template>
  <div class="eisa-page announcement-admin">
    <div class="eisa-page-header">
      <div><p class="eisa-eyebrow">YÖNETİCİ / İLETİŞİM</p><h1 class="eisa-page-title">Duyuru Yönetimi</h1><p class="eisa-page-subtitle">Genel duyuruları zamanlayın; sabit nöbet uyarılarının yalnızca içeriğini yönetin.</p></div>
      <button class="eisa-btn eisa-btn-cta" @click="newGeneral"><i class="fa-solid fa-plus"></i> Yeni Duyuru</button>
    </div>

    <div v-if="loading" class="loading"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
    <template v-else>
      <section class="eisa-panel system-section">
        <div class="section-head"><div><h2>Sistem Nöbet Uyarıları</h2><p>Koşul, tarih, hedef ay ve aksiyon sunucu tarafında sabit yönetilir.</p></div><span class="lock-badge"><i class="fa-solid fa-lock"></i> Korumalı</span></div>
        <div class="system-grid">
          <button v-for="item in systemItems" :key="item.id" class="system-card" :class="{ inactive: !item.active }" @click="edit(item)">
            <span class="eisa-pill eisa-pill-info">Sistem Duyurusu</span><strong>{{ item.title }}</strong><span>{{ item.active ? 'Aktif' : 'Pasif' }} · Düzenle</span>
          </button>
        </div>
      </section>

      <section class="eisa-panel list-panel">
        <div class="section-head"><div><h2>Genel Duyurular</h2><p>Herhangi bir sistem koşulundan bağımsızdır.</p></div><span>{{ generalItems.length }} kayıt</span></div>
        <div v-if="!generalItems.length" class="empty-list">Henüz genel duyuru yok.</div>
        <article v-for="item in generalItems" :key="item.id" class="list-item" :class="{ inactive: !item.active }">
          <div><div class="list-meta"><span>{{ recurrenceLabels[item.recurrence] }}</span><span>{{ item.target_label }}</span><span>{{ item.active ? 'Aktif' : 'Pasif' }}</span></div><h3>{{ item.title }}</h3><p>{{ item.start_date }}<template v-if="item.end_date"> – {{ item.end_date }}</template></p></div>
          <div class="row-actions"><button title="Düzenle" @click="edit(item)"><i class="fa-solid fa-pen"></i></button><button class="danger" title="Sil" @click="remove(item)"><i class="fa-solid fa-trash"></i></button></div>
        </article>
      </section>
    </template>

    <Teleport to="body">
      <div v-if="formOpen" class="eisa-modal-backdrop" @click.self="closeForm">
        <div class="eisa-modal announcement-editor-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div><h3 class="eisa-modal-title">{{ isSystem ? 'Sistem Duyurusunu Düzenle' : selected ? 'Genel Duyuruyu Düzenle' : 'Yeni Genel Duyuru' }}</h3><p v-if="isSystem" class="modal-subtitle">Yalnızca kullanıcıya gösterilen alanlar değiştirilebilir.</p></div>
            <button class="eisa-modal-close" title="Kapat" @click="closeForm"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <form @submit.prevent="save">
            <div class="eisa-modal-body announcement-form">
              <div v-if="isSystem" class="protected-note"><i class="fa-solid fa-shield-halved"></i><div><strong>Sistem Duyurusu</strong><p>Çalışma tarihleri, hedef ay, koşul ve açılacak ekran sistem tarafından yönetilir.</p></div></div>
              <label><span class="eisa-field-label">Başlık</span><input v-model="form.title" required maxlength="200" class="eisa-field"></label>
              <label><span class="eisa-field-label">Mesaj</span><textarea v-model="form.message" required rows="4" class="eisa-field"></textarea></label>
              <div class="form-row"><label><span class="eisa-field-label">Görsel tür / seviye</span><select v-model="form.severity" class="eisa-field"><option value="INFO">Bilgilendirme</option><option value="WARNING">Uyarı</option><option value="ACTION_REQUIRED">İşlem gerekli</option></select></label><label class="check-label"><input v-model="form.active" type="checkbox"> Aktif</label></div>
              <label v-if="isSystem"><span class="eisa-field-label">Aksiyon butonu yazısı</span><input v-model="form.action_label" maxlength="80" class="eisa-field"></label>

              <template v-if="!isSystem">
                <div class="form-divider">Zamanlama</div>
                <div class="form-row"><label><span class="eisa-field-label">Tekrar</span><select v-model="form.recurrence" class="eisa-field"><option value="ONCE">Tek seferlik</option><option value="DAILY">Günlük</option><option value="WEEKLY">Haftalık</option><option value="MONTHLY">Aylık</option></select></label><label><span class="eisa-field-label">Başlangıç</span><input v-model="form.start_date" required type="date" class="eisa-field"></label><label><span class="eisa-field-label">Bitiş (opsiyonel)</span><input v-model="form.end_date" type="date" class="eisa-field"></label></div>
                <div v-if="form.recurrence === 'WEEKLY'" class="weekday-picker"><button v-for="(day, i) in weekdayLabels" :key="day" type="button" :class="{ selected: form.weekdays.includes(i) }" @click="toggleWeekday(i)">{{ day }}</button></div>
                <div v-if="form.recurrence === 'MONTHLY'" class="monthly-box">
                  <label><span class="eisa-field-label">Aylık seçenek</span><select v-model="form.monthly_mode" class="eisa-field"><option value="SPECIFIC_DAY">Ayın belirli günü</option><option value="DAY_RANGE">Belirli gün aralığı</option><option value="FIRST_N_DAYS">İlk N günü</option><option value="LAST_N_DAYS">Son N günü</option><option value="LAST_WEEK">Son haftası (son 7 gün)</option></select></label>
                  <label v-if="['SPECIFIC_DAY','DAY_RANGE'].includes(form.monthly_mode)"><span class="eisa-field-label">{{ form.monthly_mode === 'DAY_RANGE' ? 'Başlangıç günü' : 'Ayın günü' }}</span><input v-model.number="form.monthly_day_start" type="number" min="1" max="31" class="eisa-field"></label>
                  <label v-if="form.monthly_mode === 'DAY_RANGE'"><span class="eisa-field-label">Bitiş günü</span><input v-model.number="form.monthly_day_end" type="number" min="1" max="31" class="eisa-field"></label>
                  <label v-if="['FIRST_N_DAYS','LAST_N_DAYS'].includes(form.monthly_mode)"><span class="eisa-field-label">Gün sayısı</span><input v-model.number="form.monthly_day_count" type="number" min="1" max="31" class="eisa-field"></label>
                </div>
                <div class="form-divider">Hedefleme</div>
                <label><span class="eisa-field-label">Hedef kapsamı</span><select v-model="form.target_scope" class="eisa-field"><option value="ALL">Tüm eczaneler</option><option value="PROVINCE">İl</option><option value="DISTRICT">İlçe</option><option value="PHARMACY">Eczane</option></select></label>
                <label v-if="form.target_scope === 'PROVINCE'"><span class="eisa-field-label">İl</span><select v-model="form.target_province" required class="eisa-field"><option :value="null" disabled>Seçin</option><option v-for="item in provinces" :key="item.id" :value="item.id">{{ item.ad }}</option></select></label>
                <template v-if="form.target_scope === 'DISTRICT'"><label><span class="eisa-field-label">İl (ilçeleri filtreler)</span><select v-model="districtProvince" required class="eisa-field"><option value="" disabled>Seçin</option><option v-for="item in provinces" :key="item.id" :value="String(item.id)">{{ item.ad }}</option></select></label><label><span class="eisa-field-label">İlçe</span><select v-model="form.target_district" required class="eisa-field"><option :value="null" disabled>Seçin</option><option v-for="item in districts" :key="item.id" :value="item.id">{{ item.ad }}</option></select></label></template>
                <label v-if="form.target_scope === 'PHARMACY'"><span class="eisa-field-label">Eczane</span><select v-model="form.target_pharmacy" required class="eisa-field"><option :value="null" disabled>Seçin</option><option v-for="item in pharmacies" :key="item.id" :value="item.id">{{ item.ad }} · {{ item.ilce_adi }}/{{ item.il_adi }}</option></select></label>
              </template>
            </div>
            <div class="eisa-modal-footer"><button type="button" class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="closeForm">İptal</button><button class="eisa-btn eisa-btn-cta" :disabled="saving"><i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i> {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}</button></div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.loading{padding:4rem;text-align:center}.system-section,.list-panel{padding:1.2rem;margin-bottom:1rem}.section-head{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:1rem}.section-head h2{font-size:1rem}.section-head p,.modal-subtitle{font-size:.78rem;color:#6b7280;margin-top:.2rem}.lock-badge{font-size:.68rem;font-weight:750;color:#4338ca;background:#eef2ff;border:1px solid #c7d2fe;border-radius:99px;padding:.3rem .55rem}.system-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.7rem}.system-card{border:1px solid #e5e7eb;background:#fff;border-radius:10px;padding:1rem;text-align:left;cursor:pointer;display:flex;flex-direction:column;align-items:flex-start;gap:.5rem}.system-card:hover{border-color:#4338ca;box-shadow:0 4px 12px rgba(67,56,202,.08)}.system-card>span:last-child{font-size:.75rem;color:#6b7280}.inactive{opacity:.58}.empty-list{padding:2rem;text-align:center;color:#6b7280}.list-item{display:flex;justify-content:space-between;gap:.7rem;padding:.9rem 0;border-top:1px solid #f1f5f9}.list-item h3{font-size:.9rem;margin:.35rem 0}.list-item p,.list-meta{font-size:.7rem;color:#6b7280}.list-meta{display:flex;flex-wrap:wrap;gap:.45rem}.list-meta span{background:#f1f5f9;padding:.2rem .4rem;border-radius:5px}.row-actions{display:flex;gap:.3rem}.row-actions button{border:0;background:#f1f5f9;width:32px;height:32px;border-radius:7px;cursor:pointer}.row-actions .danger{color:#dc2626}.announcement-editor-modal{width:min(820px,calc(100vw - 2rem));max-height:calc(100vh - 2rem);overflow:auto}.protected-note{display:flex;gap:.7rem;padding:.8rem;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px}.protected-note p{font-size:.75rem;margin-top:.2rem}.announcement-form{display:flex;flex-direction:column;gap:.85rem}.announcement-form label{display:flex;flex-direction:column;gap:.3rem;flex:1}.announcement-form textarea{resize:vertical}.form-row,.monthly-box{display:flex;gap:.7rem;align-items:end}.check-label{flex:0 0 auto!important;flex-direction:row!important;align-items:center;padding:.55rem}.form-divider{font-size:.72rem;font-weight:800;color:#b1121b;text-transform:uppercase;border-bottom:1px solid #fee2e2;padding-bottom:.35rem;margin-top:.35rem}.weekday-picker{display:flex;gap:.35rem}.weekday-picker button{border:1px solid #d1d5db;background:#fff;border-radius:7px;padding:.45rem .6rem;cursor:pointer}.weekday-picker button.selected{background:#b1121b;color:#fff;border-color:#b1121b}@media(max-width:650px){.system-grid{grid-template-columns:1fr}.form-row,.monthly-box{flex-direction:column;align-items:stretch}}
</style>
