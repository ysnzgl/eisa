<script setup>
/**
 * EisaStatCard — KPI istatistik kart
 *
 * Props:
 *   label    : string  — kart başlığı (ör. "Toplam Kullanc")
 *   value    : string | number — ana değer
 *   sub      : string  — alt açıklama (opsiyonel)
 *   icon     : string  — FontAwesome icon class (ör. "fa-solid fa-users")
 *   accent   : 'blue' | 'green' | 'teal' | 'red' | 'amber' | 'default'
 */
defineProps({
  label:  { type: String,  default: '' },
  value:  { type: [String, Number], default: '—' },
  sub:    { type: String,  default: '' },
  icon:   { type: String,  default: '' },
  accent: { type: String,  default: 'default' },
});
</script>

<template>
  <div class="eisa-stat-card" :class="`eisa-stat-card--${accent}`">
    <div class="eisa-stat-card-inner">
      <div v-if="icon" class="eisa-stat-icon" :class="`eisa-stat-icon--${accent}`">
        <i :class="icon"></i>
      </div>
      <div class="eisa-stat-text">
        <p class="eisa-stat-label">{{ label }}</p>
        <p class="eisa-stat-value">{{ value }}</p>
        <p v-if="sub" class="eisa-stat-sub">{{ sub }}</p>
      </div>
    </div>
  </div>
</template>
