<script setup>
/**
 * Eczane Durum Raporu — PDF çıktısı için modal + rapor oluşturucusu.
 *
 * Eczacı: kendi eczanesi için otomatik.
 * Admin:  belirli bir eczane ya da tüm eczanelerin özeti.
 *
 * Rapor yeni bir pencerede açılır; tarayıcının "Yazdır / PDF olarak kaydet"
 * diyaloğu otomatik tetiklenir. Diğer eczane bilgileri sızdırılmaz.
 */
import { ref, computed } from 'vue';
import { http } from '../services/api';
import { useAuthStore } from '../stores/auth';
import EczanePicker from './shared/EczanePicker.vue';

const props = defineProps({
  /** Admin modunda eczane filtresi ön doldurma */
  defaultEczaneId: { type: [Number, String], default: null },
});

const emit = defineEmits(['close']);

const auth      = useAuthStore();
const isAdmin   = computed(() => auth.role === 'superadmin');

const startDate = ref('');
const endDate   = ref('');
const eczaneId  = ref(props.defaultEczaneId || null);
const loading   = ref(false);
const error     = ref('');

// Admin modunda "tüm eczaneler" seçeneği
const tumEczaneler = ref(!props.defaultEczaneId);
watch_tumEczaneler: if (!isAdmin.value) { /* pharmacist always own */ }

import { watch } from 'vue';
watch(eczaneId, (v) => { if (v) tumEczaneler.value = false; });

async function generate() {
  error.value   = '';
  loading.value = true;
  try {
    const params = {};
    if (startDate.value) params.start_date = startDate.value;
    if (endDate.value)   params.end_date   = endDate.value;
    if (isAdmin.value && !tumEczaneler.value && eczaneId.value)
      params.eczane_id = eczaneId.value;

    const { data } = await http.get('/api/analytics/pharmacy-report/', { params });
    openPrintWindow(data, params);
    emit('close');
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Rapor oluşturulamadı.';
  } finally {
    loading.value = false;
  }
}

// ── HTML report builder ────────────────────────────────────────────────────

function fmt(n) {
  return (n ?? 0).toLocaleString('tr-TR');
}

