<script setup>
/** Web Sitesi › Medya Kütüphanesi — site görselleri (yükle, ara, alt metin, sil, URL kopyala). */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import MedyaYoneticisi from '../../../components/website/MedyaYoneticisi.vue';
import { useRoute } from 'vue-router';

// "Sitede ara" sonucundan gelindiğinde (?q=) liste o ifadeyle filtrelenmiş açılır.
const route = useRoute();
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Medya Kütüphanesi</h1>
        <p class="eisa-page-subtitle">Sayfa bloklarında, blog yazılarında ve paylaşım görsellerinde kullanılan görseller.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['medya']" />
        <SiteOnizleButonu />
      </div>
    </header>
    <section class="eisa-panel eisa-panel-body">
      <MedyaYoneticisi :baslangic-arama="typeof route.query.q === 'string' ? route.query.q : ''" />
    </section>
  </div>
</template>
