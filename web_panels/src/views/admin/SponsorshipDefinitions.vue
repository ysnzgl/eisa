<script setup>
/**
 * Sponsorluk Tanımları — DOOH sponsorlukların (campaign) tanım ekranı.
 *
 * Basitleştirilmiş 3 adımlı drawer:
 *   1) Bilgiler : ad, reklam veren, başlangıç/bitiş, durum
 *   2) Medya    : creative yükle (bekleme + işlem ekranı medyası, süre)
 *   3) Kiosklar : atanmış kioskların salt-okunur listesi + "Kiosklara Ata"
 *
 * Hedefleme / frekans / simülasyon / aktivasyon adımları kaldırıldı; atama artık
 * cihaz (kiosk) bazlıdır (bkz. Kiosk Sponsorluk ekranı).
 *
 * Route: /admin/campaigns (SuperAdmin)
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  listCampaignsV2, createCampaignV2, updateCampaignV2,
  bulkActionCampaignsV2, createCreative, uploadMedia,
  getCampaignKiosks, assignKiosksToCampaign, listSponsorshipKiosks,
} from '../../services/dooh.js';
import EisaDeleteConfirm from '../../components/shared/EisaDeleteConfirm.vue';
import EisaMultiLookup from '../../components/shared/EisaMultiLookup.vue';
import DateRangePicker from '../../components/shared/DateRangePicker.vue';
import { useConfirm } from '../../composables/useConfirm.js';
import {
  WEEKDAYS, weekdaysText, isVideoUrl, extractCapacityError,
} from '../../composables/useSponsorship.js';

const { confirm } = useConfirm();

const STATUS_MAP = {
  ACTIVE:    { label: 'Aktif',        cls: 'eisa-pill-success' },
  PAUSED:    { label: 'Duraklatıldı', cls: 'eisa-pill-warning' },
  COMPLETED: { label: 'Tamamlandı',   cls: 'eisa-pill-muted' },
};
function campStatus(c) { return STATUS_MAP[c.status] || { label: c.status, cls: '' }; }

// ─── Liste ────────────────────────────────────────────────────────────────────
const campaigns = ref([]);
const loading   = ref(false);
const search    = ref('');
const statusFilter = ref('ALL');

async function refresh() {
  loading.value = true;
  try {
    const { data } = await listCampaignsV2();
    campaigns.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch {
    toast.error('Sponsorluklar yüklenemedi.');
  } finally { loading.value = false; }
}

const filtered = computed(() => {
  const q = search.value.trim().toLocaleLowerCase('tr');
  return campaigns.value.filter((c) => {
    if (statusFilter.value !== 'ALL' && c.status !== statusFilter.value) return false;
    if (!q) return true;
    return `${c.name} ${c.advertiser_name || ''}`.toLocaleLowerCase('tr').includes(q);
  });
});

const stats = computed(() => ({
  total: campaigns.value.length,
  active: campaigns.value.filter((c) => c.status === 'ACTIVE').length,
  paused: campaigns.value.filter((c) => c.status === 'PAUSED').length,
}));

// ─── Drawer / form ────────────────────────────────────────────────────────────
const drawerOpen = ref(false);
const editingId  = ref(null);
const step       = ref(1);
const STEP_LABELS = ['Bilgiler', 'Medya', 'Kiosklar'];
const saving     = ref(false);
const stepError  = ref('');

const _defaultStart = () => new Date().toISOString().slice(0, 16);
const _defaultEnd = () => { const d = new Date(); d.setMonth(d.getMonth() + 1); return d.toISOString().slice(0, 16); };

const emptyForm = () => ({
  name: '', advertiser_name: '',
  start_date: _defaultStart(), end_date: _defaultEnd(),
  status: 'ACTIVE',
  creatives: [],
});
const form = reactive(emptyForm());

function openCreate() {
  editingId.value = null;
  Object.assign(form, emptyForm());
  assignedKiosks.value = [];
  step.value = 1; stepError.value = ''; drawerOpen.value = true;
}

async function openEdit(c) {
  editingId.value = c.id;
  Object.assign(form, emptyForm(), {
    name: c.name,
    advertiser_name: c.advertiser_name || '',
    start_date: c.start_date?.slice(0, 16) ?? '',
    end_date: c.end_date?.slice(0, 16) ?? '',
    status: c.status,
    creatives: (c.creatives ?? []).map((cr) => ({
      id: cr.id, name: cr.name || 'Mevcut medya',
      duration_seconds: cr.duration_seconds,
      media_url: cr.media_url, uploaded_url: cr.media_url,
      object_key: cr.object_key || '',
      active_media_url: cr.active_media_url || '',
      active_object_key: cr.active_object_key || '',
    })),
  });
  step.value = 1; stepError.value = ''; drawerOpen.value = true;
  loadAssignedKiosks(c.id);
}

async function close() {
  drawerOpen.value = false;
}

function validateStep(n) {
  if (n === 1) {
    if (!form.name.trim()) return 'Sponsorluk adı zorunlu.';
    if (!form.start_date || !form.end_date) return 'Başlangıç ve bitiş tarihi zorunlu.';
    if (new Date(form.end_date) <= new Date(form.start_date)) return 'Bitiş tarihi başlangıçtan sonra olmalı.';
  }
  if (n === 2 && !form.creatives.length) return 'En az bir medya yükleyin.';
  return null;
}

function nextStep() {
  const err = validateStep(step.value);
  if (err) { stepError.value = err; return; }
  stepError.value = '';
  if (step.value < 3) step.value += 1;
}
function prevStep() { stepError.value = ''; if (step.value > 1) step.value -= 1; }

// ─── Medya upload (CampaignWizard davranışı korunur) ──────────────────────────
async function onPickFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.creatives.push({
      file, name: file.name, duration_seconds: 15,
      media_url: data.media_url ?? data.url ?? '',
      object_key: data.object_key ?? '',
      checksum: data.checksum ?? '',
      active_media_url: '',
      uploaded_url: data.media_url ?? data.url ?? '',
    });
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}

async function onPickActiveFile(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  if (!form.creatives.length) { toast.warning('Önce bekleme ekranı görselini yükleyin.'); ev.target.value = ''; return; }
  try {
    saving.value = true;
    const data = await uploadMedia(file);
    form.creatives[0].active_media_url = data.media_url ?? data.url ?? '';
    form.creatives[0].active_object_key = data.object_key ?? '';
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Medya yüklenemedi.');
  } finally { saving.value = false; ev.target.value = ''; }
}
function removeActiveMedia() { if (form.creatives.length) form.creatives[0].active_media_url = ''; }
function removeCreative(idx) { form.creatives.splice(idx, 1); }

function buildCampaignPayload() {
  return {
    name: form.name,
    advertiser_name: form.advertiser_name || '',
    start_date: new Date(form.start_date).toISOString(),
    end_date: new Date(form.end_date).toISOString(),
    status: form.status,
  };
}

async function save() {
  for (let n = 1; n <= 2; n++) { const e = validateStep(n); if (e) { stepError.value = e; step.value = n; return; } }
  saving.value = true; stepError.value = '';
  try {
    const payload = buildCampaignPayload();
    let cId;
    if (editingId.value) {
      await updateCampaignV2(editingId.value, payload);
      cId = editingId.value;
    } else {
      const { data } = await createCampaignV2(payload);
      cId = data.id;
      editingId.value = cId;
    }
    for (const cr of form.creatives) {
      if (cr.id) continue;
      await createCreative({
        campaign: cId,
        media_url: cr.media_url || cr.uploaded_url || '',
        active_media_url: cr.active_media_url || '',
        object_key: cr.object_key || undefined,
        active_object_key: cr.active_object_key || undefined,
        checksum: cr.checksum || undefined,
        duration_seconds: Number(cr.duration_seconds),
        name: cr.name?.slice(0, 120) || '',
      });
    }
    toast.success('Sponsorluk kaydedildi.');
    await refresh();
    if (editingId.value) loadAssignedKiosks(editingId.value);
  } catch (e) {
    const cap = extractCapacityError(e);
    stepError.value = cap?.detail || e?.response?.data?.detail || 'Kayıt başarısız.';
  } finally { saving.value = false; }
}

// ─── Silme ────────────────────────────────────────────────────────────────────
const deleteOpen = ref(false);
const deleteTarget = ref(null);
const deleteLoading = ref(false);
function askDelete(c) { deleteTarget.value = c; deleteOpen.value = true; }
async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleteLoading.value = true;
  try {
    await bulkActionCampaignsV2('delete', [deleteTarget.value.id]);
    deleteOpen.value = false; deleteTarget.value = null;
    await refresh(); toast.success('Sponsorluk silindi.');
  } catch (e) {
    const cap = extractCapacityError(e);
    toast.error(cap?.detail || e?.response?.data?.detail || 'Silme başarısız.');
  } finally { deleteLoading.value = false; }
}

// ─── Kiosklar sekmesi (atama özeti) ───────────────────────────────────────────
const assignedKiosks = ref([]);
const assignedLoading = ref(false);
async function loadAssignedKiosks(id) {
  assignedLoading.value = true;
  try {
    const { data } = await getCampaignKiosks(id);
    assignedKiosks.value = Array.isArray(data) ? data : (data?.results ?? []);
  } catch { assignedKiosks.value = []; } finally { assignedLoading.value = false; }
}

// Kiosklara Ata modalı
const assignOpen = ref(false);
const assignKiosksList = ref([]);
const assign = reactive({
  kiosk_ids: [],
  window_start: '08:00', window_end: '19:00', count: 10,
  weekdays: [], start_date: '', end_date: '',
});
const assignPreview = ref(null);
const assignLoading = ref(false);

const assignKioskOptions = computed(() =>
  assignKiosksList.value.map((k) => ({
    id: k.id,
    label: k.ad,
    sub: [k.eczane_adi, k.il_adi, k.ilce_adi].filter(Boolean).join(' / '),
  }))
);

async function openAssign() {
  assign.kiosk_ids = []; assign.weekdays = [];
  assign.window_start = '08:00'; assign.window_end = '19:00'; assign.count = 10;
  assign.start_date = ''; assign.end_date = '';
  assignPreview.value = null;
  assignOpen.value = true;
  if (!assignKiosksList.value.length) {
    try {
      const { data } = await listSponsorshipKiosks();
      assignKiosksList.value = Array.isArray(data) ? data : (data?.results ?? []);
    } catch { /* non-critical */ }
  }
}

