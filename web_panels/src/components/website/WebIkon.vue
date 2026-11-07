<script setup>
/** Web sitesi ikon adını (Phosphor, PascalCase) ikon bileşeni olarak çizer. */
import { computed } from 'vue';
import { ikonBileseni } from '../../data/websiteIkonlari';

const props = defineProps({
  ad: { type: String, default: '' },
  size: { type: [Number, String], default: 20 },
  weight: { type: String, default: 'duotone' },
});
const bilesen = computed(() => ikonBileseni(props.ad));
</script>

<template>
  <component :is="bilesen" :size="size" :weight="weight" aria-hidden="true" />
</template>