function eczaneSection(e) {
  const em  = e.em_stats  ?? { onerilen: 0, onerilen_satilan: 0, eczaci_eklenen_satilan: 0, toplam_satilan: 0 };
  const ort = e.oturum;

  const satisOranPct = ort.toplam
    ? Math.round(e.satis.toplam / ort.toplam * 100) : 0;

  function tbl(rows, cols) {
    const thead = cols.map((c) => `<th${c.right ? ' class="r"' : ''}>${c.label}</th>`).join('');
    const tbody = rows.length
      ? rows.map((r, i) => `<tr>${cols.map((c) => `<td${c.right ? ' class="r"' : ''}>${c.fn ? c.fn(r, i) : (r[c.key] ?? '—')}</td>`).join('')}</tr>`).join('')
      : `<tr><td colspan="${cols.length}" class="empty">Veri yok</td></tr>`;
    return `<table><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table>`;
  }

  const rankCol   = { label: '#',   fn: (_, i) => i + 1 };
  const adCol     = { label: 'Ad' };
  const sayiCol   = { label: 'Adet', key: 'sayi', right: true };

  return `
  <div class="eczane-header">
    <div class="eczane-name">${e.eczane.ad}</div>
    <div class="eczane-meta">
      <span>${e.eczane.ilce} / ${e.eczane.il}</span>
      ${e.eczane.eczane_kodu ? `<span class="badge">Kod: ${e.eczane.eczane_kodu}</span>` : ''}
      ${e.eczane.sahip_adi  ? `<span>Sorumlu: <b>${e.eczane.sahip_adi}</b>${e.eczane.telefon ? ' · ' + e.eczane.telefon : ''}</span>` : ''}
    </div>
  </div>

  <div class="stats-wrap">
    <!-- Etkileşim özet -->
    <div class="stats-block">
      <div class="stats-title">ETKİLEŞİM ÖZETİ</div>
      <table class="stats-tbl">
        <tbody>
          <tr><td>Satış Yapılan</td><td class="r accent-green">${fmt(ort.satis_yapilan)}</td></tr>
          <tr><td>Satış Yapılmayan</td><td class="r accent-red">${fmt(ort.satis_yapilmayan)}</td></tr>
          <tr><td>Bekleyen / İnceleniyor</td><td class="r">${fmt(ort.bekleyen)}</td></tr>
          <tr class="total-row"><td><b>Toplam Etkileşim</b></td><td class="r"><b>${fmt(ort.toplam)}</b></td></tr>
          <tr><td>Danışma Tamamlanan</td><td class="r">${fmt(ort.danisma_tamamlanan)}</td></tr>
          <tr class="avg-row"><td>Günlük Ortalama</td><td class="r">${String(ort.gunluk_ort).replace('.', ',')}</td></tr>
          <tr><td>Satışa Dönüşüm Oranı</td><td class="r">%${satisOranPct}</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Etken Madde özet -->
    <div class="stats-block">
      <div class="stats-title">ETKEN MADDE ANALİZİ</div>
      <table class="stats-tbl">
        <tbody>
          <tr><td>Önerilenden Satılan</td><td class="r accent-green">${fmt(em.onerilen_satilan)}</td></tr>
          <tr><td>Eczacı Eklediği Satış</td><td class="r accent-blue">${fmt(em.eczaci_eklenen_satilan)}</td></tr>
          <tr class="total-row"><td><b>Toplam Satılan EM</b></td><td class="r"><b>${fmt(em.toplam_satilan)}</b></td></tr>
          <tr><td>Toplam Önerilen EM</td><td class="r">${fmt(em.onerilen)}</td></tr>
          <tr class="avg-row"><td>Günlük Ort. Satılan EM</td><td class="r">${String(e.satis.gunluk_ort).replace('.', ',')}</td></tr>
          ${em.onerilen ? `<tr><td>Öneriden Satış Oranı</td><td class="r">%${Math.round(em.onerilen_satilan / em.onerilen * 100)}</td></tr>` : ''}
        </tbody>
      </table>
    </div>
  </div>

  <div class="tri-grid">
    <div>
      <div class="tbl-hdr">POPÜler KATEGORİLER</div>
      ${tbl(e.kategoriler, [rankCol, { label: 'Kategori', key: 'ad' }, sayiCol])}
    </div>
    <div>
      <div class="tbl-hdr">EN ÇOK ÖNERİLEN ETKEN MADDELER</div>
      ${tbl(e.en_cok_onerilen_em, [rankCol, { label: 'Etken Madde', key: 'ad' }, sayiCol])}
    </div>
    <div>
      <div class="tbl-hdr">EN ÇOK SATILAN ETKEN MADDELER</div>
      ${tbl(e.etken_maddeler, [rankCol, { label: 'Etken Madde', key: 'ad' }, sayiCol])}
    </div>
  </div>

  <div class="tri-grid">
    <div>
      <div class="tbl-hdr">EN ÇOK SATIŞ YAPILAN GÜNLER</div>
      ${tbl(e.en_cok_satis_tarihler, [rankCol, { label: 'Tarih', key: 'tarih' }, { label: 'Satış', key: 'sayi', right: true }])}
    </div>
    <div>
      <div class="tbl-hdr">EN ÇOK SATIŞ YAPILAN SAATLER</div>
      ${tbl(e.en_cok_satis_saatler, [rankCol, { label: 'Saat Aralığı', key: 'saat' }, { label: 'Satış', key: 'sayi', right: true }])}
    </div>
    <div>
      <div class="tbl-hdr">EN ÇOK ETKİLEŞİM ALIAN SAATLER</div>
      ${tbl(e.en_cok_etkilesim_saatler, [rankCol, { label: 'Saat Aralığı', key: 'saat' }, { label: 'İşlem', key: 'sayi', right: true }])}
    </div>
  </div>`;
}

