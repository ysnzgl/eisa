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
  <div class="pharm-shell">
    <aside class="pharm-sidebar">
      <!-- Brand -->
      <div class="admin-brand">
        <span class="admin-brand-name">e-<span>İSA</span></span>
        <span class="admin-brand-sub">Eczacı Paneli</span>
      </div>

      <!-- Navigation -->
      <nav class="admin-nav">
        <RouterLink to="/pharmacist" class="admin-nav-link" :class="{ 'is-active': $route.path === '/pharmacist' }">
          <i class="fa-solid fa-house admin-nav-icon"></i>
          <span class="admin-nav-name">Ana Sayfa</span>
        </RouterLink>
        <RouterLink to="/pharmacist/inbox" class="admin-nav-link" active-class="is-active">
          <i class="fa-solid fa-bell admin-nav-icon"></i>
          <span class="admin-nav-name">Gelen Kutusu</span>
        </RouterLink>
        <RouterLink to="/pharmacist/qr" class="admin-nav-link" active-class="is-active">
          <i class="fa-solid fa-qrcode admin-nav-icon"></i>
          <span class="admin-nav-name">QR Okutma</span>
        </RouterLink>
      </nav>

      <!-- Footer -->
      <div class="admin-footer">
        <div class="pharm-avatar">
          <span>{{ auth.user?.first_name?.[0] ?? auth.user?.username?.[0] ?? 'E' }}</span>
        </div>
        <div class="admin-user">
          <span class="admin-user-name">{{ auth.user?.first_name ?? auth.user?.username }}</span>
          <span class="admin-user-role">Eczacı</span>
        </div>
        <button class="admin-logout" @click="logout" title="Çıkış Yap">
          <i class="fa-solid fa-arrow-right-from-bracket"></i>
        </button>
      </div>
    </aside>

    <main class="pharm-main">
      <RouterView />
    </main>
  </div>
</template>
