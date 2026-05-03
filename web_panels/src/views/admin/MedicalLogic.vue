<script setup>
/**
 * Tıbbi Mantık Editörü — Algoritma & Karar Ağacı Yönetimi
 * Kategori → Soru → Eşleşme Kuralı hiyerarşisi
 */
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import {
  getCategories,
  getQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  addMatchRule,
  updateMatchRule,
  deleteMatchRule,
  getActiveIngredients,
} from '../../services/algorithm';

// ─── Global Yükleme ───────────────────────────────────────────────────────────
const categories   = ref([]);
const ingredients  = ref([]);
const loadingCats  = ref(true);

// ─── Kategori Seçimi ──────────────────────────────────────────────────────────
const activeCatId  = ref(null);
const activeCategory = computed(() => categories.value.find((c) => c.id === activeCatId.value));

// ─── Soru Yönetimi ────────────────────────────────────────────────────────────
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

// ─── Kural Drawer ─────────────────────────────────────────────────────────────
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

// ─── Yükleme ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  const [cats, ings] = await Promise.all([getCategories(), getActiveIngredients()]);
  categories.value  = cats;
  ingredients.value = ings;
  loadingCats.value = false;
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

// ─── Soru CRUD ────────────────────────────────────────────────────────────────
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
  if (!qForm.value.text.trim()) { qFormError.value = 'Soru metni boş olamaz.'; return; }
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
  } catch { qFormError.value = 'İşlem başarısız.'; }
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

// ─── Kural Drawer ─────────────────────────────────────────────────────────────
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
  if (!ruleForm.value.primary_id) { drawerError.value = 'Ana öneri seçmelisiniz.'; return; }
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

// ─── Helpers ──────────────────────────────────────────────────────────────────
function ingredientName(id) {
  if (!id) return '—';
  return ingredients.value.find((i) => i.id === id)?.name ?? `#${id}`;
}

function genderLabel(g) {
  return g === 'F' ? 'Kadın' : g === 'M' ? 'Erkek' : 'Tümü';
}

function genderBadgeClass(g) {
  return g === 'F'
    ? 'bg-pink-900/40 text-pink-300 border border-pink-700/30'
    : g === 'M'
      ? 'bg-sky-900/40 text-sky-300 border border-sky-700/30'
      : 'bg-zinc-700/50 text-zinc-300 border border-zinc-600/30';
}
</script>

<template>
  <div class="medical-logic-root flex min-h-screen">

    <!-- ════════ LEFT RAIL: Kategoriler ════════ -->
    <aside class="category-rail w-64 flex-shrink-0 flex flex-col border-r border-zinc-800 sticky top-0 self-start" style="max-height: 100vh; overflow-y: auto;">
      <div class="px-5 pt-6 pb-4 border-b border-zinc-800">
        <p class="text-xs font-bold tracking-[0.15em] text-amber-400 uppercase mb-1">Şikayet Ağacı</p>
        <h2 class="text-base font-semibold text-zinc-100 leading-tight">Kategoriler</h2>
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
          <span class="text-lg leading-none">{{ cat.icon }}</span>
          <span class="flex-1 text-sm font-medium truncate">{{ cat.name }}</span>
          <!-- Sensitive badge -->
          <span v-if="cat.is_sensitive" class="text-[10px] font-bold text-rose-400 leading-none" title="Hassas Durum">⚠</span>
          <!-- Active indicator -->
          <span
            class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="activeCatId === cat.id ? 'bg-amber-400' : 'bg-transparent group-hover:bg-zinc-600'"
          ></span>
        </button>
      </nav>
    </aside>

    <!-- ════════ MAIN PANEL: Sorular ════════ -->
    <main class="flex-1 overflow-y-auto flex flex-col">

      <!-- Başlık Barı -->
      <div class="sticky top-0 z-10 main-header px-8 py-5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-xl">{{ activeCategory?.icon ?? '—' }}</span>
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
            · {{ questions.reduce((s, q) => s + q.match_rules.length, 0) }} kural tanımlı
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

        <!-- Boş durum -->
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
          <button @click="openAddQuestion" class="text-amber-400 text-sm hover:text-amber-300 underline underline-offset-2">İlk soruyu ekle →</button>
        </div>

        <!-- Soru Kartları (Accordion) -->
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
          <!-- Soru Başlık Satırı -->
          <div
            class="question-header flex items-center gap-3 px-5 py-4 cursor-pointer select-none group"
            :class="expandedQId === q.id ? 'bg-zinc-800/80' : 'bg-zinc-800/40 hover:bg-zinc-800/70'"
            @click="toggleQuestion(q.id)"
          >
            <!-- Sıra numarası -->
            <span class="text-xs font-mono font-bold text-zinc-500 w-5 text-center flex-shrink-0">{{ q.order + 1 }}</span>

            <!-- Soru metni -->
            <p class="flex-1 text-sm font-medium text-zinc-200 leading-snug">{{ q.text }}</p>

            <!-- Sağ taraf meta -->
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Seed ID chip -->
              <span v-if="q.seed_id" class="text-[10px] font-mono text-zinc-500 bg-zinc-700/50 px-1.5 py-0.5 rounded">
                {{ q.seed_id }}
              </span>
              <!-- Kural sayısı -->
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

                <!-- Kural Başlığı -->
                <div class="flex items-center justify-between mb-3">
                  <h3 class="text-xs font-bold tracking-[0.12em] text-zinc-400 uppercase">Eşleşme Kuralları</h3>
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

                    <!-- Yaş aralığı -->
                    <span class="flex items-center gap-1 text-xs text-zinc-400 font-mono bg-zinc-700/40 px-2 py-0.5 rounded">
                      <span class="text-zinc-500">yaş</span>
                      {{ rule.age_min }}–{{ rule.age_max }}
                    </span>

                    <!-- Öneri okları -->
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
                        title="Kuralı Düzenle"
                      >
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                      </button>
                      <button
                        @click="removeRule(q, rule.id)"
                        :disabled="ruleDeleting === rule.id"
                        class="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition disabled:opacity-40"
                        title="Kuralı Sil"
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

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!-- KURAL DRAWER                                                         -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
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
          <!-- Drawer Başlık -->
          <div class="px-6 py-5 border-b border-zinc-700/60 flex items-start justify-between flex-shrink-0">
            <div>
              <p class="text-xs font-bold tracking-[0.15em] text-amber-400 uppercase mb-1">
                {{ drawerMode === 'add' ? 'Yeni Kural' : 'Kuralı Düzenle' }}
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
                  v-for="opt in [{ v: 'all', l: 'Tümü', icon: '⚥' }, { v: 'F', l: 'Kadın', icon: '♀' }, { v: 'M', l: 'Erkek', icon: '♂' }]"
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

            <!-- 2. Yaş Aralığı -->
            <div class="form-group">
              <label class="drawer-label">Yaş Aralığı</label>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <label class="text-[11px] text-zinc-500 font-medium block mb-1">Min Yaş</label>
                  <input
                    v-model.number="ruleForm.age_min"
                    type="number" min="0" max="120"
                    class="drawer-input w-full"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label class="text-[11px] text-zinc-500 font-medium block mb-1">Max Yaş</label>
                  <input
                    v-model.number="ruleForm.age_max"
                    type="number" min="0" max="120"
                    class="drawer-input w-full"
                    placeholder="99"
                  />
                </div>
              </div>
              <!-- Yaş görselleştirme barı -->
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
              <p class="text-[11px] text-zinc-600 mt-0.5 mb-2">Hastaya öncelikli önerilecek etken madde</p>
              <select v-model.number="ruleForm.primary_id" class="drawer-input w-full">
                <option :value="null" disabled>— Seçin —</option>
                <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">{{ ing.name }}</option>
              </select>
              <!-- Seçili öneri göstergesi -->
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
                <span class="px-2 py-1 rounded bg-zinc-700 text-zinc-300 font-mono">{{ ruleForm.age_min }}–{{ ruleForm.age_max }} yaş</span>
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
              İptal
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
              {{ drawerSaving ? 'Kaydediliyor…' : (drawerMode === 'add' ? 'Kuralı Kaydet' : 'Güncelle') }}
            </button>
          </div>
        </aside>
      </Transition>
    </Teleport>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!-- Soru Ekle/Düzenle Mini Modal                                         -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
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
                  İptal
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
                <p class="text-xs text-zinc-400">Bu soru ve bağlı <span class="text-rose-300 font-semibold">{{ qDeleteTarget?.match_rules?.length ?? 0 }} kural</span> kalıcı olarak silinecek.</p>
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
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap');

