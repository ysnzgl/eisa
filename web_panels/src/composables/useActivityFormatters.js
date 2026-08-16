/**
 * Ortak kiosk-activity formatter sabitleri.
 * SessionsPanel, SalesPanel, ImpressionsPanel, EventsPanel tarafından kullanılır.
 */
export const DURUM_LABEL = {
  COMPLETED: { text: 'Tamamlandı',   cls: 'eisa-pill-success' },
  ABANDONED: { text: 'Terk Edildi',  cls: 'eisa-pill-warning' },
  EXPIRED:   { text: 'Süresi Doldu', cls: 'eisa-pill-danger'  },
};

export function fmtDT(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
