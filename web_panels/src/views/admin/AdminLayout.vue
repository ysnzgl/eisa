<script setup>
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { RouterView, RouterLink, useRoute } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useRouter } from 'vue-router';
import logoUrl from '../../assets/eisa_logo.svg';
import PharmacistCampaignDisplay from '../../components/pharmacist/PharmacistCampaignDisplay.vue';
import { http } from '../../services/api';
import { listProvisioningRequests } from '../../services/devices';
import { getBasvuruOzet } from '../../services/website';
import DutyAlertModal from '../../components/pharmacist/DutyAlertModal.vue';
import EisaConfirm from '../../components/shared/EisaConfirm.vue';
import SiteArama from '../../components/website/SiteArama.vue';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

// Mobil (≤1024px) off-canvas menü durumu.
const navOpen = ref(false);
function closeNav() { navOpen.value = false; }
watch(() => route.fullPath, closeNav);
watch(navOpen, (open) => { document.body.classList.toggle('eisa-nav-locked', open); });
function onKeydown(e) { if (e.key === 'Escape' && navOpen.value) closeNav(); }
onMounted(() => window.addEventListener('keydown', onKeydown));
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
  document.body.classList.remove('eisa-nav-locked');
});

async function logout() {
  await auth.logout();
  router.push('/login');
}

const isAdmin      = computed(() => auth.role === 'superadmin');
const isPharmacist = computed(() => auth.role === 'pharmacist');
const isEditor     = computed(() => auth.role === 'editor');
// Web Sitesi modülünü görebilen roller (superadmin + editor).
const isWebsiteYetkili = computed(() => isAdmin.value || isEditor.value);

// "Sitede ara" (Ctrl/⌘+K) — yalnızca Web Sitesi yetkilileri.
const siteArama = ref(null);
const aramaKisayolu = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? '⌘K' : 'Ctrl K';

const navBadges = reactive({ destekYeni: 0, bekleyenCihazlar: 0, bekleyenTalepler: 0, onayBekleyen: 0, basvuruYeni: 0 });
// Eczacı abonelik durumu (demo / panel kısıtı) — nav görünürlüğünü belirler.
const billing = reactive({ demo: false, panelKisitli: false, loaded: false });

async function fetchNavBadges() {
  if (!isAdmin.value) return;
  try {
    const [destekResult, pendingRequests, talepResult, onayResult] = await Promise.all([
      http.get('/api/destek/talepler/yeni-sayisi/', { __silent: true }),
      listProvisioningRequests({ status: 'PENDING' }),
      http.get('/api/abonelik/talepler/bekleyen-sayisi/', { __silent: true }),
      http.get('/api/abonelik/talepler/onay-bekleyen/', { __silent: true }),
    ]);
    navBadges.destekYeni = destekResult.data.sayi ?? 0;
    navBadges.bekleyenCihazlar = pendingRequests.length;
    navBadges.bekleyenTalepler = talepResult.data.sayi ?? 0;
    navBadges.onayBekleyen = onayResult.data.sayi ?? 0;
  } catch { /* badge hatası kullanıcıyı engellemesin */ }
}

async function fetchBilling() {
  if (!isPharmacist.value) return;
  try {
    const { data } = await http.get('/api/abonelik/hesabim/', { __silent: true });
    billing.demo = !!data.demo;
    billing.panelKisitli = !!data.panel_kisitli;
    auth.setBilling({ demo: billing.demo, panelKisitli: billing.panelKisitli });
    // Kısıtlıysa ve Hesabım dışında bir yerdeyse Hesabım'a yönlendir.
    if (billing.panelKisitli && router.currentRoute.value.path !== '/pharmacist/hesabim') {
      router.replace('/pharmacist/hesabim');
    }
  } catch { /* sessiz */ } finally { billing.loaded = true; }
}

async function fetchPharmacistBadges() {
  if (!isPharmacist.value) return;
  try {
    const { data } = await http.get('/api/abonelik/hesabim/', { __silent: true });
    navBadges.onayBekleyen = data?.onay_gerekli ? 1 : 0;
  } catch { /* sessiz */ }
}

onMounted(() => { fetchNavBadges(); fetchBilling(); fetchPharmacistBadges(); fetchWebsiteBadge(); });

