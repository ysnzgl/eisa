<script setup>
/**
 * EisaPageHeader — Sayfa başlığı bölümü
 *
 * Props:
 *   eyebrow  : string  — küçük üst etiket (ör. "Admin Panel")
 *   title    : string  — sayfa ana başlığı
 *   subtitle : string  — isteğe bal açıklama
 *
 * Slots:
 *   #actions — sağ tarafa hizalanan buton/kontrol alan
 */
defineProps({
  eyebrow:  { type: String, default: '' },
  title:    { type: String, default: '' },
  subtitle: { type: String, default: '' },
});
</script>

<template>
  <div class="eisa-page-header">
    <div>
      <p v-if="eyebrow" class="eisa-eyebrow">{{ eyebrow }}</p>
      <h1 class="eisa-page-title">{{ title }}</h1>
      <p v-if="subtitle" class="eisa-page-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="eisa-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>
