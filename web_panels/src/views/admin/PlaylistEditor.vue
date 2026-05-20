<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { toast } from 'vue-sonner';
import {
  listPlaylistTemplates, createPlaylistTemplate, updatePlaylistTemplate, deletePlaylistTemplate,
  listHourPlans, createHourPlan, updateHourPlan, deleteHourPlan,
  listDayPlans, createDayPlan, updateDayPlan, deleteDayPlan,
  listCampaignsV2, listCreatives,
  generatePlaylists, getGenerationJob,
  listKiosks, getIller, getIlceler,
} from '../../services/dooh.js';

// ─── Genel ───────────────────────────────────────────────────────────────────
const anaSecme = ref('loop');   // 'loop' | 'saat' | 'gun'

// ─── Sabitler ────────────────────────────────────────────────────────────────
const LOOP_SN = 60;
const SNAP_SN = 5;
const HP_DAK  = 60;
const HP_SNAP = 5;
const PALETTE = [
  '#B1121B','#ef4444','#22c55e','#f59e0b',
  '#8b5cf6','#ec4899','#14b8a6','#f97316',
  '#06b6d4','#84cc16','#e11d48','#7c3aed',
];
const SAAT_GRUPLARI = [
  { etiket: 'Gece',  saatler: [0,1,2,3,4,5]     },
  { etiket: 'Sabah', saatler: [6,7,8,9,10,11]    },
  { etiket: 'Öğle',  saatler: [12,13,14,15,16,17] },
  { etiket: 'Akşam', saatler: [18,19,20,21,22,23] },
];
const GRUP_RENKLERI = { 'Gece':'#6366f1','Sabah':'#f59e0b','Öğle':'#22c55e','Akşam':'#ef4444' };

// ═══════════════════════════════════════════════════════════════════════════
// TIER 1 — Loop (60s) Şablonları
// ═══════════════════════════════════════════════════════════════════════════
const sablonlar     = ref([]);
const aktifId       = ref(null);
const yukleniyor    = ref(false);
const kaydediyor    = ref(false);
const degisiklik    = ref(false);
const yenidenAdlan  = ref(false);
const altSekme      = ref('loop');   // 'loop' | 'saatler'
const yerelOgeler   = ref([]);
const kampanyalar   = ref([]);
const sagYukleniyor = ref(false);
const acikKampanya  = ref(null);
const kampanyaCreativeleri = ref({});
const ekleniyor     = ref(null);
const izRef         = ref(null);
let   surukleme     = null;
let   _lid          = 0;

const aktifSablon = computed(() => sablonlar.value.find(s => s.id === aktifId.value) ?? null);
const kullanilanSn = computed(() => yerelOgeler.value.reduce((t, o) => t + o.duration_seconds, 0));
const bosSn = computed(() => LOOP_SN - kullanilanSn.value);
const dolulukPct = computed(() => Math.min(100, (kullanilanSn.value / LOOP_SN) * 100));
const catismaVar = computed(() => {
  const s = [...yerelOgeler.value].sort((a, b) => a.offset_seconds - b.offset_seconds);
  for (let i = 0; i < s.length - 1; i++)
    if (s[i].offset_seconds + s[i].duration_seconds > s[i + 1].offset_seconds) return true;
  return false;
});
const izTiklari = Array.from({ length: LOOP_SN / SNAP_SN + 1 }, (_, i) => i * SNAP_SN);
const hedefSaatler = computed({
  get: () => aktifSablon.value?.target_hours ?? [],
  set: (v) => { if (aktifSablon.value) aktifSablon.value.target_hours = v; },
});
const gunPlani = computed(() => {
  const plan = {};
  for (const s of sablonlar.value)
    for (const saat of (s.target_hours ?? [])) plan[saat] = s;
  return plan;
});

function yenilid() { return ++_lid; }
function slotlariDonustur(slots) {
  return slots.map(s => ({
    _lid: yenilid(),
    campaign_id: s.campaign_id ?? null,
    creative_id: s.creative_id ?? null,
    offset_seconds: s.offset_seconds ?? 0,
    duration_seconds: s.duration_seconds,
    _etiket: s._etiket ?? 'Creative',
    _renk: s._renk ?? PALETTE[_lid % PALETTE.length],
  }));
}
function yerellerdenSlot(ogeler) {
  return ogeler.map(({ _lid: _l, _etiket: _e, _renk: _r, ...slot }) => slot);
}

