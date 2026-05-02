<script setup>
import { RouterView, RouterLink } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

function logout() {
  auth.logout();
  router.push('/login');
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Kenar çubuğu -->
    <aside class="w-56 bg-blue-900 text-white flex flex-col">
      <div class="px-6 py-5 border-b border-blue-800">
        <span class="text-xl font-bold tracking-tight">e-<span class="text-green-400">İSA</span></span>
        <p class="text-xs text-blue-300 mt-0.5">Süper Admin Paneli</p>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-1">
        <RouterLink
          to="/admin"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
          active-class="bg-blue-700"
        >
          📊 Dashboard
        </RouterLink>
        <RouterLink
          to="/admin/campaigns"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
          active-class="bg-blue-700"
        >
          📺 Kampanyalar
        </RouterLink>
      </nav>
      <div class="px-4 py-4 border-t border-blue-800">
        <button @click="logout" class="w-full text-left text-xs text-blue-300 hover:text-white transition">
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
