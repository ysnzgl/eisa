<script setup>
import { computed, reactive, onMounted, onBeforeUnmount } from 'vue';
import { RouterView, RouterLink } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';
import logoUrl from '../../assets/eisa_logo.svg';
import PharmacistCampaignDisplay from '../../components/pharmacist/PharmacistCampaignDisplay.vue';
import { http } from '../../services/api';
import { listProvisioningRequests } from '../../services/devices';

const auth = useAuthStore();
const router = useRouter();

async function logout() {
  await auth.logout();
  router.push('/login');
}

const isAdmin      = computed(() => auth.role === 'superadmin');
const isPharmacist = computed(() => auth.role === 'pharmacist');

const navBadges = reactive({ destekYeni: 0, bekleyenCihazlar: 0 });

async function fetchNavBadges() {
  if (!isAdmin.value) return;
  try {
    const [destekResult, pendingRequests] = await Promise.all([
      http.get('/api/destek/talepler/yeni-sayisi/', { __silent: true }),
      listProvisioningRequests({ status: 'PENDING' }),
    ]);
    navBadges.destekYeni = destekResult.data.sayi ?? 0;
    navBadges.bekleyenCihazlar = pendingRequests.length;
  } catch { /* badge hatası kullanıcıyı engellemesin */ }
}

onMounted(fetchNavBadges);

function handleNavBadgeRefresh() {
  fetchNavBadges();
}

onMounted(() => {
  window.addEventListener('eisa-nav-badges-refresh', handleNavBadgeRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener('eisa-nav-badges-refresh', handleNavBadgeRefresh);
});

const adminNavItems = [
  { to: '/admin',               exact: true, icon: 'fa-chart-line',   label: 'Dashboard' },
  { to: '/admin/devices',                    icon: 'fa-display',       label: 'Cihaz Yönetimi', badgeKey: 'bekleyenCihazlar' },
  { to: '/admin/kiosk-activities',           icon: 'fa-wave-square',   label: 'Kiosk Hareketleri' },
  { to: '/admin/medical-logic',              icon: 'fa-dna',           label: 'Algoritma Editörü' },
  { to: '/admin/danisma',                    icon: 'fa-comments',      label: 'Danışma Kategorileri' },
  { to: '/admin/content-management',         icon: 'fa-images',        label: 'İçerik Yönetimi' },
  { to: '/admin/campaigns',                  icon: 'fa-display',       label: 'Kiosk Kampanyaları' },
  { to: '/admin/pharmacy-campaigns',         icon: 'fa-prescription-bottle-medical', label: 'Eczacı Paneli Kampanyaları' },
  { to: '/admin/barkod-logolar',             icon: 'fa-barcode',       label: 'Barkod Logo Yönetimi' },
  { to: '/admin/destek',                     icon: 'fa-headset',       label: 'Görüş ve Destek', badgeKey: 'destekYeni' },
  { to: '/admin/dooh/control-center',        icon: 'fa-gauge-high',    label: 'Kontrol Merkezi' },
  { to: '/admin/playlists',                  icon: 'fa-list-ol',       label: 'Gelişmiş Manuel Yayın' },
  { to: '/admin/pricing',                    icon: 'fa-coins',         label: 'Fiyat Matrisi' },
  { to: '/admin/users',                      icon: 'fa-user-gear',     label: 'Kullanıcı Yönetimi' },
];

const pharmacistNavItems = [
  { to: '/pharmacist',          exact: true, icon: 'fa-house',      label: 'Ana Sayfa' },
  { to: '/pharmacist/kiosk-activities',      icon: 'fa-display',    label: 'Kiosk Hareketleri' },
  { to: '/pharmacist/qr',                    icon: 'fa-qrcode',     label: 'QR Okutma' },
  { to: '/pharmacist/destek',                icon: 'fa-headset',    label: 'Görüş ve Destek' },
];

const navItems   = computed(() => isAdmin.value ? adminNavItems : pharmacistNavItems);
const brandSub   = computed(() => isAdmin.value ? 'Yönetici Paneli' : 'Eczacı Paneli');
const roleLabel  = computed(() => isAdmin.value ? 'Süper Admin' : 'Eczacı');
</script>

<template>
  <div class="admin-shell" :data-role="auth.role">
    <aside class="admin-sidebar">
      <div class="brand">
        <img :src="logoUrl" alt="E-ISA logo" />        
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
          <span v-if="item.badgeKey && navBadges[item.badgeKey] > 0" class="nav-badge">
            {{ navBadges[item.badgeKey] }}
          </span>
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

    <main class="admin-main" :class="{ 'admin-main--pharmacist': isPharmacist }">
      <RouterView />
      <!-- Eczacı paneli kampanya şeridi ve idle overlay -->
      <PharmacistCampaignDisplay v-if="isPharmacist" />
    </main>
  </div>
</template>
