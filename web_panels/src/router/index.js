/**
 * Vue Router — Rol bazlı (RBAC) yönlendirme.
 * SuperAdmin -> /admin/*, Eczacı -> /pharmacist/*,
 * Editör (Web Sitesi) -> yalnız /admin/web-sitesi/* (SuperAdmin de erişir)
 */
import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/Login.vue') },

  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { roles: ['superadmin'] },
    children: [
      { path: '', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'devices',        component: () => import('../views/admin/DeviceManagement.vue') },
      { path: 'devices/pending', component: () => import('../views/admin/PendingDevices.vue') },
      { path: 'kiosk-activities', component: () => import('../views/admin/KioskActivities.vue') },
      { path: 'medical-logic',      component: () => import('../views/admin/MedicalLogic.vue') },
      { path: 'danisma',           component: () => import('../views/admin/DanismaYonetimi.vue') },
      { path: 'content-management', component: () => import('../views/admin/ContentManagement.vue') },
      { path: 'kiosk-sponsorships', component: () => import('../views/admin/KioskSponsorship.vue') },
      { path: 'campaigns',     component: () => import('../views/admin/SponsorshipDefinitions.vue') },
      { path: 'pharmacy-campaigns', component: () => import('../views/admin/PharmacyCampaigns.vue') },
      { path: 'barkod-logolar', component: () => import('../views/admin/BarkodLogoYonetimi.vue') },
      { path: 'destek', component: () => import('../views/admin/DestekYonetimi.vue') },
      { path: 'is-takip', component: () => import('../views/admin/GorevYonetimi.vue') },
      { path: 'dooh/control-center', component: () => import('../views/admin/DoohControlCenter.vue') },
      { path: 'abonelik',      component: () => import('../views/admin/AbonelikYonetimi.vue') },
      { path: 'sirket-tanimi', component: () => import('../views/admin/SirketTanimi.vue') },
      { path: 'users',         component: () => import('../views/admin/UserManagement.vue') },
      { path: 'announcements', component: () => import('../views/admin/AnnouncementManagement.vue') },
    ]
  },
  // Web Sitesi (eisa.com.tr CMS) — '/admin' parent'ından AYRI üst seviye rota:
  // '/admin' superadmin'e kilitli olduğundan editor yalnız bu ağaca girebilir.
  {
    path: '/admin/web-sitesi',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { roles: ['superadmin', 'editor'] },
    children: [
      { path: '',            component: () => import('../views/admin/web-sitesi/WebSitesiSayfalar.vue') },
      { path: 'sayfalar/:id', component: () => import('../views/admin/web-sitesi/SayfaEditoru.vue') },
      { path: 'menuler',     component: () => import('../views/admin/web-sitesi/WebSitesiMenuler.vue') },
      { path: 'blog',        component: () => import('../views/admin/web-sitesi/BlogYazilar.vue') },
      { path: 'blog/:id',    component: () => import('../views/admin/web-sitesi/BlogYaziEditoru.vue') },
      { path: 'medya',       component: () => import('../views/admin/web-sitesi/MedyaKutuphanesi.vue') },
      { path: 'basvurular',  component: () => import('../views/admin/web-sitesi/Basvurular.vue') },
      { path: 'ayarlar',     component: () => import('../views/admin/web-sitesi/SiteAyarlari.vue') },
      { path: 'yardim',      component: () => import('../views/admin/web-sitesi/Yardim.vue') },
    ]
  },
  {
    path: '/pharmacist',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { roles: ['pharmacist'] },
    children: [
      { path: '', component: () => import('../views/pharmacist/Dashboard.vue') },
      { path: 'kiosk-activities', component: () => import('../views/pharmacist/KioskActivities.vue') },
      { path: 'announcements', component: () => import('../views/pharmacist/Announcements.vue') },
      { path: 'duty', component: () => import('../views/pharmacist/DutyCalendar.vue') },
      { path: 'qr', component: () => import('../views/pharmacist/QrScan.vue') },
      { path: 'hesabim', component: () => import('../views/pharmacist/HesabimOdemeler.vue') },
      { path: 'destek', component: () => import('../views/pharmacist/DestekTalepleri.vue') }
    ]
  }
];

const router = createRouter({ history: createWebHistory(), routes });

/**
 * RBAC kararı (test edilebilir saf fonksiyon).
 * Dönüş: true (geç) | { path } (yönlendir).
 */
export function yetkiKontrolu(to, auth) {
  const required = to.meta?.roles;
  if (!required) return true;
  if (!auth.isAuthenticated) return { path: '/login' };
  if (!required.includes(auth.role)) {
    // Editör yalnız Web Sitesi modülünü kullanır; başka panele girmeye çalışırsa oraya döner.
    if (auth.role === 'editor') return { path: '/admin/web-sitesi' };
    return { path: '/login' };
  }
  // Panel kısıtlı eczacı yalnız Hesabım ve Ödemeler'e erişebilir.
  if (auth.role === 'pharmacist' && auth.panelKisitli && to.path !== '/pharmacist/hesabim') {
    return { path: '/pharmacist/hesabim' };
  }
  return true;
}

// RBAC guard
router.beforeEach((to) => yetkiKontrolu(to, useAuthStore()));

export default router;
