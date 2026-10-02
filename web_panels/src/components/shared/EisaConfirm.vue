<script setup>
import { useConfirm } from '../../composables/useConfirm.js';

const { confirmState: s, _doConfirm, _doCancel } = useConfirm();

const VARIANT_BTN = {
  danger:  'eisa-btn-danger',
  warning: 'eisa-btn-warning',
  cta:     'eisa-btn-cta',
};
const VARIANT_ICON = {
  danger:  'fa-triangle-exclamation',
  warning: 'fa-circle-exclamation',
  cta:     'fa-circle-question',
};
</script>

<template>
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="s.open"
        class="eisa-modal-backdrop"
        @click.self="_doCancel"
      >
        <Transition name="modal" appear>
          <div
            v-if="s.open"
            class="eisa-modal eisa-confirm-dialog"
            role="alertdialog"
            :aria-label="s.title"
          >
            <div class="eisa-modal-body eisa-confirm-body">
              <div class="eisa-confirm-icon" :class="`eisa-confirm-icon--${s.variant}`">
                <i class="fa-solid" :class="VARIANT_ICON[s.variant] || 'fa-circle-question'"></i>
              </div>
              <h3 class="eisa-confirm-title">{{ s.title }}</h3>
              <p class="eisa-confirm-message">{{ s.message }}</p>
            </div>
            <div class="eisa-modal-footer">
              <button class="eisa-btn eisa-btn-ghost" @click="_doCancel">
                Vazgeç
              </button>
              <button
                class="eisa-btn"
                :class="VARIANT_BTN[s.variant] || 'eisa-btn-cta'"
                @click="_doConfirm"
              >
                {{ s.confirmLabel }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.eisa-confirm-dialog { max-width: 400px; }
.eisa-confirm-body { text-align: center; padding: 1.75rem 1.5rem 1.25rem; }
.eisa-confirm-icon {
  width: 52px; height: 52px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 1.4rem; margin-bottom: .875rem;
}
.eisa-confirm-icon--danger  { background: #FEF2F2; color: #DC2626; }
.eisa-confirm-icon--warning { background: #FFFBEB; color: #D97706; }
.eisa-confirm-icon--cta     { background: #EFF6FF; color: #2563EB; }
.eisa-confirm-title {
  font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700;
  color: #1F2937; margin: 0 0 .4rem;
}
.eisa-confirm-message { font-size: .875rem; color: #6B7280; margin: 0; line-height: 1.5; }
</style>
