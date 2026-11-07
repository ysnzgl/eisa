<script setup>
/**
 * Web Sitesi › Blog — yazı listesi (durum filtresi) ve kategori yönetimi.
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import {
  listBlogYazilari, deleteBlogYazisi, listBlogKategorileri, createBlogKategori,
  updateBlogKategori, deleteBlogKategori,
} from '../../../services/website';
import { slugOlustur, SLUG_REGEX, tarihFormat } from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';
import { sorgudanOdaklan } from '../../../lib/websiteArama';

const router = useRouter();
const { confirm } = useConfirm();

const sekme = ref('yazilar');
const yazilar = ref([]);
const kategoriler = ref([]);
const loading = ref(false);
const durumFiltre = ref('hepsi');
const kategoriFiltre = ref('');
const arama = ref('');

const DURUMLAR = [
  { kod: 'hepsi', etiket: 'Tümü' },
  { kod: 'taslak', etiket: 'Taslak' },
  { kod: 'yayinda', etiket: 'Yayında' },
  { kod: 'zamanlanmis', etiket: 'Zamanlanmış' },
  { kod: 'arsiv', etiket: 'Arşiv' },
];

function zamanlanmis(y) {
  return y.durum === 'yayinda' && y.yayin_tarihi && new Date(y.yayin_tarihi) > new Date();
}
function durumBilgi(y) {
  if (zamanlanmis(y)) return { etiket: 'Zamanlanmış', sinif: 'eisa-pill-info' };
  if (y.durum === 'yayinda') return { etiket: 'Yayında', sinif: 'eisa-pill-success' };
  if (y.durum === 'arsiv') return { etiket: 'Arşiv', sinif: 'eisa-pill-warning' };
  return { etiket: 'Taslak', sinif: 'eisa-pill-muted' };
}

const filtreli = computed(() => {
  const q = arama.value.trim().toLocaleLowerCase('tr-TR');
  return yazilar.value.filter((y) => {
    if (durumFiltre.value === 'zamanlanmis' && !zamanlanmis(y)) return false;
    if (durumFiltre.value === 'yayinda' && (y.durum !== 'yayinda' || zamanlanmis(y))) return false;
    if (['taslak', 'arsiv'].includes(durumFiltre.value) && y.durum !== durumFiltre.value) return false;
    if (kategoriFiltre.value && String(y.kategori?.id ?? '') !== String(kategoriFiltre.value)) return false;
    if (q && !`${y.baslik} ${y.slug}`.toLocaleLowerCase('tr-TR').includes(q)) return false;
    return true;
  });
});
const sayilar = computed(() => Object.fromEntries(DURUMLAR.map((d) => [d.kod,
  d.kod === 'hepsi' ? yazilar.value.length
    : d.kod === 'zamanlanmis' ? yazilar.value.filter(zamanlanmis).length
      : d.kod === 'yayinda' ? yazilar.value.filter((y) => y.durum === 'yayinda' && !zamanlanmis(y)).length
        : yazilar.value.filter((y) => y.durum === d.kod).length])));

async function load() {
  loading.value = true;
  try {
    const [y, k] = await Promise.all([listBlogYazilari(), listBlogKategorileri()]);
    yazilar.value = y;
    kategoriler.value = [...k].sort((a, b) => (a.sira ?? 0) - (b.sira ?? 0));
  } catch { /* toast */ } finally {
    loading.value = false;
  }
}
onMounted(async () => {
  await load();
  kategoriHedefineGit();
});

// "Sitede ara" sonucu bir blog kategorisiyse (?kategori=<id>&alan=&q=) düzenleme formunu aç.
const route = useRoute();
function kategoriHedefineGit() {
  const k = kategoriler.value.find((x) => String(x.id) === String(route.query.kategori));
  if (!k) return;
  katDuzenle(k);
  sorgudanOdaklan(route.query, { ad: '#ws-kat-ad', slug: '#ws-kat-slug' });
}
watch(() => [route.query.kategori, route.query.q], () => { if (!loading.value) kategoriHedefineGit(); });

