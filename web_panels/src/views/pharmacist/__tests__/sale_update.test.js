import { flushPromises, shallowMount } from '@vue/test-utils';
import { expect, it, vi } from 'vitest';

const { getKioskActivities } = vi.hoisted(() => ({ getKioskActivities: vi.fn() }));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { only_pending: 'false' } }),
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock('../../../services/api', () => ({ http: { get: vi.fn().mockResolvedValue({ data: {} }) } }));
vi.mock('../../../services/analytics', () => ({
  getKioskActivities, getCampaignImpressions: vi.fn(), getKioskEvents: vi.fn(),
  markSessionReviewed: vi.fn(), completeSession: vi.fn(),
}));
vi.mock('../../../stores/auth', () => ({ useAuthStore: () => ({ pharmacyId: 1, userId: 2 }) }));

import KioskActivities from '../KioskActivities.vue';
import SessionsPanel from '../../../components/kiosk/SessionsPanel.vue';
import SessionDetailModal from '../../../components/SessionDetailModal.vue';

it('satış sonucu güncellenince oturum listesini sunucudan yeniler', async () => {
  const notSold = { id: 41, qr_kodu: 'ABCDEFGH', status: 3, sold: false, danisma_tamamlandi: true };
  const sold = { ...notSold, status: 2, sold: true };
  getKioskActivities
    .mockResolvedValueOnce({ data: { results: [notSold], count: 1 } })
    .mockResolvedValueOnce({ data: { results: [sold], count: 1 } });
  sessionStorage.clear();
  const wrapper = shallowMount(KioskActivities);
  await flushPromises();
  expect(wrapper.getComponent(SessionsPanel).props('rows')[0].sold).toBe(false);
  wrapper.getComponent(SessionsPanel).vm.$emit('open-detail', notSold);
  await flushPromises();
  wrapper.getComponent(SessionDetailModal).vm.$emit('completed', sold);
  await flushPromises();
  expect(getKioskActivities).toHaveBeenCalledTimes(2);
  expect(wrapper.getComponent(SessionsPanel).props('rows')[0].sold).toBe(true);
  expect(wrapper.getComponent(SessionDetailModal).props('session')).toBeNull();
  wrapper.unmount();
});
