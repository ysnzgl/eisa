<script setup>
/**
 * Barkod Logo Yönetimi — Admin CRUD
 * DOOH kampanya sisteminden bağımsızdır.
 * Kiosk fiş baskısında e-ISA başlığının yerini alacak logoları yönetir.
 */
import { ref, reactive, onMounted, computed, watch } from 'vue';
import { http } from '../../services/api';
import { getIller, getIlceler } from '../../services/lookups';
import { toast } from 'vue-sonner';
import EisaLookup from '../../components/shared/EisaLookup.vue';

const LOGO_URL    = '/api/barkod-logo/logolar/';
const UPLOAD_URL  = '/api/barkod-logo/upload-gorsel/';

const logolar      = ref([]);
const loading      = ref(false);
const saving       = ref(false);
const formOpen     = ref(false);
const editingId    = ref(null);

// Kiosk / il / ilçe verileri
const kiosklar      = ref([]);   // raw API: {id, ad, eczane_adi, il_id, il_adi, ilce_id, ilce_adi}
const iller         = ref([]);
const ilceler       = ref([]);
const illerLoading  = ref(false);
const ilcelerLoading = ref(false);

// Tek-seçim picker'lar — seçilince listeye eklenir, sonra null'a döner
const pickedIlId    = ref(null);
const pickedIlceId  = ref(null);
const pickedKioskId = ref(null);

const today = () => new Date().toISOString().slice(0, 10);
const oneMonthLater = (from) => {
  const d = new Date(from);
  d.setMonth(d.getMonth() + 1);
  return d.toISOString().slice(0, 10);
};

const empty = () => {
  const bas = today();
  return {
    ad: '',
    media_url: '',
    object_key: '',
    checksum: '',
    baslangic_zamani: bas + 'T00:00',
    bitis_zamani: oneMonthLater(bas) + 'T00:00',
    aktif: true,
    gunluk_baski_limiti: '',
    hedef_kiosk_idleri_write: [],
  };
};

const form = reactive(empty());
const previewUrl   = ref('');
const uploadFile   = ref(null);
const uploadError  = ref('');
const bitisElleGirildi = ref(false);

// Seçili kioskların tam nesneleri (chip gösterimi için)
const selectedKioskObjects = computed(() =>
  form.hedef_kiosk_idleri_write
    .map((id) => kiosklar.value.find((k) => k.id === id))
    .filter(Boolean),
);

// EisaLookup seçenekleri
const kioskOptions = computed(() =>
  kiosklar.value.map((k) => ({
    id: k.id,
    label: k.ad,
    sub: [k.il_adi, k.ilce_adi, k.eczane_adi].filter(Boolean).join(' / '),
  })),
);

// ── Veri yükleme ──────────────────────────────────────────────────────────────

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get(LOGO_URL);
    logolar.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Logolar yüklenemedi.');
  } finally { loading.value = false; }
}

