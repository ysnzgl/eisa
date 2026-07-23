<script setup>
/**
 * Gelişmiş Manuel Yayın — Salt Okunur (Faz 7)
 *
 * Kaldırılan: Tüm şablon/saat planı/gün planı create/edit/delete mutation fonksiyonları,
 *             ilgili importlar, state ve drag-reorder eventleri.
 * Korunan: Canonical async generation endpointi (generatePlaylists).
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { toast } from 'vue-sonner';
import {
  listPlaylistTemplates,
  listHourPlans,
  listDayPlans,
  generatePlaylists, getGenerationJob,
  listKiosks,
} from '../../services/dooh.js';
import { getIller, getIlceler } from '../../services/lookups.js';

// ─── Veri ────────────────────────────────────────────────────────────────────
const sablonlar    = ref([]);
const hourPlanlar  = ref([]);
const dayPlanlar   = ref([]);
const yukleniyor   = ref(false);

async function veriYukle() {
  yukleniyor.value = true;
  try {
    const [s, h, d] = await Promise.all([
      listPlaylistTemplates(),
      listHourPlans(),
      listDayPlans(),
    ]);
    sablonlar.value   = Array.isArray(s.data) ? s.data : (s.data?.results ?? []);
    hourPlanlar.value = Array.isArray(h.data) ? h.data : (h.data?.results ?? []);
    dayPlanlar.value  = Array.isArray(d.data) ? d.data : (d.data?.results ?? []);
  } catch {
    toast.error('Veriler yuklenemedi.');
  } finally {
    yukleniyor.value = false;
  }
}

// ─── Canonical Playlist Uretim (Async Job) ────────────────────────────────────
const uretimTarihi    = ref(new Date().toISOString().slice(0, 10));
const hedefKapsam     = ref('all');
const hedefIlId       = ref(null);
const hedefIlceId     = ref(null);
const seciliKiosklar  = ref([]);
const uretiliyor      = ref(false);
const uretimKilit     = ref(false);
const aktifIs         = ref(null);
const iller           = ref([]);
const ilceler         = ref([]);
const kiosklar        = ref([]);
const kioskYukleniyor = ref(false);
let _isAnketi = null;

const kapsamiKioskSayisi = computed(() => {
  if (hedefKapsam.value === 'all')    return kiosklar.value.length;
  if (hedefKapsam.value === 'il')     return kiosklar.value.filter(k => k.il_id   === hedefIlId.value).length;
  if (hedefKapsam.value === 'ilce')   return kiosklar.value.filter(k => k.ilce_id === hedefIlceId.value).length;
  return seciliKiosklar.value.length;
});

async function kioskTargetingYukle() {
  kioskYukleniyor.value = true;
  try {
    const [ilRes, kRes] = await Promise.all([getIller(), listKiosks({ aktif: true, page_size: 500 })]);
    iller.value = Array.isArray(ilRes) ? ilRes : (ilRes?.results ?? []);
    const kData = kRes.data;
    kiosklar.value = Array.isArray(kData) ? kData : (kData?.results ?? []);
  } catch { /* sessiz */ }
  finally { kioskYukleniyor.value = false; }
}

async function ilDegisti() {
  hedefIlceId.value = null; ilceler.value = []; seciliKiosklar.value = [];
  if (hedefIlId.value) { try { ilceler.value = await getIlceler(hedefIlId.value); } catch { /* */ } }
}

function kioskSecimiToggle(id) {
  seciliKiosklar.value = seciliKiosklar.value.includes(id)
    ? seciliKiosklar.value.filter(k => k !== id)
    : [...seciliKiosklar.value, id];
}

async function uretimBaslat() {
  if (uretimKilit.value) return;
  if (!confirm('Secilen kiosklarda playlist uretimi baslatilsin mi?')) return;
  uretimKilit.value = true;
  uretiliyor.value = true;
  aktifIs.value = null;
  try {
    const istek = { date: uretimTarihi.value, scope: hedefKapsam.value };
    if (hedefKapsam.value === 'il'    && hedefIlId.value)         istek.il_id     = hedefIlId.value;
    if (hedefKapsam.value === 'ilce'  && hedefIlceId.value)       istek.ilce_id   = hedefIlceId.value;
    if (hedefKapsam.value === 'kiosks' && seciliKiosklar.value.length) istek.kiosk_ids = seciliKiosklar.value;
    const { data } = await generatePlaylists(istek);
    toast.success('Uretim kuyruga alindi (' + (data.total_kiosks ?? '?') + ' kiosk).');
    if (data.job_id) isAnketle(data.job_id);
  } catch (e) {
    toast.error('Uretim baslatılamadi: ' + (e?.response?.data?.error ?? e?.message ?? ''));
  } finally {
    uretiliyor.value = false;
    uretimKilit.value = false;
  }
}

