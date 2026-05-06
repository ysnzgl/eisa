<script setup>
/**
 * Cihaz Yönetimi — Eczane Listesi + Kiosk İzleme Paneli
 * Modül 1: Süper Admin Device Management
 */
import { ref, computed, onMounted, watch } from 'vue';
import {
  getPharmacies,
  createPharmacy,
  updatePharmacy,
  deletePharmacy,
  getKioskStatus,
  createKiosk,
  deleteKiosk,
} from '../../services/devices';
import { getIller, getIlceler } from '../../services/lookups';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';

// ─── Lookups ──────────────────────────────────────────────────────────────────
const iller   = ref([]);
const ilceler = ref([]);
const ilcelerYukleniyor = ref(false);

async function loadIlceler(ilId) {
  if (!ilId) { ilceler.value = []; return; }
  ilcelerYukleniyor.value = true;
  try   { ilceler.value = await getIlceler(ilId); }
  finally { ilcelerYukleniyor.value = false; }
}

// ─── Veri ────────────────────────────────────────────────────────────────────
const pharmacies    = ref([]);
const kiosks        = ref([]);
const loadingPharm  = ref(true);
const loadingKiosk  = ref(true);
const pharmacySearch = ref('');

// ─── Eczane Modal ─────────────────────────────────────────────────────────────
const modalOpen    = ref(false);
const modalMode    = ref('add');        // 'add' | 'edit'
const modalTarget  = ref(null);

const EMPTY_FORM = () => ({
  name: '', il: '', ilce: '', adres: '', owner: '',
  telefon: '', eczaneKodu: '', isActive: true,
});
const form      = ref(EMPTY_FORM());
const formError = ref('');
const saving    = ref(false);

// İl değişince ilçeleri yeniden yükle
watch(() => form.value.il, (ilId) => {
  form.value.ilce = '';
  loadIlceler(ilId);
});

// ─── Kiosk Ekleme Modal ───────────────────────────────────────────────────────
const kioskModalOpen   = ref(false);
const kioskModalPharm  = ref(null);     // hangi eczaneye kiosk ekleniyor
const kioskForm        = ref({ mac: '' });
const kioskFormError   = ref('');
const kioskSaving      = ref(false);

// ─── Kiosk Silme ──────────────────────────────────────────────────────────────
const kioskDeleteTarget = ref(null);
const kioskDeleteOpen   = ref(false);
const kioskDeleting     = ref(false);

// ─── Eczane Silme Modal ───────────────────────────────────────────────────────
const deleteModalOpen   = ref(false);
const deleteTarget      = ref(null);
const deleting          = ref(false);

// ─── Computed ─────────────────────────────────────────────────────────────────
const filteredPharmacies = computed(() => {
  const q = pharmacySearch.value.trim().toLowerCase();
  if (!q) return pharmacies.value;
  return pharmacies.value.filter((p) =>
    p.name.toLowerCase().includes(q)      ||
    p.ilAdi.toLowerCase().includes(q)     ||
    p.ilceAdi.toLowerCase().includes(q)   ||
    p.owner.toLowerCase().includes(q)
  );
});

const onlineKiosks  = computed(() => kiosks.value.filter(isOnline));
const offlineKiosks = computed(() => kiosks.value.filter((k) => !isOnline(k)));

// ─── Helpers ─────────────────────────────────────────────────────────────────
function isOnline(kiosk) {
  if (!kiosk.lastPing) return false;
  const diffMin = (Date.now() - new Date(kiosk.lastPing).getTime()) / 60000;
  return diffMin <= 10;
}

