<script setup>
/**
 * Sayfa Editörü — Web Sitesi modülünün ana ekranı.
 *
 *  Sol panel : blok listesi (sürükle-bırak sıralama, göster/gizle, kopyala, sil, blok ekle)
 *  Sağ panel : seçili bloğun `blok-tipleri` şemasından üretilen formu (FieldRenderer)
 *  Üst bar   : sayfa başlığı/slug/SEO (çekmece), durum, Taslağı Kaydet, Önizle,
 *              Yayınla (not ile), Yayından kaldır, Revizyonlar (geri al)
 *
 * Kayıt: PATCH sayfalar/<id>/ (meta + surum) ve PUT sayfalar/<id>/bloklar/
 * (surum + bloklar). Sürüm uyuşmazlığında backend 409 döner.
 * Hata biçimi: 400 { bloklar: { "<index>": { "<alan>": ["mesaj"] } } }.
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue';
import { RouterLink, onBeforeRouteUpdate, useRoute } from 'vue-router';
import draggable from 'vuedraggable';
import { toast } from 'vue-sonner';
import {
  getSayfa, listBlokTipleri, updateSayfa, saveBloklar, yayinlaSayfa, yayindanKaldirSayfa,
  listRevizyonlar, geriAlRevizyon, sayfaOnizleme,
} from '../../../services/website';
import { humanError } from '../../../services/api';
import {
  veriyiTamamla, varsayilanVeri, veriyiDogrula, hataVarMi, hatalariAgacaCevir, hataMesajlari,
  blokOzeti, klonla, ANCHOR_REGEX, SLUG_REGEX, AYRILMIS_SLUGLAR, KORUMALI_SAYFALAR,
  SAYFA_DURUMLARI, tarihFormat,
} from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';
import { alanaOdaklan } from '../../../lib/websiteArama';
import { useKaydedilmemisDegisiklik } from '../../../composables/useKaydedilmemisDegisiklik.js';
import BlokFormu from '../../../components/website/BlokFormu.vue';
import WebIkon from '../../../components/website/WebIkon.vue';
import WsCekmece from '../../../components/website/WsCekmece.vue';
import MedyaSecici from '../../../components/website/MedyaSecici.vue';

const route = useRoute();
const { confirm } = useConfirm();

const yukleniyor = ref(true);
const yuklemeHatasi = ref('');
const sayfa = ref(null);
const blokTipleri = ref([]);
const bloklar = ref([]);
const seciliKey = ref(null);
const islem = ref(''); // 'kaydet' | 'yayinla' | 'kaldir' | 'onizle' | 'geri-al'
const cakisma = ref(false);
const blokHatalari = ref({}); // _key → hata ağacı
const metaHatalari = ref({});

const meta = reactive({ baslik: '', slug: '', seo_baslik: '', seo_aciklama: '', og_gorsel: null, sira: 0 });
const kayitliBloklar = ref('[]');
const kayitliMeta = ref('{}');

const seoAcik = ref(false);
const revizyonAcik = ref(false);
const revizyonlar = ref([]);
const revizyonYukleniyor = ref(false);
const blokEkleAcik = ref(false);
const blokArama = ref('');
const yayinlaAcik = ref(false);
const yayinNotu = ref('');

let keySayac = 0;
const yeniKey = () => `k${++keySayac}`;

const tipHaritasi = computed(() => Object.fromEntries(blokTipleri.value.map((t) => [t.tip, t])));
const seciliBlok = computed(() => bloklar.value.find((b) => b._key === seciliKey.value) || null);
const korumali = computed(() => KORUMALI_SAYFALAR.includes(sayfa.value?.slug));
const durum = computed(() => SAYFA_DURUMLARI[sayfa.value?.durum] || { etiket: sayfa.value?.durum || '—', sinif: 'eisa-pill-muted' });

// ── Kirli (dirty) takibi ─────────────────────────────────────────────────────
function blokPayload() {
  return bloklar.value.map((b) => ({
    ...(b.id !== undefined && b.id !== null ? { id: b.id } : {}),
    tip: b.tip,
    veri: b.veri,
    gorunur: !!b.gorunur,
    anchor_id: b.anchor_id || '',
  }));
}
function metaPayload() {
  return {
    baslik: meta.baslik,
    slug: meta.slug,
    seo_baslik: meta.seo_baslik || '',
    seo_aciklama: meta.seo_aciklama || '',
    og_gorsel: meta.og_gorsel || null,
    sira: Number(meta.sira) || 0,
  };
}
const blokJson = computed(() => JSON.stringify(blokPayload()));
const metaJson = computed(() => JSON.stringify(metaPayload()));
const kirliBloklar = computed(() => blokJson.value !== kayitliBloklar.value);
const kirliMeta = computed(() => metaJson.value !== kayitliMeta.value);
const kirli = computed(() => !!sayfa.value && (kirliBloklar.value || kirliMeta.value));

const { onayla } = useKaydedilmemisDegisiklik(kirli);
onBeforeRouteUpdate(() => onayla());

// ── Yükleme ──────────────────────────────────────────────────────────────────
function blokHazirla(b, key) {
  const tanim = tipHaritasi.value[b.tip];
  return {
    _key: key || yeniKey(),
    id: b.id ?? null,
    tip: b.tip,
    veri: tanim ? veriyiTamamla(tanim.alanlar, b.veri) : { ...(b.veri || {}) },
    gorunur: b.gorunur !== false,
    anchor_id: b.anchor_id || '',
  };
}

function metaUygula(d) {
  Object.assign(meta, {
    baslik: d.baslik ?? '',
    slug: d.slug ?? '',
    seo_baslik: d.seo_baslik ?? '',
    seo_aciklama: d.seo_aciklama ?? '',
    og_gorsel: d.og_gorsel ?? null,
    sira: d.sira ?? 0,
  });
  kayitliMeta.value = JSON.stringify(metaPayload());
}

/**
 * Sunucu detayını uygular. `anahtarKoru` iken (kayıt sonrası) sıra aynı
 * olduğundan yerel `_key`ler korunur; seçim ve açık paneller kaybolmaz.
 */
