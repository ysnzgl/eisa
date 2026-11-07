<script setup>
/**
 * Web Sitesi › Sayfalar — CMS sayfa listesi.
 * Oluştur (başlık/slug), durum, yayınlanmamış değişiklik göstergesi, taslak önizleme, sil
 * (anasayfa, kvkk, cerez-politikasi korumalıdır).
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { listSayfalar, createSayfa, deleteSayfa, sayfaOnizleme } from '../../../services/website';
import { humanError } from '../../../services/api';
import {
  slugOlustur, SLUG_REGEX, AYRILMIS_SLUGLAR, KORUMALI_SAYFALAR, SAYFA_DURUMLARI, tarihFormat,
  hatalariAgacaCevir, hataMesajlari,
} from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';

const router = useRouter();
const { confirm } = useConfirm();

const sayfalar = ref([]);
const loading = ref(false);
const arama = ref('');

// ── Önizle: taslağı yayınlamadan sitede yeni sekmede aç ─────────────────────
const onizlenen = ref(null);
async function onizle(s) {
  // Açılır pencere engelleyicisine takılmamak için sekme tıklama anında açılır.
  const sekme = window.open('about:blank', '_blank');
  onizlenen.value = s.id;
  try {
    const { url } = await sayfaOnizleme(s.id);
    if (sekme) sekme.location.href = url;
    else window.open(url, '_blank', 'noopener');
  } catch (e) {
    sekme?.close();
    toast.error(humanError(e));
  } finally {
    onizlenen.value = null;
  }
}

const formAcik = ref(false);
const kaydediliyor = ref(false);
const form = reactive({ baslik: '', slug: '' });
const slugElle = ref(false);
const formHatalari = ref({});

const filtreli = computed(() => {
  const q = arama.value.trim().toLocaleLowerCase('tr-TR');
  const liste = [...sayfalar.value].sort((a, b) => (a.sira ?? 0) - (b.sira ?? 0) || a.baslik.localeCompare(b.baslik, 'tr'));
  if (!q) return liste;
  return liste.filter((s) => `${s.baslik} ${s.slug}`.toLocaleLowerCase('tr-TR').includes(q));
});

const istatistik = computed(() => ({
  toplam: sayfalar.value.length,
  yayinda: sayfalar.value.filter((s) => s.durum === 'yayinda').length,
  taslak: sayfalar.value.filter((s) => s.durum !== 'yayinda').length,
  degisti: sayfalar.value.filter((s) => s.taslak_degisti).length,
}));

async function load() {
  loading.value = true;
  try {
    sayfalar.value = await listSayfalar();
  } catch { /* interceptor toast */ } finally {
    loading.value = false;
  }
}
onMounted(load);

function durumBilgi(d) {
  return SAYFA_DURUMLARI[d] || { etiket: d || '—', sinif: 'eisa-pill-muted' };
}
function korumali(s) {
  return KORUMALI_SAYFALAR.includes(s.slug);
}
function yol(s) {
  return s.slug === 'anasayfa' ? '/' : `/${s.slug}`;
}

// ── Oluştur ─────────────────────────────────────────────────────────────────
function yeniAc() {
  Object.assign(form, { baslik: '', slug: '' });
  slugElle.value = false;
  formHatalari.value = {};
  formAcik.value = true;
}
watch(() => form.baslik, (b) => { if (!slugElle.value) form.slug = slugOlustur(b); });

function slugDegisti(e) {
  slugElle.value = true;
  form.slug = e.target.value.toLowerCase();
}

function dogrula() {
  const h = {};
  if (!form.baslik.trim()) h.baslik = ['Başlık zorunludur.'];
  if (!form.slug) h.slug = ['Slug zorunludur.'];
  else if (!SLUG_REGEX.test(form.slug)) h.slug = ['Yalnızca küçük harf (a-z), rakam ve tire kullanılabilir.'];
  else if (AYRILMIS_SLUGLAR.includes(form.slug)) h.slug = ['Bu adres sistem tarafından ayrılmıştır.'];
  else if (sayfalar.value.some((s) => s.slug === form.slug)) h.slug = ['Bu adresle bir sayfa zaten var.'];
  formHatalari.value = h;
  return !Object.keys(h).length;
}

