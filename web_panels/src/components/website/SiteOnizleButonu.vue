<script setup>
/**
 * SiteOnizleButonu — siteyi önizleme modunda (yayınlanmamış taslaklar dahil) yeni sekmede açar.
 * Yardım butonunun yanında, liste ekranlarının başlığında kullanılır. Varsayılan: anasayfa.
 *
 *   <SiteOnizleButonu />                // anasayfa
 *   <SiteOnizleButonu :sayfa-id="12" /> // belirli sayfa
 */
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import { listSayfalar, sayfaOnizleme } from '../../services/website';
import { humanError } from '../../services/api';

const props = defineProps({
  sayfaId: { type: Number, default: null },
});

const yukleniyor = ref(false);

async function hedefSayfaId() {
  if (props.sayfaId) return props.sayfaId;
  const sayfalar = await listSayfalar();
  return (sayfalar.find((s) => s.slug === 'anasayfa') ?? sayfalar[0])?.id ?? null;
}

async function onizle() {
  // Açılır pencere engelleyicisine takılmamak için sekme tıklama anında açılır.
  const sekme = window.open('about:blank', '_blank');
  yukleniyor.value = true;
  try {
    const id = await hedefSayfaId();
    if (!id) {
      sekme?.close();
      toast.error('Önizlenecek sayfa bulunamadı.');
      return;
    }
    const { url } = await sayfaOnizleme(id);
    if (sekme) sekme.location.href = url;
    else window.open(url, '_blank', 'noopener');
  } catch (e) {
    sekme?.close();
    toast.error(humanError(e));
  } finally {
    yukleniyor.value = false;
  }
}
</script>

<template>
  <button type="button" class="eisa-btn" :disabled="yukleniyor"
    title="Siteyi önizleme modunda açar: yayınlanmamış taslaklar dahil, yalnızca siz görürsünüz" @click="onizle">
    <i class="fa-solid" :class="yukleniyor ? 'fa-circle-notch fa-spin' : 'fa-eye'"></i> Önizle
  </button>
</template>