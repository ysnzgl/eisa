<script setup>
/**
 * Kullanıcı Yönetimi (Admin)
 * — Listele, oluştur, düzenle, parola sıfırla, pasifleştir/aktifleştir.
 */
import { ref, computed, onMounted } from 'vue';
import {
  getUsers, createUser, updateUser,
  deactivateUser, activateUser, resetPassword,
} from '../../services/users';
import { getPharmacies } from '../../services/devices';
import { useToastStore } from '../../stores/toast';

const toast = useToastStore();
const users = ref([]);
const pharmacies = ref([]);
const loading = ref(false);
const search = ref('');
const filterRole = ref('all');
const filterStatus = ref('all');

const empty = () => ({
  id: null,
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  rol: 'pharmacist',
  eczane: null,
  password: '',
  is_active: true,
});

const showFormModal = ref(false);
const showResetModal = ref(false);
const editing = ref(empty());
const resetTarget = ref(null);
const newPassword = ref('');

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  return users.value.filter((u) => {
    if (filterRole.value !== 'all' && u.rol !== filterRole.value) return false;
    if (filterStatus.value === 'active' && !u.is_active) return false;
    if (filterStatus.value === 'inactive' && u.is_active) return false;
    if (!q) return true;
    return [u.username, u.email, u.first_name, u.last_name, u.eczane_detail?.ad]
      .filter(Boolean).some((v) => String(v).toLowerCase().includes(q));
  });
});

const stats = computed(() => ({
  total: users.value.length,
  active: users.value.filter((u) => u.is_active).length,
  admins: users.value.filter((u) => u.rol === 'superadmin').length,
  pharmacists: users.value.filter((u) => u.rol === 'pharmacist').length,
}));

