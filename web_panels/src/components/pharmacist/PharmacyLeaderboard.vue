<script setup>
/**
 * Eczacının tüm aktif eczaneler arasındaki etkileşim ve satış sıralaması.
 * Diğer eczane adı/bilgisi gösterilmez; yalnız sıra ve toplu istatistik gösterilir.
 */
import { ref, onMounted } from 'vue';
import { http } from '../../services/api';

const data    = ref(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const { data: res } = await http.get('/api/pharmacies/me/leaderboard/');
    data.value = res;
  } catch { /* interceptor handles errors */ }
  finally { loading.value = false; }
});

const SECTIONS = [
  {
    key:   'etkilesim',
    label: 'Etkileşim',
    icon:  'fa-arrow-right-arrow-left',
    color: '#2563EB',
    unit:  'etkileşim',
  },
  {
    key:   'satis',
    label: 'Satış',
    icon:  'fa-cart-shopping',
    color: '#10B981',
    unit:  'satış',
  },
];

function rankStyle(sira) {
  if (sira === 1) return { icon: 'fa-trophy',       bg: 'linear-gradient(135deg,#F59E0B 0%,#D97706 100%)', glow: '#F59E0B' };
  if (sira === 2) return { icon: 'fa-medal',        bg: 'linear-gradient(135deg,#94A3B8 0%,#64748B 100%)', glow: '#94A3B8' };
  if (sira === 3) return { icon: 'fa-medal',        bg: 'linear-gradient(135deg,#D97706 0%,#92400E 100%)', glow: '#CD7F32' };
  if (sira <= 10) return { icon: 'fa-ranking-star', bg: 'linear-gradient(135deg,#7C3AED 0%,#5B21B6 100%)', glow: '#7C3AED' };
  return              { icon: 'fa-hashtag',         bg: 'linear-gradient(135deg,#475569 0%,#1E293B 100%)', glow: '#64748b' };
}

function barPct(skor, en_yuksek) {
  if (!en_yuksek) return 4;
  return Math.max(4, Math.round(skor / en_yuksek * 100));
}

function rankLabel(n) {
  const s = String(n);
  if (s.endsWith('1') && n !== 11) return `${n}.`;
  if (s.endsWith('2') && n !== 12) return `${n}.`;
  if (s.endsWith('3') && n !== 13) return `${n}.`;
  return `${n}.`;
}
</script>

<template>
  <div class="eisa-panel lb-panel">

    <!-- Header -->
    <div class="lb-header">
      <div>
        <p class="eisa-eyebrow" style="font-size:0.63rem;">SIRALAMALAR</p>
        <h2 class="eisa-panel-title" style="display:flex;align-items:center;gap:0.45rem;font-size:1rem;">
          <i class="fa-solid fa-ranking-star" style="color:#F59E0B;"></i>
          Eczaneler Arasındaki Yeriniz
        </h2>
      </div>
      <div class="lb-privacy-badge">
        <i class="fa-solid fa-shield-halved"></i>
        <span>Diğer eczane bilgileri gizlidir</span>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="lb-skeleton-grid">
      <div class="lb-skeleton" v-for="i in 2" :key="i"></div>
    </div>

    <!-- Cards -->
    <div v-else-if="data" class="lb-grid">
      <div
        v-for="section in SECTIONS"
        :key="section.key"
        class="lb-card"
      >
        <!-- top color stripe -->
        <div class="lb-stripe" :style="{ background: section.color }"></div>

        <!-- Section label -->
        <p class="lb-section-title">
          <i class="fa-solid" :class="section.icon" :style="{ color: section.color }"></i>
          {{ section.label }}
        </p>

        <template v-if="data[section.key]">
          <!-- Rank badge + text -->
          <div class="lb-rank-row">
            <div
              class="lb-badge"
              :style="{
                background: rankStyle(data[section.key].sira).bg,
                boxShadow: `0 8px 28px ${rankStyle(data[section.key].sira).glow}55`,
              }"
            >
              <i class="fa-solid lb-badge-icon" :class="rankStyle(data[section.key].sira).icon"></i>
              <span class="lb-badge-num">{{ data[section.key].sira }}</span>
            </div>
            <div class="lb-rank-info">
              <span class="lb-rank-main">{{ rankLabel(data[section.key].sira) }} Sıra</span>
              <span class="lb-rank-sub">{{ data[section.key].toplam_eczane }} eczane arasında</span>
            </div>
          </div>

          <!-- Score -->
          <div class="lb-score-row">
            <span class="lb-score-num">{{ data[section.key].skor.toLocaleString('tr-TR') }}</span>
            <span class="lb-score-unit">{{ section.unit }}</span>
          </div>

          <!-- Progress bar -->
          <div class="lb-bar-wrap">
            <div class="lb-bar-labels">
              <span class="lb-bar-you">
                <span class="lb-you-tag">SİZ</span>
                {{ barPct(data[section.key].skor, data[section.key].en_yuksek_skor) }}%
              </span>
              <span class="lb-bar-leader">
                <i class="fa-solid fa-crown" style="font-size:0.65rem;color:#F59E0B;"></i>
                Lider: {{ data[section.key].en_yuksek_skor.toLocaleString('tr-TR') }}
              </span>
            </div>
            <div class="lb-bar-track">
              <div
                class="lb-bar-fill"
                :style="{
                  width: barPct(data[section.key].skor, data[section.key].en_yuksek_skor) + '%',
                  background: `linear-gradient(90deg, ${section.color}cc, ${section.color})`,
                }"
              ></div>
            </div>
          </div>

          <!-- Percentile pill -->
          <div class="lb-pct-pill" :style="{ borderColor: section.color + '44', color: section.color }">
            <i class="fa-solid fa-chart-line" style="font-size:0.7rem;"></i>
            Eczanelerin
            <strong>%{{ data[section.key].yuzdelik }}'inden öndeyiz</strong>
          </div>
        </template>

        <div v-else class="lb-empty">Henüz veri yok</div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.lb-panel { margin-bottom: 1.25rem; overflow: hidden; }

