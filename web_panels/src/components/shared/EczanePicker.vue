<script setup>
/**
 * EczanePicker — "İl / İlçe / Eczane" birleşik etiketiyle eczane AutoComplete.
 * Veriyi ilk mount'ta kendi yükler; aynı sayfadaki KioskPicker ile önbelleği paylaşır.
 *
 * Props  : modelValue (eczane id | null), provinceId, placeholder
 * Emits  : update:modelValue
 */
import { computed, onMounted } from 'vue';
import { usePharmacyLookups } from '../../composables/usePharmacyLookups.js';
import EisaLookup from './EisaLookup.vue';

const props = defineProps({
  modelValue:  { default: null },
  provinceId:  { default: null },
  placeholder: { type: String, default: 'İl / İlçe / Eczane ara…' },
});
const emit = defineEmits(['update:modelValue']);

const { pharmacies, loading, ensureLoaded } = usePharmacyLookups();

const options = computed(() =>
  pharmacies.value
    .filter((p) => !props.provinceId || String(p.il) === String(props.provinceId))
    .map((p) => ({
    id:    p.id,
    label: [p.ilAdi, p.ilceAdi, p.name].filter(Boolean).join(' / '),
  }))
);

onMounted(ensureLoaded);
</script>

<template>
  <EisaLookup
    :model-value="modelValue"
    :options="options"
    :loading="loading"
    :placeholder="placeholder"
    :clearable="true"
    @update:model-value="(v) => emit('update:modelValue', v)"
  />
</template>
