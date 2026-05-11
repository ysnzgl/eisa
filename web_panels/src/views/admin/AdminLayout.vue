<script setup>
import { computed } from 'vue';
import { RouterView, RouterLink } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

async function logout() {
  await auth.logout();
  router.push('/login');
}

const isAdmin = computed(() => auth.role === 'superadmin');

const adminNavItems = [
  { to: '/admin',               exact: true, icon: 'fa-chart-line',   label: 'Dashboard' },
  { to: '/admin/devices',                    icon: 'fa-display',       label: 'Cihaz Yönetimi' },
  { to: '/admin/medical-logic',              icon: 'fa-dna',           label: 'Algoritma Editörü' },
  { to: '/admin/campaigns',                  icon: 'fa-bullhorn',      label: 'Kampanyalar' },
  { to: '/admin/timeline',                   icon: 'fa-stream',        label: 'Loop Timeline' },
  { to: '/admin/playlists',                  icon: 'fa-list-ol',       label: 'Playlist Editörü' },
  { to: '/admin/pricing',                    icon: 'fa-coins',         label: 'Fiyat Matrisi' },
  { to: '/admin/users',                      icon: 'fa-user-gear',     label: 'Kullanıcı Yönetimi' },
];

const pharmacistNavItems = [
  { to: '/pharmacist',          exact: true, icon: 'fa-house',   label: 'Ana Sayfa' },
  { to: '/pharmacist/inbox',                 icon: 'fa-bell',    label: 'Gelen Kutusu' },
  { to: '/pharmacist/qr',                    icon: 'fa-qrcode',  label: 'QR Okutma' },
];

const navItems   = computed(() => isAdmin.value ? adminNavItems : pharmacistNavItems);
const brandSub   = computed(() => isAdmin.value ? 'Yönetici Paneli' : 'Eczacı Paneli');
const roleLabel  = computed(() => isAdmin.value ? 'Süper Admin' : 'Eczacı');
</script>

<template>
  <div class="admin-shell" :data-role="auth.role">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-logo">e-<span class="brand-accent">İSA</span></span>
        <p class="brand-sub">{{ brandSub }}</p>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'is-active': item.exact
            ? $route.path === item.to
            : $route.path === item.to || $route.path.startsWith(item.to + '/') }"
        >
          <i class="fa-solid" :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="footer">
        <div class="user">
          <div class="user-meta">
            <span class="user-name">{{ auth.user?.first_name || auth.user?.username }}</span>
            <span class="user-role">{{ roleLabel }}</span>
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
