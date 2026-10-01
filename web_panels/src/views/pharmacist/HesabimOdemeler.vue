<script setup>
/**
 * Hesabım & Ödemeler (Eczacı) — sözleşme özeti, cari borç, fatura ödeme,
 * sözleşme talepleri (yeni/uzatma/iptal), ödeme ve sözleşme hareketleri.
 * Kısıtlı panelde (sözleşmesiz/ödeme gecikmiş) yalnız bu ekran erişilebilir.
 */
import { ref, reactive, computed, onMounted } from 'vue';
import { toast } from 'vue-sonner';
import {
  getHesabim, getFaturalarim, odeFatura,
  getOdemelerim, getHareketlerim, getTaleplerim, createTalep,
} from '../../services/abonelik';

const loading = ref(false);
const hesap = ref(null);
const faturalar = ref([]);
const odemeler = ref([]);
const hareketler = ref([]);
const talepler = ref([]);
const odenenId = ref(null);

const aktifSozlesme = computed(() => hesap.value?.sozlesme || null);
const bekleyenTalep = computed(() => talepler.value.some((t) => t.durum === 'BEKLIYOR'));

function daysUntil(dateStr) {
  if (!dateStr) return Infinity;
  return Math.ceil((new Date(dateStr) - new Date()) / 86400000);
}
const bitisYakin = computed(() => {
  const s = aktifSozlesme.value;
  if (!s || s.kalan_gun == null) return false;
  return s.kalan_gun >= 0 && s.kalan_gun <= 7;
});
const suresiDoldu = computed(() => aktifSozlesme.value?.suresi_doldu === true);
const odemeYakin = computed(() =>
  faturalar.value.some((f) =>
    (f.durum === 'BEKLIYOR' || f.durum === 'GECIKTI') && daysUntil(f.vade_tarihi) <= 3));

async function load() {
  loading.value = true;
  try {
    const [h, f, o, hr, t] = await Promise.all([
      getHesabim(), getFaturalarim(), getOdemelerim(), getHareketlerim(), getTaleplerim(),
    ]);
    hesap.value = h.data;
    faturalar.value = Array.isArray(f.data) ? f.data : (f.data?.results ?? []);
    odemeler.value = o.data ?? [];
    hareketler.value = hr.data ?? [];
    talepler.value = t.data ?? [];
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Hesap bilgileri yüklenemedi.');
  } finally { loading.value = false; }
}

onMounted(load);

async function pay(f) {
  odenenId.value = f.id;
  try {
    await odeFatura(f.id, 'KREDI_KARTI');
    toast.success('Ödemeniz alındı. Teşekkürler.');
    await load();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Ödeme başarısız.');
  } finally { odenenId.value = null; }
}

// ── Talep ────────────────────────────────────────────────────────────────────
const talepOpen = ref(false);
const talepSaving = ref(false);
const emptyTalep = () => ({
  talep_tipi: 'YENI',
  istenen_tur: 'STANDART',
  istenen_tip_ay: 24,
  istenen_demo_gun: 30,
  ek_ay: 6,
  ek_gun: 15,
  aciklama: '',
});
const talepForm = reactive(emptyTalep());
const talepDemoUzatma = computed(() => aktifSozlesme.value?.tur === 'DEMO');
const TALEP_BASLIK = {
  YENI: 'Yeni Sözleşme Talebi',
  UZATMA: 'Sözleşme Uzatma Talebi',
  IPTAL: 'Sözleşme İptal Talebi',
};

function openTalep(tip) {
  if (bekleyenTalep.value) {
    toast.info('Bekleyen bir talebiniz var. Sonuçlanmadan yeni talep oluşturamazsınız.');
    return;
  }
  Object.assign(talepForm, emptyTalep());
  talepForm.talep_tipi = tip;
  talepOpen.value = true;
}

async function saveTalep() {
  const payload = { talep_tipi: talepForm.talep_tipi, aciklama: talepForm.aciklama };
  if (talepForm.talep_tipi === 'YENI') {
    payload.istenen_tur = talepForm.istenen_tur;
    if (talepForm.istenen_tur === 'DEMO') payload.istenen_demo_gun = Number(talepForm.istenen_demo_gun);
    else payload.istenen_tip_ay = Number(talepForm.istenen_tip_ay);
  } else {
    if (!aktifSozlesme.value) { toast.error('Aktif sözleşme bulunamadı.'); return; }
    payload.hedef_sozlesme = aktifSozlesme.value.id;
    if (talepForm.talep_tipi === 'UZATMA') {
      if (talepDemoUzatma.value) payload.ek_gun = Number(talepForm.ek_gun);
      else payload.ek_ay = Number(talepForm.ek_ay);
    }
  }
  talepSaving.value = true;
  try {
    await createTalep(payload);
    toast.success('Talebiniz alındı. Yönetici onayına gönderildi.');
    talepOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e?.response?.data?.detail
      || Object.values(e?.response?.data || {})?.[0]?.[0]
      || 'Talep gönderilemedi.');
  } finally { talepSaving.value = false; }
}