function sayfaUygula(d, { anahtarKoru = false } = {}) {
  if (!d) return;
  const { bloklar: sunucuBloklari, ...digeri } = d;
  sayfa.value = { ...(sayfa.value || {}), ...digeri };
  if (['baslik', 'slug', 'seo_baslik', 'seo_aciklama', 'sira'].some((k) => k in d)) metaUygula({ ...metaPayload(), ...d });
  if (Array.isArray(sunucuBloklari)) {
    const sirali = [...sunucuBloklari].sort((a, b) => (a.sira ?? 0) - (b.sira ?? 0));
    const eski = bloklar.value;
    const koru = anahtarKoru && eski.length === sirali.length;
    bloklar.value = sirali.map((b, i) => blokHazirla(b, koru ? eski[i]._key : null));
    kayitliBloklar.value = JSON.stringify(blokPayload());
    if (!bloklar.value.some((b) => b._key === seciliKey.value)) {
      seciliKey.value = bloklar.value[0]?._key ?? null;
    }
  }
}

/** Sunucu yanıtından yalnız durum/sürüm alanlarını uygular (meta ve bloklara dokunmaz). */
function durumUygula(d) {
  if (!d || typeof d !== 'object') return;
  const alanlar = ['durum', 'taslak_degisti', 'surum', 'yayin_tarihi', 'guncellenme_tarihi'];
  const guncel = { ...sayfa.value };
  alanlar.forEach((k) => { if (k in d) guncel[k] = d[k]; });
  sayfa.value = guncel;
}

async function yukle() {
  yukleniyor.value = true;
  yuklemeHatasi.value = '';
  cakisma.value = false;
  blokHatalari.value = {};
  metaHatalari.value = {};
  try {
    const [detay, tipler] = await Promise.all([
      getSayfa(route.params.id),
      blokTipleri.value.length ? Promise.resolve(blokTipleri.value) : listBlokTipleri(),
    ]);
    blokTipleri.value = tipler;
    sayfa.value = null;
    bloklar.value = [];
    seciliKey.value = null;
    sayfaUygula(detay);
  } catch (e) {
    yuklemeHatasi.value = e?.response?.status === 404 ? 'Sayfa bulunamadı.' : 'Sayfa yüklenemedi.';
  } finally {
    yukleniyor.value = false;
  }
  if (sayfa.value) aramaHedefineGit();
}

onMounted(yukle);
watch(() => route.params.id, (yeni, eski) => { if (yeni && yeni !== eski) yukle(); });

// ── "Sitede ara" sonucundan gelindiğinde: bloğu seç, alanı bul, aranan ifadeyi seç ─────
// Sorgu: ?blok=<blok id>&alan=<veri yolu | meta:alan>&q=<aranan>
const hedefYol = ref('');
provide('wsHedefYol', hedefYol);
const META_ALAN_ID = {
  baslik: 'ws-meta-baslik', slug: 'ws-meta-slug', seo_baslik: 'ws-meta-seo-baslik', seo_aciklama: 'ws-meta-seo-aciklama',
};

