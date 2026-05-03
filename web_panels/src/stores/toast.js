import { defineStore } from 'pinia';

/**
 * Hafif global toast/notification store (ERR-001).
 *
 * UI tarafında bir <Toaster /> bileşeni `useToastStore().items`'ı izleyerek
 * göstermelidir. Burada framework eklemiyoruz; sadece veri ve API'yi sağlıyoruz.
 */
let _seq = 1;

export const useToastStore = defineStore('toast', {
  state: () => ({ items: [] }),
  actions: {
    push(level, message, opts = {}) {
      if (!message) return;
      const item = {
        id: _seq++,
        level, // 'error' | 'warn' | 'info' | 'success'
        message: String(message),
        ts: Date.now(),
      };
      this.items.push(item);
      const ttl = Number.isFinite(opts.ttl) ? opts.ttl : 5000;
      if (ttl > 0) {
        setTimeout(() => this.dismiss(item.id), ttl);
      }
      return item.id;
    },
    error(msg, opts) { return this.push('error', msg, opts); },
    warn(msg, opts) { return this.push('warn', msg, opts); },
    info(msg, opts) { return this.push('info', msg, opts); },
    success(msg, opts) { return this.push('success', msg, opts); },
    dismiss(id) {
      this.items = this.items.filter((i) => i.id !== id);
    },
    clear() { this.items = []; },
  },
});