// ── Biçim ────────────────────────────────────────────────────────────────────
function fmtTL(v) {
  return Number(v || 0).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' });
}
function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}
const PILL = {
  ODENDI: 'eisa-pill-success', BEKLIYOR: 'eisa-pill-warning',
  GECIKTI: 'eisa-pill-danger', IPTAL: 'eisa-pill-muted',
  ONAYLANDI: 'eisa-pill-success', REDDEDILDI: 'eisa-pill-danger',
};
function faturaDurum(d) {
  return { ODENDI: 'Ödendi', BEKLIYOR: 'Bekliyor', GECIKTI: 'Gecikti', IPTAL: 'İptal' }[d] || d;
}
function tipLabel(t) {
  return {
    KULLANIM_BEDELI: 'Kullanım Bedeli',
    CIHAZ_TAKSIT: 'Cihaz Taksiti',
    CIHAZ_KIRA: 'Cihaz Kira Bedeli',
  }[t] || t;
}
const HAREKET_ICON = {
  SOZLESME: 'fa-file-contract', UZATMA: 'fa-calendar-plus',
  TALEP: 'fa-paper-plane', ODEME: 'fa-credit-card',
};
</script>

<template>
  <div class="eisa-page">
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">ECZACI / HESABIM</p>
        <h1 class="eisa-page-title">Hesabım ve Ödemeler</h1>
        <p class="eisa-page-subtitle">Sözleşme, ödeme ve talep yönetimi.</p>
      </div>
      <div class="eisa-header-actions">
        <span v-if="bekleyenTalep" class="eisa-pill eisa-pill-warning">
          <i class="fa-solid fa-hourglass-half"></i> Bekleyen talebiniz inceleniyor
        </span>
        <template v-else-if="aktifSozlesme">
          <button class="eisa-btn eisa-btn-ghost" @click="openTalep('UZATMA')">
            <i class="fa-solid fa-calendar-plus"></i> Uzatma Talebi
          </button>
          <button class="eisa-btn eisa-btn-ghost" @click="openTalep('IPTAL')">
            <i class="fa-solid fa-ban"></i> İptal Talebi
          </button>
        </template>
        <button v-else class="eisa-btn eisa-btn-ghost" @click="openTalep('YENI')">
          <i class="fa-solid fa-file-circle-plus"></i> Yeni Sözleşme Talebi
        </button>
      </div>
    </div>

    <!-- Kısıtlı panel uyarısı -->
    <div v-if="hesap?.panel_kisitli" class="eisa-error-banner">
      <i class="fa-solid fa-lock"></i>
      <span>
        <strong>Paneliniz kısıtlı.</strong>
        {{ hesap.kisit_nedeni === 'SOZLESME_YOK'
          ? 'Aktif bir sözleşmeniz bulunmuyor. Lütfen yeni sözleşme talebi oluşturun; onaylanınca tüm özellikler açılır.'
          : 'Gecikmiş ödemeniz nedeniyle yalnızca bu ekranı kullanabilirsiniz. Ödemenizi tamamlayın.' }}
      </span>
    </div>

    <!-- Demo -->
    <section v-if="hesap?.demo" class="eisa-panel">
      <div class="eisa-panel-body">
        <span class="eisa-pill eisa-pill-warning"><i class="fa-solid fa-flask"></i> DEMO AŞAMASI</span>
        <p class="eisa-reset-info">
          Demo sözleşmeniz aktif. Demo süresince kullanım bedeli faturalanmaz. Kalıcı kullanım için
          yeni sözleşme talebi oluşturabilirsiniz.
        </p>
      </div>
    </section>

    <!-- Yaklaşan bitiş / ödeme ısrarlı uyarıları -->
    <div v-if="suresiDoldu" class="eisa-error-banner">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span><strong>Sözleşmenizin süresi doldu.</strong> Hizmetin kesintisiz devamı için lütfen uzatma talebi oluşturun.</span>
    </div>
    <div v-else-if="bitisYakin" class="eisa-error-banner" style="background:#FFFBEB;border-color:#FDE68A;color:#B45309;">
      <i class="fa-solid fa-clock"></i>
      <span><strong>Sözleşmeniz {{ aktifSozlesme.kalan_gun }} gün içinde bitiyor.</strong> Uzatma talebi oluşturabilirsiniz.</span>
    </div>
    <div v-if="odemeYakin" class="eisa-error-banner" style="background:#FFFBEB;border-color:#FDE68A;color:#B45309;">
      <i class="fa-solid fa-hand-holding-dollar"></i>
      <span><strong>Ödeme gününüz yaklaşıyor.</strong> Gecikmeden ödeme yaparak hesabınızın kısıtlanmasını önleyin.</span>
    </div>

    <!-- Özet -->
    <section v-if="aktifSozlesme" class="eisa-stats">
      <div class="eisa-stat-card"><span class="eisa-stat-label">Açık Fatura</span><span class="eisa-stat-value">{{ hesap?.acik_fatura_sayisi ?? 0 }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Toplam Borç</span><span class="eisa-stat-value">{{ fmtTL(hesap?.toplam_borc) }}</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Kalan Süre</span><span class="eisa-stat-value">{{ aktifSozlesme.kalan_gun }} gün</span></div>
      <div class="eisa-stat-card"><span class="eisa-stat-label">Bitiş</span><span class="eisa-stat-value">{{ aktifSozlesme.bitis_tarihi }}</span></div>
    </section>

    <!-- Sözleşme bilgileri -->
    <section v-if="aktifSozlesme" class="eisa-panel">
      <div class="eisa-panel-header"><h3 class="eisa-panel-title">Sözleşme Bilgileri</h3></div>
      <div class="eisa-panel-body">
        <div class="eisa-form-grid">
          <div class="eisa-form-row"><span class="eisa-field-label">Tür</span><strong>{{ aktifSozlesme.tur_display }}</strong></div>
          <div class="eisa-form-row"><span class="eisa-field-label">Süre</span><strong>{{ aktifSozlesme.tur === 'DEMO' ? aktifSozlesme.toplam_gun + ' gün' : aktifSozlesme.tip_display }}</strong></div>
          <div v-if="aktifSozlesme.tur !== 'DEMO'" class="eisa-form-row"><span class="eisa-field-label">Aylık Kullanım Bedeli</span><strong>{{ fmtTL(aktifSozlesme.aylik_kullanim_bedeli) }}</strong></div>
          <div v-if="aktifSozlesme.cihaz_plani" class="eisa-form-row">
            <span class="eisa-field-label">Cihaz Taksiti</span>
            <strong>{{ aktifSozlesme.cihaz_plani.taksit_sayisi }}× {{ fmtTL(aktifSozlesme.cihaz_plani.taksit_tutari) }}</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- Faturalar -->
    <section v-if="aktifSozlesme || faturalar.length" class="eisa-panel">
      <div class="eisa-panel-header"><h3 class="eisa-panel-title">Faturalarım</h3></div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead><tr><th>Tip</th><th>Dönem</th><th>Taksit</th><th>Tutar</th><th>Vade</th><th>Durum</th><th></th></tr></thead>
          <tbody>
            <tr v-for="f in faturalar" :key="f.id">
              <td>{{ tipLabel(f.tip) }}</td>
              <td>{{ f.donem }}</td>
              <td>{{ f.taksit_no ?? '—' }}</td>
              <td>{{ fmtTL(f.tutar) }}</td>
              <td class="cell-muted">{{ f.vade_tarihi }}</td>
              <td><span class="eisa-pill" :class="PILL[f.durum]">{{ faturaDurum(f.durum) }}</span></td>
              <td class="cell-actions">
                <button v-if="f.durum === 'BEKLIYOR' || f.durum === 'GECIKTI'"
                        class="eisa-btn eisa-btn-success eisa-btn--sm" :disabled="odenenId === f.id" @click="pay(f)">
                  <i :class="odenenId === f.id ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-credit-card'"></i>
                  {{ odenenId === f.id ? 'İşleniyor…' : 'Ödeme Yap' }}
                </button>
              </td>
            </tr>
            <tr v-if="!faturalar.length && !loading"><td colspan="7" class="empty-row">Faturanız bulunmuyor.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Taleplerim -->
    <section v-if="talepler.length" class="eisa-panel">
      <div class="eisa-panel-header"><h3 class="eisa-panel-title">Sözleşme Taleplerim</h3></div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead><tr><th>Tip</th><th>Açıklama</th><th>Durum</th><th>Tarih</th></tr></thead>
          <tbody>
            <tr v-for="t in talepler" :key="t.id">
              <td>{{ t.tip_display }}</td>
              <td class="cell-muted">{{ t.aciklama || t.red_nedeni || '—' }}</td>
              <td><span class="eisa-pill" :class="PILL[t.durum]">{{ t.durum_display }}</span></td>
              <td class="cell-muted">{{ fmtDate(t.olusturulma_tarihi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Ödeme geçmişi -->
    <section v-if="odemeler.length" class="eisa-panel">
      <div class="eisa-panel-header"><h3 class="eisa-panel-title">Ödeme Geçmişi</h3></div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead><tr><th>Tarih</th><th>Kalem</th><th>Tutar</th><th>Yöntem</th></tr></thead>
          <tbody>
            <tr v-for="o in odemeler" :key="o.id">
              <td class="cell-muted">{{ fmtDate(o.odeme_tarihi) }}</td>
              <td>{{ o.fatura_tip }} · {{ o.fatura_donem }}</td>
              <td>{{ fmtTL(o.tutar) }}</td>
              <td>{{ o.yontem_display }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Sözleşme hareketleri -->
    <section v-if="hareketler.length" class="eisa-panel">
      <div class="eisa-panel-header"><h3 class="eisa-panel-title">Sözleşme Hareketleri</h3></div>
      <div class="eisa-table-wrap">
        <table class="eisa-table">
          <thead><tr><th></th><th>Olay</th><th>Detay</th><th>Tarih</th></tr></thead>
          <tbody>
            <tr v-for="(h, i) in hareketler" :key="i">
              <td><i class="fa-solid" :class="HAREKET_ICON[h.tip] || 'fa-circle'"></i></td>
              <td>{{ h.baslik }}</td>
              <td class="cell-muted">{{ h.detay || '—' }}</td>
              <td class="cell-muted">{{ fmtDate(h.tarih) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Talep modal -->
    <Teleport to="body">
      <div v-if="talepOpen" class="eisa-modal-backdrop" @click.self="talepOpen = false">
        <div class="eisa-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ TALEP_BASLIK[talepForm.talep_tipi] || 'Sözleşme Talebi' }}</h3>
            <button class="eisa-modal-close" title="Kapat" @click="talepOpen = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-modal-body">
            <div class="eisa-form-grid">
              <template v-if="talepForm.talep_tipi === 'YENI'">
                <label class="eisa-form-row">
                  <span class="eisa-field-label">Sözleşme Türü</span>
                  <select v-model="talepForm.istenen_tur" class="eisa-field">
                    <option value="STANDART">Standart</option>
                    <option value="DEMO">Demo</option>
                  </select>
                </label>
                <label v-if="talepForm.istenen_tur === 'DEMO'" class="eisa-form-row">
                  <span class="eisa-field-label">Demo Süresi (gün ≤30)</span>
                  <input type="number" min="1" max="30" v-model.number="talepForm.istenen_demo_gun" class="eisa-field" />
                </label>
                <label v-else class="eisa-form-row">
                  <span class="eisa-field-label">Süre</span>
                  <select v-model.number="talepForm.istenen_tip_ay" class="eisa-field">
                    <option :value="12">12 Ay</option>
                    <option :value="24">24 Ay</option>
                    <option :value="36">36 Ay</option>
                  </select>
                </label>
              </template>

              <template v-else-if="talepForm.talep_tipi === 'UZATMA'">
                <label v-if="talepDemoUzatma" class="eisa-form-row">
                  <span class="eisa-field-label">Ek Gün</span>
                  <input type="number" min="1" max="30" v-model.number="talepForm.ek_gun" class="eisa-field" />
                </label>
                <label v-else class="eisa-form-row">
                  <span class="eisa-field-label">Ek Ay</span>
                  <input type="number" min="1" max="60" v-model.number="talepForm.ek_ay" class="eisa-field" />
                </label>
              </template>

              <p v-else-if="talepForm.talep_tipi === 'IPTAL'" class="eisa-reset-info eisa-form-row-full">
                <i class="fa-solid fa-circle-info"></i>
                Aktif sözleşmenizin iptalini talep ediyorsunuz. Onaylanırsa hizmet erişiminiz kapanır.
              </p>

              <label class="eisa-form-row eisa-form-row-full">
                <span class="eisa-field-label">Açıklama / Neden</span>
                <textarea v-model="talepForm.aciklama" rows="2" class="eisa-field"></textarea>
              </label>
            </div>
          </div>
          <div class="eisa-modal-footer">
            <button class="eisa-btn eisa-btn-ghost" :disabled="talepSaving" @click="talepOpen = false">İptal</button>
            <button class="eisa-btn eisa-btn-cta" :disabled="talepSaving" @click="saveTalep">
              <i :class="talepSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-paper-plane'"></i>
              {{ talepSaving ? 'Gönderiliyor…' : 'Talep Gönder' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
