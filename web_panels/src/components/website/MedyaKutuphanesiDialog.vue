<script setup>
/**
 * MedyaKutuphanesiDialog — formlardan açılan "medya seç / yükle" diyaloğu.
 * emit('sec', medyaKaydi) sonrası diyalog kapanır.
 */
import MedyaYoneticisi from './MedyaYoneticisi.vue';

defineProps({
  open: { type: Boolean, default: false },
  seciliId: { type: [Number, String], default: null },
  baslik: { type: String, default: 'Medya Kütüphanesi' },
});
const emit = defineEmits(['close', 'sec']);

function sec(m) {
  emit('sec', m);
  emit('close');
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="eisa-modal-backdrop ws-ust-katman" @click.self="emit('close')">
      <div class="eisa-modal eisa-modal--big ws-medya-dialog" role="dialog" aria-modal="true" :aria-label="baslik">
        <div class="eisa-modal-header">
          <div>
            <h3 class="eisa-modal-title">{{ baslik }}</h3>
            <p class="ws-cekmece-alt">Bir görsele tıklayıp "Bu görseli kullan" deyin veya çift tıklayın.</p>
          </div>
          <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="eisa-modal-body">
          <MedyaYoneticisi secim-modu :secili-id="seciliId" :page-size="18" @sec="sec" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
