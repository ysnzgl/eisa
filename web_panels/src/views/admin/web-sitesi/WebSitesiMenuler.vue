<script setup>
/**
 * Web Sitesi › Menüler — header / footer / footer_alt menü ağaçları.
 *
 * 2 seviyeli sürükle-bırak ağaç (alt menü yalnız 1 seviye; alt öğesi olan bir
 * öğe başka bir öğenin altına taşınamaz). Kaydet → PUT menuler/<konum>/ ile
 * ağacın tamamı atomik olarak değiştirilir.
 *
 * AdminMenuItem: { id?, etiket, link_tipi: sayfa|bolum|blog|dis, sayfa_id,
 *                  bolum_anchor, url, yeni_sekme, cta, aktif, cocuklar }
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { sorgudanOdaklan } from '../../../lib/websiteArama';
import draggable from 'vuedraggable';
import { toast } from 'vue-sonner';
import { getMenuler, saveMenu, listSayfalar, getSayfa } from '../../../services/website';
import { humanError } from '../../../services/api';
import { izinliHref, hatalariAgacaCevir, hataMesajlari, altHata } from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';
import { useKaydedilmemisDegisiklik } from '../../../composables/useKaydedilmemisDegisiklik.js';

const { confirm } = useConfirm();

const KONUMLAR = [
  { kod: 'header', etiket: 'Üst Menü', ipucu: 'Sitenin üst menüsü. "CTA" işaretli öğe kırmızı buton olarak gösterilir. Alt öğeler açılır menüde listelenir.' },
  { kod: 'footer', etiket: 'Alt Menü (Footer)', ipucu: 'Footer\'da her üst öğe bir sütun başlığıdır; alt öğeler o sütundaki bağlantılardır.' },
  { kod: 'footer_alt', etiket: 'Alt Bilgi Bağlantıları', ipucu: 'Telif satırındaki küçük bağlantılar (ör. KVKK Aydınlatma Metni, Çerez Politikası).' },
];
const LINK_TIPLERI = [
  { deger: 'sayfa', etiket: 'Sayfa' },
  { deger: 'bolum', etiket: 'Sayfa bölümü (anchor)' },
  { deger: 'blog', etiket: 'Blog' },
  { deger: 'dis', etiket: 'Dış bağlantı' },
];

const aktifKonum = ref('header');
const menuler = reactive({ header: [], footer: [], footer_alt: [] });
const kayitli = reactive({ header: '[]', footer: '[]', footer_alt: '[]' });
const sayfalar = ref([]);
const loading = ref(true);
const kaydediliyor = ref(false);
const seciliKey = ref(null);
const hatalar = ref({}); // _key → { alan: [mesaj] }
const anchorOnbellek = reactive({}); // sayfa_id → [anchor]

let keySayac = 0;
const yeniKey = () => `m${++keySayac}`;

function ogeHazirla(o, seviye = 1) {
  return {
    _key: yeniKey(),
    id: o.id ?? null,
    etiket: o.etiket ?? '',
    link_tipi: o.link_tipi || 'sayfa',
    sayfa_id: o.sayfa_id ?? null,
    bolum_anchor: o.bolum_anchor ?? '',
    url: o.url ?? '',
    yeni_sekme: !!o.yeni_sekme,
    cta: !!o.cta,
    aktif: o.aktif !== false,
    cocuklar: seviye === 1 ? (o.cocuklar || []).map((c) => ogeHazirla(c, 2)) : [],
  };
}

function payload(liste) {
  return liste.map((o) => ({
    ...(o.id ? { id: o.id } : {}),
    etiket: o.etiket.trim(),
    link_tipi: o.link_tipi,
    sayfa_id: ['sayfa', 'bolum'].includes(o.link_tipi) ? o.sayfa_id : null,
    bolum_anchor: o.link_tipi === 'bolum' ? (o.bolum_anchor || '').replace(/^#/, '') : '',
    url: o.link_tipi === 'dis' ? o.url.trim() : '',
    yeni_sekme: !!o.yeni_sekme,
    cta: !!o.cta,
    aktif: !!o.aktif,
    cocuklar: payload(o.cocuklar || []),
  }));
}

function konumUygula(kod, agac) {
  menuler[kod] = (agac || []).map((o) => ogeHazirla(o));
  kayitli[kod] = JSON.stringify(payload(menuler[kod]));
}

const kirliKonumlar = computed(() =>
  KONUMLAR.map((k) => k.kod).filter((kod) => JSON.stringify(payload(menuler[kod])) !== kayitli[kod]));
const kirli = computed(() => kirliKonumlar.value.length > 0);
useKaydedilmemisDegisiklik(kirli);

const sayfaHaritasi = computed(() => Object.fromEntries(sayfalar.value.map((s) => [s.id, s])));
const konumBilgi = computed(() => KONUMLAR.find((k) => k.kod === aktifKonum.value));
const liste = computed({
  get: () => menuler[aktifKonum.value],
  set: (v) => { menuler[aktifKonum.value] = v; },
});

function tumOgeler(kod = aktifKonum.value) {
  return menuler[kod].flatMap((o) => [o, ...(o.cocuklar || [])]);
}
const seciliOge = computed(() => tumOgeler().find((o) => o._key === seciliKey.value) || null);
const seciliUstSeviye = computed(() => menuler[aktifKonum.value].some((o) => o._key === seciliKey.value));

async function load() {
  loading.value = true;
  try {
    const [m, s] = await Promise.all([getMenuler(), listSayfalar()]);
    sayfalar.value = s;
    KONUMLAR.forEach((k) => konumUygula(k.kod, m?.[k.kod]));
    hatalar.value = {};
    seciliKey.value = menuler[aktifKonum.value][0]?._key ?? null;
  } catch { /* toast */ } finally {
    loading.value = false;
  }
  aramaHedefineGit();
}
onMounted(load);

