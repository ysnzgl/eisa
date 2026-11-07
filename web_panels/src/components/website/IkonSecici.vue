<script setup>
/**
 * IkonSecici — CONTRACT §2 ikon listesinden aranabilir seçim.
 * v-model: ikon adı (ör. "ShieldCheck") | ''
 */
import { computed, nextTick, onBeforeUnmount, ref } from 'vue';
import { WEBSITE_IKONLARI } from '../../data/websiteIkonlari';
import WebIkon from './WebIkon.vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  zorunlu: { type: Boolean, default: false },
  hatali: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const acik = ref(false);
const arama = ref('');
const kok = ref(null);
const aramaInput = ref(null);

const liste = computed(() => {
  const q = arama.value.trim().toLocaleLowerCase('tr-TR');
  if (!q) return WEBSITE_IKONLARI;
  return WEBSITE_IKONLARI.filter((i) =>
    i.ad.toLocaleLowerCase('tr-TR').includes(q) || i.etiketler.includes(q));
});

function disariTik(e) {
  if (kok.value && !kok.value.contains(e.target)) kapat();
}
async function ac() {
  acik.value = true;
  arama.value = '';
  document.addEventListener('mousedown', disariTik);
  await nextTick();
  aramaInput.value?.focus();
}
function kapat() {
  acik.value = false;
  document.removeEventListener('mousedown', disariTik);
}
function sec(ad) {
  emit('update:modelValue', ad);
  kapat();
}
onBeforeUnmount(() => document.removeEventListener('mousedown', disariTik));
</script>

<template>
  <div ref="kok" class="ws-ikon-secici">
    <button type="button" class="ws-ikon-tetik eisa-field" :class="{ 'ws-hatali': hatali }"
      :aria-expanded="acik" @click="acik ? kapat() : ac()">
      <span v-if="modelValue" class="ws-ikon-onizleme"><WebIkon :ad="modelValue" :size="20" /></span>
      <span class="ws-ikon-ad">{{ modelValue || 'İkon seçin' }}</span>
      <i class="fa-solid fa-chevron-down ws-ikon-ok"></i>
    </button>
    <div v-if="acik" class="ws-ikon-popover" role="listbox">
      <div class="ws-ikon-arama">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input ref="aramaInput" v-model="arama" class="eisa-field" placeholder="İkon ara (ör. kalkan, para, bulut)…"
          @keydown.esc.prevent="kapat" />
      </div>
      <div class="ws-ikon-grid">
        <button v-for="ikon in liste" :key="ikon.ad" type="button" class="ws-ikon-oge"
          :class="{ 'is-active': ikon.ad === modelValue }" :title="ikon.ad" @click="sec(ikon.ad)">
          <component :is="ikon.bilesen" :size="22" weight="duotone" />
          <span>{{ ikon.ad }}</span>
        </button>
        <p v-if="!liste.length" class="ws-bos-mini">Eşleşen ikon yok.</p>
      </div>
      <div v-if="!zorunlu && modelValue" class="ws-ikon-alt">
        <button type="button" class="eisa-btn eisa-btn-ghost eisa-btn--sm" @click="sec('')">
          <i class="fa-solid fa-eraser"></i> İkonu kaldır
        </button>
      </div>
    </div>
  </div>
</template>
