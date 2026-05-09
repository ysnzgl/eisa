<script setup>
/**
 * Tıbbi Mantık Editörü — Algoritma & Karar Ağacı Yönetimi
 * Kategori → Soru → Eleme Kuralı hiyerarşisi
 */
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import {
  getCategories,
  createCategory,
  updateCategory,
  getQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  getActiveIngredients,
  addQuestionIngredient,
  removeQuestionIngredient,
} from '../../services/algorithm';
import { getCinsiyetler, getYasAraliklari } from '../../services/lookups';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import AlgorithmTargetBadges from '../../components/shared/AlgorithmTargetBadges.vue';
import CategoryCard from '../../components/shared/CategoryCard.vue';
import TargetGenderSelector from '../../components/shared/TargetGenderSelector.vue';
import IngredientManager from '../../components/shared/IngredientManager.vue';

//  Global Yükleme 
const categories   = ref([]);
const ingredients  = ref([]);
const cinsiyetler  = ref([]);
const yasAraliklari = ref([]);
const loadingCats  = ref(true);

//  Kategori CRUD 
const catModalOpen  = ref(false);
const catModalMode  = ref('add');        // 'add' | 'edit'
const catTarget     = ref(null);
const EMPTY_CAT = () => ({ name: '', icon: '', is_sensitive: false, target_gender: null, target_age_ranges: [] });
const catForm       = ref(EMPTY_CAT());
const catFormError  = ref('');
const catSaving     = ref(false);

function openAddCategory() {
  catForm.value    = EMPTY_CAT();
  catFormError.value = '';
  catModalMode.value = 'add';
  catTarget.value  = null;
  catModalOpen.value = true;
}

function openEditCategory(cat) {
  catForm.value = {
    name:             cat.name,
    icon:             cat.icon,
    is_sensitive:     cat.is_sensitive,
    target_gender:    cat.target_gender ?? null,
    target_age_ranges: [...(cat.target_age_ranges ?? [])],
  };
  catFormError.value = '';
  catModalMode.value = 'edit';
  catTarget.value    = cat;
  catModalOpen.value = true;
}

function closeCatModal() { catModalOpen.value = false; }

async function saveCategory() {
  if (!catForm.value.name.trim()) { catFormError.value = 'Kategori adı zorunludur.'; return; }
  catSaving.value    = true;
  catFormError.value = '';
  try {
    if (catModalMode.value === 'add') {
      await createCategory({ ...catForm.value });
    } else {
      await updateCategory(catTarget.value.id, { ...catForm.value });
    }
    const [cats] = await Promise.all([getCategories()]);
    categories.value = cats;
    closeCatModal();
  } catch { catFormError.value = 'Kategori kaydedilemedi.'; }
  finally { catSaving.value = false; }
}

function toggleCatAge(id) {
  const idx = catForm.value.target_age_ranges.indexOf(id);
  if (idx === -1) catForm.value.target_age_ranges.push(id);
  else catForm.value.target_age_ranges.splice(idx, 1);
}

//  Kategori Seçimi 
const activeCatId  = ref(null);
const activeCategory = computed(() => categories.value.find((c) => c.id === activeCatId.value));

//  Soru Yönetimi 
const questions        = ref([]);
const loadingQuestions = ref(false);
const expandedQId      = ref(null);      // Açık olan soru ID'si

// Soru CRUD
const qModalOpen  = ref(false);
const qModalMode  = ref('add');          // 'add' | 'edit'
const qForm       = ref({ text: '', order: 0, target_gender: null, target_age_ranges: [] });
const qTarget     = ref(null);
const qSaving     = ref(false);
const qFormError  = ref('');

const qDeleteOpen   = ref(false);
const qDeleteTarget = ref(null);
const qDeleting     = ref(false);

//  Etken Madde Yönetimi 
const qIngModalOpen = ref(false);
const qIngQuestion  = ref(null);
const qIngForm      = ref({ ingredient_id: null, role: 'ana' });
const qIngSaving    = ref(false);
const qIngError     = ref('');
const qIngDeleting  = ref(null);  // link id being deleted

const ingManageOpen = ref(false);

