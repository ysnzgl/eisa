<script setup>
/**
 * CategoryTreeNav
 * Paylaşımlı hiyerarşik kategori navigasyon bileşeni.
 * DanismaYonetimi ve MedicalLogic tarafından ortak kullanılır.
 *
 * Props:
 *   items            – düz liste (hem root hem alt kategoriler)
 *   selectedId       – seçili item id
 *   parentKey        – üst kategori FK alanı ('ust_kategori' | 'bagli_kategori')
 *   labelKey         – gösterim adı alanı ('ad' | 'name')
 *   iconKey          – ikon sınıf alanı ('ikon' | 'icon')
 *   activeKey        – aktiflik alanı ('aktif' | 'is_active')
 *   defaultIcon      – ikon yoksa fallback
 *   accent           – renk teması: 'teal' | 'eisa'
 *   collapsible      – true ise alt kategoriler toggle ile açılır
 *   showTargetBadges – true ise root itemlarda AlgorithmTargetBadges gösterilir
 *   showEditButton   – true ise hover'da düzenle butonu gösterilir
 *   cinsiyetler      – AlgorithmTargetBadges için cinsiyet lookup listesi
 *
 * Emits:
 *   update:selectedId(id)
 *   edit(item)
 */
import { ref, computed, watch } from 'vue';
import AlgorithmTargetBadges from './AlgorithmTargetBadges.vue';

defineOptions({ name: 'CategoryTreeNav' });

const props = defineProps({
  items:            { type: Array,   default: () => [] },
  selectedId:       { type: Number,  default: null },
  parentKey:        { type: String,  default: 'ust_kategori' },
  labelKey:         { type: String,  default: 'ad' },
  iconKey:          { type: String,  default: 'ikon' },
  activeKey:        { type: String,  default: 'aktif' },
  defaultIcon:      { type: String,  default: 'fa-solid fa-folder' },
  accent:           { type: String,  default: 'teal' },    // 'teal' | 'eisa'
  collapsible:      { type: Boolean, default: false },
  showTargetBadges: { type: Boolean, default: false },
  showEditButton:   { type: Boolean, default: false },
  cinsiyetler:      { type: Array,   default: () => [] },
});

const emit = defineEmits(['update:selectedId', 'edit']);

// ─── Expand state (sadece collapsible=true modunda anlamlı) ──────────────────
const expandedIds = ref(new Set());

// ─── Veri yardımcıları ───────────────────────────────────────────────────────
const rootItems = computed(() => props.items.filter(i => !i[props.parentKey]));

function childrenOf(parentId) {
  return props.items.filter(i => i[props.parentKey] === parentId);
}

function label(item)       { return item[props.labelKey]  ?? ''; }
function icon(item)        { return item[props.iconKey]   || props.defaultIcon; }
function isItemActive(item){ return item[props.activeKey] ?? true; }
function isSelected(item)  { return item.id === props.selectedId; }

function isExpanded(item) {
  if (!props.collapsible) return true;
  return expandedIds.value.has(item.id);
}

function toggleExpand(item) {
  if (!props.collapsible) return;
  const next = new Set(expandedIds.value);
  if (next.has(item.id)) next.delete(item.id);
  else next.add(item.id);
  expandedIds.value = next;
}

function select(item) {
  emit('update:selectedId', item.id);
  // collapsible modda child seçilince üst kategoriyi otomatik aç
  if (props.collapsible && item[props.parentKey]) {
    const next = new Set(expandedIds.value);
    next.add(item[props.parentKey]);
    expandedIds.value = next;
  }
}

// collapsible modda items yüklenince alt kategorisi olan rootları aç
watch(
  () => props.items,
  (items) => {
    if (props.collapsible && items.length) {
      const next = new Set(expandedIds.value);
      items
        .filter(i => !i[props.parentKey] && items.some(ch => ch[props.parentKey] === i.id))
        .forEach(i => next.add(i.id));
      expandedIds.value = next;
    }
  },
  { immediate: true },
);

// ─── Accent renk sınıfları ────────────────────────────────────────────────────
const ac = computed(() => {
  if (props.accent === 'eisa') {
    return {
      rootSel:      'bg-eisa-50 border-eisa-200 ring-1 ring-eisa-200 text-eisa-800',
      rootDef:      'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700',
      iconSel:      'bg-eisa-100 text-eisa-600',
      iconDef:      'bg-gray-100 text-gray-500',
      childSel:     'bg-eisa-50 border-eisa-200 text-eisa-700',
      childIconSel: 'text-eisa-500',
    };
  }
  // teal (varsayılan)
  return {
    rootSel:      'bg-teal-50 border-teal-200 ring-1 ring-teal-200 text-teal-800',
    rootDef:      'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700',
    iconSel:      'bg-teal-100 text-teal-600',
    iconDef:      'bg-gray-100 text-gray-500',
    childSel:     'bg-teal-50 border-teal-200 text-teal-700',
    childIconSel: 'text-teal-500',
  };
});
</script>

