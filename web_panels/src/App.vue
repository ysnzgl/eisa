<script setup>
import { RouterView } from 'vue-router';
import { Toaster } from 'vue-sonner';
</script>

<template>
  <RouterView />
  <Toaster rich-colors position="bottom-right" :duration="4000" />
</template>
