<script setup>
/**
 * YardimButonu — ekran başlığındaki "Yardım" butonu. Tıklanınca sağdan çekmece açar ve
 * o ekranın ne işe yaradığını (data/websiteYardim.js) gösterir; tam yardım dokümanına bağlantı verir.
 *
 *   <YardimButonu :konular="['sayfa-editoru', 'genel']" />
 */
import { computed, ref } from 'vue';
import { RouterLink } from 'vue-router';
import WsCekmece from './WsCekmece.vue';
import YardimIcerik from './YardimIcerik.vue';
import { YARDIM } from '../../data/websiteYardim';

const props = defineProps({
  /** Gösterilecek konu anahtarları; ilki çekmecenin başlığı olur. */
  konular: { type: Array, required: true },
});

const acik = ref(false);
const liste = computed(() => props.konular.map((k) => YARDIM[k]).filter(Boolean));
const ilk = computed(() => liste.value[0]);
</script>

<template>
  <button type="button" class="eisa-btn ws-yardim-btn" title="Bu ekran ne işe yarar?" @click="acik = true">
    <i class="fa-solid fa-circle-question"></i> Yardım
  </button>
  <WsCekmece :open="acik" :title="`Yardım — ${ilk?.baslik ?? ''}`" subtitle="Bu ekran ne işe yarar?" width="520px" @close="acik = false">
    <YardimIcerik v-for="(k, i) in liste" :key="k.key" :konu="k" :baslik-goster="i > 0" />
    <template #footer>
      <RouterLink :to="`/admin/web-sitesi/yardim#${ilk?.key ?? ''}`" class="eisa-btn" @click="acik = false">
        <i class="fa-solid fa-book-open"></i> Tüm yardım dokümanı
      </RouterLink>
      <button type="button" class="eisa-btn eisa-btn-ghost" @click="acik = false">Kapat</button>
    </template>
  </WsCekmece>
</template>