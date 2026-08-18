<script setup>
/**
 * İçerik Yönetimi — kiosk bekleme (idle) ekranı için başlık/metin tabanlı içerik CRUD.
 * İçerikler AdPromo large görünümünde başlık fade + metin daktilo animasyonuyla
 * rastgele gösterilir. Medya/HTML yoktur; yalnızca düz metin.
 * 
 * Özellikler:
 * - Kategori ilişkilendirme
 * - Pagination ve filter
 * - Toplu silme
 * - Excel import (başlık + metin)
 */
import { ref, reactive, computed, onMounted } from 'vue';
import {
  listIdleContents, createIdleContent, updateIdleContent, deleteIdleContent,
  bulkDeleteIdleContents, listKategoriler,
} from '../../services/dooh';
import { toast } from 'vue-sonner';
import * as XLSX from 'xlsx';

const BASLIK_MAX = 100;
const METIN_MAX = 300;
const PAGE_SIZE = 15;

const items        = ref([]);
const kategoriler  = ref([]);
const loading      = ref(false);
const saving       = ref(false);
const formOpen     = ref(false);
const editingId    = ref(null);

// Pagination & Filter
const currentPage  = ref(1);
const searchQuery  = ref('');
const filterKategori = ref(null);
const filterAktif  = ref(null);

// Toplu silme
const selectedIds  = ref(new Set());
const bulkDeleting = ref(false);

// Excel import
const importOpen   = ref(false);
const importFile   = ref(null);
const importing    = ref(false);

// Silme onay modalı
const deleteTarget = ref(null);
const deleting     = ref(false);

const empty = () => ({ baslik: '', metin: '', aktif: true, kategori: null });
const form = reactive(empty());

const baslikLen = computed(() => (form.baslik || '').length);
const metinLen  = computed(() => (form.metin || '').length);

// ── Filtreleme & Pagination ───────────────────────────────────────────────────

const filteredItems = computed(() => {
  let result = items.value;
  
  // Arama
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    result = result.filter(i => 
      i.baslik.toLowerCase().includes(q) || i.metin.toLowerCase().includes(q)
    );
  }
  
  // Kategori filtresi
  if (filterKategori.value !== null) {
    result = result.filter(i => i.kategori === filterKategori.value);
  }
  
  // Aktif/Pasif filtresi
  if (filterAktif.value !== null) {
    result = result.filter(i => i.aktif === filterAktif.value);
  }
  
  return result;
});

const totalPages = computed(() => Math.ceil(filteredItems.value.length / PAGE_SIZE));

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return filteredItems.value.slice(start, start + PAGE_SIZE);
});

const allSelected = computed({
  get: () => paginatedItems.value.length > 0 && 
             paginatedItems.value.every(i => selectedIds.value.has(i.id)),
  set: (val) => {
    if (val) {
      paginatedItems.value.forEach(i => selectedIds.value.add(i.id));
    } else {
      paginatedItems.value.forEach(i => selectedIds.value.delete(i.id));
    }
  }
});

function clearFilters() {
  searchQuery.value = '';
  filterKategori.value = null;
  filterAktif.value = null;
  currentPage.value = 1;
}

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
}

function getKategoriAd(kategoriId) {
  if (!kategoriId) return '—';
  const kat = kategoriler.value.find(k => k.id === kategoriId);
  return kat?.ad || '—';
}

function getKategoriIkon(kategoriId) {
  if (!kategoriId) return null;
  const kat = kategoriler.value.find(k => k.id === kategoriId);
  return kat?.ikon || null;
}

// ── Veri yükleme ──────────────────────────────────────────────────────────────

async function loadKategoriler() {
  try {
    const { data } = await listKategoriler();
    kategoriler.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch {
    toast.error('Kategoriler yüklenemedi.');
  }
}

async function load() {
  loading.value = true;
  try {
    const { data } = await listIdleContents();
    items.value = Array.isArray(data) ? data : (data?.results ?? []);
    selectedIds.value.clear();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'İçerik listesi yüklenemedi.');
  } finally { loading.value = false; }
}

onMounted(async () => {
  await loadKategoriler();
  await load();
});

// ── Form aç/kapat ─────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null;
  Object.assign(form, empty());
  formOpen.value = true;
}