function toggleAssignWeekday(v) {
  const i = assign.weekdays.indexOf(v);
  if (i >= 0) assign.weekdays.splice(i, 1); else assign.weekdays.push(v);
}

function buildAssignBody(dryRun) {
  return {
    kiosk_ids: assign.kiosk_ids.map(Number),
    window_start: assign.window_start,
    window_end: assign.window_end,
    count: Number(assign.count),
    active_weekdays: assign.weekdays.length ? [...assign.weekdays] : null,
    start_date: assign.start_date || null,
    end_date: assign.end_date || null,
    dry_run: dryRun,
  };
}

async function previewAssign() {
  if (!assign.kiosk_ids.length) { toast.warning('En az bir kiosk seçin.'); return; }
  assignLoading.value = true; assignPreview.value = null;
  try {
    const { data } = await assignKiosksToCampaign(editingId.value, buildAssignBody(true));
    assignPreview.value = data;
  } catch (e) {
    const cap = extractCapacityError(e);
    if (cap) assignPreview.value = { rejected: cap.rejected, skipped_already_assigned: cap.skipped, assigned: [], dry_run: true };
    else toast.error(e?.response?.data?.detail || 'Önizleme başarısız.');
  } finally { assignLoading.value = false; }
}

async function confirmAssign() {
  if (!assign.kiosk_ids.length) return;
  assignLoading.value = true;
  try {
    const { data } = await assignKiosksToCampaign(editingId.value, buildAssignBody(false));
    const n = (data.assigned || []).length;
    toast.success(`${n} kioska atandı.`);
    assignOpen.value = false;
    loadAssignedKiosks(editingId.value);
    await refresh();
  } catch (e) {
    const cap = extractCapacityError(e);
    if (cap) {
      assignPreview.value = { rejected: cap.rejected, skipped_already_assigned: cap.skipped, assigned: [], dry_run: false };
      toast.error(cap.detail);
    } else {
      toast.error(e?.response?.data?.detail || 'Atama başarısız.');
    }
  } finally { assignLoading.value = false; }
}