/* ── Header ──────────────────────────────────────────────── */
.lb-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 1.25rem 0.85rem;
  gap: 1rem;
  border-bottom: 1px solid #f1f5f9;
}
.lb-privacy-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: #059669;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 99px;
  padding: 0.28rem 0.7rem;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── Skeleton ────────────────────────────────────────────── */
.lb-skeleton-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 1.25rem; }
.lb-skeleton {
  height: 240px;
  border-radius: 14px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 400% 100%;
  animation: lb-shimmer 1.6s ease-in-out infinite;
}
@keyframes lb-shimmer {
  0%   { background-position: 100% 0 }
  100% { background-position: -100% 0 }
}

/* ── Grid & Cards ────────────────────────────────────────── */
.lb-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 1.25rem; }

.lb-card {
  position: relative;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.1rem 1.1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  overflow: hidden;
}
.lb-stripe {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  border-radius: 14px 14px 0 0;
}
.lb-section-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  font-weight: 800;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.1rem;
}

/* ── Rank row ────────────────────────────────────────────── */
.lb-rank-row { display: flex; align-items: center; gap: 1rem; }
.lb-badge {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  flex-shrink: 0;
  transition: transform 0.2s;
}
.lb-card:hover .lb-badge { transform: scale(1.06); }
.lb-badge-icon { font-size: 1rem; color: rgba(255,255,255,0.8); line-height: 1; }
.lb-badge-num { font-size: 1.65rem; font-weight: 900; color: #fff; line-height: 1; font-variant-numeric: tabular-nums; }
.lb-rank-info { display: flex; flex-direction: column; gap: 0.1rem; }
.lb-rank-main { font-size: 1.35rem; font-weight: 800; color: #0f172a; line-height: 1.1; }
.lb-rank-sub  { font-size: 0.72rem; color: #64748b; }

/* ── Score ───────────────────────────────────────────────── */
.lb-score-row { display: flex; align-items: baseline; gap: 0.3rem; }
.lb-score-num  { font-size: 2.1rem; font-weight: 900; color: #0f172a; line-height: 1; font-variant-numeric: tabular-nums; }
.lb-score-unit { font-size: 0.78rem; color: #64748b; font-weight: 600; }

/* ── Progress bar ────────────────────────────────────────── */
.lb-bar-wrap { display: flex; flex-direction: column; gap: 0.3rem; }
.lb-bar-labels { display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem; color: #64748b; }
.lb-bar-you   { display: flex; align-items: center; gap: 0.35rem; font-weight: 700; color: #1e293b; }
.lb-you-tag {
  font-size: 0.58rem;
  font-weight: 900;
  letter-spacing: 0.06em;
  background: #1e293b;
  color: #fff;
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
}
.lb-bar-leader { display: flex; align-items: center; gap: 0.25rem; }
.lb-bar-track {
  height: 10px;
  background: #e2e8f0;
  border-radius: 99px;
  overflow: hidden;
}
.lb-bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 1.2s cubic-bezier(.16,1,.3,1);
  min-width: 4%;
}

/* ── Percentile pill ─────────────────────────────────────── */
.lb-pct-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid;
  border-radius: 8px;
  padding: 0.35rem 0.65rem;
  background: #fff;
  align-self: flex-start;
}
.lb-pct-pill strong { font-weight: 900; }

.lb-empty { font-size: 0.82rem; color: #9ca3af; text-align: center; padding: 1.5rem 0; }

@media (max-width: 640px) {
  .lb-grid, .lb-skeleton-grid { grid-template-columns: 1fr; }
  .lb-header { flex-direction: column; gap: 0.6rem; }
}
</style>
