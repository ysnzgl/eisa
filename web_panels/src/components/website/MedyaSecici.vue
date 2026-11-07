<script setup>
/**
 * MedyaSecici — form alanı: MediaRef | null (CONTRACT §2).
 * Önizleme + Seç/Değiştir/Kaldır. Seçim medya kütüphanesi diyaloğundan yapılır.
 */
import { ref } from 'vue';
import { medyaUrl } from '../../services/website';
import { medyaRef } from '../../lib/websiteForm';
import MedyaKutuphanesiDialog from './MedyaKutuphanesiDialog.vue';

defineProps({
  modelValue: { type: Object, default: null },
  hatali: { type: Boolean, default: false },
  kaldirilabilir: { type: Boolean, default: true },
});
const emit = defineEmits(['update:modelValue']);

const dialogAcik = ref(false);

function sec(m) {
  emit('update:modelValue', medyaRef(m));
}
</script>

<template>
  <div class="ws-medya-secici" :class="{ 'ws-hatali': hatali }">
    <div v-if="modelValue?.yol" class="ws-medya-secici-onizleme">
      <img :src="medyaUrl(modelValue.yol)" :alt="modelValue.alt || ''" />
    </div>
    <div v-else class="ws-medya-secici-bos" @click="dialogAcik = true">
      <i class="fa-regular fa-image"></i>
      <span>Görsel seçilmedi</span>
    </div>
    <div class="ws-medya-secici-bilgi">
      <span v-if="modelValue?.yol" class="ws-medya-secici-alt">
        {{ modelValue.alt || 'Alt metin yok' }}
        <template v-if="modelValue.genislik"> · {{ modelValue.genislik }}×{{ modelValue.yukseklik }}</template>
      </span>
      <div class="ws-medya-secici-aksiyon">
        <button type="button" class="eisa-btn eisa-btn--sm" @click="dialogAcik = true">
          <i class="fa-solid fa-photo-film"></i> {{ modelValue ? 'Değiştir' : 'Görsel seç' }}
        </button>
        <button v-if="modelValue && kaldirilabilir" type="button" class="eisa-btn eisa-btn--sm eisa-btn-ghost"
          @click="emit('update:modelValue', null)">
          <i class="fa-solid fa-xmark"></i> Kaldır
        </button>
      </div>
    </div>
    <MedyaKutuphanesiDialog :open="dialogAcik" :secili-id="modelValue?.id" @close="dialogAcik = false" @sec="sec" />
  </div>
</template>