async function loadKiosklar() {
  if (kiosklar.value.length) return;
  try {
    const { data } = await http.get('/api/pharmacies/kiosks/');
    kiosklar.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch {
    toast.error('Kiosklar yüklenemedi.');
  }
}

async function loadIller() {
  if (iller.value.length) return;
  illerLoading.value = true;
  try {
    const data = await getIller();
    iller.value = (Array.isArray(data) ? data : []).map((il) => ({ id: il.id, label: il.ad }));
  } catch { toast.error('İl listesi yüklenemedi.'); }
  finally { illerLoading.value = false; }
}

async function refreshIlceler() {
  if (!iller.value.length) return;
  ilcelerLoading.value = true;
  try {
    const results = await Promise.all(iller.value.map((il) => getIlceler(il.id)));
    ilceler.value = results.flat().map((ilce) => ({
      id: ilce.id,
      label: ilce.ad,
      sub: iller.value.find((il) => il.id === ilce.il_id)?.label ?? '',
    }));
  } catch { toast.error('İlçe listesi yüklenemedi.'); }
  finally { ilcelerLoading.value = false; }
}

onMounted(async () => {
  await Promise.all([load(), loadKiosklar(), loadIller()]);
  refreshIlceler();
});

// ── EisaLookup picker izleyiciler ────────────────────────────────────────────

// İl seçilince o ildeki tüm kioskları ekle
watch(pickedIlId, (ilId) => {
  if (!ilId) return;
  const matched = kiosklar.value.filter((k) => k.il_id === ilId);
  for (const k of matched) {
    if (!form.hedef_kiosk_idleri_write.includes(k.id))
      form.hedef_kiosk_idleri_write.push(k.id);
  }
  if (!matched.length) toast.info('Bu ile ait kiosk bulunamadı.');
  pickedIlId.value = null;
});

// İlçe seçilince o ilçedeki tüm kioskları ekle
watch(pickedIlceId, (ilceId) => {
  if (!ilceId) return;
  const matched = kiosklar.value.filter((k) => k.ilce_id === ilceId);
  for (const k of matched) {
    if (!form.hedef_kiosk_idleri_write.includes(k.id))
      form.hedef_kiosk_idleri_write.push(k.id);
  }
  if (!matched.length) toast.info('Bu ilçeye ait kiosk bulunamadı.');
  pickedIlceId.value = null;
});

// Kiosk doğrudan seçimi
watch(pickedKioskId, (kioskId) => {
  if (!kioskId) return;
  if (!form.hedef_kiosk_idleri_write.includes(kioskId))
    form.hedef_kiosk_idleri_write.push(kioskId);
  pickedKioskId.value = null;
});

// ── Form açma/kapama ────────────────────────────────────────────────────────

function openCreate() {
  Object.assign(form, empty());
  previewUrl.value = '';
  uploadFile.value = null;
  uploadError.value = '';
  bitisElleGirildi.value = false;
  pickedIlId.value = null; pickedIlceId.value = null; pickedKioskId.value = null;
  editingId.value = null;
  formOpen.value = true;
}

function openEdit(logo) {
  Object.assign(form, {
    ad: logo.ad,
    media_url: logo.media_url,
    object_key: logo.object_key || '',
    checksum: logo.checksum || '',
    baslangic_zamani: logo.baslangic_zamani?.slice(0, 16) ?? '',
    bitis_zamani: logo.bitis_zamani?.slice(0, 16) ?? '',
    aktif: logo.aktif,
    gunluk_baski_limiti: logo.gunluk_baski_limiti ?? '',
    hedef_kiosk_idleri_write: (logo.hedef_kiosk_idleri ?? []).map((k) => (typeof k === 'object' ? k.id : k)),
  });
  previewUrl.value = logo.media_url || '';
  uploadFile.value = null;
  uploadError.value = '';
  bitisElleGirildi.value = true;
  pickedIlId.value = null; pickedIlceId.value = null; pickedKioskId.value = null;
  editingId.value = logo.id;
  formOpen.value = true;
}

function closeForm() {
  formOpen.value = false;
  editingId.value = null;
}

function removeKiosk(kioskId) {
  const idx = form.hedef_kiosk_idleri_write.indexOf(kioskId);
  if (idx !== -1) form.hedef_kiosk_idleri_write.splice(idx, 1);
}

// ── Tarih kuralları ───────────────────────────────────────────────────────────

watch(() => form.baslangic_zamani, (newVal) => {
  if (!bitisElleGirildi.value && newVal) {
    form.bitis_zamani = oneMonthLater(newVal.slice(0, 10)) + 'T00:00';
  }
});

function onBitisInput() { bitisElleGirildi.value = true; }

// ── Görsel yükleme ────────────────────────────────────────────────────────────

async function onFileChange(event) {
  const file = event.target.files[0];
  if (!file) return;
  uploadError.value = '';
  if (file.type !== 'image/png') { uploadError.value = 'Yalnızca PNG formatı kabul edilir.'; return; }
  if (file.size > 1 * 1024 * 1024) { uploadError.value = 'Dosya boyutu 1 MB\'ı aşamaz.'; return; }
  await new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      if (img.width > 336 || img.height > 336)
        uploadError.value = `Görsel en fazla 336×336 px olabilir (yüklenen: ${img.width}×${img.height}).`;
      resolve();
    };
    img.onerror = resolve;
    img.src = URL.createObjectURL(file);
  });
  if (uploadError.value) return;
  uploadFile.value = file;
  previewUrl.value = URL.createObjectURL(file);
}

