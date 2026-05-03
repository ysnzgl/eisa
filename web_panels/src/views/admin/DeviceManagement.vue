<script setup>
/**
 * Cihaz Yönetimi — Eczane Listesi + Kiosk İzleme Paneli
 * Modül 1: Süper Admin Device Management
 */
import { ref, computed, onMounted } from 'vue';
import {
  getPharmacies,
  createPharmacy,
  updatePharmacy,
  deletePharmacy,
  getKioskStatus,
} from '../../services/devices';

// ─── Veri ────────────────────────────────────────────────────────────────────
const pharmacies    = ref([]);
const kiosks        = ref([]);
const loadingPharm  = ref(true);
const loadingKiosk  = ref(true);
const pharmacySearch = ref('');

// ─── Modal state ─────────────────────────────────────────────────────────────
const modalOpen    = ref(false);
const modalMode    = ref('add');        // 'add' | 'edit'
const modalTarget  = ref(null);         // pharmacy being edited
const form         = ref({ name: '', province: '', district: '', owner: '' });
const formError    = ref('');
const saving       = ref(false);

const deleteModalOpen   = ref(false);
const deleteTarget      = ref(null);
const deleting          = ref(false);

// ─── Computed ─────────────────────────────────────────────────────────────────
const filteredPharmacies = computed(() => {
  const q = pharmacySearch.value.trim().toLowerCase();
  if (!q) return pharmacies.value;
  return pharmacies.value.filter((p) =>
    p.name.toLowerCase().includes(q)      ||
    p.province.toLowerCase().includes(q)  ||
    p.district.toLowerCase().includes(q)  ||
    p.owner.toLowerCase().includes(q)
  );
});

const onlineKiosks  = computed(() => kiosks.value.filter(isOnline));
const offlineKiosks = computed(() => kiosks.value.filter((k) => !isOnline(k)));

// ─── Helpers ─────────────────────────────────────────────────────────────────
function isOnline(kiosk) {
  const diffMin = (Date.now() - new Date(kiosk.lastPing).getTime()) / 60000;
  return diffMin <= 10;
}

function formatPing(iso) {
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (diffMin < 1)  return 'Az önce';
  if (diffMin < 60) return `${diffMin} dk önce`;
  const h = Math.floor(diffMin / 60);
  if (h < 24) return `${h} sa önce`;
  return `${Math.floor(h / 24)} gün önce`;
}

// ─── Veri Yükleme ─────────────────────────────────────────────────────────────
async function loadPharmacies() {
  loadingPharm.value = true;
  try   { pharmacies.value = await getPharmacies(); }
  finally { loadingPharm.value = false; }
}

async function loadKiosks() {
  loadingKiosk.value = true;
  try   { kiosks.value = await getKioskStatus(); }
  finally { loadingKiosk.value = false; }
}

onMounted(() => {
  loadPharmacies();
  loadKiosks();
});

// ─── CRUD Modal ───────────────────────────────────────────────────────────────
function openAdd() {
  form.value   = { name: '', province: '', district: '', owner: '' };
  formError.value = '';
  modalMode.value   = 'add';
  modalTarget.value = null;
  modalOpen.value   = true;
}

function openEdit(pharmacy) {
  form.value   = { name: pharmacy.name, province: pharmacy.province, district: pharmacy.district, owner: pharmacy.owner };
  formError.value = '';
  modalMode.value   = 'edit';
  modalTarget.value = pharmacy;
  modalOpen.value   = true;
}

function closeModal() {
  modalOpen.value = false;
}

async function saveForm() {
  const { name, province, district, owner } = form.value;
  if (!name.trim() || !province.trim() || !district.trim() || !owner.trim()) {
    formError.value = 'Tüm alanlar zorunludur.';
    return;
  }
  saving.value = true;
  formError.value = '';
  try {
    if (modalMode.value === 'add') {
      await createPharmacy({ name: name.trim(), province: province.trim(), district: district.trim(), owner: owner.trim() });
    } else {
      await updatePharmacy(modalTarget.value.id, { name: name.trim(), province: province.trim(), district: district.trim(), owner: owner.trim() });
    }
    await loadPharmacies();
    closeModal();
  } catch {
    formError.value = 'İşlem sırasında hata oluştu.';
  } finally {
    saving.value = false;
  }
}

