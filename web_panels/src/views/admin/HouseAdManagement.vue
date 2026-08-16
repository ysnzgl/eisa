<script setup>
/**
 * HouseAd Yönetimi — Dolgu (filler) reklam oluştur / düzenle / sil.
 * Tablo: Ad, Süre, Öncelik, Aktif/Pasif, Medya önizleme, Orijinal İndir.
 */
import { ref, reactive, computed, onMounted } from 'vue';
import {
  listHouseAds, createHouseAd, updateHouseAd, deleteHouseAd,
  uploadMedia, downloadHouseAdMedia,
} from '../../services/dooh.js';
import { toast } from 'vue-sonner';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';

const houseAds = ref([]);
const loading  = ref(false);
const saving   = ref(false);

const formOpen = ref(false);
const editingId = ref(null);

const deleteConfirmOpen = ref(false);
const deleteTarget = ref(null);
const deleteLoading = ref(false);

const downloadingId = ref(null);

const form = reactive({
  name: '',
  media_url: '',
  object_key: '',
  duration_seconds: 15,
  aktif: true,
  priority: 100,
});

function emptyForm() {
  return { name: '', media_url: '', object_key: '', duration_seconds: 15, aktif: true, priority: 100 };
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, emptyForm());
  formOpen.value = true;
}

function openEdit(ha) {
  editingId.value = ha.id;
  Object.assign(form, {
    name: ha.name,
    media_url: ha.media_url,
    object_key: ha.object_key || '',
    duration_seconds: ha.duration_seconds,
    aktif: ha.aktif,
    priority: ha.priority,
  });
  formOpen.value = true;
}

function closeForm() { formOpen.value = false; }

function isVideoUrl(url) {
  if (!url) return false;
  const clean = (url || '').split('?')[0].toLowerCase();
  return /\.(mp4|webm|ogg|mov)$/.test(clean);
}

async function refresh() {
  loading.value = true;
  try {
    const { data } = await listHouseAds();
    houseAds.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'HouseAd listesi yüklenemedi.');
  } finally { loading.value = false; }
}

async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.media_url  = data.media_url ?? data.url ?? '';
    form.object_key = data.object_key ?? '';
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}

async function save() {
  if (!form.name.trim()) { toast.warning('Ad zorunludur.'); return; }
  if (!form.media_url)   { toast.warning('Medya yüklemelisiniz.'); return; }

  saving.value = true;
  try {
    const payload = {
      name: form.name,
      media_url: form.media_url,
      object_key: form.object_key || undefined,
      duration_seconds: Number(form.duration_seconds),
      aktif: form.aktif,
      priority: Number(form.priority),
    };
    if (editingId.value) {
      await updateHouseAd(editingId.value, payload);
      toast.success('HouseAd güncellendi.');
    } else {
      await createHouseAd(payload);
      toast.success('HouseAd oluşturuldu.');
    }
    closeForm();
    await refresh();
  } catch (e) {
    toast.error(JSON.stringify(e?.response?.data) || 'Kaydetme başarısız.');
  } finally { saving.value = false; }
}

function askDelete(ha) { deleteTarget.value = ha; deleteConfirmOpen.value = true; }
async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleteLoading.value = true;
  try {
    await deleteHouseAd(deleteTarget.value.id);
    deleteConfirmOpen.value = false; deleteTarget.value = null;
    await refresh(); toast.success('HouseAd silindi.');
  } catch (e) { toast.error(e?.response?.data?.detail || 'Silme başarısız.'); }
  finally { deleteLoading.value = false; }
}

async function download(ha) {
  if (!ha.object_key) {
    toast.warning('Bu HouseAd için object_key bulunamadı.');
    return;
  }
  downloadingId.value = ha.id;
  try {
    const resp = await downloadHouseAdMedia(ha.id);
    const blob = new Blob([resp.data], { type: resp.headers['content-type'] || 'application/octet-stream' });
    const url  = URL.createObjectURL(blob);
    const filename = ha.object_key.split('/').pop() || `housead-${ha.id}`;
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('İndirme başladı.');
  } catch (e) {
    toast.error(e?.response?.data?.error || 'İndirme başarısız.');
  } finally { downloadingId.value = null; }
}