// ── Kaydet ────────────────────────────────────────────────────────────────────

async function save() {
  saving.value = true;
  try {
    if (uploadFile.value) {
      const fd = new FormData();
      fd.append('file', uploadFile.value);
      const { data: up } = await http.post(UPLOAD_URL, fd);
      form.media_url = up.media_url;
      form.object_key = up.object_key;
      form.checksum   = up.checksum;
    }
    const body = {
      ad: form.ad,
      media_url: form.media_url,
      object_key: form.object_key,
      checksum: form.checksum,
      baslangic_zamani: form.baslangic_zamani ? new Date(form.baslangic_zamani).toISOString() : '',
      bitis_zamani: form.bitis_zamani ? new Date(form.bitis_zamani).toISOString() : '',
      aktif: form.aktif,
      gunluk_baski_limiti: form.gunluk_baski_limiti === '' ? null : Number(form.gunluk_baski_limiti),
      hedef_kiosk_idleri_write: form.hedef_kiosk_idleri_write,
    };
    if (editingId.value) {
      await http.patch(`${LOGO_URL}${editingId.value}/`, body);
      toast.success('Logo güncellendi.');
    } else {
      await http.post(LOGO_URL, body);
      toast.success('Logo oluşturuldu.');
    }
    await load();
    closeForm();
  } catch (e) {
    toast.error(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || 'Kayıt başarısız.');
  } finally { saving.value = false; }
}

// ── Aktif/Pasif toggle ────────────────────────────────────────────────────────

async function toggleAktif(logo) {
  try {
    await http.patch(`${LOGO_URL}${logo.id}/`, { aktif: !logo.aktif });
    await load();
    toast.success(logo.aktif ? 'Logo pasifleştirildi.' : 'Logo aktifleştirildi.');
  } catch {
    toast.error('Durum değiştirilemedi.');
  }
}

