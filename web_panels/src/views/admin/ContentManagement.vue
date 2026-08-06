<script setup>
/**
 * İçerik Yönetimi — idle ekranı için görsel içerik CRUD.
 * Kullanıcıya görünen hiçbir yerde teknik "HouseAd" terimi kullanılmaz.
 */
import { ref, reactive, onMounted } from 'vue';
import { uploadMedia, listHouseAds, createHouseAd, updateHouseAd, deleteHouseAd } from '../../services/dooh';
import { toast } from 'vue-sonner';

const items      = ref([]);
const loading    = ref(false);
const saving     = ref(false);
const formOpen   = ref(false);
const previewOpen = ref(false);
const editingId  = ref(null);

const DURATIONS = [15, 30, 45, 60];
const VIDEO_EXT = /\.(mp4|webm|ogg|mov|avi|mkv|flv|wmv)$/i;
const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB client-side uyarı eşiği

const empty = () => ({
  name: '',
  media_url: '',
  object_key: '',
  duration_seconds: 15,
  priority: 100,
  aktif: true,
});
const form = reactive(empty());
const previewUrl = ref('');

// ── Veri yükleme ──────────────────────────────────────────────────────────────

async function load() {
  loading.value = true;
  try {
    const { data } = await listHouseAds();
    items.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'İçerik listesi yüklenemedi.');
  } finally { loading.value = false; }
}

onMounted(load);

// ── Form aç/kapat ─────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null;
  Object.assign(form, empty());
  previewUrl.value = '';
  formOpen.value = true;
}

function openEdit(item) {
  editingId.value = item.id;
  Object.assign(form, {
    name: item.name,
    media_url: item.media_url,
    object_key: item.object_key || '',
    duration_seconds: DURATIONS.includes(item.duration_seconds) ? item.duration_seconds : 15,
    priority: item.priority ?? 100,
    aktif: item.aktif,
  });
  previewUrl.value = item.media_url || '';
  formOpen.value = true;
}

function closeForm() { formOpen.value = false; }

// ── Görsel yükleme ────────────────────────────────────────────────────────────

async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  if (VIDEO_EXT.test(file.name)) {
    toast.error('Video dosyası yüklenemez. Yalnızca PNG, JPEG veya WebP görseller kabul edilir.');
    ev.target.value = '';
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    toast.warning('Dosya 10 MB\'dan büyük. Yüklemeye devam ediliyor; backend limiti 100 MB\'dır.');
  }
  saving.value = true;
  try {
    const data = await uploadMedia(file, 'image');
    form.media_url  = data.media_url ?? data.url ?? '';
    form.object_key = data.object_key ?? '';
    previewUrl.value = form.media_url;
    toast.success('Görsel yüklendi.');
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Görsel yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}

// ── Kayıt ─────────────────────────────────────────────────────────────────────

async function save() {
  if (!form.name.trim())  { toast.warning('İçerik adı zorunludur.'); return; }
  if (!form.media_url)    { toast.warning('Görsel yükleyin.'); return; }

  const payload = {
    name: form.name.trim(),
    media_url: form.media_url,
    object_key: form.object_key || undefined,
    duration_seconds: Number(form.duration_seconds),
    priority: Number(form.priority),
    aktif: form.aktif,
  };

  saving.value = true;
  try {
    if (editingId.value) {
      await updateHouseAd(editingId.value, payload);
      toast.success('İçerik güncellendi.');
    } else {
      await createHouseAd(payload);
      toast.success('İçerik oluşturuldu.');
    }
    formOpen.value = false;
    await load();
  } catch (e) {
    const err = e?.response?.data;
    const msg = err?.media_url?.[0] || err?.duration_seconds?.[0] || err?.detail
      || JSON.stringify(err || {});
    toast.error(msg || 'Kayıt başarısız.');
  } finally { saving.value = false; }
}

async function toggleActive(item) {
  try {
    await updateHouseAd(item.id, { aktif: !item.aktif });
    item.aktif = !item.aktif;
  } catch { toast.error('Durum güncellenemedi.'); }
}

async function remove(item) {
  if (!confirm(`"${item.name}" içeriğini silmek istiyor musunuz?`)) return;
  try {
    await deleteHouseAd(item.id);
    toast.success('İçerik silindi.');
    await load();
  } catch (e) { toast.error(e?.response?.data?.detail || 'Silme başarısız.'); }
}

// ── Önizleme modal ────────────────────────────────────────────────────────────

const previewItem = ref(null);
function openPreview(item) { previewItem.value = item; previewOpen.value = true; }
function closePreview()    { previewOpen.value = false; }
</script>

