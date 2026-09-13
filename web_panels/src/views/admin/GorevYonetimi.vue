<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import { http } from '../../services/api';

const users = ref([]);
const items = ref([]);
const loading = ref(true);
const saving = ref(false);
const modalOpen = ref(false);
const selected = ref(null);
const filters = reactive({ q: '', durum: '' });

const statuses = [
  { value: 'YENI', label: 'Yeni' },
  { value: 'INCELENIYOR', label: 'İnceleniyor' },
  { value: 'YAPILDI', label: 'Yapıldı' },
  { value: 'YAPILMADI', label: 'Yapılmadı' },
];

const adminUsers = computed(() => users.value.filter((user) => user.rol === 'superadmin' && user.is_active));
const userOptions = computed(() => adminUsers.value.map((user) => ({ id: user.id, label: user.full_name || user.username, sub: user.email || user.username })));

const filteredItems = computed(() => {
  const query = filters.q.trim().toLowerCase();
  return items.value.filter((item) => {
    if (filters.durum && item.durum !== filters.durum) return false;
    if (!query) return true;
    return [item.baslik, item.icerik, item.durum_ad, item.atanan_kullanici_adi, item.olusturan_adi]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });
});

const listStats = computed(() => ({
  total: items.value.length,
  yeni: items.value.filter((item) => item.durum === 'YENI').length,
  inceleniyor: items.value.filter((item) => item.durum === 'INCELENIYOR').length,
}));

const emptyForm = () => ({ baslik: '', icerik: '', durum: 'YENI', atanan_kullanici_id: null });
const form = reactive(emptyForm());

function resetForm() {
  Object.assign(form, emptyForm());
  selected.value = null;
}

function openCreate() {
  resetForm();
  modalOpen.value = true;
}

function openEdit(item) {
  selected.value = item;
  Object.assign(form, {
    baslik: item.baslik,
    icerik: item.icerik,
    durum: item.durum,
    atanan_kullanici_id: item.atanan_kullanici_id,
  });
  modalOpen.value = true;
}

function closeModal() {
  modalOpen.value = false;
  resetForm();
}

async function loadData() {
  loading.value = true;
  try {
    const [{ data: taskData }, { data: userData }] = await Promise.all([
      http.get('/api/is-takip/gorevler/'),
      http.get('/api/users/'),
    ]);
    items.value = Array.isArray(taskData) ? taskData : (taskData.results ?? []);
    users.value = Array.isArray(userData) ? userData : (userData.results ?? []);
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!form.baslik.trim() || !form.icerik.trim()) {
    toast.error('Başlık ve içerik zorunludur.');
    return;
  }
  saving.value = true;
  try {
    const payload = {
      baslik: form.baslik.trim(),
      icerik: form.icerik.trim(),
      durum: form.durum,
      atanan_kullanici_id: form.atanan_kullanici_id,
    };
    if (selected.value) {
      await http.patch(`/api/is-takip/gorevler/${selected.value.id}/`, payload);
      toast.success('İş güncellendi.');
    } else {
      await http.post('/api/is-takip/gorevler/', payload);
      toast.success('İş oluşturuldu.');
    }
    await loadData();
    closeModal();
  } catch (error) {
    toast.error(error?.response?.data?.detail || 'İş kaydedilemedi.');
  } finally {
    saving.value = false;
  }
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}

const statusClass = {
  YENI: 'eisa-pill-info',
  INCELENIYOR: 'eisa-pill-warning',
  YAPILDI: 'eisa-pill-success',
  YAPILMADI: 'eisa-pill-muted',
};

onMounted(loadData);
</script>