async function aramaHedefineGit() {
  const { alan, blok, q } = route.query;
  if (typeof alan !== 'string' || !alan || !sayfa.value) return;
  if (String(sayfa.value.id) !== String(route.params.id)) return; // başka sayfa yüklenirken
  const aranan = typeof q === 'string' ? q : '';
  if (alan.startsWith('meta:')) {
    seoAcik.value = true;
    const id = META_ALAN_ID[alan.slice(5)];
    if (id) await alanaOdaklan({ seciciler: [`#${id}`], aranan });
    return;
  }
  const hedef = bloklar.value.find((b) => String(b.id) === String(blok));
  if (!hedef) {
    toast.info('Aranan blok bu sayfada artık bulunmuyor (silinmiş veya kaydedilmemiş olabilir).');
    return;
  }
  seciliKey.value = hedef._key;
  hedefYol.value = alan;
  await alanaOdaklan({ veriYolu: alan, aranan });
}
// Aynı sayfadayken başka bir sonuca gidilirse
watch(() => [route.query.blok, route.query.alan, route.query.q], () => {
  if (!yukleniyor.value) aramaHedefineGit();
});

// ── İstemci doğrulaması ──────────────────────────────────────────────────────
const anchorHatalari = computed(() => {
  const sonuc = {};
  const sayim = {};
  bloklar.value.forEach((b) => { if (b.anchor_id) sayim[b.anchor_id] = (sayim[b.anchor_id] || 0) + 1; });
  bloklar.value.forEach((b) => {
    if (!b.anchor_id) return;
    if (!ANCHOR_REGEX.test(b.anchor_id)) sonuc[b._key] = 'Harf veya rakamla başlamalı; yalnızca küçük harf, rakam, tire ve alt çizgi kullanılabilir.';
    else if (sayim[b.anchor_id] > 1) sonuc[b._key] = 'Bu anchor başka bir blokta da kullanılıyor.';
  });
  return sonuc;
});

function blokHataliMi(b) {
  return hataVarMi(blokHatalari.value[b._key]) || !!anchorHatalari.value[b._key];
}

function istemciDogrula() {
  const sonuc = {};
  for (const b of bloklar.value) {
    const tanim = tipHaritasi.value[b.tip];
    if (!tanim) continue;
    const h = veriyiDogrula(tanim.alanlar, b.veri);
    if (hataVarMi(h)) sonuc[b._key] = h;
  }
  return sonuc;
}

function metaDogrula() {
  const h = {};
  if (!meta.baslik.trim()) h.baslik = ['Başlık zorunludur.'];
  if (!SLUG_REGEX.test(meta.slug)) h.slug = ['Slug yalnızca küçük harf, rakam ve tire içerebilir.'];
  else if (AYRILMIS_SLUGLAR.includes(meta.slug)) h.slug = ['Bu slug sistem tarafından ayrılmıştır.'];
  return h;
}

