<script setup>
/**
 * CategoryCard
 * Sidebar için iki satırlık kategori kartı.
 *
 * Satır 1: ikon + ad + hassas rozeti + düzenle butonu
 * Satır 2: AlgorithmTargetBadges (cinsiyet + yaş aralığı)
 *
 * Props:
 *   cat        – { id, name, icon, is_sensitive, target_gender, target_age_ranges }
 *   active     – boolean — seçili mi?
 *   cinsiyetler – { id, kod, ad }[]
 */
import AlgorithmTargetBadges from './AlgorithmTargetBadges.vue';

defineOptions({ name: 'CategoryCard' });

defineProps({
  cat:         { required: true },
  active:      { default: false },
  cinsiyetler: { default: () => [] },
});

defineEmits(['select', 'edit']);
</script>

<template>
  <button
    type="button"
    :id="`cat-card-${cat.id}`"
    :name="`cat-card-${cat.id}`"
    class="cat-item w-full text-left rounded-xl border transition-all duration-150 group"
    :class="active
      ? 'bg-blue-50 border-blue-300 ring-1 ring-blue-300 text-blue-800'
      : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700'"
    @click="$emit('select', cat.id)"
  >
    <!-- Satır 1: ikon + ad + hassas + düzenle -->
    <div class="flex items-center gap-2 px-3 pt-2.5 pb-1">
      <!-- ikon -->
      <span
        class="w-6 h-6 flex items-center justify-center rounded-md flex-shrink-0 text-sm"
        :class="active ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'"
      >
        <i :class="cat.icon || 'fa-solid fa-pills'"></i>
      </span>

      <!-- ad -->
      <span class="flex-1 text-sm font-semibold leading-tight truncate">{{ cat.name }}</span>

      <!-- düzenle butonu -->
      <button
        type="button"
        @click.stop="$emit('edit', cat)"
        class="flex-shrink-0 p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-100 opacity-0 group-hover:opacity-100 transition"
        title="Düzenle"
      >
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
      </button>
    </div>

    <!-- Satır 2: badge'ler + aktif nokta -->
    <div class="flex items-center justify-between px-3 pb-2.5">
      <AlgorithmTargetBadges
        :target-gender="cat.target_gender"
        :target-age-ranges="cat.target_age_ranges"
        :cinsiyetler="cinsiyetler"
      />      
       <!-- hassas rozeti -->
      <span
        v-if="cat.is_sensitive"
        class="flex-shrink-0 w-5 h-5 inline-flex items-center justify-center rounded-full bg-rose-100 text-rose-600 border border-rose-200"
        title="Hassas Durum"
      ><i class="fa-solid fa-circle-exclamation text-[11px]"></i></span>      
    </div>
  </button>
</template>
