<script setup>
/**
 * SiteArama — Web Sitesi modülünde "Sitede ara" penceresi (Ctrl/⌘ + K).
 * Tüm site içeriğinde (sayfa blokları, SEO, blog, menüler, ayarlar) arar; sonuca tıklayınca
 * ilgili editör açılır, alan bulunur, vurgulanır ve aranan ifade seçili gelir.
 *
 * Açma: Ctrl/⌘+K veya `ac()` (AdminLayout'taki "Sitede ara" butonu).
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { siteAra } from '../../services/website';
import { hedefRotasi } from '../../lib/websiteArama';

const router = useRouter();

const acik = ref(false);
const q = ref('');
const yukleniyor = ref(false);
const hata = ref('');
const veri = ref(null);
const aktif = ref(0);
const girdi = ref(null);
const liste = ref(null);
let zamanlayici = null;
let iptal = null;

const GRUP_IKON = {
  sayfa: 'fa-file-lines', blog: 'fa-newspaper', blog_kategori: 'fa-tags', menu: 'fa-bars-staggered',
  ayarlar: 'fa-sliders', medya: 'fa-photo-film',
};
const DURUM = { yayinda: 'Yayında', taslak: 'Taslak', arsiv: 'Arşiv' };

const sonuclar = computed(() => veri.value?.sonuclar || []);
const gruplar = computed(() => {
  const harita = new Map();
  sonuclar.value.forEach((s, i) => {
    const k = `${s.grup.tur}:${s.grup.id}`;
    if (!harita.has(k)) harita.set(k, { anahtar: k, grup: s.grup, ogeler: [] });
    harita.get(k).ogeler.push({ s, i });
  });
  return [...harita.values()];
});

function ac() {
  acik.value = true;
  nextTick(() => {
    girdi.value?.focus();
    girdi.value?.select();
  });
}
function kapat() {
  acik.value = false;
}
defineExpose({ ac });

async function aramaYap(sorgu) {
  iptal?.abort();
  if (sorgu.trim().length < 2) {
    veri.value = null;
    yukleniyor.value = false;
    hata.value = '';
    return;
  }
  iptal = new AbortController();
  yukleniyor.value = true;
  hata.value = '';
  try {
    veri.value = await siteAra(sorgu.trim(), { signal: iptal.signal });
    aktif.value = 0;
  } catch (e) {
    if (e?.code === 'ERR_CANCELED' || e?.name === 'CanceledError') return;
    hata.value = 'Arama yapılamadı. Bağlantınızı kontrol edip tekrar deneyin.';
  } finally {
    yukleniyor.value = false;
  }
}

watch(q, (yeni) => {
  clearTimeout(zamanlayici);
  zamanlayici = setTimeout(() => aramaYap(yeni), 250);
});

function git(s) {
  if (!s) return;
  kapat();
  router.push(hedefRotasi(s, q.value.trim()));
}

function aktifiGorunurYap() {
  nextTick(() => {
    liste.value?.querySelector(`[data-sira="${aktif.value}"]`)?.scrollIntoView({ block: 'nearest' });
  });
}

function girdiKlavye(e) {
  const n = sonuclar.value.length;
  if (e.key === 'ArrowDown' && n) {
    e.preventDefault();
    aktif.value = (aktif.value + 1) % n;
    aktifiGorunurYap();
  } else if (e.key === 'ArrowUp' && n) {
    e.preventDefault();
    aktif.value = (aktif.value - 1 + n) % n;
    aktifiGorunurYap();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    git(sonuclar.value[aktif.value]);
  }
}

function genelKlavye(e) {
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    if (acik.value) girdi.value?.focus();
    else ac();
  } else if (e.key === 'Escape' && acik.value) {
    kapat();
  }
}
onMounted(() => window.addEventListener('keydown', genelKlavye));
onBeforeUnmount(() => {
  window.removeEventListener('keydown', genelKlavye);
  clearTimeout(zamanlayici);
  iptal?.abort();
});
</script>

<template>
  <Teleport to="body">
    <Transition name="ws-arama">
      <div v-if="acik" class="ws-arama-arkaplan" @mousedown.self="kapat">
        <div class="ws-arama" role="dialog" aria-modal="true" aria-label="Sitede ara">
          <div class="ws-arama-girdi">
            <i class="fa-solid" :class="yukleniyor ? 'fa-circle-notch fa-spin' : 'fa-magnifying-glass'"></i>
            <input ref="girdi" v-model="q" type="search" placeholder="Sitede ara… (ör. pilot, eczacı onayı, 1 ay ücretsiz)"
              aria-label="Aranacak ifade" aria-controls="ws-arama-sonuclar" autocomplete="off" spellcheck="false"
              @keydown="girdiKlavye" />
            <kbd>Esc</kbd>
          </div>

          <div id="ws-arama-sonuclar" ref="liste" class="ws-arama-govde" role="listbox">
            <div v-if="hata" class="ws-arama-bilgi is-hata"><i class="fa-solid fa-triangle-exclamation"></i> {{ hata }}</div>

            <div v-else-if="q.trim().length < 2" class="ws-arama-bilgi">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
              <div>
                <strong>Sitenin her yerinde arayın</strong>
                <p>Sayfa blokları (metin, buton, sayı), SEO bilgileri, blog yazıları ve kategorileri, menüler, site ayarları ve görsel alternatif metinleri taranır.
                  Sonuca tıklayınca ilgili alan açılır ve ifade seçili gelir.</p>
                <p class="ws-arama-ipucu">Büyük/küçük harf ve Türkçe karakter fark etmez: "saglik" → "Sağlık".</p>
              </div>
            </div>

            <div v-else-if="!yukleniyor && veri && !sonuclar.length" class="ws-arama-bilgi">
              <i class="fa-regular fa-face-meh"></i>
              <div><strong>"{{ q.trim() }}" bulunamadı</strong><p>Farklı bir ifade veya daha kısa bir kelime deneyin.</p></div>
            </div>

            <template v-else>
              <section v-for="g in gruplar" :key="g.anahtar" class="ws-arama-grup">
                <header class="ws-arama-grup-baslik">
                  <i class="fa-solid" :class="GRUP_IKON[g.grup.tur] || 'fa-file'"></i>
                  <span>{{ g.grup.baslik }}</span>
                  <span v-if="g.grup.slug" class="ws-mono ws-arama-slug">/{{ g.grup.slug === 'anasayfa' ? '' : g.grup.slug }}</span>
                  <span v-if="g.grup.durum && g.grup.durum !== 'yayinda'" class="eisa-pill eisa-pill-warning">{{ DURUM[g.grup.durum] || g.grup.durum }}</span>
                </header>
                <button v-for="{ s, i } in g.ogeler" :key="i" type="button" role="option" :data-sira="i"
                  class="ws-arama-sonuc" :class="{ 'is-aktif': i === aktif }" :aria-selected="i === aktif"
                  @mousemove="aktif = i" @click="git(s)">
                  <span class="ws-arama-konum">
                    {{ s.konum.join(' › ') }}
                    <span v-if="s.blok?.gizli" class="ws-arama-etiket" title="Bu blok sitede gizli">gizli blok</span>
                    <span v-if="s.adet > 1" class="ws-arama-etiket">{{ s.adet }} eşleşme</span>
                  </span>
                  <span class="ws-arama-parca">{{ s.parca.onceki }}<mark>{{ s.parca.eslesen }}</mark>{{ s.parca.sonraki }}</span>
                  <i class="fa-solid fa-arrow-turn-down ws-arama-git" aria-hidden="true"></i>
                </button>
              </section>
            </template>
          </div>

          <footer class="ws-arama-alt">
            <span><kbd>↑</kbd><kbd>↓</kbd> gezin</span>
            <span><kbd>Enter</kbd> aç</span>
            <span><kbd>Esc</kbd> kapat</span>
            <span v-if="veri && sonuclar.length" class="ws-arama-sayi">
              {{ veri.toplam }} sonuç<template v-if="veri.kesildi"> · ilk {{ sonuclar.length }} gösteriliyor</template>
            </span>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>