async function sablonlariYukle() {
  yukleniyor.value = true;
  try {
    const { data } = await listPlaylistTemplates();
    sablonlar.value = Array.isArray(data) ? data : (data.results ?? []);
    if (sablonlar.value.length && !aktifId.value) sablonSec(sablonlar.value[0].id);
  } catch { toast.error('Şablonlar yüklenemedi.'); }
  finally { yukleniyor.value = false; }
}
function sablonSec(id) {
  if (degisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  aktifId.value = id; yenidenAdlan.value = false; degisiklik.value = false;
  const s = sablonlar.value.find(t => t.id === id);
  yerelOgeler.value = s ? slotlariDonustur(s.slots ?? []) : [];
}
async function yeniSablon() {
  if (degisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  kaydediyor.value = true;
  try {
    const { data } = await createPlaylistTemplate({ name: `Şablon ${sablonlar.value.length + 1}`, loop_duration_seconds: 60, slots: [], target_hours: [], description: '' });
    sablonlar.value.unshift(data); aktifId.value = data.id; yerelOgeler.value = []; degisiklik.value = false;
    nextTick(() => { yenidenAdlan.value = true; });
    toast.success('Yeni şablon oluşturuldu.');
  } catch { toast.error('Şablon oluşturulamadı.'); }
  finally { kaydediyor.value = false; }
}
async function sablonaKaydet() {
  if (!aktifSablon.value) return;
  kaydediyor.value = true;
  try {
    const istek = { name: aktifSablon.value.name, loop_duration_seconds: LOOP_SN, slots: yerellerdenSlot(yerelOgeler.value), target_hours: aktifSablon.value.target_hours ?? [], description: aktifSablon.value.description ?? '' };
    const { data } = await updatePlaylistTemplate(aktifSablon.value.id, istek);
    const i = sablonlar.value.findIndex(s => s.id === data.id);
    if (i !== -1) sablonlar.value[i] = data;
    degisiklik.value = false; toast.success('Şablon kaydedildi.');
  } catch (e) { toast.error('Kayıt hatası: ' + (e?.response?.data?.detail ?? e?.message ?? '')); }
  finally { kaydediyor.value = false; }
}
async function sablonuSil(id) {
  if (!confirm('Bu şablon silinsin mi?')) return;
  try {
    await deletePlaylistTemplate(id);
    sablonlar.value = sablonlar.value.filter(s => s.id !== id);
    if (aktifId.value === id) { aktifId.value = sablonlar.value[0]?.id ?? null; yerelOgeler.value = aktifId.value ? slotlariDonustur(sablonlar.value[0]?.slots ?? []) : []; degisiklik.value = false; }
    toast.success('Şablon silindi.');
  } catch { toast.error('Şablon silinemedi.'); }
}
function adlandirmaOnayla(yeniAd) {
  if (!aktifSablon.value || !yeniAd?.trim()) { yenidenAdlan.value = false; return; }
  aktifSablon.value.name = yeniAd.trim(); yenidenAdlan.value = false; degisiklik.value = true;
}
function saatiToggle(saat) {
  if (!aktifSablon.value) return;
  const mevcutlar = aktifSablon.value.target_hours ?? [];
  aktifSablon.value.target_hours = mevcutlar.includes(saat) ? mevcutlar.filter(s => s !== saat) : [...mevcutlar, saat].sort((a, b) => a - b);
  degisiklik.value = true;
}
function grubuToggle(grup) {
  if (!aktifSablon.value) return;
  const mevcutlar = aktifSablon.value.target_hours ?? [];
  const tumGrupta = grup.saatler.every(s => mevcutlar.includes(s));
  aktifSablon.value.target_hours = tumGrupta ? mevcutlar.filter(s => !grup.saatler.includes(s)) : [...new Set([...mevcutlar, ...grup.saatler])].sort((a, b) => a - b);
  degisiklik.value = true;
}
function gunPlaniCatisiyor(saat) {
  return gunPlani.value[saat] && gunPlani.value[saat].id !== aktifId.value;
}
// Timeline drag-drop (Loop)
function kampanyaRengi(kId) {
  const mevcut = yerelOgeler.value.find(o => o.campaign_id === kId);
  if (mevcut) return mevcut._renk;
  const kullanilanRenkler = [...new Set(yerelOgeler.value.map(o => o._renk))];
  return PALETTE.find(p => !kullanilanRenkler.includes(p)) ?? PALETTE[yerelOgeler.value.length % PALETTE.length];
}
function bosSlotBul(sure, baslangic = 0) {
  const sirali = [...yerelOgeler.value].sort((a, b) => a.offset_seconds - b.offset_seconds);
  let aday = Math.round(baslangic / SNAP_SN) * SNAP_SN;
  while (aday + sure <= LOOP_SN) {
    const catisma = sirali.find(o => aday < o.offset_seconds + o.duration_seconds && aday + sure > o.offset_seconds);
    if (!catisma) return aday;
    aday = Math.round((catisma.offset_seconds + catisma.duration_seconds) / SNAP_SN) * SNAP_SN;
  }
  return null;
}
function creativeEkle(kampanya, creative) {
  if (!aktifSablon.value) { toast.warning('Önce bir şablon seçin.'); return; }
  ekleniyor.value = creative.id;
  try {
    const sure = creative.duration_seconds ?? 15;
    const slot = bosSlotBul(sure);
    if (slot === null) { toast.warning('60 saniyelik döngüde yeterli yer yok.'); return; }
    yerelOgeler.value.push({ _lid: yenilid(), campaign_id: kampanya.id, creative_id: creative.id, offset_seconds: slot, duration_seconds: sure, _etiket: creative.name ?? kampanya.name, _renk: kampanyaRengi(kampanya.id) });
    degisiklik.value = true;
  } finally { ekleniyor.value = null; }
}
function ogeKaldir(oge) { yerelOgeler.value = yerelOgeler.value.filter(o => o._lid !== oge._lid); degisiklik.value = true; }
function timelineSifirla() { if (!confirm('Tüm öğeler kaldırılsın mı?')) return; yerelOgeler.value = []; degisiklik.value = true; }
function ogeStili(oge) { return { left: `${(oge.offset_seconds / LOOP_SN) * 100}%`, width: `${(oge.duration_seconds / LOOP_SN) * 100}%`, backgroundColor: oge._renk }; }
function suruklemeBasla(e, oge) {
  if (!izRef.value) return; e.preventDefault();
  const izRect = izRef.value.getBoundingClientRect();
  const tiklamaSn = (e.clientX - e.currentTarget.getBoundingClientRect().left) / (izRect.width / LOOP_SN);
  surukleme = { oge, tiklamaSn, izRect, pxPerSn: izRect.width / LOOP_SN };
}
function fareSurukleme(e) {
  if (!surukleme) return;
  const snapped = Math.round(((e.clientX - surukleme.izRect.left - surukleme.tiklamaSn * surukleme.pxPerSn) / surukleme.pxPerSn) / SNAP_SN) * SNAP_SN;
  surukleme.oge.offset_seconds = Math.max(0, Math.min(snapped, LOOP_SN - surukleme.oge.duration_seconds));
}
function fareBirak() { if (!surukleme) return; surukleme = null; degisiklik.value = true; }
function catisiyor(oge) {
  return yerelOgeler.value.some(d => d._lid !== oge._lid && oge.offset_seconds < d.offset_seconds + d.duration_seconds && oge.offset_seconds + oge.duration_seconds > d.offset_seconds);
}
async function sagPanelYukle() {
  sagYukleniyor.value = true;
  try { const { data } = await listCampaignsV2({ status: 'ACTIVE', page_size: 200 }); kampanyalar.value = data?.results ?? data ?? []; }
  catch { toast.error('Kampanyalar yüklenemedi.'); }
  finally { sagYukleniyor.value = false; }
}
async function kampanyayiGenislet(k) {
  if (acikKampanya.value === k.id) { acikKampanya.value = null; return; }
  acikKampanya.value = k.id;
  if (!kampanyaCreativeleri.value[k.id]) {
    try { const { data } = await listCreatives({ campaign: k.id }); kampanyaCreativeleri.value[k.id] = data?.results ?? data ?? []; }
    catch { kampanyaCreativeleri.value[k.id] = []; }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TIER 2 — HourPlan (Saatlik Plan)
// ═══════════════════════════════════════════════════════════════════════════
const hourPlanlar    = ref([]);
const aktifHpId      = ref(null);
const hpYukleniyor   = ref(false);
const hpKaydediyor   = ref(false);
const hpDegisiklik   = ref(false);
const hpYeniAdlan    = ref(false);
const hpYerelSlotlar = ref([]);
const izHpRef        = ref(null);
let   hpSurukleme    = null;
let   _hpLid         = 0;

const hpTiklari = Array.from({ length: HP_DAK / HP_SNAP + 1 }, (_, i) => i * HP_SNAP);
const aktifHp = computed(() => hourPlanlar.value.find(h => h.id === aktifHpId.value) ?? null);
const hpKullanilanDak = computed(() => hpYerelSlotlar.value.reduce((t, s) => t + s.duration_minutes, 0));
const hpBosDak = computed(() => HP_DAK - hpKullanilanDak.value);
const hpDolulukPct = computed(() => Math.min(100, (hpKullanilanDak.value / HP_DAK) * 100));
const hpCatismaVar = computed(() => {
  const s = [...hpYerelSlotlar.value].sort((a, b) => a.offset_minutes - b.offset_minutes);
  for (let i = 0; i < s.length - 1; i++)
    if (s[i].offset_minutes + s[i].duration_minutes > s[i + 1].offset_minutes) return true;
  return false;
});

function yeniHpLid() { return ++_hpLid; }
function hpSlotlariDonustur(slots) {
  return slots.map(s => {
    const tpl = sablonlar.value.find(t => t.id === s.loop_template_id);
    return { _hpLid: yeniHpLid(), offset_minutes: s.offset_minutes ?? 0, duration_minutes: s.duration_minutes ?? HP_SNAP, loop_template_id: s.loop_template_id, _etiket: tpl?.name ?? 'Loop', _renk: PALETTE[_hpLid % PALETTE.length] };
  });
}
function hpYerellerdenSlot(slots) {
  return slots.map(({ _hpLid: _, _etiket: _e, _renk: _r, ...s }) => s);
}

async function hourPlanlariYukle() {
  hpYukleniyor.value = true;
  try {
    const { data } = await listHourPlans();
    hourPlanlar.value = Array.isArray(data) ? data : (data.results ?? []);
    if (hourPlanlar.value.length && !aktifHpId.value) hpSec(hourPlanlar.value[0].id);
  } catch { toast.error('Saatlik planlar yüklenemedi.'); }
  finally { hpYukleniyor.value = false; }
}
function hpSec(id) {
  if (hpDegisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  aktifHpId.value = id; hpYeniAdlan.value = false; hpDegisiklik.value = false;
  const h = hourPlanlar.value.find(x => x.id === id);
  hpYerelSlotlar.value = h ? hpSlotlariDonustur(h.slots ?? []) : [];
}
async function yeniHourPlan() {
  if (hpDegisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  hpKaydediyor.value = true;
  try {
    const { data } = await createHourPlan({ name: `Saatlik Plan ${hourPlanlar.value.length + 1}`, slots: [], description: '' });
    hourPlanlar.value.unshift(data); hpSec(data.id);
    nextTick(() => { hpYeniAdlan.value = true; });
    toast.success('Yeni saatlik plan oluşturuldu.');
  } catch { toast.error('Saatlik plan oluşturulamadı.'); }
  finally { hpKaydediyor.value = false; }
}
async function hpKaydet() {
  if (!aktifHp.value) return;
  hpKaydediyor.value = true;
  try {
    const istek = { name: aktifHp.value.name, description: aktifHp.value.description ?? '', slots: hpYerellerdenSlot(hpYerelSlotlar.value) };
    const { data } = await updateHourPlan(aktifHp.value.id, istek);
    const i = hourPlanlar.value.findIndex(h => h.id === data.id);
    if (i !== -1) hourPlanlar.value[i] = data;
    hpDegisiklik.value = false; toast.success('Saatlik plan kaydedildi.');
  } catch (e) { toast.error('Kayıt hatası: ' + (e?.response?.data?.detail ?? e?.message ?? '')); }
  finally { hpKaydediyor.value = false; }
}
async function hpSil(id) {
  if (!confirm('Bu saatlik plan silinsin mi?')) return;
  try {
    await deleteHourPlan(id);
    hourPlanlar.value = hourPlanlar.value.filter(h => h.id !== id);
    if (aktifHpId.value === id) { aktifHpId.value = hourPlanlar.value[0]?.id ?? null; hpYerelSlotlar.value = aktifHpId.value ? hpSlotlariDonustur(hourPlanlar.value[0]?.slots ?? []) : []; hpDegisiklik.value = false; }
    toast.success('Saatlik plan silindi.');
  } catch { toast.error('Saatlik plan silinemedi.'); }
}
function hpAdlandirmaOnayla(yeniAd) {
  if (!aktifHp.value || !yeniAd?.trim()) { hpYeniAdlan.value = false; return; }
  aktifHp.value.name = yeniAd.trim(); hpYeniAdlan.value = false; hpDegisiklik.value = true;
}
// HourPlan timeline drag-drop
function hpOgeStili(slot) {
  return { left: `${(slot.offset_minutes / HP_DAK) * 100}%`, width: `${(slot.duration_minutes / HP_DAK) * 100}%`, backgroundColor: slot._renk };
}
function hpBosSlotBul(sure) {
  const sirali = [...hpYerelSlotlar.value].sort((a, b) => a.offset_minutes - b.offset_minutes);
  let aday = 0;
  while (aday + sure <= HP_DAK) {
    const catisma = sirali.find(o => aday < o.offset_minutes + o.duration_minutes && aday + sure > o.offset_minutes);
    if (!catisma) return aday;
    aday = Math.round((catisma.offset_minutes + catisma.duration_minutes) / HP_SNAP) * HP_SNAP;
  }
  return null;
}
function loopSablonuEkle(sablon) {
  if (!aktifHp.value) { toast.warning('Önce bir saatlik plan seçin.'); return; }
  const slot = hpBosSlotBul(HP_SNAP);
  if (slot === null) { toast.warning('60 dakikalık planda yeterli yer yok.'); return; }
  hpYerelSlotlar.value.push({ _hpLid: yeniHpLid(), offset_minutes: slot, duration_minutes: HP_SNAP, loop_template_id: sablon.id, _etiket: sablon.name, _renk: PALETTE[_hpLid % PALETTE.length] });
  hpDegisiklik.value = true;
}
function hpOgeKaldir(slot) { hpYerelSlotlar.value = hpYerelSlotlar.value.filter(s => s._hpLid !== slot._hpLid); hpDegisiklik.value = true; }
function hpSureGuncelle(slot, yeniSure) {
  const sure = Math.max(HP_SNAP, Math.round(parseInt(yeniSure) / HP_SNAP) * HP_SNAP);
  slot.duration_minutes = Math.min(sure, HP_DAK - slot.offset_minutes);
  hpDegisiklik.value = true;
}
function hpCatisiyor(slot) {
  return hpYerelSlotlar.value.some(d => d._hpLid !== slot._hpLid && slot.offset_minutes < d.offset_minutes + d.duration_minutes && slot.offset_minutes + slot.duration_minutes > d.offset_minutes);
}
function hpSuruklemeBasla(e, slot) {
  if (!izHpRef.value) return; e.preventDefault();
  const izRect = izHpRef.value.getBoundingClientRect();
  const tiklamaDak = (e.clientX - e.currentTarget.getBoundingClientRect().left) / (izRect.width / HP_DAK);
  hpSurukleme = { slot, tiklamaDak, izRect, pxPerDak: izRect.width / HP_DAK };
}
function fareSuruklemeHp(e) {
  if (!hpSurukleme) return;
  const snapped = Math.round(((e.clientX - hpSurukleme.izRect.left - hpSurukleme.tiklamaDak * hpSurukleme.pxPerDak) / hpSurukleme.pxPerDak) / HP_SNAP) * HP_SNAP;
  hpSurukleme.slot.offset_minutes = Math.max(0, Math.min(snapped, HP_DAK - hpSurukleme.slot.duration_minutes));
}
function fareBirakHp() { if (!hpSurukleme) return; hpSurukleme = null; hpDegisiklik.value = true; }

// ═══════════════════════════════════════════════════════════════════════════
// TIER 3 — DayPlan (Günlük Plan)
// ═══════════════════════════════════════════════════════════════════════════
const dayPlanlar     = ref([]);
const aktifDpId      = ref(null);
const dpYukleniyor   = ref(false);
const dpKaydediyor   = ref(false);
const dpDegisiklik   = ref(false);
const dpYeniAdlan    = ref(false);
const dpYerelSlotlar = ref([]);   // [{hour, hour_plan_id}]
const seciliHpId     = ref(null); // sağdan seçili HourPlan (atama için)

const aktifDp = computed(() => dayPlanlar.value.find(d => d.id === aktifDpId.value) ?? null);
const dpSaatAtamasi = computed(() => {
  const map = {};
  for (const slot of dpYerelSlotlar.value) map[slot.hour] = slot.hour_plan_id;
  return map;
});

async function dayPlanlariYukle() {
  dpYukleniyor.value = true;
  try {
    const { data } = await listDayPlans();
    dayPlanlar.value = Array.isArray(data) ? data : (data.results ?? []);
    if (dayPlanlar.value.length && !aktifDpId.value) dpSec(dayPlanlar.value[0].id);
  } catch { toast.error('Günlük planlar yüklenemedi.'); }
  finally { dpYukleniyor.value = false; }
}
function dpSec(id) {
  if (dpDegisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  aktifDpId.value = id; dpYeniAdlan.value = false; dpDegisiklik.value = false;
  const d = dayPlanlar.value.find(x => x.id === id);
  dpYerelSlotlar.value = d ? [...(d.slots ?? [])] : [];
}
async function yeniDayPlan() {
  if (dpDegisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  dpKaydediyor.value = true;
  try {
    const { data } = await createDayPlan({ name: `Günlük Plan ${dayPlanlar.value.length + 1}`, slots: [], description: '' });
    dayPlanlar.value.unshift(data); dpSec(data.id);
    nextTick(() => { dpYeniAdlan.value = true; });
    toast.success('Yeni günlük plan oluşturuldu.');
  } catch { toast.error('Günlük plan oluşturulamadı.'); }
  finally { dpKaydediyor.value = false; }
}
async function dpKaydet() {
  if (!aktifDp.value) return;
  dpKaydediyor.value = true;
  try {
    const istek = { name: aktifDp.value.name, description: aktifDp.value.description ?? '', slots: dpYerelSlotlar.value.map(({ hour, hour_plan_id }) => ({ hour, hour_plan_id })) };
    const { data } = await updateDayPlan(aktifDp.value.id, istek);
    const i = dayPlanlar.value.findIndex(d => d.id === data.id);
    if (i !== -1) dayPlanlar.value[i] = data;
    dpDegisiklik.value = false; toast.success('Günlük plan kaydedildi.');
  } catch (e) { toast.error('Kayıt hatası: ' + (e?.response?.data?.detail ?? e?.message ?? '')); }
  finally { dpKaydediyor.value = false; }
}
async function dpSil(id) {
  if (!confirm('Bu günlük plan silinsin mi?')) return;
  try {
    await deleteDayPlan(id);
    dayPlanlar.value = dayPlanlar.value.filter(d => d.id !== id);
    if (aktifDpId.value === id) { aktifDpId.value = dayPlanlar.value[0]?.id ?? null; dpYerelSlotlar.value = aktifDpId.value ? [...(dayPlanlar.value[0]?.slots ?? [])] : []; dpDegisiklik.value = false; }
    toast.success('Günlük plan silindi.');
  } catch { toast.error('Günlük plan silinemedi.'); }
}
function dpAdlandirmaOnayla(yeniAd) {
  if (!aktifDp.value || !yeniAd?.trim()) { dpYeniAdlan.value = false; return; }
  aktifDp.value.name = yeniAd.trim(); dpYeniAdlan.value = false; dpDegisiklik.value = true;
}
function dpSaatAta(saat) {
  if (!aktifDp.value) { toast.warning('Önce bir günlük plan seçin.'); return; }
  if (!seciliHpId.value) { toast.warning('Önce sağ panelden bir saatlik plan seçin.'); return; }
  const mevcut = dpYerelSlotlar.value.findIndex(s => s.hour === saat);
  if (mevcut !== -1) dpYerelSlotlar.value[mevcut] = { hour: saat, hour_plan_id: seciliHpId.value };
  else dpYerelSlotlar.value.push({ hour: saat, hour_plan_id: seciliHpId.value });
  dpDegisiklik.value = true;
}
function dpSaatTemizle(saat) { dpYerelSlotlar.value = dpYerelSlotlar.value.filter(s => s.hour !== saat); dpDegisiklik.value = true; }
function dpSaatHpAdi(saat) { const hpId = dpSaatAtamasi.value[saat]; if (!hpId) return null; return hourPlanlar.value.find(h => h.id === hpId)?.name ?? '?'; }
function dpSaatHpRenk(saat) { const hpId = dpSaatAtamasi.value[saat]; if (!hpId) return null; const idx = hourPlanlar.value.findIndex(h => h.id === hpId); return PALETTE[Math.max(0, idx) % PALETTE.length]; }

// ═══════════════════════════════════════════════════════════════════════════
// Kiosk Hedefleme + Üretim
// ═══════════════════════════════════════════════════════════════════════════
const uretimTarihi    = ref(new Date().toISOString().slice(0, 10));
const hedefKapsam     = ref('all');
const hedefIlId       = ref(null);
const hedefIlceId     = ref(null);
const seciliKiosklar  = ref([]);
const uretiliyor      = ref(false);
const aktifIs         = ref(null);
const iller           = ref([]);
const ilceler         = ref([]);
const kiosklar        = ref([]);
const kioskYukleniyor = ref(false);
let   _isAnketi       = null;

const kapsamiKioskSayisi = computed(() => {
  if (hedefKapsam.value === 'all')   return kiosklar.value.length;
  if (hedefKapsam.value === 'il')    return kiosklar.value.filter(k => k.il_id === hedefIlId.value).length;
  if (hedefKapsam.value === 'ilce')  return kiosklar.value.filter(k => k.ilce_id === hedefIlceId.value).length;
  return seciliKiosklar.value.length;
});

async function kioskTargetingYukle() {
  kioskYukleniyor.value = true;
  try {
    const [ilRes, kRes] = await Promise.all([getIller(), listKiosks({ aktif: true, page_size: 500 })]);
    iller.value = ilRes;
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
  seciliKiosklar.value = seciliKiosklar.value.includes(id) ? seciliKiosklar.value.filter(k => k !== id) : [...seciliKiosklar.value, id];
}
function gorunenKiosklar() {
  if (hedefKapsam.value === 'il'    && hedefIlId.value)   return kiosklar.value.filter(k => k.il_id    === hedefIlId.value);
  if (hedefKapsam.value === 'ilce'  && hedefIlceId.value) return kiosklar.value.filter(k => k.ilce_id  === hedefIlceId.value);
  if (hedefKapsam.value === 'kiosks') return kiosklar.value;
  return [];
}
async function uretimBaslat() {
  if (!aktifDp.value) { toast.warning('Önce bir günlük plan seçin.'); return; }
  if (dpDegisiklik.value && !confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?')) return;
  uretiliyor.value = true;
  try {
    const istek = { date: uretimTarihi.value, day_plan_id: aktifDpId.value, scope: hedefKapsam.value };
    if (hedefKapsam.value === 'il'    && hedefIlId.value)        istek.il_id     = hedefIlId.value;
    if (hedefKapsam.value === 'ilce'  && hedefIlceId.value)      istek.ilce_id   = hedefIlceId.value;
    if (hedefKapsam.value === 'kiosks' && seciliKiosklar.value.length) istek.kiosk_ids = seciliKiosklar.value;
    const { data } = await generatePlaylists(istek);
    toast.success(`Üretim başlatıldı (${data.total_kiosks} kiosk)`);
    isAnketle(data.job_id);
  } catch (e) { toast.error('Üretim başlatılamadı: ' + (e?.response?.data?.error ?? e?.message ?? '')); }
  finally { uretiliyor.value = false; }
}
function isAnketle(isId) {
  if (_isAnketi) clearInterval(_isAnketi);
  _isAnketi = setInterval(async () => {
    try {
      const { data } = await getGenerationJob(isId);
      aktifIs.value = data;
      if (data.status === 'DONE' || data.status === 'FAILED') {
        clearInterval(_isAnketi); _isAnketi = null;
        if (data.status === 'DONE') toast.success(`Tamamlandı — ${data.playlists_generated} playlist üretildi.`);
        else toast.error('Üretim başarısız oldu.');
      }
    } catch { clearInterval(_isAnketi); }
  }, 2500);
}

// ═══════════════════════════════════════════════════════════════════════════
// Lifecycle
// ═══════════════════════════════════════════════════════════════════════════
onMounted(() => {
  sablonlariYukle();
  sagPanelYukle();
  kioskTargetingYukle();
  hourPlanlariYukle();
  dayPlanlariYukle();
});

function _mousemove(e) { fareSurukleme(e); fareSuruklemeHp(e); }
function _mouseup()    { fareBirak(); fareBirakHp(); }
document.addEventListener('mousemove', _mousemove);
document.addEventListener('mouseup',   _mouseup);
onUnmounted(() => {
  document.removeEventListener('mousemove', _mousemove);
  document.removeEventListener('mouseup',   _mouseup);
  if (_isAnketi) clearInterval(_isAnketi);
});
</script>

<template>
  <div class="pe-sayfa-kapsam">

    <!-- ════ ÜST SEKME ÇUBUĞU ══════════════════════════════════════════ -->
    <div class="pe-ust-sekme-bar">
      <button class="ust-sekme" :class="{ aktif: anaSecme === 'loop' }" @click="anaSecme = 'loop'">
        <i class="fa-solid fa-circle-play"></i> Loop (60s)
      </button>
      <button class="ust-sekme" :class="{ aktif: anaSecme === 'saat' }" @click="anaSecme = 'saat'">
        <i class="fa-solid fa-clock"></i> Saatlik Plan
      </button>
      <button class="ust-sekme" :class="{ aktif: anaSecme === 'gun' }" @click="anaSecme = 'gun'">
        <i class="fa-solid fa-calendar-days"></i> Günlük Plan
      </button>
    </div>

    <!-- ════ İÇERİK ════════════════════════════════════════════════════ -->
    <div class="pe-sayfa">

      <!-- ══════════ TAB: LOOP (60s) ══════════════════════════════════ -->
      <template v-if="anaSecme === 'loop'">
        <!-- SOL -->
        <aside class="pe-sol">
          <div class="pe-panel-ust">
            <span class="pe-panel-baslik"><i class="fa-solid fa-layer-group"></i> Loop Şablonları</span>
            <button class="eisa-btn eisa-btn-cta ufak" :disabled="kaydediyor" @click="yeniSablon"><i class="fa-solid fa-plus"></i></button>
          </div>
          <div v-if="yukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-liste">
            <div v-if="!sablonlar.length" class="pe-bos-ipucu">Henüz şablon yok.</div>
            <div v-for="s in sablonlar" :key="s.id" class="pe-liste-ogesi" :class="{ aktif: s.id === aktifId }" @click="sablonSec(s.id)">
              <span class="pe-saat-renk-serit">
                <span v-for="g in SAAT_GRUPLARI" :key="g.etiket" class="serit-dilim" :class="{ aktif: (s.target_hours ?? []).some(h => g.saatler.includes(h)) }" :style="{ background: GRUP_RENKLERI[g.etiket] }"></span>
              </span>
              <span class="pe-liste-adi">{{ s.name }}</span>
              <button class="pe-sil-btn" @click.stop="sablonuSil(s.id)"><i class="fa-solid fa-trash-can"></i></button>
            </div>
          </div>
        </aside>

        <!-- ORTA -->
        <main class="pe-orta">
          <div v-if="!aktifSablon" class="pe-bos-alan">
            <i class="fa-solid fa-film fa-3x"></i>
            <p>Sol panelden bir şablon seçin ya da <strong>+</strong> ile oluşturun.</p>
          </div>
          <template v-else>
            <div class="pe-orta-ust">
              <div class="pe-ad-satiri">
                <template v-if="yenidenAdlan">
                  <input class="eisa-field pe-ad-input" :value="aktifSablon.name" @keyup.enter="e => adlandirmaOnayla(e.target.value)" @blur="e => adlandirmaOnayla(e.target.value)" autofocus />
                </template>
                <template v-else>
                  <h2 class="pe-ad" @dblclick="yenidenAdlan = true">{{ aktifSablon.name }}<span v-if="degisiklik" class="degisiklik-nok">●</span></h2>
                  <button class="ikon-btn" @click="yenidenAdlan = true"><i class="fa-solid fa-pencil"></i></button>
                </template>
              </div>
              <div class="pe-orta-eylemler">
                <span class="kapasite-rozet" :class="{ uyari: kullanilanSn > 45, dolu: kullanilanSn >= 60 }">
                  <i class="fa-solid fa-clock"></i> {{ kullanilanSn }}s / {{ LOOP_SN }}s
                </span>
                <button v-if="yerelOgeler.length" class="eisa-btn eisa-btn-ghost ufak" @click="timelineSifirla"><i class="fa-solid fa-broom"></i></button>
                <button class="eisa-btn eisa-btn-cta ufak" :disabled="kaydediyor || !degisiklik" @click="sablonaKaydet">
                  <i class="fa-solid" :class="kaydediyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i>
                  {{ kaydediyor ? 'Kaydediliyor…' : 'Kaydet' }}
                </button>
              </div>
            </div>
            <!-- Alt sekmeler -->
            <div class="pe-sekmeler">
              <button class="pe-sekme" :class="{ aktif: altSekme === 'loop' }" @click="altSekme = 'loop'"><i class="fa-solid fa-circle-play"></i> Loop Düzenle</button>
              <button class="pe-sekme" :class="{ aktif: altSekme === 'saatler' }" @click="altSekme = 'saatler'"><i class="fa-solid fa-calendar-day"></i> Hedef Saatler</button>
            </div>

            <!-- Loop düzenleme -->
            <div v-if="altSekme === 'loop'">
              <div class="dolubar-kapsam">
                <div class="dolubar" :class="{ uyari: kullanilanSn > 45, dolu: kullanilanSn >= 60 }" :style="{ width: dolulukPct + '%' }"></div>
                <span class="dolubar-etiket">{{ bosSn >= 0 ? bosSn + 's boş' : Math.abs(bosSn) + 's taşma' }}</span>
              </div>
              <div v-if="catismaVar" class="catisma-uyari"><i class="fa-solid fa-triangle-exclamation"></i> Çakışan bloklar var.</div>
              <div class="iz-kapsam">
                <div class="tiklar">
                  <span v-for="t in izTiklari" :key="t" class="tik" :style="{ left: (t/LOOP_SN*100)+'%' }">{{ t }}s</span>
                </div>
                <div ref="izRef" class="iz">
                  <div v-for="t in izTiklari" :key="'g'+t" class="iz-cizgi" :style="{ left: (t/LOOP_SN*100)+'%' }"></div>
                  <div v-for="oge in yerelOgeler" :key="oge._lid" class="iz-oge" :class="{ catisiyor: catisiyor(oge) }" :style="ogeStili(oge)" :title="`${oge._etiket} — ${oge.duration_seconds}s @ ${oge.offset_seconds}s`" @mousedown.prevent="suruklemeBasla($event, oge)" @dblclick.stop="ogeKaldir(oge)">
                    <span class="iz-oge-adi">{{ oge._etiket }}</span>
                    <span class="iz-oge-sure">{{ oge.duration_seconds }}s</span>
                    <button class="iz-oge-kaldir" @mousedown.stop @click.stop="ogeKaldir(oge)">×</button>
                  </div>
                </div>
                <p class="iz-ipucu soluk kucuk">Sürükle → taşı &nbsp;|&nbsp; Çift tıkla / × → kaldır</p>
              </div>
              <div v-if="yerelOgeler.length" class="legand">
                <div v-for="oge in [...yerelOgeler].sort((a,b) => a.offset_seconds - b.offset_seconds)" :key="oge._lid" class="legand-satir">
                  <span class="legand-renk" :style="{ background: oge._renk }"></span>
                  <span class="soluk kucuk">{{ oge.offset_seconds }}s</span>
                  <span class="legand-adi">{{ oge._etiket }}</span>
                  <span class="soluk kucuk">{{ oge.duration_seconds }}s</span>
                </div>
              </div>
              <div v-else class="pe-bos-ipucu" style="margin-top:1rem">Sağ panelden kampanya creative'i ekleyin.</div>
            </div>

            <!-- Hedef saatler -->
            <div v-if="altSekme === 'saatler'" class="saat-kismi">
              <p class="soluk kucuk" style="margin-bottom:.75rem">Bu şablon hangi saatlerde aktif olacak?</p>
              <div v-for="grup in SAAT_GRUPLARI" :key="grup.etiket" class="saat-grubu">
                <div class="saat-grubu-ust" @click="grubuToggle(grup)">
                  <span class="saat-grubu-renk" :style="{ background: GRUP_RENKLERI[grup.etiket] }"></span>
                  <span class="saat-grubu-adi">{{ grup.etiket }}</span>
                  <span class="soluk kucuk">({{ grup.saatler[0] }}:00–{{ grup.saatler[grup.saatler.length-1] }}:59)</span>
                  <span class="saat-grubu-isaretci" :class="{ aktif: grup.saatler.every(s => hedefSaatler.includes(s)) }"><i class="fa-solid fa-check"></i></span>
                </div>
                <div class="saat-kutucuklar">
                  <button v-for="saat in grup.saatler" :key="saat" class="saat-kutu" :class="{ aktif: hedefSaatler.includes(saat), catisan: gunPlaniCatisiyor(saat) }" :style="hedefSaatler.includes(saat) ? { background: GRUP_RENKLERI[grup.etiket], borderColor: GRUP_RENKLERI[grup.etiket] } : {}" @click="saatiToggle(saat)">{{ saat }}</button>
                </div>
              </div>
              <div class="secili-saatler-ozet" v-if="hedefSaatler.length"><i class="fa-solid fa-check-circle" style="color:#22c55e"></i> {{ hedefSaatler.length }} saat seçili</div>
              <div v-else class="pe-bos-ipucu">Hiçbir saat seçilmedi.</div>
            </div>
          </template>
        </main>

        <!-- SAĞ -->
        <aside class="pe-sag">
          <div class="pe-panel-ust"><span class="pe-panel-baslik"><i class="fa-solid fa-bullhorn"></i> Kampanyalar</span></div>
          <div v-if="sagYukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-sag-liste">
            <div v-if="!kampanyalar.length" class="pe-bos-ipucu">Aktif kampanya yok.</div>
            <div v-for="k in kampanyalar" :key="k.id" class="kamp-kart">
              <div class="kamp-ust" @click="kampanyayiGenislet(k)">
                <span class="kamp-renk-nokta" :style="{ background: kampanyaRengi(k.id) }"></span>
                <div class="kamp-bilgi"><div class="kamp-adi">{{ k.name }}</div><div class="soluk kucuk">{{ k.start_date?.slice(0,10) }} → {{ k.end_date?.slice(0,10) }}</div></div>
                <i class="fa-solid fa-chevron-right genislet-ikon" :class="{ donmus: acikKampanya === k.id }"></i>
              </div>
              <div v-if="acikKampanya === k.id" class="creative-liste">
                <div v-if="!kampanyaCreativeleri[k.id]" class="pe-yukleniyor kucuk"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
                <div v-else-if="!kampanyaCreativeleri[k.id].length" class="pe-bos-ipucu kucuk">Creative bulunamadı.</div>
                <div v-for="cr in kampanyaCreativeleri[k.id]" :key="cr.id" class="creative-satir">
                  <span class="soluk kucuk">{{ cr.duration_seconds }}s</span>
                  <span class="creative-adi kucuk">{{ cr.name ?? cr.media_url?.split('/').pop() }}</span>
                  <button class="eisa-btn eisa-btn-cta mikro" :disabled="!aktifSablon || ekleniyor === cr.id" @click="creativeEkle(k, cr)">
                    <i class="fa-solid" :class="ekleniyor===cr.id ? 'fa-circle-notch fa-spin' : 'fa-plus'"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </template>

      <!-- ══════════ TAB: SAATLİK PLAN ════════════════════════════════ -->
      <template v-if="anaSecme === 'saat'">
        <!-- SOL -->
        <aside class="pe-sol">
          <div class="pe-panel-ust">
            <span class="pe-panel-baslik"><i class="fa-solid fa-clock"></i> Saatlik Planlar</span>
            <button class="eisa-btn eisa-btn-cta ufak" :disabled="hpKaydediyor" @click="yeniHourPlan"><i class="fa-solid fa-plus"></i></button>
          </div>
          <div v-if="hpYukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-liste">
            <div v-if="!hourPlanlar.length" class="pe-bos-ipucu">Henüz saatlik plan yok.</div>
            <div v-for="h in hourPlanlar" :key="h.id" class="pe-liste-ogesi" :class="{ aktif: h.id === aktifHpId }" @click="hpSec(h.id)">
              <span class="hp-slot-sayisi soluk kucuk">{{ (h.slots??[]).length }} slot</span>
              <span class="pe-liste-adi">{{ h.name }}</span>
              <button class="pe-sil-btn" @click.stop="hpSil(h.id)"><i class="fa-solid fa-trash-can"></i></button>
            </div>
          </div>
        </aside>

        <!-- ORTA -->
        <main class="pe-orta">
          <div v-if="!aktifHp" class="pe-bos-alan">
            <i class="fa-solid fa-clock fa-3x"></i>
            <p>Sol panelden bir saatlik plan seçin ya da <strong>+</strong> ile oluşturun.</p>
          </div>
          <template v-else>
            <div class="pe-orta-ust">
              <div class="pe-ad-satiri">
                <template v-if="hpYeniAdlan">
                  <input class="eisa-field pe-ad-input" :value="aktifHp.name" @keyup.enter="e => hpAdlandirmaOnayla(e.target.value)" @blur="e => hpAdlandirmaOnayla(e.target.value)" autofocus />
                </template>
                <template v-else>
                  <h2 class="pe-ad" @dblclick="hpYeniAdlan = true">{{ aktifHp.name }}<span v-if="hpDegisiklik" class="degisiklik-nok">●</span></h2>
                  <button class="ikon-btn" @click="hpYeniAdlan = true"><i class="fa-solid fa-pencil"></i></button>
                </template>
              </div>
              <div class="pe-orta-eylemler">
                <span class="kapasite-rozet" :class="{ uyari: hpKullanilanDak > 45, dolu: hpKullanilanDak >= 60 }">
                  <i class="fa-solid fa-clock"></i> {{ hpKullanilanDak }}dk / {{ HP_DAK }}dk
                </span>
                <button class="eisa-btn eisa-btn-cta ufak" :disabled="hpKaydediyor || !hpDegisiklik" @click="hpKaydet">
                  <i class="fa-solid" :class="hpKaydediyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i>
                  {{ hpKaydediyor ? 'Kaydediliyor…' : 'Kaydet' }}
                </button>
              </div>
            </div>
            <div class="dolubar-kapsam">
              <div class="dolubar" :class="{ uyari: hpKullanilanDak > 45, dolu: hpKullanilanDak >= 60 }" :style="{ width: hpDolulukPct + '%' }"></div>
              <span class="dolubar-etiket">{{ hpBosDak >= 0 ? hpBosDak + 'dk boş' : Math.abs(hpBosDak) + 'dk taşma' }}</span>
            </div>
            <div v-if="hpCatismaVar" class="catisma-uyari"><i class="fa-solid fa-triangle-exclamation"></i> Çakışan bloklar var — sürükleyerek düzeltin.</div>
            <div class="iz-kapsam">
              <div class="tiklar">
                <span v-for="t in hpTiklari" :key="t" class="tik" :style="{ left: (t/HP_DAK*100)+'%' }">{{ t }}dk</span>
              </div>
              <div ref="izHpRef" class="iz iz-buyuk">
                <div v-for="t in hpTiklari" :key="'hg'+t" class="iz-cizgi" :style="{ left: (t/HP_DAK*100)+'%' }"></div>
                <div v-for="slot in hpYerelSlotlar" :key="slot._hpLid" class="iz-oge" :class="{ catisiyor: hpCatisiyor(slot) }" :style="hpOgeStili(slot)" :title="`${slot._etiket} — ${slot.duration_minutes}dk @ ${slot.offset_minutes}dk`" @mousedown.prevent="hpSuruklemeBasla($event, slot)" @dblclick.stop="hpOgeKaldir(slot)">
                  <span class="iz-oge-adi">{{ slot._etiket }}</span>
                  <span class="iz-oge-sure">{{ slot.duration_minutes }}dk</span>
                  <button class="iz-oge-kaldir" @mousedown.stop @click.stop="hpOgeKaldir(slot)">×</button>
                </div>
              </div>
              <p class="iz-ipucu soluk kucuk">Sürükle → taşı &nbsp;|&nbsp; Çift tıkla / × → kaldır</p>
            </div>
            <div v-if="hpYerelSlotlar.length" class="hp-slot-tablo">
              <div class="hp-slot-baslik soluk kucuk">
                <span>Loop Şablonu</span><span>Başlangıç</span><span>Süre (dk)</span><span></span>
              </div>
              <div v-for="slot in [...hpYerelSlotlar].sort((a,b) => a.offset_minutes-b.offset_minutes)" :key="slot._hpLid" class="hp-slot-satir">
                <span class="legand-renk" :style="{ background: slot._renk }"></span>
                <span class="legand-adi">{{ slot._etiket }}</span>
                <span class="soluk kucuk">{{ slot.offset_minutes }}dk</span>
                <input type="number" class="eisa-field ufak" style="width:60px" :value="slot.duration_minutes" :min="HP_SNAP" :max="HP_DAK" :step="HP_SNAP" @change="e => hpSureGuncelle(slot, e.target.value)" />
                <button class="pe-sil-btn" @click="hpOgeKaldir(slot)"><i class="fa-solid fa-trash-can"></i></button>
              </div>
            </div>
            <div v-else class="pe-bos-ipucu" style="margin-top:1rem">Sağ panelden bir Loop Şablonu ekleyin.</div>
          </template>
        </main>

        <!-- SAĞ: Loop şablonları -->
        <aside class="pe-sag">
          <div class="pe-panel-ust"><span class="pe-panel-baslik"><i class="fa-solid fa-layer-group"></i> Loop Şablonları</span></div>
          <div v-if="yukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-sag-liste">
            <div v-if="!sablonlar.length" class="pe-bos-ipucu">Loop şablonu yok.</div>
            <div v-for="s in sablonlar" :key="s.id" class="hp-sablon-kart">
              <div class="hp-sablon-ust">
                <span class="hp-sablon-adi">{{ s.name }}</span>
                <span class="soluk kucuk">{{ s.loop_duration_seconds }}s</span>
              </div>
              <button class="eisa-btn eisa-btn-cta mikro" style="width:100%;margin-top:.3rem" @click="loopSablonuEkle(s)">
                <i class="fa-solid fa-plus"></i> Saate Ekle
              </button>
            </div>
          </div>
        </aside>
      </template>

      <!-- ══════════ TAB: GÜNLÜK PLAN ══════════════════════════════════ -->
      <template v-if="anaSecme === 'gun'">
        <!-- SOL -->
        <aside class="pe-sol">
          <div class="pe-panel-ust">
            <span class="pe-panel-baslik"><i class="fa-solid fa-calendar-days"></i> Günlük Planlar</span>
            <button class="eisa-btn eisa-btn-cta ufak" :disabled="dpKaydediyor" @click="yeniDayPlan"><i class="fa-solid fa-plus"></i></button>
          </div>
          <div v-if="dpYukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-liste">
            <div v-if="!dayPlanlar.length" class="pe-bos-ipucu">Henüz günlük plan yok.</div>
            <div v-for="d in dayPlanlar" :key="d.id" class="pe-liste-ogesi" :class="{ aktif: d.id === aktifDpId }" @click="dpSec(d.id)">
              <span class="hp-slot-sayisi soluk kucuk">{{ (d.slots??[]).length }} saat</span>
              <span class="pe-liste-adi">{{ d.name }}</span>
              <button class="pe-sil-btn" @click.stop="dpSil(d.id)"><i class="fa-solid fa-trash-can"></i></button>
            </div>
          </div>
        </aside>

        <!-- ORTA -->
        <main class="pe-orta">
          <div v-if="!aktifDp" class="pe-bos-alan">
            <i class="fa-solid fa-calendar-days fa-3x"></i>
            <p>Sol panelden bir günlük plan seçin ya da <strong>+</strong> ile oluşturun.</p>
          </div>
          <template v-else>
            <div class="pe-orta-ust">
              <div class="pe-ad-satiri">
                <template v-if="dpYeniAdlan">
                  <input class="eisa-field pe-ad-input" :value="aktifDp.name" @keyup.enter="e => dpAdlandirmaOnayla(e.target.value)" @blur="e => dpAdlandirmaOnayla(e.target.value)" autofocus />
                </template>
                <template v-else>
                  <h2 class="pe-ad" @dblclick="dpYeniAdlan = true">{{ aktifDp.name }}<span v-if="dpDegisiklik" class="degisiklik-nok">●</span></h2>
                  <button class="ikon-btn" @click="dpYeniAdlan = true"><i class="fa-solid fa-pencil"></i></button>
                </template>
              </div>
              <div class="pe-orta-eylemler">
                <span class="soluk kucuk">{{ dpYerelSlotlar.length }}/24 saat atanmış</span>
                <button class="eisa-btn eisa-btn-cta ufak" :disabled="dpKaydediyor || !dpDegisiklik" @click="dpKaydet">
                  <i class="fa-solid" :class="dpKaydediyor ? 'fa-circle-notch fa-spin' : 'fa-floppy-disk'"></i>
                  {{ dpKaydediyor ? 'Kaydediliyor…' : 'Kaydet' }}
                </button>
              </div>
            </div>
            <p class="soluk kucuk" style="margin:.25rem 0 .5rem">
              <i class="fa-solid fa-info-circle"></i>
              Sağ panelden bir saatlik plan seçin, ardından saat kutucuklarına tıklayarak atayın.
            </p>
            <!-- 24 saat ızgarası -->
            <div class="dp-24-izgara">
              <div v-for="saat in Array.from({length:24},(_,i)=>i)" :key="saat"
                class="dp-saat-hucre"
                :class="{ atanmis: dpSaatAtamasi[saat], seciliHP: dpSaatAtamasi[saat] && dpSaatAtamasi[saat] === seciliHpId }"
                :style="dpSaatAtamasi[saat] ? { background: dpSaatHpRenk(saat) + '22', borderColor: dpSaatHpRenk(saat) } : {}"
                @click="dpSaatAta(saat)"
              >
                <span class="dp-saat-no">{{ saat.toString().padStart(2,'0') }}:00</span>
                <span v-if="dpSaatAtamasi[saat]" class="dp-saat-hp-adi">{{ dpSaatHpAdi(saat) }}</span>
                <span v-else class="soluk kucuk" style="font-size:.65rem">—</span>
                <button v-if="dpSaatAtamasi[saat]" class="dp-saat-temizle" @click.stop="dpSaatTemizle(saat)">×</button>
              </div>
            </div>

            <!-- Üretim bölümü -->
            <div class="uretim-kismi" style="margin-top:1rem">
              <div class="uretim-baslik"><i class="fa-solid fa-gears"></i><span>Playlist Üret</span></div>
              <div class="uretim-satir">
                <div class="uretim-alan">
                  <label class="pe-etiket">Tarih</label>
                  <input type="date" class="eisa-field ufak" v-model="uretimTarihi" />
                </div>
                <div class="uretim-alan" style="flex:2">
                  <label class="pe-etiket">Hedef Kiosk</label>
                  <div class="kapsam-secici">
                    <button v-for="(etk, val) in { all:'Tüm Kiosklar', il:'İle Ait', ilce:'İlçeye Ait', kiosks:'Seçili Kiosklar' }" :key="val" class="kapsam-btn" :class="{ aktif: hedefKapsam === val }" @click="hedefKapsam = val; seciliKiosklar = []">{{ etk }}</button>
                  </div>
                </div>
              </div>
              <div v-if="hedefKapsam === 'il' || hedefKapsam === 'ilce'" class="uretim-satir">
                <div class="uretim-alan">
                  <label class="pe-etiket">İl</label>
                  <select class="eisa-field ufak" v-model="hedefIlId" @change="ilDegisti">
                    <option :value="null">— İl seçin —</option>
                    <option v-for="il in iller" :key="il.id" :value="il.id">{{ il.ad }}</option>
                  </select>
                </div>
                <div v-if="hedefKapsam === 'ilce'" class="uretim-alan">
                  <label class="pe-etiket">İlçe</label>
                  <select class="eisa-field ufak" v-model="hedefIlceId" :disabled="!hedefIlId">
                    <option :value="null">— İlçe seçin —</option>
                    <option v-for="ilce in ilceler" :key="ilce.id" :value="ilce.id">{{ ilce.ad }}</option>
                  </select>
                </div>
              </div>
              <div v-if="hedefKapsam === 'kiosks'" class="kiosk-secici">
                <div v-if="kioskYukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
                <div v-else class="kiosk-liste">
                  <label v-for="k in gorunenKiosklar()" :key="k.id" class="kiosk-satir" :class="{ secili: seciliKiosklar.includes(k.id) }">
                    <input type="checkbox" :checked="seciliKiosklar.includes(k.id)" @change="kioskSecimiToggle(k.id)" />
                    <span class="kiosk-adi">{{ k.ad }}</span>
                    <span class="soluk kucuk" v-if="k.il_adi">{{ k.il_adi }}/{{ k.ilce_adi }}</span>
                  </label>
                  <div v-if="!gorunenKiosklar().length" class="pe-bos-ipucu">Kiosk bulunamadı.</div>
                </div>
              </div>
              <div class="uretim-eylem">
                <span class="kapsam-ozet soluk kucuk"><i class="fa-solid fa-server"></i> {{ kapsamiKioskSayisi }} kiosk</span>
                <button class="eisa-btn eisa-btn-cta ufak" :disabled="uretiliyor || (hedefKapsam === 'kiosks' && !seciliKiosklar.length)" @click="uretimBaslat">
                  <i class="fa-solid" :class="uretiliyor ? 'fa-circle-notch fa-spin' : 'fa-play'"></i>
                  {{ uretiliyor ? 'Başlatılıyor…' : 'Üret' }}
                </button>
              </div>
              <div v-if="aktifIs" class="is-ilerleme">
                <div class="is-ust">
                  <span class="is-durum-rozet" :class="aktifIs.status.toLowerCase()">{{ aktifIs.status }}</span>
                  <span class="soluk kucuk">{{ aktifIs.done_kiosks }}/{{ aktifIs.total_kiosks }} kiosk · {{ aktifIs.playlists_generated }} playlist</span>
                </div>
                <div class="is-barcap"><div class="is-bar" :class="{ tamam: aktifIs.status==='DONE', basarisiz: aktifIs.status==='FAILED' }" :style="{ width: (aktifIs.progress_pct??0)+'%' }"></div></div>
              </div>
            </div>
          </template>
        </main>

        <!-- SAĞ: HourPlan listesi -->
        <aside class="pe-sag">
          <div class="pe-panel-ust"><span class="pe-panel-baslik"><i class="fa-solid fa-clock"></i> Saatlik Planlar</span></div>
          <div v-if="hpYukleniyor" class="pe-yukleniyor"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else class="pe-sag-liste">
            <p class="soluk kucuk" style="padding:.4rem .5rem .2rem">Tıklayarak seçin, sonra saat hücrelerine atayın:</p>
            <div v-if="!hourPlanlar.length" class="pe-bos-ipucu">Saatlik plan yok.</div>
            <div v-for="h in hourPlanlar" :key="h.id" class="hp-sablon-kart" :class="{ secili: h.id === seciliHpId }" @click="seciliHpId = (seciliHpId === h.id ? null : h.id)">
              <div class="hp-sablon-ust">
                <span class="hp-renk-nokta" :style="{ background: PALETTE[hourPlanlar.indexOf(h) % PALETTE.length] }"></span>
                <span class="hp-sablon-adi">{{ h.name }}</span>
                <span class="soluk kucuk">{{ (h.slots??[]).length }} slot</span>
              </div>
            </div>
          </div>
        </aside>
      </template>

    </div><!-- /pe-sayfa -->
  </div><!-- /pe-sayfa-kapsam -->
</template>


<style scoped>
.pe-sayfa {
  display: grid;
  grid-template-columns: 240px 1fr 260px;
  height: calc(100vh - 64px);
  background: var(--color-bg,#F9FAFB);
  overflow: hidden;
}

/* ── Paneller ──────────────────────────────────────────────────────────── */
.pe-sol, .pe-sag {
  background: var(--color-surface,#fff);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--color-border,#E5E7EB);
}
.pe-sag { border-right: none; border-left: 1px solid var(--color-border,#E5E7EB); }

.pe-panel-ust {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .6rem .75rem;
  border-bottom: 1px solid var(--color-border,#E5E7EB);
  flex-shrink: 0;
  gap: .4rem;
}
.pe-panel-baslik { font-weight: 600; font-size: .8125rem; display: flex; align-items: center; gap: .35rem; }

.pe-liste, .pe-sag-liste { overflow-y: auto; flex: 1; padding: .4rem; }
.pe-liste-ogesi {
  display: flex; align-items: center; gap: .4rem;
  padding: .45rem .65rem; border-radius: .4rem;
  cursor: pointer; font-size: .8125rem; transition: background .12s;
}
.pe-liste-ogesi:hover { background: var(--color-hover,#F3F4F6); }
.pe-liste-ogesi.aktif { background: #FEF2F2; color: #B1121B; font-weight: 600; }
.pe-liste-adi { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pe-sil-btn { background: none; border: none; cursor: pointer; color: #9CA3AF; padding: .1rem .25rem; border-radius: .2rem; }
.pe-sil-btn:hover { color: #ef4444; background: #fee2e2; }

/* Saat şerit göstergesi */
.pe-saat-renk-serit { display: flex; gap: 2px; flex-shrink: 0; }
.serit-dilim { width: 6px; height: 14px; border-radius: 2px; opacity: .2; transition: opacity .15s; }
.serit-dilim.aktif { opacity: 1; }

/* Gün özeti */
.pe-gun-ozet { padding: .5rem .75rem .75rem; border-top: 1px solid var(--color-border,#E5E7EB); flex-shrink: 0; }
.gun-ozet-iz { display: flex; gap: 2px; margin: .4rem 0; }
.gun-saat-blok {
  flex: 1; height: 14px; border-radius: 2px;
  background: #E5E7EB; transition: background .15s;
}
.gun-saat-blok.atanmis { opacity: .85; }
.gun-legand { display: flex; flex-direction: column; gap: .2rem; max-height: 80px; overflow-y: auto; }
.gun-legand-satir { display: flex; align-items: center; gap: .35rem; font-size: .72rem; }
.gun-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.gun-saat-aralik { font-variant-numeric: tabular-nums; min-width: 60px; }
.gun-adi { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Orta alan ─────────────────────────────────────────────────────────── */
.pe-orta { overflow-y: auto; padding: 1.1rem 1.4rem; display: flex; flex-direction: column; gap: .875rem; }
.pe-bos-alan {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex: 1; gap: .875rem; color: #9CA3AF; text-align: center; margin-top: 4rem;
}

/* Başlık */
.pe-orta-ust { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .6rem; }
.pe-ad-satiri { display: flex; align-items: center; gap: .4rem; }
.pe-ad {
  font-size: 1.2rem; font-weight: 700; margin: 0; cursor: default;
  display: flex; align-items: center; gap: .35rem;
}
.degisiklik-nok { color: #f59e0b; font-size: .9rem; }
.pe-ad-input { font-size: 1.1rem; font-weight: 700; padding: .2rem .45rem; max-width: 240px; }
.pe-orta-eylemler { display: flex; align-items: center; gap: .6rem; }
.kapasite-rozet {
  display: flex; align-items: center; gap: .3rem; font-size: .8rem; font-weight: 600;
  padding: .25rem .55rem; border-radius: 1rem; background: #dcfce7; color: #16a34a; border: 1px solid #bbf7d0;
}
.kapasite-rozet.uyari { background: #fef9c3; color: #ca8a04; border-color: #fde047; }
.kapasite-rozet.dolu  { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }

/* Sekmeler */
.pe-sekmeler { display: flex; gap: .35rem; border-bottom: 1px solid var(--color-border,#E5E7EB); padding-bottom: .5rem; }
.pe-sekme {
  background: none; border: none; cursor: pointer; font-size: .8125rem; font-weight: 500;
  color: #6b7280; padding: .35rem .7rem; border-radius: .35rem; transition: background .12s,color .12s;
  display: flex; align-items: center; gap: .3rem;
}
.pe-sekme:hover { background: #f3f4f6; color: #111827; }
.pe-sekme.aktif { background: #FEF2F2; color: #B1121B; font-weight: 700; }

/* Doluluk çubuğu */
.dolubar-kapsam { position: relative; height: 7px; background: #E5E7EB; border-radius: 4px; }
.dolubar { height: 100%; border-radius: 4px; background: #22c55e; transition: width .2s, background .2s; }
.dolubar.uyari { background: #f59e0b; }
.dolubar.dolu  { background: #ef4444; }
.dolubar-etiket { position: absolute; right: 0; top: 10px; font-size: .68rem; color: #9CA3AF; }

/* Çakışma uyarısı */
.catisma-uyari {
  background: #fef3c7; border: 1px solid #fcd34d; color: #92400e;
  border-radius: .4rem; padding: .45rem .7rem; font-size: .8rem;
  display: flex; align-items: center; gap: .4rem;
}

/* Zaman çizelgesi */
.iz-kapsam { background: var(--color-surface,#fff); border: 1px solid var(--color-border,#E5E7EB); border-radius: .65rem; padding: .65rem .9rem .9rem; }
.tiklar { position: relative; height: 16px; margin-bottom: 4px; user-select: none; }
.tik { position: absolute; transform: translateX(-50%); font-size: .62rem; color: #9CA3AF; white-space: nowrap; }
.iz {
  position: relative; height: 56px; background: var(--color-bg,#F9FAFB);
  border: 1px solid var(--color-border,#E5E7EB); border-radius: .4rem; overflow: visible; user-select: none;
}
.iz-cizgi { position: absolute; top: 0; height: 100%; width: 1px; background: var(--color-border,#E5E7EB); pointer-events: none; }
.iz-oge {
  position: absolute; top: 5px; height: calc(100% - 10px);
  border-radius: .3rem; cursor: grab; display: flex; align-items: center; justify-content: space-between;
  padding: 0 .35rem; box-sizing: border-box; overflow: hidden;
  border: 2px solid transparent; box-shadow: 0 1px 3px rgba(0,0,0,.18); transition: box-shadow .1s;
}
.iz-oge:hover { box-shadow: 0 2px 7px rgba(0,0,0,.28); z-index: 10; }
.iz-oge:active { cursor: grabbing; z-index: 20; }
.iz-oge.catisiyor { border-color: #dc2626; }
.iz-oge-adi {
  font-size: .62rem; font-weight: 700; color: #fff; overflow: hidden; white-space: nowrap;
  text-overflow: ellipsis; flex: 1; pointer-events: none; text-shadow: 0 1px 2px rgba(0,0,0,.3);
}
.iz-oge-sure { font-size: .58rem; color: rgba(255,255,255,.85); white-space: nowrap; pointer-events: none; margin-left: .2rem; }
.iz-oge-kaldir {
  background: rgba(0,0,0,.25); border: none; color: #fff; border-radius: .2rem;
  width: 14px; height: 14px; font-size: .65rem; line-height: 1; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-left: .15rem; padding: 0;
}
.iz-oge-kaldir:hover { background: rgba(220,38,38,.7); }
.iz-ipucu { margin-top: .4rem; }

/* Legand */
.legand { display: flex; flex-direction: column; gap: .3rem; }
.legand-satir { display: flex; align-items: center; gap: .5rem; font-size: .8rem; }
.legand-renk { width: 11px; height: 11px; border-radius: .2rem; flex-shrink: 0; }
.legand-adi { flex: 1; font-weight: 500; }

/* Hedef saatler */
.saat-kismi { display: flex; flex-direction: column; gap: .75rem; }
.saat-grubu { border: 1px solid var(--color-border,#E5E7EB); border-radius: .5rem; overflow: hidden; }
.saat-grubu-ust {
  display: flex; align-items: center; gap: .5rem; padding: .5rem .75rem;
  cursor: pointer; background: var(--color-surface,#fff); transition: background .12s;
}
.saat-grubu-ust:hover { background: #f9fafb; }
.saat-grubu-renk { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.saat-grubu-adi { font-weight: 600; font-size: .8125rem; }
.saat-grubu-isaretci {
  margin-left: auto; width: 20px; height: 20px; border-radius: 50%;
  background: #e5e7eb; color: #9ca3af; display: flex; align-items: center; justify-content: center;
  font-size: .65rem; transition: background .15s, color .15s;
}
.saat-grubu-isaretci.aktif { background: #22c55e; color: #fff; }
.saat-kutucuklar { display: flex; gap: .35rem; padding: .5rem .75rem; flex-wrap: wrap; }
.saat-kutu {
  width: 36px; height: 36px; border-radius: .35rem; font-size: .78rem; font-weight: 600;
  border: 1.5px solid #E5E7EB; background: #f9fafb; color: #374151; cursor: pointer; transition: all .12s;
}
.saat-kutu:hover { border-color: #B1121B; color: #B1121B; }
.saat-kutu.aktif { color: #fff; border-color: transparent; }
.saat-kutu.catisan { box-shadow: 0 0 0 2px #f59e0b; }
.secili-saatler-ozet {
  display: flex; align-items: center; gap: .5rem; font-size: .8125rem;
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: .4rem; padding: .45rem .7rem;
}

/* Üretim bölümü */
.uretim-kismi {
  border: 1px solid var(--color-border,#E5E7EB); border-radius: .65rem;
  padding: .75rem 1rem; background: var(--color-surface,#fff); display: flex; flex-direction: column; gap: .6rem;
}
.uretim-baslik { display: flex; align-items: center; gap: .4rem; font-size: .8125rem; font-weight: 600; color: #374151; }
.uretim-satir { display: flex; gap: .75rem; flex-wrap: wrap; }
.uretim-alan { display: flex; flex-direction: column; gap: .25rem; flex: 1; min-width: 120px; }
.pe-etiket { font-size: .75rem; font-weight: 600; color: #6b7280; }

.kapsam-secici { display: flex; gap: .3rem; flex-wrap: wrap; }
.kapsam-btn {
  background: #f3f4f6; border: 1.5px solid #E5E7EB; cursor: pointer;
  font-size: .75rem; font-weight: 500; color: #374151; padding: .25rem .55rem; border-radius: .35rem; transition: all .12s;
}
.kapsam-btn:hover { border-color: #B1121B; color: #B1121B; }
.kapsam-btn.aktif { background: #FEF2F2; border-color: #B1121B; color: #B1121B; font-weight: 700; }

.kiosk-secici { max-height: 180px; overflow-y: auto; border: 1px solid var(--color-border,#E5E7EB); border-radius: .4rem; }
.kiosk-liste { padding: .3rem; }
.kiosk-satir {
  display: flex; align-items: center; gap: .4rem; padding: .3rem .4rem;
  border-radius: .3rem; cursor: pointer; font-size: .8rem;
}
.kiosk-satir:hover { background: #f9fafb; }
.kiosk-satir.secili { background: #FEF2F2; }
.kiosk-adi { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.uretim-eylem { display: flex; align-items: center; justify-content: space-between; gap: .6rem; flex-wrap: wrap; }
.kapsam-ozet { display: flex; align-items: center; gap: .35rem; }

/* İş ilerleme */
.is-ilerleme { display: flex; flex-direction: column; gap: .35rem; }
.is-ust { display: flex; align-items: center; gap: .6rem; }
.is-durum-rozet { font-size: .7rem; font-weight: 700; padding: .15rem .45rem; border-radius: 1rem; text-transform: uppercase; }
.is-durum-rozet.pending { background: #e5e7eb; color: #6b7280; }
.is-durum-rozet.running { background: #dbeafe; color: #2563eb; }
.is-durum-rozet.done    { background: #dcfce7; color: #16a34a; }
.is-durum-rozet.failed  { background: #fee2e2; color: #dc2626; }
.is-barcap { height: 6px; background: #e5e7eb; border-radius: 3px; }
.is-bar { height: 100%; border-radius: 3px; background: #3b82f6; transition: width .4s; }
.is-bar.tamam     { background: #22c55e; }
.is-bar.basarisiz { background: #ef4444; }

/* Sağ panel */
.kamp-kart { border: 1px solid var(--color-border,#E5E7EB); border-radius: .45rem; background: var(--color-surface,#fff); overflow: hidden; margin-bottom: .35rem; }
.kamp-ust { display: flex; align-items: center; gap: .5rem; padding: .5rem .65rem; cursor: pointer; transition: background .12s; }
.kamp-ust:hover { background: #f9fafb; }
.kamp-renk-nokta { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.kamp-bilgi { flex: 1; min-width: 0; }
.kamp-adi { font-size: .8rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.genislet-ikon { font-size: .65rem; color: #9ca3af; transition: transform .15s; }
.genislet-ikon.donmus { transform: rotate(90deg); }
.creative-liste { border-top: 1px solid var(--color-border,#E5E7EB); padding: .3rem .5rem; display: flex; flex-direction: column; gap: .25rem; }
.creative-satir { display: flex; align-items: center; gap: .4rem; padding: .25rem .3rem; border-radius: .3rem; }
.creative-satir:hover { background: #f9fafb; }
.creative-adi { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Ortak */
.ikon-btn { background: none; border: none; cursor: pointer; color: #9CA3AF; padding: .18rem .3rem; border-radius: .25rem; transition: color .12s; }
.ikon-btn:hover { color: #111827; }
.pe-yukleniyor { padding: .75rem; color: #9CA3AF; font-size: .8125rem; display: flex; align-items: center; gap: .4rem; }
.pe-bos-ipucu { color: #9CA3AF; font-size: .8rem; padding: .75rem; text-align: center; }
.soluk { color: #9CA3AF; }
.kucuk { font-size: .8rem; }
.ufak  { padding: .28rem .55rem !important; font-size: .8rem   !important; }
.mikro { padding: .18rem .4rem  !important; font-size: .72rem  !important; }

/* ── 3-Tier ek stiller ───────────────────────────────────────────────────── */
/* Üst sarmalayıcı */
.pe-sayfa-kapsam { display: flex; flex-direction: column; height: calc(100vh - 64px); overflow: hidden; }

/* Üst sekme çubuğu */
.pe-ust-sekme-bar {
  display: flex; gap: .5rem; padding: .45rem 1rem;
  background: #fff; border-bottom: 1px solid var(--color-border,#E5E7EB); flex-shrink: 0;
}
.ust-sekme {
  background: none; border: 1.5px solid transparent; cursor: pointer;
  font-size: .8125rem; font-weight: 500; color: #6b7280;
  padding: .35rem .85rem; border-radius: .4rem; transition: all .12s;
  display: flex; align-items: center; gap: .35rem;
}
.ust-sekme:hover { background: #f3f4f6; color: #111827; }
.ust-sekme.aktif { background: #FEF2F2; color: #B1121B; border-color: #fca5a5; font-weight: 700; }

/* pe-sayfa fills the remaining height */
.pe-sayfa { flex: 1; overflow: hidden; }

/* HourPlan timeline (bigger iz) */
.iz-buyuk { height: 80px !important; }

/* HP slot tablo */
.hp-slot-tablo { display: flex; flex-direction: column; gap: .3rem; margin-top: .6rem; }
.hp-slot-baslik { display: grid; grid-template-columns: 1fr auto auto auto; gap: .4rem; padding: 0 .3rem; font-size: .72rem; }
.hp-slot-satir {
  display: grid; grid-template-columns: 12px 1fr auto auto auto; gap: .4rem;
  align-items: center; padding: .2rem .3rem; border-radius: .3rem; background: #f9fafb;
}
.hp-slot-sayisi { flex-shrink: 0; font-size: .72rem; }

/* HP sablon kartları (sağ panel) */
.hp-sablon-kart {
  border: 1.5px solid var(--color-border,#E5E7EB); border-radius: .4rem;
  padding: .45rem .6rem; cursor: pointer; transition: border-color .12s, background .12s;
  margin-bottom: .3rem;
}
.hp-sablon-kart:hover { border-color: #B1121B; }
.hp-sablon-kart.secili { border-color: #B1121B; background: #FEF2F2; }
.hp-sablon-ust { display: flex; align-items: center; gap: .4rem; }
.hp-sablon-adi { flex: 1; font-size: .8rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hp-renk-nokta { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }

/* DayPlan 24-saat ızgarası */
.dp-24-izgara {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: .4rem;
  margin: .5rem 0;
}
.dp-saat-hucre {
  border: 1.5px solid var(--color-border,#E5E7EB);
  border-radius: .45rem; padding: .4rem .35rem;
  cursor: pointer; transition: border-color .12s, background .12s;
  display: flex; flex-direction: column; align-items: center; gap: .15rem;
  position: relative; min-height: 54px;
}
.dp-saat-hucre:hover { border-color: #B1121B; }
.dp-saat-hucre.atanmis { border-width: 2px; }
.dp-saat-hucre.seciliHP { outline: 2px solid #B1121B; }
.dp-saat-no { font-size: .7rem; font-weight: 700; color: #374151; font-variant-numeric: tabular-nums; }
.dp-saat-hp-adi { font-size: .62rem; font-weight: 600; color: #374151; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.dp-saat-temizle {
  position: absolute; top: 2px; right: 3px;
  background: rgba(0,0,0,.15); border: none; color: #fff; border-radius: 50%;
  width: 14px; height: 14px; font-size: .6rem; cursor: pointer; display: flex;
  align-items: center; justify-content: center; padding: 0; line-height: 1;
}
.dp-saat-temizle:hover { background: #ef4444; }
</style>