/* ── Root Layout ─────────────────────────────────────────────────────────── */
.medical-logic-root {
  background: #0e1117;
  color: #e4e4e7;
  font-family: 'Syne', system-ui, sans-serif;
}

/* ── Category Rail ───────────────────────────────────────────────────────── */
.category-rail {
  background: #0b0e14;
}

/* ── Main Header ─────────────────────────────────────────────────────────── */
.main-header {
  background: rgba(14, 17, 23, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

/* ── Question Cards ──────────────────────────────────────────────────────── */
.question-card {
  animation: slide-in 0.25s ease both;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0); }
}

.question-header {
  background: rgba(39, 39, 42, 0.4);
}

/* ── Rules Body ──────────────────────────────────────────────────────────── */
.rules-body {
  background: rgba(9, 9, 11, 0.5);
}

/* ── Accordion transition ────────────────────────────────────────────────── */
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

/* ── Drawer Panel ────────────────────────────────────────────────────────── */
.drawer-panel {
  background: #13161e;
  border-left: 1px solid rgba(63, 63, 70, 0.5);
}

.drawer-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #a1a1aa;
}

.drawer-input {
  background: #1c1f28;
  border: 1px solid rgba(63, 63, 70, 0.7);
  border-radius: 8px;
  color: #e4e4e7;
  font-size: 13px;
  padding: 8px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: 'DM Mono', monospace;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
}

.drawer-input:focus {
  border-color: rgba(245, 158, 11, 0.6);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

.drawer-input option {
  background: #1c1f28;
  color: #e4e4e7;
}

/* ── Question Modal ──────────────────────────────────────────────────────── */
.question-modal {
  background: #13161e;
  border: 1px solid rgba(63, 63, 70, 0.5);
}

/* ── Drawer Transitions ──────────────────────────────────────────────────── */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}

/* ── Backdrop Transitions ────────────────────────────────────────────────── */
.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

/* ── Modal Transitions ───────────────────────────────────────────────────── */
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

/* ── Rule preview ────────────────────────────────────────────────────────── */
.rule-preview {
  background: linear-gradient(135deg, rgba(39, 39, 42, 0.5) 0%, rgba(24, 24, 27, 0.8) 100%);
}

/* ── Gender Button ───────────────────────────────────────────────────────── */
.gender-btn {
  cursor: pointer;
  user-select: none;
}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(63, 63, 70, 0.5); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(245, 158, 11, 0.4); }
</style>
