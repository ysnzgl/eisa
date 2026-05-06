<script setup>
/**
 * Tıbbi Mantık Editörü — Algoritma & Karar Ağacı Yönetimi
 * Kategori  Soru  Eleme Kural hiyerarisi
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
  addMatchRule,
  updateMatchRule,
  deleteMatchRule,
  getActiveIngredients,
} from '../../services/algorithm';
import { getCinsiyetler, getYasAraliklari } from '../../services/lookups';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';

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
const EMPTY_CAT = () => ({ name: '', icon: '', is_sensitive: false, hedef_cinsiyetler: [], hedef_yas_araliklari: [] });
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
    name:                 cat.name,
    icon:                 cat.icon,
    is_sensitive:         cat.is_sensitive,
    hedef_cinsiyetler:    [...(cat.hedef_cinsiyetler ?? [])],
    hedef_yas_araliklari: [...(cat.hedef_yas_araliklari ?? [])],
  };
  catFormError.value = '';
  catModalMode.value = 'edit';
  catTarget.value    = cat;
  catModalOpen.value = true;
}

function closeCatModal() { catModalOpen.value = false; }

async function saveCategory() {
  if (!catForm.value.name.trim()) { catFormError.value = 'Kategori ad zorunludur.'; return; }
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

function toggleCatGender(kodId) {
  const idx = catForm.value.hedef_cinsiyetler.indexOf(kodId);
  if (idx === -1) catForm.value.hedef_cinsiyetler.push(kodId);
  else catForm.value.hedef_cinsiyetler.splice(idx, 1);
}

function toggleCatAge(kodId) {
  const idx = catForm.value.hedef_yas_araliklari.indexOf(kodId);
  if (idx === -1) catForm.value.hedef_yas_araliklari.push(kodId);
  else catForm.value.hedef_yas_araliklari.splice(idx, 1);
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
const qForm       = ref({ text: '' });
const qTarget     = ref(null);
const qSaving     = ref(false);
const qFormError  = ref('');

const qDeleteOpen   = ref(false);
const qDeleteTarget = ref(null);
const qDeleting     = ref(false);

//  Kural Drawer 
const drawerOpen    = ref(false);
const drawerMode    = ref('add');        // 'add' | 'edit'
const drawerQuestion = ref(null);
const drawerRuleId  = ref(null);
const drawerSaving  = ref(false);
const drawerError   = ref('');

const EMPTY_RULE = () => ({
  gender:     'all',
  age_min:    18,
  age_max:    65,
  primary_id: null,
  supportive_id: null,
});
const ruleForm = ref(EMPTY_RULE());

// Kural Silme
const ruleDeleting = ref(null);          // ruleId being deleted

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
  qForm.value    = { text: '' };
  qFormError.value = '';
  qModalMode.value = 'add';
  qTarget.value    = null;
  qModalOpen.value = true;
}

function openEditQuestion(q) {
  qForm.value    = { text: q.text };
  qFormError.value = '';
  qModalMode.value = 'edit';
  qTarget.value    = q;
  qModalOpen.value = true;
}

async function saveQuestion() {
  if (!qForm.value.text.trim()) { qFormError.value = 'Soru metni bo olamaz.'; return; }
  qSaving.value    = true;
  qFormError.value = '';
  try {
    if (qModalMode.value === 'add') {
      const newQ = await createQuestion(activeCatId.value, { text: qForm.value.text.trim() });
      questions.value.push(newQ);
      expandedQId.value = newQ.id;
    } else {
      const updated = await updateQuestion(qTarget.value.id, { text: qForm.value.text.trim() });
      const idx = questions.value.findIndex((q) => q.id === updated.id);
      if (idx !== -1) questions.value[idx] = updated;
    }
    qModalOpen.value = false;
  } catch { qFormError.value = 'lem baarsz.'; }
  finally { qSaving.value = false; }
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

//  Kural Drawer 
function openAddRule(question) {
  ruleForm.value    = EMPTY_RULE();
  drawerError.value = '';
  drawerMode.value  = 'add';
  drawerQuestion.value = question;
  drawerRuleId.value   = null;
  drawerOpen.value  = true;
}

function openEditRule(question, rule) {
  ruleForm.value = {
    gender:       rule.gender,
    age_min:      rule.age_min,
    age_max:      rule.age_max,
    primary_id:   rule.primary_id,
    supportive_id: rule.supportive_id,
  };
  drawerError.value    = '';
  drawerMode.value     = 'edit';
  drawerQuestion.value = question;
  drawerRuleId.value   = rule.id;
  drawerOpen.value     = true;
}

function closeDrawer() {
  drawerOpen.value = false;
}

async function saveRule() {
  if (!ruleForm.value.primary_id) { drawerError.value = 'Ana Öneri seçmelisiniz.'; return; }
  if (ruleForm.value.age_min > ruleForm.value.age_max) { drawerError.value = 'Min yaş, Max yaştan büyük olamaz.'; return; }
  drawerSaving.value = true;
  drawerError.value  = '';
  try {
    const q = drawerQuestion.value;
    let updated;
    if (drawerMode.value === 'add') {
      updated = await addMatchRule(q.id, { ...ruleForm.value });
    } else {
      updated = await updateMatchRule(q.id, drawerRuleId.value, { ...ruleForm.value });
    }
    const idx = questions.value.findIndex((x) => x.id === q.id);
    if (idx !== -1) questions.value[idx] = updated;
    drawerOpen.value = false;
  } catch { drawerError.value = 'Kural kaydedilemedi.'; }
  finally { drawerSaving.value = false; }
}

async function removeRule(question, ruleId) {
  ruleDeleting.value = ruleId;
  try {
    await deleteMatchRule(question.id, ruleId);
    const idx = questions.value.findIndex((q) => q.id === question.id);
    if (idx !== -1) {
      questions.value[idx] = {
        ...questions.value[idx],
        match_rules: questions.value[idx].match_rules.filter((r) => r.id !== ruleId),
      };
    }
  } finally { ruleDeleting.value = null; }
}

//  Helpers 
function ingredientName(id) {
  if (!id) return '—';
  return ingredients.value.find((i) => i.id === id)?.name ?? `#${id}`;
}

function genderLabel(g) {
  return g === 'F' ? 'Kadn' : g === 'M' ? 'Erkek' : 'Tümü';
}

function genderBadgeClass(g) {
  return g === 'F'
    ? 'bg-pink-50 text-pink-600 border border-pink-300'
    : g === 'M'
      ? 'bg-sky-50 text-sky-600 border border-sky-300'
      : 'bg-gray-100 text-gray-500 border border-gray-300';
}

//  İkon Seçici 
const iconPickerOpen = ref(false);
const HEALTH_ICONS = [
  { cls: 'fa-solid fa-pills',               label: 'İlaç'        },
  { cls: 'fa-solid fa-heart-pulse',         label: 'Kalp'        },
  { cls: 'fa-solid fa-lungs',               label: 'Akcier'    },
  { cls: 'fa-solid fa-brain',               label: 'Beyin'       },
  { cls: 'fa-solid fa-tooth',               label: 'Di'         },
  { cls: 'fa-solid fa-eye',                 label: 'Göz'         },
  { cls: 'fa-solid fa-ear-deaf',            label: 'Kulak'       },
  { cls: 'fa-solid fa-hand',                label: 'El/Ar'    },
  { cls: 'fa-solid fa-bone',                label: 'Kemik'       },
  { cls: 'fa-solid fa-virus',               label: 'Virüs'       },
  { cls: 'fa-solid fa-bacterium',           label: 'Bakteri'     },
  { cls: 'fa-solid fa-dumbbell',            label: 'Spor'        },
  { cls: 'fa-solid fa-leaf',                label: 'Bitkisel'    },
  { cls: 'fa-solid fa-spa',                 label: 'Cilt'        },
  { cls: 'fa-solid fa-sun',                 label: 'Güneş'      },
  { cls: 'fa-solid fa-moon',                label: 'Uyku'        },
  { cls: 'fa-solid fa-temperature-high',    label: 'Ate'        },
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
  { cls: 'fa-solid fa-triangle-exclamation',label: 'Uyar'       },
  { cls: 'fa-solid fa-circle-info',         label: 'Bilgi'       },
];
</script>

<template>
  <div class="medical-logic-root flex min-h-screen">

    <!--  LEFT RAIL: Kategoriler  -->
    <aside class="category-rail w-64 flex-shrink-0 flex flex-col border-r border-zinc-800 sticky top-0 self-start" style="max-height: 100vh; overflow-y: auto;">
      <div class="px-5 pt-6 pb-4 border-b border-zinc-800">
        <p class="text-xs font-bold tracking-[0.15em] text-amber-400 uppercase mb-1">ikayet Aac</p>
        <h2 class="text-base font-semibold text-zinc-100 leading-tight">Kategoriler</h2>
        <button
          @click="openAddCategory"
          class="mt-3 w-full flex items-center justify-center gap-1.5 text-xs font-semibold text-zinc-400 hover:text-amber-300 border border-zinc-700 hover:border-amber-600/50 rounded-lg py-1.5 transition"
        >
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
          Yeni Kategori
        </button>
      </div>

      <nav class="flex-1 px-3 py-3 space-y-0.5">
        <div
          v-if="loadingCats"
          v-for="n in 5"
          :key="n"
          class="h-10 bg-zinc-800/60 rounded-lg animate-pulse mb-1"
        ></div>

        <button
          v-for="cat in categories"
          :key="cat.id"
          @click="selectCategory(cat.id)"
          class="cat-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150 group"
          :class="activeCatId === cat.id
            ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30'
            : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'"
        >
          <span class="w-5 text-center flex-shrink-0 text-lg leading-none"><i :class="cat.icon || 'fa-solid fa-pills'"></i></span>
          <span class="flex-1 text-sm font-medium truncate">{{ cat.name }}</span>
          <!-- Sensitive badge -->
          <span v-if="cat.is_sensitive" class="text-[10px] font-bold text-rose-400 leading-none" title="Hassas Durum"></span>
          <!-- Active indicator -->
          <span
            class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="activeCatId === cat.id ? 'bg-amber-400' : 'bg-transparent group-hover:bg-zinc-600'"
          ></span>
          <!-- Edit button -->
          <button
            @click.stop="openEditCategory(cat)"
            class="ml-auto p-0.5 text-zinc-600 hover:text-amber-400 opacity-0 group-hover:opacity-100 transition rounded flex-shrink-0"
            title="Kategoriyi Düzenle"
          >
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>
        </button>
      </nav>
    </aside>

    <!--  MAIN PANEL: Sorular  -->
    <main class="flex-1 overflow-y-auto flex flex-col">

      <!-- Balk Bar -->
      <div class="sticky top-0 z-10 main-header px-8 py-5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-xl"><i :class="activeCategory?.icon || 'fa-solid fa-pills'"></i></span>
            <h1 class="text-lg font-bold text-zinc-100 tracking-tight">
              {{ activeCategory?.name ?? 'Kategori seçin' }}
            </h1>
            <span
              v-if="activeCategory?.is_sensitive"
              class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-900/50 text-rose-400 border border-rose-700/30 uppercase tracking-wider"
            >Hassas</span>
          </div>
          <p class="text-xs text-zinc-500 font-mono" v-if="activeCategory">
            {{ questions.length }} soru
            — {{ questions.reduce((s, q) => s + q.match_rules.length, 0) }} kural tanml
          </p>
        </div>
        <button
          v-if="activeCategory"
          @click="openAddQuestion"
          class="flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-zinc-900 text-sm font-bold px-4 py-2 rounded-lg transition-colors duration-150 shadow-lg shadow-amber-900/30"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Soru Ekle
        </button>
      </div>

      <!-- Sorular Listesi -->
      <div class="flex-1 px-8 py-6 space-y-3">

        <!-- Yükleniyor -->
        <div v-if="loadingQuestions" class="space-y-3">
          <div v-for="n in 3" :key="n" class="h-16 bg-zinc-800/40 rounded-xl animate-pulse"></div>
        </div>

        <!-- Bo durum -->
        <div
          v-else-if="!activeCategory"
          class="flex flex-col items-center justify-center h-64 text-zinc-600"
        >
          <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
          <p class="text-sm">Soldan bir kategori seçin</p>
        </div>

        <div
          v-else-if="questions.length === 0 && !loadingQuestions"
          class="flex flex-col items-center justify-center h-48 text-zinc-600"
        >
          <p class="text-sm mb-3">Bu kategoride henüz soru yok.</p>
          <button @click="openAddQuestion" class="text-amber-400 text-sm hover:text-amber-300 underline underline-offset-2">lk soruyu ekle </button>
        </div>

        <!-- Soru Kartlar (Accordion) -->
        <div
          v-else
          v-for="(q, qi) in questions"
          :key="q.id"
          class="question-card rounded-xl border overflow-hidden transition-all duration-200"
          :class="expandedQId === q.id
            ? 'border-amber-500/40 shadow-lg shadow-amber-900/10'
            : 'border-zinc-700/50 hover:border-zinc-600'"
          :style="{ animationDelay: qi * 40 + 'ms' }"
        >
          <!-- Soru Balk Satr -->
          <div
            class="question-header flex items-center gap-3 px-5 py-4 cursor-pointer select-none group"
            :class="expandedQId === q.id ? 'bg-zinc-800/80' : 'bg-zinc-800/40 hover:bg-zinc-800/70'"
            @click="toggleQuestion(q.id)"
          >
            <!-- Sra numaras -->
            <span class="text-xs font-mono font-bold text-zinc-500 w-5 text-center flex-shrink-0">{{ q.order + 1 }}</span>

            <!-- Soru metni -->
            <p class="flex-1 text-sm font-medium text-zinc-200 leading-snug">{{ q.text }}</p>

            <!-- Sa taraf meta -->
            <div class="flex items-center gap-2 flex-shrink-0">            
              <!-- Kural says -->
              <span
                class="text-xs font-semibold px-2 py-0.5 rounded-full"
                :class="q.match_rules.length
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                  : 'bg-zinc-700/40 text-zinc-500'"
              >
                {{ q.match_rules.length }} kural
              </span>
              <!-- Düzenle / Sil -->
              <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                <button
                  @click="openEditQuestion(q)"
                  class="p-1.5 text-zinc-500 hover:text-amber-400 hover:bg-amber-500/10 rounded transition"
                  title="Düzenle"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button
                  @click="openDeleteQuestion(q)"
                  class="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition"
                  title="Sil"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
              <!-- Chevron -->
              <svg
                class="w-4 h-4 text-zinc-500 transition-transform duration-200 ml-1"
                :class="expandedQId === q.id ? 'rotate-180' : ''"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
          </div>

          <!-- Accordion Body: Kurallar -->
          <Transition name="accordion">
            <div v-if="expandedQId === q.id" class="rules-body border-t border-zinc-700/50 bg-zinc-900/50">
              <div class="px-5 py-4">

                <!-- Kural Bal -->
                <div class="flex items-center justify-between mb-3">
                  <h3 class="text-xs font-bold tracking-[0.12em] text-zinc-400 uppercase">Eleme Kurallar</h3>
                  <button
                    @click="openAddRule(q)"
                    class="flex items-center gap-1 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 px-2.5 py-1 rounded-md transition"
                  >
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                    </svg>
                    Kural Ekle
                  </button>
                </div>

                <!-- Kural Listesi -->
                <div v-if="q.match_rules.length === 0" class="text-center py-5 text-zinc-600 text-xs">
                  Bu soruya henüz kural tanımlanmamış.
                </div>

                <div v-else class="space-y-2">
                  <div
                    v-for="rule in q.match_rules"
                    :key="rule.id"
                    class="rule-row flex items-center gap-3 bg-zinc-800/60 border border-zinc-700/40 rounded-lg px-4 py-3 group/rule hover:border-zinc-600/60 transition"
                  >
                    <!-- Rule ID -->
                    <span class="text-[10px] font-mono text-zinc-600 w-12 flex-shrink-0">#{{ rule.id }}</span>

                    <!-- Cinsiyet -->
                    <span class="text-xs font-semibold px-2 py-0.5 rounded" :class="genderBadgeClass(rule.gender)">
                      {{ genderLabel(rule.gender) }}
                    </span>

                    <!-- Ya aral -->
                    <span class="flex items-center gap-1 text-xs text-zinc-400 font-mono bg-zinc-700/40 px-2 py-0.5 rounded">
                      <span class="text-zinc-500">ya</span>
                      {{ rule.age_min }}–{{ rule.age_max }}
                    </span>

                    <!-- Öneri oklar -->
                    <div class="flex items-center gap-1.5 flex-1 min-w-0">
                      <div class="flex items-center gap-1 bg-emerald-900/30 border border-emerald-700/25 text-emerald-300 text-xs px-2 py-1 rounded truncate max-w-[180px]">
                        <svg class="w-3 h-3 flex-shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <span class="truncate font-medium">{{ ingredientName(rule.primary_id) }}</span>
                      </div>
                      <svg v-if="rule.supportive_id" class="w-3 h-3 text-zinc-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                      </svg>
                      <div v-if="rule.supportive_id" class="flex items-center gap-1 bg-sky-900/25 border border-sky-700/20 text-sky-300 text-xs px-2 py-1 rounded truncate max-w-[160px]">
                        <svg class="w-3 h-3 flex-shrink-0 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                        </svg>
                        <span class="truncate">{{ ingredientName(rule.supportive_id) }}</span>
                      </div>
                    </div>

                    <!-- Aksiyon düğmeleri -->
                    <div class="flex items-center gap-0.5 opacity-0 group-hover/rule:opacity-100 transition-opacity flex-shrink-0">
                      <button
                        @click="openEditRule(q, rule)"
                        class="p-1.5 text-zinc-500 hover:text-amber-400 hover:bg-amber-500/10 rounded transition"
                        title="Kural Düzenle"
                      >
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                      </button>
                      <button
                        @click="removeRule(q, rule.id)"
                        :disabled="ruleDeleting === rule.id"
                        class="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition disabled:opacity-40"
                        title="Kural Sil"
                      >
                        <svg v-if="ruleDeleting === rule.id" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
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
            </div>
          </Transition>
        </div>
      </div>
    </main>

    <!--  -->
    <!-- KURAL DRAWER                                                         -->
    <!--  -->
    <Teleport to="body">
      <!-- Backdrop -->
      <Transition name="backdrop">
        <div
          v-if="drawerOpen"
          class="fixed inset-0 bg-black/60 z-40"
          @click="closeDrawer"
        ></div>
      </Transition>

      <!-- Panel -->
      <Transition name="drawer">
        <aside
          v-if="drawerOpen"
          class="fixed right-0 top-0 h-full w-[420px] drawer-panel z-50 flex flex-col shadow-2xl"
        >
          <!-- Drawer Balk -->
          <div class="px-6 py-5 border-b border-zinc-700/60 flex items-start justify-between flex-shrink-0">
            <div>
              <p class="text-xs font-bold tracking-[0.15em] text-amber-400 uppercase mb-1">
                {{ drawerMode === 'add' ? 'Yeni Kural' : 'Kural Düzenle' }}
              </p>
              <h3 class="text-sm font-semibold text-zinc-100 leading-snug max-w-[300px] line-clamp-2">
                {{ drawerQuestion?.text }}
              </h3>
            </div>
            <button
              @click="closeDrawer"
              class="mt-0.5 p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 rounded-lg transition flex-shrink-0"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Form -->
          <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">

            <!-- Hata -->
            <div v-if="drawerError" class="flex items-start gap-2 bg-rose-900/30 border border-rose-700/40 text-rose-300 text-sm px-4 py-3 rounded-lg">
              <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              {{ drawerError }}
            </div>

            <!-- 1. Cinsiyet -->
            <div class="form-group">
              <label class="drawer-label">Cinsiyet</label>
              <div class="grid grid-cols-3 gap-2 mt-2">
                <button
                  v-for="opt in [{ v: 'all', l: 'Tümü', icon: '' }, { v: 'F', l: 'Kadn', icon: '' }, { v: 'M', l: 'Erkek', icon: '' }]"
                  :key="opt.v"
                  @click="ruleForm.gender = opt.v"
                  type="button"
                  class="gender-btn flex flex-col items-center gap-1 py-3 rounded-lg border text-sm font-semibold transition-all duration-150"
                  :class="ruleForm.gender === opt.v
                    ? opt.v === 'F'
                      ? 'bg-pink-900/40 border-pink-500/60 text-pink-200'
                      : opt.v === 'M'
                        ? 'bg-sky-900/40 border-sky-500/60 text-sky-200'
                        : 'bg-amber-900/40 border-amber-500/60 text-amber-200'
                    : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-300'"
                >
                  <span class="text-base">{{ opt.icon }}</span>
                  <span class="text-xs">{{ opt.l }}</span>
                </button>
              </div>
            </div>

            <!-- 2. Ya Aral -->
            <div class="form-group">
              <label class="drawer-label">Ya Aral</label>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <label class="text-[11px] text-zinc-500 font-medium block mb-1">Min Ya</label>
                  <input
                    v-model.number="ruleForm.age_min"
                    type="number" min="0" max="120"
                    class="drawer-input w-full"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label class="text-[11px] text-zinc-500 font-medium block mb-1">Max Ya</label>
                  <input
                    v-model.number="ruleForm.age_max"
                    type="number" min="0" max="120"
                    class="drawer-input w-full"
                    placeholder="99"
                  />
                </div>
              </div>
              <!-- Yaş görselleştirme bar -->
              <div class="mt-2 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-amber-400 rounded-full transition-all duration-200"
                  :style="{
                    marginLeft: `${(ruleForm.age_min / 120) * 100}%`,
                    width: `${Math.max(0, ((ruleForm.age_max - ruleForm.age_min) / 120) * 100)}%`
                  }"
                ></div>
              </div>
              <div class="flex justify-between text-[10px] text-zinc-600 mt-1 font-mono">
                <span>0</span><span>30</span><span>60</span><span>90</span><span>120</span>
              </div>
            </div>

            <!-- 3. Ana Öneri -->
            <div class="form-group">
              <label class="drawer-label">
                Ana Öneri (Primary)
                <span class="text-rose-400 ml-0.5">*</span>
              </label>
              <p class="text-[11px] text-zinc-600 mt-0.5 mb-2">Hastaya Öncelikli önerilecek etken madde</p>
              <select v-model.number="ruleForm.primary_id" class="drawer-input w-full">
                <option :value="null" disabled>— Seçin —</option>
                <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">{{ ing.name }}</option>
              </select>
              <!-- Seçili Öneri göstergesi -->
              <div v-if="ruleForm.primary_id" class="mt-2 flex items-center gap-2 bg-emerald-900/20 border border-emerald-700/25 px-3 py-2 rounded-lg">
                <svg class="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span class="text-sm font-semibold text-emerald-300">{{ ingredientName(ruleForm.primary_id) }}</span>
              </div>
            </div>

            <!-- 4. Destekleyici Öneri -->
            <div class="form-group">
              <label class="drawer-label">Destekleyici Öneri (Supportive)</label>
              <p class="text-[11px] text-zinc-600 mt-0.5 mb-2">İsteğe bağlı — ek destek etken maddesi</p>
              <select v-model.number="ruleForm.supportive_id" class="drawer-input w-full">
                <option :value="null">— Yok —</option>
                <option
                  v-for="ing in ingredients.filter(i => i.id !== ruleForm.primary_id)"
                  :key="ing.id"
                  :value="ing.id"
                >{{ ing.name }}</option>
              </select>
              <div v-if="ruleForm.supportive_id" class="mt-2 flex items-center gap-2 bg-sky-900/20 border border-sky-700/25 px-3 py-2 rounded-lg">
                <svg class="w-4 h-4 text-sky-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                </svg>
                <span class="text-sm font-medium text-sky-300">{{ ingredientName(ruleForm.supportive_id) }}</span>
              </div>
            </div>

            <!-- Özet Önizleme -->
            <div v-if="ruleForm.primary_id" class="rule-preview rounded-xl border border-zinc-700/40 bg-zinc-800/40 p-4">
              <p class="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Kural Özeti</p>
              <div class="flex flex-wrap gap-1.5 text-xs">
                <span class="px-2 py-1 rounded bg-zinc-700 text-zinc-300 font-mono">{{ genderLabel(ruleForm.gender) }}</span>
                <span class="px-2 py-1 rounded bg-zinc-700 text-zinc-300 font-mono">{{ ruleForm.age_min }}–{{ ruleForm.age_max }} ya</span>
                <svg class="w-3 h-3 self-center text-amber-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
                <span class="px-2 py-1 rounded bg-emerald-900/50 text-emerald-300 font-medium">{{ ingredientName(ruleForm.primary_id) }}</span>
                <template v-if="ruleForm.supportive_id">
                  <span class="text-zinc-500 self-center">+</span>
                  <span class="px-2 py-1 rounded bg-sky-900/40 text-sky-300">{{ ingredientName(ruleForm.supportive_id) }}</span>
                </template>
              </div>
            </div>
          </div>

          <!-- Drawer Footer -->
          <div class="px-6 py-4 border-t border-zinc-700/60 flex items-center gap-3 flex-shrink-0">
            <button
              @click="closeDrawer"
              :disabled="drawerSaving"
              class="flex-1 py-2.5 text-sm font-medium text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-500 rounded-lg transition disabled:opacity-50"
            >
              ptal
            </button>
            <button
              @click="saveRule"
              :disabled="drawerSaving || !ruleForm.primary_id"
              class="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 text-sm font-bold py-2.5 rounded-lg transition-colors duration-150 shadow-lg shadow-amber-900/20"
            >
              <svg v-if="drawerSaving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              {{ drawerSaving ? 'Kaydediliyor…' : (drawerMode === 'add' ? 'Kural Kaydet' : 'Güncelle') }}
            </button>
          </div>
        </aside>
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
              <div class="px-6 py-4 border-b border-zinc-700/60 flex items-center justify-between">
                <h3 class="text-sm font-bold text-zinc-100">
                  {{ qModalMode === 'add' ? 'Yeni Soru' : 'Soruyu Düzenle' }}
                </h3>
                <button @click="qModalOpen = false" class="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 rounded-lg transition">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
              <div class="px-6 py-5">
                <div v-if="qFormError" class="text-sm text-rose-400 bg-rose-900/20 border border-rose-700/30 px-3 py-2.5 rounded-lg mb-4">
                  {{ qFormError }}
                </div>
                <label class="drawer-label mb-2 block">Soru Metni <span class="text-rose-400">*</span></label>
                <textarea
                  v-model="qForm.text"
                  rows="3"
                  placeholder="Hastaya sorulacak soru metnini girin…"
                  class="drawer-input w-full resize-none"
                ></textarea>
              </div>
              <div class="px-6 py-4 border-t border-zinc-700/60 flex items-center gap-3">
                <button @click="qModalOpen = false" :disabled="qSaving" class="flex-1 py-2 text-sm text-zinc-400 border border-zinc-700 rounded-lg hover:border-zinc-500 hover:text-zinc-200 transition disabled:opacity-50">
                  ptal
                </button>
                <button @click="saveQuestion" :disabled="qSaving" class="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 text-sm font-bold py-2 rounded-lg transition">
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
                <div class="w-12 h-12 bg-rose-900/50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg class="w-6 h-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                </div>
                <h3 class="text-sm font-semibold text-zinc-100 mb-1">Soruyu Sil</h3>
                <p class="text-xs text-zinc-400">Bu soru ve bal <span class="text-rose-300 font-semibold">{{ qDeleteTarget?.match_rules?.length ?? 0 }} kural</span> kalc olarak silinecek.</p>
              </div>
              <div class="px-6 pb-5 flex gap-2.5">
                <button @click="qDeleteOpen = false" :disabled="qDeleting" class="flex-1 py-2 text-sm text-zinc-400 border border-zinc-700 rounded-lg hover:border-zinc-500 transition disabled:opacity-50">Vazgeç</button>
                <button @click="confirmDeleteQuestion" :disabled="qDeleting" class="flex-1 flex items-center justify-center gap-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-bold py-2 rounded-lg transition">
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
            <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-zinc-100">{{ catModalMode === 'add' ? 'Yeni Kategori' : 'Kategori Düzenle' }}</h3>
              <button @click="closeCatModal" class="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-lg transition">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <!-- Form Gövdesi -->
            <div class="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div v-if="catFormError" class="flex items-center gap-2 bg-rose-900/30 border border-rose-700/40 text-rose-400 text-sm px-3 py-2.5 rounded-lg">{{ catFormError }}</div>

              <!-- Ad + kon -->
              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2">
                  <label class="block text-xs font-semibold text-zinc-400 mb-1.5">Kategori Ad <span class="text-rose-400">*</span></label>
                  <input
                    v-model="catForm.name"
                    type="text"
                    placeholder="Örn: Enerji & Yorgunluk"
                    class="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/60 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-zinc-400 mb-1.5">İkon Seç</label>
                  <button
                    type="button"
                    @click="iconPickerOpen = true"
                    class="w-full flex items-center gap-3 px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg hover:border-amber-500/60 transition"
                  >
                    <span class="w-8 h-8 flex items-center justify-center text-lg bg-zinc-700/60 rounded">
                      <i :class="catForm.icon || 'fa-solid fa-pills'" class="text-amber-400"></i>
                    </span>
                    <span class="flex-1 text-left text-sm text-zinc-300 truncate">{{ catForm.icon || 'fa-solid fa-pills' }}</span>
                    <i class="fa-solid fa-grip text-zinc-500"></i>
                  </button>
                </div>
              </div>

              <!-- Hassas Toggle -->
              <div class="flex items-center gap-2.5">
                <input id="cat-hassas" type="checkbox" v-model="catForm.is_sensitive"
                  class="w-4 h-4 rounded bg-zinc-700 border-zinc-600 text-amber-500 focus:ring-amber-500/40" />
                <label for="cat-hassas" class="text-sm text-zinc-300 cursor-pointer">Hassas kategori <span class="text-zinc-500 text-xs">(Özel danışmanlık gerektirir)</span></label>
              </div>

              <!-- Hedef Cinsiyetler -->
              <div>
                <label class="block text-xs font-semibold text-zinc-400 mb-2">Hedef Cinsiyetler</label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="c in cinsiyetler" :key="c.id"
                    type="button"
                    @click="toggleCatGender(c.id)"
                    class="px-3 py-1 text-xs font-semibold rounded-full border transition"
                    :class="catForm.hedef_cinsiyetler.includes(c.id)
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                      : 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-500'"
                  >{{ c.ad }}</button>
                </div>
                <p class="mt-1 text-[10px] text-zinc-600">Boş bırakırsanız tüm cinsiyetler hedeflenir.</p>
              </div>

              <!-- Hedef Ya Aralklar -->
              <div>
                <label class="block text-xs font-semibold text-zinc-400 mb-2">Hedef Ya Aralklar</label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="y in yasAraliklari" :key="y.id"
                    type="button"
                    @click="toggleCatAge(y.id)"
                    class="px-3 py-1 text-xs font-semibold rounded-full border transition"
                    :class="catForm.hedef_yas_araliklari.includes(y.id)
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                      : 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-500'"
                  >{{ y.ad }}</button>
                </div>
                <p class="mt-1 text-[10px] text-zinc-600">Boş bırakırsanız tüm yaş gruplar hedeflenir.</p>
              </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 border-t border-zinc-800 flex items-center justify-end gap-2.5 bg-zinc-900/50">
              <button @click="closeCatModal" :disabled="catSaving" class="px-4 py-2 text-sm text-zinc-400 border border-zinc-700 rounded-lg hover:border-zinc-500 transition disabled:opacity-50">ptal</button>
              <button @click="saveCategory" :disabled="catSaving" class="flex items-center gap-1.5 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 text-sm font-bold px-4 py-2 rounded-lg transition">
                <svg v-if="catSaving" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                {{ catSaving ? 'Kaydediliyor…' : (catModalMode === 'add' ? 'Olutur' : 'Güncelle') }}
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
        style="background: rgba(15,23,42,0.65); backdrop-filter: blur(6px);"
        @click.self="iconPickerOpen = false"
      >
        <div
          class="w-full max-w-2xl bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          style="max-height: 80vh;"
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
            <div>
              <h3 class="text-base font-bold text-zinc-100">İkon Seç</h3>
              <p class="text-xs text-zinc-500 mt-0.5">Kategori için bir sağlık ikonu seçin</p>
            </div>
            <button
              type="button"
              @click="iconPickerOpen = false"
              class="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition"
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
                  ? 'bg-amber-500/20 border-amber-500/60 text-amber-400 ring-2 ring-amber-500/40'
                  : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-300 hover:border-amber-500/50 hover:text-amber-400 hover:bg-zinc-800'"
              >
                <i :class="ic.cls" class="text-lg"></i>
                <span class="text-[10px] leading-tight text-center px-1 truncate w-full opacity-70 group-hover:opacity-100">{{ ic.label }}</span>
              </button>
            </div>
          </div>
          <div class="px-5 py-3 border-t border-zinc-800 flex justify-between items-center bg-zinc-900/50">
            <div class="text-xs text-zinc-500">
              Mevcut: <code class="text-amber-400 ml-1">{{ catForm.icon || 'fa-solid fa-pills' }}</code>
            </div>
            <button
              type="button"
              @click="iconPickerOpen = false"
              class="px-4 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg transition"
            >
              Kapat
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<!-- Non-scoped overrides: convert dark zinc Tailwind classes to light theme -->
<style>
/*  Background overrides  */
.medical-logic-root .bg-zinc-800\/40  { background: rgba(255,255,255,0.85) !important; }
.medical-logic-root .bg-zinc-800\/80  { background: rgba(248,247,244,0.97) !important; }
.medical-logic-root .bg-zinc-800\/60  { background: rgba(249,248,246,0.9)  !important; }
.medical-logic-root .bg-zinc-800      { background: #FFFFFF                !important; }
.medical-logic-root .bg-zinc-900\/50  { background: rgba(249,248,246,0.8)  !important; }
.medical-logic-root .bg-zinc-700\/50  { background: rgba(243,244,246,0.9)  !important; }
.medical-logic-root .bg-zinc-700\/40  { background: rgba(243,244,246,0.8)  !important; }
.medical-logic-root .bg-zinc-700      { background: #F3F4F6                !important; }
.medical-logic-root .hover\:bg-zinc-800:hover { background: #F3F4F6        !important; }
.medical-logic-root .hover\:bg-zinc-800\/70:hover { background: rgba(249,248,246,0.9) !important; }

/*  Text overrides  */
.medical-logic-root .text-zinc-100    { color: #111827 !important; }
.medical-logic-root .text-zinc-200    { color: #374151 !important; }
.medical-logic-root .text-zinc-300    { color: #4B5563 !important; }
.medical-logic-root .text-zinc-400    { color: #6B7280 !important; }
.medical-logic-root .text-zinc-500    { color: #9CA3AF !important; }
.medical-logic-root .text-zinc-600    { color: #9CA3AF !important; }
.medical-logic-root .hover\:text-zinc-200:hover { color: #111827 !important; }
.medical-logic-root .placeholder-zinc-600::placeholder { color: #D1D5DB !important; }

/*  Border overrides  */
.medical-logic-root .border-zinc-700\/50 { border-color: rgba(209,213,219,0.6)  !important; }
.medical-logic-root .border-zinc-700     { border-color: #E5E7EB               !important; }
.medical-logic-root .border-zinc-800     { border-color: #E5E3DF               !important; }
.medical-logic-root .border-zinc-600\/30 { border-color: rgba(229,231,235,0.6) !important; }

/*  Amber accent overrides  */
.medical-logic-root .text-amber-400   { color: #B45309 !important; }
.medical-logic-root .text-amber-300   { color: #92400E !important; }
.medical-logic-root .bg-amber-500\/15 { background: rgba(217,119,6,0.08)   !important; }
.medical-logic-root .ring-amber-500\/30 { --tw-ring-color: rgba(217,119,6,0.25) !important; }

/*  Status color overrides  */
.medical-logic-root .bg-rose-900\/50  { background: rgba(254,226,226,0.7)  !important; }
.medical-logic-root .text-rose-400    { color: #DC2626                     !important; }
.medical-logic-root .border-rose-700\/30 { border-color: rgba(252,165,165,0.5) !important; }
.medical-logic-root .bg-emerald-900\/30 { background: rgba(209,250,229,0.6) !important; }
.medical-logic-root .text-emerald-300 { color: #059669                     !important; }
.medical-logic-root .border-emerald-700\/30 { border-color: rgba(110,231,183,0.5) !important; }
.medical-logic-root .bg-sky-900\/25   { background: rgba(224,242,254,0.6)  !important; }
.medical-logic-root .text-sky-300     { color: #0284C7                     !important; }
.medical-logic-root .border-sky-700\/30 { border-color: rgba(125,211,252,0.5) !important; }
.medical-logic-root .bg-pink-900\/40  { background: rgba(253,242,248,0.8)  !important; }
.medical-logic-root .text-pink-300    { color: #BE185D                     !important; }
.medical-logic-root .border-pink-700\/30 { border-color: rgba(249,168,212,0.5) !important; }
.medical-logic-root .bg-violet-900\/30 { background: rgba(237,233,254,0.7) !important; }
.medical-logic-root .text-violet-300  { color: #7C3AED                     !important; }
.medical-logic-root .border-violet-700\/30 { border-color: rgba(196,181,253,0.5) !important; }

/*  Form input overrides (category modal)  */
.medical-logic-root input[class*="bg-zinc-800"],
.medical-logic-root select[class*="bg-zinc-800"] {
  background: #FFFFFF !important;
  border-color: #E5E3DF !important;
  color: #111827 !important;
}
.medical-logic-root input[class*="bg-zinc-700"],
.medical-logic-root select[class*="bg-zinc-700"] {
  background: #F9FAFB !important;
  border-color: #E5E3DF !important;
}
</style>

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
  border-color: #B45309;
  box-shadow: 0 0 0 3px rgba(180,83,9,0.08);
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
::-webkit-scrollbar-thumb:hover { background: #B45309; }
</style>
