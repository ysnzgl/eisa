<script setup>
defineProps({ open: Boolean, title: String, busy: Boolean, error: String,
  saveLabel: { type: String, default: 'Kaydet' } });
defineEmits(['close', 'save']);
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="eisa-modal-backdrop" @click.self="!busy && $emit('close')" @keydown.esc="!busy && $emit('close')">
      <form class="eisa-modal eisa-modal--medium" role="dialog" aria-modal="true" :aria-label="title" @submit.prevent="$emit('save')">
        <div class="eisa-modal-header"><h2 class="eisa-modal-title">{{ title }}</h2><button type="button" class="eisa-modal-close" :disabled="busy" aria-label="Kapat" @click="$emit('close')"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="eisa-modal-body"><p v-if="error" class="eisa-error-banner" role="alert">{{ error }}</p><slot /></div>
        <div class="eisa-modal-footer"><button type="button" class="eisa-btn eisa-btn-ghost" :disabled="busy" @click="$emit('close')">Vazgeç</button><button class="eisa-btn eisa-btn-cta" :disabled="busy"><i class="fa-solid" :class="busy ? 'fa-circle-notch fa-spin' : 'fa-check'"></i>{{ busy ? 'Kaydediliyor…' : saveLabel }}</button></div>
      </form>
    </div>
  </Teleport>
</template>
