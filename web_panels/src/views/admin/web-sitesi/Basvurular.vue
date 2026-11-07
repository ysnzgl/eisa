<script setup>
/**
 * Web Sitesi › Başvurular — site formlarından gelen pilot / sponsor / genel
 * başvurular (portal gelen kutusu). Filtre, arama, sayfalama, detay çekmecesi
 * (durum, not, atanan), silme ve mevcut filtreyle Excel dışa aktarım.
 */
import YardimButonu from '../../../components/website/YardimButonu.vue';
import SiteOnizleButonu from '../../../components/website/SiteOnizleButonu.vue';
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { listBasvurular, updateBasvuru, deleteBasvuru } from '../../../services/website';
import { http } from '../../../services/api';
import { useAuthStore } from '../../../stores/auth';
import { tarihFormat } from '../../../lib/websiteForm';
import { useConfirm } from '../../../composables/useConfirm.js';
import { useExcelExport } from '../../../composables/useExcelExport.js';
import WsCekmece from '../../../components/website/WsCekmece.vue';

const auth = useAuthStore();
const { confirm } = useConfirm();
const { exportToExcel } = useExcelExport();

const TIPLER = { pilot: 'Pilot', sponsor: 'Sponsor', genel: 'Genel' };
const TIP_SINIF = { pilot: 'eisa-pill-info', sponsor: 'eisa-pill-warning', genel: 'eisa-pill-muted' };
const DURUMLAR = {
  yeni: { etiket: 'Yeni', sinif: 'eisa-pill-danger' },
  incelendi: { etiket: 'İncelendi', sinif: 'eisa-pill-info' },
  iletisimde: { etiket: 'İletişimde', sinif: 'eisa-pill-warning' },
  kapandi: { etiket: 'Kapandı', sinif: 'eisa-pill-muted' },
};
const PAGE_SIZE = 24;

const filtre = reactive({ tip: '', durum: '', q: '' });
const page = ref(1);
const count = ref(0);
const results = ref([]);
const yeniSayisi = ref(0);
const loading = ref(false);
const disaAktariliyor = ref(false);

const detay = ref(null);
const detayForm = reactive({ durum: 'yeni', notlar: '', atanan_id: null });
const kaydediliyor = ref(false);
const kullanicilar = ref([]);

const toplamSayfa = computed(() => Math.max(1, Math.ceil(count.value / PAGE_SIZE)));

function parametreler(extra = {}) {
  return {
    tip: filtre.tip || undefined,
    durum: filtre.durum || undefined,
    q: filtre.q.trim() || undefined,
    ...extra,
  };
}

async function load() {
  loading.value = true;
  try {
    const d = await listBasvurular(parametreler({ page: page.value, page_size: PAGE_SIZE }));
    count.value = d.count;
    results.value = d.results;
    yeniSayisi.value = d.yeni_sayisi;
  } catch { /* toast */ } finally {
    loading.value = false;
  }
}

let aramaZamanlayici = null;
watch(() => filtre.q, () => {
  clearTimeout(aramaZamanlayici);
  aramaZamanlayici = setTimeout(() => { if (page.value !== 1) page.value = 1; else load(); }, 300);
});
watch(() => [filtre.tip, filtre.durum], () => { if (page.value !== 1) page.value = 1; else load(); });
watch(page, load);
onMounted(() => { load(); kullanicilariYukle(); });
onBeforeUnmount(() => clearTimeout(aramaZamanlayici));

function filtreTemizle() {
  Object.assign(filtre, { tip: '', durum: '', q: '' });
}

