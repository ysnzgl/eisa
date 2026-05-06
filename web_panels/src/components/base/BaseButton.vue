<script setup>
/**
 * BaseButton — E-İSA Design System
 *
 * Props:
 *   variant  : 'primary' | 'secondary' | 'ghost' | 'danger'  (default: 'primary')
 *   size     : 'sm' | 'md' | 'lg'                            (default: 'md')
 *   loading  : boolean                                         (default: false)
 *   disabled : boolean                                         (default: false)
 *   fullWidth: boolean                                         (default: false)
 *   type     : 'button' | 'submit' | 'reset'                  (default: 'button')
 *
 * Slots:
 *   default  : button label content
 *   icon-left : optional leading icon
 *
 * Usage:
 *   <BaseButton variant="primary" size="md" :loading="saving" @click="save">
 *     Kaydet
 *   </BaseButton>
 */
defineProps({
  variant:   { type: String, default: 'primary' },
  size:      { type: String, default: 'md' },
  loading:   { type: Boolean, default: false },
  disabled:  { type: Boolean, default: false },
  fullWidth: { type: Boolean, default: false },
  type:      { type: String, default: 'button' },
});
</script>

<template>
  <button
    :type="type"
    class="eisa-btn"
    :class="[
      `eisa-btn--${variant}`,
      `eisa-btn--${size}`,
      { 'eisa-btn--full': fullWidth, 'eisa-btn--loading': loading },
    ]"
    :disabled="disabled || loading"
  >
    <!-- Leading icon slot -->
    <span v-if="$slots['icon-left'] && !loading" class="btn-icon-left" aria-hidden="true">
      <slot name="icon-left" />
    </span>

    <!-- Loading dots -->
    <span v-if="loading" class="btn-dots" aria-label="Yükleniyor">
      <span /><span /><span />
    </span>

    <!-- Label -->
    <span v-if="!loading" class="btn-label">
      <slot />
    </span>
  </button>
</template>