function openEdit(item) {
  editingId.value = item.id;
  Object.assign(form, { 
    baslik: item.baslik, 
    metin: item.metin, 
    aktif: item.aktif,
    kategori: item.kategori || null,
  });
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
  return { 
    baslik, 
    metin, 
    aktif: form.aktif,
    kategori: form.kategori || null,
  };
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
    const msg = err?.baslik?.[0] || err?.metin?.[0] || err?.kategori?.[0] || err?.detail || 'Kayıt başarısız.';
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
    selectedIds.value.delete(deleteTarget.value.id);
    deleteTarget.value = null;
    await load();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Silme başarısız.');
  } finally { deleting.value = false; }
}

// ── Toplu Silme ───────────────────────────────────────────────────────────────

async function bulkDelete() {
  if (selectedIds.value.size === 0) return;
  
  const count = selectedIds.value.size;
  if (!confirm(`Seçili ${count} içerik silinecek. Emin misiniz?`)) return;
  
  bulkDeleting.value = true;
  try {
    await bulkDeleteIdleContents(Array.from(selectedIds.value));
    toast.success(`${count} içerik silindi.`);
    selectedIds.value.clear();
    await load();
  } catch (e) {
    toast.error('Toplu silme başarısız.');
  } finally { bulkDeleting.value = false; }
}

// ── Excel Import ──────────────────────────────────────────────────────────────

function openImport() {
  importFile.value = null;
  importOpen.value = true;
}

function closeImport() {
  if (!importing.value) {
    importOpen.value = false;
    importFile.value = null;
  }
}

function handleFileSelect(event) {
  const file = event.target.files?.[0];
  if (file) importFile.value = file;
}

async function processImport() {
  if (!importFile.value) {
    toast.warning('Lütfen bir Excel dosyası seçin.');
    return;
  }
  
  importing.value = true;
  try {
    const data = await importFile.value.arrayBuffer();
    const workbook = XLSX.read(data);
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(sheet);
    
    if (!rows.length) {
      toast.warning('Excel dosyası boş.');
      importing.value = false;
      return;
    }
    
    // Sütun başlıklarını kontrol et (büyük/küçük harf duyarsız)
    const normalized = rows.map(row => {
      const obj = {};
      Object.keys(row).forEach(key => {
        const k = key.toLowerCase().trim();
        obj[k] = row[key];
      });
      return obj;
    });
    
    const valid = [];
    const errors = [];
    
    normalized.forEach((row, idx) => {
      const baslik = (row.baslik || row.başlık || '').toString().trim();
      const metin = (row.metin || '').toString().trim();
      
      if (!baslik || !metin) {
        errors.push(`Satır ${idx + 2}: Başlık veya metin boş.`);
        return;
      }
      
      if (baslik.length > BASLIK_MAX) {
        errors.push(`Satır ${idx + 2}: Başlık ${BASLIK_MAX} karakterden uzun.`);
        return;
      }
      
      if (metin.length > METIN_MAX) {
        errors.push(`Satır ${idx + 2}: Metin ${METIN_MAX} karakterden uzun.`);
        return;
      }
      
      valid.push({ baslik, metin, aktif: true });
    });
    
    if (errors.length) {
      toast.error(`${errors.length} satır hatalı:\n${errors.slice(0, 3).join('\n')}`);
      importing.value = false;
      return;
    }
    
    // Toplu kayıt
    for (const item of valid) {
      await createIdleContent(item);
    }
    
    toast.success(`${valid.length} içerik başarıyla içe aktarıldı.`);
    importOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e?.message || 'Excel işleme hatası.');
  } finally { importing.value = false; }
}