async function yaziSil(y) {
  const ok = await confirm({
    title: 'Yazıyı Sil',
    message: `"${y.baslik}" yazısı kalıcı olarak silinecek.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteBlogYazisi(y.id);
    toast.success('Yazı silindi.');
    yazilar.value = yazilar.value.filter((x) => x.id !== y.id);
  } catch { /* toast */ }
}

// ── Kategoriler ─────────────────────────────────────────────────────────────
const katForm = reactive({ id: null, ad: '', slug: '', sira: 0 });
const katSlugElle = ref(false);
const katAcik = ref(false);
const katKaydediliyor = ref(false);

function katYeni() {
  Object.assign(katForm, { id: null, ad: '', slug: '', sira: kategoriler.value.length });
  katSlugElle.value = false;
  katAcik.value = true;
}
function katDuzenle(k) {
  Object.assign(katForm, { id: k.id, ad: k.ad, slug: k.slug, sira: k.sira ?? 0 });
  katSlugElle.value = true;
  katAcik.value = true;
}
function katAdDegisti(e) {
  katForm.ad = e.target.value;
  if (!katSlugElle.value) katForm.slug = slugOlustur(katForm.ad);
}
async function katKaydet() {
  if (!katForm.ad.trim()) { toast.warning('Kategori adı zorunludur.'); return; }
  if (!SLUG_REGEX.test(katForm.slug)) { toast.warning('Slug yalnızca küçük harf, rakam ve tire içerebilir.'); return; }
  katKaydediliyor.value = true;
  const payload = { ad: katForm.ad.trim(), slug: katForm.slug, sira: Number(katForm.sira) || 0 };
  try {
    if (katForm.id) await updateBlogKategori(katForm.id, payload);
    else await createBlogKategori(payload);
    toast.success('Kategori kaydedildi.');
    katAcik.value = false;
    kategoriler.value = [...(await listBlogKategorileri())].sort((a, b) => (a.sira ?? 0) - (b.sira ?? 0));
  } catch { /* toast */ } finally {
    katKaydediliyor.value = false;
  }
}
async function katSil(k) {
  const kullanan = yazilar.value.filter((y) => y.kategori?.id === k.id).length;
  const ok = await confirm({
    title: 'Kategoriyi Sil',
    message: `"${k.ad}" kategorisi silinecek.${kullanan ? ` Bu kategorideki ${kullanan} yazı kategorisiz kalabilir.` : ''}`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteBlogKategori(k.id);
    toast.success('Kategori silindi.');
    kategoriler.value = kategoriler.value.filter((x) => x.id !== k.id);
  } catch { /* toast */ }
}
const yaziSayisi = (k) => yazilar.value.filter((y) => y.kategori?.id === k.id).length;
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Blog</h1>
        <p class="eisa-page-subtitle">Yazıları ve kategorileri yönetin. Zamanlanmış yazılar yayın tarihinde otomatik görünür.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['blog']" />
        <SiteOnizleButonu />
        <button type="button" class="eisa-btn" :disabled="loading" @click="load">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i> Yenile
        </button>
        <button v-if="sekme === 'yazilar'" type="button" class="eisa-btn eisa-btn-cta" @click="router.push('/admin/web-sitesi/blog/yeni')">
          <i class="fa-solid fa-plus"></i> Yeni Yazı
        </button>
        <button v-else type="button" class="eisa-btn eisa-btn-cta" @click="katYeni">
          <i class="fa-solid fa-plus"></i> Yeni Kategori
        </button>
      </div>
    </header>

    <nav class="ws-sekmeler" role="tablist">
      <button type="button" role="tab" class="ws-sekme" :class="{ 'is-active': sekme === 'yazilar' }" @click="sekme = 'yazilar'">
        Yazılar <span class="ws-sekme-sayi">{{ yazilar.length }}</span>
      </button>
      <button type="button" role="tab" class="ws-sekme" :class="{ 'is-active': sekme === 'kategoriler' }" @click="sekme = 'kategoriler'">
        Kategoriler <span class="ws-sekme-sayi">{{ kategoriler.length }}</span>
      </button>
    </nav>

    <template v-if="sekme === 'yazilar'">
      <section class="eisa-panel eisa-toolbar-panel">
        <div class="eisa-toolbar">
          <div class="ws-segment">
            <button v-for="d in DURUMLAR" :key="d.kod" type="button" :class="{ 'is-active': durumFiltre === d.kod }"
              @click="durumFiltre = d.kod">{{ d.etiket }} <span class="ws-sayac">{{ sayilar[d.kod] }}</span></button>
          </div>
          <select v-model="kategoriFiltre" class="eisa-field eisa-filter">
            <option value="">Tüm Kategoriler</option>
            <option v-for="k in kategoriler" :key="k.id" :value="String(k.id)">{{ k.ad }}</option>
          </select>
          <div class="eisa-search-wrap">
            <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
            <input v-model="arama" class="eisa-field eisa-search-field" placeholder="Başlık ara…" />
          </div>
        </div>
      </section>

      <section class="eisa-panel">
        <div class="eisa-table-wrap">
          <table class="eisa-table">
            <thead>
              <tr><th>Yazı</th><th>Kategori</th><th>Durum</th><th>Yayın Tarihi</th><th>Güncelleme</th><th class="actions-col">İşlem</th></tr>
            </thead>
            <tbody>
              <tr v-if="loading && !yazilar.length"><td colspan="6" class="empty-row">Yükleniyor…</td></tr>
              <tr v-else-if="!filtreli.length"><td colspan="6" class="empty-row">Kayıt bulunamadı</td></tr>
              <tr v-for="y in filtreli" :key="y.id" class="ws-tiklanir" @click="router.push(`/admin/web-sitesi/blog/${y.id}`)">
                <td>
                  <div class="eisa-cell-name">{{ y.baslik }}</div>
                  <div class="eisa-cell-sub ws-mono">/blog/{{ y.slug }}</div>
                </td>
                <td>{{ y.kategori?.ad || '—' }}</td>
                <td><span class="eisa-pill" :class="durumBilgi(y).sinif">{{ durumBilgi(y).etiket }}</span></td>
                <td class="cell-muted">{{ tarihFormat(y.yayin_tarihi) }}</td>
                <td class="cell-muted">{{ tarihFormat(y.guncellenme_tarihi) }}</td>
                <td class="cell-actions" @click.stop>
                  <RouterLink :to="`/admin/web-sitesi/blog/${y.id}`" class="eisa-icon-btn" title="Düzenle" aria-label="Düzenle">
                    <i class="fa-solid fa-pen"></i>
                  </RouterLink>
                  <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="yaziSil(y)">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <section v-else class="eisa-panel">
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead><tr><th>Sıra</th><th>Kategori</th><th>Slug</th><th>Yazı</th><th class="actions-col">İşlem</th></tr></thead>
          <tbody>
            <tr v-if="!kategoriler.length"><td colspan="5" class="empty-row">Henüz kategori yok</td></tr>
            <tr v-for="k in kategoriler" :key="k.id">
              <td class="cell-muted">{{ k.sira }}</td>
              <td class="eisa-cell-name">{{ k.ad }}</td>
              <td class="ws-mono cell-muted">{{ k.slug }}</td>
              <td>{{ yaziSayisi(k) }}</td>
              <td class="cell-actions">
                <button type="button" class="eisa-icon-btn" title="Düzenle" aria-label="Düzenle" @click="katDuzenle(k)"><i class="fa-solid fa-pen"></i></button>
                <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="katSil(k)"><i class="fa-solid fa-trash"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="katAcik" class="eisa-modal-backdrop" @click.self="katAcik = false">
        <form class="eisa-modal" role="dialog" aria-modal="true" aria-label="Kategori" @submit.prevent="katKaydet">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ katForm.id ? 'Kategoriyi Düzenle' : 'Yeni Kategori' }}</h3>
            <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="katAcik = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body ws-form-dikey">
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-kat-ad">Ad<span class="ws-zorunlu">*</span></label>
              <input id="ws-kat-ad" :value="katForm.ad" class="eisa-field" maxlength="80" @input="katAdDegisti" />
            </div>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-kat-slug">Slug<span class="ws-zorunlu">*</span></label>
              <input id="ws-kat-slug" v-model="katForm.slug" class="eisa-field" maxlength="80" @input="katSlugElle = true" />
            </div>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-kat-sira">Sıra</label>
              <input id="ws-kat-sira" v-model.number="katForm.sira" type="number" class="eisa-field ws-sayi" />
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button type="button" class="eisa-btn eisa-btn-ghost" @click="katAcik = false">Vazgeç</button>
            <button type="submit" class="eisa-btn eisa-btn-cta" :disabled="katKaydediliyor">
              <i class="fa-solid fa-check"></i> Kaydet
            </button>
          </div>
        </form>
      </div>
    </Teleport>
  </div>
</template>
