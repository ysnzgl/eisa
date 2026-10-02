/**
 * useConfirm — programmatic confirmation modal
 *
 * await confirm({ title, message, confirmLabel, variant })
 * → true if user confirmed, false if cancelled
 *
 * variant: 'danger' | 'warning' | 'cta'
 */
import { reactive } from 'vue';

// Module-level singleton — shared across all composable calls
const _state = reactive({
  open: false,
  title: '',
  message: '',
  confirmLabel: 'Onayla',
  variant: 'danger',
  _resolve: null,
});

export function useConfirm() {
  function confirm({
    title = 'Onay',
    message = 'Bu işlemi gerçekleştirmek istediğinizden emin misiniz?',
    confirmLabel = 'Onayla',
    variant = 'danger',
  } = {}) {
    return new Promise((resolve) => {
      Object.assign(_state, { open: true, title, message, confirmLabel, variant, _resolve: resolve });
    });
  }

  function _doConfirm() {
    _state.open = false;
    _state._resolve?.(true);
    _state._resolve = null;
  }

  function _doCancel() {
    _state.open = false;
    _state._resolve?.(false);
    _state._resolve = null;
  }

  return { confirmState: _state, confirm, _doConfirm, _doCancel };
}
