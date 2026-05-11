/**
 * Minimal toast notification system — drop-in compatible with vue-sonner API.
 * Usage: import { toast } from './useToast'
 *        toast.success('İşlem başarılı')
 *        toast.error('Bir hata oluştu')
 *        toast.info('Bilgi mesajı')
 *        toast.warning('Uyarı')
 */
import { reactive } from 'vue';

let _id = 0;

export const _toasts = reactive([]);

function add(message, type = 'info', duration = 4000) {
  const id = ++_id;
  _toasts.push({ id, message, type });
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration);
  }
  return id;
}

function dismiss(id) {
  const i = _toasts.findIndex((t) => t.id === id);
  if (i !== -1) _toasts.splice(i, 1);
}

export const toast = {
  success: (msg, opts) => add(msg, 'success', opts?.duration ?? 4000),
  error:   (msg, opts) => add(msg, 'error',   opts?.duration ?? 6000),
  info:    (msg, opts) => add(msg, 'info',     opts?.duration ?? 4000),
  warning: (msg, opts) => add(msg, 'warning',  opts?.duration ?? 5000),
  dismiss,
};
