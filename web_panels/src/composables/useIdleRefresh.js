/**
 * 5 dakika boyunca ekranda hiç hareket yoksa refreshFn'i çağırır.
 * Fare, klavye, dokunma ve scroll hareketlerini hareket olarak sayar.
 */
import { onMounted, onUnmounted } from 'vue';

const IDLE_EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];

export function useIdleRefresh(refreshFn, idleMs = 5 * 60 * 1000) {
  let timer = null;

  function reset() {
    clearTimeout(timer);
    timer = setTimeout(refreshFn, idleMs);
  }

  onMounted(() => {
    IDLE_EVENTS.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset();
  });

  onUnmounted(() => {
    clearTimeout(timer);
    IDLE_EVENTS.forEach((e) => window.removeEventListener(e, reset));
  });
}