function kioskHedefOzeti(logo) {
  const sayı = (logo.hedef_kiosk_idleri ?? []).length;
  return sayı === 0 ? 'Tüm kiosklar' : `${sayı} kiosk`;
}
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <h1>Barkod Logo Yönetimi</h1>
      <button class="btn btn-primary" @click="openCreate">
        <i class="fa-solid fa-plus"></i> Yeni Logo
      </button>
    </div>

    <div v-if="loading" class="loading-msg">Yükleniyor…</div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Ad</th>
          <th>Görsel</th>
          <th>Başlangıç</th>
          <th>Bitiş</th>
          <th>Limit</th>
          <th>Kiosklar</th>
          <th>Durum</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!logolar.length">
          <td colspan="8" class="empty-row">Henüz logo eklenmedi.</td>
        </tr>
        <tr v-for="logo in logolar" :key="logo.id">
          <td>{{ logo.ad }}</td>
          <td>
            <img v-if="logo.media_url" :src="logo.media_url" alt="logo önizleme"
              class="thumb" @error="e => e.target.style.display='none'" />
            <span v-else class="no-img">—</span>
          </td>
          <td>{{ logo.baslangic_zamani?.slice(0,10) }}</td>
          <td>{{ logo.bitis_zamani?.slice(0,10) }}</td>
          <td>{{ logo.gunluk_baski_limiti ?? 'Sınırsız' }}</td>
          <td>{{ kioskHedefOzeti(logo) }}</td>
          <td>
            <span :class="['badge', logo.aktif ? 'badge-active' : 'badge-passive']">
              {{ logo.aktif ? 'Aktif' : 'Pasif' }}
            </span>
          </td>
          <td class="actions">
            <button class="btn btn-sm btn-secondary" @click="openEdit(logo)">Düzenle</button>
            <button class="btn btn-sm" :class="logo.aktif ? 'btn-warning' : 'btn-success'"
              @click="toggleAktif(logo)">
              {{ logo.aktif ? 'Pasifleştir' : 'Aktifleştir' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Form modal -->
    <div v-if="formOpen" class="modal-overlay" @click.self="closeForm">
      <div class="modal-box">
        <h2>{{ editingId ? 'Logo Düzenle' : 'Yeni Logo' }}</h2>

        <div class="form-group">
          <label>Ad *</label>
          <input v-model="form.ad" type="text" class="form-control" placeholder="Logo adı" />
        </div>

        <div class="form-group">
          <label>PNG Görsel (max 336×336 px, ≤ 1 MB)</label>
          <input type="file" accept="image/png" @change="onFileChange" class="form-control" />
          <p v-if="uploadError" class="field-error">{{ uploadError }}</p>
          <img v-if="previewUrl" :src="previewUrl" alt="Önizleme" class="preview" />
          <div class="print-warning">
            <i class="fa-solid fa-triangle-exclamation"></i>
            İnce çizgiler, düşük kontrast ve küçük yazılar termal baskıda iyi sonuç vermeyebilir.
            Siyah-beyaz veya yüksek kontrastlı görsel kullanın.
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Başlangıç Tarihi *</label>
            <input v-model="form.baslangic_zamani" type="datetime-local" class="form-control" />
          </div>
          <div class="form-group">
            <label>Bitiş Tarihi *</label>
            <input v-model="form.bitis_zamani" type="datetime-local" class="form-control"
              @input="onBitisInput" />
          </div>
        </div>

        <div class="form-group">
          <label>Günlük Baskı Limiti (kiosk başına)</label>
          <input v-model="form.gunluk_baski_limiti" type="number" min="1" step="1"
            class="form-control" placeholder="Boş = sınırsız" />
          <p class="field-hint">
            Her bir kioskta, bir takvim günü içinde yapılabilecek en fazla baskı sayısıdır.
            Boş bırakılırsa sınırsızdır.
          </p>
        </div>

        <div class="form-group">
          <label>Aktif</label>
          <label class="toggle">
            <input type="checkbox" v-model="form.aktif" />
            <span class="toggle-label">{{ form.aktif ? 'Aktif' : 'Pasif' }}</span>
          </label>
        </div>

        <div class="form-group">
          <label>Hedef Kiosklar</label>

          <!-- İl filtresi -->
          <div class="target-row">
            <span class="target-label">İle göre ekle</span>
            <EisaLookup
              v-model="pickedIlId"
              :options="iller"
              :loading="illerLoading"
              placeholder="İl seç — o ildeki tüm kiosklar eklenir"
            />
          </div>

          <!-- İlçe filtresi -->
          <div class="target-row">
            <span class="target-label">İlçeye göre ekle</span>
            <EisaLookup
              v-model="pickedIlceId"
              :options="ilceler"
              :loading="ilcelerLoading"
              placeholder="İlçe seç — o ilçedeki tüm kiosklar eklenir"
            />
          </div>

          <!-- Tekil kiosk seçimi -->
          <div class="target-row">
            <span class="target-label">Kiosk ekle</span>
            <EisaLookup
              v-model="pickedKioskId"
              :options="kioskOptions"
              placeholder="Kiosk adı veya yer ara…"
            />
          </div>

          <!-- Seçili kiosklar (chip listesi) -->
          <div v-if="selectedKioskObjects.length" class="chip-list">
            <span v-for="k in selectedKioskObjects" :key="k.id" class="chip chip--kiosk">
              <i class="fa-solid fa-display"></i>
              {{ k.ad }}
              <span v-if="k.il_adi" class="chip-sub">, {{ k.il_adi }}</span>
              <button type="button" class="chip-remove" @click="removeKiosk(k.id)">×</button>
            </span>
          </div>
          <div v-else class="all-kiosks-note">
            <i class="fa-solid fa-circle-info"></i>
            Seçim yapılmadı — bu logo <strong>tüm kiosklar</strong>a dağıtılır.
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeForm">İptal</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            <i v-if="saving" class="fa-solid fa-spinner fa-spin"></i>
            {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-shell { padding: 1.5rem; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.4rem; font-weight: 600; }
.data-table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.data-table th, .data-table td { padding: .6rem .8rem; border-bottom: 1px solid #e5e7eb; text-align: left; }
.data-table th { background: #f9fafb; font-weight: 600; }
.empty-row { text-align: center; color: #6b7280; padding: 2rem; }
.thumb { width: 48px; height: 48px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 4px; }
.no-img { color: #9ca3af; }
.badge { display: inline-block; padding: .2rem .6rem; border-radius: 9999px; font-size: .75rem; font-weight: 600; }
.badge-active { background: #d1fae5; color: #065f46; }
.badge-passive { background: #fee2e2; color: #991b1b; }
.actions { display: flex; gap: .5rem; }
.loading-msg { padding: 2rem; text-align: center; color: #6b7280; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { background: #fff; border-radius: 8px; padding: 1.5rem; width: 620px; max-height: 90vh; overflow-y: auto; }
.modal-box h2 { font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: .5rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }

/* Form */
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: .85rem; font-weight: 500; margin-bottom: .35rem; color: #374151; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-control { width: 100%; padding: .45rem .7rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: .9rem; }
.form-control:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px #bfdbfe; }
.field-error { margin-top: .3rem; color: #dc2626; font-size: .8rem; }
.field-hint { margin-top: .3rem; color: #6b7280; font-size: .8rem; }
.preview { margin-top: .5rem; width: 100px; height: 100px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 4px; }
.print-warning { margin-top: .5rem; background: #fefce8; border: 1px solid #fde68a; border-radius: 6px; padding: .5rem .75rem; font-size: .8rem; color: #92400e; }
.print-warning i { margin-right: .4rem; }
.toggle { display: flex; align-items: center; gap: .5rem; cursor: pointer; }
.toggle input { width: auto; }
.toggle-label { font-size: .9rem; }
.kiosk-list { max-height: 180px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 6px; padding: .5rem; }
.kiosk-item { display: flex; align-items: center; gap: .5rem; padding: .3rem; font-size: .85rem; }
.kiosk-item input { width: auto; }

/* Kiosk targeting */
.target-row { display: flex; align-items: center; gap: .5rem; margin-bottom: .5rem; }
.target-label { flex-shrink: 0; width: 130px; font-size: .8rem; color: #6b7280; }
.target-row > :last-child { flex: 1; }
.chip-list { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .5rem; }
.chip { display: inline-flex; align-items: center; gap: .3rem; padding: .25rem .55rem; border-radius: 9999px; font-size: .78rem; font-weight: 500; }
.chip--kiosk { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.chip-sub { opacity: .7; }
.chip-remove { background: none; border: none; cursor: pointer; font-size: .9rem; line-height: 1; padding: 0 0 0 .15rem; color: inherit; opacity: .6; }
.chip-remove:hover { opacity: 1; }
.all-kiosks-note { margin-top: .5rem; padding: .45rem .7rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; font-size: .82rem; color: #166534; }

/* Buttons */
.btn { padding: .45rem .9rem; border: none; border-radius: 6px; font-size: .85rem; cursor: pointer; font-weight: 500; transition: background .15s; }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-secondary:hover { background: #d1d5db; }
.btn-warning { background: #f59e0b; color: #fff; }
.btn-warning:hover { background: #d97706; }
.btn-success { background: #10b981; color: #fff; }
.btn-success:hover { background: #059669; }
.btn-sm { padding: .3rem .65rem; font-size: .8rem; }
</style>