<template>
  <div class="space-y-1">
    <div v-for="root in rootItems" :key="root.id" class="mb-1">

      <!-- Root item satırı -->
      <div class="flex items-center gap-0.5">

        <!-- Chevron toggle (sadece collapsible modda ve alt kategorisi varsa) -->
        <button
          v-if="collapsible && childrenOf(root.id).length"
          type="button"
          @click.stop="toggleExpand(root)"
          class="flex-shrink-0 w-5 h-5 flex items-center justify-center text-gray-400 hover:text-gray-700 rounded transition"
          :title="isExpanded(root) ? 'Daralt' : 'Genişlet'"
        >
          <svg
            class="w-3 h-3 transition-transform duration-200"
            :class="isExpanded(root) ? 'rotate-90' : ''"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
        <!-- Chevron placeholder (hizalamak için) -->
        <div v-else-if="collapsible" class="w-5 flex-shrink-0"></div>

        <!-- Root buton -->
        <button
          type="button"
          class="flex-1 text-left rounded-xl border px-3 py-2.5 flex flex-col group transition-all duration-150"
          :class="isSelected(root) ? ac.rootSel : ac.rootDef"
          @click="select(root)"
        >
          <!-- Satır 1: ikon badge + etiket + pasif + alt sayısı + düzenle -->
          <div class="flex items-center gap-2 w-full">
            <span
              class="w-6 h-6 flex items-center justify-center rounded-md flex-shrink-0 text-sm"
              :class="isSelected(root) ? ac.iconSel : ac.iconDef"
            >
              <i :class="icon(root)"></i>
            </span>

            <span class="flex-1 text-sm font-semibold truncate leading-tight">{{ label(root) }}</span>

            <span v-if="!isItemActive(root)"
              class="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-400 rounded font-bold flex-shrink-0">
              pasif
            </span>

            <span
              v-if="childrenOf(root.id).length"
              class="text-[10px] px-1 py-0.5 bg-gray-100 text-gray-400 rounded opacity-0 group-hover:opacity-100 transition flex-shrink-0"
            >
              {{ childrenOf(root.id).length }} alt
            </span>

            <button
              v-if="showEditButton"
              type="button"
              @click.stop="$emit('edit', root)"
              class="flex-shrink-0 p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition"
              title="Düzenle"
            >
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
          </div>

          <!-- Satır 2: Hedef cinsiyet/yaş badges (opsiyonel) -->
          <div v-if="showTargetBadges" class="pl-8 mt-1">
            <AlgorithmTargetBadges
              :target-gender="root.target_gender"
              :target-age-ranges="root.target_age_ranges"
              :cinsiyetler="cinsiyetler"
            />
          </div>
        </button>
      </div>

      <!-- Alt kategoriler (girintili, DanismaYonetimi stili) -->
      <Transition name="tree-accordion">
        <div
          v-if="isExpanded(root) && childrenOf(root.id).length"
          class="ml-4 mt-0.5 space-y-0.5 border-l-2 border-gray-100 pl-2"
        >
          <button
            v-for="child in childrenOf(root.id)"
            :key="child.id"
            type="button"
            class="w-full text-left rounded-lg border px-2.5 py-2 flex items-center gap-2 group transition-all duration-150"
            :class="isSelected(child)
              ? ac.childSel
              : 'bg-white border-transparent hover:bg-gray-50 hover:border-gray-200 text-gray-600'"
            @click="select(child)"
          >
            <i
              :class="[icon(child), 'text-xs flex-shrink-0 transition-colors',
                       isSelected(child) ? ac.childIconSel : 'text-gray-400']"
            ></i>
            <span class="flex-1 text-xs font-medium truncate">{{ label(child) }}</span>
            <span v-if="!isItemActive(child)"
              class="text-[10px] px-1 py-0.5 bg-gray-100 text-gray-400 rounded font-bold flex-shrink-0">
              pasif
            </span>
            <button
              v-if="showEditButton"
              type="button"
              @click.stop="$emit('edit', child)"
              class="flex-shrink-0 p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition"
              title="Düzenle"
            >
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
          </button>
        </div>
      </Transition>

    </div>

    <!-- Boş durum -->
    <div v-if="items.length === 0" class="text-center py-10 text-gray-400 text-sm">
      <slot name="empty">
        <i class="fa-solid fa-folder-open text-xl mb-2 opacity-30 block"></i>
        Henüz kategori yok.
      </slot>
    </div>
  </div>
</template>

<style scoped>
.tree-accordion-enter-active,
.tree-accordion-leave-active {
  transition: max-height 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease;
  overflow: hidden;
  max-height: 800px;
}
.tree-accordion-enter-from,
.tree-accordion-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