function openPrintWindow(data, params) {
  const period = params.start_date || params.end_date
    ? `${params.start_date || '…'} — ${params.end_date || '…'}`
    : 'Tüm Zamanlar';

  const genel = data.genel_ozet;
  const genel_section = genel ? `
  <div class="genel-box">
    <div class="genel-hdr">GENEL ÖZET — ${genel.toplam_eczane} ECZANE</div>
    <div class="genel-row">
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_oturum)}</div><div class="g-lbl">Toplam Etkileşim</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_satis_yapilan ?? 0)}</div><div class="g-lbl">Satış Yapılan</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_satis_yapilmayan ?? 0)}</div><div class="g-lbl">Satış Yapılmayan</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_bekleyen ?? 0)}</div><div class="g-lbl">Bekleyen</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_onerilen_em ?? 0)}</div><div class="g-lbl">Toplam Önerilen EM</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_satilan_em ?? 0)}</div><div class="g-lbl">Toplam Satılan EM</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_onerilen_satilan ?? 0)}</div><div class="g-lbl">Önerilenden Satılan</div></div>
      <div class="g-item"><div class="g-val">${fmt(genel.toplam_eczaci_eklenen ?? 0)}</div><div class="g-lbl">Eczacı Eklediği</div></div>
    </div>
  </div>` : '';

  const sections = data.eczaneler
    .map((e, i) => `<div class="eczane-wrap${i > 0 ? ' pgbrk' : ''}">${eczaneSection(e)}</div>`)
    .join('');

  const css = `
*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
body { font-family:Arial,Helvetica,sans-serif; font-size:10.5px; color:#1e293b; background:#fff; line-height:1.35; }
.doc-hdr { display:flex; justify-content:space-between; align-items:flex-end; padding-bottom:8px; border-bottom:2.5px solid #B1121B; margin-bottom:14px; }
.brand-name { font-size:18px; font-weight:900; color:#B1121B; }
.brand-tag  { font-size:8px; color:#64748b; margin-top:1px; }
.doc-info { text-align:right; }
.doc-ttl  { font-size:12px; font-weight:800; }
.doc-meta { font-size:8.5px; color:#64748b; margin-top:2px; }
.genel-box { background:#f8fafc; border:1px solid #cbd5e1; border-radius:5px; padding:8px 12px; margin-bottom:14px; }
.genel-hdr { font-size:7.5px; font-weight:800; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; margin-bottom:7px; }
.genel-row { display:flex; }
.g-item    { flex:1; text-align:center; border-right:1px solid #e2e8f0; padding:0 6px; }
.g-item:last-child { border:none; }
.g-val     { font-size:15px; font-weight:900; color:#B1121B; line-height:1; }
.g-lbl     { font-size:7.5px; color:#475569; margin-top:2px; font-weight:600; }
.eczane-header { border-bottom:1.5px solid #e2e8f0; padding-bottom:6px; margin-bottom:10px; }
.eczane-name { font-size:13px; font-weight:900; color:#0f172a; }
.eczane-meta { display:flex; gap:10px; margin-top:2px; font-size:8.5px; color:#64748b; align-items:center; flex-wrap:wrap; }
.badge { background:#f1f5f9; border:1px solid #e2e8f0; border-radius:3px; padding:1px 4px; font-weight:700; color:#334155; }
.stats-wrap { display:flex; gap:12px; margin-bottom:12px; }
.stats-block { flex:1; border:1px solid #e2e8f0; border-radius:5px; overflow:hidden; }
.stats-title { background:#f1f5f9; padding:4px 8px; font-size:8px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:#475569; border-bottom:1px solid #e2e8f0; }
.stats-tbl { width:100%; border-collapse:collapse; }
.stats-tbl td { padding:3px 8px; font-size:10px; border-bottom:1px solid #f8fafc; }
.stats-tbl tr:last-child td { border-bottom:none; }
.stats-tbl .r { text-align:right; font-variant-numeric:tabular-nums; }
.stats-tbl .total-row td { font-weight:700; background:#fafafa; border-top:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0; }
.stats-tbl .avg-row td { color:#7c3aed; font-weight:700; }
.accent-green { color:#059669; font-weight:700; }
.accent-red   { color:#dc2626; font-weight:700; }
.accent-blue  { color:#2563eb; font-weight:700; }
.tri-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px; }
.tbl-hdr { font-size:7.5px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:#475569; border-bottom:1px solid #cbd5e1; padding-bottom:3px; margin-bottom:4px; }
table { width:100%; border-collapse:collapse; }
thead th { background:#f1f5f9; padding:3px 5px; font-size:8.5px; font-weight:700; color:#475569; border-bottom:1px solid #cbd5e1; text-align:left; }
th.r, td.r { text-align:right; }
tbody td { padding:2.5px 5px; font-size:9.5px; border-bottom:1px solid #f1f5f9; color:#374151; }
tbody tr:last-child td { border-bottom:none; }
td.empty { text-align:center; color:#94a3b8; font-style:italic; font-size:8.5px; }
.doc-ftr { margin-top:14px; padding-top:6px; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; font-size:7.5px; color:#94a3b8; }
@media print {
  @page { size:A4 portrait; margin:1.4cm 1.6cm 1.2cm; }
  .pgbrk { page-break-before:always; }
  .eczane-wrap { page-break-inside:avoid; }
  .tri-grid    { page-break-inside:avoid; }
  .stats-wrap  { page-break-inside:avoid; }
  tr           { page-break-inside:avoid; }
}`;

  const html = `<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Eczane Durum Raporu — e-isa</title>
<style>${css}</style>
</head>
<body>
<div class="doc-hdr">
  <div>
    <div class="brand-name">e-isa</div>
    <div class="brand-tag">İnteraktif Supplement Asistanı</div>
  </div>
  <div class="doc-info">
    <div class="doc-ttl">Eczane Durum Raporu</div>
    <div class="doc-meta">Dönem: ${period}</div>
    <div class="doc-meta">Oluşturulma: ${data.rapor_tarihi}</div>
  </div>
</div>
${genel_section}
${sections}
<div class="doc-ftr">
  <span>Yönetici Raporu</span>
  <span>${data.rapor_tarihi} · ${data.eczaneler.length} eczane</span>
</div>
</body>
</html>`;

  const win = window.open('', '_blank', 'width=860,height=720');
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 700);
}
</script>