<template>
  <div class="eisa-page gorev-page">
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">YÖNETİCİ / İŞ TAKİBİ</p>
        <h1 class="eisa-page-title">İş Takibi</h1>
        <p class="eisa-page-subtitle">Başlık, içerik, durum ve atanacak admin seçimiyle basit bir iç iş akışı.</p>
      </div>
      <button class="eisa-btn eisa-btn-cta" @click="openCreate">
        <i class="fa-solid fa-plus"></i> Yeni İş
      </button>
    </div>

    <section class="eisa-stats gorev-stats">
      <div class="eisa-stat-card"><span class="eisa-stat-label">Toplam</span><span class="eisa-stat-value">{{ listStats.total }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Yeni</span><span class="eisa-stat-value">{{ listStats.yeni }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">İnceleniyor</span><span class="eisa-stat-value">{{ listStats.inceleniyor }}</span></div>
    </section>

    <section class="eisa-panel toolbar-panel">
      <div class="eisa-toolbar">
        <div class="eisa-search-wrap">
          <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
          <input v-model="filters.q" class="eisa-field eisa-search-field" placeholder="Başlık, içerik, kişi veya durum ara..." />
        </div>
        <select v-model="filters.durum" class="eisa-field eisa-filter">
          <option value="">Tüm durumlar</option>
          <option v-for="status in statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
        </select>
      </div>
    </section>

    <section class="eisa-panel">
      <div v-if="loading" class="center-state">
        <i class="fa-solid fa-circle-notch fa-spin"></i>
      </div>

      <div v-else-if="!filteredItems.length" class="center-state empty-state">
        <i class="fa-solid fa-clipboard-list"></i>
        Uygun iş kaydı bulunamadı.
      </div>

      <div v-else class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Başlık</th>
              <th>Durum</th>
              <th>Atanan</th>
              <th>Oluşturan</th>
              <th>Oluşturma</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id" class="row-clickable" @click="openEdit(item)">
              <td>
                <strong>{{ item.baslik }}</strong>
                <div class="cell-muted cell-clamp">{{ item.icerik }}</div>
              </td>
              <td><span class="eisa-pill" :class="statusClass[item.durum]">{{ item.durum_ad }}</span></td>
              <td>{{ item.atanan_kullanici_adi || '—' }}</td>
              <td class="cell-muted">{{ item.olusturan_adi }}</td>
              <td class="cell-muted">{{ formatDate(item.olusturulma_tarihi) }}</td>
              <td class="row-actions" @click.stop>
                <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(item)"><i class="fa-solid fa-pen"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="modalOpen" class="eisa-modal-backdrop" @click.self="closeModal">
        <div class="eisa-modal gorev-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">{{ selected ? 'İşi Düzenle' : 'Yeni İş Oluştur' }}</h3>
              <p class="modal-subtitle">Yalnızca admin kullanıcıları atanabilir.</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="closeModal">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <form @submit.prevent="save">
            <div class="eisa-modal-body gorev-form">
              <label>
                <span class="eisa-field-label">Başlık</span>
                <input v-model="form.baslik" class="eisa-field" maxlength="200" required />
              </label>

              <label>
                <span class="eisa-field-label">İçerik</span>
                <textarea v-model="form.icerik" class="eisa-field" rows="6" maxlength="2000" required></textarea>
              </label>

              <div class="form-row">
                <label>
                  <span class="eisa-field-label">Durum</span>
                  <select v-model="form.durum" class="eisa-field">
                    <option v-for="status in statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
                  </select>
                </label>

                <label>
                  <span class="eisa-field-label">Yapacak kullanıcı</span>
                  <select v-model="form.atanan_kullanici_id" class="eisa-field">
                    <option :value="null">Seçilmedi</option>
                    <option v-for="user in userOptions" :key="user.id" :value="user.id">
                      {{ user.label }}<template v-if="user.sub"> · {{ user.sub }}</template>
                    </option>
                  </select>
                </label>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button type="button" class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="closeModal">İptal</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="saving">
                <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
                {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.gorev-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.gorev-stats {
  margin-bottom: 0.25rem;
}

.gorev-form :deep(.eisa-field) {
  min-height: 44px;
}

.gorev-form :deep(textarea.eisa-field) {
  min-height: 156px;
}

.center-state {
  padding: 3rem 1rem;
  text-align: center;
  color: #6b7280;
}

.center-state i {
  font-size: 1.4rem;
  margin-bottom: .5rem;
  display: block;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: .4rem;
}

.row-clickable {
  cursor: pointer;
}

.row-clickable:hover {
  background: #fafafa;
}

.cell-clamp {
  max-width: 46rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-actions {
  width: 56px;
}

.row-actions .eisa-icon-btn {
  width: 32px;
  height: 32px;
}

.gorev-form {
  display: flex;
  flex-direction: column;
  gap: .95rem;
}

.gorev-form label {
  display: flex;
  flex-direction: column;
  gap: .35rem;
}

.gorev-form textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .8rem;
}

.gorev-modal {
  width: calc(100vw - 2rem);
  max-width: 640px;
}

.gorev-panel-note {
  display: none;
}

@media (max-width: 900px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .gorev-stats {
    grid-template-columns: 1fr;
  }
}
</style>