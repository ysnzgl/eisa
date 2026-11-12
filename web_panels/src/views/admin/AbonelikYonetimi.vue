<script setup>
/**
 * Abonelik Yönetimi (SuperAdmin) — Sözleşmeler, cihaz ödeme planları ve faturalar.
 * Sözleşme tipi 12/24/36 ay + kullanım bedeli öteleme (vade kaydırma) + cihaz taksit matrisi.
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { toast } from 'vue-sonner';
import {
  listSozlesmeler, createSozlesme, updateSozlesme, saveCihazPlanlari,
  listFaturalar, odeFaturaAdmin, uzatSozlesme, getSozlesmeGecmis,
  iptalSozlesme, listTalepler, kararVerTalep, listOdemeler,
  getFaturaAdmin,
  listFiyatlar, createFiyat, deleteFiyat, getAktifFiyat, faturalandir,
  uploadIslakImza, getIslakImzaUrl, getContractDataCheck, downloadGeneratedContract,
} from '../../services/abonelik';
import { getPharmacies } from '../../services/devices';
import SozlesmeForm from '../../components/shared/SozlesmeForm.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import EczanePicker from '../../components/shared/EczanePicker.vue';
import SozlesmeMatbu from '../../components/shared/SozlesmeMatbu.vue';
import FaturaIslemModal from '../../components/shared/FaturaIslemModal.vue';
import { useConfirm } from '../../composables/useConfirm.js';
import { useExcelExport } from '../../composables/useExcelExport.js';

const route = useRoute();
const { confirm } = useConfirm();
const { exportToExcel, exporting } = useExcelExport();
const tab = ref('sozlesmeler');

async function downloadContract(kind) {
  if (!editingId.value) return toast.info('Belge oluşturmak için önce sözleşmeyi kaydedin.');
  try {
    const [{ data: check }, response] = await Promise.all([
      getContractDataCheck(editingId.value, kind),
      downloadGeneratedContract(editingId.value, kind),
    ]);
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url; link.download = `sozlesme-${editingId.value}-${kind.toLowerCase()}.docx`;
    link.click(); URL.revokeObjectURL(url);
    if (check.eksik_alanlar?.length) {
      toast.warning(`Belge oluşturuldu. Elle tamamlanacak alanlar: ${check.eksik_alanlar.join(', ')}`);
    } else toast.success('Doldurulmuş Word belgesi indirildi.');
  } catch (e) { toast.error(e?.response?.data?.detail || 'Word belgesi oluşturulamadı.'); }
}

const sozlesmeler = ref([]);
const faturalar = ref([]);
const talepler = ref([]);
const odemeler = ref([]);
const odemeOzeti = computed(() => ({
  gecerli: odemeler.value.filter(o => !o.geri_alinma_tarihi).length,
  tutar: odemeler.value.filter(o => !o.geri_alinma_tarihi).reduce((sum, o) => sum + Number(o.tutar || 0), 0),
  geriAlinan: odemeler.value.filter(o => o.geri_alinma_tarihi).length,
}));
const eczaneler = ref([]);
const eczanelerLoading = ref(false);
const eczaneOptions = computed(() => eczaneler.value.map((p) => ({
  id: p.id,
  label: p.name,
  sub: [p.ilAdi, p.ilceAdi].filter(Boolean).join(' / '),
})));
// İptal edilen sözleşmeler varsayılan gizli; tik ile görünür (salt-okunur).
const showIptal = ref(false);
const gorunenSozlesmeler = computed(() =>
  showIptal.value
    ? sozlesmeler.value
    : sozlesmeler.value.filter((s) => s.durum !== 'IPTAL'));

// Son 3 ay başlangıcı / bu ay bitişi
function lastThreeMonthsStart() {
  const d = new Date();
  d.setMonth(d.getMonth() - 2);
  d.setDate(1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}
function thisMonthEnd() {
  const d = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const faturaFilters = reactive({ eczane: null, tarih_baslangic: lastThreeMonthsStart(), tarih_bitis: thisMonthEnd(), unpaid_only: false });
const odemeFilters = reactive({ eczane: null, tarih_baslangic: lastThreeMonthsStart(), tarih_bitis: thisMonthEnd() });
const loading = ref(false);

const TAKSITLER = [
  { value: 1, label: '1 Taksit (Peşin)' },
  { value: 4, label: '4 Taksit' },
  { value: 8, label: '8 Taksit' },
  { value: 12, label: '12 Taksit' },
];

const stats = computed(() => {
  const aktif  = sozlesmeler.value.filter((s) => s.durum === 'AKTIF').length;
  const iptal  = sozlesmeler.value.filter((s) => s.durum === 'IPTAL').length;
  const pasif  = sozlesmeler.value.length - aktif - iptal;
  const odenmeyenFatura = faturalar.value.filter((f) => f.durum === 'BEKLIYOR' || f.durum === 'GECIKTI').length;
  const toplamOdeme = odemeler.value.filter(o => !o.geri_alinma_tarihi).reduce((s, o) => s + Number(o.tutar || 0), 0);
  return {
    toplam: sozlesmeler.value.length,
    aktif,
    pasif,
    iptal,
    odenmeyenFatura,
    toplamOdeme,
    bekleyenTalepler: talepler.value.filter((t) => t.durum === 'BEKLIYOR').length,
  };
});

// ── Fiyat tanımları (parametre) ─────────────────────────────────────
const aktifFiyat = ref(null);
const fiyatlar = ref([]);
const fiyatOpen = ref(false);
const fiyatSaving = ref(false);
const billingRunning = ref(false);
const today = () => new Date().toISOString().slice(0, 10);
const DEFAULT_ACMA_KAPAMA_ORANI = 25;

function hesaplaAcmaKapamaBedeli(abonelikBedeli, oran) {
  const ab = Number(abonelikBedeli) || 0;
  const pct = Number(oran) || 0;
  return (ab * pct / 100).toFixed(2);
}

function hesaplaAcmaKapamaOrani(abonelikBedeli, acmaKapamaBedeli) {
  const ab = Number(abonelikBedeli) || 0;
  const ak = Number(acmaKapamaBedeli) || 0;
  if (ab <= 0 || ak <= 0) return DEFAULT_ACMA_KAPAMA_ORANI.toFixed(2);
  return (ak * 100 / ab).toFixed(2);
}

const fiyatForm = reactive({
  abonelik_kdv_orani: 0,
  cihaz_kdv_orani: 0,
  abonelik_bedeli: '3900.00',
  cihaz_kira_bedeli: '0.00',
  acma_kapama_orani: DEFAULT_ACMA_KAPAMA_ORANI.toFixed(2),
  acma_kapama_bedeli: '0.00',
  gecerlilik_baslangic: today(),
  aciklama: '',
});

watch(
  () => [fiyatForm.abonelik_bedeli, fiyatForm.acma_kapama_orani],
  () => {
    fiyatForm.acma_kapama_bedeli = hesaplaAcmaKapamaBedeli(
      fiyatForm.abonelik_bedeli,
      fiyatForm.acma_kapama_orani,
    );
  },
  { immediate: true },
);

async function loadAktifFiyat() {
  try {
    const { data } = await getAktifFiyat();
    aktifFiyat.value = data || null;
    return true;
  } catch { aktifFiyat.value = null; return false; }
}

async function openFiyat() {
  fiyatOpen.value = true;
  try {
    const { data } = await listFiyatlar();
    fiyatlar.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Fiyat tanımları yüklenemedi.');
  }
  Object.assign(fiyatForm, {
    abonelik_kdv_orani: aktifFiyat.value?.abonelik_kdv_orani ?? 0,
    cihaz_kdv_orani: aktifFiyat.value?.cihaz_kdv_orani ?? 0,
    abonelik_bedeli: aktifFiyat.value?.abonelik_bedeli || '3900.00',
    cihaz_kira_bedeli: aktifFiyat.value?.cihaz_kira_bedeli || '0.00',
    acma_kapama_orani: hesaplaAcmaKapamaOrani(
      aktifFiyat.value?.abonelik_bedeli || '3900.00',
      aktifFiyat.value?.acma_kapama_bedeli || '0.00',
    ),
    acma_kapama_bedeli: aktifFiyat.value?.acma_kapama_bedeli || '0.00',
    gecerlilik_baslangic: today(),
    aciklama: '',
  });
}

async function saveFiyat() {
  if (!fiyatForm.gecerlilik_baslangic) { toast.error('Geçerlilik tarihi girin.'); return; }
  if (
    Number(fiyatForm.abonelik_bedeli) < 0
    || Number(fiyatForm.cihaz_kira_bedeli) < 0
    || Number(fiyatForm.acma_kapama_orani) < 0
  ) {
    toast.error('Bedeller 0 veya üzeri olmalı.'); return;
  }
  fiyatSaving.value = true;
  try {
    await createFiyat({
      abonelik_kdv_orani: Number(fiyatForm.abonelik_kdv_orani),
      cihaz_kdv_orani: Number(fiyatForm.cihaz_kdv_orani),
      abonelik_bedeli: String(fiyatForm.abonelik_bedeli),
      cihaz_kira_bedeli: String(fiyatForm.cihaz_kira_bedeli),
      acma_kapama_bedeli: String(fiyatForm.acma_kapama_bedeli),
      gecerlilik_baslangic: fiyatForm.gecerlilik_baslangic,
      aciklama: fiyatForm.aciklama,
    });
    toast.success('Fiyat tanımı kaydedildi.');
    const { data } = await listFiyatlar();
    fiyatlar.value = Array.isArray(data) ? data : (data?.results ?? []);
    await loadAktifFiyat();
  } catch (e) {
    toast.error(e?.response?.data?.detail
      || Object.values(e?.response?.data || {})?.[0]?.[0]
      || 'Kaydedilemedi.');
  } finally { fiyatSaving.value = false; }
}

async function deleteFiyatItem(fp) {
  const ok = await confirm({
    title: 'Fiyat Tanımını Sil',
    message: `${fp.gecerlilik_baslangic} tarihli fiyat tanımı kalıcı olarak silinecek.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteFiyat(fp.id);
    toast.success('Fiyat tanımı silindi.');
    fiyatlar.value = fiyatlar.value.filter(x => x.id !== fp.id);
    await loadAktifFiyat();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Silinemedi.');
  }
}

async function runFaturalandir() {
  billingRunning.value = true;
  try {
    const { data } = await faturalandir();
    const yeni = data?.toplam_yeni ?? 0;
    toast.success(yeni > 0
      ? `${yeni} yeni fatura oluşturuldu.`
      : 'Bu dönem için oluşturulacak yeni fatura yok.');
    await Promise.all([loadSozlesmeler(), faturalar.value.length ? loadFaturalar() : Promise.resolve()]);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Faturalandırma başarısız.');
  } finally { billingRunning.value = false; }
}

// ── Sözleşme formu ──────────────────────────────────────────────────────────
const formOpen = ref(false);
const editingId = ref(null);
const saving = ref(false);
const islakImzaDosya = ref(null);      // seçilen dosya (File obj)
const ek2IslakImzaDosya = ref(null);
const islakImzaYukleniyor = ref(false);
const emptySozlesme = () => ({
  eczane: null,
  tur: 'STANDART',
  sozlesme_tipi_ay: 24,
  demo_gun: 30,
  baslangic_tarihi: '',
  oteleme_ay: 0,
  aylik_kullanim_bedeli: aktifFiyat.value?.abonelik_bedeli ?? '3900.00',
  cihaz_durumu: 'TAHSIS',
  cihaz_kira_bedeli: '',
  pesin_fiyat: '',
  vade_farki_orani: '0.00',
  taksit_sayisi: 1,
  cihaz_baslangic_tarihi: '',
  durum: 'AKTIF',
  notlar: '',
  kdv_orani: aktifFiyat.value?.abonelik_kdv_orani ?? 0,
  cihaz_kdv_orani: aktifFiyat.value?.cihaz_kdv_orani ?? 0,
  tevkifat_orani: '',
  iptal_ceza_orani: aktifFiyat.value?.iptal_ceza_orani ?? '2.00',
  imza_tipi: 'ISLAK',
  sozlesme_surumu: '2026-EK1',
  gercek_imza_tarihi: '',
  islak_imza_url: '',
  ek2_islak_imza_url: '',
  cihaz_planlari: [],
});
const form = reactive(emptySozlesme());

// ── Cihaz planı formu ───────────────────────────────────────────────────────
const cihazOpen = ref(false);
const cihazSozlesme = ref(null);
const cihazSaving = ref(false);
const emptyCihaz = () => ({
  pesin_fiyat: '',
  vade_farki_orani: '0.00',
  taksit_sayisi: 1,
  baslangic_tarihi: '',
});
const cihazForm = reactive(emptyCihaz());

const vadeFarkiGerekli = computed(() => Number(cihazForm.taksit_sayisi) !== 1);
const vadeFarkiEksik = computed(() =>
  vadeFarkiGerekli.value && !(Number(cihazForm.vade_farki_orani) > 0));

const cihazToplam = computed(() => {
  const pesin = Number(cihazForm.pesin_fiyat) || 0;
  const vade = Number(cihazForm.vade_farki_orani) || 0;
  return pesin * (1 + vade / 100);
});
const cihazTaksitTutar = computed(() => {
  const n = Number(cihazForm.taksit_sayisi) || 1;
  return cihazToplam.value / n;
});

// ── Yükleme ─────────────────────────────────────────────────────────────────
async function loadSozlesmeler() {
  loading.value = true;
  try {
    const params = route.query.eczane ? { eczane: route.query.eczane } : {};
    const { data } = await listSozlesmeler(params);
    sozlesmeler.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Sözleşmeler yüklenemedi.');
  } finally { loading.value = false; }
}

async function loadFaturalar() {
  loading.value = true;
  try {
    const params = {};
    if (faturaFilters.eczane) params.eczane = faturaFilters.eczane;
    if (faturaFilters.tarih_baslangic) params.tarih_baslangic = faturaFilters.tarih_baslangic;
    if (faturaFilters.tarih_bitis) params.tarih_bitis = faturaFilters.tarih_bitis;
    if (faturaFilters.unpaid_only) params.unpaid_only = true;
    const { data } = await listFaturalar(params);
    faturalar.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Faturalar yüklenemedi.');
  } finally { loading.value = false; }
}

async function loadTalepler() {
  loading.value = true;
  try {
    const { data } = await listTalepler();
    talepler.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Talepler yüklenemedi.');
  } finally { loading.value = false; }
}

async function loadOdemeler() {
  loading.value = true;
  try {
    const params = {};
    if (odemeFilters.eczane) params.eczane = odemeFilters.eczane;
    if (odemeFilters.tarih_baslangic) params.tarih_baslangic = odemeFilters.tarih_baslangic;
    if (odemeFilters.tarih_bitis) params.tarih_bitis = odemeFilters.tarih_bitis;
    const { data } = await listOdemeler(params);
    odemeler.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Ödemeler yüklenemedi.');
  } finally { loading.value = false; }
}

function exportOdemeler() {
  if (!odemeler.value.length) { toast.info('Dışa aktarılacak ödeme yok.'); return; }
  const cols = [
    { label: 'Tarih', fn: (o) => fmtDate(o.odeme_tarihi) },
    { label: 'Eczane', key: 'eczane_ad' },
    { label: 'Fatura Tipi', key: 'fatura_tip' },
    { label: 'Dönem', key: 'fatura_donem' },
    { label: 'Tutar (TL)', fn: (o) => Number(o.tutar || 0) },
    { label: 'Yöntem', key: 'yontem_display' },
    { label: 'Açıklama', key: 'aciklama' },
    { label: 'Tahsilat Durumu', fn: o => o.geri_alinma_tarihi ? 'Geri alındı' : 'Geçerli' },
    { label: 'Geri Alma Nedeni', key: 'geri_alma_nedeni' },
  ];
  exportToExcel(odemeler.value, cols, `odemeler-${today()}.xlsx`, 'Ödemeler');
}

const kararOpen = ref(false);
const kararTarget = ref(null);
const kararSaving = ref(false);
const kararForm = reactive({
  onayla: true,
  red_nedeni: '',
  aciklama: '',
  ek_ay: 6,
  ek_gun: 15,
});
// YENI onayında tam sözleşme detayı (SozlesmeForm'a bağlanır).
const kararSozlesme = reactive(emptySozlesme());

function openKarar(t, onayla) {
  kararTarget.value = t;
  kararForm.onayla = onayla;
  kararForm.red_nedeni = t.red_nedeni || '';
  kararForm.aciklama = t.aciklama || '';
  kararForm.ek_ay = Number(t.ek_ay || 6);
  kararForm.ek_gun = Number(t.ek_gun || 15);

  // Onay + YENI ise sözleşme formunu talep ve aktif fiyatla doldur.
  if (onayla && t.talep_tipi === 'YENI') {
    Object.assign(kararSozlesme, emptySozlesme());
    kararSozlesme.tur = t.istenen_tur || 'STANDART';
    kararSozlesme.eczane = t.eczane;
    kararSozlesme.sozlesme_tipi_ay = Number(t.istenen_tip_ay || 24);
    kararSozlesme.demo_gun = Number(t.istenen_demo_gun || 30);
    kararSozlesme.baslangic_tarihi = '';
    kararSozlesme.cihaz_baslangic_tarihi = '';
    kararSozlesme.cihaz_planlari = [];
  }
  kararOpen.value = true;
}

function closeKarar() {
  kararOpen.value = false;
  kararTarget.value = null;
}

async function karar(t, onayla) {
  openKarar(t, onayla);
}

async function saveKarar() {
  if (!kararTarget.value) return;
  const tip = kararTarget.value.talep_tipi;
  const detail = { aciklama: kararForm.aciklama };

  if (kararForm.onayla && tip === 'YENI') {
    const f = kararSozlesme;
    if (!f.baslangic_tarihi) { toast.error('Başlangıç tarihi girin.'); return; }
    Object.assign(detail, {
      istenen_tur: f.tur,
      istenen_tip_ay: Number(f.sozlesme_tipi_ay || 0),
      istenen_demo_gun: Number(f.demo_gun || 0),
      baslangic_tarihi: f.baslangic_tarihi,
      oteleme_ay: Number(f.oteleme_ay || 0),
      aylik_kullanim_bedeli: String(f.aylik_kullanim_bedeli || '0'),
      cihaz_durumu: f.cihaz_durumu,
      cihaz_kira_bedeli: String(f.cihaz_kira_bedeli || '0.00'),
      notlar: f.notlar || '',
      kdv_orani: Number(f.kdv_orani || 0),
      tevkifat_orani: f.tevkifat_orani || '',
      iptal_ceza_orani: String(f.iptal_ceza_orani || '0.00'),
      cihaz_planlari: f.cihaz_planlari || [],
    });
  } else if (kararForm.onayla && tip === 'UZATMA') {
    detail.ek_ay = Number(kararForm.ek_ay || 0);
    detail.ek_gun = Number(kararForm.ek_gun || 0);
  }

  kararSaving.value = true;
  try {
    await kararVerTalep(kararTarget.value.id, kararForm.onayla, kararForm.red_nedeni, detail);
    toast.success(kararForm.onayla ? 'Talep onaylandı.' : 'Talep reddedildi.');
    kararOpen.value = false;
    kararTarget.value = null;
    await Promise.all([loadTalepler(), loadSozlesmeler()]);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'İşlem başarısız.');
  } finally { kararSaving.value = false; }
}

async function loadEczaneler() {
  eczanelerLoading.value = true;
  try {
    eczaneler.value = await getPharmacies();
  } catch {
    toast.error('Eczaneler yüklenemedi. Lütfen tekrar deneyin.');
  } finally { eczanelerLoading.value = false; }
}

onMounted(async () => {
  await Promise.all([loadSozlesmeler(), loadAktifFiyat(), loadFaturalar(), loadOdemeler(), loadEczaneler()]);
});

function switchTab(t) {
  tab.value = t;
  if (t === 'faturalar' && !faturalar.value.length) loadFaturalar();
  if (t === 'talepler' && !talepler.value.length) loadTalepler();
  if (t === 'odemeler' && !odemeler.value.length) loadOdemeler();
}

// ── Sözleşme CRUD ───────────────────────────────────────────────────────────
const createLoading = ref(false);
async function openCreate() {
  if (createLoading.value) return;
  createLoading.value = true;
  const fiyatYuklendi = await loadAktifFiyat();
  if (!fiyatYuklendi) toast.error('Aktif fiyat yüklenemedi. Sözleşme tutarlarını kontrol edin.');
  editingId.value = null;
  Object.assign(form, emptySozlesme());
  formOpen.value = true;
  if (!eczaneler.value.length && !eczanelerLoading.value) loadEczaneler();
  createLoading.value = false;
}

function openEdit(s) {
  editingId.value = s.id;
  Object.assign(form, {
    eczane: s.eczane,
    tur: s.tur,
    sozlesme_tipi_ay: s.sozlesme_tipi_ay ?? 24,
    demo_gun: s.demo_gun ?? 30,
    baslangic_tarihi: s.baslangic_tarihi,
    oteleme_ay: s.oteleme_ay,
    aylik_kullanim_bedeli: s.aylik_kullanim_bedeli,
    cihaz_durumu: s.cihaz_durumu || 'TAHSIS',
    cihaz_kira_bedeli: s.cihaz_kira_bedeli || '0.00',
    pesin_fiyat: s.cihaz_plani?.pesin_fiyat || '',
    vade_farki_orani: s.cihaz_plani?.vade_farki_orani || '0.00',
    taksit_sayisi: s.cihaz_plani?.taksit_sayisi || 1,
    cihaz_baslangic_tarihi: s.cihaz_planlari?.[0]?.baslangic_tarihi || s.baslangic_tarihi,
    durum: s.durum,
    notlar: s.notlar || '',
    kdv_orani: s.kdv_orani || 0,
    tevkifat_orani: s.tevkifat_orani || '',
    iptal_ceza_orani: s.iptal_ceza_orani || '0.00',
    imza_tipi: s.imza_tipi || 'ISLAK',
    sozlesme_surumu: s.sozlesme_surumu || 'LEGACY',
    gercek_imza_tarihi: s.gercek_imza_tarihi || '',
    islak_imza_url: s.islak_imza_url || '',
    ek2_islak_imza_url: s.ek2_islak_imza_url || '',
    cihaz_planlari: (s.cihaz_planlari || []).map(p => ({
      id: p.id,
      cihazlar: p.cihazlar || [],
      tip: p.tip || 'SATILIK',
      adet: p.adet || 1,
      cihaz_bilgisi: p.cihaz_bilgisi || '',
      pesin_fiyat: p.pesin_fiyat || '',
      vade_farki_orani: p.vade_farki_orani || '0.00',
      taksit_sayisi: p.taksit_sayisi || 1,
      aylik_kira_bedeli: p.aylik_kira_bedeli || '',
      tahsis_bedeli: p.tahsis_bedeli || '',
      donanim_degeri: p.donanim_degeri || '',
      cihaz_kdv_orani: p.cihaz_kdv_orani || 0,
      tevkifat_orani: p.tevkifat_orani || '',
      oteleme_ay: p.oteleme_ay ?? 0,
      baslangic_tarihi: p.baslangic_tarihi || s.baslangic_tarihi,
    })),
  });
  formOpen.value = true;
}

async function saveSozlesme() {
  if (!form.eczane) { toast.error('Eczane seçin.'); return; }
  if (!form.baslangic_tarihi) { toast.error('Başlangıç tarihi girin.'); return; }
  saving.value = true;
  try {
    const payload = {
      eczane: form.eczane,
      tur: form.tur,
      sozlesme_tipi_ay: form.sozlesme_tipi_ay,
      demo_gun: form.demo_gun,
      baslangic_tarihi: form.baslangic_tarihi,
      oteleme_ay: form.oteleme_ay,
      aylik_kullanim_bedeli: form.aylik_kullanim_bedeli,
      cihaz_durumu: form.sozlesme_surumu === 'LEGACY' ? form.cihaz_durumu : (form.cihaz_planlari?.some((p) => p.tip === 'SATILIK') ? 'SATILIK' : 'TAHSIS'),
      cihaz_kira_bedeli: form.sozlesme_surumu === 'LEGACY' ? (form.cihaz_kira_bedeli || '0.00') : '0.00',
      notlar: form.notlar,
      kdv_orani: Number(form.kdv_orani || 0),
      tevkifat_orani: form.tevkifat_orani || '',
      iptal_ceza_orani: String(form.iptal_ceza_orani || '0.00'),
      imza_tipi: form.imza_tipi || 'ISLAK',
      gercek_imza_tarihi: form.gercek_imza_tarihi || null,
      cihaz_planlari: form.cihaz_planlari || [],
    };

    let saved;
    if (editingId.value) {
      saved = await updateSozlesme(editingId.value, payload);
    } else {
      // Atomik: sözleşme + cihaz planları tek istekte (ya hep ya hiç).
      saved = await createSozlesme({ ...payload, cihaz_planlari: form.cihaz_planlari || [] });
    }

    const targetId = editingId.value ?? saved?.data?.id;
    // Islak imza belgesi seçilmişse yükle
    if (targetId && form.imza_tipi === 'ISLAK' && islakImzaDosya.value) {
      islakImzaYukleniyor.value = true;
      try {
        const { data } = await uploadIslakImza(targetId, islakImzaDosya.value, 'SOZLESME_EK1');
        form.islak_imza_url = data.object_key;
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Belge yüklenemedi.');
      } finally {
        islakImzaDosya.value = null;
        islakImzaYukleniyor.value = false;
      }
    }
    if (targetId && form.imza_tipi === 'ISLAK' && ek2IslakImzaDosya.value) {
      islakImzaYukleniyor.value = true;
      try {
        const { data } = await uploadIslakImza(targetId, ek2IslakImzaDosya.value, 'EK2');
        form.ek2_islak_imza_url = data.object_key;
      } catch (e) { toast.error(e?.response?.data?.detail || 'Ek-2 yüklenemedi.'); }
      finally { ek2IslakImzaDosya.value = null; islakImzaYukleniyor.value = false; }
    }
    toast.success(editingId.value ? 'Sözleşme güncellendi.' : 'Sözleşme oluşturuldu.');
    closeForm();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Kaydedilemedi.');
  } finally { saving.value = false; }
}

// Modal her kapanışında (kaydet / iptal / X / backdrop) liste otomatik yenilenir.
function closeForm() {
  formOpen.value = false;
  editingId.value = null;
  loadSozlesmeler();
}

const matbuAdminOpen = ref(false);
const matbuAdminSozlesme = ref(null);
function openMatbuAdmin(sozlesme) {
  matbuAdminSozlesme.value = sozlesme;
  matbuAdminOpen.value = true;
}
function closeMatbuAdmin() {
  matbuAdminOpen.value = false;
  matbuAdminSozlesme.value = null;
}

// ── Cihaz planı ─────────────────────────────────────────────────────────────
function openCihaz(s) {
  cihazSozlesme.value = s;
  const p = s.cihaz_plani;
  if (p) {
    Object.assign(cihazForm, {
      pesin_fiyat: p.pesin_fiyat,
      vade_farki_orani: p.vade_farki_orani,
      taksit_sayisi: p.taksit_sayisi,
      baslangic_tarihi: p.baslangic_tarihi,
    });
  } else {
    Object.assign(cihazForm, emptyCihaz());
    cihazForm.baslangic_tarihi = s.baslangic_tarihi;
  }
  cihazOpen.value = true;
}

async function saveCihaz() {
  if (!cihazForm.pesin_fiyat) { toast.error('Peşin fiyat girin.'); return; }
  if (!cihazForm.baslangic_tarihi) { toast.error('Başlangıç tarihi girin.'); return; }
  cihazSaving.value = true;
  try {
    await setCihazPlani(cihazSozlesme.value.id, { ...cihazForm });
    toast.success('Cihaz ödeme planı kaydedildi.');
    cihazOpen.value = false;
    await loadSozlesmeler();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Plan kaydedilemedi.');
  } finally { cihazSaving.value = false; }
}

// ── Fatura tahsilat ─────────────────────────────────────────────────────────
const odemeModalOpen = ref(false);
const odemeSaving = ref(false);
const odemeHedef = ref(null);
const odemeAciklama = ref('');

function openOdemeModal(f) {
  odemeHedef.value = f;
  odemeAciklama.value = `${f.donem} dönemi manuel tahsilat`;
  odemeModalOpen.value = true;
}

function closeOdemeModal() {
  odemeModalOpen.value = false;
  odemeHedef.value = null;
  odemeAciklama.value = '';
}

async function savePaid() {
  if (!odemeHedef.value) return;
  if (!odemeAciklama.value.trim()) {
    toast.error('Manuel ödeme için açıklama zorunludur.');
    return;
  }
  odemeSaving.value = true;
  try {
    await odeFaturaAdmin(odemeHedef.value.id, 'MANUEL', odemeAciklama.value.trim());
    toast.success('Fatura ödendi olarak işaretlendi.');
    closeOdemeModal();
    await loadFaturalar();
  } catch (e) {
    toast.error(
      e?.response?.data?.aciklama?.[0]
      || e?.response?.data?.detail
      || 'İşaretlenemedi.'
    );
  } finally {
    odemeSaving.value = false;
  }
}

// ── Admin fatura görüntüleme ───────────────────────────────────────────────
const faturaModalOpen = ref(false);
const faturaModalLoading = ref(false);
const faturaHedef = ref(null);
const faturaIslem = ref(null);
async function faturaIslemSaved(data) {
  faturaIslem.value = null;
  if (faturaHedef.value?.id === data.id) faturaHedef.value = data;
  toast.success('Fatura işlemi kaydedildi.');
  await Promise.all([loadFaturalar(), loadOdemeler()]);
}

async function openFaturaModal(f) {
  faturaModalOpen.value = true;
  faturaModalLoading.value = true;
  faturaHedef.value = null;
  try {
    const { data } = await getFaturaAdmin(f.id);
    faturaHedef.value = data;
  } catch (e) {
    faturaHedef.value = f;
    toast.error(e?.response?.data?.detail || 'Fatura detayı yüklenemedi.');
  } finally {
    faturaModalLoading.value = false;
  }
}

function kapatFaturaModal() {
  faturaModalOpen.value = false;
  faturaHedef.value = null;
}

const faturaKalemler = computed(() => {
  if (!faturaHedef.value) return [];
  if (Array.isArray(faturaHedef.value.kalemler) && faturaHedef.value.kalemler.length) {
    return faturaHedef.value.kalemler;
  }
  return [{
    id: 'tek-kalem',
    tip_display: faturaHedef.value.tip_display,
    aciklama: faturaHedef.value.aciklama || 'Fatura kalemi',
    tutar: faturaHedef.value.tutar,
  }];
});

function fmtTL(v) {
  return Number(v || 0).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' });
}
const PILL = {
  AKTIF: 'eisa-pill-success', ODENDI: 'eisa-pill-success', ONAYLANDI: 'eisa-pill-success',
  BEKLIYOR: 'eisa-pill-warning', GECIKTI: 'eisa-pill-danger', REDDEDILDI: 'eisa-pill-danger',
  IPTAL: 'eisa-pill-muted',
};
function durumPill(s) {
  return {
    IPTAL: 'eisa-pill-muted', SURESI_DOLDU: 'eisa-pill-danger', AKTIF: 'eisa-pill-success',
  }[s?.etkin_durum] || 'eisa-pill-muted';
}
function durumLabel(s) {
  return {
    IPTAL: 'İptal', SURESI_DOLDU: 'Süresi Doldu', AKTIF: 'Aktif',
  }[s?.etkin_durum] || s?.durum_display;
}
function turPill(tur) {
  return tur === 'DEMO' ? 'eisa-pill-warning' : 'eisa-pill-info';
}
function kalanPill(s) {
  const k = s?.kalan_gun;
  if (k == null) return 'eisa-pill-muted';
  if (k < 0) return 'eisa-pill-danger';
  if (k <= 30) return 'eisa-pill-warning';
  return 'eisa-pill-success';
}
function kalanLabel(s) {
  const k = s?.kalan_gun;
  if (k == null) return '—';
  return k < 0 ? `${Math.abs(k)} gün geçti` : `${k} gün`;
}
function cihazPlanLabel(s) {
  const p = s?.cihaz_plani || (Array.isArray(s?.cihaz_planlari) ? s.cihaz_planlari[0] : null);
  if (!p) return null;
  const odeme = p.tip === 'SATILIK' && p.taksit_sayisi === 1 ? 'Peşin' : `${p.taksit_sayisi}x`;
  const tutar = p.cihaz_kdv_orani > 0
    ? (p.tip === 'SATILIK' && p.taksit_sayisi === 1 ? p.kdv_dahil_toplam : p.kdv_dahil_taksit)
    : (p.tip === 'SATILIK' && p.taksit_sayisi === 1 ? p.toplam_tutar : p.taksit_tutari);
  return { odeme, tutar: fmtTL(tutar), adet: p.adet ?? 1 };
}

// ── Uzatma ──────────────────────────────────────────────────────────────────
const uzatOpen = ref(false);
const uzatSaving = ref(false);
const uzatHedef = ref(null);
const uzatForm = reactive({ ek_ay: 6, ek_gun: 15, neden: '' });
const uzatDemo = computed(() => uzatHedef.value?.tur === 'DEMO');

function openUzat(s) {
  uzatHedef.value = s;
  Object.assign(uzatForm, { ek_ay: 6, ek_gun: 15, neden: '' });
  uzatOpen.value = true;
}
async function saveUzat() {
  uzatSaving.value = true;
  try {
    const payload = uzatDemo.value
      ? { ek_gun: uzatForm.ek_gun, neden: uzatForm.neden }
      : { ek_ay: uzatForm.ek_ay, neden: uzatForm.neden };
    await uzatSozlesme(uzatHedef.value.id, payload);
    toast.success('Sözleşme uzatıldı.');
    uzatOpen.value = false;
    await loadSozlesmeler();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Uzatılamadı.');
  } finally { uzatSaving.value = false; }
}

// ── Sözleşme iptal ─────────────────────────────────────────────────────────
const iptalOpen = ref(false);
const iptalSaving = ref(false);
const iptalHedef = ref(null);
const iptalForm = reactive({ neden: '' });

function openIptal(s) {
  iptalHedef.value = s;
  iptalForm.neden = '';
  iptalOpen.value = true;
}

function closeIptal() {
  iptalOpen.value = false;
  iptalHedef.value = null;
  iptalForm.neden = '';
}

async function saveIptal() {
  if (!iptalHedef.value) return;
  iptalSaving.value = true;
  try {
    await iptalSozlesme(iptalHedef.value.id, {
      neden: iptalForm.neden.trim() || 'İptal edildi',
    });
    toast.success('Sözleşme iptal edildi.');
    const hedefId = iptalHedef.value.id;
    closeIptal();
    await loadSozlesmeler();
    if (gecmisOpen.value && gecmisHedef.value?.id === hedefId) {
      const guncel = sozlesmeler.value.find((x) => x.id === hedefId) || { id: hedefId };
      await openGecmis(guncel);
    }
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Sözleşme iptal edilemedi.');
  } finally { iptalSaving.value = false; }
}

// ── Geçmiş ──────────────────────────────────────────────────────────────────
const gecmisOpen = ref(false);
const gecmisLoading = ref(false);
const gecmisHedef = ref(null);
const gecmisUzatmalar = ref([]);
const gecmisSozlesmeler = ref([]);

async function openGecmis(s) {
  gecmisHedef.value = s;
  gecmisOpen.value = true;
  gecmisLoading.value = true;
  gecmisUzatmalar.value = [];
  gecmisSozlesmeler.value = [];
  try {
    const { data } = await getSozlesmeGecmis(s.id);
    gecmisUzatmalar.value = data.uzatmalar ?? [];
    gecmisSozlesmeler.value = data.sozlesmeler ?? [];
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Geçmiş yüklenemedi.');
  } finally { gecmisLoading.value = false; }
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}
</script>

<template>
  <div class="eisa-page ay-billing-page">
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">YÖNETİCİ / ABONELİK</p>
        <h1 class="eisa-page-title">Abonelik ve Ödeme</h1>
        <p class="eisa-page-subtitle">Sözleşme, cihaz ödeme planı ve fatura yönetimi.</p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-icon-btn ay-icon-action" title="Fiyat tanımlarını yönet" aria-label="Fiyat tanımlarını yönet" @click="openFiyat">
          <i class="fa-solid fa-tags" aria-hidden="true"></i>
        </button>
        <button class="eisa-icon-btn ay-icon-action" :disabled="billingRunning" :title="billingRunning ? 'Faturalar oluşturuluyor…' : 'Bu dönemin faturalarını oluştur'" :aria-label="billingRunning ? 'Faturalar oluşturuluyor' : 'Bu dönemin faturalarını oluştur'" @click="runFaturalandir">
          <i :class="billingRunning ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-file-invoice-dollar'" aria-hidden="true"></i>
        </button>
        <button v-if="tab === 'sozlesmeler'" class="eisa-btn eisa-btn-cta" :disabled="createLoading" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni Sözleşme
        </button>
      </div>
    </div>

    <section class="eisa-stats kpi-grid">
      <!-- Sözleşme grubu -->
      <div class="kpi-group">
        <p class="kpi-group-label"><i class="fa-solid fa-file-contract"></i> Sözleşmeler</p>
        <div class="kpi-group-cards">
          <div class="eisa-stat-card">
            <span class="eisa-stat-label">Aktif</span>
            <span class="eisa-stat-value kpi-aktif">{{ stats.aktif }}</span>
          </div>
          <div class="eisa-stat-card">
            <span class="eisa-stat-label">Pasif</span>
            <span class="eisa-stat-value">{{ stats.pasif }}</span>
          </div>
          <div class="eisa-stat-card">
            <span class="eisa-stat-label">Toplam</span>
            <span class="eisa-stat-value">{{ stats.toplam }}</span>
          </div>
        </div>
      </div>
      <!-- Bu ay grubu -->
      <div class="kpi-group">
        <p class="kpi-group-label"><i class="fa-solid fa-calendar-day"></i> Seçili Dönem</p>
        <div class="kpi-group-cards">
          <button class="eisa-stat-card eisa-stat-card--clickable" type="button"
            @click="switchTab('odemeler')">
            <span class="eisa-stat-label">Toplam Tahsilat</span>
            <span class="eisa-stat-value kpi-tahsilat">{{ fmtTL(stats.toplamOdeme) }}</span>
          </button>
          <button class="eisa-stat-card eisa-stat-card--clickable" type="button"
            :class="{ 'kpi-card--alert': stats.odenmeyenFatura > 0 }"
            @click="faturaFilters.unpaid_only = true; switchTab('faturalar')">
            <span class="eisa-stat-label">Ödenmeyen Fatura</span>
            <span class="eisa-stat-value" :class="stats.odenmeyenFatura > 0 ? 'kpi-alert' : ''">{{ stats.odenmeyenFatura }}</span>
          </button>
        </div>
      </div>
      <!-- Talepler -->
      <button
        v-if="stats.bekleyenTalepler > 0"
        class="eisa-stat-card eisa-stat-card--clickable kpi-card--warn"
        type="button"
        @click="switchTab('talepler')"
      >
        <span class="eisa-stat-label">Bekleyen Talep</span>
        <span class="eisa-stat-value kpi-warn">{{ stats.bekleyenTalepler }}</span>
      </button>
    </section>

    <nav class="ay-tab-bar">
      <button class="ay-tab" :class="{ 'ay-tab--active': tab === 'sozlesmeler' }" @click="switchTab('sozlesmeler')">
        <i class="fa-solid fa-file-contract"></i> Sözleşmeler
        <span class="ay-tab-count">{{ sozlesmeler.length }}</span>
      </button>
      <button class="ay-tab" :class="{ 'ay-tab--active': tab === 'faturalar' }" @click="switchTab('faturalar')">
        <i class="fa-solid fa-file-invoice-dollar"></i> Faturalar
      </button>
      <button class="ay-tab" :class="{ 'ay-tab--active': tab === 'talepler' }" @click="switchTab('talepler')">
        <i class="fa-solid fa-paper-plane"></i> Talepler
        <span v-if="stats.bekleyenTalepler > 0" class="ay-tab-badge">{{ stats.bekleyenTalepler }}</span>
      </button>
      <button class="ay-tab" :class="{ 'ay-tab--active': tab === 'odemeler' }" @click="switchTab('odemeler')">
        <i class="fa-solid fa-receipt"></i> Ödemeler
      </button>
    </nav>

    <!-- ── Sözleşmeler ─────────────────────────────────────────────── -->
    <section v-if="tab === 'sozlesmeler'" class="eisa-panel">
      <div class="ay-filter-bar">
        <label class="iptal-toggle" aria-label="İptaller dahil">
          <input type="checkbox" v-model="showIptal" />
          <span class="iptal-toggle-track"><span class="iptal-toggle-thumb"></span></span>
          <span class="iptal-toggle-text">İptaller dahil</span>
        </label>
        <span class="ay-filter-result">{{ gorunenSozlesmeler.length }} kayıt</span>
      </div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Eczane</th><th>Tür</th><th>Süre</th><th>Kalan</th><th>Öteleme</th>
              <th>Kullanım Bedeli</th><th>Başlangıç</th><th>Bitiş</th>
              <th>Cihaz Planı</th><th>Durum</th><th>Onay</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in gorunenSozlesmeler" :key="s.id">
              <td><strong>{{ s.eczane_ad }}</strong></td>
              <td><span class="eisa-pill" :class="turPill(s.tur)">{{ s.tur_display }}</span></td>
              <td>{{ s.tur === 'DEMO' ? `${s.toplam_gun} gün` : `${s.tip_display}${s.oteleme_ay ? ` (öteleme +${s.oteleme_ay} ay)` : ''}` }}</td>
              <td><span class="eisa-pill" :class="kalanPill(s)">{{ kalanLabel(s) }}</span></td>
              <td>{{ s.tur === 'DEMO' ? '—' : (s.oteleme_ay ? `${s.oteleme_ay} ay` : '—') }}</td>
              <td>{{ s.tur === 'DEMO' ? '—' : fmtTL(s.aylik_kullanim_bedeli) }}</td>
              <td class="cell-muted">{{ s.baslangic_tarihi }}</td>
              <td class="cell-muted">{{ s.bitis_tarihi }}</td>
              <td>
                <template v-if="cihazPlanLabel(s)">
                  <span class="eisa-pill eisa-pill-info">{{ cihazPlanLabel(s).odeme }}</span>
                  <span style="font-size:.8rem;margin-left:.25rem;">{{ cihazPlanLabel(s).tutar }}</span>
                </template>
                <span v-else class="cell-muted">—</span>
              </td>
              <td><span class="eisa-pill" :class="durumPill(s)">{{ durumLabel(s) }}</span></td>
              <td class="cell-muted" style="font-size:.75rem;">
                <span v-if="s.imza_tipi === 'ISLAK'" class="eisa-pill eisa-pill-info" title="Islak imzalı sözleşme; eczacıdan dijital onay istenmez"><i class="fa-solid fa-signature" aria-hidden="true"></i> Islak imzalı</span>
                <span v-else-if="s.eczaci_onay_tarihi" class="eisa-pill eisa-pill-success" title="Eczacı dijital olarak onayladı"><i class="fa-solid fa-check" aria-hidden="true"></i> Onaylandı</span>
                <span v-else class="eisa-pill eisa-pill-warning" title="Eczacının dijital onayı bekleniyor"><i class="fa-regular fa-clock" aria-hidden="true"></i> Onay bekliyor</span>
              </td>
              <td class="cell-actions"><div class="ay-row-actions">
                <button class="eisa-icon-btn ay-icon-action" title="Düzenle" aria-label="Düzenle" :disabled="s.durum === 'IPTAL'" @click="openEdit(s)"><i class="fa-solid fa-pen"></i></button>
                <button class="eisa-icon-btn ay-icon-action" title="Sözleşmeyi Görüntüle" aria-label="Sözleşmeyi Görüntüle" @click="openMatbuAdmin(s)"><i class="fa-solid fa-file-contract" aria-hidden="true"></i></button>
                <button class="eisa-icon-btn ay-icon-action" title="Uzat" aria-label="Uzat" :disabled="s.durum === 'IPTAL'" @click="openUzat(s)"><i class="fa-solid fa-calendar-plus"></i></button>
                <button v-if="s.durum !== 'IPTAL'" class="eisa-icon-btn ay-icon-action" title="İptal Et" aria-label="İptal Et" @click="openIptal(s)"><i class="fa-solid fa-ban"></i></button>
                <button class="eisa-icon-btn ay-icon-action" title="Geçmiş" aria-label="Geçmiş" @click="openGecmis(s)"><i class="fa-solid fa-clock-rotate-left"></i></button>
              </div></td>
            </tr>
            <tr v-if="!sozlesmeler.length && !loading">
              <td colspan="12" class="empty-row">Henüz sözleşme yok.</td>
            </tr>
            <tr v-else-if="!gorunenSozlesmeler.length && !loading">
              <td colspan="12" class="empty-row">Görüntülenecek aktif sözleşme yok. İptal edilenleri görmek için filtreyi açın.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Faturalar ───────────────────────────────────────────────── -->
    <section v-else-if="tab === 'faturalar'" class="eisa-panel">
      <div class="ay-section-head">
        <div class="ay-section-title"><span class="ay-section-icon"><i class="fa-solid fa-file-invoice-dollar" aria-hidden="true"></i></span><div><h2>Fatura Kayıtları <span class="ay-record-count">{{ faturalar.length }}</span></h2><p>Dönem faturaları ve tahsilat işlemleri</p></div></div>
      </div>
      <div class="ay-filter-bar">
        <div class="ay-filter-fields">
          <div class="ay-filter-field ay-filter-field--lookup">
            <label class="ay-filter-label">Eczane</label>
            <EczanePicker v-model="faturaFilters.eczane" placeholder="Eczane ara…" />
          </div>
          <div class="ay-filter-field">
            <label class="ay-filter-label">Başlangıç</label>
            <input type="date" v-model="faturaFilters.tarih_baslangic" class="ay-filter-input" />
          </div>
          <div class="ay-filter-field">
            <label class="ay-filter-label">Bitiş</label>
            <input type="date" v-model="faturaFilters.tarih_bitis" class="ay-filter-input" />
          </div>
          <label class="ay-chip-toggle" :class="{ 'ay-chip-toggle--on': faturaFilters.unpaid_only }">
            <input type="checkbox" v-model="faturaFilters.unpaid_only" />
            <i class="fa-solid fa-circle-exclamation"></i> Ödenmemişler
          </label>
        </div>
        <div class="ay-filter-actions">
          <button class="eisa-icon-btn ay-icon-action ay-icon-action--primary" title="Fatura filtrelerini uygula" aria-label="Fatura filtrelerini uygula" @click="loadFaturalar">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
          </button>
          <button class="eisa-icon-btn ay-icon-action" title="Fatura filtrelerini temizle" aria-label="Fatura filtrelerini temizle" @click="faturaFilters.eczane=null;faturaFilters.tarih_baslangic='';faturaFilters.tarih_bitis='';faturaFilters.unpaid_only=false;loadFaturalar()">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Eczane</th><th>Tip</th><th>Dönem</th><th>Taksit</th>
              <th class="ay-money">Tutar</th><th>Vade</th><th>Durum</th><th class="ay-actions-heading">İşlemler</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in faturalar" :key="f.id">
              <td><strong>{{ f.eczane_ad }}</strong><span class="ay-cell-sub">Fatura #{{ f.id }}</span></td>
              <td>{{ f.tip_display }}</td>
              <td>{{ f.donem }}</td>
              <td>{{ f.taksit_no ?? '—' }}</td>
              <td class="ay-money"><strong>{{ fmtTL(f.tutar) }}</strong></td>
              <td class="cell-muted">{{ f.vade_tarihi }}</td>
              <td><span class="eisa-pill" :class="PILL[f.durum]">{{ f.durum_display }}</span></td>
              <td class="cell-actions"><div class="ay-row-actions">
                <button class="eisa-icon-btn ay-icon-action" title="Faturayı görüntüle" aria-label="Faturayı görüntüle" @click="openFaturaModal(f)">
                  <i class="fa-solid fa-file-lines" aria-hidden="true"></i>
                </button>
                <button v-if="f.durum === 'BEKLIYOR' || f.durum === 'GECIKTI'"
                        class="eisa-icon-btn ay-icon-action ay-icon-action--success" title="Manuel tahsilat kaydet" aria-label="Manuel tahsilat kaydet" @click="openOdemeModal(f)">
                  <i class="fa-solid fa-check" aria-hidden="true"></i>
                </button>
                <button class="eisa-icon-btn ay-icon-action ay-icon-action--info" title="Faturayı yeniden oluştur" aria-label="Faturayı yeniden oluştur" @click="faturaIslem = { fatura: f, action: 'yeniden-olustur' }">
                  <i class="fa-solid fa-rotate" aria-hidden="true"></i>
                </button>
                <button v-if="f.durum !== 'IPTAL'" class="eisa-icon-btn ay-icon-action ay-icon-action--danger" title="Faturayı iptal et" aria-label="Faturayı iptal et" @click="faturaIslem = { fatura: f, action: 'iptal' }">
                  <i class="fa-solid fa-ban" aria-hidden="true"></i>
                </button>
                <button v-if="f.aktif_tahsilat_var" class="eisa-icon-btn ay-icon-action ay-icon-action--warning" title="Tahsilat kaydını geri al" aria-label="Tahsilat kaydını geri al" @click="faturaIslem = { fatura: f, action: 'odemeyi-geri-al' }">
                  <i class="fa-solid fa-rotate-left" aria-hidden="true"></i>
                </button>
              </div></td>
            </tr>
            <tr v-if="!faturalar.length && !loading">
              <td colspan="8" class="empty-row">Fatura bulunamadı.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Talepler ────────────────────────────────────────────────── -->
    <section v-else-if="tab === 'talepler'" class="eisa-panel">
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr><th>Eczane</th><th>Tip</th><th>İstenen</th><th>Açıklama</th><th>Durum</th><th>Tarih</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in talepler" :key="t.id">
              <td><strong>{{ t.eczane_ad }}</strong></td>
              <td>{{ t.tip_display }}</td>
              <td class="cell-muted">
                <span v-if="t.talep_tipi === 'YENI'">{{ t.istenen_tur === 'DEMO' ? (t.istenen_demo_gun + ' gün demo') : (t.istenen_tip_ay + ' ay') }}</span>
                <span v-else-if="t.talep_tipi === 'UZATMA'">+{{ t.ek_gun ? (t.ek_gun + ' gün') : (t.ek_ay + ' ay') }}</span>
                <span v-else>—</span>
              </td>
              <td class="cell-muted">{{ t.aciklama || t.red_nedeni || '—' }}</td>
              <td><span class="eisa-pill" :class="PILL[t.durum]">{{ t.durum_display }}</span></td>
              <td class="cell-muted">{{ fmtDate(t.olusturulma_tarihi) }}</td>
              <td class="cell-actions"><div class="ay-row-actions">
                <template v-if="t.durum === 'BEKLIYOR'">
                  <button class="eisa-icon-btn ay-icon-action ay-icon-action--success" title="Talebi onayla" aria-label="Talebi onayla" @click="karar(t, true)">
                    <i class="fa-solid fa-check" aria-hidden="true"></i>
                  </button>
                  <button class="eisa-icon-btn ay-icon-action ay-icon-action--danger" title="Talebi reddet" aria-label="Talebi reddet" @click="karar(t, false)">
                    <i class="fa-solid fa-xmark" aria-hidden="true"></i>
                  </button>
                </template>
              </div></td>
            </tr>
            <tr v-if="!talepler.length && !loading">
              <td colspan="7" class="empty-row">Talep bulunamadı.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Ödemeler (tarihçe) ──────────────────────────────────────── -->
    <section v-else class="eisa-panel">
      <div class="ay-section-head">
        <div class="ay-section-title"><span class="ay-section-icon ay-section-icon--success"><i class="fa-solid fa-receipt" aria-hidden="true"></i></span><div><h2>Tahsilat Geçmişi <span class="ay-record-count">{{ odemeler.length }}</span></h2><p>Geçerli ve geri alınmış ödeme kayıtları</p></div></div>
      </div>
      <div class="ay-payment-summary">
        <div><span class="ay-summary-label">Geçerli tahsilat</span><strong class="ay-summary-amount">{{ fmtTL(odemeOzeti.tutar) }}</strong><span class="ay-cell-sub">Seçili filtrelerdeki toplam</span></div>
        <div><span class="ay-summary-label">Geçerli ödeme</span><strong>{{ odemeOzeti.gecerli }} <small>kayıt</small></strong></div>
        <div><span class="ay-summary-label">Geri alınan</span><strong>{{ odemeOzeti.geriAlinan }} <small>kayıt</small></strong></div>
      </div>
      <div class="ay-filter-bar">
        <div class="ay-filter-fields">
          <div class="ay-filter-field ay-filter-field--lookup">
            <label class="ay-filter-label">Eczane</label>
            <EczanePicker v-model="odemeFilters.eczane" placeholder="Eczane ara…" />
          </div>
          <div class="ay-filter-field">
            <label class="ay-filter-label">Başlangıç</label>
            <input type="date" v-model="odemeFilters.tarih_baslangic" class="ay-filter-input" />
          </div>
          <div class="ay-filter-field">
            <label class="ay-filter-label">Bitiş</label>
            <input type="date" v-model="odemeFilters.tarih_bitis" class="ay-filter-input" />
          </div>
        </div>
        <div class="ay-filter-actions">
          <button class="eisa-icon-btn ay-icon-action ay-icon-action--primary" title="Ödeme filtrelerini uygula" aria-label="Ödeme filtrelerini uygula" @click="loadOdemeler">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
          </button>
          <button class="eisa-icon-btn ay-icon-action" title="Ödeme filtrelerini temizle" aria-label="Ödeme filtrelerini temizle" @click="odemeFilters.eczane=null;odemeFilters.tarih_baslangic='';odemeFilters.tarih_bitis='';loadOdemeler()">
            <i class="fa-solid fa-xmark"></i>
          </button>
          <button class="eisa-icon-btn ay-icon-action ay-icon-action--success" title="Ödemeleri Excel'e aktar" aria-label="Ödemeleri Excel'e aktar" :disabled="exporting || !odemeler.length" @click="exportOdemeler">
            <i class="fa-solid fa-file-excel" aria-hidden="true"></i>
          </button>
        </div>
      </div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr><th>İşlem / Tarih</th><th>Eczane</th><th>Fatura</th><th class="ay-money">Tutar</th><th>Yöntem</th><th>Durum</th><th class="ay-actions-heading">İşlemler</th></tr>
          </thead>
          <tbody>
            <tr v-for="o in odemeler" :key="o.id">
              <td><strong class="ay-payment-ref">#{{ o.id }}</strong><span class="ay-cell-sub ay-no-wrap">{{ fmtDate(o.odeme_tarihi) }}</span></td>
              <td><strong>{{ o.eczane_ad }}</strong></td>
              <td><span>{{ o.fatura_tip }}</span><span class="ay-cell-sub">{{ o.fatura_donem }} · #{{ o.fatura }}</span></td>
              <td class="ay-money" :class="{ 'ay-money--reversed': o.geri_alinma_tarihi }"><strong>{{ fmtTL(o.tutar) }}</strong></td>
              <td><span class="ay-method"><i :class="o.yontem === 'KREDI_KARTI' ? 'fa-regular fa-credit-card' : o.yontem === 'EFT_HAVALE' ? 'fa-solid fa-building-columns' : 'fa-solid fa-money-bill-transfer'" aria-hidden="true"></i>{{ o.yontem_display }}</span></td>
              <td><span class="eisa-pill" :class="o.geri_alinma_tarihi ? 'eisa-pill-muted' : 'eisa-pill-success'"><i :class="o.geri_alinma_tarihi ? 'fa-solid fa-rotate-left' : 'fa-solid fa-check'" aria-hidden="true"></i>{{ o.geri_alinma_tarihi ? 'Geri alındı' : 'Geçerli' }}</span><span v-if="o.geri_alinma_tarihi" class="ay-cell-sub ay-reversal-reason">{{ o.geri_alma_nedeni }}</span></td>
              <td class="cell-actions"><div class="ay-row-actions"><button class="eisa-icon-btn ay-icon-action" title="İlgili faturayı görüntüle" aria-label="İlgili faturayı görüntüle" @click="openFaturaModal({ id: o.fatura })"><i class="fa-solid fa-file-invoice" aria-hidden="true"></i></button></div></td>
            </tr>
            <tr v-if="!odemeler.length && !loading">
              <td colspan="7" class="empty-row"><i class="fa-solid fa-receipt ay-empty-icon" aria-hidden="true"></i>Seçili filtrelerde ödeme kaydı bulunamadı.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Talep karar modal ─────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="kararOpen" class="eisa-modal-backdrop" @click.self="kararOpen = false">
        <div class="eisa-modal" :class="{ 'eisa-modal--big': kararForm.onayla && kararTarget?.talep_tipi === 'YENI' }" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">
                {{ kararForm.onayla
                  ? (kararTarget?.talep_tipi === 'YENI' ? 'Talebi Onayla — Sözleşme Oluştur'
                    : kararTarget?.talep_tipi === 'UZATMA' ? 'Uzatma Talebini Onayla' : 'İptal Talebini Onayla')
                  : 'Talebi Reddet' }}
              </h3>
              <p class="eisa-reset-info">{{ kararTarget?.eczane_ad }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="kararOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div v-if="kararTarget" class="eisa-form-grid">
              <div class="eisa-info-box eisa-form-row-full">
                <strong>{{ kararTarget.eczane_ad || kararTarget.eczane }}</strong>
                — {{ kararTarget.tip_display }}
                <div v-if="kararTarget.aciklama">Eczacı notu: {{ kararTarget.aciklama }}</div>
              </div>

              <!-- Onay + YENI: tam sözleşme formu -->
              <div v-if="kararForm.onayla && kararTarget.talep_tipi === 'YENI'" class="eisa-form-row-full">
                <SozlesmeForm :form="kararSozlesme" />
              </div>

              <!-- Onay + UZATMA -->
              <template v-else-if="kararForm.onayla && kararTarget.talep_tipi === 'UZATMA'">
                <label class="eisa-form-row">
                  <span class="eisa-field-label">Ek Ay</span>
                  <input type="number" min="0" v-model.number="kararForm.ek_ay" class="eisa-field" />
                </label>
                <label class="eisa-form-row">
                  <span class="eisa-field-label">Ek Gün</span>
                  <input type="number" min="0" v-model.number="kararForm.ek_gun" class="eisa-field" />
                </label>
              </template>

              <!-- Onay + IPTAL -->
              <p v-else-if="kararForm.onayla && kararTarget.talep_tipi === 'IPTAL'" class="eisa-reset-info eisa-form-row-full">
                <i class="fa-solid fa-triangle-exclamation"></i>
                Onaylandığında ilgili sözleşme iptal edilir ve hizmet erişimi kapanır.
              </p>

              <!-- Red -->
              <label v-if="!kararForm.onayla" class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Red Nedeni</span>
                <textarea v-model="kararForm.red_nedeni" rows="2" class="eisa-field"></textarea>
              </label>

              <label v-if="!(kararForm.onayla && kararTarget.talep_tipi === 'YENI')" class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Açıklama / Not</span>
                <textarea v-model="kararForm.aciklama" rows="2" class="eisa-field"></textarea>
              </label>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="kararSaving" @click="closeKarar">Vazgeç</button>
            <button class="eisa-btn" :class="kararForm.onayla ? 'eisa-btn-cta' : 'eisa-btn-danger'" :disabled="kararSaving" @click="saveKarar">
              <i v-if="kararSaving" class="fa-solid fa-circle-notch fa-spin"></i>
              {{ kararForm.onayla ? 'Onayla' : 'Reddet' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Admin fatura görüntüleme ─────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="faturaModalOpen" class="eisa-modal-backdrop" @click.self="kapatFaturaModal">
        <div class="eisa-modal eisa-modal--big" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Fatura Görüntüleme</h3>
              <p class="eisa-reset-info">Basit önizleme</p>
            </div>
            <button class="eisa-modal-close" @click="kapatFaturaModal"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div v-if="faturaModalLoading" class="cell-muted">Yükleniyor…</div>
            <div v-else-if="faturaHedef" class="invoice-preview">
              <div class="invoice-head">
                <div>
                  <p class="invoice-brand">E-ISA</p>
                  <h4>FATURA</h4>
                </div>
                <div class="invoice-meta-right">
                  <p><strong>No:</strong> #{{ faturaHedef.id }}</p>
                  <p><strong>Dönem:</strong> {{ faturaHedef.donem }}</p>
                </div>
              </div>

              <div class="invoice-meta-grid">
                <p><strong>Eczane:</strong> {{ faturaHedef.eczane_ad }}</p>
                <p><strong>Tip:</strong> {{ faturaHedef.tip_display }}</p>
                <p><strong>Vade:</strong> {{ faturaHedef.vade_tarihi || '—' }}</p>
                <p><strong>Durum:</strong> {{ faturaHedef.durum_display }}</p>
              </div>

              <table class="invoice-table">
                <thead>
                  <tr>
                    <th>Kalem</th>
                    <th>Açıklama</th>
                    <th style="text-align:right;">Tutar</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="k in faturaKalemler" :key="k.id">
                    <td>{{ k.tip_display || '—' }}</td>
                    <td>{{ k.aciklama || '—' }}</td>
                    <td style="text-align:right;">{{ fmtTL(k.tutar) }}</td>
                  </tr>
                </tbody>
              </table>

              <div class="invoice-total">
                <span>Toplam</span>
                <strong>{{ fmtTL(faturaHedef.tutar) }}</strong>
              </div>
              <p v-if="faturaHedef.iptal_nedeni"><strong>İptal nedeni:</strong> {{ faturaHedef.iptal_nedeni }}</p>
              <section v-if="faturaHedef.islemler?.length" aria-label="Fatura işlem geçmişi">
                <h4>İşlem Geçmişi</h4>
                <div v-for="islem in faturaHedef.islemler" :key="islem.id" class="eisa-reset-info">
                  <strong>{{ islem.islem_display }}</strong> · {{ fmtDate(islem.olusturulma_tarihi) }} · {{ islem.yapan }}
                  <p>{{ islem.neden }}</p>
                  <p>{{ fmtTL(islem.onceki.tutar) }} → {{ fmtTL(islem.sonraki.tutar) }} · {{ islem.onceki.durum }} → {{ islem.sonraki.durum }}</p>
                </div>
              </section>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="kapatFaturaModal">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>

    <FaturaIslemModal v-if="faturaIslem" :fatura="faturaIslem.fatura" :action="faturaIslem.action" @close="faturaIslem = null" @saved="faturaIslemSaved" />

    <!-- ── Fiyat tanımları modal ─────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="fiyatOpen" class="eisa-modal-backdrop" @click.self="fiyatOpen = false">
        <div class="eisa-modal eisa-modal--big" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Fiyat Tanımları</h3>
              <p class="eisa-reset-info">Aylık abonelik ve cihaz kira bedeli — geçerlilik tarihli, tarihçeli.</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="fiyatOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <label class="eisa-form-row">
                <span class="eisa-field-label">Aylık Abonelik Bedeli (TL)</span>
                <input type="number" step="0.01" min="0" v-model="fiyatForm.abonelik_bedeli" class="eisa-field" />
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Aylık Cihaz Kira Bedeli (TL)</span>
                <input type="number" step="0.01" min="0" v-model="fiyatForm.cihaz_kira_bedeli" class="eisa-field" />
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Abonelik KDV Oranı</span>
                <select v-model.number="fiyatForm.abonelik_kdv_orani" class="eisa-field"><option v-for="oran in [0, 1, 10, 20]" :key="oran" :value="oran">%{{ oran }}</option></select>
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Cihaz KDV Oranı</span>
                <select v-model.number="fiyatForm.cihaz_kdv_orani" class="eisa-field"><option v-for="oran in [0, 1, 10, 20]" :key="oran" :value="oran">%{{ oran }}</option></select>
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Açma/Kapama Oranı (Aboneliğe göre %)</span>
                <div class="eisa-input-group">
                  <input type="number" step="0.01" min="0" v-model="fiyatForm.acma_kapama_orani" class="eisa-field" />
                  <span class="eisa-input-suffix">%</span>
                </div>
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Açma/Kapama Bedeli (Hesaplanan TL)</span>
                <input type="text" :value="fmtTL(fiyatForm.acma_kapama_bedeli)" class="eisa-field" readonly />
              </label>
              <div class="eisa-reset-info eisa-form-row"><i class="fa-solid fa-scale-balanced"></i>
                Erken fesih cezası fiyat tanımından alınmaz; sözleşmedeki 2–12 aylık kural uygulanır.
              </div>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Geçerlilik Başlangıcı</span>
                <input type="date" v-model="fiyatForm.gecerlilik_baslangic" class="eisa-field" />
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Açıklama</span>
                <input type="text" v-model="fiyatForm.aciklama" maxlength="255" class="eisa-field" />
              </label>
              <div class="eisa-form-row-full">
                <button class="eisa-btn eisa-btn-cta" :disabled="fiyatSaving" @click="saveFiyat">
                  <i :class="fiyatSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
                  {{ fiyatSaving ? 'Kaydediliyor…' : 'Yeni Fiyat Tanımı Ekle' }}
                </button>
              </div>
            </div>

            <h4 class="eisa-field-label" style="margin-top:1rem;">Tarihçe</h4>
            <div class="eisa-table-wrap">
              <table class="eisa-table">
                <thead><tr><th>Geçerlilik</th><th>Abonelik</th><th>Abonelik KDV</th><th>Cihaz Kira</th><th>Cihaz KDV</th><th>Aç/Kapa</th><th>Açıklama</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="fp in fiyatlar" :key="fp.id">
                    <td class="cell-muted">{{ fp.gecerlilik_baslangic }}</td>
                    <td>{{ fmtTL(fp.abonelik_bedeli) }}</td>
                    <td>%{{ fp.abonelik_kdv_orani ?? 0 }}</td>
                    <td>{{ fmtTL(fp.cihaz_kira_bedeli) }}</td>
                    <td>%{{ fp.cihaz_kdv_orani ?? 0 }}</td>
                    <td>{{ fmtTL(fp.acma_kapama_bedeli) }}</td>
                    <td class="cell-muted">{{ fp.aciklama || '—' }}</td>
                    <td class="cell-actions"><div class="ay-row-actions">
                      <button class="eisa-icon-btn ay-icon-action ay-icon-action--danger" title="Sil" aria-label="Sil" @click="deleteFiyatItem(fp)">
                        <i class="fa-solid fa-trash"></i>
                      </button>
                    </div></td>
                  </tr>
                  <tr v-if="!fiyatlar.length"><td colspan="8" class="empty-row">Henüz fiyat tanımı yok.</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="fiyatOpen = false">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── İptal modal ───────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="iptalOpen" class="eisa-modal-backdrop" @click.self="closeIptal">
        <div class="eisa-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Sözleşmeyi İptal Et</h3>
              <p class="eisa-reset-info">{{ iptalHedef?.eczane_ad }} · {{ iptalHedef?.tur_display }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="closeIptal"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <div class="eisa-info-box eisa-form-row-full">
                Bu işlem sözleşmenin durumunu <strong>İptal</strong> yapar ve sözleşme tarihçesine iptal satırı ekler.
              </div>
              <div v-if="Number(iptalHedef?.iptal_ceza_tutari) > 0" class="eisa-error-banner eisa-form-row-full">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>Standart erken fesih hesabı: <strong>{{ fmtTL(iptalHedef.iptal_ceza_tutari) }}</strong>
                  (kalan ücretli süre, 2–12 aylık sınır). Fesih istisnası işlem gerekçesine göre ayrıca değerlendirilir.</span>
              </div>
              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">İptal Nedeni (opsiyonel)</span>
                <textarea
                  v-model="iptalForm.neden"
                  rows="3"
                  maxlength="255"
                  class="eisa-field"
                  placeholder="Örn: müşteri talebi, yanlış kayıt, sözleşme yenilenmedi"
                ></textarea>
              </label>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="iptalSaving" @click="closeIptal">Vazgeç</button>
            <button class="eisa-btn eisa-btn-danger" :disabled="iptalSaving" @click="saveIptal">
              <i :class="iptalSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-ban'"></i>
              {{ iptalSaving ? 'İptal Ediliyor…' : 'Sözleşmeyi İptal Et' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Sözleşme modal ──────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="formOpen" class="eisa-modal-backdrop" @click.self="closeForm">
        <div class="eisa-modal eisa-modal--big" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ editingId ? 'Sözleşme Düzenle' : 'Yeni Sözleşme' }}</h3>
            <button class="eisa-modal-close" title="Kapat" @click="closeForm"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Eczane</span>
                <EisaLookup
                  v-model="form.eczane"
                  :options="eczaneOptions"
                  :loading="eczanelerLoading"
                  placeholder="Eczane ara…"
                  :disabled="!!editingId"
                />
              </label>
            </div>
            <SozlesmeForm :form="form" />
            <!-- İmza tipi seçimi -->
            <div class="sf-section" style="margin-top:.5rem;">
              <div class="sf-section-header"><i class="fa-solid fa-signature"></i> İmza Tipi</div>
              <div class="eisa-form-grid sf-section-body">
                <div v-if="editingId" class="eisa-form-row eisa-form-row-full">
                  <span class="eisa-field-label">Otomatik Doldurulan Word Belgeleri</span>
                  <div style="display:flex;flex-wrap:wrap;gap:.5rem;">
                    <button type="button" class="eisa-btn eisa-btn-ghost eisa-btn--sm" @click="downloadContract('EK1')">
                      <i class="fa-solid fa-file-word"></i> Ana Sözleşme ve Ek-1'i İndir
                    </button>
                    <button type="button" class="eisa-btn eisa-btn-ghost eisa-btn--sm" @click="downloadContract('EK2')">
                      <i class="fa-solid fa-file-word"></i> Ek-2'yi İndir
                    </button>
                  </div>
                  <span class="cell-muted" style="font-size:.78rem;">Eksik seri no, teslim personeli ve teslim saati belgede açıkça işaretlenir; 4, 5 ve 7. bölümler elle doldurulur.</span>
                </div>
                <label class="eisa-form-row">
                  <span class="eisa-field-label">İmza Tipi</span>
                  <select v-model="form.imza_tipi" class="eisa-field">
                    <option value="DIJITAL" :disabled="form.sozlesme_surumu !== 'LEGACY'">Dijital İmza (entegrasyon bekleniyor)</option>
                    <option value="ISLAK">Islak İmza (taranıp yüklenir)</option>
                  </select>
                </label>
                <label class="eisa-form-row"><span class="eisa-field-label">Gerçek imza tarihi</span><input v-model="form.gercek_imza_tarihi" type="date" class="eisa-field" /></label>
                <label v-if="form.imza_tipi === 'ISLAK'" class="eisa-form-row eisa-form-row-full">
                  <span class="eisa-field-label">
                    Taranmış Belge
                    <span v-if="islakImzaYukleniyor" class="cell-muted">Yükleniyor…</span>
                  </span>
                  <div style="display:flex;flex-direction:column;gap:.4rem;">
                    <label class="eisa-btn eisa-btn-ghost eisa-btn--sm" style="cursor:pointer;width:fit-content;">
                      <i class="fa-solid fa-upload"></i>
                      {{ islakImzaDosya ? islakImzaDosya.name : 'Dosya Seç (PDF/JPG/PNG)' }}
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff"
                             style="display:none;"
                             @change="islakImzaDosya = $event.target.files[0]" />
                    </label>
                    <span v-if="form.islak_imza_url" class="cell-muted" style="font-size:.78rem;">
                      <i class="fa-solid fa-check" style="color:#16a34a;"></i>
                      Yüklendi:
                      <a :href="`/api/abonelik/sozlesmeler/${editingId}/islak-imza-indir/`"
                         target="_blank" style="color:#2563EB;">
                        {{ form.islak_imza_url.split('/').pop() }}
                      </a>
                    </span>
                    <span v-else-if="!islakImzaDosya" class="cell-muted" style="font-size:.78rem;">
                      Sözleşme kaydedildikten sonra belge RustFS'e yüklenir.
                    </span>
                  </div>
                </label>
                <label v-if="form.imza_tipi === 'ISLAK'" class="eisa-form-row eisa-form-row-full">
                  <span class="eisa-field-label">Ek-2 Teslim ve Zimmet Tutanağı</span>
                  <div style="display:flex;flex-direction:column;gap:.4rem;">
                    <label class="eisa-btn eisa-btn-ghost eisa-btn--sm" style="cursor:pointer;width:fit-content;">
                      <i class="fa-solid fa-upload"></i>
                      {{ ek2IslakImzaDosya ? ek2IslakImzaDosya.name : 'Ek-2 Dosyası Seç' }}
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff" style="display:none;"
                             @change="ek2IslakImzaDosya = $event.target.files[0]" />
                    </label>
                    <a v-if="form.ek2_islak_imza_url" :href="getIslakImzaUrl(editingId, 'EK2')"
                       target="_blank" class="cell-muted">Yüklenen Ek-2'yi görüntüle</a>
                  </div>
                </label>
                <p v-if="form.imza_tipi === 'ISLAK'" class="eisa-reset-info eisa-form-row-full">
                  <i class="fa-solid fa-circle-info"></i>
                  Ana sözleşme/Ek-1 ile Ek-2 ayrı saklanır. Dosyanın yüklenme zamanı sözleşme başlangıcını, faturayı veya gerçek imza tarihini değiştirmez.
                </p>
              </div>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="closeForm">İptal</button>
            <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="saveSozlesme">
              <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
              {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Admin ödeme modal (zorunlu açıklama) ─────────────────── -->
    <Teleport to="body">
      <div v-if="odemeModalOpen" class="eisa-modal-backdrop" @click.self="closeOdemeModal">
        <div class="eisa-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Fatura Tahsilat</h3>
              <p class="eisa-reset-info">{{ odemeHedef?.eczane_ad }} · {{ fmtTL(odemeHedef?.tutar) }}</p>
            </div>
            <button class="eisa-modal-close" @click="closeOdemeModal"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <div class="eisa-info-box eisa-form-row-full">
                <strong>Elden/Manuel ödeme kaydı.</strong> Ödeme yapıldığını gösteren referans, dekont no veya açıklama yazın.
              </div>
              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Açıklama / Referans <span class="cell-muted">(zorunlu)</span></span>
                <textarea v-model="odemeAciklama" rows="3" class="eisa-field" placeholder="Örn: Elden nakit, Akbank havale 12345, vb."></textarea>
              </label>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="odemeSaving" @click="closeOdemeModal">Vazgeç</button>
            <button class="eisa-btn eisa-btn-success" :disabled="odemeSaving || !odemeAciklama.trim()" @click="savePaid">
              <i :class="odemeSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-check'"></i>
              {{ odemeSaving ? 'Kaydediliyor…' : 'Ödendi Olarak İşaretle' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Admin matbu sözleşme görüntüle ──────────────────────── -->
    <Teleport to="body">
      <div v-if="matbuAdminOpen" class="eisa-modal-backdrop" @click.self="closeMatbuAdmin">
        <div class="eisa-modal eisa-modal--medium" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Sözleşme Belgesi</h3>
              <p class="eisa-reset-info">{{ matbuAdminSozlesme?.eczane_ad }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="closeMatbuAdmin"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <SozlesmeMatbu v-if="matbuAdminSozlesme" :sozlesme="matbuAdminSozlesme" />
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="closeMatbuAdmin">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Cihaz planı modal ───────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="cihazOpen" class="eisa-modal-backdrop" @click.self="cihazOpen = false">
        <div class="eisa-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Cihaz Ödeme Planı</h3>
              <p class="eisa-reset-info">{{ cihazSozlesme?.eczane_ad }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="cihazOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <label class="eisa-form-row">
                <span class="eisa-field-label">Peşin Fiyat (TL)</span>
                <input type="number" step="0.01" min="0" v-model="cihazForm.pesin_fiyat" class="eisa-field" />
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">Taksit Sayısı</span>
                <select v-model.number="cihazForm.taksit_sayisi" class="eisa-field">
                  <option v-for="t in TAKSITLER" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">
                  Vade Farkı (%)<template v-if="vadeFarkiGerekli"> *</template>
                </span>
                <input type="number" step="0.01" min="0" v-model="cihazForm.vade_farki_orani"
                       class="eisa-field" :disabled="!vadeFarkiGerekli" />
              </label>
              <label class="eisa-form-row">
                <span class="eisa-field-label">İlk Taksit Ayı</span>
                <input type="date" v-model="cihazForm.baslangic_tarihi" class="eisa-field" />
              </label>

              <div v-if="vadeFarkiEksik" class="eisa-error-banner eisa-form-row-full">
                <i class="fa-solid fa-triangle-exclamation"></i>
                1 aydan fazla taksitte vade farkı zorunludur (> %0).
              </div>

              <div class="eisa-stats eisa-form-row-full">
                <div class="eisa-stat-card">
                  <span class="eisa-stat-label">Toplam (vade farkı dahil)</span>
                  <span class="eisa-stat-value">{{ fmtTL(cihazToplam) }}</span>
                </div>
                <div class="eisa-stat-card">
                  <span class="eisa-stat-label">Aylık Taksit</span>
                  <span class="eisa-stat-value">{{ fmtTL(cihazTaksitTutar) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="cihazSaving" @click="cihazOpen = false">İptal</button>
            <button class="eisa-btn eisa-btn-cta" :disabled="cihazSaving || vadeFarkiEksik" @click="saveCihaz">
              <i :class="cihazSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
              {{ cihazSaving ? 'Kaydediliyor…' : 'Kaydet' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Uzatma modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="uzatOpen" class="eisa-modal-backdrop" @click.self="uzatOpen = false">
        <div class="eisa-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Sözleşme Uzat</h3>
              <p class="eisa-reset-info">{{ uzatHedef?.eczane_ad }} · {{ uzatHedef?.tur_display }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="uzatOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <label v-if="uzatDemo" class="eisa-form-row">
                <span class="eisa-field-label">Ek Gün</span>
                <input type="number" min="1" max="30" v-model.number="uzatForm.ek_gun" class="eisa-field" />
              </label>
              <label v-else class="eisa-form-row">
                <span class="eisa-field-label">Ek Ay</span>
                <input type="number" min="1" max="60" v-model.number="uzatForm.ek_ay" class="eisa-field" />
              </label>
              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Neden</span>
                <input type="text" v-model="uzatForm.neden" class="eisa-field" maxlength="255" />
              </label>
              <p v-if="uzatDemo" class="eisa-reset-info eisa-form-row-full">
                <i class="fa-solid fa-circle-info"></i>
                Demo toplamı 30 günü aşamaz (mevcut: {{ uzatHedef?.toplam_gun }} gün).
              </p>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="uzatSaving" @click="uzatOpen = false">İptal</button>
            <button class="eisa-btn eisa-btn-cta" :disabled="uzatSaving" @click="saveUzat">
              <i :class="uzatSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-calendar-plus'"></i>
              {{ uzatSaving ? 'Uzatılıyor…' : 'Uzat' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Geçmiş modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="gecmisOpen" class="eisa-modal-backdrop" @click.self="gecmisOpen = false">
        <div class="eisa-modal eisa-modal--big" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Sözleşme Geçmişi</h3>
              <p class="eisa-reset-info">{{ gecmisHedef?.eczane_ad }}</p>
            </div>
            <button class="eisa-modal-close" title="Kapat" @click="gecmisOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div v-if="gecmisLoading" class="empty-row">Yükleniyor…</div>
            <template v-else>
              <h4 class="eisa-field-label">Uzatmalar</h4>
              <div class="eisa-table-wrap">
                <table class="eisa-table">
                  <thead><tr><th>Ek Süre</th><th>Neden</th><th>Kullanıcı</th><th>Tarih</th></tr></thead>
                  <tbody>
                    <tr v-for="u in gecmisUzatmalar" :key="u.id">
                      <td>{{ u.is_iptal ? 'İptal' : (u.ek_gun ? `${u.ek_gun} gün` : `${u.ek_ay} ay`) }}</td>
                      <td class="cell-muted">{{ u.is_iptal ? (u.iptal_nedeni || u.neden || '—') : (u.neden || '—') }}</td>
                      <td class="cell-muted">{{ u.olusturan_adi || '—' }}</td>
                      <td class="cell-muted">{{ fmtDate(u.olusturulma_tarihi) }}</td>
                    </tr>
                    <tr v-if="!gecmisUzatmalar.length"><td colspan="4" class="empty-row">Uzatma kaydı yok.</td></tr>
                  </tbody>
                </table>
              </div>

              <h4 class="eisa-field-label" style="margin-top:1rem;">Eczane Sözleşmeleri</h4>
              <div class="eisa-table-wrap">
                <table class="eisa-table">
                  <thead><tr><th>Tür</th><th>Süre</th><th>Başlangıç</th><th>Bitiş</th><th>Durum</th></tr></thead>
                  <tbody>
                    <tr v-for="s in gecmisSozlesmeler" :key="s.id">
                      <td><span class="eisa-pill" :class="turPill(s.tur)">{{ s.tur_display }}</span></td>
                      <td>{{ s.tur === 'DEMO' ? `${s.toplam_gun} gün` : s.tip_display }}</td>
                      <td class="cell-muted">{{ s.baslangic_tarihi }}</td>
                      <td class="cell-muted">{{ s.bitis_tarihi }}</td>
                      <td><span class="eisa-pill" :class="durumPill(s)">{{ durumLabel(s) }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="gecmisOpen = false">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Fatura ve ödeme listeleri */
