<script setup>
/**
 * Campaigns — DOOH reklam kampanyası yönetim sayfası.
 * Kampanyaları listeler, oluşturur, günceller ve siler.
 * Targeting: şehir/ilçe, yaş aralığı, cinsiyet, tarih aralığı.
 */
import { ref, onMounted } from 'vue';
import { http } from '../../services/api';

const campaigns = ref([]);
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const toast = ref({ show: false, message: '', type: 'success' });

const showModal = ref(false);
const editingId = ref(null);

// Form alanları
const form = ref(emptyForm());

function emptyForm() {
  return {
    name: '',
    media_url: '',
    starts_at: '',
    ends_at: '',
    target_cities: '',
    target_districts: '',
    target_age_ranges: [],
    target_genders: [],
    is_active: true,
  };
}

const AGE_RANGES = ['0-17', '18-25', '26-35', '36-50', '51-65', '65+'];
const GENDERS = [{ value: 'F', label: 'Kadın' }, { value: 'M', label: 'Erkek' }, { value: 'O', label: 'Diğer' }];

// ── Veri çekme ──────────────────────────────────────────────
async function fetchCampaigns() {
  loading.value = true;
  try {
    const res = await http.get('/api/campaigns/');
    campaigns.value = Array.isArray(res.data) ? res.data : res.data.results ?? [];
  } catch {
    error.value = 'Kampanyalar yüklenemedi.';
  } finally {
    loading.value = false;
  }
}

onMounted(fetchCampaigns);

// ── Modal aç/kapat ───────────────────────────────────────────
function openCreate() {
  editingId.value = null;
  form.value = emptyForm();
  showModal.value = true;
}

function openEdit(campaign) {
  editingId.value = campaign.id;
  form.value = {
    name: campaign.name,
    media_url: campaign.media_url,
    starts_at: toDatetimeLocal(campaign.starts_at),
    ends_at: toDatetimeLocal(campaign.ends_at),
    target_cities: (campaign.target_cities ?? []).join(', '),
    target_districts: (campaign.target_districts ?? []).join(', '),
    target_age_ranges: [...(campaign.target_age_ranges ?? [])],
    target_genders: [...(campaign.target_genders ?? [])],
    is_active: campaign.is_active,
  };
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
}

// ── Kaydet (oluştur veya güncelle) ──────────────────────────
async function save() {
  saving.value = true;
  try {
    const payload = {
      name: form.value.name,
      media_url: form.value.media_url,
      starts_at: form.value.starts_at,
      ends_at: form.value.ends_at,
      target_cities: splitTrim(form.value.target_cities),
      target_districts: splitTrim(form.value.target_districts),
      target_age_ranges: form.value.target_age_ranges,
      target_genders: form.value.target_genders,
      is_active: form.value.is_active,
    };

    if (editingId.value) {
      await http.patch(`/api/campaigns/${editingId.value}/`, payload);
      showToast('Kampanya güncellendi', 'success');
    } else {
      await http.post('/api/campaigns/', payload);
      showToast('Kampanya oluşturuldu', 'success');
    }
    closeModal();
    await fetchCampaigns();
  } catch {
    showToast('Kayıt başarısız. Alanları kontrol edin.', 'error');
  } finally {
    saving.value = false;
  }
}

// ── Silme ────────────────────────────────────────────────────
async function deleteCampaign(id) {
  if (!confirm('Kampanyayı silmek istediğinize emin misiniz?')) return;
  try {
    await http.delete(`/api/campaigns/${id}/`);
    showToast('Kampanya silindi', 'success');
    await fetchCampaigns();
  } catch {
    showToast('Silme işlemi başarısız', 'error');
  }
}

// ── Aktif/Pasif toggle ───────────────────────────────────────
async function toggleActive(campaign) {
  try {
    await http.patch(`/api/campaigns/${campaign.id}/`, { is_active: !campaign.is_active });
    await fetchCampaigns();
  } catch {
    showToast('Durum değiştirilemedi', 'error');
  }
}

// ── Yardımcılar ──────────────────────────────────────────────
function showToast(message, type = 'success') {
  toast.value = { show: true, message, type };
  setTimeout(() => (toast.value.show = false), 3000);
}

function splitTrim(str) {
  return str.split(',').map(s => s.trim()).filter(Boolean);
}