const searchQuery = ref('');
const filteredHouseAds = computed(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase('tr');
  if (!q) return houseAds.value;
  return houseAds.value.filter((ha) => ha.name.toLocaleLowerCase('tr').includes(q));
});

onMounted(refresh);
</script>

<template>
  <div class="eisa-page house-ad-page">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Reklam</p>
        <h1 class="eisa-page-title">HouseAd Yönetimi</h1>
        <p class="eisa-page-subtitle">Dolgu (filler) reklamları oluştur ve yönet.</p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn" @click="refresh" :disabled="loading">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i> Yenile
        </button>
        <button class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni HouseAd
        </button>
      </div>
    </header>

    <section class="eisa-panel toolbar-panel">
      <div class="eisa-toolbar">
        <div class="eisa-search" style="flex:1;min-width:240px;position:relative">
          <i class="fa-solid fa-magnifying-glass" style="position:absolute;left:.75rem;top:50%;transform:translateY(-50%);color:#94a3b8"></i>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="HouseAd adı ara…"
            class="eisa-field"
            style="padding-left:2.25rem;width:100%"
          />
        </div>
      </div>
    </section>

    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">HouseAd Listesi ({{ filteredHouseAds.length }})</h2>
      </div>
      <div class="eisa-panel-body">
        <div class="table-wrap">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>Medya</th>
                <th>Ad</th>
                <th>Süre</th>
                <th>Öncelik</th>
                <th>Durum</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="6" class="empty-row">Yükleniyor…</td></tr>
              <tr v-else-if="!filteredHouseAds.length">
                <td colspan="6" class="empty-row">
                  <template v-if="searchQuery">Eşleşen HouseAd yok. <button class="link-btn" @click="searchQuery=''">Temizle</button></template>
                  <template v-else>Henüz HouseAd yok. <button class="link-btn" @click="openCreate">Hemen oluştur →</button></template>
                </td>
              </tr>
              <tr v-else v-for="ha in filteredHouseAds" :key="ha.id">
                <!-- Medya önizleme -->
                <td class="media-cell">
                  <div class="ha-media-preview" v-if="ha.media_url">
                    <video
                      v-if="isVideoUrl(ha.media_url)"
                      :src="ha.media_url"
                      muted
                      controls
                      preload="metadata"
                      controlslist="nodownload nofullscreen"
                      class="ha-media-video"
                    />
                    <img
                      v-else
                      :src="ha.media_url"
                      :alt="ha.name"
                      loading="lazy"
                      class="ha-media-img"
                      @error="(e) => e.target.style.display='none'"
                    />
                  </div>
                  <div v-else class="ha-media-placeholder">
                    <i class="fa-regular fa-image"></i>
                  </div>
                </td>

                <td><strong>{{ ha.name }}</strong></td>
                <td>{{ ha.duration_seconds }} sn</td>
                <td>{{ ha.priority }}</td>
                <td>
                  <span class="eisa-pill" :class="ha.aktif ? 'eisa-pill-success' : 'eisa-pill-muted'">
                    {{ ha.aktif ? 'Aktif' : 'Pasif' }}
                  </span>
                </td>
                <td class="actions">
                  <button
                    class="eisa-icon-btn"
                    title="Orijinali İndir"
                    :disabled="downloadingId === ha.id || !ha.object_key"
                    @click="download(ha)"
                  >
                    <i class="fa-solid" :class="downloadingId === ha.id ? 'fa-circle-notch fa-spin' : 'fa-download'"></i>
                  </button>
                  <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(ha)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="eisa-icon-btn danger" title="Sil" @click="askDelete(ha)">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Oluştur / Düzenle modal -->
    <div v-if="formOpen" class="eisa-modal-backdrop" @click.self="closeForm">
      <div class="eisa-modal" style="max-width:560px">
        <div class="eisa-modal-header">
          <h3>{{ editingId ? 'HouseAd Düzenle' : 'Yeni HouseAd' }}</h3>
          <button class="eisa-icon-btn" @click="closeForm"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="eisa-modal-body">
          <div class="eisa-form-grid">
            <div class="eisa-form-row eisa-form-row-full">
              <label class="eisa-field-label">Ad *</label>
              <input v-model="form.name" class="eisa-field" placeholder="Örn. Kış İndirimi" />
            </div>

            <!-- Medya yükleme / önizleme -->
            <div class="eisa-form-row eisa-form-row-full">
              <label class="eisa-field-label">Medya (görsel veya video)</label>
              <div v-if="form.media_url" class="ha-form-preview">
                <video
                  v-if="isVideoUrl(form.media_url)"
                  :src="form.media_url"
                  muted
                  controls
                  preload="metadata"
                  controlslist="nodownload nofullscreen"
                  class="ha-form-media"
                />
                <img
                  v-else
                  :src="form.media_url"
                  alt="Önizleme"
                  class="ha-form-media"
                  @error="(e) => e.target.style.display='none'"
                />
                <button
                  type="button"
                  class="eisa-btn eisa-btn-ghost eisa-btn-sm"
                  style="margin-top:.5rem"
                  @click="form.media_url=''; form.object_key=''"
                >
                  <i class="fa-solid fa-trash"></i> Kaldır
                </button>
              </div>
              <label v-else class="upload" style="display:flex;align-items:center;gap:.5rem;padding:.75rem;border:2px dashed #e2e8f0;border-radius:8px;cursor:pointer">
                <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickFile" :disabled="saving" style="display:none" />
                <i class="fa-solid fa-cloud-arrow-up" style="color:#94a3b8;font-size:1.25rem"></i>
                <span class="muted small">{{ saving ? 'Yükleniyor…' : 'Dosya seç (PNG/JPG/WebP/MP4/WebM, max 100 MB)' }}</span>
              </label>
            </div>

            <div class="eisa-form-row">
              <label class="eisa-field-label">Süre (sn) *</label>
              <select v-model.number="form.duration_seconds" class="eisa-field">
                <option :value="15">15 sn</option>
                <option :value="30">30 sn</option>
                <option :value="45">45 sn</option>
                <option :value="60">60 sn</option>
              </select>
            </div>

            <div class="eisa-form-row">
              <label class="eisa-field-label">Öncelik</label>
              <input v-model.number="form.priority" type="number" min="1" max="999" class="eisa-field" />
            </div>

            <div class="eisa-form-row eisa-form-row-full">
              <label class="eisa-field-label">Durum</label>
              <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer">
                <input type="checkbox" v-model="form.aktif" />
                <span>{{ form.aktif ? 'Aktif' : 'Pasif' }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" @click="closeForm">İptal</button>
          <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="save">
            <i class="fa-solid fa-floppy-disk"></i>
            {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Silme onay -->
    <EisaDeleteConfirm
      :open="deleteConfirmOpen"
      title="HouseAd Sil"
      :message="deleteTarget ? `'${deleteTarget.name}' kalıcı olarak silinecek. Bu işlem geri alınamaz.` : ''"
      confirm-label="Evet, Sil"
      :loading="deleteLoading"
      @confirm="confirmDelete"
      @cancel="deleteConfirmOpen = false; deleteTarget = null"
    />
  </div>
</template>

<style scoped>
/* HouseAd medya önizleme — tablo hücresi */
.media-cell { padding: .5rem .75rem; width: 160px; }

.ha-media-preview {
  width: 140px;
  max-height: 110px;
  overflow: hidden;
  border-radius: 6px;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--c-border, #e2e8f0);
}
.ha-media-video {
  width: 140px;
  max-height: 110px;
  object-fit: contain;
  display: block;
}
.ha-media-img {
  width: 140px;
  max-height: 110px;
  object-fit: contain;
  display: block;
}
.ha-media-placeholder {
  width: 140px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-radius: 6px;
  border: 1px solid var(--c-border, #e2e8f0);
  color: #94a3b8;
  font-size: 1.5rem;
}

/* Form modal — medya önizleme */
.ha-form-preview {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: .5rem;
}
.ha-form-media {
  max-width: 280px;
  max-height: 220px;
  object-fit: contain;
  display: block;
  border-radius: 8px;
  background: #0f172a;
  border: 1px solid var(--c-border, #e2e8f0);
}

.eisa-btn-sm { padding: .25rem .65rem; font-size: .78rem; height: auto; }
.muted { color: #94a3b8; }
.small { font-size: .75rem; }
</style>
