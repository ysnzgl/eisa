<script setup>
/**
 * Eczacı Paneli Kampanyaları — Admin CRUD
 * Kiosk playlist/scheduler sisteminden bağımsız basit kampanya yönetimi.
 */
import { ref, reactive, onMounted, watch } from 'vue';
import { http } from '../../services/api';
import { uploadMedia } from '../../services/dooh';
import { getIller, getIlceler } from '../../services/lookups';
import { toast } from 'vue-sonner';
import EisaLookup from '../../components/shared/EisaLookup.vue';

const campaigns       = ref([]);
const loading         = ref(false);
const saving          = ref(false);
const formOpen        = ref(false);
const editingId       = ref(null);

// Lookup listeleri — EisaLookup için { id, label, sub? } formatında
const iller           = ref([]);
const ilceler         = ref([]);
const eczaneler       = ref([]);
const illerLoading    = ref(false);
const ilcelerLoading  = ref(false);
const eczanelerLoading = ref(false);

// Tek-seçim pickerlar — seçilince listeye eklenir, sonra null'a döner
const pickedIlId     = ref(null);
const pickedIlceId   = ref(null);
const pickedEczaneId = ref(null);

const ALLOWED_DURATIONS = [15, 30, 60];

const empty = () => ({
  name: '',
  media_url: '',
  object_key: '',
  start_at: '',
  end_at: '',
  duration_seconds: 15,
  is_active: true,
  target_pharmacies: [],
  target_iller: [],
  target_ilceler: [],
});
const form = reactive(empty());
const previewUrl = ref('');

// ── Veri yükleme ──────────────────────────────────────────────────────────────

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get('/api/campaigns/v2/pharmacy-campaigns/');
    campaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Kampanyalar yüklenemedi.');
  } finally { loading.value = false; }
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
  const ilIds = form.target_iller.map((x) => x.id);
  if (!ilIds.length) { ilceler.value = []; return; }
  ilcelerLoading.value = true;
  try {
    const results = await Promise.all(ilIds.map((id) => getIlceler(id)));
    const flat = results.flat();
    ilceler.value = flat.map((ilce) => ({
      id: ilce.id,
      label: ilce.ad,
      sub: iller.value.find((il) => il.id === ilce.il_id)?.label ?? '',
    }));
    // Artık geçersiz ilçeleri temizle
    const validIds = new Set(ilceler.value.map((x) => x.id));
    form.target_ilceler = form.target_ilceler.filter((x) => validIds.has(x.id));
  } catch { toast.error('İlçe listesi yüklenemedi.'); }
  finally { ilcelerLoading.value = false; }
}

async function loadEczaneler() {
  if (eczaneler.value.length) return;
  eczanelerLoading.value = true;
  try {
    const { data } = await http.get('/api/pharmacies/');
    const list = Array.isArray(data) ? data : (data?.results ?? []);
    eczaneler.value = list.map((e) => ({
      id: e.id,
      label: e.ad,
      sub: [e.il_adi, e.ilce_adi].filter(Boolean).join(' / '),
    }));
  } catch { toast.error('Eczane listesi yüklenemedi.'); }
  finally { eczanelerLoading.value = false; }
}

onMounted(async () => {
  await load();
  loadIller();
  loadEczaneler();
});

// İl seçimi değişince ilçe listesini yenile
watch(() => form.target_iller.length, refreshIlceler);

// EisaLookup seçimi → listeye ekle, picker'ı sıfırla
watch(pickedIlId, (id) => {
  if (!id) return;
  const opt = iller.value.find((x) => x.id === id);
  if (opt && !form.target_iller.some((x) => x.id === id)) form.target_iller.push(opt);
  pickedIlId.value = null;
});
watch(pickedIlceId, (id) => {
  if (!id) return;
  const opt = ilceler.value.find((x) => x.id === id);
  if (opt && !form.target_ilceler.some((x) => x.id === id)) form.target_ilceler.push(opt);
  pickedIlceId.value = null;
});
watch(pickedEczaneId, (id) => {
  if (!id) return;
  const opt = eczaneler.value.find((x) => x.id === id);
  if (opt && !form.target_pharmacies.some((x) => x.id === id)) form.target_pharmacies.push(opt);
  pickedEczaneId.value = null;
});

// ── Form aç/kapat ─────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null;
  Object.assign(form, empty());
  previewUrl.value = '';
  pickedIlId.value = null; pickedIlceId.value = null; pickedEczaneId.value = null;
  formOpen.value = true;
}

