<script setup>
/**
 * Görüş ve Destek — Pharmacy (Eczacı) paneli
 *
 * - Eczanenin tüm destek taleplerini listeler (açık/kapalı filtresi).
 * - Yeni talep formu: tür, alan, parametrik alt konu, kiosk seçimi, açıklama.
 * - Talep detay modalı: açıklama + kronolojik yorumlar + cevap formu.
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { http } from '../../services/api';
import { toast } from 'vue-sonner';
import EisaLookup from '../../components/shared/EisaLookup.vue';

// ── Parametreler ──────────────────────────────────────────────────────────────
const params = ref([]);

const talepTurleri = computed(() => params.value.filter(p => p.grup === 'TALEP_TURU'));
const alanlar      = computed(() => params.value.filter(p => p.grup === 'ALAN'));
const altKonular   = computed(() => params.value.filter(p => p.grup === 'ALT_KONU'));

function altKonularFor(alanId) {
  if (!alanId) return [];
  return altKonular.value.filter(p => p.ust_parametre_id === alanId);
}

// ── Talep listesi ─────────────────────────────────────────────────────────────
const talepler     = ref([]);
const listLoading  = ref(false);
const listFilter   = ref('acik');   // 'acik' | 'kapali' | ''
const listTotal    = ref(0);
const listPage     = ref(1);

async function loadTalepler() {
  listLoading.value = true;
  try {
    const params = { page: listPage.value, page_size: 20 };
    if (listFilter.value) params.durum_kategori = listFilter.value;
    const { data } = await http.get('/api/destek/talepler/', { params });
    talepler.value = data.results ?? data;
    listTotal.value = data.count ?? talepler.value.length;
  } catch { /* interceptor toast */ }
  finally { listLoading.value = false; }
}

watch(listFilter, () => { listPage.value = 1; loadTalepler(); });

// ── Kiosk listesi (eczane filtreli) ───────────────────────────────────────────
const kiosklar = ref([]);

async function loadKiosklar() {
  if (kiosklar.value.length) return;
  try {
    const { data } = await http.get('/api/pharmacies/me/dashboard/');
    kiosklar.value = Array.isArray(data?.kiosklar) ? data.kiosklar : [];
  } catch { /* ignore */ }
}

const kioskOptions = computed(() =>
  kiosklar.value.map(k => ({ id: k.id, label: k.ad, sub: k.eczane_adi || '' }))
);

// ── Yeni talep formu ──────────────────────────────────────────────────────────
const formOpen = ref(false);
const saving   = ref(false);

const emptyForm = () => ({
  talep_turu_id: null,
  alan_id: null,
  alt_konu_id: null,
  kiosk_id: null,
  aciklama: '',
});
const form = reactive(emptyForm());

function openForm() {
  Object.assign(form, emptyForm());
  formOpen.value = true;
}

watch(() => form.alan_id, () => {
  form.alt_konu_id = null;
  form.kiosk_id    = null;
});

const secilenAlan   = computed(() => alanlar.value.find(a => a.id === form.alan_id));
const secilenAltKonu = computed(() => altKonular.value.find(a => a.id === form.alt_konu_id));

const kioskGoster = computed(() => {
  if (!secilenAlan.value) return false;
  return secilenAlan.value.kod === 'KIOSK';
});

const kioskZorunlu = computed(() => {
  if (!secilenAltKonu.value) return false;
  return secilenAltKonu.value.kod === 'KIOSK_CIHAZ' && kiosklar.value.length > 1;
});

async function submitForm() {
  if (!form.talep_turu_id || !form.alan_id || !form.alt_konu_id || !form.aciklama.trim()) {
    toast.error('Lütfen zorunlu alanları doldurun.');
    return;
  }
  saving.value = true;
  try {
    await http.post('/api/destek/talepler/', {
      talep_turu_id: form.talep_turu_id,
      alan_id:       form.alan_id,
      alt_konu_id:   form.alt_konu_id,
      kiosk_id:      form.kiosk_id || null,
      aciklama:      form.aciklama.trim(),
    });
    toast.success('Talebiniz oluşturuldu.');
    formOpen.value = false;
    listFilter.value = 'acik';
    loadTalepler();
  } catch { /* interceptor */ }
  finally { saving.value = false; }
}

// ── Talep detay modalı ────────────────────────────────────────────────────────
const detailOpen   = ref(false);
const detailLoading = ref(false);
const detail       = ref(null);
const yeniYorum    = ref('');
const yorumSaving  = ref(false);

async function openDetail(talep) {
  detailOpen.value   = true;
  detailLoading.value = true;
  yeniYorum.value    = '';
  try {
    const { data } = await http.get(`/api/destek/talepler/${talep.id}/`);
    detail.value = data;
  } catch { detailOpen.value = false; }
  finally { detailLoading.value = false; }
}