//  Yükleme 
onMounted(async () => {
  const [cats, ings, cins, yas] = await Promise.all([
    getCategories(), getActiveIngredients(), getCinsiyetler(), getYasAraliklari()
  ]);
  categories.value    = cats;
  ingredients.value   = ings;
  cinsiyetler.value   = cins;
  yasAraliklari.value = yas;
  loadingCats.value   = false;
  if (cats.length) selectCategory(cats[0].id);
});

async function selectCategory(id) {
  if (activeCatId.value === id) return;
  activeCatId.value  = id;
  expandedQId.value  = null;
  questions.value    = [];
  loadingQuestions.value = true;
  questions.value    = await getQuestions(id);
  loadingQuestions.value = false;
}

function toggleQuestion(id) {
  expandedQId.value = expandedQId.value === id ? null : id;
}

//  Soru CRUD 
function openAddQuestion() {
  qForm.value    = { text: '', order: questions.value.length, target_gender: null, target_age_ranges: [] };
  qFormError.value = '';
  qModalMode.value = 'add';
  qTarget.value    = null;
  qModalOpen.value = true;
}

function openEditQuestion(q) {
  qForm.value    = {
    text:              q.text,
    order:             q.order ?? 0,
    target_gender:     q.target_gender ?? null,
    target_age_ranges: [...(q.target_age_ranges ?? [])],
  };
  qFormError.value = '';
  qModalMode.value = 'edit';
  qTarget.value    = q;
  qModalOpen.value = true;
}

async function saveQuestion() {
  if (!qForm.value.text.trim()) { qFormError.value = 'Soru metni boş olamaz.'; return; }
  qSaving.value    = true;
  qFormError.value = '';
  try {
    const payload = {
      text:              qForm.value.text.trim(),
      order:             qForm.value.order,
      target_gender:     qForm.value.target_gender,
      target_age_ranges: qForm.value.target_age_ranges,
    };
    if (qModalMode.value === 'add') {
      const newQ = await createQuestion(activeCatId.value, payload);
      questions.value.push(newQ);
      expandedQId.value = newQ.id;
    } else {
      const updated = await updateQuestion(qTarget.value.id, payload);
      const idx = questions.value.findIndex((q) => q.id === updated.id);
      if (idx !== -1) questions.value[idx] = updated;
    }
    qModalOpen.value = false;
  } catch { qFormError.value = 'İşlem başarısız.'; }
  finally { qSaving.value = false; }
}

function toggleQAge(id) {
  const idx = qForm.value.target_age_ranges.indexOf(id);
  if (idx === -1) qForm.value.target_age_ranges.push(id);
  else qForm.value.target_age_ranges.splice(idx, 1);
}

function openDeleteQuestion(q) {
  qDeleteTarget.value = q;
  qDeleteOpen.value   = true;
}

async function confirmDeleteQuestion() {
  qDeleting.value = true;
  try {
    await deleteQuestion(qDeleteTarget.value.id);
    questions.value = questions.value.filter((q) => q.id !== qDeleteTarget.value.id);
    if (expandedQId.value === qDeleteTarget.value.id) expandedQId.value = null;
    qDeleteOpen.value = false;
  } finally { qDeleting.value = false; }
}

//  Etken Madde Yönetimi 
function openAddIngredient(question) {
  qIngQuestion.value = question;
  qIngForm.value     = { ingredient_id: null, role: 'ana' };
  qIngError.value    = '';
  qIngModalOpen.value = true;
}

async function saveQuestionIngredient() {
  if (!qIngForm.value.ingredient_id) { qIngError.value = 'Etken madde seçin.'; return; }
  qIngSaving.value = true;
  qIngError.value  = '';
  try {
    const link = await addQuestionIngredient(
      qIngQuestion.value.id,
      qIngForm.value.ingredient_id,
      qIngForm.value.role,
    );
    const idx = questions.value.findIndex((q) => q.id === qIngQuestion.value.id);
    if (idx !== -1) questions.value[idx].hedef_etken_maddeler.push(link);
    qIngModalOpen.value = false;
  } catch { qIngError.value = 'Eklenemedi.'; }
  finally { qIngSaving.value = false; }
}