async function ilkHatayaGit() {
  const ilk = bloklar.value.find(blokHataliMi);
  if (ilk) seciliKey.value = ilk._key;
  await nextTick();
  document.querySelector('.ws-editor-form .ws-alan--hatali')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── Sunucu hata işleme ───────────────────────────────────────────────────────
function hataIsle(e, varsayilan = 'İşlem tamamlanamadı.') {
  const status = e?.response?.status;
  const data = e?.response?.data;
  if (status === 409) {
    cakisma.value = true;
    toast.error('Bu sayfa siz düzenlerken başka bir oturumda değiştirildi. Değişiklikleriniz kaydedilmedi.', { duration: 8000 });
    return;
  }
  if (status === 400 && data && typeof data === 'object') {
    const agac = hatalariAgacaCevir(data) || {};
    const { bloklar: bh, detail, ...metaH } = agac;
    if (bh && typeof bh === 'object' && !Array.isArray(bh)) {
      const yeni = {};
      for (const [indeks, h] of Object.entries(bh)) {
        const b = bloklar.value[Number(indeks)];
        if (b) yeni[b._key] = h;
      }
      blokHatalari.value = yeni;
    }
    const metaAnahtarlar = Object.keys(metaH).filter((k) => hataVarMi(metaH[k]));
    if (metaAnahtarlar.length) {
      metaHatalari.value = metaH;
      if (metaAnahtarlar.some((k) => ['baslik', 'slug', 'seo_baslik', 'seo_aciklama', 'og_gorsel', 'sira'].includes(k))) {
        seoAcik.value = true;
      }
    }
    const genel = [...hataMesajlari(detail), ...hataMesajlari(bh)];
    toast.error(genel[0] || 'Kaydedilemedi: işaretli alanları kontrol edin.');
    ilkHatayaGit();
    return;
  }
  toast.error(e?.response ? humanError(e) : (e?.message || varsayilan));
}

// ── Kaydet ───────────────────────────────────────────────────────────────────
async function kaydet({ sessiz = false } = {}) {
  if (!sayfa.value) return false;
  if (cakisma.value) {
    toast.warning('Önce sayfanın güncel halini yükleyin (çakışma uyarısı).');
    return false;
  }
  const istemci = istemciDogrula();
  const mh = metaDogrula();
  blokHatalari.value = istemci;
  metaHatalari.value = mh;
  if (Object.keys(istemci).length || Object.keys(anchorHatalari.value).length || Object.keys(mh).length) {
    toast.warning('Kaydetmeden önce işaretli alanları düzeltin.');
    if (Object.keys(mh).length) seoAcik.value = true;
    ilkHatayaGit();
    return false;
  }
  if (!kirli.value) {
    if (!sessiz) toast.info('Kaydedilecek değişiklik yok.');
    return true;
  }
  islem.value = islem.value || 'kaydet';
  try {
    if (kirliMeta.value) {
      const d = await updateSayfa(sayfa.value.id, { ...metaPayload(), surum: sayfa.value.surum });
      sayfaUygula({ ...(d || {}), bloklar: undefined }, { anahtarKoru: true });
      if (!d || !('slug' in d)) kayitliMeta.value = JSON.stringify(metaPayload());
    }
    if (kirliBloklar.value) {
      const d = await saveBloklar(sayfa.value.id, sayfa.value.surum, blokPayload());
      sayfaUygula(d, { anahtarKoru: true });
      if (!Array.isArray(d?.bloklar)) kayitliBloklar.value = blokJson.value;
    }
    blokHatalari.value = {};
    metaHatalari.value = {};
    if (!sessiz) toast.success('Taslak kaydedildi.');
    return true;
  } catch (e) {
    hataIsle(e, 'Taslak kaydedilemedi.');
    return false;
  } finally {
    if (islem.value === 'kaydet') islem.value = '';
  }
}

// ── Önizle ───────────────────────────────────────────────────────────────────
async function onizle() {
  if (!sayfa.value) return;
  // Açılır pencere engelleyicisine takılmamak için sekme tıklama anında açılır.
  const sekme = window.open('about:blank', '_blank');
  islem.value = 'onizle';
  try {
    if (kirli.value && !(await kaydet({ sessiz: true }))) { sekme?.close(); return; }
    const { url } = await sayfaOnizleme(sayfa.value.id);
    if (sekme) sekme.location.href = url;
    else window.open(url, '_blank', 'noopener');
  } catch {
    sekme?.close();
  } finally {
    islem.value = '';
  }
}

// ── Yayınla / Yayından kaldır ────────────────────────────────────────────────
function yayinlaAc() {
  yayinNotu.value = '';
  yayinlaAcik.value = true;
}

async function yayinla() {
  islem.value = 'yayinla';
  try {
    if (kirli.value && !(await kaydet({ sessiz: true }))) return;
    const d = await yayinlaSayfa(sayfa.value.id, yayinNotu.value.trim());
    if (d && typeof d === 'object') sayfaUygula(d, { anahtarKoru: true });
    sayfa.value = { ...sayfa.value, durum: d?.durum || 'yayinda', taslak_degisti: d?.taslak_degisti ?? false };
    yayinlaAcik.value = false;
    toast.success('Sayfa yayınlandı. Site birkaç saniye içinde güncellenir.');
    if (revizyonAcik.value) revizyonlariYukle();
  } catch {
    /* interceptor toast gösterir */
  } finally {
    islem.value = '';
  }
}

async function yayindanKaldir() {
  const ok = await confirm({
    title: 'Yayından Kaldır',
    message: `"${sayfa.value.baslik}" sayfası sitede görünmez olacak (404). Menüdeki bağlantıları da gizlenir. Taslak içerik korunur.`,
    confirmLabel: 'Yayından Kaldır',
    variant: 'warning',
  });
  if (!ok) return;
  islem.value = 'kaldir';
  try {
    const d = await yayindanKaldirSayfa(sayfa.value.id);
    // Yalnız durum alanları alınır; ekrandaki kaydedilmemiş taslak/meta korunur.
    durumUygula(d);
    sayfa.value = { ...sayfa.value, durum: d?.durum || 'taslak' };
    toast.success('Sayfa yayından kaldırıldı.');
  } catch { /* toast */ } finally {
    islem.value = '';
  }
}

// ── Revizyonlar ──────────────────────────────────────────────────────────────
async function revizyonlariYukle() {
  revizyonYukleniyor.value = true;
  try {
    revizyonlar.value = await listRevizyonlar(sayfa.value.id);
  } catch { revizyonlar.value = []; } finally {
    revizyonYukleniyor.value = false;
  }
}
function revizyonlariAc() {
  revizyonAcik.value = true;
  revizyonlariYukle();
}
async function geriAl(r) {
  const ok = await confirm({
    title: 'Revizyona Geri Dön',
    message: `${tarihFormat(r.yayin_tarihi)} tarihli revizyon taslağa yüklenecek ve HEMEN yeniden yayınlanacak.`
      + (kirli.value ? ' Kaydedilmemiş değişiklikleriniz kaybolacak.' : ''),
    confirmLabel: 'Geri Al ve Yayınla',
    variant: 'warning',
  });
  if (!ok) return;
  islem.value = 'geri-al';
  try {
    await geriAlRevizyon(sayfa.value.id, r.id);
    toast.success('Revizyon geri alındı ve yayınlandı.');
    await yukle();
    await revizyonlariYukle();
  } catch { /* toast */ } finally {
    islem.value = '';
  }
}

async function cakismaYenile() {
  const ok = await confirm({
    title: 'Güncel Hali Yükle',
    message: 'Sayfanın sunucudaki son hali yüklenecek. Bu ekrandaki kaydedilmemiş değişiklikler kaybolur.',
    confirmLabel: 'Yükle',
    variant: 'warning',
  });
  if (ok) yukle();
}

// ── Blok işlemleri ───────────────────────────────────────────────────────────
const filtreliTipler = computed(() => {
  const q = blokArama.value.trim().toLocaleLowerCase('tr-TR');
  if (!q) return blokTipleri.value;
  return blokTipleri.value.filter((t) =>
    `${t.ad} ${t.aciklama || ''} ${t.tip}`.toLocaleLowerCase('tr-TR').includes(q));
});

function blokEkle(tanim) {
  const yeni = {
    _key: yeniKey(),
    id: null,
    tip: tanim.tip,
    veri: varsayilanVeri(tanim.alanlar || []),
    gorunur: true,
    anchor_id: '',
  };
  const idx = bloklar.value.findIndex((b) => b._key === seciliKey.value);
  const liste = [...bloklar.value];
  liste.splice(idx >= 0 ? idx + 1 : liste.length, 0, yeni);
  bloklar.value = liste;
  seciliKey.value = yeni._key;
  blokEkleAcik.value = false;
  blokArama.value = '';
}

function blokKopyala(b) {
  const kopya = { ...klonla({ tip: b.tip, veri: b.veri, gorunur: b.gorunur }), _key: yeniKey(), id: null, anchor_id: '' };
  const idx = bloklar.value.indexOf(b);
  const liste = [...bloklar.value];
  liste.splice(idx + 1, 0, kopya);
  bloklar.value = liste;
  seciliKey.value = kopya._key;
  toast.info('Blok kopyalandı (anchor boşaltıldı).');
}

async function blokSil(b) {
  const ad = tipHaritasi.value[b.tip]?.ad || b.tip;
  const ok = await confirm({
    title: 'Bloğu Sil',
    message: `"${ad}" bloğu taslaktan kaldırılacak. Değişiklik "Taslağı Kaydet" ile kalıcı olur.`,
    confirmLabel: 'Sil',
    variant: 'danger',
  });
  if (!ok) return;
  const idx = bloklar.value.indexOf(b);
  bloklar.value = bloklar.value.filter((x) => x !== b);
  if (seciliKey.value === b._key) {
    seciliKey.value = bloklar.value[Math.min(idx, bloklar.value.length - 1)]?._key ?? null;
  }
}

function blokGorunurluk(b) {
  b.gorunur = !b.gorunur;
}

function ozet(b) {
  return blokOzeti(b.veri, tipHaritasi.value[b.tip]);
}

// ── Klavye kısayolu: Ctrl/Cmd + S ────────────────────────────────────────────
function klavye(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    if (!islem.value) kaydet();
  }
}
onMounted(() => window.addEventListener('keydown', klavye));
onBeforeUnmount(() => window.removeEventListener('keydown', klavye));

