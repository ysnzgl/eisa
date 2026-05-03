<script setup>
import { RouterView, RouterLink } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

async function logout() {
  await auth.logout();
  router.push('/login');
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Kenar çubuğu -->
    <aside class="w-56 bg-teal-800 text-white flex flex-col">
      <div class="px-6 py-5 border-b border-teal-700">
        <span class="text-xl font-bold tracking-tight">e-<span class="text-green-400">İSA</span></span>
        <p class="text-xs text-teal-300 mt-0.5">Eczacı Paneli</p>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-1">
        <RouterLink
          to="/pharmacist"
          :class="$route.path === '/pharmacist' ? 'bg-teal-600' : ''"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-teal-700 transition"
        >
          📊 Ana Sayfa
        </RouterLink>
        <RouterLink
          to="/pharmacist/inbox"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-teal-700 transition"
          active-class="bg-teal-600"
        >
          🔔 Gelen Kutusu
        </RouterLink>
        <RouterLink
          to="/pharmacist/qr"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-teal-700 transition"
          active-class="bg-teal-600"
        >
          🔍 QR Okutma
        </RouterLink>
      </nav>
      <div class="px-4 py-4 border-t border-teal-700">
        <button @click="logout" class="w-full text-left text-xs text-teal-300 hover:text-white transition">
          Çıkış Yap
        </button>
      </div>
    </aside>

    <!-- İçerik alanı -->
    <main class="flex-1 overflow-auto">
      <RouterView />
    </main>
  </div>
</template>
