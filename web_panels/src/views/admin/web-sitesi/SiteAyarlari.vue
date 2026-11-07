<script setup>
/**
 * Web Sitesi › Site Ayarları — CONTRACT §3 `ayarlar` alanları.
 * PATCH ayarlar/ sonrası backend `site` tag'ini revalidate eder.
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import draggable from 'vuedraggable';
import { toast } from 'vue-sonner';
import { getAyarlar, updateAyarlar } from '../../../services/website';
import { humanError } from '../../../services/api';
import { hatalariAgacaCevir, hataMesajlari, altHata, hataVarMi } from '../../../lib/websiteForm';
import { useKaydedilmemisDegisiklik } from '../../../composables/useKaydedilmemisDegisiklik.js';
import MedyaSecici from '../../../components/website/MedyaSecici.vue';
import { sorgudanOdaklan } from '../../../lib/websiteArama';

const PLATFORMLAR = [
  { deger: 'linkedin', etiket: 'LinkedIn', ikon: 'fa-linkedin' },
  { deger: 'instagram', etiket: 'Instagram', ikon: 'fa-instagram' },
  { deger: 'x', etiket: 'X (Twitter)', ikon: 'fa-x-twitter' },
  { deger: 'youtube', etiket: 'YouTube', ikon: 'fa-youtube' },
  { deger: 'facebook', etiket: 'Facebook', ikon: 'fa-facebook' },
];

const bos = () => ({
  site_adi: '', seo_baslik_sablonu: '%s | e-isa', seo_aciklama: '', og_gorsel: null,
  eposta: '', telefon: '', whatsapp: '', adres: '', firma_unvani: '', footer_aciklama: '',
  sosyal_linkler: [],
});

const form = reactive(bos());
const kayitli = ref('');
const loading = ref(true);
const kaydediliyor = ref(false);
const hatalar = ref({});
let keySayac = 0;

function payload() {
  return {
    ...form,
    og_gorsel: form.og_gorsel || null,
    sosyal_linkler: form.sosyal_linkler.map(({ platform, url }) => ({ platform, url: url.trim() })),
  };
}
const kirli = computed(() => !loading.value && JSON.stringify(payload()) !== kayitli.value);
useKaydedilmemisDegisiklik(kirli);

function uygula(d) {
  const veri = { ...bos(), ...(d || {}) };
  Object.keys(bos()).forEach((k) => { form[k] = veri[k] ?? bos()[k]; });
  form.sosyal_linkler = (veri.sosyal_linkler || []).map((s) => ({ _key: ++keySayac, platform: s.platform, url: s.url || '' }));
  kayitli.value = JSON.stringify(payload());
}

async function load() {
  loading.value = true;
  try {
    uygula(await getAyarlar());
  } catch { /* toast */ } finally {
    loading.value = false;
    sorgudanOdaklan(route.query, AYAR_ALAN_SECICI);
  }
}
onMounted(load);

// "Sitede ara" sonucundan gelindiğinde ilgili alana odaklan (?alan=&q=)
const route = useRoute();
const AYAR_ALAN_SECICI = {
  site_adi: '#ws-ay-site-adi', seo_baslik_sablonu: '#ws-ay-sablon', seo_aciklama: '#ws-ay-seo-aciklama',
  firma_unvani: '#ws-ay-unvan', eposta: '#ws-ay-eposta', telefon: '#ws-ay-telefon', whatsapp: '#ws-ay-whatsapp',
  adres: '#ws-ay-adres', footer_aciklama: '#ws-ay-footer', sosyal_linkler: '[data-alan-yolu="sosyal_linkler"]',
};
watch(() => [route.query.alan, route.query.q], () => { if (!loading.value) sorgudanOdaklan(route.query, AYAR_ALAN_SECICI); });

function sosyalEkle() {
  const kullanilan = form.sosyal_linkler.map((s) => s.platform);
  const ilkBos = PLATFORMLAR.find((p) => !kullanilan.includes(p.deger));
  form.sosyal_linkler.push({ _key: ++keySayac, platform: ilkBos?.deger || 'linkedin', url: '' });
}

