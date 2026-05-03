<script setup>
/**
 * BaseInput — E-İSA Design System
 *
 * Props:
 *   modelValue : string | number         (v-model)
 *   label      : string                  (optional field label)
 *   type       : string                  (default: 'text')
 *   placeholder: string
 *   error      : string                  (error message; triggers red state)
 *   helper     : string                  (helper/hint text below input)
 *   disabled   : boolean
 *   id         : string                  (ties label htmlFor; auto-generated if omitted)
 *
 * Slots:
 *   icon-left  : leading icon (16-20 px SVG recommended)
 *   icon-right : trailing icon (use for actions like clear/search; replaces pw-toggle)
 *
 * Usage:
 *   <BaseInput
 *     v-model="email"
 *     label="E-posta"
 *     type="email"
 *     placeholder="ornek@eczane.com"
 *     :error="errors.email"
 *   >
 *     <template #icon-left>
 *       <MailIcon />
 *     </template>
 *   </BaseInput>
 */
import { ref, computed } from 'vue';

const props = defineProps({
  modelValue:  { type: [String, Number], default: '' },
  label:       { type: String,  default: '' },
  type:        { type: String,  default: 'text' },
  placeholder: { type: String,  default: '' },
  error:       { type: String,  default: '' },
  helper:      { type: String,  default: '' },
  disabled:    { type: Boolean, default: false },
  id:          { type: String,  default: '' },
});

const emit = defineEmits(['update:modelValue']);

// Auto-generate a unique id if none provided (for label-input linkage)
const uid = ref(`eisa-input-${Math.random().toString(36).slice(2, 9)}`);
const inputId = computed(() => props.id || uid.value);

// Password show/hide toggle
const showPw = ref(false);
const resolvedType = computed(() => {
  if (props.type !== 'password') return props.type;
  return showPw.value ? 'text' : 'password';
});
</script>

<template>
  <div class="bi-root" :class="{ 'bi-root--error': !!error, 'bi-root--disabled': disabled }">
    <!-- Label -->
    <label v-if="label" :for="inputId" class="bi-label">
      {{ label }}
    </label>

    <!-- Input wrapper -->
    <div class="bi-wrap">
      <!-- Left icon slot -->
      <span v-if="$slots['icon-left']" class="bi-icon bi-icon--left" aria-hidden="true">
        <slot name="icon-left" />
      </span>

      <input
        :id="inputId"
        :type="resolvedType"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        class="bi-input"
        :class="{
          'bi-input--icon-l': $slots['icon-left'],
          'bi-input--icon-r': $slots['icon-right'] || type === 'password',
        }"
        v-bind="$attrs"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />

      <!-- Password toggle (only when type="password") -->
      <button
        v-if="type === 'password'"
        type="button"
        class="bi-pw-btn"
        :aria-label="showPw ? 'Şifreyi gizle' : 'Şifreyi göster'"
        @click="showPw = !showPw"
      >
        <svg v-if="!showPw" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        <svg v-else fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
        </svg>
      </button>

      <!-- Right icon slot (non-password) -->
      <span v-else-if="$slots['icon-right']" class="bi-icon bi-icon--right" aria-hidden="true">
        <slot name="icon-right" />
      </span>
    </div>

    <!-- Error message -->
    <p v-if="error" class="bi-error" role="alert">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
      </svg>
      {{ error }}
    </p>

    <!-- Helper text -->
    <p v-else-if="helper" class="bi-helper">{{ helper }}</p>
  </div>
</template>

<!-- Disable attribute inheritance on root (let it land on input) -->
<script lang="ts">
export default { inheritAttrs: false };
</script>

<style scoped>
/* ─── Root ───────────────────────────────────── */
.bi-root {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  font-family: 'Figtree', system-ui, sans-serif;
}

/* ─── Label ──────────────────────────────────── */
.bi-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #374151;
  letter-spacing: 0.015em;
  cursor: pointer;
}
.bi-root--disabled .bi-label { color: #94A3B8; }

/* ─── Wrapper ─────────────────────────────────── */
.bi-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

/* ─── Input ──────────────────────────────────── */
.bi-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1.5px solid #E2E8F0;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-family: 'Figtree', system-ui, sans-serif;
  color: #0F172A;
  background: #F8FAFC;
  outline: none;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}
.bi-input::placeholder { color: #CBD5E1; }
.bi-input:focus {
  border-color: #2563EB;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
.bi-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #F1F5F9;
}

/* Paddings when icons are present */
.bi-input--icon-l { padding-left: 2.75rem; }
.bi-input--icon-r { padding-right: 2.75rem; }

/* Error state */
.bi-root--error .bi-input {
  border-color: #FCA5A5;
  background: #FFF5F5;
}
.bi-root--error .bi-input:focus {
  border-color: #EF4444;
  box-shadow: 0 0 0 3px rgba(239,68,68,0.12);
}

/* ─── Icons ──────────────────────────────────── */
.bi-icon {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94A3B8;
  pointer-events: none;
}
.bi-icon--left  { left: 0.9rem; }
.bi-icon--right { right: 0.9rem; }
.bi-icon :deep(svg) { width: 18px; height: 18px; }

/* ─── Password toggle ────────────────────────── */
.bi-pw-btn {
  position: absolute;
  right: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  background: none;
  border: none;
  cursor: pointer;
  color: #94A3B8;
  padding: 0;
  transition: color 0.15s ease;
}
.bi-pw-btn:hover { color: #475569; }
.bi-pw-btn svg { width: 18px; height: 18px; }

/* ─── Error / Helper text ────────────────────── */
.bi-error {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0;
  font-size: 0.8rem;
  color: #EF4444;
}
.bi-error svg { width: 14px; height: 14px; flex-shrink: 0; }

.bi-helper {
  margin: 0;
  font-size: 0.8rem;
  color: #94A3B8;
}
</style>