const seoBaslikUzunluk = computed(() => (meta.seo_baslik || '').length);
const seoAciklamaUzunluk = computed(() => (meta.seo_aciklama || '').length);
const metaHataMesaji = (alan) => hataMesajlari(metaHatalari.value?.[alan]);
</script>

<template>
  <div class="eisa-page ws-sayfa ws-editor">
    <div v-if="yukleniyor && !sayfa" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor…</div>
    <div v-else-if="yuklemeHatasi" class="ws-bos">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <p>{{ yuklemeHatasi }}</p>
      <RouterLink to="/admin/web-sitesi" class="eisa-btn"><i class="fa-solid fa-arrow-left"></i> Sayfalara dön</RouterLink>
    </div>

    <template v-else-if="sayfa">
      <!-- Üst bar -->
      <header class="ws-editor-ust">
        <div class="ws-editor-kimlik">
          <RouterLink to="/admin/web-sitesi" class="ws-geri" aria-label="Sayfalara dön"><i class="fa-solid fa-arrow-left"></i></RouterLink>
          <div class="ws-editor-baslik-alani">
            <div class="ws-editor-baslik-satir">
              <h1 class="ws-editor-baslik">{{ meta.baslik || 'Adsız sayfa' }}</h1>
              <span class="eisa-pill" :class="durum.sinif">{{ durum.etiket }}</span>
              <span v-if="kirli" class="eisa-pill eisa-pill-warning" title="Bu ekranda kaydedilmemiş değişiklik var">
                <i class="fa-solid fa-circle ws-nokta"></i> Kaydedilmedi
              </span>
              <span v-else-if="sayfa.taslak_degisti" class="eisa-pill eisa-pill-info" title="Taslak, yayındaki sürümden farklı">
                Yayınlanmamış değişiklik
              </span>
            </div>
            <button type="button" class="ws-slug-btn" @click="seoAcik = true">
              /{{ meta.slug === 'anasayfa' ? '' : meta.slug }} <i class="fa-solid fa-pen"></i> Sayfa ve SEO ayarları
            </button>
          </div>
        </div>
        <div class="ws-editor-aksiyonlar">
          <YardimButonu :konular="['sayfa-editoru', 'genel']" />
          <button type="button" class="eisa-btn" :disabled="!!islem" title="Taslağı kaydeder ve yayınlamadan sitede yeni sekmede açar" @click="onizle">
            <i class="fa-solid" :class="islem === 'onizle' ? 'fa-circle-notch fa-spin' : 'fa-eye'"></i> Önizle
          </button>
          <button type="button" class="eisa-btn" @click="revizyonlariAc">
            <i class="fa-solid fa-clock-rotate-left"></i> Revizyonlar
          </button>
          <button v-if="sayfa.durum === 'yayinda'" type="button" class="eisa-btn" :disabled="!!islem" @click="yayindanKaldir">
            <i class="fa-solid fa-eye-slash"></i> Yayından kaldır
          </button>
          <button type="button" class="eisa-btn" :disabled="!!islem || cakisma" title="Ctrl+S" @click="kaydet()">
            <i class="fa-solid" :class="islem === 'kaydet' ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i> Taslağı Kaydet
          </button>
          <button type="button" class="eisa-btn eisa-btn-cta" :disabled="!!islem || cakisma" @click="yayinlaAc">
            <i class="fa-solid fa-rocket"></i> Yayınla
          </button>
        </div>
      </header>

      <div v-if="cakisma" class="ws-banner ws-banner--hata" role="alert">
        <i class="fa-solid fa-code-merge"></i>
        <div>
          <strong>Sürüm çakışması</strong>
          <p>Bu sayfa siz düzenlerken başka bir oturumda kaydedildi. Üzerine yazmamak için kaydetme durduruldu.
            Güncel hali yükleyip değişikliklerinizi yeniden uygulayın.</p>
        </div>
        <button type="button" class="eisa-btn eisa-btn--sm" @click="cakismaYenile">Güncel hali yükle</button>
      </div>

      <div class="ws-editor-govde">
        <!-- Sol: blok listesi -->
        <aside class="ws-blok-paneli eisa-panel">
          <div class="ws-blok-paneli-ust">
            <h2 class="eisa-panel-title">Bloklar <span class="ws-sayac">({{ bloklar.length }})</span></h2>
            <button type="button" class="eisa-btn eisa-btn--sm eisa-btn-cta" @click="blokEkleAcik = true">
              <i class="fa-solid fa-plus"></i> Blok ekle
            </button>
          </div>
          <p v-if="!bloklar.length" class="ws-bos-mini">Bu sayfada henüz blok yok. "Blok ekle" ile başlayın.</p>
          <draggable v-model="bloklar" item-key="_key" handle=".ws-tutamac" :animation="150"
            ghost-class="ws-surukle-hayalet" class="ws-blok-listesi" tag="ul">
            <template #item="{ element: b, index: i }">
              <li class="ws-blok-oge"
                :class="{ 'is-active': b._key === seciliKey, 'is-gizli': !b.gorunur, 'is-hatali': blokHataliMi(b) }"
                @click="seciliKey = b._key">
                <span class="ws-tutamac" title="Sürükleyerek sırala" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
                <span class="ws-blok-ikon"><WebIkon :ad="tipHaritasi[b.tip]?.ikon" :size="18" /></span>
                <div class="ws-blok-oge-metin">
                  <span class="ws-blok-oge-ad">
                    <span class="ws-sira">{{ i + 1 }}.</span> {{ tipHaritasi[b.tip]?.ad || b.tip }}
                    <i v-if="blokHataliMi(b)" class="fa-solid fa-circle-exclamation ws-hata-ikon" title="Bu blokta hata var"></i>
                  </span>
                  <span class="ws-blok-oge-ozet">{{ ozet(b) || '—' }}</span>
                  <span v-if="b.anchor_id || !b.gorunur" class="ws-blok-oge-etiketler">
                    <span v-if="b.anchor_id" class="ws-etiket">#{{ b.anchor_id }}</span>
                    <span v-if="!b.gorunur" class="ws-etiket ws-etiket--gri">Gizli</span>
                  </span>
                </div>
                <div class="ws-blok-oge-aksiyon" @click.stop>
                  <button type="button" class="eisa-icon-btn" :title="b.gorunur ? 'Gizle' : 'Göster'"
                    :aria-label="b.gorunur ? 'Gizle' : 'Göster'" @click="blokGorunurluk(b)">
                    <i class="fa-solid" :class="b.gorunur ? 'fa-eye' : 'fa-eye-slash'"></i>
                  </button>
                  <button type="button" class="eisa-icon-btn" title="Kopyala" aria-label="Kopyala" @click="blokKopyala(b)">
                    <i class="fa-regular fa-copy"></i>
                  </button>
                  <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="blokSil(b)">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </li>
            </template>
          </draggable>
        </aside>

        <!-- Sağ: blok formu -->
        <section class="ws-editor-form eisa-panel">
          <BlokFormu v-if="seciliBlok" :key="seciliBlok._key" :blok="seciliBlok" :tip-tanimi="tipHaritasi[seciliBlok.tip]"
            :hata="blokHatalari[seciliBlok._key]" :anchor-hatasi="anchorHatalari[seciliBlok._key] || ''" />
          <div v-else class="ws-bos">
            <i class="fa-regular fa-hand-pointer"></i>
            <p>Düzenlemek için soldan bir blok seçin.</p>
          </div>
        </section>
      </div>
    </template>

    <!-- Blok ekle diyaloğu -->
    <Teleport to="body">
      <div v-if="blokEkleAcik" class="eisa-modal-backdrop" @click.self="blokEkleAcik = false">
        <div class="eisa-modal eisa-modal--medium" role="dialog" aria-modal="true" aria-label="Blok ekle">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">Blok Ekle</h3>
            <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="blokEkleAcik = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-search-wrap ws-mb">
              <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
              <input v-model="blokArama" class="eisa-field eisa-search-field" placeholder="Blok tipi ara…" />
            </div>
            <p class="ws-yardim ws-mb">Yeni blok, seçili bloğun altına eklenir.</p>
            <div class="ws-blok-tip-grid">
              <button v-for="t in filtreliTipler" :key="t.tip" type="button" class="ws-blok-tip" @click="blokEkle(t)">
                <span class="ws-blok-ikon"><WebIkon :ad="t.ikon" :size="24" /></span>
                <strong>{{ t.ad }}</strong>
                <span>{{ t.aciklama }}</span>
              </button>
              <p v-if="!filtreliTipler.length" class="ws-bos-mini">Eşleşen blok tipi yok.</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Yayınla diyaloğu -->
    <Teleport to="body">
      <div v-if="yayinlaAcik" class="eisa-modal-backdrop" @click.self="yayinlaAcik = false">
        <div class="eisa-modal" role="dialog" aria-modal="true" aria-label="Yayınla">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">Sayfayı Yayınla</h3>
            <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="yayinlaAcik = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <p class="ws-yardim ws-mb">
              Taslak içerik yeni bir revizyon olarak yayınlanır ve site birkaç saniye içinde güncellenir.
              <template v-if="kirli"><br /><strong>Kaydedilmemiş değişiklikler önce taslağa kaydedilecek.</strong></template>
            </p>
            <label class="eisa-field-label" for="ws-yayin-notu">Revizyon notu (opsiyonel)</label>
            <textarea id="ws-yayin-notu" v-model="yayinNotu" rows="3" maxlength="300" class="eisa-field"
              placeholder="ör. SSS bölümüne 2 yeni soru eklendi"></textarea>
          </div>
          <div class="eisa-modal-footer">
            <button type="button" class="eisa-btn eisa-btn-ghost" :disabled="islem === 'yayinla'" @click="yayinlaAcik = false">Vazgeç</button>
            <button type="button" class="eisa-btn eisa-btn-cta" :disabled="!!islem" @click="yayinla">
              <i class="fa-solid" :class="islem === 'yayinla' ? 'fa-circle-notch fa-spin' : 'fa-rocket'"></i> Yayınla
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Sayfa / SEO çekmecesi -->
    <WsCekmece :open="seoAcik" title="Sayfa ve SEO Ayarları" subtitle="Değişiklikler &quot;Taslağı Kaydet&quot; ile kaydedilir."
      @close="seoAcik = false">
      <div class="ws-form-dikey">
        <div class="ws-alan" :class="{ 'ws-alan--hatali': metaHataMesaji('baslik').length }">
          <label class="eisa-field-label" for="ws-meta-baslik">Sayfa başlığı<span class="ws-zorunlu">*</span></label>
          <input id="ws-meta-baslik" v-model="meta.baslik" class="eisa-field" maxlength="160" />
          <p v-for="m in metaHataMesaji('baslik')" :key="m" class="ws-alan-hata">{{ m }}</p>
        </div>
        <div class="ws-alan" :class="{ 'ws-alan--hatali': metaHataMesaji('slug').length }">
          <label class="eisa-field-label" for="ws-meta-slug">Adres (slug)<span class="ws-zorunlu">*</span></label>
          <div class="eisa-input-group">
            <span class="eisa-input-prefix">eisa.com.tr/</span>
            <input id="ws-meta-slug" v-model="meta.slug" class="eisa-field" :disabled="korumali" maxlength="80" />
          </div>
          <p v-if="korumali" class="ws-yardim">Bu sistem sayfasının adresi değiştirilemez.</p>
          <p v-else class="ws-yardim">Küçük harf, rakam ve tire. Adresi değiştirmek eski bağlantıları kırar.</p>
          <p v-for="m in metaHataMesaji('slug')" :key="m" class="ws-alan-hata">{{ m }}</p>
        </div>
        <div class="ws-alan">
          <div class="ws-alan-ust">
            <label class="eisa-field-label" for="ws-meta-seo-baslik">SEO başlığı</label>
            <span class="ws-sayac" :class="{ 'is-asim': seoBaslikUzunluk > 60 }">{{ seoBaslikUzunluk }}/60</span>
          </div>
          <input id="ws-meta-seo-baslik" v-model="meta.seo_baslik" class="eisa-field" maxlength="160"
            :placeholder="meta.baslik" />
          <p class="ws-yardim">Boş bırakılırsa sayfa başlığı kullanılır.</p>
          <p v-for="m in metaHataMesaji('seo_baslik')" :key="m" class="ws-alan-hata">{{ m }}</p>
        </div>
        <div class="ws-alan">
          <div class="ws-alan-ust">
            <label class="eisa-field-label" for="ws-meta-seo-aciklama">SEO açıklaması</label>
            <span class="ws-sayac" :class="{ 'is-asim': seoAciklamaUzunluk > 160 }">{{ seoAciklamaUzunluk }}/160</span>
          </div>
          <textarea id="ws-meta-seo-aciklama" v-model="meta.seo_aciklama" rows="3" class="eisa-field" maxlength="320"></textarea>
          <p v-for="m in metaHataMesaji('seo_aciklama')" :key="m" class="ws-alan-hata">{{ m }}</p>
        </div>
        <div class="ws-alan">
          <span class="eisa-field-label">Paylaşım görseli (OG)</span>
          <MedyaSecici v-model="meta.og_gorsel" />
          <p class="ws-yardim">Önerilen ölçü 1200×630. Boşsa site ayarlarındaki varsayılan görsel kullanılır.</p>
        </div>
        <div class="ws-alan">
          <label class="eisa-field-label" for="ws-meta-sira">Sıra</label>
          <input id="ws-meta-sira" v-model.number="meta.sira" type="number" class="eisa-field ws-sayi" />
        </div>
        <div class="ws-serp" aria-label="Arama sonucu önizlemesi">
          <span class="ws-serp-url">eisa.com.tr/{{ meta.slug === 'anasayfa' ? '' : meta.slug }}</span>
          <span class="ws-serp-baslik">{{ meta.seo_baslik || meta.baslik || 'Sayfa başlığı' }}</span>
          <span class="ws-serp-aciklama">{{ meta.seo_aciklama || 'Açıklama girilmedi; site varsayılan açıklaması kullanılır.' }}</span>
        </div>
      </div>
      <template #footer>
        <button type="button" class="eisa-btn eisa-btn-cta" @click="seoAcik = false"><i class="fa-solid fa-check"></i> Tamam</button>
      </template>
    </WsCekmece>

    <!-- Revizyonlar çekmecesi -->
    <WsCekmece :open="revizyonAcik" title="Revizyonlar" subtitle="Her yayın bir revizyon oluşturur." @close="revizyonAcik = false">
      <div v-if="revizyonYukleniyor" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
      <p v-else-if="!revizyonlar.length" class="ws-bos-mini">Bu sayfa henüz hiç yayınlanmamış.</p>
      <ol v-else class="ws-revizyonlar">
        <li v-for="r in revizyonlar" :key="r.id" :class="{ 'is-aktif': r.aktif }">
          <div class="ws-revizyon-ust">
            <strong>{{ tarihFormat(r.yayin_tarihi) }}</strong>
            <span v-if="r.aktif" class="eisa-pill eisa-pill-success">Yayında</span>
          </div>
          <span class="ws-revizyon-kisi"><i class="fa-regular fa-user"></i> {{ r.yayinlayan_adi || '—' }}</span>
          <p v-if="r.not" class="ws-revizyon-not">{{ r.not }}</p>
          <button v-if="!r.aktif" type="button" class="eisa-btn eisa-btn--sm" :disabled="!!islem" @click="geriAl(r)">
            <i class="fa-solid fa-clock-rotate-left"></i> Bu sürüme geri dön
          </button>
        </li>
      </ol>
    </WsCekmece>
  </div>
</template>