async function removeQuestionIngredientLink(question, linkId) {
  qIngDeleting.value = linkId;
  try {
    await removeQuestionIngredient(linkId);
    const idx = questions.value.findIndex((q) => q.id === question.id);
    if (idx !== -1) {
      questions.value[idx].hedef_etken_maddeler =
        questions.value[idx].hedef_etken_maddeler.filter((e) => e.id !== linkId);
    }
  } finally { qIngDeleting.value = null; }
}

//  Helpers 
function ingredientName(id) {
  if (!id) return '—';
  return ingredients.value.find((i) => i.id === id)?.name ?? `#${id}`;
}

function openIngredientManager() {
  ingManageOpen.value = true;
}

async function onIngredientUpdated() {
  // Soru etken madde seçici dropdown'larını güncel tut
  ingredients.value = await getActiveIngredients();
}

function roleBadgeClass(role) {
  return role === 'ana'
    ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
    : 'bg-sky-50 text-sky-700 border border-sky-300';
}

//  İkon Seçici 
const iconPickerOpen = ref(false);
const HEALTH_ICONS = [
  { cls: 'fa-solid fa-pills',               label: 'İlaç'        },
  { cls: 'fa-solid fa-heart-pulse',         label: 'Kalp'        },
  { cls: 'fa-solid fa-lungs',               label: 'Akciğer'     },
  { cls: 'fa-solid fa-brain',               label: 'Beyin'       },
  { cls: 'fa-solid fa-tooth',               label: 'Diş'         },
  { cls: 'fa-solid fa-eye',                 label: 'Göz'         },
  { cls: 'fa-solid fa-ear-deaf',            label: 'Kulak'       },
  { cls: 'fa-solid fa-hand',                label: 'El/Ağrı'     },
  { cls: 'fa-solid fa-bone',                label: 'Kemik'       },
  { cls: 'fa-solid fa-virus',               label: 'Virüs'       },
  { cls: 'fa-solid fa-bacterium',           label: 'Bakteri'     },
  { cls: 'fa-solid fa-dumbbell',            label: 'Spor'        },
  { cls: 'fa-solid fa-leaf',                label: 'Bitkisel'    },
  { cls: 'fa-solid fa-spa',                 label: 'Cilt'        },
  { cls: 'fa-solid fa-sun',                 label: 'Güneş'      },
  { cls: 'fa-solid fa-moon',                label: 'Uyku'        },
  { cls: 'fa-solid fa-temperature-high',    label: 'Ateş'        },
  { cls: 'fa-solid fa-syringe',             label: 'Enjeksiyon'  },
  { cls: 'fa-solid fa-droplet',             label: 'Kan'         },
  { cls: 'fa-solid fa-stethoscope',         label: 'Stetoskop'   },
  { cls: 'fa-solid fa-bandage',             label: 'Yara'        },
  { cls: 'fa-solid fa-capsules',            label: 'Kapsül'      },
  { cls: 'fa-solid fa-microscope',          label: 'Lab'         },
  { cls: 'fa-solid fa-user-doctor',         label: 'Doktor'      },
  { cls: 'fa-solid fa-weight-scale',        label: 'Kilo'        },
  { cls: 'fa-solid fa-fire',                label: 'Enerji'      },
  { cls: 'fa-solid fa-wind',                label: 'Solunum'     },
  { cls: 'fa-solid fa-shield-heart',        label: 'Koruma'      },
  { cls: 'fa-solid fa-baby',                label: 'Bebek'       },
  { cls: 'fa-solid fa-person-walking',      label: 'Hareket'     },
  { cls: 'fa-solid fa-triangle-exclamation',label: 'Uyarı'       },
  { cls: 'fa-solid fa-circle-info',         label: 'Bilgi'       },
];
</script>

