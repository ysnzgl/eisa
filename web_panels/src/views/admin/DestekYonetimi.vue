<script setup>
/**
 * Görüş ve Destek Yönetimi — Admin paneli
 *
 * - Tüm eczanelerden gelen talepleri listeler.
 * - Eczane, tür, alan, alt konu, durum, tarih ve ticket no filtreleri.
 * - Detay modalında konuşma geçmişi, yorum ekleme ve durum değiştirme.
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { http } from '../../services/api';
import { toast } from 'vue-sonner';
import EisaLookup from '../../components/shared/EisaLookup.vue';

// ── Parametreler ──────────────────────────────────────────────────────────────
const params    = ref([]);
const eczaneler = ref([]);

const talepTurleri = computed(() => params.value.filter(p => p.grup === 'TALEP_TURU'));
const alanlar      = computed(() => params.value.filter(p => p.grup === 'ALAN'));
const durumlar     = computed(() => params.value.filter(p => p.grup === 'DURUM'));
const altKonular   = computed(() => params.value.filter(p => p.grup === 'ALT_KONU'));

function altKonularFor(alanId) {
  if (!alanId) return altKonular.value;
  return altKonular.value.filter(p => p.ust_parametre_id === alanId);
}

const eczaneOptions = computed(() =>
  eczaneler.value.map(e => ({ id: e.id, label: e.ad, sub: `${e.il_adi||''} / ${e.ilce_adi||''}` }))
);

// ── Filtreler ─────────────────────────────────────────────────────────────────
const filters = reactive({
  eczane_id:       null,
  talep_turu_kod:  '',
  alan_kod:        '',
  alt_konu_kod:    '',
  durum_kod:       '',
  baslangic_tarihi:'',
  bitis_tarihi:    '',
  talep_no:        '',
});

watch(() => filters.alan_kod, () => { filters.alt_konu_kod = ''; });

function clearFilters() {
  Object.assign(filters, {
    eczane_id: null, talep_turu_kod: '', alan_kod: '',
    alt_konu_kod: '', durum_kod: '', baslangic_tarihi: '', bitis_tarihi: '', talep_no: '',
  });
}

// ── Talep listesi ─────────────────────────────────────────────────────────────
const talepler    = ref([]);
const listLoading = ref(false);
const listTotal   = ref(0);
const listPage    = ref(1);

async function loadTalepler() {
  listLoading.value = true;
  try {
    const q = { page: listPage.value, page_size: 20 };
    if (filters.eczane_id)        q.eczane_id        = filters.eczane_id;
    if (filters.talep_turu_kod)   q.talep_turu_kod   = filters.talep_turu_kod;
    if (filters.alan_kod)         q.alan_kod         = filters.alan_kod;
    if (filters.alt_konu_kod)     q.alt_konu_kod     = filters.alt_konu_kod;
    if (filters.durum_kod)        q.durum_kod        = filters.durum_kod;
    if (filters.baslangic_tarihi) q.baslangic_tarihi = filters.baslangic_tarihi;
    if (filters.bitis_tarihi)     q.bitis_tarihi     = filters.bitis_tarihi;
    if (filters.talep_no)         q.talep_no         = filters.talep_no.trim();

    const { data } = await http.get('/api/destek/talepler/', { params: q });
    talepler.value = data.results ?? [];
    listTotal.value = data.count ?? 0;
  } catch { /* interceptor */ }
  finally { listLoading.value = false; }
}

watch(filters, () => { listPage.value = 1; loadTalepler(); }, { deep: true });

// ── Detay modalı ──────────────────────────────────────────────────────────────
const detailOpen     = ref(false);
const detailLoading  = ref(false);
const detail         = ref(null);
const yeniYorum      = ref('');
const yorumSaving    = ref(false);
const durumSecilen   = ref('');
const durumSaving    = ref(false);

async function openDetail(talep) {
  detailOpen.value    = true;
  detailLoading.value = true;
  yeniYorum.value     = '';
  detail.value        = null;
  try {
    const { data } = await http.get(`/api/destek/talepler/${talep.id}/`);
    detail.value     = data;
    durumSecilen.value = data.durum_kod;
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
    durumSecilen.value = data.durum_kod;
    loadTalepler();
    toast.success('Yorum eklendi.');
  } catch { /* interceptor */ }
  finally { yorumSaving.value = false; }
}

async function changeDurum() {
  if (!durumSecilen.value || durumSecilen.value === detail.value.durum_kod) return;
  durumSaving.value = true;
  try {
    const { data } = await http.patch(
      `/api/destek/talepler/${detail.value.id}/durum-degistir/`,
      { durum_kod: durumSecilen.value }
    );
    detail.value.durum_kod = data.durum_kod;
    detail.value.durum_ad  = data.durum_ad;
    loadTalepler();
    toast.success('Durum güncellendi.');
  } catch { /* interceptor */ }
  finally { durumSaving.value = false; }
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
  const [{ data: pData }, { data: eData }] = await Promise.all([
    http.get('/api/destek/parametreler/'),
    http.get('/api/pharmacies/'),
    loadTalepler(),
  ]);
  params.value    = pData;
  eczaneler.value = Array.isArray(eData) ? eData : (eData?.results ?? []);
});
</script>