function kioskNameById(id) {
  const k = assignKiosksList.value.find((x) => String(x.id) === String(id));
  return k ? k.ad : `#${id}`;
}

onMounted(refresh);
</script>

<template>
  <div class="eisa-page">
    <div class="eisa-page-header">
      <div>
        <h1 class="eisa-page-title">Sponsorluk Tanımları</h1>
        <p class="eisa-page-subtitle">Sponsorluk kampanyalarını ve medyalarını tanımlayın; kiosklara buradan atayın.</p>
      </div>
      <button class="eisa-btn eisa-btn-cta" @click="openCreate">
        <i class="fa-solid fa-plus"></i> Yeni Sponsorluk
      </button>
    </div>

    <div class="sd-stats">
      <span class="sd-stat">Toplam <strong>{{ stats.total }}</strong></span>
      <span class="sd-stat">Aktif <strong>{{ stats.active }}</strong></span>
      <span class="sd-stat">Duraklatıldı <strong>{{ stats.paused }}</strong></span>
    </div>

    <div class="sd-toolbar">
      <div class="eisa-input-group" style="max-width:320px">
        <i class="fa-solid fa-magnifying-glass" style="padding:0 .6rem;color:#9CA3AF"></i>
        <input v-model="search" class="eisa-field" placeholder="Ad / reklam veren ara…" />
      </div>
      <select v-model="statusFilter" class="eisa-field" style="max-width:180px">
        <option value="ALL">Tüm durumlar</option>
        <option value="ACTIVE">Aktif</option>
        <option value="PAUSED">Duraklatıldı</option>
        <option value="COMPLETED">Tamamlandı</option>
      </select>
    </div>

    <div v-if="loading" class="eisa-empty">Yükleniyor…</div>
    <table v-else class="eisa-table">
      <thead>
        <tr>
          <th>Sponsorluk</th><th>Reklam Veren</th><th>Tarih</th>
          <th>Medya</th><th>Atanmış Kiosk</th><th>Durum</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in filtered" :key="c.id">
          <td><strong>{{ c.name }}</strong></td>
          <td>{{ c.advertiser_name || '—' }}</td>
          <td class="cell-muted">{{ (c.start_date || '').slice(0,10) }} → {{ (c.end_date || '').slice(0,10) }}</td>
          <td>{{ (c.creatives || []).length }}</td>
          <td>{{ c.assigned_kiosk_count ?? 0 }}</td>
          <td><span class="eisa-pill" :class="campStatus(c).cls">{{ campStatus(c).label }}</span></td>
          <td class="cell-actions">
            <button class="eisa-icon-btn" title="Düzenle" @click="openEdit(c)"><i class="fa-solid fa-pen"></i></button>
            <button class="eisa-icon-btn danger" title="Sil" @click="askDelete(c)"><i class="fa-solid fa-trash"></i></button>
          </td>
        </tr>
        <tr v-if="!filtered.length"><td colspan="7" class="eisa-empty">Sponsorluk bulunamadı.</td></tr>
      </tbody>
    </table>

    <!-- Drawer -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div v-if="drawerOpen" class="eisa-modal-backdrop" @click.self="close">
          <div class="eisa-modal eisa-modal--medium sd-drawer">
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">{{ editingId ? 'Sponsorluğu Düzenle' : 'Yeni Sponsorluk' }}</h3>
              <button class="eisa-modal-close" @click="close"><i class="fa-solid fa-xmark"></i></button>
            </div>

            <div class="sd-steps">
              <span v-for="(l, i) in STEP_LABELS" :key="i"
                class="sd-step" :class="{ 'sd-step--active': step === i+1, 'sd-step--done': step > i+1 }">
                {{ i+1 }}. {{ l }}
              </span>
            </div>

            <div class="eisa-modal-body">
              <!-- 1. Bilgiler -->
              <section v-if="step === 1">
                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">Sponsorluk adı</label>
                  <input v-model="form.name" class="eisa-field" placeholder="Örn. Bayer Yaz Kampanyası" />
                </div>
                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">Reklam veren</label>
                  <input v-model="form.advertiser_name" class="eisa-field" placeholder="Örn. Bayer İlaç" />
                </div>
                <div class="eisa-form-row eisa-form-row-full">
                  <DateRangePicker
                    :start="form.start_date" :end="form.end_date"
                    @update:start="(v) => form.start_date = v"
                    @update:end="(v) => form.end_date = v"
                  />
                </div>
                <div class="eisa-form-row eisa-form-row-full">
                  <label class="eisa-field-label">Durum</label>
                  <select v-model="form.status" class="eisa-field">
                    <option value="ACTIVE">Aktif</option>
                    <option value="PAUSED">Duraklatıldı</option>
                    <option value="COMPLETED">Tamamlandı</option>
                  </select>
                </div>
              </section>

              <!-- 2. Medya -->
              <section v-if="step === 2">
                <div class="sd-media-slot">
                  <div class="sd-media-head">
                    <span class="sd-media-label">Bekleme Ekranı Medyası</span>
                    <span class="sd-media-hint">Önerilen: 1080×1920 (9:16)</span>
                  </div>
                  <label v-if="!form.creatives.length" class="sd-upload">
                    <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickFile" :disabled="saving" />
                    <span><i class="fa-solid fa-cloud-arrow-up"></i> Dosya seç (max 100 MB)</span>
                  </label>
                  <div v-else class="sd-creative">
                    <div class="sd-preview">
                      <video v-if="isVideoUrl(form.creatives[0].media_url || form.creatives[0].uploaded_url)"
                        :src="form.creatives[0].media_url || form.creatives[0].uploaded_url" muted controls preload="metadata" />
                      <img v-else :src="form.creatives[0].media_url || form.creatives[0].uploaded_url"
                        alt="Bekleme medyası" @error="(e)=>e.target.style.display='none'" />
                    </div>
                    <div class="sd-cmeta">
                      <strong>{{ form.creatives[0].name }}</strong>
                      <label class="eisa-field-label">Ekran süresi
                        <select v-model.number="form.creatives[0].duration_seconds" class="eisa-field" :disabled="!!form.creatives[0].id">
                          <option :value="5">5 sn</option><option :value="10">10 sn</option>
                          <option :value="15">15 sn</option><option :value="30">30 sn</option><option :value="60">60 sn</option>
                        </select>
                      </label>
                    </div>
                    <button v-if="!form.creatives[0].id" class="eisa-icon-btn danger" @click="removeCreative(0)"><i class="fa-solid fa-trash"></i></button>
                  </div>
                </div>

                <div class="sd-media-slot" style="margin-top:1rem">
                  <div class="sd-media-head">
                    <span class="sd-media-label">İşlem Ekranı Medyası</span>
                    <span class="sd-media-hint">Önerilen: 1080×768 (yatay)</span>
                  </div>
                  <p class="cell-muted" style="font-size:.78rem;margin:.25rem 0 .5rem">
                    Kiosk kullanılırken alt şeritte gösterilir. Yüklenmezse bekleme görseli kullanılır.
                  </p>
                  <div v-if="form.creatives[0]?.active_media_url" class="sd-creative">
                    <div class="sd-preview">
                      <video v-if="isVideoUrl(form.creatives[0].active_media_url)" :src="form.creatives[0].active_media_url" muted controls preload="metadata" />
                      <img v-else :src="form.creatives[0].active_media_url" alt="İşlem medyası" @error="(e)=>e.target.style.display='none'" />
                    </div>
                    <div class="sd-cmeta"><strong>İşlem ekranı medyası</strong></div>
                    <button class="eisa-icon-btn danger" @click="removeActiveMedia"><i class="fa-solid fa-trash"></i></button>
                  </div>
                  <label v-else class="sd-upload" :class="{ 'sd-upload--disabled': !form.creatives.length }">
                    <input type="file" accept="image/*,video/mp4,video/webm" @change="onPickActiveFile" :disabled="saving || !form.creatives.length" />
                    <span><i class="fa-solid fa-cloud-arrow-up"></i> Dosya seç (yatay)</span>
                  </label>
                </div>
                <p v-if="saving" class="cell-muted" style="font-size:.8rem">Yükleniyor…</p>
              </section>

              <!-- 3. Kiosklar -->
              <section v-if="step === 3">
                <div class="sd-kiosk-head">
                  <h4 style="margin:0;font-size:.95rem">Atanmış Kiosklar</h4>
                  <button class="eisa-btn eisa-btn-cta" :disabled="!editingId" @click="openAssign">
                    <i class="fa-solid fa-plus"></i> Kiosklara Ata
                  </button>
                </div>
                <p v-if="!editingId" class="cell-muted" style="font-size:.8rem">Önce sponsorluğu kaydedin.</p>
                <div v-else-if="assignedLoading" class="eisa-empty">Yükleniyor…</div>
                <table v-else-if="assignedKiosks.length" class="eisa-table" style="font-size:.82rem">
                  <thead><tr><th>Kiosk</th><th>Eczane</th><th>Konum</th><th>Pencere</th><th>Sayı</th><th>Günler</th><th>Aktif</th></tr></thead>
                  <tbody>
                    <tr v-for="a in assignedKiosks" :key="a.id">
                      <td>{{ a.kiosk_name }}</td>
                      <td>{{ a.eczane_adi }}</td>
                      <td class="cell-muted">{{ [a.il_adi, a.ilce_adi].filter(Boolean).join(' / ') }}</td>
                      <td>{{ a.window_start }}–{{ a.window_end }}</td>
                      <td>{{ a.count }}</td>
                      <td>{{ weekdaysText(a.active_weekdays) }}</td>
                      <td><span class="eisa-pill" :class="a.is_active ? 'eisa-pill-success' : 'eisa-pill-muted'">{{ a.is_active ? 'Evet' : 'Hayır' }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <div v-else class="eisa-empty">Bu sponsorluk henüz hiçbir kioska atanmamış.</div>
              </section>

              <p v-if="stepError" class="sd-error"><i class="fa-solid fa-circle-exclamation"></i> {{ stepError }}</p>
            </div>

            <div class="eisa-modal-footer">
              <button v-if="step > 1" class="eisa-btn eisa-btn-ghost" @click="prevStep">Geri</button>
              <button v-if="step < 3" class="eisa-btn" @click="nextStep">İleri</button>
              <button class="eisa-btn eisa-btn-cta" :disabled="saving" @click="save">
                <i class="fa-solid fa-floppy-disk"></i> {{ saving ? 'Kaydediliyor…' : 'Kaydet' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Kiosklara Ata modalı -->
    <Teleport to="body">
      <Transition name="backdrop">
        <div v-if="assignOpen" class="eisa-modal-backdrop" @click.self="assignOpen = false">
          <div class="eisa-modal eisa-modal--medium">
            <div class="eisa-modal-header">
              <h3 class="eisa-modal-title">Kiosklara Ata</h3>
              <button class="eisa-modal-close" @click="assignOpen = false"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="eisa-modal-body">
              <label class="eisa-field-label">Kiosklar</label>
              <EisaMultiLookup v-model="assign.kiosk_ids" :options="assignKioskOptions" placeholder="Kiosk ara / seç…" />

              <div class="sd-assign-row">
                <label class="eisa-field-label">Başlangıç
                  <input type="time" v-model="assign.window_start" class="eisa-field" />
                </label>
                <label class="eisa-field-label">Bitiş
                  <input type="time" v-model="assign.window_end" class="eisa-field" />
                </label>
                <label class="eisa-field-label">Gösterim sayısı
                  <input type="number" min="1" v-model.number="assign.count" class="eisa-field" />
                </label>
              </div>

              <label class="eisa-field-label">Günler (opsiyonel)</label>
              <div class="ks-weekdays">
                <button v-for="w in WEEKDAYS" :key="w.value" type="button" class="ks-chip"
                  :class="{ 'ks-chip--on': assign.weekdays.includes(w.value) }" @click="toggleAssignWeekday(w.value)">{{ w.label }}</button>
              </div>

              <div class="sd-assign-row" style="margin-top:.75rem">
                <label class="eisa-field-label">Baş. tarih (ops.)
                  <input type="date" v-model="assign.start_date" class="eisa-field" />
                </label>
                <label class="eisa-field-label">Bit. tarih (ops.)
                  <input type="date" v-model="assign.end_date" class="eisa-field" />
                </label>
              </div>

              <div v-if="assignPreview" class="sd-assign-preview">
                <div v-if="assignPreview.assigned?.length" class="sd-assign-grp">
                  <strong class="diff-add">Atanacak ({{ assignPreview.assigned.length }}):</strong>
                  {{ assignPreview.assigned.map(kioskNameById).join(', ') }}
                </div>
                <div v-if="assignPreview.skipped_already_assigned?.length" class="sd-assign-grp">
                  <strong class="diff-keep">Zaten atanmış, atlanacak:</strong>
                  {{ assignPreview.skipped_already_assigned.map(kioskNameById).join(', ') }}
                </div>
                <div v-if="assignPreview.rejected?.length" class="sd-assign-grp">
                  <strong class="diff-rem">Reddedilen (kapasite):</strong>
                  <ul>
                    <li v-for="r in assignPreview.rejected" :key="r.kiosk_id">
                      {{ r.kiosk_name || kioskNameById(r.kiosk_id) }}
                      <span v-if="r.conflicts?.length" class="cell-muted">
                        — {{ r.conflicts.map(c => `${c.date}: ${c.placed}/${c.requested}`).join('; ') }}
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="eisa-modal-footer">
              <button class="eisa-btn" :disabled="assignLoading || !assign.kiosk_ids.length" @click="previewAssign">
                <i class="fa-solid fa-eye"></i> Önizle
              </button>
              <button class="eisa-btn eisa-btn-cta" :disabled="assignLoading || !assign.kiosk_ids.length" @click="confirmAssign">
                <i class="fa-solid fa-check"></i> Ata
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <EisaDeleteConfirm
      :open="deleteOpen"
      :loading="deleteLoading"
      title="Sponsorluğu Sil"
      :message="`'${deleteTarget?.name}' silinecek. Emin misiniz?`"
      @confirm="confirmDelete"
      @cancel="deleteOpen = false"
    />
  </div>
</template>

<style scoped>
.sd-stats { display: flex; gap: 1rem; margin-bottom: .75rem; }
.sd-stat { font-size: .85rem; color: #6B7280; }
.sd-toolbar { display: flex; gap: .75rem; margin-bottom: 1rem; flex-wrap: wrap; }
.eisa-empty { padding: 1.5rem; text-align: center; color: #6B7280; }

.sd-drawer { max-width: 720px; width: 95%; }
.sd-steps { display: flex; gap: .5rem; padding: .5rem 1.25rem; border-bottom: 1px solid #E5E7EB; }
.sd-step { font-size: .78rem; color: #9CA3AF; }
.sd-step--active { color: #B1121B; font-weight: 700; }
.sd-step--done { color: #059669; }
.sd-error { color: #B91C1C; font-size: .82rem; margin-top: .75rem; }

.sd-media-slot { border: 1px solid #E5E7EB; border-radius: 12px; padding: .9rem; }
.sd-media-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: .5rem; }
.sd-media-label { font-weight: 600; font-size: .85rem; }
.sd-media-hint { font-size: .72rem; color: #9CA3AF; }
.sd-upload { display: flex; align-items: center; justify-content: center; border: 2px dashed #D1D5DB; border-radius: 10px; padding: 1.25rem; cursor: pointer; color: #6B7280; font-size: .85rem; }
.sd-upload input { display: none; }
.sd-upload--disabled { opacity: .5; pointer-events: none; }
.sd-creative { display: flex; gap: .9rem; align-items: center; }
.sd-preview { width: 120px; height: 120px; border-radius: 8px; overflow: hidden; background: #F3F4F6; display: flex; align-items: center; justify-content: center; }
.sd-preview img, .sd-preview video { max-width: 100%; max-height: 100%; object-fit: contain; }
.sd-cmeta { flex: 1; display: flex; flex-direction: column; gap: .4rem; }

.sd-kiosk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: .75rem; }
.sd-assign-row { display: flex; gap: .75rem; margin-top: .75rem; flex-wrap: wrap; }
.sd-assign-row label { display: flex; flex-direction: column; gap: .2rem; font-size: .78rem; color: #4B5563; }
.sd-assign-preview { margin-top: 1rem; font-size: .82rem; background: #F9FAFB; border-radius: 10px; padding: .75rem; }
.sd-assign-grp { margin-bottom: .5rem; }
.sd-assign-grp ul { margin: .25rem 0 0; padding-left: 1.1rem; }
.diff-add { color: #059669; } .diff-rem { color: #B91C1C; } .diff-keep { color: #6B7280; }

.ks-weekdays { display: flex; flex-wrap: wrap; gap: .25rem; margin: .25rem 0; }
.ks-chip { border: 1px solid #D1D5DB; background: #fff; border-radius: 6px; padding: .18rem .4rem; font-size: .72rem; cursor: pointer; color: #6B7280; }
.ks-chip--on { background: #B1121B; color: #fff; border-color: #B1121B; }
</style>