function dogrula() {
  const h = {};
  if (!form.site_adi.trim()) h.site_adi = ['Site adı zorunludur.'];
  if (form.seo_baslik_sablonu && !form.seo_baslik_sablonu.includes('%s')) {
    h.seo_baslik_sablonu = ['Şablon sayfa başlığı için "%s" içermelidir.'];
  }
  if (form.eposta && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.eposta)) h.eposta = ['Geçerli bir e-posta girin.'];
  const sh = {};
  form.sosyal_linkler.forEach((s, i) => {
    if (!/^https:\/\//i.test(s.url.trim())) sh[String(i)] = { url: ['Adres https:// ile başlamalıdır.'] };
  });
  if (Object.keys(sh).length) h.sosyal_linkler = sh;
  hatalar.value = h;
  return !hataVarMi(h);
}

async function kaydet() {
  if (!dogrula()) { toast.warning('Kaydetmeden önce işaretli alanları düzeltin.'); return; }
  kaydediliyor.value = true;
  try {
    const d = await updateAyarlar(payload());
    if (d && typeof d === 'object' && 'site_adi' in d) uygula(d);
    else kayitli.value = JSON.stringify(payload());
    hatalar.value = {};
    toast.success('Site ayarları kaydedildi. Site birkaç saniye içinde güncellenir.');
  } catch (e) {
    if (e?.response?.status === 400) {
      hatalar.value = hatalariAgacaCevir(e.response.data) || {};
      toast.error(hataMesajlari(hatalar.value.detail)[0] || 'Kaydedilemedi; işaretli alanları kontrol edin.');
    } else {
      toast.error(humanError(e));
    }
  } finally {
    kaydediliyor.value = false;
  }
}

const h = (alan) => hataMesajlari(hatalar.value?.[alan]);
const sosyalHata = (i) => hataMesajlari(altHata(altHata(hatalar.value?.sosyal_linkler, i), 'url'))
  .concat(hataMesajlari(altHata(altHata(hatalar.value?.sosyal_linkler, i), 'platform')));
