<script setup>
/**
 * KioskPicker — "İl / İlçe / Eczane / Kiosk" birleşik etiketiyle kiosk AutoComplete.
 * Veriyi ilk mount'ta kendi yükler; aynı sayfadaki EczanePicker ile önbelleği paylaşır.
 * eczaneId prop'u verilirse sadece o eczanenin kiosklarını listeler.
 *
 * Props  : modelValue (kiosk id | null), eczaneId (filtre, opsiyonel), placeholder
 * Emits  : update:modelValue
 */
import { computed, onMounted, watch } from 'vue';
import { usePharmacyLookups } from '../../composables/usePharmacyLookups.js';
import EisaLookup from './EisaLookup.vue';

const props = defineProps({
  modelValue:  { default: null },
  eczaneId:    { default: null },
  placeholder: { type: String, default: 'İl / İlçe / Eczane / Kiosk ara…' },
});
const emit = defineEmits(['update:modelValue']);

const { pharmacies, kiosks, loading, ensureLoaded } = usePharmacyLookups();

const pharmMap = computed(() =>
  Object.fromEntries(pharmacies.value.map((p) => [String(p.id), p]))
);

const options = computed(() => {
  const source = props.eczaneId
    ? kiosks.value.filter((k) => String(k.pharmacyId) === String(props.eczaneId))
    : kiosks.value;
  return source.map((k) => {
    const p     = pharmMap.value[String(k.pharmacyId)];
    const label = [p?.ilAdi, p?.ilceAdi, p?.name, k.ad || k.mac].filter(Boolean).join(' / ');
    return { id: k.id, label };
  });
});

// Eczane değişince seçili kiosk'u temizle
watch(() => props.eczaneId, () => {
  if (props.modelValue != null) emit('update:modelValue', null);
});

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
