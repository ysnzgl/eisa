<script setup>
/**
 * ButonAlani — CONTRACT §2 Buton: { etiket, href, stil }.
 * hata: { etiket?: [..], href?: [..] } | string[]
 */
import { computed } from 'vue';
import { BUTON_STILLERI, altHata, hataMesajlari } from '../../lib/websiteForm';

const props = defineProps({
  modelValue: { type: Object, default: null },
  hata: { type: [Object, Array], default: null },
  idOnek: { type: String, default: 'btn' },
  zorunlu: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const deger = computed(() => ({ etiket: '', href: '', stil: 'birincil', ...(props.modelValue || {}) }));

function guncelle(anahtar, v) {
  const yeni = { ...deger.value, [anahtar]: v };
  // Opsiyonel buton tamamen boşaltılırsa null gönderilir (backend boş nesneyi reddeder).
  if (!props.zorunlu && !yeni.etiket.trim() && !yeni.href.trim()) {
    emit('update:modelValue', null);
    return;
  }
  emit('update:modelValue', yeni);
}
const hEtiket = computed(() => hataMesajlari(altHata(props.hata, 'etiket')));
const hHref = computed(() => hataMesajlari(altHata(props.hata, 'href')));
const hStil = computed(() => hataMesajlari(altHata(props.hata, 'stil')));
</script>

<template>
  <div class="ws-buton-alani">
    <div class="ws-buton-satir">
      <div class="ws-buton-etiket">
        <label class="ws-mini-label" :for="`${idOnek}-etiket`">Etiket</label>
        <input :id="`${idOnek}-etiket`" class="eisa-field" :class="{ 'ws-hatali': hEtiket.length }"
          :value="deger.etiket" maxlength="60" placeholder="ör. Pilot Süreci İncele"
          @input="guncelle('etiket', $event.target.value)" />
      </div>
      <div class="ws-buton-stil">
        <label class="ws-mini-label" :for="`${idOnek}-stil`">Stil</label>
        <select :id="`${idOnek}-stil`" class="eisa-field" :value="deger.stil" @change="guncelle('stil', $event.target.value)">
          <option v-for="s in BUTON_STILLERI" :key="s.deger" :value="s.deger">{{ s.etiket }}</option>
        </select>
      </div>
    </div>
    <div>
      <label class="ws-mini-label" :for="`${idOnek}-href`">Bağlantı</label>
      <input :id="`${idOnek}-href`" class="eisa-field" :class="{ 'ws-hatali': hHref.length }"
        :value="deger.href" placeholder="/#pilot, /iletisim, https://…, mailto:…, tel:…"
        @input="guncelle('href', $event.target.value)" />
    </div>
    <p v-for="m in [...hEtiket, ...hHref, ...hStil]" :key="m" class="ws-alan-hata">{{ m }}</p>
  </div>
</template>
