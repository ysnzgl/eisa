<script setup>
/**
 * SalesPanel — satış listesi (loading / error / empty / table / sayfalama).
 *
 * Props:
 *   rows, loading, error, total, summary, page, totalPages
 *   showEczane — Admin: Eczane sütunu; false → Kiosk sütunu
 *
 * Emits:
 *   change-page(newPage)
 *   open-detail(row)
 */
import { fmtDT } from '../../composables/useActivityFormatters.js';

const props = defineProps({
  rows:       { type: Array,  default: () => [] },
  loading:    Boolean,
  error:      { type: String, default: '' },
  total:      { type: Number, default: 0 },
  summary:    { type: Object, default: () => ({ recommended: 0, sold: 0 }) },
  page:       { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  showEczane: Boolean,
});
const emit = defineEmits(['change-page', 'open-detail']);

function getSoldCount(row) {
  if (!row.etken_madde_detaylari?.length) return 0;
  return row.etken_madde_detaylari.filter(ing => ing.satildi).length;
}

function getTotalCount(row) {
  return row.etken_madde_detaylari?.length || 0;
}
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
      <p>Bu filtreye ait satış kaydı bulunamadı.</p>
    </div>
    <div v-else class="eisa-panel">
      <div style="overflow-x:auto;">
        <table class="eisa-table">
          <thead>
            <tr>
              <th style="min-width:110px;">Tarih / Saat</th>
              <th v-if="showEczane" style="min-width:140px;">Eczane</th>
              <th style="min-width:120px;">Kiosk</th>
              <th style="min-width:100px;">Tür</th>
              <th style="min-width:100px;">Önerilen / Satılan</th>
              <th style="min-width:200px;">Etken Maddeler</th>
              <th style="min-width:220px;">Danışma Notu</th>
              <th style="width:80px;"></th>
            </tr>
          </thead>
          <tbody>
            <tr style="background:rgba(13,148,136,0.08);">
              <td
                :colspan="showEczane ? 4 : 3"
                style="font-size:0.82rem;font-weight:700;color:#0F766E;"
              >
                Toplam
              </td>
              <td style="font-size:0.82rem;">
                <span style="font-weight:700;color:#111827;">{{ summary.recommended }} / {{ summary.sold }}</span>
              </td>
              <td style="font-size:0.78rem;color:#0F766E;">
                {{ summary.sold }} satılan etken madde
              </td>
              <td></td>
              <td></td>
            </tr>
            <tr v-for="row in rows" :key="row.id">
              <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.olusturulma_tarihi) }}</td>
              <td v-if="showEczane" style="font-size:0.82rem;">
                <div style="font-weight:600;">{{ row.eczane_adi || '—' }}</div>
              </td>
              <td style="font-size:0.82rem;">
                <div style="font-weight:600;">{{ row.kiosk_ad || '—' }}</div>
              </td>
              <td>
                <span
                  class="eisa-pill"
                  :class="row.oturum_tipi === 'OZEL_DANISMANLIK' ? 'eisa-pill-info' : 'eisa-pill-muted'"
                  style="font-size:0.7rem;"
                >
                  {{ row.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Danışmanlık' : 'Şikayet' }}
                </span>
              </td>
              <td style="font-size:0.82rem;">
                <div style="display:flex;align-items:center;gap:0.5rem;">
                  <span style="font-weight:700;color:#111827;">{{ getTotalCount(row) }} / {{ getSoldCount(row) }}</span>
                  <i v-if="getSoldCount(row) > 0" class="fa-solid fa-check-circle" style="color:#059669;font-size:0.85rem;"></i>
                </div>
              </td>
              <td style="font-size:0.8rem;max-width:300px;">
                <div v-if="row.etken_madde_detaylari?.length" style="display:flex;flex-wrap:wrap;gap:0.35rem;">
                  <span
                    v-for="(ing, idx) in row.etken_madde_detaylari"
                    :key="idx"
                    class="eisa-pill"
                    :class="ing.satildi ? 'eisa-pill-success' : 'eisa-pill-muted'"
                    style="font-size:0.72rem;"
                  >
                    <i v-if="ing.satildi" class="fa-solid fa-check" style="font-size:0.65rem;margin-right:0.2rem;"></i>
                    {{ ing.ad }}
                  </span>
                </div>
                <span v-else style="color:#6B7280;">—</span>
              </td>
              <td style="font-size:0.82rem;max-width:250px;color:#374151;">
                <span v-if="row.danisma_notu" :title="row.danisma_notu" style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                  {{ row.danisma_notu }}
                </span>
                <span v-else style="color:#6B7280;">—</span>
              </td>
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
        <span style="font-size:0.8rem;color:#9CA3AF;">{{ total }} satış</span>
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
