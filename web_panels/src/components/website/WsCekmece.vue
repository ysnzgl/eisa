<script setup>
/**
 * WsCekmece — sağdan açılan çekmece (drawer). Web Sitesi modülü genelinde
 * SEO ayarları, revizyonlar, başvuru detayı gibi yan paneller için kullanılır.
 *
 * Props: open, title, subtitle, width (CSS genişliği)
 * Slots: default (gövde), footer, header-extra
 */
import { onBeforeUnmount, onMounted } from 'vue';

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '480px' },
});
const emit = defineEmits(['close']);

function onKey(e) {
  if (e.key === 'Escape' && props.open) emit('close');
}
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
  <Teleport to="body">
    <Transition name="ws-cekmece">
      <div v-if="open" class="ws-cekmece-backdrop" @click.self="emit('close')">
        <aside class="ws-cekmece" :style="{ width }" role="dialog" aria-modal="true" :aria-label="title">
          <header class="ws-cekmece-header">
            <div class="ws-cekmece-baslik">
              <h3 class="eisa-modal-title">{{ title }}</h3>
              <p v-if="subtitle" class="ws-cekmece-alt">{{ subtitle }}</p>
            </div>
            <slot name="header-extra" />
            <button type="button" class="eisa-modal-close" aria-label="Kapat" @click="emit('close')">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </header>
          <div class="ws-cekmece-govde">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="ws-cekmece-footer">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
