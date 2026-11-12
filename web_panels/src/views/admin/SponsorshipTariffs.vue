<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import DefinitionPage from '../../components/shared/DefinitionPage.vue';
import DefinitionDialog from '../../components/shared/DefinitionDialog.vue';
import { listSponsorshipTariffs, createSponsorshipTariff, updateSponsorshipTariff } from '../../services/dooh';
import { humanError } from '../../services/api';

const records = ref([]), loading = ref(false), error = ref(''), search = ref(''), type = ref('');
const open = ref(false), saving = ref(false), formError = ref('');
const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Istanbul' }).format(new Date());
const empty = () => ({ id: null, ad: '', tur: 'BOLGE', min_cihaz: 6, max_cihaz: 15, brut_bedel: '', kdv_orani: 20, gecerlilik_baslangic: today(), gecerlilik_bitis: '', aktif: true });
const form = reactive(empty());
const filtered = computed(() => records.value.filter(row => (!type.value || row.tur === type.value) && row.ad.toLocaleLowerCase('tr').includes(search.value.toLocaleLowerCase('tr'))));
const money = value => Number(value).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
const date = value => value ? value.split('-').reverse().join('.') : 'Süresiz';
async function load() { loading.value = true; error.value = ''; try { const { data } = await listSponsorshipTariffs(); records.value = Array.isArray(data) ? data : data.results || []; } catch (e) { error.value = humanError(e); } finally { loading.value = false; } }
function edit(row = null) { Object.assign(form, empty(), row || {}, { gecerlilik_bitis: row?.gecerlilik_bitis || '' }); formError.value = ''; open.value = true; }
async function save() {
  saving.value = true; formError.value = '';
  const { ad, tur, min_cihaz, max_cihaz, brut_bedel, kdv_orani, gecerlilik_baslangic, gecerlilik_bitis, aktif } = form;
  const payload = { ad, tur, min_cihaz, max_cihaz: max_cihaz || null, brut_bedel, kdv_orani, gecerlilik_baslangic, gecerlilik_bitis: gecerlilik_bitis || null, aktif };
  try { form.id ? await updateSponsorshipTariff(form.id, payload) : await createSponsorshipTariff(payload); open.value = false; toast.success('Tarife kaydedildi.'); await load(); } catch (e) { formError.value = humanError(e); } finally { saving.value = false; }
}
onMounted(load);
</script>

<template>
  <DefinitionPage v-model:search="search" title="Sponsorluk Tarifeleri" description="Sponsorluk paketlerini, cihaz aralıklarını ve geçerlilik tarihlerini yönetin." :count="filtered.length" :loading="loading" :error="error" new-label="Yeni Tarife" @create="edit()" @refresh="load">
    <template #filters><select v-model="type" class="eisa-field eisa-filter" aria-label="Sponsorluk türü"><option value="">Tüm sponsorluk türleri</option><option value="BOLGE">Bölge sponsorluğu</option><option value="ECZANE">Eczane sponsorluğu</option></select></template>
    <div v-if="filtered.length" class="eisa-table-wrap"><table class="eisa-table"><thead><tr><th>Tarife</th><th>Cihaz aralığı</th><th>Bedel</th><th>Geçerlilik</th><th>Durum</th><th>İşlemler</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id"><td><span class="eisa-record-name">{{ row.ad }}</span><span class="eisa-record-detail">{{ row.tur === 'BOLGE' ? 'Bölge sponsorluğu' : 'Eczane sponsorluğu' }}</span></td><td>{{ row.min_cihaz }} – {{ row.max_cihaz || 'Sınırsız' }} cihaz</td><td><span class="eisa-record-name">{{ money(row.brut_bedel) }}</span><span class="eisa-record-detail">KDV %{{ row.kdv_orani }}</span></td><td>{{ date(row.gecerlilik_baslangic) }}<span class="eisa-record-detail">{{ date(row.gecerlilik_bitis) }}</span></td><td><span class="eisa-pill" :class="row.aktif ? 'eisa-pill-success' : 'eisa-pill-muted'">{{ row.aktif ? 'Aktif' : 'Pasif' }}</span></td><td><div class="eisa-table-actions"><button class="eisa-icon-btn" title="Tarifeyi düzenle" aria-label="Tarifeyi düzenle" @click="edit(row)"><i class="fa-solid fa-pen"></i></button></div></td></tr></tbody></table></div>
    <div v-else class="eisa-definition-empty"><i class="fa-solid fa-tags"></i><strong>{{ search || type ? 'Filtreye uygun tarife yok' : 'Henüz tarife tanımlanmadı' }}</strong><span>Kampanya ve sözleşmelerde kullanılacak sponsorluk paketini ekleyin.</span></div>
    <template #dialogs><DefinitionDialog :open="open" :title="form.id ? 'Tarifeyi Düzenle' : 'Yeni Sponsorluk Tarifesi'" :busy="saving" :error="formError" @close="open = false" @save="save">
      <div class="eisa-form-grid">
        <label class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Tarife adı *</span><input v-model.trim="form.ad" class="eisa-field" placeholder="Örn. Bölge Sponsorluğu — 6 ila 15 Cihaz" required maxlength="160" /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">Sponsorluk türü</span><select v-model="form.tur" class="eisa-field"><option value="BOLGE">Bölge sponsorluğu</option><option value="ECZANE">Eczane sponsorluğu</option></select></label>
        <label class="eisa-form-row"><span class="eisa-field-label">KDV dahil tarife bedeli (TL) *</span><input v-model="form.brut_bedel" class="eisa-field" type="number" min="0" step="0.01" required /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">En az cihaz</span><input v-model.number="form.min_cihaz" class="eisa-field" type="number" min="1" required /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">En fazla cihaz</span><input v-model.number="form.max_cihaz" class="eisa-field" type="number" :min="form.min_cihaz" placeholder="Sınır yoksa boş bırakın" /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">Başlangıç tarihi *</span><input v-model="form.gecerlilik_baslangic" class="eisa-field" type="date" required /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">Bitiş tarihi</span><input v-model="form.gecerlilik_bitis" class="eisa-field" type="date" :min="form.gecerlilik_baslangic" /></label>
        <label class="eisa-form-row"><span class="eisa-field-label">KDV oranı</span><select v-model.number="form.kdv_orani" class="eisa-field"><option v-for="rate in [0, 1, 10, 20]" :key="rate" :value="rate">%{{ rate }}</option></select></label>
      </div><div class="eisa-form-section"><label class="eisa-toggle"><input v-model="form.aktif" type="checkbox" />Tarife aktif</label><span class="eisa-form-note">Eczane katkı payı cihaz aralığına eşit bölünmez; o dönemdeki uygun aktif cihaz-günlere göre hesaplanır.</span></div>
    </DefinitionDialog></template>
  </DefinitionPage>
</template>