<template>
  <div id="medical-logic-root" class="medical-logic-root flex min-h-screen">

    <!--  LEFT RAIL: Kategoriler  -->
    <aside
      id="algorithm-sidebar"
      name="algorithm-sidebar"
      class="category-rail w-64 flex-shrink-0 flex flex-col border-r border-gray-200 sticky top-0 self-start"
      style="max-height: 100vh; overflow-y: auto;"
    >
      <div class="px-5 pt-6 pb-4 border-b border-gray-200">
        <p class="text-xs font-bold tracking-[0.15em] text-blue-600 uppercase mb-1">Şikayet Ağacı</p>
        <h2 class="text-base font-semibold text-gray-900 leading-tight">Kategoriler</h2>
        <button
          @click="openAddCategory"
          class="mt-3 w-full flex items-center justify-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-blue-700 border border-gray-300 hover:border-blue-500 rounded-lg py-1.5 transition"
        >
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
          Yeni Kategori
        </button>
      </div>

      <nav class="flex-1 px-3 py-3 space-y-1.5">
        <div
          v-if="loadingCats"
          v-for="n in 5"
          :key="n"
          class="h-14 bg-gray-100 rounded-xl animate-pulse"
        ></div>

        <CategoryCard
          v-for="cat in categories"
          :key="cat.id"
          :cat="cat"
          :active="activeCatId === cat.id"
          :cinsiyetler="cinsiyetler"
          @select="selectCategory"
          @edit="openEditCategory"
        />
      </nav>
    </aside>

    <!--  MAIN PANEL: Sorular  -->
    <main id="algorithm-main" name="algorithm-main" class="flex-1 overflow-y-auto flex flex-col">

      <!-- Header Bar -->
      <div id="algorithm-header" class="sticky top-0 z-10 main-header px-8 py-5 border-b border-gray-200 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-xl"><i :class="activeCategory?.icon || 'fa-solid fa-pills'"></i></span>
            <h1 class="text-lg font-bold text-gray-900 tracking-tight">
              {{ activeCategory?.name ?? 'Kategori seçin' }}
            </h1>
            <span
              v-if="activeCategory?.is_sensitive"
              class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-600 border border-rose-200 uppercase tracking-wider"
            >Hassas</span>
          </div>
          <p class="text-xs text-gray-500 font-mono" v-if="activeCategory">
            {{ questions.length }} soru
            — {{ questions.reduce((s, q) => s + q.hedef_etken_maddeler.length, 0) }} etken madde bağlantısı
          </p>
        </div>
        <div v-if="activeCategory" class="flex items-center gap-2">
          <button
            @click="openIngredientManager"
            class="eisa-btn text-sm"
          >
            <i class="fa-solid fa-capsules"></i>
            Etken Maddeler
          </button>
          <button
            @click="openAddQuestion"
            class="eisa-btn eisa-btn-cta text-sm"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            Soru Ekle
          </button>
        </div>
      </div>

      <!-- Sorular Listesi -->
      <div id="algorithm-questions-list" class="flex-1 px-8 py-6 space-y-3">

        <!-- Yükleniyor -->
        <div v-if="loadingQuestions" class="space-y-3">
          <div v-for="n in 3" :key="n" class="h-16 bg-gray-100 rounded-xl animate-pulse"></div>
        </div>

        <!-- Bo durum -->
        <div
          v-else-if="!activeCategory"
          class="flex flex-col items-center justify-center h-64 text-gray-400"
        >
          <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
          <p class="text-sm">Soldan bir kategori seçin</p>
        </div>

        <div
          v-else-if="questions.length === 0 && !loadingQuestions"
          class="flex flex-col items-center justify-center h-48 text-gray-500"
        >
          <p class="text-sm mb-3">Bu kategoride henüz soru yok.</p>
          <button @click="openAddQuestion" class="text-blue-600 text-sm hover:text-blue-700 underline underline-offset-2">İlk soruyu ekle →</button>
        </div>

        <!-- Soru Kartlar (Accordion) -->
        <div
          v-else
          v-for="(q, qi) in questions"
          :key="q.id"
          class="question-card rounded-xl border overflow-hidden transition-all duration-200"
          :class="expandedQId === q.id
            ? 'border-blue-400 shadow-lg shadow-blue-500/10'
            : 'border-gray-200 hover:border-gray-400'"
          :style="{ animationDelay: qi * 40 + 'ms' }"
        >
          <!-- Soru Balk Satr -->
          <div
            class="question-header flex items-center gap-3 px-5 py-4 cursor-pointer select-none group"
            :class="expandedQId === q.id ? 'bg-gray-50' : 'bg-white hover:bg-gray-50'"
            @click="toggleQuestion(q.id)"
          >
            <!-- Sıra numarası -->
            <span class="text-xs font-mono font-bold text-gray-500 w-5 text-center flex-shrink-0">{{ q.order }}</span>

            <!-- Soru metni -->
            <p class="flex-1 text-sm font-medium text-gray-800 leading-snug">{{ q.text }}</p>

            <!-- Sağ taraf meta -->
            <div class="flex items-center gap-2 flex-shrink-0">            
              <!-- Hedefleme badge'leri -->
              <AlgorithmTargetBadges
                :target-gender="q.target_gender"
                :target-age-ranges="q.target_age_ranges"
                :ingredient-count="q.hedef_etken_maddeler.length"
                :cinsiyetler="cinsiyetler"
              />
              <!-- Düzenle / Sil -->
              <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                <button
                  @click="openEditQuestion(q)"
                  class="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition"
                  title="Düzenle"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button
                  @click="openDeleteQuestion(q)"
                  class="p-1.5 text-gray-500 hover:text-rose-600 hover:bg-rose-50 rounded transition"
                  title="Sil"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
              <!-- Chevron -->
              <svg
                class="w-4 h-4 text-gray-500 transition-transform duration-200 ml-1"
                :class="expandedQId === q.id ? 'rotate-180' : ''"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
          </div>

              <!-- Accordion Body: Etken Maddeler -->
          <Transition name="accordion">
            <div v-if="expandedQId === q.id" class="rules-body border-t border-gray-200 bg-gray-50">
              <div class="px-5 py-4">

                <!-- Başlık -->
                <div class="flex items-center justify-between mb-3">
                  <h3 class="text-xs font-bold tracking-[0.12em] text-gray-600 uppercase">Etken Maddeler</h3>
                  <button
                    @click="openAddIngredient(q)"
                    class="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2.5 py-1 rounded-md transition"
                  >
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                    </svg>
                    Etken Madde Ekle
                  </button>
                </div>

                <!-- Etken Madde Listesi -->
                <div v-if="q.hedef_etken_maddeler.length === 0" class="text-center py-5 text-gray-500 text-xs">
                  Bu soruya henüz etken madde eklenmemiş.
                </div>

                <div v-else class="space-y-2">
                  <div
                    v-for="em in q.hedef_etken_maddeler"
                    :key="em.id"
                    class="rule-row flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3 group/em hover:border-gray-300 transition"
                  >
                    <span
                      class="text-xs font-semibold px-2 py-0.5 rounded"
                      :class="roleBadgeClass(em.role)"
                    >
                      {{ em.role === 'ana' ? 'Ana' : 'Destekleyici' }}
                    </span>
                    <span class="flex-1 text-sm text-gray-800 font-medium">{{ em.ingredient_name }}</span>
                    <button
                      @click="removeQuestionIngredientLink(q, em.id)"
                      :disabled="qIngDeleting === em.id"
                      class="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded transition disabled:opacity-40 opacity-0 group-hover/em:opacity-100"
                      title="Bağlantıyı Sil"
                    >
                      <svg v-if="qIngDeleting === em.id" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                      </svg>
                      <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </main>

    <!--  -->
    <!-- Etken Madde Yönetim Bileşeni                                         -->
    <!--  -->
    <IngredientManager
      v-if="ingManageOpen"
      @close="ingManageOpen = false"
      @updated="onIngredientUpdated"
    />

    <!--  -->
    <!-- Etken Madde Ekle Mini Modal                                          -->
    <!--  -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div
          v-if="qIngModalOpen"
          class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          @click.self="qIngModalOpen = false"
        >
          <Transition name="modal" appear>
            <div v-if="qIngModalOpen" class="question-modal w-full max-w-md rounded-2xl overflow-hidden shadow-2xl">
              <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-bold text-gray-900">Etken Madde Ekle</h3>
                  <p class="text-xs text-gray-500 mt-0.5 line-clamp-1">{{ qIngQuestion?.text }}</p>
                </div>
                <button @click="qIngModalOpen = false" class="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
              <div class="px-6 py-5 space-y-4">
                <div v-if="qIngError" class="text-sm text-rose-600 bg-rose-50 border border-rose-200 px-3 py-2.5 rounded-lg">{{ qIngError }}</div>
                <div>
                  <label class="drawer-label mb-2 block">Etken Madde <span class="text-rose-600">*</span></label>
                  <select v-model.number="qIngForm.ingredient_id" class="drawer-input w-full">
                    <option :value="null" disabled>— Seçin —</option>
                    <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">{{ ing.name }}</option>
                  </select>
                </div>
                <div>
                  <label class="drawer-label mb-2 block">Rol</label>
                  <div class="grid grid-cols-2 gap-2">
                    <button
                      v-for="opt in [{ v: 'ana', l: 'Ana' }, { v: 'destekleyici', l: 'Destekleyici' }]"
                      :key="opt.v"
                      type="button"
                      @click="qIngForm.role = opt.v"
                      class="py-2.5 rounded-lg border text-sm font-semibold transition"
                      :class="qIngForm.role === opt.v
                        ? 'bg-blue-100 border-blue-500 text-blue-800'
                        : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'"
                    >{{ opt.l }}</button>
                  </div>
                </div>
              </div>
              <div class="px-6 py-4 border-t border-gray-200 flex gap-2.5">
                <button @click="qIngModalOpen = false" :disabled="qIngSaving" class="eisa-btn flex-1 disabled:opacity-50">İptal</button>
                <button @click="saveQuestionIngredient" :disabled="qIngSaving" class="eisa-btn eisa-btn-cta flex-1 disabled:opacity-60">
                  <svg v-if="qIngSaving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  {{ qIngSaving ? 'Ekleniyor…' : 'Ekle' }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!--  -->
    <!-- Soru Ekle/Düzenle Mini Modal                                         -->
    <!--  -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div
          v-if="qModalOpen"
          class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          @click.self="qModalOpen = false"
        >
          <Transition name="modal" appear>
            <div v-if="qModalOpen" class="question-modal w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl">
              <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 class="text-sm font-bold text-gray-900">
                  {{ qModalMode === 'add' ? 'Yeni Soru' : 'Soruyu Düzenle' }}
                </h3>
                <button @click="qModalOpen = false" class="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
              <div class="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
                <div v-if="qFormError" class="text-sm text-rose-600 bg-rose-50 border border-rose-200 px-3 py-2.5 rounded-lg">
                  {{ qFormError }}
                </div>
                <!-- Soru Metni + Sıra -->
                <div class="grid grid-cols-4 gap-3">
                  <div class="col-span-3">
                    <label class="drawer-label mb-2 block">Soru Metni <span class="text-rose-600">*</span></label>
                    <textarea
                      v-model="qForm.text"
                      rows="3"
                      placeholder="Hastaya sorulacak soru metnini girin…"
                      class="drawer-input w-full resize-none"
                    ></textarea>
                  </div>
                  <div>
                    <label class="drawer-label mb-2 block">Sıra</label>
                    <input
                      v-model.number="qForm.order"
                      type="number"
                      min="0"
                      class="drawer-input w-full"
                      placeholder="0"
                    />
                    <p class="mt-1 text-[10px] text-gray-500">1'den başlar. Kategori içinde benzersiz olmalı.</p>
                  </div>
                </div>
                <!-- Hedef Cinsiyet -->
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-2">Hedef Cinsiyet</label>
                  <TargetGenderSelector
                    v-model="qForm.target_gender"
                    :cinsiyetler="cinsiyetler"
                    all-label="Tümü"
                  />
                  <p class="mt-1 text-[10px] text-gray-500">Boş = tüm cinsiyetlere göster.</p>
                </div>
                <!-- Hedef Yaş Aralıkları -->
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-2">Hedef Yaş Aralıkları</label>
                  <div class="flex flex-wrap gap-2">
                    <button
                      v-for="y in yasAraliklari" :key="y.id"
                      type="button"
                      @click="toggleQAge(y.id)"
                      class="px-3 py-1 text-xs font-semibold rounded-full border transition"
                      :class="qForm.target_age_ranges.includes(y.id)
                        ? 'bg-blue-100 text-blue-700 border-blue-400'
                        : 'bg-white text-gray-500 border-gray-300 hover:border-gray-400'"
                    >{{ y.ad }}</button>
                  </div>
                  <p class="mt-1 text-[10px] text-gray-500">Boş = herkese göster.</p>
                </div>
              </div>
              <div class="px-6 py-4 border-t border-gray-200 flex items-center gap-3">
                <button @click="qModalOpen = false" :disabled="qSaving" class="eisa-btn flex-1 disabled:opacity-50">
                  İptal
                </button>
                <button @click="saveQuestion" :disabled="qSaving" class="eisa-btn eisa-btn-cta flex-1 disabled:opacity-60">
                  <svg v-if="qSaving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  {{ qSaving ? 'Kaydediliyor…' : (qModalMode === 'add' ? 'Ekle' : 'Güncelle') }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!-- Soru Silme Onay -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div
          v-if="qDeleteOpen"
          class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          @click.self="qDeleteOpen = false"
        >
          <Transition name="modal" appear>
            <div v-if="qDeleteOpen" class="question-modal w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl">
              <div class="p-6 text-center">
                <div class="w-12 h-12 bg-rose-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg class="w-6 h-6 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                </div>
                <h3 class="text-sm font-semibold text-gray-900 mb-1">Soruyu Sil</h3>
                <p class="text-xs text-gray-600">Bu soru ve bağlı <span class="text-rose-600 font-semibold">{{ qDeleteTarget?.hedef_etken_maddeler?.length ?? 0 }} etken madde</span> bağlantısı kalıcı olarak silinecek.</p>
              </div>
              <div class="px-6 pb-5 flex gap-2.5">
                <button @click="qDeleteOpen = false" :disabled="qDeleting" class="eisa-btn flex-1 disabled:opacity-50">Vazgeç</button>
                <button @click="confirmDeleteQuestion" :disabled="qDeleting" class="eisa-btn eisa-btn-danger flex-1 disabled:opacity-60">
                  <svg v-if="qDeleting" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  {{ qDeleting ? 'Siliniyor…' : 'Sil' }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

  </div>

  <!--  -->
  <!-- KATEGOR EKLE / DÜZENLE Modal                                          -->
  <!--  -->
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="catModalOpen"
        class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
        @click.self="closeCatModal"
      >
        <Transition name="modal" appear>
          <div v-if="catModalOpen" class="question-modal w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl">
            <!-- Balk -->
            <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-gray-900">{{ catModalMode === 'add' ? 'Yeni Kategori' : 'Kategori Düzenle' }}</h3>
              <button @click="closeCatModal" class="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <!-- Form Gövdesi -->
            <div class="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div v-if="catFormError" class="flex items-center gap-2 bg-rose-50 border border-rose-200 text-rose-600 text-sm px-3 py-2.5 rounded-lg">{{ catFormError }}</div>

              <!-- Ad + ikon -->
              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2">
                  <label class="block text-xs font-semibold text-gray-600 mb-2">Kategori Adı <span class="text-rose-600">*</span></label>
                  <input
                    v-model="catForm.name"
                    type="text"
                    placeholder="Örn: Enerji & Yorgunluk"
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
                    <span class="w-6 h-6 flex items-center justify-center text-sm bg-blue-50 rounded flex-shrink-0">
                      <i :class="catForm.icon || 'fa-solid fa-pills'" class="text-blue-600"></i>
                    </span>                   
                    <i class="fa-solid fa-grip text-gray-400 flex-shrink-0"></i>
                  </button>
                </div>
              </div>

              <!-- Hassas Toggle -->
              <div class="flex items-center gap-2.5">
                <input id="cat-hassas" type="checkbox" v-model="catForm.is_sensitive"
                  class="w-4 h-4 rounded bg-white border-gray-300 text-blue-600 focus:ring-blue-400" />
                <label for="cat-hassas" class="text-sm text-gray-700 cursor-pointer">Hassas kategori <span class="text-gray-500 text-xs">(Özel danışmanlık gerektirir)</span></label>
              </div>

              <!-- Hedef Cinsiyet (tek seçim) -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-2">Hedef Cinsiyet</label>
                <TargetGenderSelector
                  v-model="catForm.target_gender"
                  :cinsiyetler="cinsiyetler"
                  all-label="Tümü"
                />
                <p class="mt-1 text-[10px] text-gray-500">Boş bırakırsanız tüm cinsiyetler hedeflenir.</p>
              </div>

              <!-- Hedef Yaş Aralıkları -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-2">Hedef Yaş Aralıkları</label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="y in yasAraliklari" :key="y.id"
                    type="button"
                    @click="toggleCatAge(y.id)"
                    class="px-3 py-1 text-xs font-semibold rounded-full border transition"
                    :class="catForm.target_age_ranges.includes(y.id)
                      ? 'bg-blue-100 text-blue-700 border-blue-400'
                      : 'bg-white text-gray-500 border-gray-300 hover:border-gray-400'"
                  >{{ y.ad }}</button>
                </div>
                <p class="mt-1 text-[10px] text-gray-500">Boş bırakırsanız tüm yaş grupları hedeflenir.</p>
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

  <!--  İkon Seçici Popup  -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="iconPickerOpen"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4"
        style="background: rgba(15,23,42,0.45); backdrop-filter: blur(6px);"
        @click.self="iconPickerOpen = false"
      >
        <div
          class="w-full max-w-2xl bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          style="max-height: 80vh;"
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <div>
              <h3 class="text-base font-bold text-gray-900">İkon Seç</h3>
              <p class="text-xs text-gray-500 mt-0.5">Kategori için bir sağlık ikonu seçin</p>
            </div>
            <button
              type="button"
              @click="iconPickerOpen = false"
              class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="flex-1 overflow-y-auto p-4">
            <div class="grid grid-cols-6 sm:grid-cols-8 gap-2">
              <button
                v-for="ic in HEALTH_ICONS"
                :key="ic.cls"
                type="button"
                :title="ic.label"
                @click="catForm.icon = ic.cls; iconPickerOpen = false"
                class="aspect-square flex flex-col items-center justify-center gap-1 rounded-xl border transition group"
                :class="catForm.icon === ic.cls
                  ? 'bg-blue-100 border-blue-500 text-blue-700 ring-2 ring-blue-400'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50'"
              >
                <i :class="ic.cls" class="text-lg"></i>
                <span class="text-[10px] leading-tight text-center px-1 truncate w-full opacity-70 group-hover:opacity-100">{{ ic.label }}</span>
              </button>
            </div>
          </div>
          <div class="px-5 py-3 border-t border-gray-200 flex justify-between items-center bg-gray-50">
            <div class="text-xs text-gray-500">
              Mevcut: <code class="text-blue-600 ml-1">{{ catForm.icon || 'fa-solid fa-pills' }}</code>
            </div>
            <button
              type="button"
              @click="iconPickerOpen = false"
              class="eisa-btn"
            >
              Kapat
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>


<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap');

/*  Root Layout  */
.medical-logic-root {
  background: #F2F1EE;
  color: #111827;
  font-family: 'Syne', system-ui, sans-serif;
}

/*  Category Rail  */
.category-rail {
  background: #FFFFFF;
  border-right: 1px solid #E5E3DF;
}

/*  Main Header  */
.main-header {
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid #E5E3DF;
}

/*  Question Cards  */
.question-card {
  animation: slide-in 0.25s ease both;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0); }
}

