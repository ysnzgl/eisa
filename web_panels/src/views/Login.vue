<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const auth = useAuthStore();
const router = useRouter();

async function submit() {
  await auth.login(username.value, password.value);
  router.push(auth.role === 'superadmin' ? '/admin' : '/pharmacist');
}
</script>

<template>
  <form @submit.prevent="submit" class="max-w-sm mx-auto mt-24 space-y-3">
    <h1 class="text-2xl font-semibold">E-İSA Panel Giriş</h1>
    <input v-model="username" placeholder="Kullanıcı adı" class="border p-2 w-full" />
    <input v-model="password" type="password" placeholder="Şifre" class="border p-2 w-full" />
    <button class="bg-black text-white px-4 py-2 w-full">Giriş</button>
  </form>
</template>
