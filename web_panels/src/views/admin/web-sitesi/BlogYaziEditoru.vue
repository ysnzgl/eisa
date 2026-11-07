<script setup>
/**
 * Web Sitesi › Blog › Yazı Editörü (`/admin/web-sitesi/blog/:id`, yeni için `yeni`).
 *
 * Alanlar (CONTRACT §5 Blog): baslik, slug, ozet, kapak (MediaRef), icerik_html
 * (TipTap; görseller medya kütüphanesinden), kategori_id, etiketler, yazar_adi,
 * durum, yayin_tarihi, seo_baslik, seo_aciklama, okuma_suresi (salt-okunur), surum.
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { RouterLink, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import {
  getBlogYazisi, createBlogYazisi, updateBlogYazisi, listBlogKategorileri, blogYazisiOnizleme,
} from '../../../services/website';
import { humanError } from '../../../services/api';
import {
  slugOlustur, SLUG_REGEX, hatalariAgacaCevir, hataMesajlari, htmlMetin,
  isoToLocalInput, localInputToIso,
} from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';
import { useKaydedilmemisDegisiklik } from '../../../composables/useKaydedilmemisDegisiklik.js';
import ZenginMetinEditoru from '../../../components/website/ZenginMetinEditoru.vue';
import { sorgudanOdaklan } from '../../../lib/websiteArama';
import MedyaSecici from '../../../components/website/MedyaSecici.vue';

const route = useRoute();
const router = useRouter();
const { confirm } = useConfirm();

const DURUMLAR = [
  { deger: 'taslak', etiket: 'Taslak' },
  { deger: 'yayinda', etiket: 'Yayında' },
  { deger: 'arsiv', etiket: 'Arşiv' },
];

const bosForm = () => ({
  baslik: '', slug: '', ozet: '', kapak: null, icerik_html: '', kategori_id: null,
  etiketler: [], yazar_adi: '', durum: 'taslak', yayin_tarihi: '', seo_baslik: '', seo_aciklama: '',
});

const form = reactive(bosForm());
const yazi = ref(null); // sunucu kaydı (id, surum, okuma_suresi...)
const kategoriler = ref([]);
const yukleniyor = ref(true);
const yuklemeHatasi = ref('');
const islem = ref('');
const hatalar = ref({});
const cakisma = ref(false);
const slugElle = ref(false);
const etiketGirdi = ref('');
const kayitli = ref('');

const yeni = computed(() => route.params.id === 'yeni');

function payload() {
  return {
    baslik: form.baslik.trim(),
    slug: form.slug,
    ozet: form.ozet,
    kapak: form.kapak || null,
    icerik_html: form.icerik_html,
    kategori_id: form.kategori_id || null,
    etiketler: [...form.etiketler],
    yazar_adi: form.yazar_adi,
    durum: form.durum,
    yayin_tarihi: localInputToIso(form.yayin_tarihi),
    seo_baslik: form.seo_baslik,
    seo_aciklama: form.seo_aciklama,
  };
}
const kirli = computed(() => !yukleniyor.value && JSON.stringify(payload()) !== kayitli.value);
const { onayla } = useKaydedilmemisDegisiklik(kirli);
onBeforeRouteUpdate(() => onayla());

function formUygula(d) {
  Object.assign(form, bosForm(), {
    baslik: d.baslik ?? '',
    slug: d.slug ?? '',
    ozet: d.ozet ?? '',
    kapak: d.kapak ?? null,
    icerik_html: d.icerik_html ?? '',
    kategori_id: d.kategori_id ?? d.kategori?.id ?? null,
    etiketler: Array.isArray(d.etiketler) ? [...d.etiketler] : [],
    yazar_adi: d.yazar_adi ?? '',
    durum: d.durum || 'taslak',
    yayin_tarihi: isoToLocalInput(d.yayin_tarihi),
    seo_baslik: d.seo_baslik ?? '',
    seo_aciklama: d.seo_aciklama ?? '',
  });
  kayitli.value = JSON.stringify(payload());
}

async function yukle() {
  yukleniyor.value = true;
  yuklemeHatasi.value = '';
  cakisma.value = false;
  hatalar.value = {};
  try {
    const kategoriIstegi = kategoriler.value.length ? Promise.resolve(kategoriler.value) : listBlogKategorileri();
    if (yeni.value) {
      kategoriler.value = await kategoriIstegi;
      yazi.value = null;
      slugElle.value = false;
      formUygula({});
    } else {
      const [d, k] = await Promise.all([getBlogYazisi(route.params.id), kategoriIstegi]);
      kategoriler.value = k;
      yazi.value = d;
      slugElle.value = true;
      formUygula(d);
    }
  } catch (e) {
    yuklemeHatasi.value = e?.response?.status === 404 ? 'Yazı bulunamadı.' : 'Yazı yüklenemedi.';
  } finally {
    yukleniyor.value = false;
  }
  if (yazi.value) sorgudanOdaklan(route.query, BLOG_ALAN_SECICI);
}
onMounted(yukle);

// "Sitede ara" sonucundan gelindiğinde ilgili alana odaklan (?alan=&q=)
const BLOG_ALAN_SECICI = {
  baslik: '#ws-blog-baslik', slug: '#ws-blog-slug', ozet: '#ws-blog-ozet',
  icerik_html: '[data-alan-yolu="icerik_html"]', etiketler: '#ws-blog-etiket', yazar_adi: '#ws-blog-yazar',
  seo_baslik: '#ws-blog-seo-baslik', seo_aciklama: '#ws-blog-seo-aciklama',
};
watch(() => [route.query.alan, route.query.q], () => { if (!yukleniyor.value && yazi.value) sorgudanOdaklan(route.query, BLOG_ALAN_SECICI); });
watch(() => route.params.id, (y, e) => { if (y && y !== e && !(e === 'yeni' && yazi.value?.id === Number(y))) yukle(); });

watch(() => form.baslik, (b) => { if (!slugElle.value) form.slug = slugOlustur(b); });

// ── Etiketler ────────────────────────────────────────────────────────────────
function etiketEkle() {
  const parcalar = etiketGirdi.value.split(',').map((s) => s.trim()).filter(Boolean);
  parcalar.forEach((p) => {
    if (!form.etiketler.some((e) => e.toLocaleLowerCase('tr-TR') === p.toLocaleLowerCase('tr-TR'))) form.etiketler.push(p);
  });
  etiketGirdi.value = '';
}
function etiketTus(e) {
  if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); etiketEkle(); }
  else if (e.key === 'Backspace' && !etiketGirdi.value && form.etiketler.length) form.etiketler.pop();
}

// ── Kaydet ───────────────────────────────────────────────────────────────────
function dogrula() {
  const h = {};
  if (!form.baslik.trim()) h.baslik = ['Başlık zorunludur.'];
  if (!form.slug) h.slug = ['Slug zorunludur.'];
  else if (!SLUG_REGEX.test(form.slug)) h.slug = ['Yalnızca küçük harf, rakam ve tire kullanılabilir.'];
  if (form.durum === 'yayinda' && !htmlMetin(form.icerik_html) && !/<img/i.test(form.icerik_html)) {
    h.icerik_html = ['Yayınlanacak yazının içeriği boş olamaz.'];
  }
  hatalar.value = h;
  return !Object.keys(h).length;
}

async function kaydet({ sessiz = false } = {}) {
  if (cakisma.value) { toast.warning('Önce yazının güncel halini yükleyin.'); return false; }
  if (!dogrula()) { toast.warning('Kaydetmeden önce işaretli alanları düzeltin.'); return false; }
  if (!kirli.value && !yeni.value) { if (!sessiz) toast.info('Kaydedilecek değişiklik yok.'); return true; }
  islem.value = islem.value || 'kaydet';
  try {
    let d;
    if (yeni.value) d = await createBlogYazisi(payload());
    else d = await updateBlogYazisi(yazi.value.id, { ...payload(), surum: yazi.value.surum });
    yazi.value = d;
    formUygula(d);
    slugElle.value = true;
    hatalar.value = {};
    if (!sessiz) toast.success('Yazı kaydedildi.');
    if (yeni.value && d?.id) router.replace(`/admin/web-sitesi/blog/${d.id}`);
    return true;
  } catch (e) {
    const status = e?.response?.status;
    if (status === 409) {
      cakisma.value = true;
      toast.error('Bu yazı siz düzenlerken başka bir oturumda değiştirildi. Değişiklikleriniz kaydedilmedi.', { duration: 8000 });
    } else if (status === 400) {
      hatalar.value = hatalariAgacaCevir(e.response.data) || {};
      toast.error(hataMesajlari(hatalar.value.detail)[0] || 'Kaydedilemedi; işaretli alanları kontrol edin.');
    } else {
      toast.error(humanError(e));
    }
    return false;
  } finally {
    if (islem.value === 'kaydet') islem.value = '';
  }
}

async function yayinla() {
  const onceki = form.durum;
  form.durum = 'yayinda';
  islem.value = 'yayinla';
  try {
    const ok = await kaydet({ sessiz: true });
    if (ok) toast.success(form.yayin_tarihi && new Date(form.yayin_tarihi) > new Date()
      ? 'Yazı zamanlandı; yayın tarihinde sitede görünecek.' : 'Yazı yayınlandı.');
    else form.durum = onceki;
  } finally {
    islem.value = '';
  }
}

async function onizle() {
  const sekme = window.open('about:blank', '_blank');
  islem.value = 'onizle';
  try {
    if ((yeni.value || kirli.value) && !(await kaydet({ sessiz: true }))) { sekme?.close(); return; }
    const { url } = await blogYazisiOnizleme(yazi.value.id);
    if (sekme) sekme.location.href = url;
    else window.open(url, '_blank', 'noopener');
  } catch {
    sekme?.close();
  } finally {
    islem.value = '';
  }
}

async function cakismaYenile() {
  const ok = await confirm({
    title: 'Güncel Hali Yükle',
    message: 'Yazının sunucudaki son hali yüklenecek. Bu ekrandaki kaydedilmemiş değişiklikler kaybolur.',
    confirmLabel: 'Yükle',
    variant: 'warning',
  });
  if (ok) yukle();
}

const zamanlanmis = computed(() => form.durum === 'yayinda' && form.yayin_tarihi && new Date(form.yayin_tarihi) > new Date());
const durumEtiket = computed(() => {
  if (zamanlanmis.value) return { etiket: 'Zamanlanmış', sinif: 'eisa-pill-info' };
  return {
    taslak: { etiket: 'Taslak', sinif: 'eisa-pill-muted' },
    yayinda: { etiket: 'Yayında', sinif: 'eisa-pill-success' },
    arsiv: { etiket: 'Arşiv', sinif: 'eisa-pill-warning' },
  }[yazi.value?.durum || 'taslak'] || { etiket: '—', sinif: 'eisa-pill-muted' };
});
const h = (alan) => hataMesajlari(hatalar.value?.[alan]);
</script>

<template>
  <div class="eisa-page ws-sayfa ws-blog-editor">
    <div v-if="yukleniyor && !yazi && !yeni" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor…</div>
    <div v-else-if="yuklemeHatasi" class="ws-bos">
      <i class="fa-solid fa-triangle-exclamation"></i><p>{{ yuklemeHatasi }}</p>
      <RouterLink to="/admin/web-sitesi/blog" class="eisa-btn"><i class="fa-solid fa-arrow-left"></i> Blog'a dön</RouterLink>
    </div>
    <template v-else>
      <header class="ws-editor-ust">
        <div class="ws-editor-kimlik">
          <RouterLink to="/admin/web-sitesi/blog" class="ws-geri" aria-label="Blog listesine dön"><i class="fa-solid fa-arrow-left"></i></RouterLink>
          <div class="ws-editor-baslik-alani">
            <div class="ws-editor-baslik-satir">
              <h1 class="ws-editor-baslik">{{ form.baslik || (yeni ? 'Yeni yazı' : 'Adsız yazı') }}</h1>
              <span v-if="!yeni" class="eisa-pill" :class="durumEtiket.sinif">{{ durumEtiket.etiket }}</span>
              <span v-if="kirli" class="eisa-pill eisa-pill-warning"><i class="fa-solid fa-circle ws-nokta"></i> Kaydedilmedi</span>
            </div>
            <span class="ws-mono ws-yardim">/blog/{{ form.slug || '…' }}</span>
          </div>
        </div>
        <div class="ws-editor-aksiyonlar">
          <YardimButonu :konular="['blog']" />
          <button type="button" class="eisa-btn" :disabled="!!islem" @click="onizle">
            <i class="fa-solid" :class="islem === 'onizle' ? 'fa-circle-notch fa-spin' : 'fa-eye'"></i> Önizle
          </button>
          <button type="button" class="eisa-btn" :class="{ 'eisa-btn-cta': form.durum === 'yayinda' && yazi?.durum === 'yayinda' }"
            :disabled="!!islem || cakisma" @click="kaydet()">
            <i class="fa-solid" :class="islem === 'kaydet' ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i> Kaydet
          </button>
          <button v-if="yazi?.durum !== 'yayinda'" type="button" class="eisa-btn eisa-btn-cta" :disabled="!!islem || cakisma" @click="yayinla">
            <i class="fa-solid fa-rocket"></i> {{ zamanlanmis ? 'Zamanla' : 'Yayınla' }}
          </button>
        </div>
      </header>

      <div v-if="cakisma" class="ws-banner ws-banner--hata" role="alert">
        <i class="fa-solid fa-code-merge"></i>
        <div><strong>Sürüm çakışması</strong><p>Bu yazı başka bir oturumda kaydedildi. Üzerine yazmamak için kaydetme durduruldu.</p></div>
        <button type="button" class="eisa-btn eisa-btn--sm" @click="cakismaYenile">Güncel hali yükle</button>
      </div>

      <div class="ws-blog-govde">
        <section class="eisa-panel eisa-panel-body ws-form-dikey">
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('baslik').length }">
            <label class="eisa-field-label" for="ws-blog-baslik">Başlık<span class="ws-zorunlu">*</span></label>
            <input id="ws-blog-baslik" v-model="form.baslik" class="eisa-field ws-buyuk-input" maxlength="200"
              placeholder="ör. Reçete bekleme süresi eczane için neden bir fırsat?" />
            <p v-for="m in h('baslik')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('slug').length }">
            <label class="eisa-field-label" for="ws-blog-slug">Adres (slug)<span class="ws-zorunlu">*</span></label>
            <div class="eisa-input-group">
              <span class="eisa-input-prefix">/blog/</span>
              <input id="ws-blog-slug" v-model="form.slug" class="eisa-field" maxlength="120" @input="slugElle = true" />
              <button v-if="slugElle" type="button" class="eisa-input-suffix ws-suffix-btn" title="Başlıktan yeniden üret"
                @click="form.slug = slugOlustur(form.baslik); slugElle = false"><i class="fa-solid fa-wand-magic-sparkles"></i></button>
            </div>
            <p v-if="!yeni && yazi?.durum === 'yayinda'" class="ws-yardim">Yayındaki yazının adresini değiştirmek eski bağlantıları kırar.</p>
            <p v-for="m in h('slug')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('ozet').length }">
            <div class="ws-alan-ust">
              <label class="eisa-field-label" for="ws-blog-ozet">Özet</label>
              <span class="ws-sayac">{{ form.ozet.length }}/300</span>
            </div>
            <textarea id="ws-blog-ozet" v-model="form.ozet" rows="3" maxlength="300" class="eisa-field"
              placeholder="Liste kartlarında ve arama sonuçlarında görünen kısa açıklama"></textarea>
            <p v-for="m in h('ozet')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('icerik_html').length }" data-alan-yolu="icerik_html">
            <span class="eisa-field-label">İçerik</span>
            <ZenginMetinEditoru v-model="form.icerik_html" gorsel-ekle min-yukseklik="420px" :hatali="!!h('icerik_html').length" />
            <p class="ws-yardim">Temkinli dil kullanın: teşhis/tedavi vaadi yok; son karar eczacıdadır.</p>
            <p v-for="m in h('icerik_html')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
        </section>

        <aside class="ws-blog-yan">
          <section class="eisa-panel eisa-panel-body ws-form-dikey">
            <h2 class="ws-yan-baslik">Yayın</h2>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-blog-durum">Durum</label>
              <select id="ws-blog-durum" v-model="form.durum" class="eisa-field">
                <option v-for="d in DURUMLAR" :key="d.deger" :value="d.deger">{{ d.etiket }}</option>
              </select>
            </div>
            <div class="ws-alan" :class="{ 'ws-alan--hatali': h('yayin_tarihi').length }">
              <label class="eisa-field-label" for="ws-blog-tarih">Yayın tarihi</label>
              <input id="ws-blog-tarih" v-model="form.yayin_tarihi" type="datetime-local" class="eisa-field" />
              <p class="ws-yardim">Boşsa yayınlandığı an atanır. İleri bir tarih seçilirse yazı o tarihte görünür.</p>
              <p v-for="m in h('yayin_tarihi')" :key="m" class="ws-alan-hata">{{ m }}</p>
            </div>
            <p v-if="yazi?.okuma_suresi" class="ws-yardim"><i class="fa-regular fa-clock"></i> Okuma süresi: {{ yazi.okuma_suresi }} dk</p>
          </section>

          <section class="eisa-panel eisa-panel-body ws-form-dikey">
            <h2 class="ws-yan-baslik">Kapak görseli</h2>
            <MedyaSecici v-model="form.kapak" :hatali="!!h('kapak').length" />
            <p v-for="m in h('kapak')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </section>

          <section class="eisa-panel eisa-panel-body ws-form-dikey">
            <h2 class="ws-yan-baslik">Sınıflandırma</h2>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-blog-kategori">Kategori</label>
              <select id="ws-blog-kategori" v-model="form.kategori_id" class="eisa-field">
                <option :value="null">— Kategorisiz —</option>
                <option v-for="k in kategoriler" :key="k.id" :value="k.id">{{ k.ad }}</option>
              </select>
            </div>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-blog-etiket">Etiketler</label>
              <div class="ws-etiket-girdi eisa-field">
                <span v-for="(e, i) in form.etiketler" :key="e" class="ws-cip is-active">
                  {{ e }} <button type="button" :aria-label="`${e} etiketini kaldır`" @click="form.etiketler.splice(i, 1)"><i class="fa-solid fa-xmark"></i></button>
                </span>
                <input id="ws-blog-etiket" v-model="etiketGirdi" placeholder="Etiket yazıp Enter'a basın" @keydown="etiketTus" @blur="etiketEkle" />
              </div>
            </div>
            <div class="ws-alan">
              <label class="eisa-field-label" for="ws-blog-yazar">Yazar adı</label>
              <input id="ws-blog-yazar" v-model="form.yazar_adi" class="eisa-field" maxlength="120" placeholder="ör. e-isa Ekibi" />
            </div>
          </section>

          <section class="eisa-panel eisa-panel-body ws-form-dikey">
            <h2 class="ws-yan-baslik">SEO</h2>
            <div class="ws-alan">
              <div class="ws-alan-ust">
                <label class="eisa-field-label" for="ws-blog-seo-baslik">SEO başlığı</label>
                <span class="ws-sayac" :class="{ 'is-asim': form.seo_baslik.length > 60 }">{{ form.seo_baslik.length }}/60</span>
              </div>
              <input id="ws-blog-seo-baslik" v-model="form.seo_baslik" class="eisa-field" maxlength="160" :placeholder="form.baslik" />
            </div>
            <div class="ws-alan">
              <div class="ws-alan-ust">
                <label class="eisa-field-label" for="ws-blog-seo-aciklama">SEO açıklaması</label>
                <span class="ws-sayac" :class="{ 'is-asim': form.seo_aciklama.length > 160 }">{{ form.seo_aciklama.length }}/160</span>
              </div>
              <textarea id="ws-blog-seo-aciklama" v-model="form.seo_aciklama" rows="3" maxlength="320" class="eisa-field"
                :placeholder="form.ozet"></textarea>
            </div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>
