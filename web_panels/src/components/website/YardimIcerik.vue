<script setup>
/**
 * YardimIcerik — tek bir yardım konusunu (data/websiteYardim.js) render eder.
 * Hem yardım çekmecesinde (YardimButonu) hem tam yardım sayfasında (Yardim.vue) kullanılır.
 * Props: konu (YARDIM_KONULARI öğesi), bloklar ([{ tip, ad, aciklama, ikon }] — blok kataloğu için), baslikGoster
 */
defineProps({
  konu: { type: Object, required: true },
  bloklar: { type: Array, default: () => [] },
  baslikGoster: { type: Boolean, default: true },
});
</script>

<template>
  <section class="ws-yardim-konu">
    <h2 v-if="baslikGoster" class="ws-yardim-baslik">
      <i class="fa-solid" :class="konu.ikon"></i> {{ konu.baslik }}
    </h2>
    <p v-if="konu.ozet" class="ws-yardim-ozet">{{ konu.ozet }}</p>

    <ol v-if="konu.adimlar?.length" class="ws-yardim-adimlar">
      <li v-for="(a, i) in konu.adimlar" :key="i">{{ a }}</li>
    </ol>

    <dl v-if="konu.maddeler?.length" class="ws-yardim-maddeler">
      <div v-for="m in konu.maddeler" :key="m.baslik" class="ws-yardim-madde">
        <dt>{{ m.baslik }}</dt>
        <dd>{{ m.metin }}</dd>
      </div>
    </dl>

    <dl v-if="konu.blokListesi && bloklar.length" class="ws-yardim-maddeler ws-yardim-bloklar">
      <div v-for="b in bloklar" :key="b.tip" class="ws-yardim-madde">
        <dt>{{ b.ad }}</dt>
        <dd>{{ b.aciklama }}</dd>
      </div>
    </dl>

    <div v-if="konu.ipuclari?.length" class="ws-yardim-ipucu">
      <i class="fa-solid fa-lightbulb"></i>
      <ul>
        <li v-for="(ip, i) in konu.ipuclari" :key="i">{{ ip }}</li>
      </ul>
    </div>
  </section>
</template>