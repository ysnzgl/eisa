<script setup>
import { computed } from 'vue';

defineOptions({ name: 'TargetGenderBadge' });

const props = defineProps({
  targetGender: { default: null },
  cinsiyetler: { default: () => [] },
});

const genderEntry = computed(() =>
  props.targetGender !== null
    ? props.cinsiyetler.find((c) => c.id === props.targetGender) ?? null
    : null
);

function normalizeGender(entry) {
  const code = `${entry?.kod ?? ''}`.trim().toLowerCase();
  const name = `${entry?.ad ?? ''}`.trim().toLowerCase();
  if (code === 'e' || name.includes('erkek')) return 'male';
  if (code === 'k' || name.includes('kad')) return 'female';
  return 'other';
}

const genderKind = computed(() => {
  if (!genderEntry.value) return 'all';
  return normalizeGender(genderEntry.value);
});

const genderLabel = computed(() => {
  if (!genderEntry.value) return 'T';
  return genderEntry.value.kod ?? genderEntry.value.ad?.[0]?.toUpperCase() ?? '?';
});

const genderTooltip = computed(() =>
  genderEntry.value ? `Cinsiyet: ${genderEntry.value.ad}` : 'Cinsiyet: Tümü'
);

const genderClass = computed(() => {
  if (genderKind.value === 'male') return 'bg-sky-50 text-sky-700 border-sky-200';
  if (genderKind.value === 'female') return 'bg-pink-50 text-pink-700 border-pink-200';
  return 'bg-gray-100 text-gray-500 border-gray-200';
});
</script>

<template>
  <span
    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border leading-none transition"
    :class="genderClass"
    :title="genderTooltip"
  >
    <svg class="w-2.5 h-2.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <circle cx="12" cy="8" r="4"/>
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
    </svg>
    {{ genderLabel }}
  </span>
</template>