async function openEdit(c) {
  editingId.value = c.id;
  Object.assign(form, {
    name: c.name,
    media_url: c.media_url,
    object_key: c.object_key || '',
    start_at: c.start_at?.slice(0, 16) ?? '',
    end_at:   c.end_at?.slice(0, 16) ?? '',
    duration_seconds: ALLOWED_DURATIONS.includes(c.duration_seconds) ? c.duration_seconds : 15,
    is_active: c.is_active,
    target_pharmacies: (c.target_pharmacies ?? []).map((id) => {
      const opt = eczaneler.value.find((e) => e.id === id);
      return opt ?? { id, label: String(id) };
    }),
    target_iller: (c.target_iller ?? []).map((id) => {
      const opt = iller.value.find((il) => il.id === id);
      return opt ?? { id, label: String(id) };
    }),
    target_ilceler: [],
  });
  previewUrl.value = c.media_url || '';
  pickedIlId.value = null; pickedIlceId.value = null; pickedEczaneId.value = null;
  formOpen.value = true;

  // İlçeleri yükle, sonra seçilenleri set et
  if ((c.target_ilceler ?? []).length) {
    await refreshIlceler();
    form.target_ilceler = ilceler.value.filter((x) => (c.target_ilceler ?? []).includes(x.id));
  }
}

function closeForm() { formOpen.value = false; }

async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.media_url  = data.media_url ?? data.url ?? '';
    form.object_key = data.object_key ?? '';
    previewUrl.value = form.media_url;
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Görsel yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}

function removePharmacy(idx) { form.target_pharmacies.splice(idx, 1); }
function removeIl(idx)       { form.target_iller.splice(idx, 1); }
function removeIlce(idx)     { form.target_ilceler.splice(idx, 1); }

// ── Kayıt ─────────────────────────────────────────────────────────────────────

async function save() {
  if (!form.name.trim()) { toast.warning('Kampanya adı zorunludur.'); return; }
  if (!form.media_url)   { toast.warning('Görsel yükleyin.'); return; }
  if (!form.start_at || !form.end_at) { toast.warning('Tarih aralığı zorunludur.'); return; }
  if (new Date(form.end_at) <= new Date(form.start_at)) {
    toast.warning('Bitiş tarihi başlangıçtan sonra olmalıdır.'); return;
  }
  if (!form.target_pharmacies.length && !form.target_iller.length && !form.target_ilceler.length) {
    toast.warning('En az bir hedef seçin: eczane, il veya ilçe.'); return;
  }

  const payload = {
    name: form.name,
    media_url: form.media_url,
    object_key: form.object_key || undefined,
    start_at: new Date(form.start_at).toISOString(),
    end_at:   new Date(form.end_at).toISOString(),
    duration_seconds: Number(form.duration_seconds),
    is_active: form.is_active,
    target_pharmacies: form.target_pharmacies.map((p) => p.id),
    target_iller:      form.target_iller.map((x) => x.id),
    target_ilceler:    form.target_ilceler.map((x) => x.id),
  };

  saving.value = true;
  try {
    if (editingId.value) {
      await http.patch(`/api/campaigns/v2/pharmacy-campaigns/${editingId.value}/`, payload);
      toast.success('Kampanya güncellendi.');
    } else {
      await http.post('/api/campaigns/v2/pharmacy-campaigns/', payload);
      toast.success('Kampanya oluşturuldu.');
    }
    formOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e?.response?.data?.detail || JSON.stringify(e?.response?.data || {}) || 'Kayıt başarısız.');
  } finally { saving.value = false; }
}