<template>
  <div class="eisa-page">
    <!-- ── Başlık ──────────────────────────────────────────────────────────── -->
    <div class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Destek</p>
        <h1 class="eisa-page-title">Görüş ve Destek Yönetimi</h1>
      </div>
      <div style="text-align:right">
        <span class="eisa-stat-label">Toplam</span>
        <div class="eisa-stat-value" style="font-size:1.4rem">{{ listTotal }}</div>
      </div>
    </div>

    <!-- ── Filtreler ──────────────────────────────────────────────────────── -->
    <div class="eisa-panel eisa-toolbar-panel">
      <div class="eisa-toolbar" style="flex-wrap:wrap;gap:.65rem">
        <!-- Ticket no -->
        <div class="eisa-search-wrap" style="min-width:180px;max-width:220px">
          <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
          <input v-model="filters.talep_no" class="eisa-field eisa-search-field" placeholder="Ticket no..." />
        </div>

        <!-- Eczane -->
        <div style="min-width:200px;max-width:260px">
          <EisaLookup
            v-model="filters.eczane_id"
            :options="eczaneOptions"
            placeholder="Eczane filtrele..."
            :clearable="true"
          />
        </div>

        <!-- Talep türü -->
        <select v-model="filters.talep_turu_kod" class="eisa-field eisa-filter">
          <option value="">Tüm Türler</option>
          <option v-for="p in talepTurleri" :key="p.kod" :value="p.kod">{{ p.ad }}</option>
        </select>

        <!-- Alan -->
        <select v-model="filters.alan_kod" class="eisa-field eisa-filter">
          <option value="">Tüm Alanlar</option>
          <option v-for="p in alanlar" :key="p.kod" :value="p.kod">{{ p.ad }}</option>
        </select>

        <!-- Alt konu -->
        <select v-model="filters.alt_konu_kod" class="eisa-field eisa-filter">
          <option value="">Tüm Alt Konular</option>
          <option v-for="p in altKonularFor(filters.alan_kod ? alanlar.find(a=>a.kod===filters.alan_kod)?.id : null)"
                  :key="p.kod" :value="p.kod">{{ p.ad }}</option>
        </select>

        <!-- Durum -->
        <select v-model="filters.durum_kod" class="eisa-field eisa-filter">
          <option value="">Tüm Durumlar</option>
          <option v-for="p in durumlar" :key="p.kod" :value="p.kod">{{ p.ad }}</option>
        </select>

        <!-- Tarih -->
        <input v-model="filters.baslangic_tarihi" type="date" class="eisa-field" style="width:140px" />
        <input v-model="filters.bitis_tarihi"     type="date" class="eisa-field" style="width:140px" />

        <button class="eisa-btn eisa-btn-ghost" @click="clearFilters">
          <i class="fa-solid fa-xmark"></i> Temizle
        </button>
      </div>
    </div>

    <!-- ── Tablo ──────────────────────────────────────────────────────────── -->
    <div class="eisa-panel">
      <div v-if="listLoading" style="text-align:center;padding:2.5rem">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;color:#B1121B"></i>
      </div>

      <div v-else-if="!talepler.length" style="text-align:center;color:#6B7280;padding:2.5rem">
        <i class="fa-solid fa-inbox" style="font-size:2rem;display:block;margin-bottom:.75rem"></i>
        Filtrelere uygun talep bulunamadı.
      </div>

      <div v-else class="eisa-table-wrap">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>No</th><th>Eczane</th><th>Açan</th><th>Tür</th><th>Alan</th>
              <th>Alt Konu</th><th>Kiosk</th><th>Durum</th><th>Tarih</th><th>Son Hareket</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in talepler" :key="t.id" class="admin-destek-row" @click="openDetail(t)">
              <td><span class="destek-no">{{ t.talep_no }}</span></td>
              <td>{{ t.eczane_adi }}</td>
              <td class="cell-muted">{{ t.olusturan_adi }}</td>
              <td>{{ t.talep_turu_ad }}</td>
              <td>{{ t.alan_ad }}</td>
              <td>{{ t.alt_konu_ad }}</td>
              <td class="cell-muted">{{ t.kiosk_ad || '—' }}</td>
              <td><span class="eisa-pill" :class="durumPill[t.durum_kod]">{{ t.durum_ad }}</span></td>
              <td class="cell-muted">{{ formatDate(t.olusturulma_tarihi) }}</td>
              <td class="cell-muted">{{ formatDate(t.son_hareket_tarihi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Sayfalama -->
      <div v-if="listTotal > 20" class="eisa-panel-footer">
        <span>Toplam {{ listTotal }} kayıt</span>
        <div style="display:flex;gap:.4rem">
          <button class="eisa-btn" :disabled="listPage<=1" @click="listPage--;loadTalepler()">‹</button>
          <span style="padding:.35rem .6rem;font-size:.8rem">{{ listPage }}</span>
          <button class="eisa-btn" :disabled="listPage*20>=listTotal" @click="listPage++;loadTalepler()">›</button>
        </div>
      </div>
    </div>

    <!-- ── Detay Modalı ───────────────────────────────────────────────────── -->
    <div v-if="detailOpen" class="eisa-modal-backdrop" @click.self="detailOpen=false">
      <div class="eisa-modal" style="max-width:680px">
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
            <!-- Meta bilgiler -->
            <div class="destek-detail-meta" style="margin-bottom:.85rem">
              <span class="eisa-pill" :class="durumPill[detail.durum_kod]">{{ detail.durum_ad }}</span>
              <span class="cell-muted">{{ detail.eczane_adi }}</span>
              <span class="cell-muted">·</span>
              <span class="cell-muted">{{ detail.talep_turu_ad }}</span>
              <span class="cell-muted">·</span>
              <span class="cell-muted">{{ detail.alan_ad }}</span>
              <span class="cell-muted">·</span>
              <span class="cell-muted">{{ detail.alt_konu_ad }}</span>
              <template v-if="detail.kiosk_ad">
                <span class="cell-muted">·</span>
                <span class="cell-muted"><i class="fa-solid fa-display" style="font-size:.7rem"></i> {{ detail.kiosk_ad }}</span>
              </template>
            </div>

            <!-- Konuşma geçmişi -->
            <div class="destek-convo">
              <div class="destek-msg destek-msg--user">
                <div class="destek-msg-header">
                  <strong>{{ detail.olusturan_adi }}</strong>
                  <span class="cell-muted">{{ formatDate(detail.olusturulma_tarihi) }}</span>
                </div>
                <div class="destek-msg-body">{{ detail.aciklama }}</div>
              </div>
              <div
                v-for="y in detail.yorumlar" :key="y.id"
                class="destek-msg"
                :class="y.yazar_rol === 'superadmin' ? 'destek-msg--admin' : 'destek-msg--user'"
              >
                <div class="destek-msg-header">
                  <strong>{{ y.yazar_adi }}</strong>
                  <span v-if="y.yazar_rol==='superadmin'" class="destek-admin-badge">E-İSA Destek</span>
                  <span class="cell-muted">{{ formatDate(y.olusturulma_tarihi) }}</span>
                </div>
                <div class="destek-msg-body">{{ y.yorum_metni }}</div>
              </div>
            </div>

            <!-- Yorum ekleme (kapalı değilse) -->
            <div v-if="detail.durum_kod !== 'KAPATILDI'" class="destek-reply" style="margin-top:1rem">
              <label class="eisa-field-label">
                Yorum Ekle
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
                <button class="eisa-btn eisa-btn-cta" @click="sendYorum" :disabled="yorumSaving||!yeniYorum.trim()">
                  <i v-if="yorumSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                  <i v-else class="fa-solid fa-paper-plane"></i>
                  {{ yorumSaving ? 'Gönderiliyor...' : 'Yorum Gönder' }}
                </button>
              </div>
            </div>

            <!-- Durum değiştirme -->
            <div class="destek-durum-row">
              <label class="eisa-field-label" style="margin:0;white-space:nowrap">Durum Değiştir</label>
              <select v-model="durumSecilen" class="eisa-field" style="max-width:200px">
                <option v-for="d in durumlar" :key="d.kod" :value="d.kod">{{ d.ad }}</option>
              </select>
              <button
                class="eisa-btn eisa-btn-cta"
                :disabled="durumSaving || durumSecilen === detail.durum_kod"
                @click="changeDurum"
              >
                <i v-if="durumSaving" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-check"></i>
                Kaydet
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.destek-no { font-family: 'DM Mono', monospace; font-size: .8rem; font-weight: 700; color: #B1121B; }
.admin-destek-row { cursor: pointer; }
.admin-destek-row:hover td { background: #FEF2F2; }
.eisa-table-wrap { overflow-x: auto; }
.destek-detail-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
  padding-bottom: .75rem; border-bottom: 1px solid #E5EBF1; font-size: .8rem;
}
.destek-convo {
  display: flex; flex-direction: column; gap: .75rem;
  max-height: 300px; overflow-y: auto;
  padding: .5rem; background: #F8FAFC; border-radius: 10px;
}
.destek-msg { border-radius: 10px; padding: .75rem 1rem; }
.destek-msg--user  { background: #fff; border: 1px solid #E5EBF1; }
.destek-msg--admin { background: #FFF1F2; border: 1px solid #FECACA; }
.destek-msg-header {
  display: flex; align-items: center; gap: .5rem; margin-bottom: .35rem; font-size: .78rem;
}
.destek-msg-header strong { font-weight: 700; color: #111827; }
.destek-admin-badge {
  background: #B1121B; color: #fff; font-size: .65rem; font-weight: 700;
  padding: .1rem .45rem; border-radius: 4px;
}
.destek-msg-body { font-size: .875rem; color: #374151; line-height: 1.5; white-space: pre-wrap; }
.destek-reply { margin-top: .5rem; }
.destek-durum-row {
  display: flex; align-items: center; gap: .65rem; margin-top: 1rem;
  padding-top: 1rem; border-top: 1px solid #E5EBF1;
}
</style>