.question-header {
  background: #FAFAF9;
}

/*  Rules Body  */
.rules-body {
  background: #F9F8F6;
}

/*  Accordion transition  */
.accordion-enter-active,
.accordion-leave-active {
  transition: max-height 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease;
  overflow: hidden;
  max-height: 800px;
}
.accordion-enter-from,
.accordion-leave-to {
  max-height: 0;
  opacity: 0;
}

/*  Drawer Panel  */
.drawer-panel {
  background: #FFFFFF;
  border-left: 1px solid #E5E3DF;
  box-shadow: -4px 0 24px rgba(0,0,0,0.06);
}

.drawer-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #6B7280;
}

.drawer-input {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  border-radius: 8px;
  color: #111827;
  font-size: 13px;
  padding: 8px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: 'DM Mono', monospace;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
}

.drawer-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.10);
}

.drawer-input option {
  background: #FFFFFF;
  color: #111827;
}

/*  Question Modal  */
.question-modal {
  background: #FFFFFF;
  border: 1px solid #E5E3DF;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
}

/*  Drawer Transitions  */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}

/*  Backdrop Transitions  */
.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

/*  Modal Transitions  */
.modal-enter-active {
  transition: opacity 0.2s ease, transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.94) translateY(8px);
}

/*  Rule preview  */
.rule-preview {
  background: linear-gradient(135deg, #FAFAF9 0%, #F3F4F6 100%);
}

/*  Gender Button  */
.gender-btn {
  cursor: pointer;
  user-select: none;
}

/*  Scrollbars  */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #2563EB; }
</style>
