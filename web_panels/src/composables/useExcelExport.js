/**
 * Excel dışa aktarım yardımcısı (SheetJS/xlsx).
 *
 * exportSessions  — oturum listesi (sessions / sales tabları)
 * exportImpressions — kampanya gösterimleri
 * exportToExcel   — ham rows + columns ile doğrudan kullanım
 */
import * as XLSX from 'xlsx';
import { ref } from 'vue';

function _buildSheet(rows, columns) {
  const header = columns.map((c) => c.label);
  const data = rows.map((row) =>
    columns.map((c) => {
      const val = typeof c.fn === 'function' ? c.fn(row) : (row[c.key] ?? '');
      return val === null || val === undefined ? '' : val;
    })
  );
  const ws = XLSX.utils.aoa_to_sheet([header, ...data]);
  ws['!cols'] = header.map((h, i) => ({
    wch: Math.max(h.length, ...data.map((r) => String(r[i] ?? '').length)) + 2,
  }));
  return ws;
}

export function useExcelExport() {
  const exporting = ref(false);

  function exportToExcel(rows, columns, filename = 'rapor.xlsx', sheetName = 'Rapor') {
    const ws = _buildSheet(rows, columns);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
    XLSX.writeFile(wb, filename);
  }

  async function exportSessions(fetchFn, params = {}, filename = 'oturumlar.xlsx') {
    exporting.value = true;
    try {
      const { data } = await fetchFn({ ...params, page_size: 1000, page: 1 });
      const rows = data.results ?? data;
      exportToExcel(rows, SESSION_COLS, filename);
    } finally {
      exporting.value = false;
    }
  }

  async function exportSales(fetchFn, params = {}, filename = 'satislar.xlsx') {
    exporting.value = true;
    try {
      const { data } = await fetchFn({ ...params, sold: 'true', page_size: 1000, page: 1 });
      const rows = data.results ?? data;
      exportToExcel(rows, SALES_COLS, filename);
    } finally {
      exporting.value = false;
    }
  }

  async function exportImpressions(fetchFn, params = {}, filename = 'gosterimler.xlsx') {
    exporting.value = true;
    try {
      const { data } = await fetchFn({ ...params, page_size: 1000, page: 1 });
      const rows = data.results ?? data;
      exportToExcel(rows, IMPRESSION_COLS, filename);
    } finally {
      exporting.value = false;
    }
  }

  return { exporting, exportToExcel, exportSessions, exportSales, exportImpressions };
}

// ── Kolon tanımları ───────────────────────────────────────────────────────────

const _fmtDate = (iso) => iso ? new Date(iso).toLocaleString('tr-TR') : '';
const _fmtTip  = (r)   => r.oturum_tipi === 'SIKAYET' ? 'Şikayet' : 'Özel Danışmanlık';
const _fmtSold = (r)   => {
  if (r.status === 2 || r.sold === true)  return 'Satış Yapıldı';
  if (r.status === 3 || r.sold === false) return 'Satış Yapılmadı';
  return '—';
};

const SESSION_COLS = [
  { label: 'ID',                  key: 'id' },
  { label: 'QR Kodu',             key: 'qr_kodu' },
  { label: 'Kiosk',               key: 'kiosk_ad' },
  { label: 'Eczane',              key: 'eczane_adi' },
  { label: 'Yaş Aralığı',         key: 'yas_araligi_ad' },
  { label: 'Cinsiyet',            key: 'cinsiyet_ad' },
  { label: 'Kategori',            key: 'kategori_adi' },
  { label: 'İşlem Türü',          fn: _fmtTip },
  { label: 'Durum',               key: 'durum' },
  { label: 'Danışma Tamamlandı',  fn: (r) => r.danisma_tamamlandi ? 'Evet' : 'Hayır' },
  { label: 'Satış Sonucu',        fn: _fmtSold },
  { label: 'Oluşturulma Tarihi',  fn: (r) => _fmtDate(r.olusturulma_tarihi) },
];

const SALES_COLS = [
  { label: 'ID',                    key: 'id' },
  { label: 'QR Kodu',               key: 'qr_kodu' },
  { label: 'Kiosk',                 key: 'kiosk_ad' },
  { label: 'Eczane',                key: 'eczane_adi' },
  { label: 'Yaş Aralığı',           key: 'yas_araligi_ad' },
  { label: 'Cinsiyet',              key: 'cinsiyet_ad' },
  { label: 'Kategori',              key: 'kategori_adi' },
  { label: 'Satılan Etken Maddeler', fn: (r) => (r.etken_madde_adlari ?? []).join(', ') },
  { label: 'Sonuç Tarihi',          fn: (r) => _fmtDate(r.result_at) },
];

const IMPRESSION_COLS = [
  { label: 'Kiosk',          key: 'kiosk_ad' },
  { label: 'Eczane',         key: 'eczane_adi' },
  { label: 'Kampanya',       key: 'campaign_adi' },
  { label: 'Creative',       key: 'creative_adi' },
  { label: 'Süre (sn)',      key: 'duration_played' },
  { label: 'Oynatma Tarihi', fn: (r) => _fmtDate(r.played_at) },
];