function downloadTemplate() {
  const template = [
    { baslik: 'Örnek Başlık 1', metin: 'Örnek metin içeriği buraya gelir.' },
    { baslik: 'Örnek Başlık 2', metin: 'Bir başka örnek metin.' },
  ];
  const ws = XLSX.utils.json_to_sheet(template);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'İçerikler');
  XLSX.writeFile(wb, 'icerik-sablonu.xlsx');
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
        <div class="cm-header-actions">
          <button class="eisa-btn eisa-btn-ghost" @click="openImport" title="Excel İçe Aktar">
            <i class="fa-solid fa-file-excel"></i> İçe Aktar
          </button>
          <button 
            v-if="selectedIds.size > 0" 
            class="eisa-btn eisa-btn-danger" 
            @click="bulkDelete"
            :disabled="bulkDeleting"
          >
            <i class="fa-solid" :class="bulkDeleting ? 'fa-spinner fa-spin' : 'fa-trash'"></i>
            {{ selectedIds.size }} Öğe Sil
          </button>
          <button class="eisa-btn eisa-btn-cta" @click="openCreate">
            <i class="fa-solid fa-plus"></i> Yeni İçerik
          </button>
        </div>
      </div>

      <div class="eisa-panel-body">
        <p class="cm-desc">
          Kiosk bekleme ekranında başlık ve metin olarak gösterilecek içerikler.
          Aktif içerikler rastgele sırayla görüntülenir.
        </p>

        <!-- Filter Bar -->
        <div class="cm-filter-bar">
          <div class="cm-filter-row">
            <input 
              v-model="searchQuery" 
              type="text" 
              class="eisa-field cm-search-field" 
              placeholder="Başlık veya metinde ara..."
            />
            <select v-model="filterKategori" class="eisa-field cm-filter-select">
              <option :value="null">Tüm Kategoriler</option>
              <option v-for="kat in kategoriler" :key="kat.id" :value="kat.id">
                {{ kat.ad }}
              </option>
            </select>
            <select v-model="filterAktif" class="eisa-field cm-filter-select">
              <option :value="null">Tümü</option>
              <option :value="true">Aktif</option>
              <option :value="false">Pasif</option>
            </select>
            <button class="eisa-btn eisa-btn-ghost" @click="clearFilters">
              <i class="fa-solid fa-filter-circle-xmark"></i> Temizle
            </button>
          </div>
          <div class="cm-filter-info">
            {{ filteredItems.length }} içerik {{ filteredItems.length !== items.length ? `(${items.length} toplam)` : '' }}
          </div>
        </div>

        <div v-if="loading" class="cm-loading">
          <i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor…
        </div>

        <table v-else class="eisa-table">
          <thead>
            <tr>
              <th class="cm-checkbox-col">
                <input type="checkbox" v-model="allSelected" />
              </th>
              <th>Başlık</th>
              <th>Kategori</th>
              <th>Metin</th>
              <th>Durum</th>
              <th>Güncelleme</th>
              <th class="actions-col"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!paginatedItems.length">
              <td colspan="7" class="empty-row">
                {{ filteredItems.length === 0 && searchQuery ? 'Sonuç bulunamadı.' : 'Henüz içerik yok.' }}
              </td>
            </tr>
            <tr v-for="item in paginatedItems" :key="item.id">
              <td>
                <input 
                  type="checkbox" 
                  :checked="selectedIds.has(item.id)"
                  @change="e => e.target.checked ? selectedIds.add(item.id) : selectedIds.delete(item.id)"
                />
              </td>
              <td><span class="eisa-cell-name">{{ item.baslik }}</span></td>
              <td class="cell-muted">
                <span v-if="item.kategori" class="cm-kategori-badge">
                  <i v-if="getKategoriIkon(item.kategori)" class="fa-solid" :class="getKategoriIkon(item.kategori)"></i>
                  {{ getKategoriAd(item.kategori) }}
                </span>
                <span v-else class="cm-no-kategori">—</span>
              </td>
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
              <td class="cell-muted cm-date-cell">{{ fmtDate(item.updated_at) }}</td>
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

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="cm-pagination">
          <button 
            class="cm-page-btn" 
            :disabled="currentPage === 1" 
            @click="goToPage(currentPage - 1)"
          >
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="cm-page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button 
            class="cm-page-btn" 
            :disabled="currentPage === totalPages" 
            @click="goToPage(currentPage + 1)"
          >
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
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
                  <label class="eisa-field-label">Kategori</label>
                  <select v-model="form.kategori" class="eisa-field">
                    <option :value="null">Kategori seçilmedi</option>
                    <option v-for="kat in kategoriler" :key="kat.id" :value="kat.id">
                      {{ kat.ad }}
                    </option>
                  </select>
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
                  <div v-if="form.kategori" class="cm-kiosk-icon">
                    <i class="fa-solid" :class="getKategoriIkon(form.kategori) || 'fa-heart'"></i>
                  </div>
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

    <!-- Excel Import Modal -->
    <Teleport to="body">
      <div v-if="importOpen" class="eisa-modal-backdrop" @click.self="closeImport">
        <div class="eisa-modal cm-import-modal">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">Excel İçe Aktar</h3>
            <button class="eisa-modal-close" @click="closeImport">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="eisa-modal-body">
            <div class="cm-import-info">
              <p><strong>Excel dosyanız şu sütunları içermelidir:</strong></p>
              <ul>
                <li><code>baslik</code> — İçerik başlığı (max 100 karakter)</li>
                <li><code>metin</code> — İçerik metni (max 300 karakter)</li>
              </ul>
              <p class="cm-import-note">
                <i class="fa-solid fa-circle-info"></i>
                Tüm içerikler aktif olarak oluşturulacaktır.
              </p>
            </div>
            
            <div class="cm-import-actions">
              <button class="eisa-btn eisa-btn-ghost" @click="downloadTemplate">
                <i class="fa-solid fa-download"></i> Şablon İndir
              </button>
              <label class="eisa-btn eisa-btn-primary cm-file-btn">
                <i class="fa-solid fa-file-arrow-up"></i>
                {{ importFile ? importFile.name : 'Dosya Seç' }}
                <input type="file" accept=".xlsx,.xls" @change="handleFileSelect" hidden />
              </label>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="closeImport">İptal</button>
            <button 
              class="eisa-btn eisa-btn-cta" 
              :disabled="!importFile || importing" 
              @click="processImport"
            >
              <i class="fa-solid" :class="importing ? 'fa-spinner fa-spin' : 'fa-upload'"></i>
              {{ importing ? 'İçe Aktarılıyor…' : 'İçe Aktar' }}
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
.cm-desc { color: var(--color-muted, #6b7280); font-size: 0.875rem; margin-bottom: 1rem; }
.cm-loading { padding: 2rem; text-align: center; color: var(--color-muted, #6b7280); }

.cm-header-actions { display: flex; gap: 0.5rem; align-items: center; }

/* Filter Bar */
.cm-filter-bar { 
  margin-bottom: 1rem; 
  padding: 1rem; 
  background: rgba(0,0,0,0.02); 
  border-radius: 8px; 
}
.cm-filter-row { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.5rem; }
.cm-search-field { flex: 1; min-width: 200px; }
.cm-filter-select { min-width: 160px; }
.cm-filter-info { font-size: 0.8rem; color: var(--color-muted, #6b7280); }

/* Table */
.cm-checkbox-col { width: 40px; text-align: center; }
.cm-metin-cell { max-width: 320px; white-space: normal; }
.cm-date-cell { font-size: 0.8rem; }
.cm-pill-toggle { cursor: pointer; border: none; font-size: 0.75rem; }

.cm-kategori-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  background: rgba(177, 18, 27, 0.08);
  color: #B1121B;
  font-size: 0.75rem;
  font-weight: 600;
}
.cm-no-kategori { color: #9ca3af; }

/* Pagination */
.cm-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(0,0,0,0.06);
}
.cm-page-btn {
  padding: 0.4rem 0.8rem;
  border: 1px solid rgba(0,0,0,0.15);
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.15s;
}
.cm-page-btn:hover:not(:disabled) { background: rgba(177,18,27,0.05); border-color: #B1121B; }
.cm-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.cm-page-info { font-size: 0.9rem; color: var(--color-muted, #6b7280); font-weight: 600; }

/* Form Modal */
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
.cm-kiosk-icon { color: #B1121B; font-size: 1.2rem; margin-top: 4px; }
.cm-kiosk-title { color: #fff; font-weight: 800; font-size: 0.6rem; line-height: 1.15; margin-top: 2px; }
.cm-kiosk-heart { color: #B1121B; font-size: 1.4rem; margin: 4px 0; }
.cm-kiosk-text { color: #cfd6e4; font-size: 0.5rem; line-height: 1.2; flex: 1; }
.cm-kiosk-cta { color: #fff; font-size: 0.5rem; }
.cm-kiosk-cta b { color: #e0444c; }
.cm-kiosk-sponsor {
  color: #9aa3b2; font-size: 0.45rem; padding: 4px 8px;
  border: 1px solid rgba(255,255,255,.12); border-radius: 6px;
  background: rgba(17,24,39,.6); width: 100%;
}

/* Import Modal */
.cm-import-modal { width: min(540px, 92vw); }
.cm-import-info { margin-bottom: 1.5rem; }
.cm-import-info p { margin-bottom: 0.5rem; line-height: 1.5; }
.cm-import-info ul { 
  margin: 0.75rem 0; 
  padding-left: 1.5rem; 
  list-style: disc; 
  line-height: 1.6;
}
.cm-import-info code {
  padding: 0.15rem 0.4rem;
  background: rgba(0,0,0,0.06);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  font-weight: 600;
  color: #B1121B;
}
.cm-import-note {
  margin-top: 1rem;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: #1e40af;
  font-size: 0.8rem;
  display: flex; align-items: flex-start; gap: 0.5rem;
}
.cm-import-actions { 
  display: flex; 
  gap: 0.75rem; 
  align-items: center; 
  justify-content: center; 
}
.cm-file-btn { cursor: pointer; }

/* Confirm Modal */
.cm-confirm-modal { width: min(440px, 92vw); }
.cm-confirm-text { color: var(--color-text, #374151); font-size: 0.9rem; line-height: 1.5; }
</style>
