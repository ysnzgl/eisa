<script setup>
defineProps({ title: String, description: String, eyebrow: { type: String, default: 'YÖNETİM / TANIMLAR' },
  count: Number, loading: Boolean, error: String, search: String, newLabel: String });
defineEmits(['create', 'refresh', 'update:search']);
</script>

<template>
  <div class="eisa-page eisa-definition-page">
    <header class="eisa-page-header">
      <div><p class="eisa-eyebrow">{{ eyebrow }}</p><h1 class="eisa-page-title">{{ title }}</h1><p class="eisa-page-subtitle">{{ description }}</p></div>
      <div class="eisa-header-actions"><button class="eisa-btn eisa-btn-ghost" :disabled="loading" title="Yenile" aria-label="Yenile" @click="$emit('refresh')"><i class="fa-solid fa-arrows-rotate" :class="{ 'fa-spin': loading }"></i></button><button v-if="newLabel" class="eisa-btn eisa-btn-cta" @click="$emit('create')"><i class="fa-solid fa-plus"></i>{{ newLabel }}</button></div>
    </header>
    <slot name="intro" />
    <section class="eisa-panel">
      <div class="eisa-toolbar">
        <div class="eisa-search-wrap"><i class="fa-solid fa-magnifying-glass"></i><input class="eisa-field eisa-search-field" :value="search" aria-label="Kayıtlarda ara" placeholder="Kayıtlarda ara…" @input="$emit('update:search', $event.target.value)" /></div>
        <slot name="filters" />
        <span class="eisa-record-count">{{ count ?? 0 }} kayıt</span>
      </div>
      <div v-if="error" class="eisa-definition-empty" role="alert"><i class="fa-solid fa-circle-exclamation"></i><strong>{{ error }}</strong><button class="eisa-btn eisa-btn-ghost" @click="$emit('refresh')">Tekrar dene</button></div>
      <div v-else-if="loading" class="eisa-definition-empty" role="status"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Kayıtlar yükleniyor…</span></div>
      <slot v-else />
    </section>
    <slot name="extra" />
    <slot name="dialogs" />
  </div>
</template>