// Web sitesi başvuru rozeti: açılışta, rota değişiminde ve periyodik (60 sn) yenilenir.
async function fetchWebsiteBadge() {
  if (!isWebsiteYetkili.value) return;
  try {
    const { yeni } = await getBasvuruOzet();
    navBadges.basvuruYeni = yeni ?? 0;
  } catch { /* badge hatası kullanıcıyı engellemesin */ }
}
let websiteBadgeTimer = null;
onMounted(() => {
  if (isWebsiteYetkili.value) websiteBadgeTimer = setInterval(fetchWebsiteBadge, 60_000);
});
onBeforeUnmount(() => clearInterval(websiteBadgeTimer));
watch(() => route.path, (yeni, eski) => {
  if (yeni !== eski && yeni.startsWith('/admin/web-sitesi')) fetchWebsiteBadge();
});

function handleNavBadgeRefresh() {
  fetchNavBadges();
  fetchWebsiteBadge();
}

onMounted(() => {
  window.addEventListener('eisa-nav-badges-refresh', handleNavBadgeRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener('eisa-nav-badges-refresh', handleNavBadgeRefresh);
});

// Superadmin menüsü: mantıksal, katlanabilir gruplar. Başlıksız grup her zaman açıktır.
const adminNavGroups = [
  { key: 'genel', title: '', items: [
    { to: '/admin', exact: true, icon: 'fa-chart-line', label: 'Dashboard' },
  ] },
  { key: 'eczane', title: 'Eczane & Kiosk', icon: 'fa-store', items: [
    { to: '/admin/devices',          icon: 'fa-display',     label: 'Eczane & Cihaz', badgeKey: 'bekleyenCihazlar' },
    { to: '/admin/kiosk-activities', icon: 'fa-wave-square', label: 'Kiosk Hareketleri' },
  ] },
  { key: 'kiosk-icerik', title: 'Kiosk İçeriği', icon: 'fa-dna', items: [
    { to: '/admin/medical-logic',      icon: 'fa-dna',      label: 'Algoritma Editörü' },
    { to: '/admin/danisma',            icon: 'fa-comments', label: 'Danışma Kategorileri' },
    { to: '/admin/content-management', icon: 'fa-images',   label: 'İçerik Yönetimi' },
  ] },
  { key: 'sponsorluk', title: 'Sponsorluk & Yayın', icon: 'fa-bullhorn', items: [
    { to: '/admin/dooh/control-center', icon: 'fa-gauge-high', label: 'Kontrol Merkezi' },
    { to: '/admin/kiosk-sponsorships',  icon: 'fa-display',    label: 'Kiosk Sponsorluk' },
    { to: '/admin/campaigns',           icon: 'fa-bullhorn',   label: 'Sponsorluk Tanımları' },
    { to: '/admin/pharmacy-campaigns',  icon: 'fa-prescription-bottle-medical', label: 'Eczacı Ekran Sponsorluk' },
    { to: '/admin/barkod-logolar',      icon: 'fa-barcode',    label: 'Barkod Logo Sponsorluk' },
  ] },
  { key: 'web-sitesi', title: 'Web Sitesi', icon: 'fa-globe', web: true },
  { key: 'iletisim', title: 'Destek & İletişim', icon: 'fa-headset', items: [
    { to: '/admin/destek',        icon: 'fa-headset',    label: 'Görüş ve Destek', badgeKey: 'destekYeni' },
    { to: '/admin/is-takip',      icon: 'fa-list-check', label: 'İş Takibi' },
    { to: '/admin/announcements', icon: 'fa-bell',       label: 'Duyuru Yönetimi' },
  ] },
  { key: 'yonetim', title: 'Yönetim', icon: 'fa-gear', items: [
    { to: '/admin/abonelik',      icon: 'fa-file-invoice-dollar', label: 'Abonelik ve Ödeme', badgeKey: 'bekleyenTalepler' },
    { to: '/admin/sirket-tanimi', icon: 'fa-building',            label: 'Şirket Tanımı' },
    { to: '/admin/users',         icon: 'fa-user-gear',           label: 'Kullanıcı Yönetimi' },
  ] },
];

const pharmacistNavItems = [
   { to: '/pharmacist',          exact: true, icon: 'fa-house',      label: 'Ana Sayfa' },
   { to: '/pharmacist/kiosk-activities',      icon: 'fa-display',    label: 'Kiosk Hareketleri' },
   { to: '/pharmacist/qr',                    icon: 'fa-qrcode',     label: 'QR Okutma' },
   { to: '/pharmacist/hesabim',               icon: 'fa-file-invoice-dollar', label: 'Hesabım ve Ödemeler', badgeKey: 'onayBekleyen' },
   { to: '/pharmacist/destek',                icon: 'fa-headset',    label: 'Görüş ve Destek' },
   { to: '/pharmacist/announcements',         icon: 'fa-bullhorn', label: 'Duyurular' },
   { to: '/pharmacist/duty',                  icon: 'fa-calendar-days', label: 'Nöbet Takvimi' },

];

// Web Sitesi (eisa.com.tr CMS) grubu — superadmin'de gruplardan biri, editor'de tek (sabit açık) grup.
const websiteNavItems = [
  // Rota değil eylem: eisa.com.tr içeriğinde arama penceresini açar (Ctrl/⌘+K).
  { eylem: 'ara', icon: 'fa-magnifying-glass', label: 'Sitede ara' },
  { to: '/admin/web-sitesi',            exact: true, icon: 'fa-file-lines', label: 'Sayfalar', prefixes: ['/admin/web-sitesi/sayfalar'] },
  { to: '/admin/web-sitesi/menuler',                 icon: 'fa-bars-staggered', label: 'Menüler' },
  { to: '/admin/web-sitesi/blog',                    icon: 'fa-newspaper',   label: 'Blog' },
  { to: '/admin/web-sitesi/medya',                   icon: 'fa-photo-film',  label: 'Medya' },
  { to: '/admin/web-sitesi/basvurular',              icon: 'fa-inbox',       label: 'Başvurular', badgeKey: 'basvuruYeni' },
  { to: '/admin/web-sitesi/ayarlar',                 icon: 'fa-sliders',     label: 'Site Ayarları' },
  { to: '/admin/web-sitesi/yardim',                  icon: 'fa-circle-question', label: 'Yardım' },
];

const navGroups = computed(() => {
  if (isAdmin.value) {
    return adminNavGroups.map((g) => (g.web ? { ...g, items: websiteNavItems } : g));
  }
  if (isEditor.value) {
    return [{ key: 'web-sitesi', title: 'Web Sitesi', icon: 'fa-globe', sabit: true, items: websiteNavItems }];
  }
  // Panel kısıtlıysa (sözleşmesiz/ödeme gecikmiş) eczacı yalnız Hesabım'ı görür.
  const items = billing.panelKisitli
    ? pharmacistNavItems.filter((item) => item.to === '/pharmacist/hesabim')
    : pharmacistNavItems;
  return [{ key: 'ana', title: '', items }];
});
const allNavItems = computed(() => navGroups.value.flatMap((g) => g.items));

// Katlanabilir grupların açık/kapalı durumu tarayıcıda hatırlanır; aktif sayfanın grubu otomatik açılır.
const GRUP_ANAHTARI = 'eisa-nav-acik-gruplar';
function acikGruplariOku() {
  try { return new Set(JSON.parse(localStorage.getItem(GRUP_ANAHTARI) || '[]')); } catch { return new Set(); }
}
const acikGruplar = ref(acikGruplariOku());
function acikGruplariYaz() {
  try { localStorage.setItem(GRUP_ANAHTARI, JSON.stringify([...acikGruplar.value])); } catch { /* gizli mod vb. */ }
}
function grupAcikMi(group) {
  return !group.title || group.sabit || acikGruplar.value.has(group.key);
}
function grupDegistir(key) {
  const yeni = new Set(acikGruplar.value);
  if (yeni.has(key)) yeni.delete(key); else yeni.add(key);
  acikGruplar.value = yeni;
  acikGruplariYaz();
}
function grupRozeti(group) {
  return group.items.reduce((t, i) => t + (i.badgeKey ? navBadges[i.badgeKey] || 0 : 0), 0);
}
watch(() => route.path, (path) => {
  const grup = navGroups.value.find((g) => g.title && g.items.some((i) => isNavActive(i, path)));
  if (grup && !acikGruplar.value.has(grup.key)) {
    acikGruplar.value = new Set([...acikGruplar.value, grup.key]);
    acikGruplariYaz();
  }
}, { immediate: true });

function isNavActive(item, path) {
  if (!item.to) return false;
  if (item.prefixes?.some((p) => path === p || path.startsWith(p + '/'))) return true;
  return item.exact ? path === item.to : path === item.to || path.startsWith(item.to + '/');
}
const brandSub   = computed(() => {
  if (isAdmin.value) return 'Yönetici Paneli';
  if (isEditor.value) return 'Web Sitesi Paneli';
  return 'Eczacı Paneli';
});
const roleLabel  = computed(() => {
  if (isAdmin.value) return 'Süper Admin';
  if (isEditor.value) return 'Editör';
  return 'Eczacı';
});
</script>

<template>
  <div class="admin-shell" :class="{ 'is-nav-open': navOpen }" :data-role="auth.role">
    <header class="admin-topbar">
      <button type="button" class="admin-topbar-toggle" :aria-expanded="navOpen" aria-controls="admin-sidebar"
        :aria-label="navOpen ? 'Menüyü kapat' : 'Menüyü aç'" @click="navOpen = !navOpen">
        <i class="fa-solid" :class="navOpen ? 'fa-xmark' : 'fa-bars'"></i>
        <span v-if="!navOpen && allNavItems.some((i) => i.badgeKey && navBadges[i.badgeKey] > 0)"
          class="admin-topbar-dot" aria-hidden="true"></span>
      </button>
      <img :src="logoUrl" alt="E-ISA logo" class="admin-topbar-logo" />
      <span class="admin-topbar-sub">{{ brandSub }}</span>
    </header>
    <div class="admin-nav-backdrop" aria-hidden="true" @click="closeNav"></div>

    <aside id="admin-sidebar" class="admin-sidebar">
      <div class="brand">
        <img :src="logoUrl" alt="E-ISA logo" />        
        <p class="brand-sub">{{ brandSub }}</p>
        <span v-if="isPharmacist && billing.demo" class="eisa-pill eisa-pill-warning" style="margin-top:.4rem;">
          <i class="fa-solid fa-flask"></i> DEMO
        </span>
      </div>

      <nav class="nav">
        <div v-for="group in navGroups" :key="group.key" class="nav-grup" :class="{ 'is-open': grupAcikMi(group) }">
          <template v-if="group.title">
            <p v-if="group.sabit" class="nav-group-title">{{ group.title }}</p>
            <button v-else type="button" class="nav-grup-baslik" :aria-expanded="grupAcikMi(group)"
              :aria-controls="`nav-grup-${group.key}`" @click="grupDegistir(group.key)">
              <i class="fa-solid" :class="group.icon"></i>
              <span>{{ group.title }}</span>
              <span v-if="!grupAcikMi(group) && grupRozeti(group) > 0" class="nav-badge">{{ grupRozeti(group) }}</span>
              <i class="fa-solid fa-chevron-down nav-grup-ok"></i>
            </button>
          </template>
          <div v-show="grupAcikMi(group)" :id="`nav-grup-${group.key}`"
            class="nav-grup-ogeler" :class="{ 'is-girintili': group.title && !group.sabit }">
            <template v-for="item in group.items" :key="item.to || item.eylem">
              <button v-if="item.eylem === 'ara'" type="button" class="nav-link nav-link--eylem"
                title="eisa.com.tr içeriğinde ara" @click="siteArama?.ac()">
                <i class="fa-solid" :class="item.icon"></i>
                <span>{{ item.label }}</span>
                <kbd class="nav-kisayol">{{ aramaKisayolu }}</kbd>
              </button>
              <RouterLink
                v-else
                :to="item.to"
                class="nav-link"
                :class="{ 'is-active': isNavActive(item, $route.path) }"
              >
                <i class="fa-solid" :class="item.icon"></i>
                <span>{{ item.label }}</span>
                <span v-if="item.badgeKey && navBadges[item.badgeKey] > 0" class="nav-badge">
                  {{ navBadges[item.badgeKey] }}
                </span>
              </RouterLink>
            </template>
          </div>
        </div>
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
    <DutyAlertModal v-if="isPharmacist" />
    <EisaConfirm />
    <SiteArama v-if="isWebsiteYetkili" ref="siteArama" />
  </div>
</template>
