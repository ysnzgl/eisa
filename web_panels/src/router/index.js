/**
 * Vue Router — Rol bazlı (RBAC) yönlendirme.
 * SuperAdmin -> /admin/*, Eczacı -> /pharmacist/*
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
      { path: 'medical-logic',      component: () => import('../views/admin/MedicalLogic.vue') },
      { path: 'ad-manager',    component: () => import('../views/admin/CampaignManager.vue') },
      { path: 'scheduler',     component: () => import('../views/admin/CampaignScheduler.vue') },
      { path: 'timeline',      component: () => import('../views/admin/AdTimelineView.vue') },
      { path: 'pricing',       component: () => import('../views/admin/PricingMatrixConfigurator.vue') },
      { path: 'users',         component: () => import('../views/admin/UserManagement.vue') },
    ]
  },
  {
    path: '/pharmacist',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { roles: ['pharmacist'] },
    children: [
      { path: '', component: () => import('../views/pharmacist/Dashboard.vue') },
      { path: 'inbox', component: () => import('../views/pharmacist/Inbox.vue') },
      { path: 'qr', component: () => import('../views/pharmacist/QrScan.vue') }
    ]
  }
];

const router = createRouter({ history: createWebHistory(), routes });

// RBAC guard
router.beforeEach((to) => {
  const auth = useAuthStore();
  const required = to.meta?.roles;
  if (!required) return true;
  if (!auth.isAuthenticated) return { path: '/login' };
  if (!required.includes(auth.role)) return { path: '/login' };
  return true;
});

export default router;