// ── "Sitede ara" sonucundan gelindiğinde: ?konum=&oge=&alan=&q= ──────────────
const route = useRoute();
const MENU_ALAN_SECICI = { etiket: '#ws-menu-etiket', url: '#ws-menu-url', bolum_anchor: '#ws-menu-anchor' };
async function aramaHedefineGit() {
  const { konum, oge } = route.query;
  if (!oge || !KONUMLAR.some((k) => k.kod === konum)) return;
  aktifKonum.value = konum;
  await nextTick(); // aktifKonum watch'ı ilk öğeyi seçer; ardından hedef öğe seçilir
  const hedef = tumOgeler(konum).find((o) => String(o.id) === String(oge));
  if (!hedef) return;
  seciliKey.value = hedef._key;
  await sorgudanOdaklan(route.query, MENU_ALAN_SECICI);
}
watch(() => [route.query.konum, route.query.oge, route.query.alan, route.query.q], () => { if (!loading.value) aramaHedefineGit(); });

watch(aktifKonum, () => {
  seciliKey.value = menuler[aktifKonum.value][0]?._key ?? null;
});

// ── href önizleme (backend çözümüyle aynı kural, CONTRACT §3) ─────────────
function hrefOnizle(o) {
  const s = sayfaHaritasi.value[o.sayfa_id];
  const kok = s ? (s.slug === 'anasayfa' ? '/' : `/${s.slug}`) : '';
  switch (o.link_tipi) {
    case 'sayfa': return s ? kok : '(sayfa seçilmedi)';
    case 'bolum': {
      if (!s) return '(sayfa seçilmedi)';
      const a = (o.bolum_anchor || '').replace(/^#/, '');
      return `${s.slug === 'anasayfa' ? '/' : kok}#${a}`;
    }
    case 'blog': return '/blog';
    case 'dis': return o.url || '(adres girilmedi)';
    default: return '';
  }
}
function sayfaYayindaDegil(o) {
  const s = sayfaHaritasi.value[o.sayfa_id];
  return ['sayfa', 'bolum'].includes(o.link_tipi) && s && s.durum !== 'yayinda';
}

// ── Ağaç işlemleri ──────────────────────────────────────────────────────────
function ogeEkle(ust = null) {
  const yeni = ogeHazirla({ etiket: 'Yeni bağlantı', link_tipi: 'sayfa' }, ust ? 2 : 1);
  if (ust) ust.cocuklar.push(yeni);
  else menuler[aktifKonum.value].push(yeni);
  seciliKey.value = yeni._key;
}

async function ogeSil(o) {
  const altSayisi = o.cocuklar?.length || 0;
  const ok = await confirm({
    title: 'Menü Öğesini Sil',
    message: `"${o.etiket}" öğesi${altSayisi ? ` ve ${altSayisi} alt öğesi` : ''} menüden kaldırılacak. Değişiklik "Kaydet" ile kalıcı olur.`,
    confirmLabel: 'Sil',
    variant: 'danger',
  });
  if (!ok) return;
  const kod = aktifKonum.value;
  const ustIdx = menuler[kod].indexOf(o);
  if (ustIdx >= 0) menuler[kod].splice(ustIdx, 1);
  else menuler[kod].forEach((u) => { const i = u.cocuklar.indexOf(o); if (i >= 0) u.cocuklar.splice(i, 1); });
  if (seciliKey.value === o._key) seciliKey.value = null;
}

/** 2 seviye kuralı: alt öğesi olan öğe bir alt listeye bırakılamaz. */
function hareketKontrol(evt) {
  const hedefAlt = evt.to?.dataset?.seviye === '2';
  const oge = evt.draggedContext?.element;
  return !(hedefAlt && oge?.cocuklar?.length);
}
/** Alt listeye taşınan öğenin olası çocuklarını temizle (güvenlik). */
function altListeDegisti(ust) {
  ust.cocuklar.forEach((c) => { if (c.cocuklar?.length) c.cocuklar = []; });
}

// ── Bölüm anchor önerileri ───────────────────────────────────────────────────
async function anchorlariYukle(sayfaId) {
  if (!sayfaId || anchorOnbellek[sayfaId]) return;
  anchorOnbellek[sayfaId] = [];
  try {
    const d = await getSayfa(sayfaId);
    anchorOnbellek[sayfaId] = [...new Set((d?.bloklar || []).map((b) => b.anchor_id).filter(Boolean))];
  } catch { /* öneri yoksa elle yazılır */ }
}
watch(() => [seciliOge.value?.link_tipi, seciliOge.value?.sayfa_id], ([tip, id]) => {
  if (tip === 'bolum' && id) anchorlariYukle(id);
}, { immediate: true });
const anchorOnerileri = computed(() => anchorOnbellek[seciliOge.value?.sayfa_id] || []);

// ── Doğrulama & kayıt ───────────────────────────────────────────────────────
function dogrula(kod) {
  const h = {};
  tumOgeler(kod).forEach((o) => {
    const e = {};
    if (!o.etiket.trim()) e.etiket = ['Etiket zorunludur.'];
    if (['sayfa', 'bolum'].includes(o.link_tipi) && !o.sayfa_id) e.sayfa_id = ['Bir sayfa seçin.'];
    if (o.link_tipi === 'bolum' && !(o.bolum_anchor || '').replace(/^#/, '')) e.bolum_anchor = ['Bölüm (anchor) zorunludur.'];
    if (o.link_tipi === 'dis') {
      if (!o.url.trim()) e.url = ['Adres zorunludur.'];
      else if (!izinliHref(o.url)) e.url = ['Adres https://, mailto:, tel:, / veya # ile başlamalıdır.'];
    }
    if (Object.keys(e).length) h[o._key] = e;
  });
  return h;
}

function sunucuHatalariniEsle(kod, data) {
  const agac = hatalariAgacaCevir(data) || {};
  const h = {};
  menuler[kod].forEach((o, i) => {
    const oh = altHata(agac, i);
    if (!oh) return;
    const { cocuklar, ...kendi } = oh;
    if (Object.keys(kendi).length) h[o._key] = kendi;
    o.cocuklar.forEach((c, j) => {
      const ch = altHata(cocuklar, j);
      if (ch) h[c._key] = ch;
    });
  });
  return { h, genel: hataMesajlari(agac) };
}

async function kaydet() {
  const kod = aktifKonum.value;
  const h = dogrula(kod);
  hatalar.value = h;
  if (Object.keys(h).length) {
    seciliKey.value = Object.keys(h)[0];
    toast.warning('Kaydetmeden önce işaretli öğeleri düzeltin.');
    return;
  }
  kaydediliyor.value = true;
  try {
    const yeni = await saveMenu(kod, payload(menuler[kod]));
    const seciliIndeks = tumOgeler(kod).findIndex((o) => o._key === seciliKey.value);
    konumUygula(kod, Array.isArray(yeni) ? yeni : (yeni?.[kod] ?? payload(menuler[kod])));
    seciliKey.value = tumOgeler(kod)[seciliIndeks]?._key ?? null;
    hatalar.value = {};
    toast.success('Menü kaydedildi. Site birkaç saniye içinde güncellenir.');
  } catch (e) {
    if (e?.response?.status === 400) {
      const { h: sh, genel } = sunucuHatalariniEsle(kod, e.response.data);
      hatalar.value = sh;
      if (Object.keys(sh).length) seciliKey.value = Object.keys(sh)[0];
      toast.error(genel[0] || 'Menü kaydedilemedi; işaretli öğeleri kontrol edin.');
    } else {
      toast.error(humanError(e));
    }
  } finally {
    kaydediliyor.value = false;
  }
}

async function geriAl() {
  const ok = await confirm({
    title: 'Değişiklikleri Geri Al',
    message: 'Bu menüdeki kaydedilmemiş değişiklikler atılacak ve son kaydedilen hali yüklenecek.',
    confirmLabel: 'Geri Al',
    variant: 'warning',
  });
  if (!ok) return;
  konumUygula(aktifKonum.value, JSON.parse(kayitli[aktifKonum.value]));
  hatalar.value = {};
  seciliKey.value = menuler[aktifKonum.value][0]?._key ?? null;
}

const hata = (alan) => hataMesajlari(hatalar.value[seciliKey.value]?.[alan]);
const ogeHatali = (o) => !!hatalar.value[o._key];
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Menüler</h1>
        <p class="eisa-page-subtitle">Üst menü, footer sütunları ve alt bilgi bağlantılarını düzenleyin.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['menuler']" />
        <SiteOnizleButonu />
        <button type="button" class="eisa-btn" :disabled="!kirliKonumlar.includes(aktifKonum) || kaydediliyor" @click="geriAl">
          <i class="fa-solid fa-rotate-left"></i> Geri Al
        </button>
        <button type="button" class="eisa-btn eisa-btn-cta" :disabled="kaydediliyor || loading" @click="kaydet">
          <i class="fa-solid" :class="kaydediliyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i> Kaydet
        </button>
      </div>
    </header>

    <nav class="ws-sekmeler eisa-tabs-scroll" role="tablist">
      <button v-for="k in KONUMLAR" :key="k.kod" type="button" role="tab" :aria-selected="aktifKonum === k.kod"
        class="ws-sekme" :class="{ 'is-active': aktifKonum === k.kod }" @click="aktifKonum = k.kod">
        {{ k.etiket }}
        <span class="ws-sekme-sayi">{{ menuler[k.kod].length }}</span>
        <span v-if="kirliKonumlar.includes(k.kod)" class="ws-kirli-nokta" title="Kaydedilmemiş değişiklik"></span>
      </button>
    </nav>

    <div v-if="loading" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
    <div v-else class="ws-iki-kolon">
      <section class="eisa-panel ws-menu-agac">
        <div class="eisa-panel-header">
          <div>
            <h2 class="eisa-panel-title">{{ konumBilgi.etiket }}</h2>
            <p class="ws-yardim">{{ konumBilgi.ipucu }}</p>
          </div>
          <button type="button" class="eisa-btn eisa-btn--sm" @click="ogeEkle()"><i class="fa-solid fa-plus"></i> Öğe ekle</button>
        </div>
        <div class="eisa-panel-body">
          <p v-if="!liste.length" class="ws-bos-mini">Bu menüde öğe yok.</p>
          <draggable v-model="liste" item-key="_key" handle=".ws-tutamac" :group="{ name: `menu-${aktifKonum}` }"
            :move="hareketKontrol" :animation="150" ghost-class="ws-surukle-hayalet" class="ws-menu-liste" data-seviye="1">
            <template #item="{ element: o }">
              <div class="ws-menu-dugum">
                <div class="ws-menu-oge" :class="{ 'is-active': o._key === seciliKey, 'is-pasif': !o.aktif, 'is-hatali': ogeHatali(o) }"
                  @click="seciliKey = o._key">
                  <span class="ws-tutamac" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
                  <div class="ws-menu-oge-metin">
                    <strong>{{ o.etiket || '(etiketsiz)' }}</strong>
                    <span class="ws-mono">{{ hrefOnizle(o) }}</span>
                  </div>
                  <span v-if="o.cta" class="ws-etiket ws-etiket--kirmizi">CTA</span>
                  <span v-if="o.yeni_sekme" class="ws-etiket" title="Yeni sekmede açılır"><i class="fa-solid fa-arrow-up-right-from-square"></i></span>
                  <span v-if="!o.aktif" class="ws-etiket ws-etiket--gri">Pasif</span>
                  <span v-if="sayfaYayindaDegil(o)" class="ws-etiket ws-etiket--sari" title="Bağlı sayfa yayında değil; sitede gösterilmez">Yayında değil</span>
                  <i v-if="ogeHatali(o)" class="fa-solid fa-circle-exclamation ws-hata-ikon"></i>
                  <div class="ws-menu-oge-aksiyon" @click.stop>
                    <button type="button" class="eisa-icon-btn" title="Alt öğe ekle" aria-label="Alt öğe ekle" @click="ogeEkle(o)">
                      <i class="fa-solid fa-turn-down"></i>
                    </button>
                    <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="ogeSil(o)">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </div>
                </div>
                <draggable v-model="o.cocuklar" item-key="_key" handle=".ws-tutamac" :group="{ name: `menu-${aktifKonum}` }"
                  :move="hareketKontrol" :animation="150" ghost-class="ws-surukle-hayalet" class="ws-menu-alt-liste"
                  data-seviye="2" @change="altListeDegisti(o)">
                  <template #item="{ element: c }">
                    <div class="ws-menu-oge ws-menu-oge--alt"
                      :class="{ 'is-active': c._key === seciliKey, 'is-pasif': !c.aktif, 'is-hatali': ogeHatali(c) }"
                      @click="seciliKey = c._key">
                      <span class="ws-tutamac" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
                      <div class="ws-menu-oge-metin">
                        <strong>{{ c.etiket || '(etiketsiz)' }}</strong>
                        <span class="ws-mono">{{ hrefOnizle(c) }}</span>
                      </div>
                      <span v-if="c.cta" class="ws-etiket ws-etiket--kirmizi">CTA</span>
                      <span v-if="!c.aktif" class="ws-etiket ws-etiket--gri">Pasif</span>
                      <span v-if="sayfaYayindaDegil(c)" class="ws-etiket ws-etiket--sari">Yayında değil</span>
                      <i v-if="ogeHatali(c)" class="fa-solid fa-circle-exclamation ws-hata-ikon"></i>
                      <div class="ws-menu-oge-aksiyon" @click.stop>
                        <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="ogeSil(c)">
                          <i class="fa-solid fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </template>
                </draggable>
              </div>
            </template>
          </draggable>
        </div>
      </section>

      <section class="eisa-panel ws-menu-form">
        <div class="eisa-panel-header"><h2 class="eisa-panel-title">Öğe Ayarları</h2></div>
        <div v-if="!seciliOge" class="ws-bos"><i class="fa-regular fa-hand-pointer"></i><p>Düzenlemek için bir öğe seçin.</p></div>
        <div v-else class="eisa-panel-body ws-form-dikey">
          <div class="ws-alan" :class="{ 'ws-alan--hatali': hata('etiket').length }">
            <label class="eisa-field-label" for="ws-menu-etiket">Etiket<span class="ws-zorunlu">*</span></label>
            <input id="ws-menu-etiket" v-model="seciliOge.etiket" class="eisa-field" maxlength="60" />
            <p v-for="m in hata('etiket')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div class="ws-alan">
            <span class="eisa-field-label">Bağlantı tipi</span>
            <div class="ws-segment" role="radiogroup">
              <button v-for="t in LINK_TIPLERI" :key="t.deger" type="button" role="radio" :aria-checked="seciliOge.link_tipi === t.deger"
                :class="{ 'is-active': seciliOge.link_tipi === t.deger }" @click="seciliOge.link_tipi = t.deger">{{ t.etiket }}</button>
            </div>
          </div>
          <div v-if="['sayfa', 'bolum'].includes(seciliOge.link_tipi)" class="ws-alan" :class="{ 'ws-alan--hatali': hata('sayfa_id').length }">
            <label class="eisa-field-label" for="ws-menu-sayfa">Sayfa<span class="ws-zorunlu">*</span></label>
            <select id="ws-menu-sayfa" v-model="seciliOge.sayfa_id" class="eisa-field">
              <option :value="null">— Sayfa seçin —</option>
              <option v-for="s in sayfalar" :key="s.id" :value="s.id">
                {{ s.baslik }} (/{{ s.slug === 'anasayfa' ? '' : s.slug }}){{ s.durum !== 'yayinda' ? ' · yayında değil' : '' }}
              </option>
            </select>
            <p v-for="m in hata('sayfa_id')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div v-if="seciliOge.link_tipi === 'bolum'" class="ws-alan" :class="{ 'ws-alan--hatali': hata('bolum_anchor').length }">
            <label class="eisa-field-label" for="ws-menu-anchor">Bölüm (anchor)<span class="ws-zorunlu">*</span></label>
            <div class="eisa-input-group">
              <span class="eisa-input-prefix">#</span>
              <input id="ws-menu-anchor" v-model="seciliOge.bolum_anchor" class="eisa-field" list="ws-anchor-onerileri" maxlength="60" />
            </div>
            <datalist id="ws-anchor-onerileri">
              <option v-for="a in anchorOnerileri" :key="a" :value="a" />
            </datalist>
            <div v-if="anchorOnerileri.length" class="ws-cipler">
              <button v-for="a in anchorOnerileri" :key="a" type="button" class="ws-cip"
                :class="{ 'is-active': seciliOge.bolum_anchor === a }" @click="seciliOge.bolum_anchor = a">#{{ a }}</button>
            </div>
            <p v-else-if="seciliOge.sayfa_id" class="ws-yardim">Bu sayfanın bloklarında tanımlı anchor yok. Sayfa Editörü'nde bloğa anchor ekleyebilirsiniz.</p>
            <p v-for="m in hata('bolum_anchor')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <div v-if="seciliOge.link_tipi === 'dis'" class="ws-alan" :class="{ 'ws-alan--hatali': hata('url').length }">
            <label class="eisa-field-label" for="ws-menu-url">Adres<span class="ws-zorunlu">*</span></label>
            <input id="ws-menu-url" v-model="seciliOge.url" class="eisa-field" placeholder="https://…" />
            <p v-for="m in hata('url')" :key="m" class="ws-alan-hata">{{ m }}</p>
          </div>
          <p v-if="seciliOge.link_tipi === 'blog'" class="ws-yardim">Blog listesine (/blog) bağlanır.</p>

          <div class="ws-toggle-grup">
            <label class="eisa-toggle"><input v-model="seciliOge.aktif" type="checkbox" /><span>Aktif (sitede göster)</span></label>
            <label class="eisa-toggle"><input v-model="seciliOge.yeni_sekme" type="checkbox" /><span>Yeni sekmede aç</span></label>
            <label v-if="aktifKonum === 'header'" class="eisa-toggle">
              <input v-model="seciliOge.cta" type="checkbox" /><span>CTA butonu olarak göster</span>
            </label>
          </div>
          <p v-for="m in hata('non_field_errors').concat(hata('_genel'))" :key="m" class="ws-alan-hata">{{ m }}</p>

          <div class="ws-menu-onizleme">
            <span class="ws-mini-label">Bağlantı</span>
            <code>{{ hrefOnizle(seciliOge) }}</code>
          </div>
          <button v-if="seciliUstSeviye" type="button" class="eisa-btn eisa-btn--sm" @click="ogeEkle(seciliOge)">
            <i class="fa-solid fa-turn-down"></i> Bu öğeye alt öğe ekle
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