function toDatetimeLocal(iso) {
  if (!iso) return '';
  return iso.replace('Z', '').replace('+00:00', '').slice(0, 16);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">📺 Kampanya Yönetimi</h1>
      <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition">
        + Yeni Kampanya
      </button>
    </div>

    <!-- Hata -->
    <div v-if="error" class="bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{{ error }}</div>

    <!-- Yükleniyor -->
    <div v-if="loading" class="text-gray-500 flex items-center gap-2">
      <svg class="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      Yükleniyor…
    </div>

    <!-- Kampanya Tablosu -->
    <div v-else class="bg-white rounded-xl shadow overflow-hidden">
      <div v-if="campaigns.length === 0" class="p-8 text-center text-gray-400">
        Henüz kampanya yok. Yeni bir kampanya ekleyin.
      </div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
          <tr>
            <th class="px-4 py-3 text-left">Kampanya Adı</th>
            <th class="px-4 py-3 text-left">Hedef Şehirler</th>
            <th class="px-4 py-3 text-left">Tarih Aralığı</th>
            <th class="px-4 py-3 text-center">Durum</th>
            <th class="px-4 py-3 text-right">İşlemler</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in campaigns" :key="c.id" class="border-t border-gray-100 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-800">{{ c.name }}</td>
            <td class="px-4 py-3 text-gray-600">
              {{ (c.target_cities ?? []).join(', ') || 'Tümü' }}
            </td>
            <td class="px-4 py-3 text-gray-600">
              {{ formatDate(c.starts_at) }} – {{ formatDate(c.ends_at) }}
            </td>
            <td class="px-4 py-3 text-center">
              <button
                @click="toggleActive(c)"
                :class="c.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                class="px-3 py-1 rounded-full text-xs font-semibold transition"
              >
                {{ c.is_active ? 'Aktif' : 'Pasif' }}
              </button>
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <button @click="openEdit(c)" class="text-blue-600 hover:underline text-xs">Düzenle</button>
              <button @click="deleteCampaign(c.id)" class="text-red-600 hover:underline text-xs">Sil</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Modal ─────────────────────────────────────────────── -->
    <div v-if="showModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b">
          <h2 class="text-lg font-bold text-gray-800">{{ editingId ? 'Kampanyayı Düzenle' : 'Yeni Kampanya' }}</h2>
        </div>
        <form @submit.prevent="save" class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Kampanya Adı *</label>
            <input v-model="form.name" required class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Medya URL *</label>
            <input v-model="form.media_url" required type="url" placeholder="https://..." class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Başlangıç *</label>
              <input v-model="form.starts_at" required type="datetime-local" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Bitiş *</label>
              <input v-model="form.ends_at" required type="datetime-local" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hedef Şehirler (virgülle ayır)</label>
            <input v-model="form.target_cities" placeholder="Diyarbakır, Şanlıurfa" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hedef İlçeler (virgülle ayır)</label>
            <input v-model="form.target_districts" placeholder="Merkez, Bağcılar" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Hedef Yaş Aralıkları</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="ar in AGE_RANGES" :key="ar" class="flex items-center gap-1 cursor-pointer text-sm">
                <input type="checkbox" :value="ar" v-model="form.target_age_ranges" class="accent-blue-600" />
                {{ ar }}
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Hedef Cinsiyet</label>
            <div class="flex gap-4">
              <label v-for="g in GENDERS" :key="g.value" class="flex items-center gap-1 cursor-pointer text-sm">
                <input type="checkbox" :value="g.value" v-model="form.target_genders" class="accent-blue-600" />
                {{ g.label }}
              </label>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" id="is_active" v-model="form.is_active" class="accent-blue-600 w-4 h-4" />
            <label for="is_active" class="text-sm font-medium text-gray-700">Kampanyayı aktif yap</label>
          </div>
          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="saving" class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white py-2 rounded-lg font-medium transition">
              {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
            </button>
            <button type="button" @click="closeModal" class="flex-1 border border-gray-300 hover:bg-gray-50 py-2 rounded-lg font-medium transition">
              İptal
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ── Toast bildirimi ───────────────────────────────────── -->
    <transition name="fade">
      <div
        v-if="toast.show"
        :class="toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'"
        class="fixed bottom-6 right-6 text-white px-5 py-3 rounded-xl shadow-lg font-medium z-50"
      >
        {{ toast.message }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
