<script setup>
/**
 * Danışma Kategorileri Yönetimi
 * Eczacıya danışın akışında gösterilecek kategorileri yönetir.
 * Her kategorinin alt kategorileri olabilir; soru/yaş/cinsiyet hedefleme yoktur.
 */
import { ref, computed, onMounted } from 'vue';
import {
  getDanismaKategorileri,
  createDanisma,
  updateDanisma,
  deleteDanisma,
} from '../../services/algorithm';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import CategoryTreeNav from '../../components/shared/CategoryTreeNav.vue';
import IconPickerPopup from '../../components/shared/IconPickerPopup.vue';

// ─── Veri ─────────────────────────────────────────────────────────────────────
const kategoriler  = ref([]);
const loadingCats  = ref(true);

// ─── Seçim ────────────────────────────────────────────────────────────────────
const selectedId   = ref(null);
const selectedItem = computed(() => kategoriler.value.find(c => c.id === selectedId.value));

function altKategoriler(parentId) {
  return kategoriler.value.filter(c => c.ust_kategori === parentId);
}

// ─── Yükleme ──────────────────────────────────────────────────────────────────
async function reload() {
  loadingCats.value = true;
  try {
    kategoriler.value = await getDanismaKategorileri();
    if (!selectedId.value && kategoriler.value.length) {
      selectedId.value = kategoriler.value[0].id;
    }
  } finally {
    loadingCats.value = false;
  }
}

onMounted(reload);

// ─── Kategori Modal ───────────────────────────────────────────────────────────
const catModalOpen  = ref(false);
const catModalMode  = ref('add');     // 'add' | 'edit'
const catTarget     = ref(null);
const EMPTY_CAT = () => ({ ad: '', ikon: 'fa-solid fa-comments', aktif: true, ust_kategori: null });
const catForm       = ref(EMPTY_CAT());
const catFormIsRoot = ref(true);
const catFormError  = ref('');
const catSaving     = ref(false);

function openAddCategory(ustKategoriId = null) {
  catForm.value      = { ...EMPTY_CAT(), ust_kategori: ustKategoriId };
  catFormIsRoot.value = ustKategoriId === null;
  catFormError.value = '';
  catModalMode.value = 'add';
  catTarget.value    = null;
  catModalOpen.value = true;
}

function openEditCategory(item) {
  catForm.value = {
    ad:           item.ad,
    ikon:         item.ikon || 'fa-solid fa-comments',
    aktif:        item.aktif,
    ust_kategori: item.ust_kategori ?? null,
  };
  catFormIsRoot.value = item.ust_kategori === null;
  catFormError.value  = '';
  catModalMode.value  = 'edit';
  catTarget.value     = item;
  catModalOpen.value  = true;
}

function closeCatModal() { catModalOpen.value = false; }

async function saveCategory() {
  if (!catForm.value.ad.trim()) { catFormError.value = 'Kategori adı zorunludur.'; return; }
  if (!catFormIsRoot.value && !catForm.value.ust_kategori) { catFormError.value = 'Üst kategori seçin veya "Ana Kategori" olarak işaretleyin.'; return; }
  if (catFormIsRoot.value) catForm.value.ust_kategori = null;
  catSaving.value    = true;
  catFormError.value = '';
  try {
    if (catModalMode.value === 'add') {
      const created = await createDanisma({ ...catForm.value });
      selectedId.value = created.id;
    } else {
      await updateDanisma(catTarget.value.id, { ...catForm.value });
    }
    await reload();
    closeCatModal();
  } catch { catFormError.value = 'Kategori kaydedilemedi.'; }
  finally { catSaving.value = false; }
}

// ─── Silme ────────────────────────────────────────────────────────────────────
const deleteOpen   = ref(false);
const deleteTarget = ref(null);
const deleting     = ref(false);

function confirmDelete(item) {
  deleteTarget.value = item;
  deleteOpen.value   = true;
}

async function onDeleteConfirm() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteDanisma(deleteTarget.value.id);
    if (selectedId.value === deleteTarget.value.id) selectedId.value = null;
    await reload();
    deleteOpen.value = false;
  } finally { deleting.value = false; }
}

// ─── İkon Seçici ─────────────────────────────────────────────────────────────
const iconPickerOpen = ref(false);
</script>

