<script setup>
/**
 * Etken Madde Yönetim Bileşeni
 * - Tüm etken maddeleri (aktif + pasif) listeler
 * - Ad alanında autocomplete (duplicate kontrolü)
 * - Yalnızca aktif filtre toggle (ikon buton)
 * - Ekleme / düzenleme / pasifleştirme / aktifleştirme
 */
import { ref, computed, onMounted } from "vue";
import {
  getAllIngredients,
  createIngredient,
  updateIngredient,
  softDeleteIngredient,
  reactivateIngredient,
} from "../../services/algorithm";

const emit = defineEmits(["close", "updated"]);

const allIngredients = ref([]);
const loading        = ref(true);
const error          = ref("");

const showActiveOnly = ref(false); // Tümü default

const form      = ref({ name: "", description: "" });
const editId    = ref(null);
const saving    = ref(false);
const formError = ref("");

const actionPending = ref(null);

const filteredIngredients = computed(() => {
  const query = form.value.name.trim().toLocaleLowerCase("tr");

  return allIngredients.value.filter((ingredient) => {
    const matchesActive = !showActiveOnly.value || ingredient.is_active;
    const matchesName = !query || ingredient.name.toLocaleLowerCase("tr").includes(query);
    return matchesActive && matchesName;
  });
});

const duplicateWarning = computed(() => {
  const q = form.value.name.trim().toLocaleLowerCase("tr");
  if (!q) return null;
  return allIngredients.value.find(
    (i) => i.name.toLocaleLowerCase("tr") === q && i.id !== editId.value,
  ) ?? null;
});

onMounted(fetchAll);