.ay-section-head { padding:1.25rem 1.4rem; border-bottom:1px solid var(--border-default); }
.ay-section-title { display:flex; align-items:center; gap:.85rem; }
.ay-section-title h2 { display:flex; align-items:center; gap:.6rem; margin:0; font-size:1rem; font-weight:700; color:var(--text-primary); }
.ay-section-title p { margin:.25rem 0 0; font-size:.78rem; color:var(--text-secondary); }
.ay-section-icon { display:grid; place-items:center; width:42px; height:42px; flex-shrink:0; border-radius:12px; background:var(--eisa-info-soft); color:var(--eisa-info); }
.ay-section-icon--success { background:#E8F6F3; color:var(--eisa-turquoise); }
.ay-record-count { padding:.15rem .5rem; border-radius:6px; background:var(--surface-muted); color:var(--text-secondary); font-size:.7rem; font-weight:600; font-variant-numeric:tabular-nums; }
.ay-payment-summary { display:grid; grid-template-columns:1.6fr 1fr 1fr; margin:1.25rem 1.4rem; border:1px solid var(--border-default); border-radius:14px; background:linear-gradient(110deg, #F0FAF7, #FFFFFF 65%); }
.ay-payment-summary > div { padding:1.1rem 1.25rem; display:flex; flex-direction:column; justify-content:center; gap:.35rem; min-width:0; }
.ay-payment-summary > div + div { border-left:1px solid var(--border-default); }
.ay-summary-label { font-size:.74rem; font-weight:600; color:var(--text-secondary); }
.ay-payment-summary strong { font-size:1.5rem; line-height:1.3; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
.ay-payment-summary .ay-summary-amount { color:var(--eisa-turquoise); }
.ay-payment-summary small { font-size:.75rem; color:var(--text-secondary); font-weight:500; }
.ay-cell-sub { display:block; margin-top:.3rem; font-size:.72rem; color:#6B7280; font-weight:400; line-height:1.5; }
.ay-no-wrap { white-space:nowrap; }
.ay-payment-ref { font-family:'DM Mono', monospace; font-size:.8rem; color:var(--text-secondary); }
.ay-billing-page .eisa-table th.ay-money, .ay-billing-page .eisa-table td.ay-money { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
.ay-money--reversed strong { color:#6B7280; text-decoration:line-through; text-decoration-color:#CBD5E1; }
.ay-method { display:inline-flex; align-items:center; gap:.5rem; white-space:nowrap; font-size:.78rem; color:var(--text-secondary); }
.ay-method i { color:#7B8798; width:1rem; text-align:center; }
.ay-reversal-reason { max-width:240px; overflow-wrap:anywhere; }
.ay-billing-page .eisa-table td { vertical-align:middle; }
.eisa-table td.cell-actions { display:table-cell; text-align:right; }
.ay-row-actions { display:flex; align-items:center; justify-content:flex-end; gap:.4rem; min-height:38px; white-space:nowrap; }
.ay-actions-heading { text-align:right !important; }
.ay-icon-action { width:36px; height:36px; border-radius:10px; box-shadow:0 1px 2px rgba(17,24,39,.03); }
.ay-icon-action i { width:1.1em; text-align:center; }
.ay-icon-action:hover:not(:disabled) { transform:translateY(-1px); }
.ay-icon-action:focus-visible, .ay-billing-page .eisa-icon-btn:focus-visible { outline:2px solid var(--border-focus); outline-offset:3px; }
.ay-icon-action:disabled { opacity:.4; cursor:not-allowed; }
.ay-icon-action--primary { background:var(--eisa-red); border-color:var(--eisa-red); color:#fff; }
.ay-icon-action--primary:hover:not(:disabled) { background:#8F1017; border-color:#8F1017; color:#fff; }
.ay-icon-action--success { color:#0F766E; border-color:#C4E8DD; background:#F0FAF7; }
.ay-icon-action--success:hover:not(:disabled) { background:#DCF4EA; color:#075E50; border-color:#8FD4BB; }
.ay-icon-action--info { color:var(--eisa-info); border-color:#DDDDF7; background:#F5F5FF; }
.ay-icon-action--info:hover:not(:disabled) { background:#E9E8FF; color:#3730A3; border-color:#BDB7F5; }
.ay-icon-action--danger { color:#B91C1C; border-color:#F4D1D5; background:#FFF5F5; }
.ay-icon-action--danger:hover:not(:disabled) { background:#FEE2E2; color:#991B1B; border-color:#FCA5A5; }
.ay-icon-action--warning { color:#A16207; border-color:#EFDEB7; background:#FFFBEB; }
.ay-icon-action--warning:hover:not(:disabled) { background:#FEF3C7; color:#854D0E; border-color:#FCD34D; }
.ay-empty-icon { display:block; font-size:1.75rem; color:#CBD5E1; margin-bottom:.75rem; }
.ay-billing-page .eisa-header-actions { align-items:center; }

/* ── KPI grid ──────────────────────────────────────────────────── */
.kpi-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-start;
}

.kpi-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.kpi-group-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted, #6B7280);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.kpi-group-cards {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.kpi-aktif   { color: #0F8F8A; }
.kpi-tahsilat { font-size: 1rem !important; color: #0F8F8A; }
.kpi-alert   { color: #B1121B; }
.kpi-warn    { color: #D97706; }

.kpi-card--alert {
  border-color: rgba(177, 18, 27, 0.25) !important;
  background: rgba(177, 18, 27, 0.04) !important;
}

.kpi-card--warn {
  border-color: rgba(217, 119, 6, 0.3) !important;
  background: rgba(254, 243, 199, 0.5) !important;
}

.invoice-preview {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
  background: #fff;
}

.invoice-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}

.invoice-brand {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: #6b7280;
}

.invoice-head h4 {
  margin: 0.1rem 0 0;
  font-size: 1rem;
  color: #111827;
}

.invoice-meta-right p,
.invoice-meta-grid p {
  margin: 0;
  font-size: 0.82rem;
  color: #374151;
}

.invoice-meta-right {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.invoice-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem 1rem;
  margin-bottom: 0.75rem;
}

.invoice-table {
  width: 100%;
  border-collapse: collapse;
}

.invoice-table th,
.invoice-table td {
  padding: 0.55rem 0.45rem;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.82rem;
  text-align: left;
}

.invoice-table th {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #6b7280;
}

.invoice-total {
  margin-top: 0.9rem;
  display: flex;
  justify-content: flex-end;
  align-items: baseline;
  gap: 0.75rem;
}

.invoice-total span {
  color: #6b7280;
  font-size: 0.82rem;
}

.invoice-total strong {
  font-size: 1rem;
  color: #111827;
}

/* ── Tab bar ─────────────────────────────────────────────────────── */
.ay-tab-bar {
  display: flex;
  gap: 0;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 1.25rem;
  width: fit-content;
}

.ay-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 1.1rem;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  position: relative;
  white-space: nowrap;
}

.ay-tab:hover:not(.ay-tab--active) {
  background: #e2e8f0;
  color: #334155;
}

.ay-tab--active {
  background: #fff;
  color: #1e40af;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.1);
}

.ay-tab-count {
  background: #e0e7ff;
  color: #3730a3;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  min-width: 1.4rem;
  text-align: center;
}

.ay-tab-badge {
  background: #ef4444;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  min-width: 1.4rem;
  text-align: center;
}

/* ── Filter bar ──────────────────────────────────────────────────── */
.ay-filter-bar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  margin-bottom: 1rem;
}

.ay-filter-fields {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.ay-filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.ay-filter-label {
  font-size: 0.73rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.ay-filter-select,
.ay-filter-input {
  height: 38px;
  padding: 0 0.75rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #111827;
  font-size: 0.875rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
  min-width: 0;
}

.ay-filter-select { min-width: 160px; }
.ay-filter-input  { width: 140px; }

/* EczanePicker (EisaLookup) margin sıfırlama + hizalama */
.ay-filter-field--lookup :deep(.eisa-lookup) { margin: 0; }
.ay-filter-field--lookup :deep(.lookup-trigger) { min-height: 38px; height: 38px; }

.ay-filter-field--lookup {
  min-width: 240px;
}

.ay-filter-select:focus,
.ay-filter-input:focus {
  border-color: #B1121B;
  box-shadow: 0 0 0 3px rgba(177, 18, 27, 0.12);
}

.ay-chip-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  height: 38px;
  padding: 0 0.85rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #6B7280;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  align-self: flex-end;
}

.ay-chip-toggle input { display: none; }

.ay-chip-toggle--on {
  background: rgba(177,18,27,0.07);
  border-color: #B1121B;
  color: #B1121B;
}

.ay-chip-toggle:hover {
  border-color: #B1121B;
}

.ay-filter-actions {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
  flex-shrink: 0;
}

.ay-filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  height: 38px;
  padding: 0 1rem;
  background: linear-gradient(135deg, #7F1D1D 0%, #B1121B 55%, #D72638 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(177, 18, 27, 0.28);
  transition: box-shadow 0.15s, transform 0.15s;
  white-space: nowrap;
}

.ay-filter-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(177,18,27,0.38); }

.ay-filter-reset {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 0.85rem;
}

.ay-filter-reset:hover {
  border-color: #B1121B;
  color: #B1121B;
  background: rgba(177,18,27,0.06);
}

.ay-filter-export {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  height: 38px;
  padding: 0 0.9rem;
  background: #fff;
  color: #0F8F8A;
  border: 1.5px solid #0F8F8A;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.ay-filter-export:hover:not(:disabled) {
  background: #0F8F8A;
  color: #fff;
}

.ay-filter-export:disabled {
  opacity: 0.45;
  cursor: default;
}

.ay-filter-result {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
  margin-left: auto;
  white-space: nowrap;
}

.iptal-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.45rem 0.8rem;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f8fafc;
  color: #374151;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.iptal-toggle:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.iptal-toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.iptal-toggle-track {
  position: relative;
  width: 2.5rem;
  height: 1.4rem;
  border-radius: 999px;
  background: #dfe5ef;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
  transition: background 0.2s ease;
}

.iptal-toggle-thumb {
  position: absolute;
  top: 0.18rem;
  left: 0.18rem;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
  transition: transform 0.2s ease;
}

.iptal-toggle input:checked + .iptal-toggle-track {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.iptal-toggle input:checked + .iptal-toggle-track .iptal-toggle-thumb {
  transform: translateX(1.05rem);
}

.iptal-toggle-text {
  line-height: 1;
}

@media (max-width: 768px) {
  .ay-section-head { padding:1rem; }
  .ay-payment-summary { margin:1rem; grid-template-columns:1fr 1fr; }
  .ay-payment-summary > div:first-child { grid-column:1 / -1; border-bottom:1px solid var(--border-default); }
  .ay-payment-summary > div:nth-child(2) { border-left:0; }
  .ay-payment-summary > div { padding:.9rem 1rem; }
  .ay-billing-page .eisa-header-actions > .ay-icon-action { flex:0 0 38px; }
  .ay-icon-action { width:38px; height:38px; }
  .ay-tab-bar { width: 100%; max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .ay-filter-fields, .ay-filter-field { width: 100%; }
  .ay-filter-select, .ay-filter-input, .ay-filter-field--lookup { width: 100%; min-width: 0; }
  .invoice-meta-grid { grid-template-columns: 1fr; }
  .invoice-table { display: block; overflow-x: auto; }
}
</style>
