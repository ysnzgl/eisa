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
  uploadIslakImza, getIslakImzaUrl,
} from '../../services/abonelik';
import { getPharmacies } from '../../services/devices';
import SozlesmeForm from '../../components/shared/SozlesmeForm.vue';
import EisaLookup from '../../components/shared/EisaLookup.vue';
import SozlesmeMatbu from '../../components/shared/SozlesmeMatbu.vue';
import { useConfirm } from '../../composables/useConfirm.js';

const route = useRoute();
const { confirm } = useConfirm();
const tab = ref('sozlesmeler');

const sozlesmeler = ref([]);
const faturalar = ref([]);
const talepler = ref([]);
const odemeler = ref([]);
const eczaneler = ref([]);
const eczaneOptions = computed(() =>
  eczaneler.value.map(e => ({ id: e.id, label: e.name || e.ad || String(e.id) })));
const loading = ref(false);

const TAKSITLER = [
  { value: 1, label: '1 Taksit (Peşin)' },
  { value: 4, label: '4 Taksit' },
  { value: 8, label: '8 Taksit' },
  { value: 12, label: '12 Taksit' },
];

const stats = computed(() => ({
  toplam: sozlesmeler.value.length,
  aktif: sozlesmeler.value.filter((s) => s.durum === 'AKTIF').length,
  cihazli: sozlesmeler.value.filter((s) => s.cihaz_plani).length,
  bekleyenTalepler: talepler.value.filter((t) => t.durum === 'BEKLIYOR').length,
}));

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
  abonelik_bedeli: '3900.00',
  cihaz_kira_bedeli: '0.00',
  acma_kapama_orani: DEFAULT_ACMA_KAPAMA_ORANI.toFixed(2),
  acma_kapama_bedeli: '0.00',
  iptal_ceza_orani: '2.00',
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
  } catch { /* sessiz */ }
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
    abonelik_bedeli: aktifFiyat.value?.abonelik_bedeli || '3900.00',
    cihaz_kira_bedeli: aktifFiyat.value?.cihaz_kira_bedeli || '0.00',
    acma_kapama_orani: hesaplaAcmaKapamaOrani(
      aktifFiyat.value?.abonelik_bedeli || '3900.00',
      aktifFiyat.value?.acma_kapama_bedeli || '0.00',
    ),
    acma_kapama_bedeli: aktifFiyat.value?.acma_kapama_bedeli || '0.00',
    iptal_ceza_orani: aktifFiyat.value?.iptal_ceza_orani || '2.00',
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
    || Number(fiyatForm.iptal_ceza_orani) < 0
  ) {
    toast.error('Bedeller ve ceza çarpanı 0 veya üzeri olmalı.'); return;
  }
  fiyatSaving.value = true;
  try {
    await createFiyat({
      abonelik_bedeli: String(fiyatForm.abonelik_bedeli),
      cihaz_kira_bedeli: String(fiyatForm.cihaz_kira_bedeli),
      acma_kapama_bedeli: String(fiyatForm.acma_kapama_bedeli),
      iptal_ceza_orani: String(fiyatForm.iptal_ceza_orani),
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
const islakImzaYukleniyor = ref(false);
const emptySozlesme = () => ({
  eczane: null,
  tur: 'STANDART',
  sozlesme_tipi_ay: 24,
  demo_gun: 30,
  baslangic_tarihi: '',
  oteleme_ay: 0,
  aylik_kullanim_bedeli: '3900.00',
  cihaz_durumu: 'SATILIK',
  cihaz_kira_bedeli: '0.00',
  pesin_fiyat: '',
  vade_farki_orani: '0.00',
  taksit_sayisi: 1,
  cihaz_baslangic_tarihi: '',
  durum: 'AKTIF',
  notlar: '',
  kdv_orani: 0,
  tevkifat_orani: '',
  iptal_ceza_orani: '2.00',
  imza_tipi: 'DIJITAL',
  islak_imza_url: '',
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
    const { data } = await listFaturalar();
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
    const { data } = await listOdemeler();
    odemeler.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Ödemeler yüklenemedi.');
  } finally { loading.value = false; }
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
    kararSozlesme.sozlesme_tipi_ay = Number(t.istenen_tip_ay || 24);
    kararSozlesme.demo_gun = Number(t.istenen_demo_gun || 30);
    kararSozlesme.baslangic_tarihi = today();
    kararSozlesme.cihaz_baslangic_tarihi = today();
    kararSozlesme.cihaz_planlari = [];
    if (aktifFiyat.value) {
      kararSozlesme.aylik_kullanim_bedeli = aktifFiyat.value.abonelik_bedeli;
      kararSozlesme.iptal_ceza_orani = aktifFiyat.value.iptal_ceza_orani || '2.00';
    }
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
    if (f.cihaz_durumu === 'KIRALIK' && Number(f.cihaz_kira_bedeli || 0) <= 0) {
      toast.error('Kiralık cihaz için kira bedeli girin.'); return;
    }
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
  try {
    eczaneler.value = await getPharmacies();
  } catch { /* sessiz */ }
}

onMounted(async () => {
  await Promise.all([loadSozlesmeler(), loadEczaneler(), loadAktifFiyat()]);
});

function switchTab(t) {
  tab.value = t;
  if (t === 'faturalar' && !faturalar.value.length) loadFaturalar();
  if (t === 'talepler' && !talepler.value.length) loadTalepler();
  if (t === 'odemeler' && !odemeler.value.length) loadOdemeler();
}

// ── Sözleşme CRUD ───────────────────────────────────────────────────────────
function openCreate() {
  editingId.value = null;
  Object.assign(form, emptySozlesme());
  if (aktifFiyat.value) {
    form.aylik_kullanim_bedeli = aktifFiyat.value.abonelik_bedeli;
    form.iptal_ceza_orani = aktifFiyat.value.iptal_ceza_orani || '2.00';
  }
  formOpen.value = true;
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
    cihaz_durumu: s.cihaz_durumu || 'SATILIK',
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
    imza_tipi: s.imza_tipi || 'DIJITAL',
    islak_imza_url: s.islak_imza_url || '',
    cihaz_planlari: (s.cihaz_planlari || []).map(p => ({
      id: p.id,
      tip: p.tip || 'SATILIK',
      adet: p.adet || 1,
      pesin_fiyat: p.pesin_fiyat || '',
      vade_farki_orani: p.vade_farki_orani || '0.00',
      taksit_sayisi: p.taksit_sayisi || 1,
      aylik_kira_bedeli: p.aylik_kira_bedeli || '',
      cihaz_kdv_orani: p.cihaz_kdv_orani || 0,
      tevkifat_orani: p.tevkifat_orani || '',
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
      cihaz_durumu: 'SATILIK',
      cihaz_kira_bedeli: '0.00',
      notlar: form.notlar,
      kdv_orani: Number(form.kdv_orani || 0),
      tevkifat_orani: form.tevkifat_orani || '',
      iptal_ceza_orani: String(form.iptal_ceza_orani || '0.00'),
      imza_tipi: form.imza_tipi || 'DIJITAL',
      islak_imza_url: form.islak_imza_url || '',
    };

    let saved;
    if (editingId.value) {
      saved = await updateSozlesme(editingId.value, payload);
      toast.success('Sözleşme güncellendi.');
    } else {
      saved = await createSozlesme(payload);
      toast.success('Sözleşme oluşturuldu.');
    }

    const targetId = editingId.value ?? saved?.data?.id;
    if (targetId && form.cihaz_planlari.length > 0) {
      await saveCihazPlanlari(targetId, form.cihaz_planlari);
    }
    // Islak imza belgesi seçilmişse yükle
    if (targetId && form.imza_tipi === 'ISLAK' && islakImzaDosya.value) {
      islakImzaYukleniyor.value = true;
      try {
        const { data } = await uploadIslakImza(targetId, islakImzaDosya.value);
        form.islak_imza_url = data.object_key;
        toast.success('Islak imza belgesi RustFS\'e yüklendi.');
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Belge yüklenemedi.');
      } finally {
        islakImzaDosya.value = null;
        islakImzaYukleniyor.value = false;
      }
    }
    formOpen.value = false;
    await loadSozlesmeler();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Kaydedilemedi.');
  } finally { saving.value = false; }
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
  if (vadeFarkiEksik.value) {
    toast.error('1 aydan fazla taksitte vade farkı zorunludur (> %0).');
    return;
  }
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
  <div class="eisa-page">
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">YÖNETİCİ / ABONELİK</p>
        <h1 class="eisa-page-title">Abonelik ve Ödeme</h1>
        <p class="eisa-page-subtitle">Sözleşme, cihaz ödeme planı ve fatura yönetimi.</p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn eisa-btn-ghost" title="Aylık abonelik ve cihaz kira bedeli tanımları" @click="openFiyat">
          <i class="fa-solid fa-tags"></i> Fiyat Tanımları
        </button>
        <button class="eisa-btn eisa-btn-ghost" :disabled="billingRunning" title="Bu dönemin faturalarını şimdi üret" @click="runFaturalandir">
          <i :class="billingRunning ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-file-invoice-dollar'"></i>
          {{ billingRunning ? 'Faturalandırılıyor…' : 'Faturalandır' }}
        </button>
        <button v-if="tab === 'sozlesmeler'" class="eisa-btn eisa-btn-cta" @click="openCreate">
          <i class="fa-solid fa-plus"></i> Yeni Sözleşme
        </button>
      </div>
    </div>

    <section class="eisa-stats">
      <div class="eisa-stat-card"><span class="eisa-stat-label">Toplam Sözleşme</span><span class="eisa-stat-value">{{ stats.toplam }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Aktif</span><span class="eisa-stat-value">{{ stats.aktif }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Cihaz Planlı</span><span class="eisa-stat-value">{{ stats.cihazli }}</span></div>
      <button
        v-if="stats.bekleyenTalepler > 0"
        class="eisa-stat-card eisa-stat-card--clickable"
        type="button"
        @click="switchTab('talepler')"
      >
        <span class="eisa-stat-label">Bekleyen Talep</span>
        <span class="eisa-stat-value">{{ stats.bekleyenTalepler }}</span>
      </button>
    </section>

    <div class="eisa-header-actions">
      <button class="eisa-btn" :class="tab === 'sozlesmeler' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="switchTab('sozlesmeler')">
        <i class="fa-solid fa-file-contract"></i> Sözleşmeler
      </button>
      <button class="eisa-btn" :class="tab === 'faturalar' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="switchTab('faturalar')">
        <i class="fa-solid fa-file-invoice-dollar"></i> Faturalar
      </button>
      <button class="eisa-btn" :class="tab === 'talepler' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="switchTab('talepler')">
        <i class="fa-solid fa-paper-plane"></i> Talepler
      </button>
      <button class="eisa-btn" :class="tab === 'odemeler' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="switchTab('odemeler')">
        <i class="fa-solid fa-receipt"></i> Ödemeler
      </button>
    </div>

    <!-- ── Sözleşmeler ─────────────────────────────────────────────── -->
    <section v-if="tab === 'sozlesmeler'" class="eisa-panel">
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
            <tr v-for="s in sozlesmeler" :key="s.id">
              <td><strong>{{ s.eczane_ad }}</strong></td>
              <td><span class="eisa-pill" :class="turPill(s.tur)">{{ s.tur_display }}</span></td>
              <td>{{ s.tur === 'DEMO' ? `${s.toplam_gun} gün` : s.tip_display }}</td>
              <td><span class="eisa-pill" :class="kalanPill(s)">{{ kalanLabel(s) }}</span></td>
              <td>{{ s.tur === 'DEMO' ? '—' : `${s.oteleme_ay} ay` }}</td>
              <td>{{ s.tur === 'DEMO' ? '—' : fmtTL(s.aylik_kullanim_bedeli) }}</td>
              <td class="cell-muted">{{ s.baslangic_tarihi }}</td>
              <td class="cell-muted">{{ s.bitis_tarihi }}</td>
              <td>
                <span v-if="s.cihaz_plani" class="eisa-pill eisa-pill-info">
                  {{ s.cihaz_plani.taksit_sayisi }}× {{ fmtTL(s.cihaz_plani.taksit_tutari) }}
                </span>
                <span v-else class="cell-muted">—</span>
              </td>
              <td><span class="eisa-pill" :class="durumPill(s)">{{ durumLabel(s) }}</span></td>
              <td class="cell-muted" style="font-size:.75rem;">
                <span v-if="s.eczaci_onay_tarihi" title="Eczacı onayladı">✅</span>
                <span v-else title="Eczacı onayı bekleniyor" style="color:#D97706;">⏳</span>
              </td>
              <td class="cell-actions">
                <button class="eisa-icon-btn" title="Düzzenle" @click="openEdit(s)"><i class="fa-solid fa-pen"></i></button>
                <button class="eisa-icon-btn" title="Sözleşmeyi Görüntle" @click="openMatbuAdmin(s)"><i class="fa-solid fa-file-contract"></i></button>
                <button class="eisa-icon-btn" title="Uzat" @click="openUzat(s)"><i class="fa-solid fa-calendar-plus"></i></button>
                <button v-if="s.durum !== 'IPTAL'" class="eisa-icon-btn" title="İptal Et" @click="openIptal(s)"><i class="fa-solid fa-ban"></i></button>
                <button class="eisa-icon-btn" title="Geçmiş" @click="openGecmis(s)"><i class="fa-solid fa-clock-rotate-left"></i></button>
              </td>
            </tr>
            <tr v-if="!sozlesmeler.length && !loading">
              <td colspan="11" class="empty-row">Henüz sözleşme yok.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Faturalar ───────────────────────────────────────────────── -->
    <section v-else-if="tab === 'faturalar'" class="eisa-panel">
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Eczane</th><th>Tip</th><th>Dönem</th><th>Taksit</th>
              <th>Tutar</th><th>Vade</th><th>Durum</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in faturalar" :key="f.id">
              <td><strong>{{ f.eczane_ad }}</strong></td>
              <td>{{ f.tip_display }}</td>
              <td>{{ f.donem }}</td>
              <td>{{ f.taksit_no ?? '—' }}</td>
              <td>{{ fmtTL(f.tutar) }}</td>
              <td class="cell-muted">{{ f.vade_tarihi }}</td>
              <td><span class="eisa-pill" :class="PILL[f.durum]">{{ f.durum_display }}</span></td>
              <td class="cell-actions">
                <button class="eisa-btn eisa-btn-ghost eisa-btn--sm" @click="openFaturaModal(f)">
                  <i class="fa-solid fa-file-lines"></i> Görüntüle
                </button>
                <button v-if="f.durum === 'BEKLIYOR' || f.durum === 'GECIKTI'"
                        class="eisa-btn eisa-btn-success eisa-btn--sm" @click="openOdemeModal(f)">
                  <i class="fa-solid fa-check"></i> Ödendi
                </button>
              </td>
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
              <td class="cell-actions">
                <template v-if="t.durum === 'BEKLIYOR'">
                  <button class="eisa-btn eisa-btn-success eisa-btn--sm" @click="karar(t, true)">
                    <i class="fa-solid fa-check"></i> Onayla
                  </button>
                  <button class="eisa-btn eisa-btn-danger eisa-btn--sm" @click="karar(t, false)">
                    <i class="fa-solid fa-xmark"></i> Reddet
                  </button>
                </template>
              </td>
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
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr><th>Tarih</th><th>Eczane</th><th>Kalem</th><th>Tutar</th><th>Yöntem</th></tr>
          </thead>
          <tbody>
            <tr v-for="o in odemeler" :key="o.id">
              <td class="cell-muted">{{ fmtDate(o.odeme_tarihi) }}</td>
              <td><strong>{{ o.eczane_ad }}</strong></td>
              <td>{{ o.fatura_tip }} · {{ o.fatura_donem }}</td>
              <td>{{ fmtTL(o.tutar) }}</td>
              <td>{{ o.yontem_display }}</td>
            </tr>
            <tr v-if="!odemeler.length && !loading">
              <td colspan="5" class="empty-row">Ödeme kaydı bulunamadı.</td>
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
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="kapatFaturaModal">Kapat</button>
          </div>
        </div>
      </div>
    </Teleport>

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
              <label class="eisa-form-row">
                <span class="eisa-field-label">Ceza Çarpanı (× aylık)</span>
                <input type="number" step="0.01" min="0" v-model="fiyatForm.iptal_ceza_orani" class="eisa-field" />
              </label>
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
                <thead><tr><th>Geçerlilik</th><th>Abonelik</th><th>Cihaz Kira</th><th>Aç/Kapa</th><th>Ceza Çarpanı</th><th>Açıklama</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="fp in fiyatlar" :key="fp.id">
                    <td class="cell-muted">{{ fp.gecerlilik_baslangic }}</td>
                    <td>{{ fmtTL(fp.abonelik_bedeli) }}</td>
                    <td>{{ fmtTL(fp.cihaz_kira_bedeli) }}</td>
                    <td>{{ fmtTL(fp.acma_kapama_bedeli) }}</td>
                    <td>×{{ fp.iptal_ceza_orani }}</td>
                    <td class="cell-muted">{{ fp.aciklama || '—' }}</td>
                    <td class="cell-actions">
                      <button class="eisa-icon-btn" title="Sil" @click="deleteFiyatItem(fp)">
                        <i class="fa-solid fa-trash"></i>
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!fiyatlar.length"><td colspan="7" class="empty-row">Henüz fiyat tanımı yok.</td></tr>
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
              <div v-if="iptalHedef?.iptal_ceza_orani > 0" class="eisa-error-banner eisa-form-row-full">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>Erken iptal cezası: <strong>{{ fmtTL(iptalHedef.iptal_ceza_tutari) }}</strong>
                  (%{{ iptalHedef.iptal_ceza_orani }} × {{ iptalHedef.kalan_gun }} kalan gün)</span>
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
      <div v-if="formOpen" class="eisa-modal-backdrop" @click.self="formOpen = false">
        <div class="eisa-modal eisa-modal--big" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ editingId ? 'Sözleşme Düzenle' : 'Yeni Sözleşme' }}</h3>
            <button class="eisa-modal-close" title="Kapat" @click="formOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Eczane</span>
                <EisaLookup
                  v-model="form.eczane"
                  :options="eczaneOptions"
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
                <label class="eisa-form-row">
                  <span class="eisa-field-label">İmza Tipi</span>
                  <select v-model="form.imza_tipi" class="eisa-field">
                    <option value="DIJITAL">Dijital İmza (eczacı ekrandan onaylar)</option>
                    <option value="ISLAK">Islak İmza (taranıp yüklenir)</option>
                  </select>
                </label>
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
                <p v-if="form.imza_tipi === 'ISLAK'" class="eisa-reset-info eisa-form-row-full">
                  <i class="fa-solid fa-circle-info"></i>
                  Islak imzalı sözleşme eczacı ekranına onay için düşmez. Taranan belgeyi RustFS'e yükleyip kalıcı path girin (expiring URL değil).
                </p>
              </div>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="formOpen = false">İptal</button>
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
      <div v-if="matbuAdminOpen" class="eisa-modal-backdrop" @click.self="matbuAdminOpen = false">
        <div class="eisa-modal eisa-modal--medium" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <div>
              <h3 class="eisa-modal-title">Sözleşme Belgesi</h3>
              <p class="eisa-reset-info">{{ matbuAdminSozlesme?.eczane_ad }}</p>
            </div>
            <button class="eisa-modal-close" @click="matbuAdminOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <SozlesmeMatbu v-if="matbuAdminSozlesme" :sozlesme="matbuAdminSozlesme" />
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" @click="matbuAdminOpen = false">Kapat</button>
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
</style>
