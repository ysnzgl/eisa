<script setup>
import { _toasts, toast } from '../../composables/useToast.js';
</script>

<template>
  <teleport to="body">
    <div class="toast-portal" aria-live="polite">
      <transition-group name="toast" tag="div" class="toast-stack">
        <div
          v-for="t in _toasts"
          :key="t.id"
          class="toast-item"
          :class="`toast-${t.type}`"
          @click="toast.dismiss(t.id)"
        >
          <span class="toast-icon">
            <i v-if="t.type === 'success'" class="fa-solid fa-circle-check"></i>
            <i v-else-if="t.type === 'error'"   class="fa-solid fa-circle-xmark"></i>
            <i v-else-if="t.type === 'warning'" class="fa-solid fa-triangle-exclamation"></i>
            <i v-else                            class="fa-solid fa-circle-info"></i>
          </span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click.stop="toast.dismiss(t.id)">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<style scoped>
.toast-portal {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 99999;
  pointer-events: none;
}
.toast-stack {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  align-items: flex-end;
}
.toast-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 280px;
  max-width: 420px;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: 0 8px 24px rgba(0,0,0,.12), 0 2px 6px rgba(0,0,0,.08);
  cursor: pointer;
  pointer-events: all;
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #0f172a;
}
.toast-success { border-left: 4px solid #22c55e; }
.toast-success .toast-icon { color: #22c55e; }
.toast-error   { border-left: 4px solid #ef4444; }
.toast-error   .toast-icon { color: #ef4444; }
.toast-warning { border-left: 4px solid #f59e0b; }
.toast-warning .toast-icon { color: #f59e0b; }
.toast-info    { border-left: 4px solid #6366f1; }
.toast-info    .toast-icon { color: #6366f1; }

.toast-icon { font-size: 1rem; flex-shrink: 0; }
.toast-msg  { flex: 1; line-height: 1.4; }
.toast-close {
  background: none; border: none; cursor: pointer;
  color: #94a3b8; padding: 0; font-size: 0.8rem;
  flex-shrink: 0; opacity: 0.7;
}
.toast-close:hover { opacity: 1; }

/* Transition */
.toast-enter-active { transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from   { opacity: 0; transform: translateX(40px) scale(0.95); }
.toast-leave-to     { opacity: 0; transform: translateX(40px); }
</style>