const platformIkon = (p) => PLATFORMLAR.find((x) => x.deger === p)?.ikon || 'fa-link';
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Site Ayarları</h1>
        <p class="eisa-page-subtitle">İletişim bilgileri, sosyal medya ve varsayılan SEO ayarları. Boş bırakılan iletişim alanları sitede gizlenir.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['ayarlar']" />
        <SiteOnizleButonu />
        <span v-if="kirli" class="eisa-pill eisa-pill-warning"><i class="fa-solid fa-circle ws-nokta"></i> Kaydedilmedi</span>
        <button type="button" class="eisa-btn eisa-btn-cta" :disabled="loading || kaydediliyor || !kirli" @click="kaydet">
          <i class="fa-solid" :class="kaydediliyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i> Kaydet
        </button>
      </div>
    </header>

    <div v-if="loading" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
    <div v-else class="ws-ayarlar-grid">
      <section class="eisa-panel">
        <div class="eisa-panel-header"><h2 class="eisa-panel-title">Genel ve SEO</h2></div>
        <div class="eisa-panel-body ws-form-dikey">
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('site_adi').length }">
            <label class="eisa-field-label" for="ws-ay-site-adi">Site adı<span class="ws-zorunlu">*</span></label>
            <input id="ws-ay-site-adi" v-model="form.site_adi" class="eisa-field" maxlength="80" />
            <p v-for="m in h('site_adi')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('seo_baslik_sablonu').length }">
            <label class="eisa-field-label" for="ws-ay-sablon">SEO başlık şablonu</label>
            <input id="ws-ay-sablon" v-model="form.seo_baslik_sablonu" class="eisa-field ws-mono" maxlength="120" />
            <p class="ws-yardim">"%s" sayfa başlığıyla değiştirilir. Örnek: "Teknoloji | e-isa".</p>
            <p v-for="m in h('seo_baslik_sablonu')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('seo_aciklama').length }">
            <div class="ws-alan-ust">
              <label class="eisa-field-label" for="ws-ay-seo-aciklama">Varsayılan SEO açıklaması</label>
              <span class="ws-sayac" :class="{ 'is-asim': form.seo_aciklama.length > 160 }">{{ form.seo_aciklama.length }}/160</span>
            </div>
            <textarea id="ws-ay-seo-aciklama" v-model="form.seo_aciklama" rows="3" class="eisa-field" maxlength="320"></textarea>
            <p v-for="m in h('seo_aciklama')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan">
            <span class="eisa-field-label">Varsayılan paylaşım görseli (OG)</span>
            <MedyaSecici v-model="form.og_gorsel" :hatali="!!h('og_gorsel').length" />
            <p class="ws-yardim">Sosyal medyada paylaşımlarda görünür. Önerilen ölçü 1200×630.</p>
            <p v-for="m in h('og_gorsel')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
        </div>
      </section>

      <section class="eisa-panel">
        <div class="eisa-panel-header"><h2 class="eisa-panel-title">İletişim ve Kurumsal</h2></div>
        <div class="eisa-panel-body ws-form-dikey">
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('firma_unvani').length }">
            <label class="eisa-field-label" for="ws-ay-unvan">Firma unvanı</label>
            <input id="ws-ay-unvan" v-model="form.firma_unvani" class="eisa-field" maxlength="160" />
            <p v-for="m in h('firma_unvani')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('eposta').length }">
            <label class="eisa-field-label" for="ws-ay-eposta">E-posta</label>
            <input id="ws-ay-eposta" v-model="form.eposta" type="email" class="eisa-field" maxlength="160" />
            <p v-for="m in h('eposta')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-iki-alan">
            <div class="ws-alan" :class="{ 'ws-alan--hatali': h('telefon').length }">
              <label class="eisa-field-label" for="ws-ay-telefon">Telefon</label>
              <input id="ws-ay-telefon" v-model="form.telefon" type="tel" class="eisa-field" maxlength="30" placeholder="+90 …" />
              <p v-for="m in h('telefon')" :key="m" class="ws-alan-hata">{{ m }}</p>
            </div>
            <div class="ws-alan" :class="{ 'ws-alan--hatali': h('whatsapp').length }">
              <label class="eisa-field-label" for="ws-ay-whatsapp">WhatsApp</label>
              <input id="ws-ay-whatsapp" v-model="form.whatsapp" class="eisa-field" maxlength="30" placeholder="905xxxxxxxxx" />
              <p v-for="m in h('whatsapp')" :key="m" class="ws-alan-hata">{{ m }}</p>
            </div>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('adres').length }">
            <label class="eisa-field-label" for="ws-ay-adres">Adres</label>
            <textarea id="ws-ay-adres" v-model="form.adres" rows="2" class="eisa-field" maxlength="300"></textarea>
            <p v-for="m in h('adres')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan" :class="{ 'ws-alan--hatali': h('footer_aciklama').length }">
            <label class="eisa-field-label" for="ws-ay-footer">Footer açıklaması</label>
            <textarea id="ws-ay-footer" v-model="form.footer_aciklama" rows="3" class="eisa-field" maxlength="400"></textarea>
            <p v-for="m in h('footer_aciklama')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
        </div>
      </section>

      <section class="eisa-panel">
        <div class="eisa-panel-header">
          <h2 class="eisa-panel-title">Sosyal Medya</h2>
          <button type="button" class="eisa-btn eisa-btn--sm" :disabled="form.sosyal_linkler.length >= PLATFORMLAR.length" @click="sosyalEkle">
            <i class="fa-solid fa-plus"></i> Bağlantı ekle
          </button>
        </div>
        <div class="eisa-panel-body">
          <p v-if="!form.sosyal_linkler.length" class="ws-bos-mini">Sosyal medya bağlantısı eklenmemiş.</p>
          <draggable v-model="form.sosyal_linkler" data-alan-yolu="sosyal_linkler" item-key="_key" handle=".ws-tutamac" :animation="150" class="ws-sosyal-liste">
            <template #item="{ element: s, index: i }">
              <div class="ws-sosyal-satir" :class="{ 'is-hatali': sosyalHata(i).length }">
                <span class="ws-tutamac" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
                <i class="fa-brands ws-sosyal-ikon" :class="platformIkon(s.platform)"></i>
                <select v-model="s.platform" class="eisa-field ws-sosyal-platform" aria-label="Platform">
                  <option v-for="p in PLATFORMLAR" :key="p.deger" :value="p.deger">{{ p.etiket }}</option>
                </select>
                <input v-model="s.url" class="eisa-field" placeholder="https://…" aria-label="Adres" />
                <button type="button" class="eisa-icon-btn danger" title="Kaldır" aria-label="Kaldır" @click="form.sosyal_linkler.splice(i, 1)">
                  <i class="fa-solid fa-trash"></i>
                </button>
                <p v-for="m in sosyalHata(i)" :key="m" class="ws-alan-hata ws-tam-satir">{{ m }}</p>
              </div>
            </template>
          </draggable>
        </div>
      </section>
    </div>
  </div>
</template>