<template>
  <div class="cm-root">
    <div class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">
          <i class="fa-solid fa-images"></i> İçerik Yönetimi
        </h2>
        <button class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni İçerik
        </button>
      </div>

      <div class="eisa-panel-body">
        <p class="cm-desc">
          Kiosk bekleme ekranında arka plan olarak gösterilecek görseller.
          Yalnızca PNG, JPEG veya WebP formatları kabul edilir.
        </p>

        <div v-if="loading" class="cm-loading">
          <i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor…
        </div>

        <table v-else class="eisa-table">
          <thead>
            <tr>
              <th class="cm-thumb-col">Görsel</th>
              <th>Ad</th>
              <th>Süre</th>
              <th>Öncelik</th>
              <th>Durum</th>
              <th class="actions-col"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!items.length">
              <td colspan="6" class="empty-row">Henüz içerik yok.</td>
            </tr>
            <tr v-for="item in items" :key="item.id">
              <td>
                <div class="cm-thumb">
                  <img v-if="item.media_url" :src="item.media_url" :alt="item.name" />
                  <i v-else class="fa-solid fa-image cm-thumb-placeholder"></i>
                </div>
              </td>
              <td><span class="eisa-cell-name">{{ item.name }}</span></td>
              <td class="cell-muted">{{ item.duration_seconds }} sn</td>
              <td class="cell-muted">{{ item.priority }}</td>
              <td>
                <button
                  class="eisa-pill cm-pill-toggle"
                  :class="item.aktif ? 'eisa-pill-success' : 'eisa-pill-muted'"
                  :title="item.aktif ? 'Pasife Al' : 'Aktife Al'"
                  @click="toggleActive(item)"
                >
                  {{ item.aktif ? 'Aktif' : 'Pasif' }}
                </button>
              </td>
              <td>
                <div class="cell-actions">
                  <button class="eisa-icon-btn" title="Ekran Önizleme" @click="openPreview(item)">
                    <i class="fa-solid fa-eye"></i>
                  </button>
                  <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(item)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="eisa-icon-btn danger" title="Sil" @click="remove(item)">
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
        <div class="eisa-modal cm-form-modal">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ editingId ? 'İçerik Düzenle' : 'Yeni İçerik' }}</h3>
            <button class="eisa-modal-close" @click="closeForm">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">

              <!-- Ad -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">İçerik Adı *</label>
                <input v-model="form.name" class="eisa-field" placeholder="İçerik adı" />
              </div>

              <!-- Görsel yükleme -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label">Görsel * <span class="cm-hint">(PNG / JPEG / WebP)</span></label>
                <div v-if="previewUrl" class="cm-preview">
                  <img :src="previewUrl" alt="Önizleme" />
                  <button class="eisa-icon-btn danger cm-preview-rm" @click="form.media_url=''; previewUrl=''">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
                <label class="eisa-btn eisa-btn-outline cm-upload-btn" :class="{ disabled: saving }">
                  <i class="fa-solid fa-upload"></i>
                  {{ saving ? 'Yükleniyor…' : (previewUrl ? 'Değiştir' : 'Görsel Seç') }}
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                    class="cm-file-hidden"
                    :disabled="saving"
                    @change="onPickFile"
                  />
                </label>
              </div>

              <!-- Süre -->
              <div class="eisa-form-row">
                <label class="eisa-field-label">Gösterim Süresi *</label>
                <select v-model.number="form.duration_seconds" class="eisa-field">
                  <option v-for="d in DURATIONS" :key="d" :value="d">{{ d }} saniye</option>
                </select>
              </div>

              <!-- Öncelik -->
              <div class="eisa-form-row">
                <label class="eisa-field-label">Öncelik <span class="cm-hint">(düşük = önce)</span></label>
                <input v-model.number="form.priority" type="number" min="1" max="999" class="eisa-field" />
              </div>

              <!-- Durum -->
              <div class="eisa-form-row eisa-form-row-full">
                <label class="eisa-field-label eisa-checkbox-label">
                  <input type="checkbox" v-model="form.aktif" />
                  Aktif — kiosk bekleme ekranında gösterilsin
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
    </Teleport>

    <!-- Önizleme Modal — kiosk idle ekranı mockup -->
    <Teleport to="body">
      <div v-if="previewOpen" class="eisa-modal-backdrop" @click.self="closePreview">
        <div class="eisa-modal cm-preview-modal">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">
              <i class="fa-solid fa-mobile-screen"></i> Kiosk Ekranı Önizleme
            </h3>
            <button class="eisa-modal-close" @click="closePreview">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="eisa-modal-body cm-preview-body">
            <!-- 9:16 oranında kiosk simülasyonu -->
            <div class="cm-kiosk-sim">
              <div class="cm-kiosk-bg">
                <img v-if="previewItem?.media_url" :src="previewItem.media_url" class="cm-kiosk-bg-img" alt="arka plan" />
                <div v-else class="cm-kiosk-safe-bg"></div>
              </div>
              <!-- Logo + CTA overlay -->
              <div class="cm-kiosk-overlay">
                <div class="cm-kiosk-logo">e-<span>İSA</span></div>
                <div class="cm-kiosk-tap">
                  <i class="fa-solid fa-hand-pointer"></i> Başlamak için dokunun
                </div>
              </div>
              <!-- AdPromo temsili — alt overlay -->
              <div class="cm-kiosk-adpromo">
                <div class="cm-kiosk-adpromo-inner">
                  <i class="fa-solid fa-bullhorn"></i>
                  <span>Bu alana sponsor olabilirsiniz</span>
                </div>
              </div>
              <!-- Güvenli alan çerçeveleri (1080x1920) -->
              <div class="cm-safe-frame"></div>
            </div>
            <p class="cm-preview-caption">
              Temsili önizleme — 9:16 (1080×1920). Gerçek boyut kiosk ekranında görünür.
            </p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.cm-root { padding: 1.5rem; }