<template>
  <Teleport to="body">
    <div class="eisa-modal-backdrop" @click.self="emit('close')">
      <div class="eisa-modal rpt-modal" role="dialog" aria-modal="true">

        <!-- Header -->
        <div class="eisa-modal-header">
          <div>
            <h3 class="eisa-modal-title">
              <i class="fa-solid fa-file-pdf" style="color:#B1121B;"></i>
              Eczane Durum Raporu
            </h3>
            <p style="font-size:0.78rem;color:#6b7280;margin-top:0.2rem;">
              Rapor yeni pencerede açılır ve otomatik yazdırma ekranı gösterilir.
            </p>
          </div>
          <button class="eisa-modal-close" @click="emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <!-- Body -->
        <div class="eisa-modal-body rpt-body">

          <!-- Admin: pharmacy selector -->
          <template v-if="isAdmin">
            <div class="rpt-field">
              <label class="eisa-label">Kapsam</label>
              <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                <label class="rpt-radio" :class="{ active: tumEczaneler }">
                  <input type="radio" v-model="tumEczaneler" :value="true" @change="eczaneId = null" />
                  <i class="fa-solid fa-building"></i> Tüm Eczaneler
                </label>
                <label class="rpt-radio" :class="{ active: !tumEczaneler }">
                  <input type="radio" v-model="tumEczaneler" :value="false" />
                  <i class="fa-solid fa-house-medical"></i> Belirli Eczane
                </label>
              </div>
            </div>

            <div v-if="!tumEczaneler" class="rpt-field">
              <label class="eisa-label">Eczane Seç</label>
              <EczanePicker v-model="eczaneId" placeholder="İl / İlçe / Eczane ara…" />
            </div>
          </template>

          <!-- Date range -->
          <div class="rpt-date-row">
            <div class="rpt-field">
              <label class="eisa-label">Dönem Başlangıcı</label>
              <input v-model="startDate" type="date" class="eisa-field" />
            </div>
            <div class="rpt-field">
              <label class="eisa-label">Dönem Bitişi</label>
              <input v-model="endDate" type="date" class="eisa-field" />
            </div>
          </div>

          <p style="font-size:0.75rem;color:#94a3b8;">
            Dönem seçilmezse tüm zamanlara ait veri kullanılır.
          </p>

          <div v-if="error" class="rpt-error">
            <i class="fa-solid fa-triangle-exclamation"></i> {{ error }}
          </div>
        </div>

        <!-- Footer -->
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" @click="emit('close')">İptal</button>
          <button class="eisa-btn eisa-btn-cta" :disabled="loading" @click="generate">
            <i class="fa-solid" :class="loading ? 'fa-circle-notch fa-spin' : 'fa-file-pdf'"></i>
            {{ loading ? 'Hazırlanıyor…' : 'Raporu Oluştur & Aç' }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.rpt-modal { width: min(520px, calc(100vw - 2rem)); }
.rpt-body  { display: flex; flex-direction: column; gap: 1rem; }
.rpt-field { display: flex; flex-direction: column; gap: 0.3rem; }
.rpt-date-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.rpt-radio {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
  background: #f9fafb;
  transition: border-color 0.15s;
}
.rpt-radio input { display: none; }
.rpt-radio.active { border-color: #B1121B; background: #fff5f5; color: #B1121B; }
.rpt-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
}
@media (max-width: 480px) {
  .rpt-date-row { grid-template-columns: 1fr; }
}
</style>