async function fetchAll() {
  loading.value = true;
  error.value   = "";
  try {
    allIngredients.value = await getAllIngredients();
  } catch {
    error.value = "Liste yüklenemedi.";
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  form.value      = { name: "", description: "" };
  editId.value    = null;
  formError.value = "";
}

function startEdit(ing) {
  form.value      = { name: ing.name, description: ing.description ?? "" };
  editId.value    = ing.id;
  formError.value = "";
}

async function save() {
  const trimmed = form.value.name.trim();
  if (!trimmed) { formError.value = "Ad zorunludur."; return; }
  if (duplicateWarning.value) {
    formError.value = '"' + duplicateWarning.value.name + '" adıyla zaten bir kayıt mevcut.';
    return;
  }
  saving.value    = true;
  formError.value = "";
  try {
    if (editId.value) {
      await updateIngredient(editId.value, { name: trimmed, description: form.value.description.trim() });
    } else {
      await createIngredient({ name: trimmed, description: form.value.description.trim() });
    }
    await fetchAll();
    resetForm();
    emit("updated");
  } catch {
    formError.value = "Kaydedilemedi. Tekrar deneyin.";
  } finally {
    saving.value = false;
  }
}

async function deactivate(ing) {
  actionPending.value = ing.id;
  error.value = "";
  try {
    await softDeleteIngredient(ing.id);
    const idx = allIngredients.value.findIndex((i) => i.id === ing.id);
    if (idx !== -1) allIngredients.value[idx] = { ...allIngredients.value[idx], is_active: false };
    if (editId.value === ing.id) resetForm();
    emit("updated");
  } catch {
    error.value = "Pasifleştirme başarısız.";
  } finally {
    actionPending.value = null;
  }
}

async function activate(ing) {
  actionPending.value = ing.id;
  error.value = "";
  try {
    const updated = await reactivateIngredient(ing.id);
    const idx = allIngredients.value.findIndex((i) => i.id === ing.id);
    if (idx !== -1) allIngredients.value[idx] = updated;
    emit("updated");
  } catch {
    error.value = "Aktifleştirme başarısız.";
  } finally {
    actionPending.value = null;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="ing-backdrop">
      <div class="ing-backdrop" @click.self="emit('close')">
        <Transition name="ing-modal" appear>
          <div class="ing-modal">

            <!-- Header -->
            <div class="ing-modal-header">
              <div>
                <p class="ing-modal-title">Etken Madde Yönetimi</p>
              </div>
              <button class="ing-icon-btn" @click="emit('close')" title="Kapat">
                <svg class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="ing-modal-body">

              <!-- Global error -->
              <div v-if="error" class="ing-error-banner">{{ error }}</div>

              <!-- Form row -->
              <div class="ing-form-row">

                <!-- Name + Autocomplete -->
                <div class="ing-field" style="flex:1 1 150px">
                  <label class="ing-label">Ad <span class="ing-req">*</span></label>
                  <div class="ing-ac-wrap">
                    <input
                      v-model="form.name"
                      type="text"
                      class="ing-input"
                      :class="{ 'ing-input--warn': duplicateWarning }"
                      placeholder="Örn: Magnezyum"
                      autocomplete="off"
                    />
                    <p v-if="duplicateWarning" class="ing-warn-text">
                      Zaten mevcut<span v-if="!duplicateWarning.is_active"> (pasif)</span>
                    </p>
                  </div>
                </div>

                <!-- Description -->
                <div class="ing-field" style="flex:1 1 150px">
                  <label class="ing-label">Açıklama</label>
                  <input v-model="form.description" type="text" class="ing-input" placeholder="Kısa açıklama (opsiyonel)" />
                </div>

                <!-- Action buttons -->
                <div class="ing-form-btns">
                  <button
                    class="ing-icon-btn"
                    :class="editId ? 'ing-icon-btn--save' : 'ing-icon-btn--add'"
                    :disabled="saving || !!duplicateWarning"
                    :title="editId ? 'Güncelle' : 'Ekle'"
                    @click="save"
                  >
                    <svg v-if="saving" class="w-icon spin" fill="none" viewBox="0 0 24 24">
                      <circle class="op25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                      <path class="op75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    <svg v-else-if="!editId" class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                    </svg>
                    <svg v-else class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                    </svg>
                  </button>
                  <button v-if="editId" class="ing-icon-btn" title="İptal" @click="resetForm">
                    <svg class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>

              <p v-if="formError" class="ing-form-error">{{ formError }}</p>

              <!-- List -->
              <div class="ing-list-card">
                <div class="ing-list-toolbar">
                  <span class="ing-list-count">
                    {{ filteredIngredients.length }} kayıt
                    <span v-if="!showActiveOnly" class="ing-list-count-muted">
                      ({{ allIngredients.filter(i => !i.is_active).length }} pasif)
                    </span>
                  </span>
                  <!-- Active-only filter icon button -->
                  <button
                    class="ing-icon-btn"
                    :class="showActiveOnly ? 'ing-icon-btn--filter-on' : ''"
                    :title="showActiveOnly ? 'Yalnız aktifler — tümünü göster' : 'Yalnız aktifleri göster'"
                    @click="showActiveOnly = !showActiveOnly"
                  >
                    <svg class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 9h10M11 14h2M11 19h2"/>
                    </svg>
                  </button>
                </div>

                <div v-if="loading">
                  <div v-for="n in 4" :key="n" class="ing-skeleton"></div>
                </div>
                <div v-else-if="!filteredIngredients.length" class="ing-empty">
                  <span v-if="showActiveOnly">Aktif etken madde yok.</span>
                  <span v-else>Henüz etken madde eklenmemiş.</span>
                </div>
                <div v-else>
                  <div
                    v-for="ing in filteredIngredients"
                    :key="ing.id"
                    class="ing-row"
                    :class="{ 'ing-row--editing': editId === ing.id, 'ing-row--passive': !ing.is_active }"
                  >
                    <span class="ing-dot" :class="ing.is_active ? 'ing-dot--on' : 'ing-dot--off'"></span>
                    <div class="ing-row-text">
                      <span class="ing-row-name">{{ ing.name }}</span>
                      <span class="ing-row-desc">{{ ing.description || "—" }}</span>
                    </div>
                    <span v-if="!ing.is_active" class="ing-passive-badge">Pasif</span>
                    <div class="ing-row-actions">
                      <button v-if="ing.is_active" class="ing-icon-btn ing-icon-btn--edit" title="Düzenle" @click="startEdit(ing)">
                        <svg class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                      </button>
                      <button v-if="ing.is_active" class="ing-icon-btn ing-icon-btn--deact" :disabled="actionPending === ing.id" title="Pasifleştir" @click="deactivate(ing)">
                        <svg v-if="actionPending === ing.id" class="w-icon spin" fill="none" viewBox="0 0 24 24">
                          <circle class="op25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                          <path class="op75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                        </svg>
                        <svg v-else class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                      </button>
                      <button v-if="!ing.is_active" class="ing-icon-btn ing-icon-btn--act" :disabled="actionPending === ing.id" title="Aktifleştir" @click="activate(ing)">
                        <svg v-if="actionPending === ing.id" class="w-icon spin" fill="none" viewBox="0 0 24 24">
                          <circle class="op25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                          <path class="op75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                        </svg>
                        <svg v-else class="w-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ing-backdrop {
  position: fixed; inset: 0;
  background: rgba(15,23,42,0.6);
  backdrop-filter: blur(4px);
  z-index: 60;
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.ing-modal {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 18px;
  box-shadow: 0 24px 64px -8px rgba(15,23,42,0.22);
  width: 100%; max-width: 680px;
  height: min(720px, 90vh);
  max-height: 90vh;
  display: flex; flex-direction: column; overflow: hidden;
}
.ing-modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #E5E3DF;
  flex-shrink: 0;
}
.ing-modal-title { font-size: .875rem; font-weight: 700; color: #111827; margin: 0; }
.ing-modal-sub   { font-size: .7rem; color: #9CA3AF; margin-top: 2px; }
.ing-modal-body {
  flex: 1;
  overflow: hidden;
  padding: 1.25rem;
  display: flex; flex-direction: column; gap: .875rem;
  min-height: 0;
}
.ing-error-banner {
  font-size: .8rem; color: #B91C1C;
  background: #FEF2F2; border: 1px solid #FECACA;
  padding: .5rem .75rem; border-radius: 8px;
}
/* Form */
.ing-form-row { display: flex; align-items: flex-end; gap: .625rem; flex-wrap: wrap; }
.ing-field { display: flex; flex-direction: column; gap: .3rem; min-width: 0; }
.ing-label {
  font-size: .68rem; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; color: #6B7280;
}
.ing-req { color: #DC2626; }
.ing-form-btns { display: flex; align-items: flex-end; gap: .3rem; padding-bottom: 1px; }
.ing-form-error { font-size: .75rem; color: #DC2626; margin-top: -.25rem; }
/* Input */
.ing-input {
  background: #FFFFFF; border: 1.5px solid #E5E3DF; border-radius: 8px;
  color: #111827; font-size: .8125rem; padding: .5rem .75rem;
  font-family: inherit; outline: none; width: 100%;
  transition: border-color .15s, box-shadow .15s;
  appearance: none; -webkit-appearance: none;
}
.ing-input::placeholder { color: #B6B2AB; }
.ing-input:focus { border-color: #2563EB; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.ing-input--warn { border-color: #F59E0B !important; box-shadow: 0 0 0 3px rgba(245,158,11,.12) !important; }
.ing-warn-text { font-size: .68rem; color: #B45309; margin-top: 2px; }
/* Icon button */
.ing-icon-btn {
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 8px; border: 1px solid #E5E3DF;
  background: #FFFFFF; color: #4B5563;
  cursor: pointer; transition: all .15s; flex-shrink: 0;
}
.ing-icon-btn:hover:not(:disabled) { background: #F4F3EF; color: #111827; border-color: #C7C4BD; }
.ing-icon-btn:disabled { opacity: .4; cursor: not-allowed; }
.ing-icon-btn--add {
  background: linear-gradient(135deg,#1E40AF,#2563EB);
  color: #fff; border-color: transparent;
  box-shadow: 0 2px 8px rgba(37,99,235,.3);
}
.ing-icon-btn--add:hover:not(:disabled) {
  background: linear-gradient(135deg,#1E3A8A,#1E40AF);
  box-shadow: 0 4px 12px rgba(37,99,235,.4);
}
.ing-icon-btn--save {
  background: #059669; color: #fff; border-color: transparent;
  box-shadow: 0 2px 8px rgba(5,150,105,.3);
}
.ing-icon-btn--save:hover:not(:disabled) { background: #047857; }
.ing-icon-btn--filter-on { background: #EFF6FF; color: #1D4ED8; border-color: #BFDBFE; }
.ing-icon-btn--edit:hover:not(:disabled)  { background: #EFF6FF; color: #2563EB; border-color: #BFDBFE; }
.ing-icon-btn--deact:hover:not(:disabled) { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }
.ing-icon-btn--act:hover:not(:disabled)   { background: #ECFDF5; color: #059669; border-color: #A7F3D0; }
/* List */
.ing-list-card {
  border: 1px solid #E5E3DF;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex: 1;
  flex-basis: 0;
  min-height: 0;
}
.ing-list-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: .5rem .75rem;
  background: #FAFAF9; border-bottom: 1px solid #E5E3DF;
  flex-shrink: 0;
}
.ing-list-count { font-size: .7rem; font-weight: 600; color: #6B7280; }
.ing-list-count-muted { font-weight: 400; color: #9CA3AF; }
.ing-list-card > div:last-child {
  overflow-y: auto;
  min-height: 0;
}
/* Skeleton */
.ing-skeleton {
  height: 44px; margin: 2px 0;
  background: linear-gradient(90deg,#F4F3EF 25%,#EDECE9 50%,#F4F3EF 75%);
  background-size: 200% 100%;
  animation: ing-shimmer 1.4s infinite;
}
@keyframes ing-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
/* Empty */
.ing-empty { padding: 2rem; text-align: center; font-size: .8rem; color: #9CA3AF; }
@media (max-width: 640px) {
  .ing-modal {
    height: min(640px, calc(100vh - 2rem));
  }
}
/* Row */
.ing-row {
  display: flex; align-items: center; gap: .625rem;
  padding: .55rem .75rem;
  border-bottom: 1px solid #F3F2EF;
  transition: background .12s;
}
.ing-row:last-child { border-bottom: none; }
.ing-row:hover { background: #FAFAF9; }
.ing-row--editing { background: #EFF6FF; }
.ing-row--passive { opacity: .6; }
.ing-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.ing-dot--on  { background: #10B981; }
.ing-dot--off { background: #D1D5DB; }
.ing-row-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.ing-row-name { font-size: .8125rem; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ing-row-desc { font-size: .7rem; color: #9CA3AF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ing-passive-badge {
  font-size: .65rem; font-weight: 700; padding: 1px 7px;
  border-radius: 999px; background: #F1F0EC; color: #6B7280;
  border: 1px solid #E5E3DF; flex-shrink: 0;
}
.ing-row-actions { display: flex; align-items: center; gap: 2px; opacity: 0; transition: opacity .15s; }
.ing-row:hover .ing-row-actions { opacity: 1; }
/* Helper classes for SVG spinner */
.w-icon { width: 14px; height: 14px; }
.op25 { opacity: .25; }
.op75 { opacity: .75; }
.spin { animation: ing-spin .8s linear infinite; }
@keyframes ing-spin { to { transform: rotate(360deg); } }
/* Transitions */
.ing-backdrop-enter-active, .ing-backdrop-leave-active { transition: opacity .2s ease; }
.ing-backdrop-enter-from,  .ing-backdrop-leave-to     { opacity: 0; }
.ing-modal-enter-active { transition: opacity .2s ease, transform .2s cubic-bezier(.34,1.56,.64,1); }
.ing-modal-leave-active { transition: opacity .15s ease, transform .15s ease; }
.ing-modal-enter-from,  .ing-modal-leave-to { opacity: 0; transform: scale(.96) translateY(6px); }
</style>
