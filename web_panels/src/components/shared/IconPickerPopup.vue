<script setup>
/**
 * İkon Seçici Popup
 * Props:
 *   modelValue (String) — seçili ikon css sınıfı
 *   open       (Boolean) — popup açık mı
 * Emits:
 *   update:modelValue — yeni ikon seçildiğinde
 *   update:open       — popup kapanınca false gönderir
 */
import { HEALTH_ICONS } from '../../data/healthIcons.js';

defineProps({
  modelValue: { type: String, default: '' },
  open:       { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue', 'update:open']);

function select(cls) {
  emit('update:modelValue', cls);
  emit('update:open', false);
}

function close() {
  emit('update:open', false);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4"
        style="background: rgba(15,23,42,0.45); backdrop-filter: blur(6px);"
        @click.self="close"
      >
        <div
          class="w-full max-w-2xl bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          style="max-height: 80vh;"
        >
          <!-- Başlık -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <div>
              <h3 class="text-base font-bold text-gray-900">İkon Seç</h3>
              <p class="text-xs text-gray-500 mt-0.5">Kategori için bir sağlık ikonu seçin</p>
            </div>
            <button
              type="button"
              @click="close"
              class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- İkon Grid -->
          <div class="flex-1 overflow-y-auto p-4">
            <div class="grid grid-cols-6 sm:grid-cols-8 gap-2">
              <button
                v-for="ic in HEALTH_ICONS"
                :key="ic.cls"
                type="button"
                :title="ic.label"
                @click="select(ic.cls)"
                class="aspect-square flex flex-col items-center justify-center gap-1 rounded-xl border transition group"
                :class="modelValue === ic.cls
                  ? 'bg-eisa-100 border-eisa-600 text-eisa-700 ring-2 ring-eisa-300'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-eisa-300 hover:text-eisa-600 hover:bg-eisa-50'"
              >
                <i :class="ic.cls" class="text-lg"></i>
                <span class="text-[10px] leading-tight text-center px-1 truncate w-full opacity-70 group-hover:opacity-100">{{ ic.label }}</span>
              </button>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-5 py-3 border-t border-gray-200 flex justify-between items-center bg-gray-50">
            <div class="text-xs text-gray-500">
              Mevcut: <code class="text-eisa-600 ml-1">{{ modelValue || '—' }}</code>
            </div>
            <button type="button" @click="close" class="eisa-btn">Kapat</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