async function load() {
  loading.value = true;
  try {
    const [u, p] = await Promise.all([getUsers(), getPharmacies().catch(() => [])]);
    users.value = u;
    pharmacies.value = p;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = empty();
  showFormModal.value = true;
}

function openEdit(u) {
  editing.value = {
    id: u.id,
    username: u.username,
    email: u.email ?? '',
    first_name: u.first_name ?? '',
    last_name: u.last_name ?? '',
    rol: u.rol,
    eczane: u.eczane,
    is_active: u.is_active,
    password: '',
  };
  showFormModal.value = true;
}

async function save() {
  const f = editing.value;
  if (!f.username.trim()) { toast.error('Kullanıcı adı zorunlu'); return; }
  if (!f.id && !f.password) { toast.error('Parola zorunlu'); return; }
  try {
    if (f.id) {
      const payload = {
        email: f.email, first_name: f.first_name, last_name: f.last_name,
        rol: f.rol, eczane: f.eczane, is_active: f.is_active,
      };
      await updateUser(f.id, payload);
      toast.success('Kullanıcı güncellendi');
    } else {
      await createUser({
        username: f.username,
        email: f.email,
        first_name: f.first_name,
        last_name: f.last_name,
        rol: f.rol,
        eczane: f.eczane,
        password: f.password,
        is_active: f.is_active,
      });
      toast.success('Kullanıcı oluşturuldu');
    }
    showFormModal.value = false;
    await load();
  } catch (e) { /* interceptor toast gösterir */ }
}

async function toggleActive(u) {
  try {
    if (u.is_active) {
      if (!confirm(`${u.username} pasifleştirilsin mi?`)) return;
      await deactivateUser(u.id);
      toast.success('Kullanıcı pasifleştirildi');
    } else {
      await activateUser(u.id);
      toast.success('Kullanıcı aktifleştirildi');
    }
    await load();
  } catch (e) { /* */ }
}

function openReset(u) {
  resetTarget.value = u;
  newPassword.value = '';
  showResetModal.value = true;
}

async function doReset() {
  if (!newPassword.value || newPassword.value.length < 6) {
    toast.error('Parola en az 6 karakter olmalı');
    return;
  }
  try {
    await resetPassword(resetTarget.value.id, newPassword.value);
    toast.success('Parola sıfırlandı');
    showResetModal.value = false;
  } catch (e) { /* */ }
}

function formatDate(d) {
  if (!d) return '—';
  try { return new Date(d).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return d; }
}

onMounted(load);
</script>

<template>
  <div class="eisa-page user-mgmt">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Yönetim</p>
        <h1 class="eisa-page-title">Kullanıcı Yönetimi</h1>
        <p class="eisa-page-subtitle">Eczaneye bağlı kullanıcıları oluştur, düzenle, parolayı sıfırla.</p>
      </div>
      <div class="header-actions">
        <button class="eisa-btn" @click="load" :disabled="loading">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i>
          Yenile
        </button>
        <button class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i>
          Yeni Kullanıcı
        </button>
      </div>
    </header>

    <section class="stats">
      <div class="stat-card"><span class="stat-label">Toplam</span><span class="stat-value">{{ stats.total }}</span></div>
      <div class="stat-card"><span class="stat-label">Aktif</span><span class="stat-value">{{ stats.active }}</span></div>
      <div class="stat-card"><span class="stat-label">Süper Admin</span><span class="stat-value">{{ stats.admins }}</span></div>
      <div class="stat-card"><span class="stat-label">Eczacı</span><span class="stat-value">{{ stats.pharmacists }}</span></div>
    </section>

    <section class="eisa-panel toolbar-panel">
      <div class="toolbar">
        <div class="search-wrap">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input
            v-model="search"
            class="eisa-field search-field"
            placeholder="Kullanıcı adı, e-posta, eczane ara..."
          />
        </div>
        <select v-model="filterRole" class="eisa-field filter">
          <option value="all">Tüm Roller</option>
          <option value="superadmin">Süper Admin</option>
          <option value="pharmacist">Eczacı</option>
        </select>
        <select v-model="filterStatus" class="eisa-field filter">
          <option value="all">Tüm Durumlar</option>
          <option value="active">Aktif</option>
          <option value="inactive">Pasif</option>
        </select>
      </div>
    </section>

    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Kullanıcılar ({{ filtered.length }})</h2>
      </div>
      <div class="table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Kullanıcı</th>
              <th>E-posta</th>
              <th>Rol</th>
              <th>Eczane</th>
              <th>Durum</th>
              <th>Son Giriş</th>
              <th class="actions-col">İşlem</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="7" class="empty-row">Yükleniyor...</td></tr>
            <tr v-else-if="!filtered.length"><td colspan="7" class="empty-row">Kayıt bulunamadı</td></tr>
            <tr v-for="u in filtered" :key="u.id">
              <td>
                <div class="user-cell">
                  <div class="avatar">{{ (u.first_name || u.username)[0]?.toUpperCase() }}</div>
                  <div>
                    <div class="user-name">{{ u.full_name || u.username }}</div>
                    <div class="user-handle">@{{ u.username }}</div>
                  </div>
                </div>
              </td>
              <td>{{ u.email || '—' }}</td>
              <td>
                <span class="eisa-pill" :class="u.rol === 'superadmin' ? 'eisa-pill-info' : 'eisa-pill-muted'">
                  {{ u.rol === 'superadmin' ? 'Admin' : 'Eczacı' }}
                </span>
              </td>
              <td>{{ u.eczane_detail?.ad || '—' }}</td>
              <td>
                <span class="eisa-pill" :class="u.is_active ? 'eisa-pill-success' : 'eisa-pill-danger'">
                  <i class="fa-solid" :class="u.is_active ? 'fa-circle-check' : 'fa-circle-xmark'"></i>
                  {{ u.is_active ? 'Aktif' : 'Pasif' }}
                </span>
              </td>
              <td class="muted">{{ formatDate(u.last_login) }}</td>
              <td class="actions">
                <button class="icon-btn" title="Düzenle" @click="openEdit(u)">
                  <i class="fa-solid fa-pen"></i>
                </button>
                <button class="icon-btn" title="Parola Sıfırla" @click="openReset(u)">
                  <i class="fa-solid fa-key"></i>
                </button>
                <button
                  class="icon-btn"
                  :class="u.is_active ? 'danger' : 'success'"
                  :title="u.is_active ? 'Pasifleştir' : 'Aktifleştir'"
                  @click="toggleActive(u)"
                >
                  <i class="fa-solid" :class="u.is_active ? 'fa-user-slash' : 'fa-user-check'"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Form Modal -->
    <div v-if="showFormModal" class="eisa-modal-backdrop" @click.self="showFormModal = false">
      <div class="eisa-modal" style="max-width: 540px;">
        <div class="eisa-modal-header">
          <h3 class="eisa-modal-title">{{ editing.id ? 'Kullanıcıyı Düzenle' : 'Yeni Kullanıcı' }}</h3>
          <button class="icon-btn" @click="showFormModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="eisa-modal-body">
          <div class="form-grid">
            <div class="form-row">
              <label class="eisa-field-label">Kullanıcı Adı *</label>
              <input v-model="editing.username" class="eisa-field" :disabled="!!editing.id" />
            </div>
            <div class="form-row">
              <label class="eisa-field-label">E-posta</label>
              <input v-model="editing.email" type="email" class="eisa-field" />
            </div>
            <div class="form-row">
              <label class="eisa-field-label">Ad</label>
              <input v-model="editing.first_name" class="eisa-field" />
            </div>
            <div class="form-row">
              <label class="eisa-field-label">Soyad</label>
              <input v-model="editing.last_name" class="eisa-field" />
            </div>
            <div class="form-row">
              <label class="eisa-field-label">Rol *</label>
              <select v-model="editing.rol" class="eisa-field">
                <option value="pharmacist">Eczacı</option>
                <option value="superadmin">Süper Admin</option>
              </select>
            </div>
            <div class="form-row">
              <label class="eisa-field-label">Eczane</label>
              <select v-model="editing.eczane" class="eisa-field" :disabled="editing.rol === 'superadmin'">
                <option :value="null">— Seçilmedi —</option>
                <option v-for="p in pharmacies" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div v-if="!editing.id" class="form-row form-row-full">
              <label class="eisa-field-label">Parola *</label>
              <input v-model="editing.password" type="password" class="eisa-field" placeholder="En az 6 karakter" />
            </div>
            <div class="form-row form-row-full toggle-row">
              <label class="toggle">
                <input type="checkbox" v-model="editing.is_active" />
                <span>Hesap aktif</span>
              </label>
            </div>
          </div>
        </div>
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" @click="showFormModal = false">Vazgeç</button>
          <button class="eisa-btn eisa-btn-cta" @click="save">
            <i class="fa-solid fa-check"></i>
            {{ editing.id ? 'Güncelle' : 'Oluştur' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Reset Password Modal -->
    <div v-if="showResetModal" class="eisa-modal-backdrop" @click.self="showResetModal = false">
      <div class="eisa-modal" style="max-width: 420px;">
        <div class="eisa-modal-header">
          <h3 class="eisa-modal-title">Parola Sıfırla</h3>
          <button class="icon-btn" @click="showResetModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="eisa-modal-body">
          <p class="reset-info">
            <strong>{{ resetTarget?.username }}</strong> kullanıcısı için yeni parola belirleyin.
          </p>
          <label class="eisa-field-label">Yeni Parola</label>
          <input
            v-model="newPassword"
            type="password"
            class="eisa-field"
            placeholder="En az 6 karakter"
            @keyup.enter="doReset"
          />
        </div>
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" @click="showResetModal = false">Vazgeç</button>
          <button class="eisa-btn eisa-btn-cta" @click="doReset">
            <i class="fa-solid fa-key"></i>
            Sıfırla
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
