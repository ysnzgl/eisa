<script setup>
/**
 * İçerik Yönetimi — kiosk bekleme (idle) ekranı için başlık/metin tabanlı içerik CRUD.
 * İçerikler AdPromo large görünümünde başlık fade + metin daktilo animasyonuyla
 * rastgele gösterilir. Medya/HTML yoktur; yalnızca düz metin.
 */
import { ref, reactive, computed, onMounted } from 'vue';
import {
  listIdleContents, createIdleContent, updateIdleContent, deleteIdleContent,
} from '../../services/dooh';
import { toast } from 'vue-sonner';

const BASLIK_MAX = 100;
const METIN_MAX = 300;

const items     = ref([]);
const loading   = ref(false);
const saving    = ref(false);
const formOpen  = ref(false);
const editingId = ref(null);

// Silme onay modalı
const deleteTarget = ref(null);
const deleting     = ref(false);

const empty = () => ({ baslik: '', metin: '', aktif: true });
const form = reactive(empty());

const baslikLen = computed(() => (form.baslik || '').length);
const metinLen  = computed(() => (form.metin || '').length);

// ── Veri yükleme ──────────────────────────────────────────────────────────────

async function load() {
  loading.value = true;
  try {
    const { data } = await listIdleContents();
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
  formOpen.value = true;
}

function openEdit(item) {
  editingId.value = item.id;
  Object.assign(form, { baslik: item.baslik, metin: item.metin, aktif: item.aktif });
  formOpen.value = true;
}

function closeForm() { if (!saving.value) formOpen.value = false; }

// ── Kayıt ─────────────────────────────────────────────────────────────────────

function validate() {
  const baslik = (form.baslik || '').trim();
  const metin = (form.metin || '').trim();
  if (!baslik) { toast.warning('Başlık zorunludur.'); return null; }
  if (!metin)  { toast.warning('Metin zorunludur.'); return null; }
  if (baslik.length > BASLIK_MAX) { toast.warning(`Başlık en fazla ${BASLIK_MAX} karakter olabilir.`); return null; }
  if (metin.length > METIN_MAX)   { toast.warning(`Metin en fazla ${METIN_MAX} karakter olabilir.`); return null; }
  return { baslik, metin, aktif: form.aktif };
}

async function save() {
  const payload = validate();
  if (!payload) return;

  saving.value = true;
  try {
    if (editingId.value) {
      await updateIdleContent(editingId.value, payload);
      toast.success('İçerik güncellendi.');
    } else {
      await createIdleContent(payload);
      toast.success('İçerik oluşturuldu.');
    }
    formOpen.value = false;
    await load();
  } catch (e) {
    const err = e?.response?.data;
    const msg = err?.baslik?.[0] || err?.metin?.[0] || err?.detail || 'Kayıt başarısız.';
    toast.error(msg);
  } finally { saving.value = false; }
}

async function toggleActive(item) {
  const prev = item.aktif;
  item.aktif = !prev;
  try {
    await updateIdleContent(item.id, { aktif: item.aktif });
  } catch {
    item.aktif = prev;
    toast.error('Durum güncellenemedi.');
  }
}

// ── Silme ─────────────────────────────────────────────────────────────────────

function askDelete(item) { deleteTarget.value = item; }
function cancelDelete()  { if (!deleting.value) deleteTarget.value = null; }

async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteIdleContent(deleteTarget.value.id);
    toast.success('İçerik silindi.');
    deleteTarget.value = null;
    await load();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Silme başarısız.');
  } finally { deleting.value = false; }
}

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('tr-TR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return '—'; }
}
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
          Kiosk bekleme ekranında başlık ve metin olarak gösterilecek içerikler.
          Aktif içerikler rastgele sırayla görüntülenir.
        </p>

        <div v-if="loading" class="cm-loading">
          <i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor…
        </div>

        <table v-else class="eisa-table">
          <thead>
            <tr>
              <th>Başlık</th>
              <th>Metin</th>
              <th>Durum</th>
              <th>Son Güncelleme</th>
              <th class="actions-col"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!items.length">
              <td colspan="5" class="empty-row">Henüz içerik yok.</td>
            </tr>
            <tr v-for="item in items" :key="item.id">
              <td><span class="eisa-cell-name">{{ item.baslik }}</span></td>
              <td class="cell-muted cm-metin-cell">{{ item.metin }}</td>
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
              <td class="cell-muted">{{ fmtDate(item.updated_at) }}</td>
              <td>
                <div class="cell-actions">
                  <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(item)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="eisa-icon-btn danger" title="Sil" @click="askDelete(item)">
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
            <div class="cm-form-layout">
              <div class="cm-form-fields">
                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">
                    Başlık *
                    <span class="cm-counter" :class="{ over: baslikLen > BASLIK_MAX }">{{ baslikLen }}/{{ BASLIK_MAX }}</span>
                  </label>
                  <input
                    v-model="form.baslik"
                    class="eisa-field"
                    :maxlength="BASLIK_MAX"
                    placeholder="Örn. Güne Dengeli Bir Kahvaltıyla Başlayın"
                  />
                </div>

                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">
                    Metin *
                    <span class="cm-counter" :class="{ over: metinLen > METIN_MAX }">{{ metinLen }}/{{ METIN_MAX }}</span>
                  </label>
                  <textarea
                    v-model="form.metin"
                    class="eisa-field cm-textarea"
                    :maxlength="METIN_MAX"
                    rows="4"
                    placeholder="Kısa, bilgilendirici bir metin girin."
                  ></textarea>
                </div>

                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label eisa-checkbox-label">
                    <input type="checkbox" v-model="form.aktif" />
                    Aktif — kiosk bekleme ekranında gösterilsin
                  </label>
                </div>

                <div class="cm-note">
                  <i class="fa-solid fa-circle-info"></i>
                  Tanı, tedavi veya kesin sağlık sonucu ifade eden içerikler kullanmayın.
                </div>
              </div>

              <!-- 1080×1920 oranlı kiosk önizleme -->
              <div class="cm-preview-pane">
                <span class="cm-preview-label">Önizleme (1080×1920)</span>
                <div class="cm-kiosk-sim">
                  <div class="cm-kiosk-title">{{ form.baslik || 'Başlık' }}</div>
                  <div class="cm-kiosk-heart"><i class="fa-solid fa-heart-pulse"></i></div>
                  <div class="cm-kiosk-text">{{ form.metin || 'Metin buraya daktilo animasyonuyla yazılır.' }}</div>
                  <div class="cm-kiosk-cta">Size özel öneriler için <b>DOKUNUN</b></div>
                  <div class="cm-kiosk-sponsor">Bu alana sponsor olabilirsiniz</div>
                </div>
              </div>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="closeForm">İptal</button>
            <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="save">
              <i class="fa-solid" :class="saving ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i>
              {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Silme Onay Modalı -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="eisa-modal-backdrop" @click.self="cancelDelete">
        <div class="eisa-modal cm-confirm-modal">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">İçeriği Sil</h3>
            <button class="eisa-modal-close" @click="cancelDelete">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="eisa-modal-body">
            <p class="cm-confirm-text">
              <b>{{ deleteTarget.baslik }}</b> başlıklı içeriği silmek istediğinize emin misiniz?
              Bu işlem geri alınamaz.
            </p>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="cancelDelete">Vazgeç</button>
            <button class="eisa-btn eisa-btn-danger" :disabled="deleting" @click="confirmDelete">
              <i class="fa-solid" :class="deleting ? 'fa-spinner fa-spin' : 'fa-trash'"></i>
              {{ deleting ? 'Siliniyor…' : 'Sil' }}
            </button>
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

.cm-metin-cell { max-width: 420px; white-space: normal; }
.cm-pill-toggle { cursor: pointer; border: none; font-size: 0.75rem; }

.cm-form-modal { width: min(820px, 96vw); }
.cm-form-layout { display: flex; gap: 1.5rem; }
.cm-form-fields { flex: 1 1 auto; min-width: 0; }
.cm-preview-pane { flex: none; width: 160px; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.cm-preview-label { font-size: 0.7rem; color: var(--color-muted, #6b7280); }

.cm-counter { float: right; font-size: 0.7rem; color: var(--color-muted, #9ca3af); font-weight: 400; }
.cm-counter.over { color: #dc2626; font-weight: 700; }

.cm-textarea { resize: vertical; min-height: 90px; font-family: inherit; }

.cm-note {
  margin-top: 0.75rem;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.35);
  color: #92620a;
  font-size: 0.8rem;
  display: flex; align-items: flex-start; gap: 0.5rem;
}

/* 1080×1920 kiosk simülasyonu */
.cm-kiosk-sim {
  width: 160px;
  aspect-ratio: 9 / 16;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
  background: radial-gradient(120% 140% at 50% 0%, #1b2436 0%, #0f1622 55%, #0b1019 100%);
  display: flex; flex-direction: column; align-items: center;
  padding: 12px 8px; gap: 6px; text-align: center;
}
.cm-kiosk-title { color: #fff; font-weight: 800; font-size: 0.6rem; line-height: 1.15; margin-top: 6px; }
.cm-kiosk-heart { color: #B1121B; font-size: 1.4rem; margin: 4px 0; }
.cm-kiosk-text { color: #cfd6e4; font-size: 0.5rem; line-height: 1.2; flex: 1; }
.cm-kiosk-cta { color: #fff; font-size: 0.5rem; }
.cm-kiosk-cta b { color: #e0444c; }
.cm-kiosk-sponsor {
  color: #9aa3b2; font-size: 0.45rem; padding: 4px 8px;
  border: 1px solid rgba(255,255,255,.12); border-radius: 6px;
  background: rgba(17,24,39,.6); width: 100%;
}

.cm-confirm-modal { width: min(440px, 92vw); }
.cm-confirm-text { color: var(--color-text, #374151); font-size: 0.9rem; line-height: 1.5; }
</style>
