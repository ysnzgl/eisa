<script setup>
import { computed } from 'vue';

defineOptions({ name: 'TargetGenderSelector' });

const props = defineProps({
  modelValue: { default: null },
  cinsiyetler: { default: () => [] },
  allLabel: { type: String, default: 'Tümü' },
});

const emit = defineEmits(['update:modelValue']);

function normalizeGender(entry) {
  const code = `${entry?.kod ?? ''}`.trim().toLowerCase();
  const name = `${entry?.ad ?? ''}`.trim().toLowerCase();
  if (code === 'e' || name.includes('erkek')) return 'male';
  if (code === 'k' || name.includes('kad')) return 'female';
  return 'other';
}

function buttonClass(isActive, kind) {
  if (!isActive) return 'bg-white text-gray-500 border-gray-300 hover:border-gray-400';
  if (kind === 'male') return 'bg-sky-100 text-sky-700 border-sky-400';
  if (kind === 'female') return 'bg-pink-100 text-pink-700 border-pink-400';
  return 'bg-gray-100 text-gray-700 border-gray-400';
}

const options = computed(() => props.cinsiyetler ?? []);

function onSelect(nextValue) {
  emit('update:modelValue', props.modelValue === nextValue ? null : nextValue);
}
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      type="button"
      @click="onSelect(null)"
      class="px-3 py-1 text-xs font-semibold rounded-full border transition"
      :class="buttonClass(modelValue === null, 'all')"
    >{{ allLabel }}</button>

    <button
      v-for="c in options"
      :key="c.id"
      type="button"
      @click="onSelect(c.id)"
      class="px-3 py-1 text-xs font-semibold rounded-full border transition"
      :class="buttonClass(modelValue === c.id, normalizeGender(c))"
    >{{ c.ad }}</button>
  </div>
</template>