.cm-desc { color: var(--color-muted, #6b7280); font-size: 0.875rem; margin-bottom: 1.25rem; }
.cm-loading { padding: 2rem; text-align: center; color: var(--color-muted, #6b7280); }
.cm-hint { font-size: 0.75rem; color: var(--color-muted, #6b7280); font-weight: 400; }

.cm-thumb-col { width: 72px; }
.cm-thumb {
  width: 56px; height: 72px;
  border-radius: 4px; overflow: hidden;
  background: #f3f4f6;
  display: flex; align-items: center; justify-content: center;
}
.cm-thumb img { width: 100%; height: 100%; object-fit: cover; }
.cm-thumb-placeholder { color: #9ca3af; font-size: 1.25rem; }

.cm-pill-toggle { cursor: pointer; border: none; font-size: 0.75rem; }

.cm-form-modal { width: min(560px, 95vw); }

.cm-preview {
  position: relative; display: inline-block;
  max-width: 100%; margin-bottom: 0.5rem;
}
.cm-preview img { max-height: 180px; border-radius: 6px; object-fit: contain; }
.cm-preview-rm { position: absolute; top: 4px; right: 4px; }

.cm-upload-btn { display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.cm-upload-btn.disabled { opacity: 0.6; pointer-events: none; }
.cm-file-hidden { display: none; }

/* Kiosk önizleme */
.cm-preview-modal { width: min(400px, 92vw); }
.cm-preview-body  { display: flex; flex-direction: column; align-items: center; gap: 1rem; }

.cm-kiosk-sim {
  position: relative;
  width: 200px;
  aspect-ratio: 9/16;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
  background: #0f1622;
}
.cm-kiosk-bg { position: absolute; inset: 0; }
.cm-kiosk-bg-img { width: 100%; height: 100%; object-fit: cover; }
.cm-kiosk-safe-bg {
  width: 100%; height: 100%;
  background: radial-gradient(120% 140% at 50% 0%, #1b2436 0%, #0f1622 55%, #0b1019 100%);
}
.cm-kiosk-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 8px; padding: 16px;
}
.cm-kiosk-logo {
  font-size: 1.4rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;
}
.cm-kiosk-logo span { color: #B1121B; }
.cm-kiosk-tap { font-size: 0.6rem; color: rgba(255,255,255,.75); }

.cm-kiosk-adpromo {
  position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
  width: 85%; z-index: 10;
}
.cm-kiosk-adpromo-inner {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px; border-radius: 8px;
  background: rgba(17,24,39,.7); border: 1px solid rgba(255,255,255,.1);
  color: #fff; font-size: 0.55rem; white-space: nowrap; overflow: hidden;
}
.cm-kiosk-adpromo-inner i { color: #B1121B; flex-shrink: 0; }

/* Güvenli alan çerçevesi */
.cm-safe-frame {
  position: absolute; inset: 5%;
  border: 1px dashed rgba(255,255,255,.2);
  border-radius: 4px; pointer-events: none;
}

.cm-preview-caption { font-size: 0.75rem; color: #6b7280; text-align: center; }
</style>
