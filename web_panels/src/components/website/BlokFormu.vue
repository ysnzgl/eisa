<script setup>
/**
 * BlokFormu — Sayfa Editörü sağ paneli: seçili bloğun şemadan üretilen formu.
 * `blok` reaktif nesnesi yerinde güncellenir (veri, anchor_id, gorunur).
 */
import { computed } from 'vue';
import FieldRenderer from './FieldRenderer.vue';
import WebIkon from './WebIkon.vue';
import { altHata, hataMesajlari } from '../../lib/websiteForm';

const props = defineProps({
  blok: { type: Object, required: true },
  tipTanimi: { type: Object, default: null },
  hata: { type: [Object, Array], default: null },
  anchorHatasi: { type: String, default: '' },
});

const alanlar = computed(() => props.tipTanimi?.alanlar || []);
const anchorMesajlari = computed(() => {
  const m = hataMesajlari(altHata(props.hata, 'anchor_id'));
  return props.anchorHatasi ? [props.anchorHatasi, ...m] : m;
});
const genelMesajlar = computed(() => hataMesajlari(props.hata));

function alanGuncelle(ad, v) {
  // eslint-disable-next-line vue/no-mutating-props
  props.blok.veri[ad] = v;
}
function anchorGuncelle(e) {
  // Anchor yalnız küçük harf, rakam ve tire içerir.
  // eslint-disable-next-line vue/no-mutating-props
  props.blok.anchor_id = e.target.value.toLowerCase().replace(/\s+/g, '-');
}
</script>

<template>
  <div class="ws-blok-formu">
    <header class="ws-blok-formu-ust">
      <span class="ws-blok-ikon"><WebIkon :ad="tipTanimi?.ikon" :size="22" /></span>
      <div>
        <h2 class="ws-blok-formu-baslik">{{ tipTanimi?.ad || blok.tip }}</h2>
        <p v-if="tipTanimi?.aciklama" class="ws-yardim">{{ tipTanimi.aciklama }}</p>
      </div>
    </header>

    <p v-if="!tipTanimi" class="ws-uyari">
      <i class="fa-solid fa-triangle-exclamation"></i>
      "{{ blok.tip }}" blok tipi sunucu şemasında bulunamadı. Bu blok düzenlenemez; silebilir veya olduğu gibi bırakabilirsiniz.
    </p>
    <p v-for="m in genelMesajlar" :key="m" class="ws-alan-hata">{{ m }}</p>

    <div class="ws-alan ws-anchor" :class="{ 'ws-alan--hatali': anchorMesajlari.length }" data-alan-yolu="anchor_id">
      <div class="ws-alan-ust">
        <label class="eisa-field-label" :for="`anchor-${blok._key}`">Bölüm bağlantısı (anchor)</label>
      </div>
      <div class="eisa-input-group">
        <span class="eisa-input-prefix">#</span>
        <input :id="`anchor-${blok._key}`" class="eisa-field" :value="blok.anchor_id" maxlength="60"
          placeholder="ör. nasil-calisir" @input="anchorGuncelle" />
      </div>
      <p class="ws-yardim">Menüden veya butonlardan bu bloğa doğrudan gitmek için kullanılır. Küçük harf, rakam ve tire.</p>
      <p v-for="m in anchorMesajlari" :key="m" class="ws-alan-hata">{{ m }}</p>
    </div>

    <FieldRenderer v-for="alan in alanlar" :key="`${blok._key}-${alan.ad}`" :alan="alan"
      :model-value="blok.veri[alan.ad]" :hata="altHata(hata, alan.ad)" :yol="`b${blok._key}`"
      @update:model-value="(v) => alanGuncelle(alan.ad, v)" />
  </div>
</template>