async function sendYorum() {
  if (!yeniYorum.value.trim()) return;
  yorumSaving.value = true;
  try {
    await http.post(`/api/destek/talepler/${detail.value.id}/yorum-ekle/`,
      { yorum_metni: yeniYorum.value.trim() });
    yeniYorum.value = '';
    const { data } = await http.get(`/api/destek/talepler/${detail.value.id}/`);
    detail.value = data;
    loadTalepler();
    toast.success('Yanıtınız gönderildi.');
  } catch { /* interceptor */ }
  finally { yorumSaving.value = false; }
}

// ── Yardımcılar ───────────────────────────────────────────────────────────────
const durumPill = {
  YENI:        'eisa-pill-info',
  INCELENIYOR: 'eisa-pill-warning',
  YANITLANDI:  'eisa-pill-success',
  KAPATILDI:   'eisa-pill-muted',
};

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}

// ── Mount ─────────────────────────────────────────────────────────────────────
onMounted(async () => {
  const [{ data: pData }] = await Promise.all([
    http.get('/api/destek/parametreler/'),
    loadTalepler(),
    loadKiosklar(),
  ]);
  params.value = pData;
});
</script>

<template>
  <div class="eisa-page">
    <!-- ── Karşılama Alanı ──────────────────────────────────────────────── -->
    <div class="destek-banner">
      <div class="destek-banner-icon"><i class="fa-solid fa-heart-pulse"></i></div>
      <div>
        <h2 class="destek-banner-title">Görüş ve Destek</h2>
        <p class="destek-banner-text">
          Görüşleriniz E-İSA'yı her gün daha iyi hâle getiriyor. Sahadaki deneyiminiz bizim için en değerli rehberdir.
          Paylaştığınız her öneri ve bildirimi dikkatle değerlendiriyor, katkılarınızla birlikte gelişiyoruz.
        </p>
      </div>
    </div>

    <!-- ── Yeni Talep Formu ──────────────────────────────────────────────── -->
    <div class="eisa-panel" style="margin-bottom:1.5rem">
      <div class="eisa-panel-header">
        <span class="eisa-panel-title">Yeni Talep Oluştur</span>
        <button class="eisa-btn eisa-btn-cta" @click="openForm" v-if="!formOpen">
          <i class="fa-solid fa-plus"></i> Yeni Talep
        </button>
        <button class="eisa-btn eisa-btn-ghost" @click="formOpen = false" v-else>
          <i class="fa-solid fa-xmark"></i> İptal
        </button>
      </div>

      <div v-if="formOpen" class="eisa-panel-body">
        <div class="destek-form-grid">
          <!-- Talep türü -->
          <div class="eisa-form-row">
            <label class="eisa-field-label">Talep Türü <span class="req">*</span></label>
            <select v-model="form.talep_turu_id" class="eisa-field">
              <option :value="null" disabled>Seçin...</option>
              <option v-for="t in talepTurleri" :key="t.id" :value="t.id">{{ t.ad }}</option>
            </select>
          </div>

          <!-- Alan (Kiosk/Portal) -->
          <div class="eisa-form-row">
            <label class="eisa-field-label">İlgili Alan <span class="req">*</span></label>
            <select v-model="form.alan_id" class="eisa-field">
              <option :value="null" disabled>Seçin...</option>
              <option v-for="a in alanlar" :key="a.id" :value="a.id">{{ a.ad }}</option>
            </select>
          </div>

          <!-- Alt konu -->
          <div class="eisa-form-row">
            <label class="eisa-field-label">Alt Konu <span class="req">*</span></label>
            <select v-model="form.alt_konu_id" class="eisa-field" :disabled="!form.alan_id">
              <option :value="null" disabled>{{ form.alan_id ? 'Seçin...' : 'Önce alan seçin' }}</option>
              <option v-for="ak in altKonularFor(form.alan_id)" :key="ak.id" :value="ak.id">{{ ak.ad }}</option>
            </select>
          </div>

          <!-- Kiosk seçimi (koşullu) -->
          <div v-if="kioskGoster" class="eisa-form-row">
            <label class="eisa-field-label">
              İlgili Kiosk
              <span v-if="kioskZorunlu" class="req"> *</span>
              <span v-else class="eisa-cell-sub"> (opsiyonel)</span>
            </label>
            <EisaLookup
              v-model="form.kiosk_id"
              :options="kioskOptions"
              placeholder="Kiosk ara..."
              :clearable="true"
            />
          </div>

          <!-- Açıklama (full width) -->
          <div class="eisa-form-row eisa-form-row-full">
            <label class="eisa-field-label">
              Açıklama <span class="req">*</span>
              <span class="eisa-cell-sub" style="font-weight:400"> {{ form.aciklama.length }}/1000</span>
            </label>
            <textarea
              v-model="form.aciklama"
              class="eisa-field"
              rows="4"
              maxlength="1000"
              placeholder="Talebinizi detaylıca açıklayın..."
              style="resize:vertical"
            ></textarea>
            <p v-if="form.aciklama.length >= 950" class="destek-char-warn">
              {{ 1000 - form.aciklama.length }} karakter kaldı.
            </p>
          </div>
        </div>

        <div style="display:flex;justify-content:flex-end;margin-top:1rem">
          <button class="eisa-btn eisa-btn-cta" @click="submitForm" :disabled="saving">
            <i v-if="saving" class="fa-solid fa-circle-notch fa-spin"></i>
            <i v-else class="fa-solid fa-paper-plane"></i>
            {{ saving ? 'Gönderiliyor...' : 'Talebi Gönder' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Talep Listesi ────────────────────────────────────────────────── -->
    <div class="eisa-panel">
      <div class="eisa-panel-header">
        <span class="eisa-panel-title">Taleplerim</span>
        <div style="display:flex;gap:.5rem">
          <button
            v-for="opt in [{v:'acik',l:'Açık'},{v:'kapali',l:'Kapalı'},{v:'',l:'Tümü'}]"
            :key="opt.v"
            class="eisa-btn"
            :class="listFilter===opt.v ? 'eisa-btn-cta' : ''"
            @click="listFilter=opt.v"
          >{{ opt.l }}</button>
        </div>
      </div>

      <div v-if="listLoading" class="eisa-panel-body" style="text-align:center;padding:2rem">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;color:#B1121B"></i>
      </div>

      <div v-else-if="!talepler.length" class="eisa-panel-body" style="text-align:center;color:#6B7280;padding:2.5rem">
        <i class="fa-solid fa-inbox" style="font-size:2rem;margin-bottom:.75rem;display:block"></i>
        Henüz bir talebiniz bulunmuyor.
      </div>

      <div v-else class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>No</th><th>Tür</th><th>Alan</th><th>Alt Konu</th>
              <th>Kiosk</th><th>Durum</th><th>Açan</th><th>Tarih</th><th>Son Hareket</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in talepler" :key="t.id" class="destek-row" @click="openDetail(t)">
              <td><span class="destek-no">{{ t.talep_no }}</span></td>
              <td>{{ t.talep_turu_ad }}</td>
              <td>{{ t.alan_ad }}</td>
              <td>{{ t.alt_konu_ad }}</td>
              <td class="cell-muted">{{ t.kiosk_ad || '—' }}</td>
              <td><span class="eisa-pill" :class="durumPill[t.durum_kod]">{{ t.durum_ad }}</span></td>
              <td class="cell-muted">{{ t.olusturan_adi }}</td>
              <td class="cell-muted">{{ formatDate(t.olusturulma_tarihi) }}</td>
              <td class="cell-muted">{{ formatDate(t.son_hareket_tarihi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Detay Modalı ──────────────────────────────────────────────────── -->
    <div v-if="detailOpen" class="eisa-modal-backdrop" @click.self="detailOpen=false">
      <div class="eisa-modal" style="max-width:640px">
        <div class="eisa-modal-header">
          <h3 class="eisa-modal-title">
            <i class="fa-solid fa-ticket" style="color:#B1121B;margin-right:.5rem"></i>
            {{ detail?.talep_no ?? '...' }}
          </h3>
          <button class="eisa-modal-close" @click="detailOpen=false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div v-if="detailLoading" class="eisa-modal-body" style="text-align:center;padding:2rem">
          <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;color:#B1121B"></i>
        </div>

        <template v-else-if="detail">
          <div class="eisa-modal-body">
            <!-- Bilgi satırı -->
            <div class="destek-detail-meta">
              <span class="eisa-pill" :class="durumPill[detail.durum_kod]">{{ detail.durum_ad }}</span>
              <span class="cell-muted">{{ detail.talep_turu_ad }}</span>
              <span class="cell-muted">·</span>
              <span class="cell-muted">{{ detail.alan_ad }}</span>
              <span class="cell-muted">·</span>
              <span class="cell-muted">{{ detail.alt_konu_ad }}</span>
              <template v-if="detail.kiosk_ad">
                <span class="cell-muted">·</span>
                <span class="cell-muted"><i class="fa-solid fa-display" style="font-size:.75rem"></i> {{ detail.kiosk_ad }}</span>
              </template>
            </div>

            <!-- Konuşma geçmişi -->
            <div class="destek-convo">
              <!-- İlk mesaj (açıklama) -->
              <div class="destek-msg destek-msg--user">
                <div class="destek-msg-header">
                  <strong>{{ detail.olusturan_adi }}</strong>
                  <span class="cell-muted">{{ formatDate(detail.olusturulma_tarihi) }}</span>
                </div>
                <div class="destek-msg-body">{{ detail.aciklama }}</div>
              </div>

              <!-- Yorumlar -->
              <div
                v-for="y in detail.yorumlar"
                :key="y.id"
                class="destek-msg"
                :class="y.yazar_rol === 'superadmin' ? 'destek-msg--admin' : 'destek-msg--user'"
              >
                <div class="destek-msg-header">
                  <strong>{{ y.yazar_adi }}</strong>
                  <span v-if="y.yazar_rol === 'superadmin'" class="destek-admin-badge">E-İSA Destek</span>
                  <span class="cell-muted">{{ formatDate(y.olusturulma_tarihi) }}</span>
                </div>
                <div class="destek-msg-body">{{ y.yorum_metni }}</div>
              </div>
            </div>

            <!-- Cevap alanı (kapalı değilse) -->
            <div v-if="detail.durum_kod !== 'KAPATILDI'" class="destek-reply">
              <label class="eisa-field-label">
                Yanıtınız
                <span class="eisa-cell-sub"> {{ yeniYorum.length }}/1000</span>
              </label>
              <textarea
                v-model="yeniYorum"
                class="eisa-field"
                rows="3"
                maxlength="1000"
                placeholder="Yanıtınızı yazın..."
                style="resize:vertical"
              ></textarea>
              <div style="display:flex;justify-content:flex-end;margin-top:.5rem">
                <button class="eisa-btn eisa-btn-cta" @click="sendYorum" :disabled="yorumSaving || !yeniYorum.trim()">
                  <i v-if="yorumSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                  <i v-else class="fa-solid fa-paper-plane"></i>
                  {{ yorumSaving ? 'Gönderiliyor...' : 'Gönder' }}
                </button>
              </div>
            </div>
            <div v-else class="destek-closed-note">
              <i class="fa-solid fa-lock"></i> Bu talep kapatılmıştır.
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.destek-banner {
  display: flex; gap: 1.25rem; align-items: flex-start;
  background: linear-gradient(135deg, #FFF1F2 0%, #FEF2F2 100%);
  border: 1px solid #FECACA; border-radius: 16px;
  padding: 1.5rem 1.75rem; margin-bottom: 1.75rem;
}
.destek-banner-icon {
  font-size: 1.75rem; color: #B1121B; flex-shrink: 0; margin-top: .1rem;
}
.destek-banner-title {
  font-family: 'Syne', sans-serif; font-size: 1.25rem; font-weight: 700;
  color: #111827; margin: 0 0 .4rem;
}
.destek-banner-text {
  font-size: .875rem; color: #4B5563; margin: 0; line-height: 1.6;
}
.destek-form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: .85rem 1rem;
}
.req { color: #B1121B; }
.destek-char-warn { font-size:.75rem; color:#B45309; margin:.25rem 0 0; }
.eisa-table-wrap { overflow-x: auto; }
.destek-row { cursor: pointer; }
.destek-row:hover td { background: #FEF2F2; }
.destek-no { font-family: 'DM Mono', monospace; font-size: .8rem; font-weight: 700; color: #B1121B; }
.destek-detail-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
  margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #E5EBF1;
  font-size: .8rem;
}
.destek-convo {
  display: flex; flex-direction: column; gap: .75rem;
  max-height: 320px; overflow-y: auto; margin-bottom: 1rem;
  padding: .5rem; background: #F8FAFC; border-radius: 10px;
}
.destek-msg { border-radius: 10px; padding: .75rem 1rem; }
.destek-msg--user  { background: #fff; border: 1px solid #E5EBF1; }
.destek-msg--admin { background: #FFF1F2; border: 1px solid #FECACA; }
.destek-msg-header {
  display: flex; align-items: center; gap: .5rem; margin-bottom: .35rem;
  font-size: .78rem;
}
.destek-msg-header strong { font-weight: 700; color: #111827; }
.destek-admin-badge {
  background: #B1121B; color: #fff; font-size: .65rem; font-weight: 700;
  padding: .1rem .45rem; border-radius: 4px; letter-spacing: .02em;
}
.destek-msg-body { font-size: .875rem; color: #374151; line-height: 1.5; white-space: pre-wrap; }
.destek-reply { margin-top: .25rem; }
.destek-closed-note {
  text-align: center; color: #6B7280; font-size: .875rem;
  padding: .75rem; background: #F3F4F6; border-radius: 8px;
  margin-top: .5rem;
}
@media (max-width: 640px) {
  .destek-form-grid { grid-template-columns: 1fr; }
}
</style>
