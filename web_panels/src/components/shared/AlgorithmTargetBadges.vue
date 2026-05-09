<script setup>
/**
 * AlgorithmTargetBadges
 * Algoritma hedefleme özetini küçük ikonlu badge'ler olarak gösterir.
 * Hem kategori sidebar'ı hem soru kartları için kullanılır.
 *
 * Props:
 *   targetGender    – FK id | null  → cinsiyet badge (E / K / T)
 *   targetAgeRanges – number[]      → yaş aralığı sayısı badge
 *   ingredientCount – number | null → etken madde sayısı badge (null = gizle)
 *   cinsiyetler     – { id, kod, ad }[] → cinsiyet lookup listesi
 */
import { computed } from 'vue';
import TargetGenderBadge from './TargetGenderBadge.vue';

defineOptions({ name: 'AlgorithmTargetBadges' });

const props = defineProps({
  targetGender:    { default: null },
  targetAgeRanges: { default: () => [] },
  ingredientCount: { default: null },   // null → badge gösterilmez
  cinsiyetler:     { default: () => [] },
});

const ageCount = computed(() => (props.targetAgeRanges ?? []).length);
</script>

<template>
  <!-- wrapper: satır içi küçük badge grubu -->
  <span class="inline-flex items-center gap-1">

    <!-- ① Etken Madde badge (sadece ingredientCount verilmişse) -->
    <span
      v-if="ingredientCount !== null"
      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border leading-none transition"
      :class="ingredientCount > 0
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : 'bg-gray-100 text-gray-400 border-gray-200'"
      :title="`${ingredientCount} etken madde`"
    >
      <!-- yaprak ikonu -->
      <svg class="w-2.5 h-2.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1-2.3A4.49 4.49 0 0 0 8 20C19 20 22 3 22 3c-1 2-8 2-10 5.5 1.06-.69 2.21-1.19 3.45-1.5A6 6 0 0 0 17 8Z"/>
      </svg>
      {{ ingredientCount }}
    </span>

    <!-- ② Yaş Aralığı badge -->
    <span
      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border leading-none transition"
      :class="ageCount > 0
        ? 'bg-violet-50 text-violet-700 border-violet-200'
        : 'bg-gray-100 text-gray-400 border-gray-200'"
      :title="ageCount > 0 ? `${ageCount} yaş aralığı` : 'Yaş aralığı: Tümü'"
    >
      <!-- takvim ikonu -->
      <svg class="w-2.5 h-2.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8"  y1="2" x2="8"  y2="6"/>
        <line x1="3"  y1="10" x2="21" y2="10"/>
      </svg>
      {{ ageCount > 0 ? ageCount : '∞' }}
    </span>

    <!-- ③ Cinsiyet badge -->
    <TargetGenderBadge :target-gender="targetGender" :cinsiyetler="cinsiyetler" />

  </span>
</template>