function formatPing(iso) {
  if (!iso) return 'Hiç bağlanmadı';
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

onMounted(async () => {
  const [ils] = await Promise.all([getIller(), loadPharmacies(), loadKiosks()]);
  iller.value = ils;
});

// ─── Eczane CRUD Modal ────────────────────────────────────────────────────────
function openAdd() {
  form.value      = EMPTY_FORM();
  formError.value = '';
  modalMode.value   = 'add';
  modalTarget.value = null;
  ilceler.value     = [];
  modalOpen.value   = true;
}

function openEdit(pharmacy) {
  form.value = {
    name:       pharmacy.name,
    il:         pharmacy.il,
    ilce:       pharmacy.ilce,
    adres:      pharmacy.adres,
    owner:      pharmacy.owner,
    telefon:    pharmacy.telefon,
    eczaneKodu: pharmacy.eczaneKodu,
    isActive:   pharmacy.isActive,
  };
  formError.value   = '';
  modalMode.value   = 'edit';
  modalTarget.value = pharmacy;
  loadIlceler(pharmacy.il);
  modalOpen.value   = true;
}

function closeModal() { modalOpen.value = false; }

async function saveForm() {
  const { name, il, ilce, owner } = form.value;
  if (!name.trim() || !il || !ilce || !owner.trim()) {
    formError.value = 'Eczane adı, il, ilçe ve eczacı zorunludur.';
    return;
  }
  saving.value    = true;
  formError.value = '';
  try {
    if (modalMode.value === 'add') {
      await createPharmacy({ ...form.value });
    } else {
      await updatePharmacy(modalTarget.value.id, { ...form.value });
    }
    await loadPharmacies();
    closeModal();
  } catch {
    formError.value = 'İşlem sırasında hata oluştu.';
  } finally {
    saving.value = false;
  }
}

// ─── Eczane Silme Modal ───────────────────────────────────────────────────────
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

function openAddKiosk(pharmacy) {
  kioskModalPharm.value = pharmacy;
  kioskForm.value       = { mac: '' };
  kioskFormError.value  = '';
  kioskModalOpen.value  = true;
}

function closeKioskModal() { kioskModalOpen.value = false; }

async function saveKiosk() {
  const mac = kioskForm.value.mac.trim();
  if (!mac) { kioskFormError.value = 'MAC adresi zorunludur.'; return; }
  // Basic MAC validation
  if (!/^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/.test(mac)) {
    kioskFormError.value = 'Geçerli bir MAC adresi girin (örn: AA:BB:CC:DD:EE:FF).';
    return;
  }
  kioskSaving.value    = true;
  kioskFormError.value = '';
  try {
    await createKiosk({ pharmacyId: kioskModalPharm.value.id, mac });
    await Promise.all([loadKiosks(), loadPharmacies()]);
    closeKioskModal();
  } catch {
    kioskFormError.value = 'Kiosk eklenemedi. MAC adresi zaten kayıtlı olabilir.';
  } finally {
    kioskSaving.value = false;
  }
}

function openDeleteKiosk(kiosk) {
  kioskDeleteTarget.value = kiosk;
  kioskDeleteOpen.value   = true;
}

function closeDeleteKiosk() {
  kioskDeleteOpen.value   = false;
  kioskDeleteTarget.value = null;
}

async function confirmDeleteKiosk() {
  kioskDeleting.value = true;
  try {
    await deleteKiosk(kioskDeleteTarget.value.id);
    await Promise.all([loadKiosks(), loadPharmacies()]);
    closeDeleteKiosk();
  } finally {
    kioskDeleting.value = false;
  }
}
</script>

<template>
  <div class="eisa-page">

    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Süper Admin / Cihaz Yönetimi</p>
        <h1 class="eisa-page-title">Eczane &amp; Kiosk Yönetimi</h1>
        <p class="eisa-page-subtitle">Eczaneleri yönetin ve kioskların anlık durumunu izleyin.</p>
      </div>
      <div class="eisa-header-actions">
        <button
          class="eisa-btn eisa-btn-ghost"
          @click="() => { loadPharmacies(); loadKiosks(); }"
        >
          <i class="fa-solid fa-rotate-right"></i>
          Yenile
        </button>
      </div>
    </div>

   <div class="eisa-panel">
      <div class="eisa-panel-header">
        <div>
          <h2 class="eisa-panel-title">
            <i class="fa-solid fa-hospital" style="color:#2563EB;margin-right:0.4rem;"></i>
            Eczane Listesi
          </h2>
          <p class="eisa-stat-sub" style="margin-top:0.15rem;">
            {{ loadingPharm ? '…' : `${pharmacies.length} eczane kayıtlı` }}
          </p>
        </div>
        <div class="eisa-header-actions">
          <div class="eisa-search-wrap" style="min-width:200px;">
            <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
            <input
              id="pharmacy-search"
              name="pharmacySearch"
              v-model="pharmacySearch"
              type="search"
              placeholder="Eczane ara…"
              class="eisa-field eisa-search-field"
            />
          </div>
          <button class="eisa-btn eisa-btn-cta" @click="openAdd">
            <i class="fa-solid fa-plus"></i>
            Yeni Eczane
          </button>
        </div>
      </div>

      <div class="eisa-panel-body" style="padding:0;">
        <div style="overflow-x:auto;">
          <table class="eisa-table">
            <thead>
              <tr>
                <th>Eczane Adı</th>
                <th>İl</th>
                <th>İlçe</th>
                <th>Eczacı</th>
                <th>Telefon</th>
                <th style="text-align:center;">Kiosk</th>
                <th class="actions-col">İşlemler</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loadingPharm">
                <td colspan="7" class="empty-row">
                  <i class="fa-solid fa-circle-notch fa-spin" style="margin-right:0.5rem;color:#2563EB;"></i>
                  Yükleniyor…
                </td>
              </tr>
              <tr v-else-if="filteredPharmacies.length === 0">
                <td colspan="7" class="empty-row">
                  <i class="fa-regular fa-face-frown" style="display:block;font-size:1.75rem;margin-bottom:0.4rem;color:#D1D5DB;"></i>
                  Sonuç bulunamadı.
                </td>
              </tr>
              <tr v-else v-for="ph in filteredPharmacies" :key="ph.id">
                <td style="font-weight:600;">{{ ph.name }}</td>
                <td class="cell-muted">{{ ph.ilAdi }}</td>
                <td class="cell-muted">{{ ph.ilceAdi }}</td>
                <td class="cell-muted">{{ ph.owner }}</td>
                <td class="cell-muted">{{ ph.telefon || '—' }}</td>
                <td style="text-align:center;">
                  <span class="eisa-pill eisa-pill-info">{{ ph.kioskCount }}</span>
                </td>
                <td>
                  <div class="cell-actions">
                    <button
                      class="eisa-icon-btn"
                      title="Kiosk Ekle"
                      @click="openAddKiosk(ph)"
                    >
                      <i class="fa-solid fa-display"></i>
                    </button>
                    <button
                      class="eisa-icon-btn"
                      title="Düzenle"
                      @click="openEdit(ph)"
                    >
                      <i class="fa-solid fa-pen"></i>
                    </button>
                    <button
                      class="eisa-icon-btn"
                      title="Sil"
                      @click="openDelete(ph)"
                    >
                      <i class="fa-solid fa-trash" style="color:#EF4444;"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="!loadingPharm && filteredPharmacies.length > 0" class="eisa-panel-footer">
        <span>{{ filteredPharmacies.length }} / {{ pharmacies.length }} eczane gösteriliyor</span>
        <span v-if="pharmacySearch">· Filtre: "{{ pharmacySearch }}"</span>
      </div>
    </div>

  <div class="eisa-panel">
      <div class="eisa-panel-header">
        <div>
          <h2 class="eisa-panel-title">
            <i class="fa-solid fa-tv" style="color:#059669;margin-right:0.4rem;"></i>
            Kiosk İzleme
          </h2>
          <p class="eisa-stat-sub" style="margin-top:0.15rem;">
            {{ loadingKiosk ? '…' : `${kiosks.length} cihaz` }}
          </p>
        </div>
        <div v-if="!loadingKiosk" class="kiosk-summary">
          <span class="kiosk-summary-pill kiosk-summary-pill--online">
            <span class="eisa-kiosk-dot eisa-kiosk-dot--online"></span>
            {{ onlineKiosks.length }} Online
          </span>
          <span class="kiosk-summary-pill kiosk-summary-pill--offline">
            <span class="eisa-kiosk-dot eisa-kiosk-dot--offline"></span>
            {{ offlineKiosks.length }} Offline
          </span>
        </div>
      </div>

      <div class="eisa-panel-body">
        <div v-if="loadingKiosk" style="display:flex;align-items:center;gap:0.5rem;padding:3rem 0;justify-content:center;color:#6B7280;">
          <i class="fa-solid fa-circle-notch fa-spin" style="color:#059669;"></i>
          Kiosk durumları alınıyor…
        </div>

        <div v-else class="dm-kiosk-grid" style="padding:0;">
          <div
            v-for="kiosk in kiosks"
            :key="kiosk.id"
            class="eisa-kiosk-card"
            :class="isOnline(kiosk) ? 'eisa-kiosk-card--online' : 'eisa-kiosk-card--offline'"
          >
            <div
              class="eisa-kiosk-card-stripe"
              :class="isOnline(kiosk) ? 'eisa-kiosk-card-stripe--online' : 'eisa-kiosk-card-stripe--offline'"
            ></div>
            <div class="eisa-kiosk-card-body">
              <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:0.6rem;">
                <span style="font-family:'DM Mono',monospace;font-size:0.8rem;font-weight:700;color:#111827;">{{ kiosk.id }}</span>
                <span
                  class="eisa-kiosk-status"
                  :class="isOnline(kiosk) ? 'eisa-kiosk-status--online' : 'eisa-kiosk-status--offline'"
                >
                  <span
                    class="eisa-kiosk-dot"
                    :class="isOnline(kiosk) ? 'eisa-kiosk-dot--online' : 'eisa-kiosk-dot--offline'"
                  ></span>
                  {{ isOnline(kiosk) ? 'Online' : 'Offline' }}
                </span>
              </div>
              <p style="font-size:0.78rem;color:#6B7280;min-height:2rem;line-height:1.4;">
                <i class="fa-solid fa-hospital" style="margin-right:0.35rem;color:#9CA3AF;font-size:0.7rem;"></i>
                {{ kiosk.pharmacyName }}
              </p>
            </div>
            <div class="eisa-kiosk-card-footer">
              <div>
                <p style="font-size:0.65rem;color:#9CA3AF;margin-bottom:0.1rem;">Son Ping</p>
                <p
                  style="font-size:0.78rem;font-weight:600;"
                  :style="{ color: isOnline(kiosk) ? '#059669' : '#EF4444' }"
                >{{ formatPing(kiosk.lastPing) }}</p>
              </div>
              <button
                class="eisa-icon-btn"
                title="Kiosk'u Kaldır"
                @click="openDeleteKiosk(kiosk)"
              >
                <i class="fa-solid fa-trash" style="color:#EF4444;"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!loadingKiosk" class="eisa-panel-footer">
        <span>Son güncelleme: az önce</span>
        <span>10 dakikadan eski ping → Offline</span>
      </div>
    </div>

  </div><!-- /eisa-page -->

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- CRUD Modal: Eczane Ekle / Düzenle                                      -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="modalOpen"
        id="pharmacy-modal-backdrop"
        class="eisa-modal-backdrop"
        @click.self="closeModal"
      >
        <Transition name="modal" appear>
          <div v-if="modalOpen" id="pharmacy-modal" class="eisa-modal">
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">
                {{ modalMode === 'add' ? 'Yeni Eczane Ekle' : 'Eczane Düzenle' }}
              </h3>
              <button class="eisa-modal-close" @click="closeModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body">
              <div v-if="formError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ formError }}
              </div>

              <div class="eisa-form-grid">
                <!-- Eczane Adı -->
                <div class="eisa-form-row eisa-form-row-full">
                  <label for="ph-name" class="eisa-field-label">Eczane Adı <span style="color:#EF4444;">*</span></label>
                  <input
                    id="ph-name"
                    name="name"
                    v-model="form.name"
                    type="text"
                    placeholder="Örn: Merkez Eczanesi"
                    class="eisa-field"
                  />
                </div>

                <!-- İl -->
                <div class="eisa-form-row">
                  <label for="ph-il" class="eisa-field-label">İl <span style="color:#EF4444;">*</span></label>
                  <select id="ph-il" name="il" v-model="form.il" class="eisa-field">
                    <option value="">Seçiniz…</option>
                    <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad }}</option>
                  </select>
                </div>

                <!-- İlçe -->
                <div class="eisa-form-row">
                  <label for="ph-ilce" class="eisa-field-label">İlçe <span style="color:#EF4444;">*</span></label>
                  <select
                    id="ph-ilce"
                    name="ilce"
                    v-model="form.ilce"
                    :disabled="!form.il || ilcelerYukleniyor"
                    class="eisa-field"
                  >
                    <option value="">{{ ilcelerYukleniyor ? 'Yükleniyor…' : 'Seçiniz…' }}</option>
                    <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad }}</option>
                  </select>
                </div>

                <!-- Adres -->
                <div class="eisa-form-row eisa-form-row-full">
                  <label for="ph-adres" class="eisa-field-label">Adres</label>
                  <textarea
                    id="ph-adres"
                    name="adres"
                    v-model="form.adres"
                    rows="2"
                    placeholder="Sokak, mahalle, bina no…"
                    class="eisa-field"
                    style="resize:none;"
                  ></textarea>
                </div>

                <!-- Eczacı -->
                <div class="eisa-form-row">
                  <label for="ph-owner" class="eisa-field-label">Eczacı <span style="color:#EF4444;">*</span></label>
                  <input id="ph-owner" name="owner" v-model="form.owner" type="text" placeholder="Ad Soyad" class="eisa-field" />
                </div>

                <!-- Telefon -->
                <div class="eisa-form-row">
                  <label for="ph-telefon" class="eisa-field-label">Telefon</label>
                  <input id="ph-telefon" name="telefon" v-model="form.telefon" type="tel" placeholder="05xx xxx xx xx" class="eisa-field" />
                </div>

                <!-- Eczane Kodu -->
                <div class="eisa-form-row">
                  <label for="ph-kod" class="eisa-field-label">Eczane Kodu</label>
                  <input id="ph-kod" name="eczaneKodu" v-model="form.eczaneKodu" type="text" placeholder="ECZ-001" class="eisa-field" />
                </div>

                <!-- Aktif -->
                <div class="eisa-form-row eisa-toggle-row" style="justify-content:flex-end;padding-bottom:0.25rem;">
                  <label class="eisa-toggle">
                    <input id="ph-aktif" name="isActive" type="checkbox" v-model="form.isActive" />
                    Aktif
                  </label>
                </div>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="closeModal">İptal</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="saveForm">
                <i v-if="saving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-check"></i>
                {{ saving ? 'Kaydediliyor…' : (modalMode === 'add' ? 'Ekle' : 'Güncelle') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- Kiosk Ekle Modal                                                        -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="kioskModalOpen"
        id="kiosk-modal-backdrop"
        class="eisa-modal-backdrop"
        @click.self="closeKioskModal"
      >
        <Transition name="modal" appear>
          <div v-if="kioskModalOpen" id="kiosk-modal" class="eisa-modal" style="max-width:420px;">
            <div class="eisa-modal-header">
              <div>
                <h3 class="eisa-modal-title">Kiosk Ekle</h3>
                <p class="eisa-stat-sub">{{ kioskModalPharm?.name }}</p>
              </div>
              <button class="eisa-modal-close" @click="closeKioskModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="eisa-modal-body">
              <div v-if="kioskFormError" class="eisa-error-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                {{ kioskFormError }}
              </div>
              <div class="eisa-form-row">
                <label for="kiosk-mac" class="eisa-field-label">
                  MAC Adresi <span style="color:#EF4444;">*</span>
                </label>
                <input
                  id="kiosk-mac"
                  name="mac"
                  v-model="kioskForm.mac"
                  type="text"
                  placeholder="AA:BB:CC:DD:EE:FF"
                  class="eisa-field"
                  style="font-family:'DM Mono',monospace;"
                />
                <p style="margin-top:0.35rem;font-size:0.75rem;color:#6B7280;">Kiosk cihazının fiziksel MAC adresi</p>
              </div>
            </div>

            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" :disabled="kioskSaving" @click="closeKioskModal">İptal</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="kioskSaving" @click="saveKiosk">
                <i v-if="kioskSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-plus"></i>
                {{ kioskSaving ? 'Ekleniyor…' : 'Kiosk Ekle' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <!-- Kiosk Sil -->
  <EisaDeleteConfirm
    :open="kioskDeleteOpen"
    title="Kiosk'u Kaldır"
    :message="`${kioskDeleteTarget?.mac} MAC adresli kiosku kaldırmak istediğinizden emin misiniz?`"
    confirm-label="Evet, Kaldır"
    :loading="kioskDeleting"
    @confirm="confirmDeleteKiosk"
    @cancel="closeDeleteKiosk"
  />

  <!-- Eczane Sil -->
  <EisaDeleteConfirm
    :open="deleteModalOpen"
    title="Eczane Sil"
    :message="`${deleteTarget?.name} eczanesini kalıcı olarak silmek istediğinizden emin misiniz?`"
    confirm-label="Evet, Sil"
    :loading="deleting"
    @confirm="confirmDelete"
    @cancel="closeDelete"
  />
</template>