async function olustur() {
  if (!dogrula()) return;
  kaydediliyor.value = true;
  try {
    const yeni = await createSayfa({
      baslik: form.baslik.trim(),
      slug: form.slug,
      seo_baslik: '',
      seo_aciklama: '',
      og_gorsel: null,
      sira: sayfalar.value.length,
    });
    toast.success('Sayfa oluşturuldu.');
    formAcik.value = false;
    if (yeni?.id) router.push(`/admin/web-sitesi/sayfalar/${yeni.id}`);
    else load();
  } catch (e) {
    if (e?.response?.status === 400) {
      formHatalari.value = hatalariAgacaCevir(e.response.data) || {};
      toast.error(hataMesajlari(formHatalari.value.detail)[0] || 'Sayfa oluşturulamadı; alanları kontrol edin.');
    } else {
      toast.error(humanError(e));
    }
  } finally {
    kaydediliyor.value = false;
  }
}

// ── Sil ─────────────────────────────────────────────────────────────────────
async function sil(s) {
  if (korumali(s)) return;
  const ok = await confirm({
    title: 'Sayfayı Sil',
    message: `"${s.baslik}" (/${s.slug}) sayfası ve tüm revizyonları kalıcı olarak silinecek.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteSayfa(s.id);
    toast.success('Sayfa silindi.');
    await load();
  } catch { /* interceptor backend mesajını (ör. menüde kullanılıyor) gösterir */ }
}
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Sayfalar</h1>
        <p class="eisa-page-subtitle">eisa.com.tr sayfalarını blok blok düzenleyin, önizleyin ve yayınlayın.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['sayfalar', 'genel']" />
        <SiteOnizleButonu />
        <button type="button" class="eisa-btn" :disabled="loading" @click="load">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i> Yenile
        </button>
        <button type="button" class="eisa-btn eisa-btn-cta" @click="yeniAc">
          <i class="fa-solid fa-plus"></i> Yeni Sayfa
        </button>
      </div>
    </header>

    <section class="eisa-stats">
      <div class="eisa-stat-card"><span class="eisa-stat-label">Toplam</span><span class="eisa-stat-value">{{ istatistik.toplam }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Yayında</span><span class="eisa-stat-value">{{ istatistik.yayinda }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Taslak / Arşiv</span><span class="eisa-stat-value">{{ istatistik.taslak }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Yayınlanmamış Değişiklik</span><span class="eisa-stat-value">{{ istatistik.degisti }}</span></div>
    </section>

    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Sayfalar ({{ filtreli.length }})</h2>
        <div class="eisa-search-wrap ws-arama-dar">
          <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
          <input v-model="arama" class="eisa-field eisa-search-field" placeholder="Başlık veya adres ara…" />
        </div>
      </div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Sayfa</th>
              <th>Durum</th>
              <th>Son Yayın</th>
              <th>Son Güncelleme</th>
              <th class="actions-col">İşlem</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && !sayfalar.length"><td colspan="5" class="empty-row">Yükleniyor…</td></tr>
            <tr v-else-if="!filtreli.length"><td colspan="5" class="empty-row">Kayıt bulunamadı</td></tr>
            <tr v-for="s in filtreli" :key="s.id" class="ws-tiklanir" @click="router.push(`/admin/web-sitesi/sayfalar/${s.id}`)">
              <td>
                <div class="eisa-cell-name">
                  {{ s.baslik }}
                  <i v-if="korumali(s)" class="fa-solid fa-lock ws-kilit" title="Sistem sayfası (silinemez)"></i>
                </div>
                <div class="eisa-cell-sub ws-mono">{{ yol(s) }}</div>
              </td>
              <td>
                <span class="eisa-pill" :class="durumBilgi(s.durum).sinif">{{ durumBilgi(s.durum).etiket }}</span>
                <span v-if="s.taslak_degisti" class="eisa-pill eisa-pill-info ws-ml" title="Taslak, yayındaki sürümden farklı">
                  <i class="fa-solid fa-pen-to-square"></i> Yayınlanmamış değişiklik
                </span>
              </td>
              <td class="cell-muted">{{ tarihFormat(s.yayin_tarihi) }}</td>
              <td class="cell-muted">{{ tarihFormat(s.guncellenme_tarihi) }}</td>
              <td class="cell-actions" @click.stop>
                <button type="button" class="eisa-icon-btn" :disabled="onizlenen === s.id"
                  title="Önizle — taslağı yayınlamadan sitede aç" aria-label="Önizle" @click="onizle(s)">
                  <i class="fa-solid" :class="onizlenen === s.id ? 'fa-circle-notch fa-spin' : 'fa-eye'"></i>
                </button>
                <RouterLink :to="`/admin/web-sitesi/sayfalar/${s.id}`" class="eisa-icon-btn" title="Düzenle" aria-label="Düzenle">
                  <i class="fa-solid fa-pen"></i>
                </RouterLink>
                <button type="button" class="eisa-icon-btn danger" :disabled="korumali(s)"
                  :title="korumali(s) ? 'Sistem sayfası silinemez' : 'Sil'" aria-label="Sil" @click="sil(s)">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Yeni sayfa -->
    <Teleport to="body">
      <div v-if="formAcik" class="eisa-modal-backdrop" @click.self="formAcik = false">
        <form class="eisa-modal" role="dialog" aria-modal="true" aria-label="Yeni sayfa" @submit.prevent="olustur">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">Yeni Sayfa</h3>
            <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="formAcik = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body ws-form-dikey">
            <div class="ws-alan" :class="{ 'ws-alan--hatali': hataMesajlari(formHatalari.baslik).length }">
              <label class="eisa-field-label" for="ws-yeni-baslik">Başlık<span class="ws-zorunlu">*</span></label>
              <input id="ws-yeni-baslik" v-model="form.baslik" class="eisa-field" maxlength="160" autofocus />
              <p v-for="m in hataMesajlari(formHatalari.baslik)" :key="m" class="ws-alan-hata">{{ m }}</p>
            </div>
            <div class="ws-alan" :class="{ 'ws-alan--hatali': hataMesajlari(formHatalari.slug).length }">
              <label class="eisa-field-label" for="ws-yeni-slug">Adres (slug)<span class="ws-zorunlu">*</span></label>
              <div class="eisa-input-group">
                <span class="eisa-input-prefix">eisa.com.tr/</span>
                <input id="ws-yeni-slug" :value="form.slug" class="eisa-field" maxlength="80" @input="slugDegisti" />
              </div>
              <p class="ws-yardim">Başlıktan otomatik üretilir. Ayrılmış adresler: {{ AYRILMIS_SLUGLAR.join(', ') }}.</p>
              <p v-for="m in hataMesajlari(formHatalari.slug)" :key="m" class="ws-alan-hata">{{ m }}</p>
            </div>
            <p class="ws-yardim">Sayfa taslak olarak oluşturulur; blokları ekledikten sonra yayınlayabilirsiniz.</p>
          </div>
          <div class="eisa-modal-footer">
            <button type="button" class="eisa-btn eisa-btn-ghost" @click="formAcik = false">Vazgeç</button>
            <button type="submit" class="eisa-btn eisa-btn-cta" :disabled="kaydediliyor">
              <i class="fa-solid" :class="kaydediliyor ? 'fa-circle-notch fa-spin' : 'fa-check'"></i> Oluştur ve Düzenle
            </button>
          </div>
        </form>
      </div>
    </Teleport>
  </div>
</template>
