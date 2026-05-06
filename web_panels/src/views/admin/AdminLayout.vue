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

const navItems = [
  { to: '/admin',                exact: true, icon: 'fa-chart-line',     label: 'Dashboard' },
  { to: '/admin/devices',        icon: 'fa-display',         label: 'Cihaz Yönetimi' },
  { to: '/admin/medical-logic',  icon: 'fa-dna',             label: 'Algoritma Editörü' },
  { to: '/admin/ad-manager',     icon: 'fa-bullhorn',        label: 'Reklam Yöneticisi' },
  { to: '/admin/scheduler',      icon: 'fa-calendar-week',   label: 'Yayın Takvimi' },
  { to: '/admin/users',          icon: 'fa-user-gear',       label: 'Kullanıcı Yönetimi' },
];
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-logo">e-<span class="brand-accent">İSA</span></span>
        <p class="brand-sub">Yönetici Paneli</p>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'is-active': $route.path === item.to || (!item.exact && $route.path.startsWith(item.to) && item.to !== '/admin') }"
        >
          <i class="fa-solid" :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="footer">
        <div class="user">          
          <div class="user-meta">
            <span class="user-name">{{ auth.user?.first_name || auth.user?.username }}</span>
            <span class="user-role">Süper Admin</span>
          </div>
        </div>
        <button class="logout" @click="logout">
          <i class="fa-solid fa-right-from-bracket"></i>
          <span>Çıkış</span>
        </button>
      </div>
    </aside>

    <main class="admin-main">
      <RouterView />
    </main>
  </div>
</template>