function isAnketle(isId) {
  if (!isId) return;
  if (_isAnketi) { clearInterval(_isAnketi); _isAnketi = null; }
  _isAnketi = setInterval(async () => {
    try {
      const { data } = await getGenerationJob(isId);
      aktifIs.value = data;
      if (data.status === 'DONE' || data.status === 'FAILED') {
        clearInterval(_isAnketi); _isAnketi = null;
        if (data.status === 'DONE') toast.success('Tamamlandi — ' + (data.playlists_generated ?? 0) + ' playlist uretildi.');
        else toast.error('Uretim basarisiz oldu.');
      }
    } catch { clearInterval(_isAnketi); _isAnketi = null; }
  }, 3000);
}

onMounted(async () => {
  await Promise.all([veriYukle(), kioskTargetingYukle()]);
});

onUnmounted(() => {
  if (_isAnketi) { clearInterval(_isAnketi); _isAnketi = null; }
});
</script>

<template>
  <div class="eisa-page">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">Gelismis</p>
        <h1 class="eisa-page-title">Gelismis Manuel Yayin</h1>
        <p class="eisa-page-subtitle">Mevcut sablonlari ve planlari goruntule. Kampanya yonetimi icin CampaignWizard kullanin.</p>
      </div>
      <div class="eisa-header-actions">
        <button class="eisa-btn" @click="veriYukle" :disabled="yukleniyor">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': yukleniyor }"></i> Yenile
        </button>
        <a href="/admin/campaigns" class="eisa-btn eisa-btn-cta">
          <i class="fa-solid fa-bullhorn"></i> Kampanyalar
        </a>
      </div>
    </header>

    <!-- Salt okunur uyarisi -->
    <div class="eisa-panel" style="border-left:4px solid #f59e0b;background:#fffbeb;margin-bottom:.75rem">
      <div class="eisa-panel-body" style="padding:.6rem 1rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
        <i class="fa-solid fa-lock" style="color:#f59e0b"></i>
        <span style="font-size:.875rem">
          <strong>Salt okunur gorunum.</strong>
          Sablon, saat plani veya gun plani olusturma/duzenleme/silme bu ekranda yapilamaz.
          Kampanya yonetimi icin <a href="/admin/campaigns" style="color:#B1121B;font-weight:600">Kampanyalar (CampaignWizard)</a>,
          izleme icin <a href="/admin/dooh/control-center" style="color:#B1121B;font-weight:600">Kontrol Merkezi</a> kullanin.
        </span>
      </div>
    </div>

    <!-- Loop Sablonlari -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Loop Sablonlari</h2>
        <span class="eisa-pill eisa-pill-muted" style="font-size:.75rem">Salt Okunur</span>
      </div>
      <div class="eisa-panel-body">
        <div v-if="yukleniyor" class="empty-row">Yukleniyor...</div>
        <div v-else-if="!sablonlar.length" class="empty-row">Loop sablonu yok.</div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead><tr><th>Ad</th><th>Slot Sayisi</th><th>Sure</th><th>Hedef Saatler</th></tr></thead>
            <tbody>
              <tr v-for="s in sablonlar" :key="s.id">
                <td><strong>{{ s.name }}</strong></td>
                <td>{{ (s.slots ?? []).length }}</td>
                <td>{{ s.loop_duration_seconds ?? 60 }}sn</td>
                <td class="cell-muted">{{ s.target_hours?.length ? s.target_hours.join(', ') : 'Tum gun' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Saatlik Planlar -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Saatlik Planlar</h2>
        <span class="eisa-pill eisa-pill-muted" style="font-size:.75rem">Salt Okunur</span>
      </div>
      <div class="eisa-panel-body">
        <div v-if="yukleniyor" class="empty-row">Yukleniyor...</div>
        <div v-else-if="!hourPlanlar.length" class="empty-row">Saatlik plan yok.</div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead><tr><th>Ad</th><th>Slot Sayisi</th></tr></thead>
            <tbody>
              <tr v-for="h in hourPlanlar" :key="h.id">
                <td><strong>{{ h.name }}</strong></td>
                <td>{{ (h.slots ?? []).length }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Gunluk Planlar -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title">Gunluk Planlar</h2>
        <span class="eisa-pill eisa-pill-muted" style="font-size:.75rem">Salt Okunur</span>
      </div>
      <div class="eisa-panel-body">
        <div v-if="yukleniyor" class="empty-row">Yukleniyor...</div>
        <div v-else-if="!dayPlanlar.length" class="empty-row">Gunluk plan yok.</div>
        <div v-else class="table-wrap">
          <table class="eisa-table">
            <thead><tr><th>Ad</th><th>Atanmis Saat</th></tr></thead>
            <tbody>
              <tr v-for="d in dayPlanlar" :key="d.id">
                <td><strong>{{ d.name }}</strong></td>
                <td>{{ (d.slots ?? []).length }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Canonical Playlist Uretimi -->
    <section class="eisa-panel">
      <div class="eisa-panel-header">
        <h2 class="eisa-panel-title"><i class="fa-solid fa-gears"></i> Manuel Playlist Uretimi</h2>
        <span class="eisa-pill eisa-pill-info" style="font-size:.75rem">Canonical Async Endpoint</span>
      </div>
      <div class="eisa-panel-body" style="padding:1rem">
        <p class="muted small" style="margin-bottom:.75rem">
          Secilen tarih ve kiosklarda playlist uretimi baslatir. Is kuyruga alinir;
          <a href="/admin/dooh/control-center" style="color:#B1121B">Kontrol Merkezi</a>'nde izleyebilirsiniz.
        </p>
        <div style="display:flex;gap:.75rem;flex-wrap:wrap;margin-bottom:.75rem;align-items:flex-end">
          <div>
            <label class="eisa-field-label">Tarih</label>
            <input type="date" class="eisa-field" v-model="uretimTarihi" />
          </div>
          <div>
            <label class="eisa-field-label">Kapsam</label>
            <select class="eisa-field" v-model="hedefKapsam" @change="seciliKiosklar = []">
              <option value="all">Tum Aktif Kiosklar</option>
              <option value="il">Ile Ait</option>
              <option value="ilce">Ilceye Ait</option>
              <option value="kiosks">Secili Kiosklar</option>
            </select>
          </div>
          <div v-if="hedefKapsam === 'il' || hedefKapsam === 'ilce'">
            <label class="eisa-field-label">Il</label>
            <select class="eisa-field" v-model="hedefIlId" @change="ilDegisti">
              <option :value="null">— Secin —</option>
              <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad }}</option>
            </select>
          </div>
          <div v-if="hedefKapsam === 'ilce' && hedefIlId">
            <label class="eisa-field-label">Ilce</label>
            <select class="eisa-field" v-model="hedefIlceId">
              <option :value="null">— Secin —</option>
              <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad }}</option>
            </select>
          </div>
        </div>
        <div v-if="hedefKapsam === 'kiosks'" style="margin-bottom:.75rem;max-height:200px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px;padding:.5rem">
          <div v-if="kioskYukleniyor" class="empty-row">Yukleniyor...</div>
          <label v-for="k in kiosklar" :key="k.id"
                 style="display:flex;align-items:center;gap:.5rem;padding:.3rem .5rem;cursor:pointer;border-radius:4px"
                 :style="seciliKiosklar.includes(k.id) ? 'background:#eef2ff' : ''">
            <input type="checkbox" :checked="seciliKiosklar.includes(k.id)" @change="kioskSecimiToggle(k.id)" />
            <span style="font-size:.875rem">{{ k.ad }}</span>
          </label>
        </div>
        <div style="display:flex;align-items:center;gap:1rem">
          <button class="eisa-btn eisa-btn-cta"
                  :disabled="uretiliyor || uretimKilit || (hedefKapsam === 'kiosks' && !seciliKiosklar.length)"
                  @click="uretimBaslat">
            <i class="fa-solid" :class="uretiliyor ? 'fa-circle-notch fa-spin' : 'fa-play'"></i>
            {{ uretiliyor ? 'Baslatiliyor...' : 'Playlist Uret' }}
          </button>
          <span class="muted small">{{ kapsamiKioskSayisi }} kiosk</span>
        </div>
        <div v-if="aktifIs" style="margin-top:.75rem;padding:.75rem;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0">
          <div style="display:flex;align-items:center;gap:.75rem">
            <span class="eisa-pill" :class="{
              'eisa-pill-warning': aktifIs.status === 'PENDING' || aktifIs.status === 'RUNNING',
              'eisa-pill-success': aktifIs.status === 'DONE',
              'eisa-pill-danger':  aktifIs.status === 'FAILED',
            }">{{ aktifIs.status }}</span>
            <span v-if="aktifIs.total_kiosks" class="muted small">
              {{ aktifIs.done_kiosks }}/{{ aktifIs.total_kiosks }} kiosk
            </span>
            <i v-if="aktifIs.status === 'PENDING' || aktifIs.status === 'RUNNING'" class="fa-solid fa-circle-notch fa-spin muted"></i>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<style scoped>
.empty-row { text-align:center; padding:1.5rem; color:var(--c-text-muted,#64748b); font-size:.875rem; }
.cell-muted { color:var(--c-text-muted,#64748b); font-size:.85rem; }
</style>