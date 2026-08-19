<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Ara…' },
  loading: { type: Boolean, default: false },
  clearable: { type: Boolean, default: true },
  maxVisible: { type: Number, default: 8 },
});
const emit = defineEmits(['update:modelValue']);

const rootEl = ref(null);
const query = ref('');
const open = ref(false);

const selected = computed(() =>
  props.options.filter((opt) =>
    props.modelValue.some((id) => String(id) === String(opt.id))
  )
);

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  const base = props.options.filter((opt) => !props.modelValue.some((id) => String(id) === String(opt.id)));
  if (!q) return base.slice(0, props.maxVisible);
  return base.filter((opt) => {
    const label = (opt.label || '').toLowerCase();
    const sub = (opt.sub || '').toLowerCase();
    return label.includes(q) || sub.includes(q);
  }).slice(0, props.maxVisible);
});

function toggleOption(opt) {
  if (!opt || opt.disabled) return;
  const next = [...props.modelValue.map((id) => String(id))];
  const value = String(opt.id);
  if (!next.includes(value)) next.push(value);
  emit('update:modelValue', next.map((id) => Number(id)));
  query.value = '';
  open.value = true;
}

function removeSelected(id) {
  emit('update:modelValue', props.modelValue
    .map((v) => Number(v))
    .filter((v) => Number(v) !== Number(id))
  );
}

function handleClickOutside(event) {
  if (rootEl.value && !rootEl.value.contains(event.target)) {
    open.value = false;
    query.value = '';
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside));
onBeforeUnmount(() => document.removeEventListener('mousedown', handleClickOutside));
</script>

<template>
  <div class="eisa-multi-lookup" ref="rootEl">
    <div class="eisa-multi-lookup__box" :class="{ 'eisa-multi-lookup__box--open': open }" @click="open = true">
      <div v-if="selected.length" class="eisa-multi-lookup__chips">
        <button
          v-for="opt in selected"
          :key="opt.id"
          type="button"
          class="eisa-multi-lookup__chip"
          @click.stop="removeSelected(opt.id)"
        >
          <span>{{ opt.label }}</span>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="eisa-multi-lookup__input-row">
        <i class="fa-solid fa-magnifying-glass eisa-multi-lookup__icon"></i>
        <input
          v-model="query"
          type="text"
          class="eisa-multi-lookup__input"
          :placeholder="placeholder"
          autocomplete="off"
          @focus="open = true"
        />
      </div>
    </div>

    <div v-if="open" class="eisa-multi-lookup__dropdown">
      <div v-if="filtered.length" class="eisa-multi-lookup__list">
        <button
          v-for="opt in filtered"
          :key="opt.id"
          type="button"
          class="eisa-multi-lookup__item"
          @click="toggleOption(opt)"
        >
          <span class="eisa-multi-lookup__item-label">{{ opt.label }}</span>
          <span v-if="opt.sub" class="eisa-multi-lookup__item-sub">{{ opt.sub }}</span>
        </button>
      </div>
      <div v-else class="eisa-multi-lookup__empty">Sonuç bulunamadı</div>
    </div>
  </div>
</template>

<style scoped>
.eisa-multi-lookup {
  position: relative;
  width: 100%;
}

.eisa-multi-lookup__box {
  width: 100%;
  min-height: 2.8rem;
  border: 1.5px solid #D1D5DB;
  border-radius: 12px;
  background: #fff;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04);
  padding: 0.45rem 0.7rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.eisa-multi-lookup__box--open,
.eisa-multi-lookup__box:focus-within {
  border-color: #B1121B;
  box-shadow: 0 0 0 3px rgba(177, 18, 27, 0.12);
}

.eisa-multi-lookup__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}

.eisa-multi-lookup__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid #C7D2FE;
  background: #EEF2FF;
  color: #4338CA;
  border-radius: 999px;
  padding: 0.22rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}

.eisa-multi-lookup__chip i {
  font-size: 0.68rem;
  opacity: 0.8;
}

.eisa-multi-lookup__input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 1.4rem;
}

.eisa-multi-lookup__icon {
  font-size: 0.76rem;
  color: #6B7280;
}

.eisa-multi-lookup__input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  color: #111827;
  font-size: 0.9rem;
  font-family: inherit;
  outline: none;
  padding: 0;
}

.eisa-multi-lookup__input::placeholder {
  color: #9CA3AF;
}

.eisa-multi-lookup__dropdown {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 0.35rem);
  z-index: 20;
  background: #fff;
  border: 1px solid #D1D5DB;
  border-radius: 10px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}

.eisa-multi-lookup__list {
  max-height: 240px;
  overflow-y: auto;
}

.eisa-multi-lookup__item {
  display: block;
  width: 100%;
  text-align: left;
  background: #fff;
  border: none;
  padding: 0.6rem 0.75rem;
  cursor: pointer;
  color: #374151;
}

.eisa-multi-lookup__item:hover {
  background: #ECFDF5;
}

.eisa-multi-lookup__item-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
}

.eisa-multi-lookup__item-sub {
  display: block;
  font-size: 0.72rem;
  color: #6B7280;
  margin-top: 0.1rem;
}

.eisa-multi-lookup__empty {
  padding: 0.75rem 0.9rem;
  font-size: 0.8rem;
  color: #6B7280;
  text-align: center;
}
</style>
