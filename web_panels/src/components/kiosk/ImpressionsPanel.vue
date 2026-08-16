<script setup>
/**
 * ImpressionsPanel — kampanya gösterim listesi (loading / error / empty / table / sayfalama).
 *
 * Props:
 *   rows, loading, error, total, page, totalPages
 *   showEczane — Admin: Eczane sütunu
 *
 * Emits:
 *   change-page(newPage)
 */
import { fmtDT } from '../../composables/useActivityFormatters.js';

const props = defineProps({
  rows:       { type: Array,  default: () => [] },
  loading:    Boolean,
  error:      { type: String, default: '' },
  total:      { type: Number, default: 0 },
  page:       { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  showEczane: Boolean,
});
const emit = defineEmits(['change-page']);
</script>

<template>
  <div v-if="loading" style="padding:3rem;text-align:center;color:#6B7280;">
    <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
  </div>
  <div v-else-if="error" class="eisa-error-banner">
    <i class="fa-solid fa-triangle-exclamation"></i> {{ error }}
  </div>
  <template v-else>
    <div v-if="!rows.length" class="eisa-panel" style="padding:3rem;text-align:center;color:#6B7280;">
      <i class="fa-regular fa-folder-open" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.75rem;"></i>
      <p>Bu filtreye ait gösterim bulunamadı.</p>
    </div>
    <div v-else class="eisa-panel">
      <div style="overflow-x:auto;">
        <table class="eisa-table">
          <thead>
            <tr>
              <th>Kampanya</th>
              <th v-if="showEczane">Eczane</th>
              <th>Kiosk</th>
              <th>Süre</th>
              <th>Tarih</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.campaign_adi || row.house_ad_adi || '—' }}</td>
              <td v-if="showEczane" style="font-size:0.82rem;">{{ row.eczane_adi || '—' }}</td>
              <td style="font-size:0.82rem;">{{ row.kiosk_ad || '—' }}</td>
              <td>{{ row.duration_played }}sn</td>
              <td style="white-space:nowrap;font-size:0.78rem;color:#9CA3AF;">{{ fmtDT(row.played_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:0.8rem;color:#9CA3AF;">{{ total }} gösterim</span>
        <div v-if="totalPages > 1" style="display:flex;gap:0.5rem;">
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
