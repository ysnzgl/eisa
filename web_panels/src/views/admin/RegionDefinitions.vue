<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import DefinitionPage from '../../components/shared/DefinitionPage.vue';
import DefinitionDialog from '../../components/shared/DefinitionDialog.vue';
import { listSponsorshipRegions, createSponsorshipRegion, updateSponsorshipRegion } from '../../services/dooh';
import { getIller, getIlceler } from '../../services/lookups';
import { humanError } from '../../services/api';

const records = ref([]), provinces = ref([]), districts = ref([]);
const loading = ref(false), error = ref(''), search = ref(''), open = ref(false), saving = ref(false), formError = ref('');
const form = reactive({ id: null, ad: '', aktif: true, kapsamlar: [] });
const scope = reactive({ il: '', ilce: '' });
const filtered = computed(() => records.value.filter(row => `${row.ad} ${row.kapsamlar.map(x => `${x.il_adi} ${x.ilce_adi || ''}`).join(' ')}`.toLocaleLowerCase('tr').includes(search.value.toLocaleLowerCase('tr'))));
async function load() { loading.value = true; error.value = ''; try { const { data } = await listSponsorshipRegions(); records.value = Array.isArray(data) ? data : data.results || []; } catch (e) { error.value = humanError(e); } finally { loading.value = false; } }
function edit(row = null) { Object.assign(form, { id: row?.id || null, ad: row?.ad || '', aktif: row?.aktif ?? true, kapsamlar: (row?.kapsamlar || []).map(x => ({ ...x })) }); scope.il = ''; scope.ilce = ''; districts.value = []; formError.value = ''; open.value = true; }
async function provinceChanged() { scope.ilce = ''; districts.value = []; if (scope.il) { try { districts.value = await getIlceler(scope.il); } catch (e) { formError.value = humanError(e); } } }
function addScope() {
  if (!scope.il) { formError.value = 'Önce il seçin.'; return; }
  const province = provinces.value.find(x => String(x.id) === String(scope.il));
  const district = districts.value.find(x => String(x.id) === String(scope.ilce));
  if (form.kapsamlar.some(x => x.il === Number(scope.il) && (!x.ilce || !scope.ilce || x.ilce === Number(scope.ilce)))) { formError.value = 'Bu il veya ilçe zaten kapsama eklenmiş.'; return; }
  form.kapsamlar.push({ il: Number(scope.il), ilce: scope.ilce ? Number(scope.ilce) : null, il_adi: province.ad, ilce_adi: district?.ad || '' }); formError.value = '';
}
async function save() {
  if (!form.ad.trim() || !form.kapsamlar.length) { formError.value = 'Bölge adı ve en az bir il/ilçe kapsamı gerekli.'; return; }
  saving.value = true; formError.value = '';
  const payload = { ad: form.ad.trim(), aktif: form.aktif, kapsamlar: form.kapsamlar.map(({ il, ilce }) => ({ il, ilce })) };
  try { form.id ? await updateSponsorshipRegion(form.id, payload) : await createSponsorshipRegion(payload); open.value = false; toast.success('Bölge kaydedildi.'); await load(); } catch (e) { formError.value = humanError(e); } finally { saving.value = false; }
}
onMounted(async () => { await load(); try { provinces.value = await getIller(); } catch (e) { error.value = humanError(e); } });
</script>

<template>
  <DefinitionPage v-model:search="search" title="Bölge Tanımları" description="İl ve ilçeleri bir bölge adı altında bir araya getirin." :count="filtered.length" :loading="loading" :error="error" new-label="Yeni Bölge" @create="edit()" @refresh="load">
    <div v-if="filtered.length" class="eisa-table-wrap"><table class="eisa-table"><thead><tr><th>Bölge adı</th><th>İl / İlçe kapsamı</th><th>Durum</th><th>İşlemler</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id"><td><span class="eisa-record-name">{{ row.ad }}</span></td><td><span v-for="item in row.kapsamlar" :key="`${item.il}-${item.ilce}`" class="eisa-record-detail">{{ item.il_adi }} / {{ item.ilce_adi || 'Tüm ilçeler' }}</span></td><td><span class="eisa-pill" :class="row.aktif ? 'eisa-pill-success' : 'eisa-pill-muted'">{{ row.aktif ? 'Aktif' : 'Pasif' }}</span></td><td><div class="eisa-table-actions"><button class="eisa-icon-btn" title="Bölgeyi düzenle" aria-label="Bölgeyi düzenle" @click="edit(row)"><i class="fa-solid fa-pen"></i></button></div></td></tr></tbody></table></div>
    <div v-else class="eisa-definition-empty"><i class="fa-solid fa-map-location-dot"></i><strong>{{ search ? 'Aramanıza uygun bölge yok' : 'Henüz bölge tanımlanmadı' }}</strong><span>İlk bölgeyi adı ve kapsadığı il / ilçelerle oluşturun.</span></div>
    <template #dialogs>
      <DefinitionDialog :open="open" :title="form.id ? 'Bölgeyi Düzenle' : 'Yeni Bölge'" :busy="saving" :error="formError" @close="open = false" @save="save">
        <label class="eisa-form-row"><span class="eisa-field-label">Bölge adı *</span><input v-model.trim="form.ad" class="eisa-field" placeholder="Örn. Kayseri Merkez" required maxlength="128" autofocus /></label>
        <section class="eisa-form-section"><h3 class="eisa-form-section-title">Bölgenin kapsadığı yerler</h3><div class="eisa-scope-picker">
          <label><span class="eisa-field-label">İl</span><select v-model="scope.il" class="eisa-field" aria-label="İl" @change="provinceChanged"><option value="">İl seçin</option><option v-for="province in provinces" :key="province.id" :value="province.id">{{ province.ad }}</option></select></label>
          <label><span class="eisa-field-label">İlçe</span><select v-model="scope.ilce" class="eisa-field" aria-label="İlçe" :disabled="!scope.il"><option value="">Tüm ilçeler</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.ad }}</option></select></label>
          <button type="button" class="eisa-btn eisa-btn-ghost" @click="addScope"><i class="fa-solid fa-plus"></i>Ekle</button>
        </div><div class="eisa-scope-tags"><span v-for="(item, index) in form.kapsamlar" :key="`${item.il}-${item.ilce}`" class="eisa-scope-tag">{{ item.il_adi }} / {{ item.ilce_adi || 'Tüm ilçeler' }}<button type="button" :aria-label="`${item.il_adi} kapsamını kaldır`" @click="form.kapsamlar.splice(index, 1)"><i class="fa-solid fa-xmark"></i></button></span></div><span class="eisa-form-note">İlçe seçmeden eklerseniz ilin tüm ilçeleri bu bölgeye dahil edilir.</span></section>
        <div class="eisa-form-section"><label class="eisa-toggle"><input v-model="form.aktif" type="checkbox" />Bölge aktif</label></div>
      </DefinitionDialog>
    </template>
  </DefinitionPage>
</template>
