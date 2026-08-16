<script setup>
/**
 * SessionsPanel — oturum listesi (loading / error / empty / table / sayfalama).
 *
 * Props:
 *   rows, loading, error, total, page, totalPages
 *   showEczane   — Admin: Eczane sütununu göster
 *   showKiosk    — Eczacı: Kiosk sütununu göster
 *   showHassas   — Eczacı: Hassas sütununu göster
 *   warnDanismanlik — Admin: Danışmanlık tipi için sarı badge
 *
 * Emits:
 *   change-page(newPage)
 *   open-detail(row)
 */
import { DURUM_LABEL, fmtDT } from '../../composables/useActivityFormatters.js';

const props = defineProps({
  rows:            { type: Array,   default: () => [] },
  loading:         Boolean,
  error:           { type: String,  default: '' },
  total:           { type: Number,  default: 0 },
  page:            { type: Number,  default: 1 },
  totalPages:      { type: Number,  default: 1 },
  showEczane:      Boolean,
  showKiosk:       Boolean,
  showHassas:      Boolean,
  warnDanismanlik: Boolean,
});
const emit = defineEmits(['change-page', 'open-detail']);
</script>

<template>
  <div v-if="loading" style="padding:3rem;text-align:center;color:#6B7280;">
    <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
  </div>
  <div v-else-if="error" class="eisa-error-banner" style="margin-bottom:1rem;">
    <i class="fa-solid fa-triangle-exclamation"></i> {{ error }}
  </div>
  <template v-else>
    <div v-if="!rows.length" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
      <i class="fa-regular fa-folder-open" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.75rem;"></i>
      <p>Bu filtreye ait kayıt bulunamadı.</p>
    </div>
    <div v-else class="eisa-panel">
      <div style="overflow-x:auto;">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>QR</th>
              <th v-if="showEczane">Eczane</th>
              <th v-if="showKiosk">Kiosk</th>
              <th>Tür</th>
              <th>Durum</th>
              <th v-if="showHassas">Hassas</th>
              <th>Danışma</th>
              <th>Tarih</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td style="font-family:'DM Mono',monospace;font-size:0.82rem;font-weight:700;">{{ row.qr_kodu }}</td>
              <td v-if="showEczane" style="font-size:0.82rem;">{{ row.eczane_adi || '—' }}</td>
              <td v-if="showKiosk" style="font-size:0.82rem;">{{ row.kiosk_ad || '—' }}</td>
              <td>
                <span
                  class="eisa-pill"
                  :class="warnDanismanlik && row.oturum_tipi === 'OZEL_DANISMANLIK' ? 'eisa-pill-warning' : 'eisa-pill-muted'"
                  style="font-size:0.7rem;"
                >
                  {{ row.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Danışmanlık' : 'Şikayet' }}
                </span>
              </td>
              <td>
                <span class="eisa-pill" :class="DURUM_LABEL[row.durum]?.cls || 'eisa-pill-muted'" style="font-size:0.7rem;">
                  {{ DURUM_LABEL[row.durum]?.text || row.durum }}
                </span>
              </td>
              <td v-if="showHassas">
                <i v-if="row.hassas_akis" class="fa-solid fa-triangle-exclamation" style="color:#F59E0B;" title="Hassas konu"></i>
                <span v-else style="color:#6B7280;">—</span>
              </td>
              <td>
                <i v-if="row.danisma_tamamlandi" class="fa-solid fa-check-circle" style="color:#10B981;"></i>
                <span v-else style="color:#6B7280;">Bekliyor</span>
              </td>
              <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.olusturulma_tarihi) }}</td>
              <td>
                <button class="eisa-btn eisa-btn-ghost" style="font-size:0.75rem;padding:0.25rem 0.5rem;" @click="emit('open-detail', row)">
                  Detay
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:0.8rem;color:#9CA3AF;">{{ total }} kayıt</span>
        <div style="display:flex;gap:0.5rem;">
          <button class="eisa-btn eisa-btn-ghost" :disabled="page <= 1" @click="emit('change-page', page - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span style="font-size:0.8rem;padding:0.4rem 0.6rem;">{{ page }} / {{ totalPages }}</span>
          <button class="eisa-btn eisa-btn-ghost" :disabled="page >= totalPages" @click="emit('change-page', page + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </template>
</template>
