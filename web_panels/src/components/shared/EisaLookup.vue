<script setup>
/**
 * EisaLookup — Generic autocomplete / type-ahead select component.
 *
 * Props:
 *   modelValue   : selected item id (v-model)
 *   options      : Array<{ id, label, sub? }>  — full list to filter
 *   placeholder  : String  (default "Ara…")
 *   loading      : Boolean  (shows spinner while options are fetching)
 *   clearable    : Boolean  (show ✕ button when something is selected)
 *
 * Emits:
 *   update:modelValue  — emits the selected item id (or null on clear)
 *
 * Usage:
 *   <EisaLookup v-model="selectedId" :options="pharmacies" placeholder="Eczane ara..." />
 *   where pharmacies = [{ id: 1, label: 'Merkez Eczanesi', sub: 'İstanbul / Kadıköy' }]
 */
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  modelValue: { default: null },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Ara…' },
  loading: { type: Boolean, default: false },
  clearable: { type: Boolean, default: true },
});
const emit = defineEmits(['update:modelValue']);

const query = ref('');
const open = ref(false);
const rootEl = ref(null);

// Currently selected option object
const selected = computed(() =>
  props.modelValue != null
    ? props.options.find((o) => String(o.id) === String(props.modelValue)) || null
    : null,
);

// Filtered list
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.options.slice(0, 60);  // limit for performance
  return props.options
    .filter((o) => o.label.toLowerCase().includes(q) || (o.sub || '').toLowerCase().includes(q))
    .slice(0, 60);
});

function select(opt) {
  if (opt.disabled) return;
  emit('update:modelValue', opt.id);
  query.value = '';
  open.value = false;
}

function clear() {
  emit('update:modelValue', null);
  query.value = '';
  open.value = false;
}

function onFocus() {
  open.value = true;
}

function onClickOutside(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) {
    open.value = false;
    query.value = '';
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside));
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside));
</script>

<template>
  <div class="eisa-lookup" ref="rootEl">
    <!-- Trigger -->
    <div class="lookup-trigger" :class="{ 'lookup-open': open }" @click="open = !open">
      <span v-if="loading" class="lookup-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i></span>
      <span v-else-if="selected" class="lookup-selected">
        <strong>{{ selected.label }}</strong>
        <span v-if="selected.sub" class="lookup-sub"> — {{ selected.sub }}</span>
      </span>
      <span v-else class="lookup-placeholder">{{ placeholder }}</span>
      <div class="lookup-icons">
        <button v-if="clearable && selected" type="button" class="lookup-clear" @click.stop="clear" title="Temizle">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <i class="fa-solid fa-chevron-down lookup-caret" :class="{ 'lookup-caret-up': open }"></i>
      </div>
    </div>

    <!-- Dropdown -->
    <div v-if="open" class="lookup-dropdown">
      <div class="lookup-search">
        <i class="fa-solid fa-magnifying-glass lookup-search-icon"></i>
        <input
          ref="inputEl"
          v-model="query"
          class="lookup-input"
          :placeholder="placeholder"
          autofocus
          @click.stop
        />
      </div>
      <div class="lookup-list">
        <div v-if="!filtered.length" class="lookup-empty">Sonuç bulunamadı</div>
        <button
          v-for="opt in filtered"
          :key="opt.id"
          type="button"
          class="lookup-item"
          :class="{ 'lookup-item--active': String(opt.id) === String(modelValue), 'lookup-item--disabled': opt.disabled }"
          :disabled="opt.disabled"
          @click="select(opt)"
        >
          <span class="lookup-item-label">{{ opt.label }}</span>
          <span v-if="opt.sub" class="lookup-item-sub">{{ opt.sub }}</span>
          <span v-if="opt.disabled && opt.disabledReason" class="lookup-item-sub lookup-item-disabled-reason">{{ opt.disabledReason }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
