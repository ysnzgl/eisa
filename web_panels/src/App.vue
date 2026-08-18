<script setup>
import { RouterView } from 'vue-router';
import { Toaster } from 'vue-sonner';
</script>

<template>
  <RouterView />
  <Toaster rich-colors position="top-center" :duration="4000" :offset="22" />
</template>