// ─── Silme Modal ─────────────────────────────────────────────────────────────
function openDelete(pharmacy) {
  deleteTarget.value     = pharmacy;
  deleteModalOpen.value  = true;
}

function closeDelete() {
  deleteModalOpen.value = false;
  deleteTarget.value    = null;
}

async function confirmDelete() {
  deleting.value = true;
  try {
    await deletePharmacy(deleteTarget.value.id);
    await loadPharmacies();
    closeDelete();
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <div class="p-6 space-y-8 min-h-full">

    <!-- ── Sayfa Başlığı ─────────────────────────────────────────────────── -->
    <div class="flex items-start justify-between">
      <div>
        <div class="flex items-center gap-2 text-xs text-gray-400 mb-1 font-medium tracking-wide uppercase">
          <span>Süper Admin</span>
          <svg class="w-3 h-3" fill="none" viewBox="0 0 16 16"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span class="text-blue-600">Cihaz Yönetimi</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">Eczane & Kiosk Yönetimi</h1>
        <p class="text-sm text-gray-500 mt-0.5">Eczaneleri yönetin ve kioskların anlık durumunu izleyin.</p>
      </div>
      <button
        @click="() => { loadPharmacies(); loadKiosks(); }"
        class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg transition-colors duration-150"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5M4 9a9 9 0 0114.13-2.13M20 15A9 9 0 015.87 17.13"/>
        </svg>
        Yenile
      </button>
    </div>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!-- BÖLÜM 1: Eczane Listesi                                             -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <section class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <!-- Kart Başlığı -->
      <div class="px-6 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div>
            <h2 class="text-base font-semibold text-gray-800">Eczane Listesi</h2>
            <p class="text-xs text-gray-400">
              {{ loadingPharm ? '…' : `${pharmacies.length} eczane` }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <!-- Arama -->
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z"/>
            </svg>
            <input
              v-model="pharmacySearch"
              type="text"
              placeholder="Eczane ara…"
              class="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-44 transition"
            />
          </div>
          <!-- Yeni Ekle Butonu -->
          <button
            @click="openAdd"
            class="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-lg transition-colors duration-150 shadow-sm"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            Yeni Eczane
          </button>
        </div>
      </div>

      <!-- Tablo -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-100">
              <th class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Eczane Adı</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">İl</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">İlçe</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Eczane Sahibi</th>
              <th class="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Kiosk</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">İşlemler</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <!-- Yükleniyor -->
            <tr v-if="loadingPharm">
              <td colspan="6" class="px-6 py-10 text-center text-gray-400">
                <div class="flex items-center justify-center gap-2">
                  <svg class="animate-spin w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  <span class="text-sm">Yükleniyor…</span>
                </div>
              </td>
            </tr>
            <!-- Boş durum -->
            <tr v-else-if="filteredPharmacies.length === 0">
              <td colspan="6" class="px-6 py-12 text-center text-gray-400 text-sm">
                <svg class="w-8 h-8 mx-auto mb-2 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Sonuç bulunamadı.
              </td>
            </tr>
            <!-- Satırlar -->
            <tr
              v-else
              v-for="ph in filteredPharmacies"
              :key="ph.id"
              class="hover:bg-blue-50/40 transition-colors duration-100 group"
            >
              <td class="px-6 py-3.5 font-medium text-gray-800">{{ ph.name }}</td>
              <td class="px-4 py-3.5 text-gray-600">{{ ph.province }}</td>
              <td class="px-4 py-3.5 text-gray-600">{{ ph.district }}</td>
              <td class="px-4 py-3.5 text-gray-600">{{ ph.owner }}</td>
              <td class="px-4 py-3.5 text-center">
                <span class="inline-flex items-center justify-center w-6 h-6 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                  {{ ph.kioskCount }}
                </span>
              </td>
              <td class="px-4 py-3.5 text-right">
                <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                  <button
                    @click="openEdit(ph)"
                    title="Düzenle"
                    class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                    </svg>
                  </button>
                  <button
                    @click="openDelete(ph)"
                    title="Sil"
                    class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Tablo Footer: toplam sayı -->
      <div v-if="!loadingPharm && filteredPharmacies.length > 0" class="px-6 py-3 border-t border-gray-50 bg-gray-50/50 flex items-center justify-between text-xs text-gray-400">
        <span>{{ filteredPharmacies.length }} / {{ pharmacies.length }} eczane gösteriliyor</span>
        <span v-if="pharmacySearch">· Filtre: "{{ pharmacySearch }}"</span>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!-- BÖLÜM 2: Kiosk İzleme Paneli                                        -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <section class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <!-- Kart Başlığı -->
      <div class="px-6 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17H3a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-2"/>
            </svg>
          </div>
          <div>
            <h2 class="text-base font-semibold text-gray-800">Kiosk İzleme</h2>
            <p class="text-xs text-gray-400">
              {{ loadingKiosk ? '…' : `${kiosks.length} cihaz` }}
            </p>
          </div>
        </div>
        <!-- Durum özeti -->
        <div v-if="!loadingKiosk" class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 text-xs font-semibold px-3 py-1.5 rounded-full">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            {{ onlineKiosks.length }} Online
          </div>
          <div class="flex items-center gap-1.5 bg-red-50 text-red-600 text-xs font-semibold px-3 py-1.5 rounded-full">
            <span class="inline-flex rounded-full h-2 w-2 bg-red-400"></span>
            {{ offlineKiosks.length }} Offline
          </div>
        </div>
      </div>

      <!-- Grid -->
      <div class="p-6">
        <!-- Yükleniyor -->
        <div v-if="loadingKiosk" class="flex items-center justify-center py-10 text-gray-400">
          <svg class="animate-spin w-5 h-5 text-emerald-500 mr-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span class="text-sm">Kiosk durumları alınıyor…</span>
        </div>

        <!-- Kart Grid -->
        <div
          v-else
          class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
        >
          <div
            v-for="kiosk in kiosks"
            :key="kiosk.id"
            class="relative rounded-xl border bg-white overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200 kiosk-card"
            :class="isOnline(kiosk) ? 'border-emerald-200' : 'border-red-100'"
          >
            <!-- Durum şeridi (üst) -->
            <div
              class="h-1 w-full"
              :class="isOnline(kiosk) ? 'bg-emerald-400' : 'bg-red-400'"
            ></div>

            <div class="p-4">
              <!-- ID + Badge satırı -->
              <div class="flex items-start justify-between mb-2.5">
                <span class="font-mono text-sm font-bold text-gray-800 tracking-tight">{{ kiosk.id }}</span>
                <!-- Online/Offline rozeti -->
                <span
                  class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full"
                  :class="isOnline(kiosk)
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-red-100 text-red-600'"
                >
                  <span
                    class="inline-block w-1.5 h-1.5 rounded-full"
                    :class="isOnline(kiosk) ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'"
                  ></span>
                  {{ isOnline(kiosk) ? 'Online' : 'Offline' }}
                </span>
              </div>

              <!-- Eczane adı -->
              <div class="flex items-center gap-1.5 text-xs text-gray-500 mb-3 min-h-[2.5rem]">
                <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                <span class="leading-tight">{{ kiosk.pharmacyName }}</span>
              </div>

              <!-- Son senkronizasyon -->
              <div class="pt-2.5 border-t border-gray-50">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400">Son Ping</span>
                  <span
                    class="text-xs font-medium"
                    :class="isOnline(kiosk) ? 'text-emerald-600' : 'text-red-500'"
                  >
                    {{ formatPing(kiosk.lastPing) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Kiosk Footer -->
      <div v-if="!loadingKiosk" class="px-6 py-3 border-t border-gray-50 bg-gray-50/50 text-xs text-gray-400">
        Son güncelleme: az önce · 10 dakikadan eski ping → Offline
      </div>
    </section>

  </div><!-- /p-6 -->

  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!-- CRUD Modal: Eczane Ekle / Düzenle                                      -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="modalOpen"
        class="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="closeModal"
      >
        <Transition name="modal" appear>
          <div
            v-if="modalOpen"
            class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
          >
            <!-- Modal Başlık -->
            <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 class="text-base font-semibold text-gray-800">
                {{ modalMode === 'add' ? 'Yeni Eczane Ekle' : 'Eczane Düzenle' }}
              </h3>
              <button
                @click="closeModal"
                class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- Form -->
            <div class="px-6 py-5 space-y-4">
              <!-- Hata mesajı -->
              <div v-if="formError" class="flex items-center gap-2 bg-red-50 border border-red-100 text-red-600 text-sm px-3 py-2.5 rounded-lg">
                <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                {{ formError }}
              </div>

              <!-- Eczane Adı -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5">Eczane Adı <span class="text-red-400">*</span></label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Örn: Merkez Eczanesi"
                  class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>

              <!-- İl / İlçe -->
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1.5">İl <span class="text-red-400">*</span></label>
                  <input
                    v-model="form.province"
                    type="text"
                    placeholder="İstanbul"
                    class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1.5">İlçe <span class="text-red-400">*</span></label>
                  <input
                    v-model="form.district"
                    type="text"
                    placeholder="Kadıköy"
                    class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  />
                </div>
              </div>

              <!-- Eczane Sahibi -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5">Eczane Sahibi <span class="text-red-400">*</span></label>
                <input
                  v-model="form.owner"
                  type="text"
                  placeholder="Ad Soyad"
                  class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-2.5 bg-gray-50/50">
              <button
                @click="closeModal"
                :disabled="saving"
                class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition disabled:opacity-50"
              >
                İptal
              </button>
              <button
                @click="saveForm"
                :disabled="saving"
                class="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium px-4 py-2 rounded-lg transition shadow-sm"
              >
                <svg v-if="saving" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
                {{ saving ? 'Kaydediliyor…' : (modalMode === 'add' ? 'Ekle' : 'Güncelle') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!-- Silme Onay Modal                                                       -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="deleteModalOpen"
        class="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="closeDelete"
      >
        <Transition name="modal" appear>
          <div v-if="deleteModalOpen" class="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div class="p-6 text-center">
              <!-- İkon -->
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </div>
              <h3 class="text-base font-semibold text-gray-800 mb-1">Eczane Sil</h3>
              <p class="text-sm text-gray-500">
                <span class="font-medium text-gray-700">{{ deleteTarget?.name }}</span> eczanesini kalıcı olarak silmek istediğinizden emin misiniz?
              </p>
            </div>
            <div class="px-6 pb-5 flex gap-2.5">
              <button
                @click="closeDelete"
                :disabled="deleting"
                class="flex-1 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-200 hover:bg-gray-50 rounded-lg transition disabled:opacity-50"
              >
                Vazgeç
              </button>
              <button
                @click="confirmDelete"
                :disabled="deleting"
                class="flex-1 flex items-center justify-center gap-1.5 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm font-medium py-2 rounded-lg transition"
              >
                <svg v-if="deleting" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                {{ deleting ? 'Siliniyor…' : 'Evet, Sil' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ── Modal geçiş animasyonları ─────────────────────────────────────────────── */
.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

.modal-enter-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.94) translateY(8px);
}

/* ── Kiosk kart hover ──────────────────────────────────────────────────────── */
.kiosk-card {
  animation: fade-up 0.3s ease both;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