async function remove(c) {
  if (!confirm(`"${c.name}" kampanyasını silmek istiyor musunuz?`)) return;
  try {
    await http.delete(`/api/campaigns/v2/pharmacy-campaigns/${c.id}/`);
    toast.success('Kampanya silindi.');
    await load();
  } catch (e) { toast.error(e?.response?.data?.detail || 'Silme başarısız.'); }
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function targetSummary(c) {
  const parts = [];
  if (c.target_pharmacies?.length) parts.push(`${c.target_pharmacies.length} eczane`);
  if (c.target_iller?.length)      parts.push(`${c.target_iller.length} il`);
  if (c.target_ilceler?.length)    parts.push(`${c.target_ilceler.length} ilçe`);
  return parts.join(', ') || '—';
}
</script>

<template>
  <div class="ph-camp-root">
    <!-- Başlık -->
    <div class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title"><i class="fa-solid fa-prescription-bottle-medical"></i> Eczacı Paneli Kampanyaları</h2>
        <button class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni Kampanya
        </button>
      </div>

      <div class="eisa-panel-body">
        <p class="ph-desc">Eczacı panelinde gösterilen kampanyalar. Kiosk playlist sisteminden bağımsızdır.</p>

        <div v-if="loading" class="ph-loading">
          <i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor…
        </div>

        <table v-else class="eisa-table">
          <thead>
            <tr>
              <th class="ph-thumb-col">Görsel</th>
              <th>Kampanya Adı</th>
              <th>Başlangıç</th>
              <th>Bitiş</th>
              <th>Süre</th>
              <th>Hedef</th>
              <th>Durum</th>
              <th class="actions-col"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!campaigns.length">
              <td colspan="8" class="empty-row">Henüz kampanya yok.</td>
            </tr>
            <tr v-for="c in campaigns" :key="c.id">
              <td>
                <div class="ph-thumb">
                  <img v-if="c.media_url" :src="c.media_url" :alt="c.name" />
                  <i v-else class="fa-solid fa-image ph-thumb-placeholder"></i>
                </div>
              </td>
              <td><span class="eisa-cell-name">{{ c.name }}</span></td>
              <td class="cell-muted">{{ fmtDate(c.start_at) }}</td>
              <td class="cell-muted">{{ fmtDate(c.end_at) }}</td>
              <td class="cell-muted">{{ c.duration_seconds }} sn</td>
              <td class="cell-muted small">{{ targetSummary(c) }}</td>
              <td>
                <span class="eisa-pill" :class="c.is_active ? 'eisa-pill-success' : 'eisa-pill-muted'">
                  {{ c.is_active ? 'Aktif' : 'Pasif' }}
                </span>
              </td>
              <td>
                <div class="cell-actions">
                  <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(c)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="eisa-icon-btn danger" title="Sil" @click="remove(c)">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Form Modal -->
    <Teleport to="body">
      <div v-if="formOpen" class="eisa-modal-backdrop" @click.self="closeForm">
        <div class="eisa-modal ph-form-modal">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ editingId ? 'Kampanya Düzenle' : 'Yeni Kampanya' }}</h3>
            <button class="eisa-modal-close" @click="closeForm"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <!-- Ad -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Kampanya Adı *</label>
                <input v-model="form.name" class="eisa-field" placeholder="Kampanya adı" />
              </div>

              <!-- Görsel -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Yatay Görsel *</label>
                <div v-if="previewUrl" class="ph-preview">
                  <img :src="previewUrl" alt="Önizleme" />
                  <button class="eisa-icon-btn danger ph-preview-rm" title="Kaldır" @click="form.media_url=''; previewUrl=''">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
                <label v-else class="upload">
                  <input type="file" accept="image/*" @change="onPickFile" :disabled="saving" />
                  <span><i class="fa-solid fa-cloud-arrow-up"></i> Görsel seç</span>
                </label>
              </div>

              <!-- Tarihler -->
              <div class="eisa-form-row">
                <label class="eisa-field-label">Başlangıç *</label>
                <input v-model="form.start_at" type="datetime-local" class="eisa-field" />
              </div>
              <div class="eisa-form-row">
                <label class="eisa-field-label">Bitiş *</label>
                <input v-model="form.end_at" type="datetime-local" class="eisa-field" />
              </div>

              <!-- Süre -->
              <div class="eisa-form-row">
                <label class="eisa-field-label">Gösterim Süresi</label>
                <select v-model.number="form.duration_seconds" class="eisa-field">
                  <option :value="15">15 saniye</option>
                  <option :value="30">30 saniye</option>
                  <option :value="60">60 saniye</option>
                </select>
              </div>

              <!-- Aktif -->
              <div class="eisa-form-row eisa-toggle-row">
                <label class="eisa-toggle">
                  <input v-model="form.is_active" type="checkbox" />
                  <span>Aktif</span>
                </label>
              </div>

              <!-- Hedef: İl -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Hedef İller</label>
                <EisaLookup
                  v-model="pickedIlId"
                  :options="iller"
                  :loading="illerLoading"
                  placeholder="İl ara…"
                />
                <div v-if="form.target_iller.length" class="ph-chip-list">
                  <span v-for="(x, i) in form.target_iller" :key="x.id" class="ph-chip ph-chip--il">
                    <i class="fa-solid fa-map"></i> {{ x.label }}
                    <button type="button" class="chip-remove" @click="removeIl(i)">×</button>
                  </span>
                </div>
              </div>

              <!-- Hedef: İlçe -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Hedef İlçeler
                  <span class="ph-field-note">(il seçilince çıkar)</span>
                </label>
                <EisaLookup
                  v-model="pickedIlceId"
                  :options="ilceler"
                  :loading="ilcelerLoading"
                  placeholder="İlçe ara…"
                />
                <p v-if="!form.target_iller.length" class="muted small" style="margin-top:.3rem">
                  İlçe seçmek için önce en az bir il ekleyin.
                </p>
                <div v-else-if="form.target_ilceler.length" class="ph-chip-list">
                  <span v-for="(x, i) in form.target_ilceler" :key="x.id" class="ph-chip ph-chip--ilce">
                    <i class="fa-solid fa-map-pin"></i> {{ x.label }}<span v-if="x.sub" class="ph-chip-sub">, {{ x.sub }}</span>
                    <button type="button" class="chip-remove" @click="removeIlce(i)">×</button>
                  </span>
                </div>
              </div>

              <!-- Hedef: Eczane -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Hedef Eczaneler</label>
                <EisaLookup
                  v-model="pickedEczaneId"
                  :options="eczaneler"
                  :loading="eczanelerLoading"
                  placeholder="Eczane ara…"
                />
                <div v-if="form.target_pharmacies.length" class="ph-chip-list">
                  <span v-for="(p, i) in form.target_pharmacies" :key="p.id" class="ph-chip ph-chip--eczane">
                    <i class="fa-solid fa-house-medical"></i> {{ p.label || p.id }}
                    <span v-if="p.sub" class="ph-chip-sub">, {{ p.sub }}</span>
                    <button type="button" class="chip-remove" @click="removePharmacy(i)">×</button>
                  </span>
                </div>
                <p v-else class="muted small" style="margin-top:.35rem">Henüz eczane seçilmedi.</p>
              </div>
              <p class="muted small ph-target-note">
                En az bir il, ilçe veya eczane seçilmelidir.
              </p>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="closeForm">İptal</button>
            <button class="eisa-btn eisa-btn-cta" @click="save" :disabled="saving">
              <i class="fa-solid fa-check"></i> {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.ph-camp-root { padding: 1.5rem; }
.ph-desc { font-size: .875rem; color: #6B7280; margin: 0 0 1rem; }
.ph-loading { text-align: center; padding: 2rem; color: #6B7280; }
.ph-form-modal { max-width: 660px; }

/* Grid thumbnail — sabit, satır boyutunu bozmaz */
.ph-thumb-col { width: 136px; }
.ph-thumb {
  width: 120px;
  height: 68px;
  border-radius: 6px;
  overflow: hidden;
  background: #F4F3EF;
  border: 1px solid #E5E3DF;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ph-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-width: 100%;
  display: block;
}
.ph-thumb-placeholder { font-size: 1.1rem; color: #9CA3AF; }

/* Önizleme görsel (form içi) */
.ph-preview {
  position: relative;
  width: 100%;
  max-height: 160px;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #E5E3DF;
}
.ph-preview img { width: 100%; height: 160px; object-fit: contain; background: #F4F3EF; }
.ph-preview-rm {
  position: absolute;
  top: 6px;
  right: 6px;
}

/* Chip'ler */
.ph-chip-list { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .5rem; }
.ph-chip {
  display: inline-flex; align-items: center; gap: .3rem;
  border-radius: 999px;
  padding: .2rem .65rem; font-size: .78rem; font-weight: 500;
  border: 1px solid;
}
.ph-chip--il     { background: #FEF2F2; color: #B1121B; border-color: #FECACA; }
.ph-chip--ilce   { background: #f0fdf4; color: #166534; border-color: #A7F3D0; }
.ph-chip--eczane { background: #faf5ff; color: #7c3aed; border-color: #e9d5ff; }
.ph-chip-sub { opacity: .7; font-weight: 400; }
.chip-remove { background: none; border: none; cursor: pointer; padding: 0; color: inherit; opacity: .7; line-height: 1; margin-left: .1rem; }
.chip-remove:hover { opacity: 1; }

.ph-field-note { font-weight: 400; color: #9CA3AF; font-size: .7rem; margin-left: .4rem; }
.ph-target-note { margin-top: .5rem; color: #9CA3AF; }

.upload {
  display: flex; align-items: center; gap: .5rem;
  padding: .65rem 1rem;
  border: 2px dashed #D1D5DB; border-radius: 10px;
  cursor: pointer; font-size: .875rem; color: #6B7280;
  transition: border-color .15s, color .15s;
}
.upload:hover { border-color: #B1121B; color: #B1121B; }
.upload input { display: none; }
</style>
