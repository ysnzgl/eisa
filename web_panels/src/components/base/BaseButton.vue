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

<style scoped>
/* ─── Base ───────────────────────────────────── */
.eisa-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: none;
  border-radius: 12px;
  font-family: 'Figtree', system-ui, sans-serif;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  transition:
    transform 0.15s ease,
    box-shadow 0.2s ease,
    opacity 0.2s ease,
    background-color 0.2s ease;
}
.eisa-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none !important;
}
.eisa-btn--full { width: 100%; }

/* ─── Sizes ──────────────────────────────────── */
.eisa-btn--sm { font-size: 0.8125rem; padding: 0.5rem 1rem; }
.eisa-btn--md { font-size: 0.9375rem; padding: 0.72rem 1.375rem; }
.eisa-btn--lg { font-size: 1rem;      padding: 0.875rem 1.75rem; }

/* ─── Primary ────────────────────────────────── */
.eisa-btn--primary {
  background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #3B82F6 100%);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(37,99,235,0.35);
}
.eisa-btn--primary::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, transparent 60%);
  pointer-events: none;
}
.eisa-btn--primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 7px 22px rgba(37,99,235,0.45);
}
.eisa-btn--primary:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(37,99,235,0.3);
}

/* ─── Secondary ──────────────────────────────── */
.eisa-btn--secondary {
  background: #EFF6FF;
  color: #2563EB;
  border: 1.5px solid #BFDBFE;
  box-shadow: none;
}
.eisa-btn--secondary:hover:not(:disabled) {
  background: #DBEAFE;
  border-color: #93C5FD;
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(37,99,235,0.12);
}
.eisa-btn--secondary:active:not(:disabled) {
  transform: translateY(0);
}

/* ─── Ghost ──────────────────────────────────── */
.eisa-btn--ghost {
  background: transparent;
  color: #475569;
  border: 1.5px solid #E2E8F0;
  box-shadow: none;
}
.eisa-btn--ghost:hover:not(:disabled) {
  background: #F8FAFC;
  border-color: #CBD5E1;
  color: #0F172A;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(11,29,58,0.06);
}
.eisa-btn--ghost:active:not(:disabled) {
  transform: translateY(0);
}

/* ─── Danger ─────────────────────────────────── */
.eisa-btn--danger {
  background: linear-gradient(135deg, #B91C1C 0%, #DC2626 55%, #EF4444 100%);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(220,38,38,0.3);
}
.eisa-btn--danger:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 7px 20px rgba(220,38,38,0.4);
}
.eisa-btn--danger:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(220,38,38,0.25);
}

/* ─── Loading dots ───────────────────────────── */
.btn-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-dots span {
  display: block;
  width: 5px; height: 5px;
  background: currentColor;
  border-radius: 50%;
  animation: btnDot 1.2s ease-in-out infinite;
}
.btn-dots span:nth-child(2) { animation-delay: 0.18s; }
.btn-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes btnDot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.45; }
  40%           { transform: scale(1);   opacity: 1;    }
}

/* ─── Icon ───────────────────────────────────── */
.btn-icon-left {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
</style>
