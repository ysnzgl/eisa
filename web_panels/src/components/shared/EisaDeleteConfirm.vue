<script setup>
/**
 * EisaDeleteConfirm — Silme onay modal
 *
 * Props:
 *   open      : boolean  — modalın açık/kapal durumu
 *   title     : string   — modalı başlığı (ör. "Eczane Sil")
 *   message   : string   — açıklama metni
 *   confirmLabel : string — onay butonu etiketi (default: "Evet, Sil")
 *   loading   : boolean  — silme işlemi devam ediyor mu
 *
 * Emits:
 *   confirm   — kullanıcıc onay butonuna tklad
 *   cancel    — kullanıcıc iptal etti / backdrop'a tklad
 */
defineProps({
  open:         { type: Boolean, default: false },
  title:        { type: String,  default: 'Silme Onay' },
  message:      { type: String,  default: 'Bu ilem geri alnamaz.' },
  confirmLabel: { type: String,  default: 'Evet, Sil' },
  loading:      { type: Boolean, default: false },
});
defineEmits(['confirm', 'cancel']);
</script>

<template>
  <Teleport to="body">
    <Transition name="backdrop">
      <div
        v-if="open"
        id="delete-confirm-backdrop"
        class="eisa-modal-backdrop"
        @click.self="$emit('cancel')"
      >
        <Transition name="modal" appear>
          <div
            v-if="open"
            id="delete-confirm-dialog"
            class="eisa-modal"
            style="max-width: 400px;"
            role="alertdialog"
            :aria-label="title"
          >
            <div class="eisa-modal-body" style="text-align: center; padding: 1.75rem 1.5rem 1.25rem;">
              <div class="delete-confirm-icon">
                <i class="fa-solid fa-triangle-exclamation"></i>
              </div>
              <h3 class="delete-confirm-title">{{ title }}</h3>
              <p class="delete-confirm-message">{{ message }}</p>
            </div>
            <div class="eisa-modal-footer">
              <button
                name="cancel"
                class="eisa-btn eisa-btn-ghost"
                :disabled="loading"
                @click="$emit('cancel')"
              >
                Vazgeç
              </button>
              <button
                name="confirm"
                class="eisa-btn eisa-btn-danger"
                :disabled="loading"
                @click="$emit('confirm')"
              >
                <i v-if="loading" class="fa-solid fa-circle-notch fa-spin"></i>
                <i v-else class="fa-solid fa-trash"></i>
                {{ loading ? 'Siliniyor…' : confirmLabel }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