<template>
  <div class="medical-logic-root flex min-h-screen">

    <!-- ─── SOL RAIL ──────────────────────────────────────────────────────── -->
    <aside
      class="category-rail w-64 flex-shrink-0 flex flex-col border-r border-gray-200 sticky top-0 self-start"
      style="max-height: 100vh; overflow-y: auto;"
    >
      <div class="px-5 pt-6 pb-4 border-b border-gray-200">
        <p class="text-xs font-bold tracking-[0.15em] text-eisa-600 uppercase mb-1">Danışma Akışı</p>
        <h2 class="text-base font-semibold text-gray-900 leading-tight">Danışma Kategorileri</h2>
        <button
          @click="openAddCategory()"
          class="mt-3 w-full flex items-center justify-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-eisa-600 border border-gray-300 hover:border-eisa-600 rounded-lg py-1.5 transition"
        >
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Yeni Kategori
        </button>
      </div>

      <nav class="flex-1 px-3 py-3 space-y-1">
        <template v-if="loadingCats">
          <div v-for="n in 4" :key="n" class="h-14 bg-gray-100 rounded-xl animate-pulse mb-1.5"></div>
        </template>

        <CategoryTreeNav
          v-else
          :items="kategoriler"
          :selected-id="selectedId"
          @update:selected-id="selectedId = $event"
          parent-key="ust_kategori"
          label-key="ad"
          icon-key="ikon"
          active-key="aktif"
          default-icon="fa-solid fa-comments"
          accent="eisa"
          :collapsible="true"
          :show-edit-button="true"
          @edit="openEditCategory"
        >
          <template #empty>
            <i class="fa-solid fa-comments text-2xl mb-2 opacity-30 block"></i>
            Henüz danışma kategorisi yok.
          </template>
        </CategoryTreeNav>
      </nav>
    </aside>

    <!-- ─── ANA PANEL ─────────────────────────────────────────────────────── -->
    <main class="flex-1 overflow-y-auto flex flex-col">

      <!-- Header -->
      <div class="sticky top-0 z-10 main-header px-8 py-5 border-b border-gray-200 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-xl"><i :class="selectedItem?.ikon || 'fa-solid fa-comments'"></i></span>
            <h1 class="text-lg font-bold text-gray-900 tracking-tight">
              {{ selectedItem?.ad ?? 'Kategori seçin' }}
            </h1>
          </div>
          <p class="text-xs text-gray-500 font-mono" v-if="selectedItem">
            {{ altKategoriler(selectedItem.id).length }} alt kategori
          </p>
        </div>

        <div v-if="selectedItem" class="flex items-center gap-2">
          <button
            v-if="selectedItem.ust_kategori === null"
            @click="openAddCategory(selectedItem.id)"
            class="eisa-btn eisa-btn-cta text-sm"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            Alt Kategori Ekle
          </button>
          <button @click="openEditCategory(selectedItem)" class="eisa-btn text-sm">
            <i class="fa-solid fa-pencil"></i>
            Düzenle
          </button>
          <button
            @click="confirmDelete(selectedItem)"
            class="eisa-btn text-sm text-rose-600 border-rose-200 hover:bg-rose-50"
          >
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </div>

      <!-- İçerik -->
      <div class="flex-1 px-8 py-6 space-y-3">

        <!-- Kategori seçilmedi -->
        <div v-if="!selectedItem && !loadingCats"
          class="flex flex-col items-center justify-center h-64 text-gray-400"
        >
          <i class="fa-solid fa-comments text-4xl mb-3 opacity-30"></i>
          <p class="text-sm">Soldan bir kategori seçin</p>
        </div>

        <!-- Kök kategori → alt kategoriler -->
        <template v-else-if="selectedItem?.ust_kategori === null">
          <div v-if="altKategoriler(selectedItem.id).length === 0"
            class="flex flex-col items-center justify-center h-48 text-gray-500"
          >
            <i class="fa-solid fa-sitemap text-3xl mb-3 opacity-30"></i>
            <p class="text-sm mb-3">Bu ana kategoriye henüz alt kategori eklenmedi.</p>
            <button
              @click="openAddCategory(selectedItem.id)"
              class="text-eisa-600 text-sm hover:text-eisa-700 underline underline-offset-2"
            >Alt Kategori Ekle →</button>
          </div>

          <div v-else class="grid grid-cols-2 gap-3">
            <div
              v-for="alt in altKategoriler(selectedItem.id)"
              :key="alt.id"
              class="question-card rounded-xl border border-gray-200 px-4 py-3 flex items-center gap-3 group hover:border-eisa-200 transition cursor-pointer"
              @click="selectedId = alt.id"
            >
              <span class="w-9 h-9 flex items-center justify-center rounded-lg bg-eisa-50 text-eisa-600 flex-shrink-0">
                <i :class="alt.ikon || 'fa-solid fa-comments'" class="text-sm"></i>
              </span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-gray-800 truncate">{{ alt.ad }}</p>
                <code class="text-[10px] text-gray-400 font-mono">{{ alt.slug }}</code>
              </div>
              <span v-if="!alt.aktif" class="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-400 rounded font-bold flex-shrink-0">pasif</span>
              <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition" @click.stop>
                <button @click="openEditCategory(alt)" class="p-1.5 text-gray-400 hover:text-eisa-600 hover:bg-eisa-50 rounded transition" title="Düzenle">
                  <i class="fa-solid fa-pencil text-xs"></i>
                </button>
                <button @click="confirmDelete(alt)" class="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded transition" title="Sil">
                  <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- Alt kategori → bilgi -->
        <div v-else-if="selectedItem"
          class="flex flex-col items-center justify-center h-48 gap-3 rounded-2xl border border-eisa-100 bg-eisa-50 text-eisa-700"
        >
          <i class="fa-solid fa-comments text-3xl opacity-60"></i>
          <div class="text-center">
            <p class="text-sm font-semibold">Danışma Alt Kategorisi</p>
            <p class="text-xs text-eisa-600 mt-1">Kioskta "Eczacınıza Danışın" akışında gösterilir.</p>
            <p class="text-xs text-eisa-600 mt-1">
              Üst: <strong>{{ kategoriler.find(c => c.id === selectedItem.ust_kategori)?.ad }}</strong>
            </p>
          </div>
        </div>
      </div>
    </main>

    <!-- ─── Silme Onayı ───────────────────────────────────────────────────── -->
    <EisaDeleteConfirm
      v-if="deleteOpen"
      :name="deleteTarget?.ad ?? ''"
      :loading="deleting"
      @confirm="onDeleteConfirm"
      @cancel="deleteOpen = false"
    />
  </div>

  <!-- ─── KATEGORİ EKLE / DÜZENLE Modal ─────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="catModalOpen"
        class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
        @click.self="closeCatModal"
      >
        <Transition name="modal" appear>
          <div v-if="catModalOpen" class="question-modal w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl">

            <!-- Başlık -->
            <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-gray-900">
                {{ catModalMode === 'add' ? 'Yeni Danışma Kategorisi' : 'Kategori Düzenle' }}
              </h3>
              <button @click="closeCatModal" class="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- Form -->
            <div class="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div v-if="catFormError" class="text-sm text-rose-600 bg-rose-50 border border-rose-200 px-3 py-2.5 rounded-lg">
                {{ catFormError }}
              </div>

              <!-- Ad + İkon -->
              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2">
                  <label class="block text-xs font-semibold text-gray-600 mb-2">Kategori Adı <span class="text-rose-600">*</span></label>
                  <input
                    v-model="catForm.ad"
                    type="text"
                    placeholder="Örn: Kadın Sağlığı"
                    class="drawer-input w-full"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1.5">İkon Seç</label>
                  <button
                    type="button"
                    @click="iconPickerOpen = true"
                    class="drawer-input flex items-center gap-2"
                  >
                    <span class="w-6 h-6 flex items-center justify-center text-sm bg-eisa-50 rounded flex-shrink-0">
                      <i :class="catForm.ikon || 'fa-solid fa-comments'" class="text-eisa-600"></i>
                    </span>
                    <i class="fa-solid fa-grip text-gray-400 flex-shrink-0"></i>
                  </button>
                </div>
              </div>

              <!-- Ana Kategori Checkbox -->
              <div class="flex items-center gap-2.5 pt-1 pb-1 px-3 rounded-lg border"
                :class="catFormIsRoot ? 'border-eisa-200 bg-eisa-50' : 'border-gray-200 bg-gray-50'"
              >
                <input
                  id="danisma-is-root"
                  type="checkbox"
                  v-model="catFormIsRoot"
                  @change="catFormIsRoot && (catForm.ust_kategori = null)"
                  class="w-4 h-4 rounded border-gray-300 text-eisa-600 focus:ring-eisa-300 cursor-pointer"
                />
                <label for="danisma-is-root" class="flex-1 py-2 text-sm font-semibold cursor-pointer"
                  :class="catFormIsRoot ? 'text-eisa-700' : 'text-gray-700'"
                >Ana Kategori</label>
                <span class="text-[11px] text-gray-400">Başka bir kategoriye bağlı değil</span>
              </div>

              <!-- Üst Kategori (sadece alt kategori ise) -->
              <div v-if="!catFormIsRoot">
                <label class="block text-xs font-semibold text-gray-600 mb-2">
                  Üst Kategori <span class="text-rose-600">*</span>
                </label>
                <select v-model.number="catForm.ust_kategori" class="drawer-input w-full">
                  <option :value="null">— Seçin —</option>
                  <option
                    v-for="c in kategoriler.filter(c => c.ust_kategori === null && c.id !== catTarget?.id)"
                    :key="c.id"
                    :value="c.id"
                  >{{ c.ad }}</option>
                </select>
                <p class="mt-1 text-[10px] text-gray-500">Yalnızca ana kategoriler seçilebilir (tek seviye derinlik).</p>
              </div>

              <!-- Aktif -->
              <div class="flex items-center gap-2.5 pt-1">
                <input
                  id="danisma-aktif"
                  type="checkbox"
                  v-model="catForm.aktif"
                  class="w-4 h-4 rounded border-gray-300 text-eisa-600 focus:ring-eisa-300"
                />
                <label for="danisma-aktif" class="text-sm text-gray-700 cursor-pointer">
                  Aktif — kioskta göster
                </label>
              </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-2.5 bg-gray-50">
              <button @click="closeCatModal" :disabled="catSaving" class="eisa-btn disabled:opacity-50">İptal</button>
              <button @click="saveCategory" :disabled="catSaving" class="eisa-btn eisa-btn-cta disabled:opacity-60">
                <svg v-if="catSaving" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                {{ catSaving ? 'Kaydediliyor…' : (catModalMode === 'add' ? 'Oluştur' : 'Güncelle') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>

  <IconPickerPopup
    v-model="catForm.ikon"
    :open="iconPickerOpen"
    @update:open="iconPickerOpen = $event"
  />
</template>