/** Atama listesi: kullanıcı listesine yalnız superadmin erişebilir; erişim yoksa sessizce geçilir. */
async function kullanicilariYukle() {
  try {
    const { data } = await http.get('/api/users/', { __silent: true });
    const liste = Array.isArray(data) ? data : (data?.results ?? []);
    kullanicilar.value = liste
      .filter((u) => u.is_active !== false && ['superadmin', 'editor'].includes(u.rol))
      .map((u) => ({ id: u.id, ad: u.full_name || [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username }));
  } catch {
    kullanicilar.value = [];
  }
}
const atamaSecenekleri = computed(() => {
  const liste = [...kullanicilar.value];
  const atanan = detay.value?.atanan;
  if (atanan && !liste.some((k) => k.id === atanan.id)) liste.unshift(atanan);
  if (auth.userId && !liste.some((k) => k.id === auth.userId)) liste.unshift({ id: auth.userId, ad: 'Ben' });
  return liste;
});

function rozetleriYenile() {
  window.dispatchEvent(new Event('eisa-nav-badges-refresh'));
}

// ── Detay ────────────────────────────────────────────────────────────────────
function detayAc(b) {
  detay.value = b;
  Object.assign(detayForm, { durum: b.durum, notlar: b.notlar || '', atanan_id: b.atanan?.id ?? null });
}
const detayKirli = computed(() => detay.value && (
  detayForm.durum !== detay.value.durum
  || detayForm.notlar !== (detay.value.notlar || '')
  || detayForm.atanan_id !== (detay.value.atanan?.id ?? null)));

async function detayKaydet() {
  if (!detay.value) return;
  kaydediliyor.value = true;
  try {
    const d = await updateBasvuru(detay.value.id, {
      durum: detayForm.durum,
      notlar: detayForm.notlar,
      atanan_id: detayForm.atanan_id,
    });
    const guncel = { ...detay.value, ...(d || {}) };
    detay.value = guncel;
    results.value = results.value.map((r) => (r.id === guncel.id ? guncel : r));
    toast.success('Başvuru güncellendi.');
    rozetleriYenile();
    load();
  } catch { /* toast */ } finally {
    kaydediliyor.value = false;
  }
}

async function detayKapat() {
  if (detayKirli.value) {
    const ok = await confirm({
      title: 'Kaydedilmemiş Değişiklikler',
      message: 'Başvuruda yaptığınız değişiklikler kaydedilmedi. Kapatılsın mı?',
      confirmLabel: 'Kapat',
      variant: 'warning',
    });
    if (!ok) return;
  }
  detay.value = null;
}

async function sil(b) {
  const ok = await confirm({
    title: 'Başvuruyu Sil',
    message: `${b.ad_soyad} adlı kişinin başvurusu kalıcı olarak silinecek. Bu işlem geri alınamaz.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteBasvuru(b.id);
    toast.success('Başvuru silindi.');
    if (detay.value?.id === b.id) detay.value = null;
    rozetleriYenile();
    if (results.value.length === 1 && page.value > 1) page.value -= 1;
    else load();
  } catch { /* toast */ }
}

// ── Excel ────────────────────────────────────────────────────────────────────
const EXCEL_KOLONLARI = [
  { label: 'ID', key: 'id' },
  { label: 'Tarih', fn: (r) => (r.olusturulma_tarihi ? new Date(r.olusturulma_tarihi).toLocaleString('tr-TR') : '') },
  { label: 'Tip', fn: (r) => TIPLER[r.tip] || r.tip },
  { label: 'Durum', fn: (r) => DURUMLAR[r.durum]?.etiket || r.durum },
  { label: 'Ad Soyad', key: 'ad_soyad' },
  { label: 'Kurum', key: 'kurum' },
  { label: 'E-posta', key: 'eposta' },
  { label: 'Telefon', key: 'telefon' },
  { label: 'İl', key: 'il' },
  { label: 'Mesaj', key: 'mesaj' },
  { label: 'KVKK Onayı', fn: (r) => (r.kvkk_onay ? 'Evet' : 'Hayır') },
  { label: 'KVKK Metin Versiyonu', key: 'kvkk_metin_versiyonu' },
  { label: 'Kaynak Sayfa', key: 'kaynak_sayfa' },
  { label: 'Atanan', fn: (r) => r.atanan?.ad || '' },
  { label: 'Notlar', key: 'notlar' },
];

async function disaAktar() {
  disaAktariliyor.value = true;
  try {
    const tumu = [];
    let p = 1;
    // Mevcut filtreyle tüm sayfalar (sayfa başı en fazla 100).
    for (;;) {
      const d = await listBasvurular(parametreler({ page: p, page_size: 100 }));
      tumu.push(...d.results);
      if (!d.results.length || tumu.length >= d.count) break;
      p += 1;
    }
    if (!tumu.length) { toast.info('Dışa aktarılacak başvuru yok.'); return; }
    const tarih = new Date().toISOString().slice(0, 10);
    exportToExcel(tumu, EXCEL_KOLONLARI, `web-basvurulari-${tarih}.xlsx`, 'Başvurular');
    toast.success(`${tumu.length} başvuru dışa aktarıldı.`);
  } catch { /* toast */ } finally {
    disaAktariliyor.value = false;
  }
}

function telLink(t) {
  return `tel:${String(t || '').replace(/[^\d+]/g, '')}`;
}
</script>

<template>
  <div class="eisa-page ws-sayfa">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Web Sitesi</p>
        <h1 class="eisa-page-title">Başvurular</h1>
        <p class="eisa-page-subtitle">Siteden gelen pilot, sponsor ve iletişim başvuruları.</p>
      </div>
      <div class="eisa-header-actions">
        <YardimButonu :konular="['basvurular']" />
        <SiteOnizleButonu />
        <button type="button" class="eisa-btn" :disabled="loading" @click="load">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i> Yenile
        </button>
        <button type="button" class="eisa-btn" :disabled="disaAktariliyor" @click="disaAktar">
          <i class="fa-solid" :class="disaAktariliyor ? 'fa-circle-notch fa-spin' : 'fa-file-excel'"></i> Excel'e Aktar
        </button>
      </div>
    </header>

    <section class="eisa-stats">
      <div class="eisa-stat-card"><span class="eisa-stat-label">Yeni</span><span class="eisa-stat-value">{{ yeniSayisi }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Filtreye Uyan</span><span class="eisa-stat-value">{{ count }}</span></div>
    </section>

    <section class="eisa-panel eisa-toolbar-panel">
      <div class="eisa-toolbar">
        <div class="eisa-search-wrap">
          <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
          <input v-model="filtre.q" class="eisa-field eisa-search-field" placeholder="Ad, kurum, e-posta, telefon ara…" />
        </div>
        <select v-model="filtre.tip" class="eisa-field eisa-filter">
          <option value="">Tüm Tipler</option>
          <option v-for="(e, k) in TIPLER" :key="k" :value="k">{{ e }}</option>
        </select>
        <select v-model="filtre.durum" class="eisa-field eisa-filter">
          <option value="">Tüm Durumlar</option>
          <option v-for="(d, k) in DURUMLAR" :key="k" :value="k">{{ d.etiket }}</option>
        </select>
        <button v-if="filtre.tip || filtre.durum || filtre.q" type="button" class="eisa-btn eisa-btn-ghost" @click="filtreTemizle">
          <i class="fa-solid fa-filter-circle-xmark"></i> Temizle
        </button>
      </div>
    </section>

    <section class="eisa-panel">
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr><th>Tarih</th><th>Başvuran</th><th>Tip</th><th>İletişim</th><th>İl</th><th>Durum</th><th>Atanan</th><th class="actions-col">İşlem</th></tr>
          </thead>
          <tbody>
            <tr v-if="loading && !results.length"><td colspan="8" class="empty-row">Yükleniyor…</td></tr>
            <tr v-else-if="!results.length"><td colspan="8" class="empty-row">Başvuru bulunamadı</td></tr>
            <tr v-for="b in results" :key="b.id" class="ws-tiklanir" :class="{ 'ws-satir-yeni': b.durum === 'yeni' }" @click="detayAc(b)">
              <td class="cell-muted">{{ tarihFormat(b.olusturulma_tarihi) }}</td>
              <td>
                <div class="eisa-cell-name">{{ b.ad_soyad }}</div>
                <div v-if="b.kurum" class="eisa-cell-sub">{{ b.kurum }}</div>
              </td>
              <td><span class="eisa-pill" :class="TIP_SINIF[b.tip] || 'eisa-pill-muted'">{{ TIPLER[b.tip] || b.tip }}</span></td>
              <td>
                <div>{{ b.eposta }}</div>
                <div v-if="b.telefon" class="eisa-cell-sub">{{ b.telefon }}</div>
              </td>
              <td>{{ b.il || '—' }}</td>
              <td><span class="eisa-pill" :class="DURUMLAR[b.durum]?.sinif || 'eisa-pill-muted'">{{ DURUMLAR[b.durum]?.etiket || b.durum }}</span></td>
              <td class="cell-muted">{{ b.atanan?.ad || '—' }}</td>
              <td class="cell-actions" @click.stop>
                <button type="button" class="eisa-icon-btn" title="Detay" aria-label="Detay" @click="detayAc(b)"><i class="fa-solid fa-eye"></i></button>
                <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" @click="sil(b)"><i class="fa-solid fa-trash"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="toplamSayfa > 1" class="ws-sayfalama eisa-panel-footer">
        <button type="button" class="eisa-icon-btn" :disabled="page <= 1" aria-label="Önceki sayfa" @click="page -= 1"><i class="fa-solid fa-chevron-left"></i></button>
        <span>{{ page }} / {{ toplamSayfa }} · {{ count }} başvuru</span>
        <button type="button" class="eisa-icon-btn" :disabled="page >= toplamSayfa" aria-label="Sonraki sayfa" @click="page += 1"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    </section>

    <WsCekmece :open="!!detay" :title="detay?.ad_soyad || 'Başvuru'"
      :subtitle="detay ? `${TIPLER[detay.tip] || detay.tip} başvurusu · ${tarihFormat(detay.olusturulma_tarihi)}` : ''"
      width="520px" @close="detayKapat">
      <template v-if="detay">
        <dl class="ws-detay-liste">
          <div><dt>Ad Soyad</dt><dd>{{ detay.ad_soyad }}</dd></div>
          <div><dt>Kurum</dt><dd>{{ detay.kurum || '—' }}</dd></div>
          <div><dt>E-posta</dt><dd><a :href="`mailto:${detay.eposta}`">{{ detay.eposta }}</a></dd></div>
          <div><dt>Telefon</dt><dd><a v-if="detay.telefon" :href="telLink(detay.telefon)">{{ detay.telefon }}</a><template v-else>—</template></dd></div>
          <div><dt>İl</dt><dd>{{ detay.il || '—' }}</dd></div>
          <div><dt>Tip</dt><dd>{{ TIPLER[detay.tip] || detay.tip }}</dd></div>
          <div><dt>Kaynak sayfa</dt><dd class="ws-mono">{{ detay.kaynak_sayfa || '—' }}</dd></div>
          <div><dt>KVKK onayı</dt><dd>{{ detay.kvkk_onay ? 'Evet' : 'Hayır' }}<template v-if="detay.kvkk_metin_versiyonu"> · metin v{{ detay.kvkk_metin_versiyonu }}</template></dd></div>
        </dl>
        <div class="ws-mesaj-kutu">
          <span class="ws-mini-label">Mesaj</span>
          <p>{{ detay.mesaj || 'Mesaj yazılmamış.' }}</p>
        </div>

        <div class="ws-form-dikey ws-mt">
          <div class="ws-alan">
            <span class="eisa-field-label">Durum</span>
            <div class="ws-segment">
              <button v-for="(d, k) in DURUMLAR" :key="k" type="button" :class="{ 'is-active': detayForm.durum === k }"
                @click="detayForm.durum = k">{{ d.etiket }}</button>
            </div>
          </div>
          <div class="ws-alan">
            <label class="eisa-field-label" for="ws-basvuru-atanan">Atanan</label>
            <div class="ws-satir">
              <select id="ws-basvuru-atanan" v-model="detayForm.atanan_id" class="eisa-field">
                <option :value="null">— Atanmadı —</option>
                <option v-for="k in atamaSecenekleri" :key="k.id" :value="k.id">{{ k.ad }}</option>
              </select>
              <button v-if="auth.userId && detayForm.atanan_id !== auth.userId" type="button" class="eisa-btn eisa-btn--sm"
                @click="detayForm.atanan_id = auth.userId">Bana ata</button>
            </div>
          </div>
          <div class="ws-alan">
            <label class="eisa-field-label" for="ws-basvuru-not">İç notlar</label>
            <textarea id="ws-basvuru-not" v-model="detayForm.notlar" rows="5" class="eisa-field"
              placeholder="Görüşme notları, sonraki adımlar… (başvurana gösterilmez)"></textarea>
          </div>
        </div>
      </template>
      <template #footer>
        <button type="button" class="eisa-btn ws-btn-tehlike" @click="sil(detay)"><i class="fa-solid fa-trash"></i> Sil</button>
        <span class="ws-bosluk"></span>
        <button type="button" class="eisa-btn eisa-btn-ghost" @click="detayKapat">Kapat</button>
        <button type="button" class="eisa-btn eisa-btn-cta" :disabled="!detayKirli || kaydediliyor" @click="detayKaydet">
          <i class="fa-solid" :class="kaydediliyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i> Kaydet
        </button>
      </template>
    </WsCekmece>
  </div>
</template>
