<script setup>
/**
 * Web Sitesi › Yardım — modülün tam kullanım dokümanı.
 * İçerik: data/websiteYardim.js; blok kataloğu API'deki blok tiplerinden (ad + açıklama) gelir.
 * URL hash'i (#sayfa-editoru gibi) ilgili konuya kaydırır.
 */
import { nextTick, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import YardimIcerik from '../../../components/website/YardimIcerik.vue';
import { YARDIM_KONULARI } from '../../../data/websiteYardim';
import { listBlokTipleri } from '../../../services/website';

const route = useRoute();
const bloklar = ref([]);
const aktif = ref(YARDIM_KONULARI[0].key);

function kaydir(key, yumusak = true) {
  const el = document.getElementById(`yardim-${key}`);
  if (!el) return;
  aktif.value = key;
  el.scrollIntoView({ behavior: yumusak ? 'smooth' : 'auto', block: 'start' });
}

/** İçindekilerden seçim: kaydır + adres çubuğundaki hash'i güncelle (yeniden yönlendirme olmadan). */
function sec(key) {
  kaydir(key);
  window.history.replaceState(window.history.state, '', `#${key}`);
}

onMounted(async () => {
  try {
    bloklar.value = await listBlokTipleri();
  } catch { /* blok listesi opsiyonel */ }
  await nextTick();
  const hash = route.hash?.slice(1);
  if (hash) kaydir(hash, false);
});
watch(() => route.hash, (h) => { if (h) kaydir(h.slice(1)); });
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Yardım</h1>
        <p class="eisa-page-subtitle">eisa.com.tr içeriklerini yönetmek için adım adım kullanım kılavuzu.</p>
      </div>
    </header>

    <div class="ws-yardim-duzen">
      <nav class="ws-yardim-icindekiler eisa-panel" aria-label="Yardım konuları">
        <p class="ws-mini-label">Konular</p>
        <a v-for="k in YARDIM_KONULARI" :key="k.key" :href="`#${k.key}`"
          class="ws-yardim-toc" :class="{ 'is-active': aktif === k.key }"
          @click.prevent="sec(k.key)">
          <i class="fa-solid" :class="k.ikon"></i> {{ k.baslik }}
        </a>
      </nav>

      <div class="ws-yardim-govde">
        <article v-for="k in YARDIM_KONULARI" :id="`yardim-${k.key}`" :key="k.key" class="eisa-panel eisa-panel-body ws-yardim-kart">
          <YardimIcerik :konu="k" :bloklar="bloklar" />
          <RouterLink v-if="k.rota" :to="k.rota" class="ws-yardim-git">
            Ekrana git <i class="fa-solid fa-arrow-right"></i>
          </RouterLink>
        </article>
      </div>
    </div>
  </div>
</template>