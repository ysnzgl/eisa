/**
 * KioskSponsorship.vue — bileşen testleri (servisler mock'lanır).
 *
 * Senaryolar:
 *   - kiosk listesi yüklenir
 *   - kiosk seçince sponsorluklar yüklenir
 *   - satır ekleyip kaydedince PUT doğru gövdeyle çağrılır
 *   - capacity_exceeded hatası gösterilir ve state kirli kalır
 *   - kopyalama akışı önce dry_run, onaydan sonra gerçek copy çağırır
 *   - simülasyon probe sonucu render edilir
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

// vue-sonner toast'ı sessizce mock'la
vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }));

// confirm her zaman onaylanmış say (kopyalama akışı için)
vi.mock('../../composables/useConfirm.js', () => ({
  useConfirm: () => ({ confirm: vi.fn(() => Promise.resolve(true)) }),
}));

const mockApi = vi.hoisted(() => ({
  listSponsorshipKiosks: vi.fn(),
  getKioskSponsorships: vi.fn(),
  putKioskSponsorships: vi.fn(),
  previewKioskSponsorships: vi.fn(),
  copyKioskSponsorships: vi.fn(),
  simulateKioskSponsorship: vi.fn(),
  getKioskDayStream: vi.fn(),
  listCampaignsV2: vi.fn(),
}));
vi.mock('../../services/dooh.js', () => mockApi);

import KioskSponsorship from '../../views/admin/KioskSponsorship.vue';

const KIOSKS = [
  { id: 1, ad: 'Kiosk A', eczane_adi: 'Merkez Ecz.', il_adi: 'İstanbul', ilce_adi: 'Kadıköy', is_online: true, sponsorship_count: 2 },
  { id: 2, ad: 'Kiosk B', eczane_adi: 'Sahil Ecz.', il_adi: 'İzmir', ilce_adi: 'Konak', is_online: false, sponsorship_count: 0 },
];
const CAMPAIGNS = [
  { id: 'c1', name: 'Bayer', advertiser_name: 'Bayer İlaç', creatives: [{ duration_seconds: 15 }] },
  { id: 'c2', name: 'Pfizer', advertiser_name: 'Pfizer', creatives: [{ duration_seconds: 30 }] },
];

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.listSponsorshipKiosks.mockResolvedValue({ data: KIOSKS });
  mockApi.listCampaignsV2.mockResolvedValue({ data: CAMPAIGNS });
  mockApi.getKioskSponsorships.mockResolvedValue({
    data: {
      kiosk: KIOSKS[0],
      items: [{
        campaign_id: 'c1', campaign_name: 'Bayer', advertiser_name: 'Bayer İlaç',
        creative_durations: [15], window_start: '08:00', window_end: '19:00',
        count: 50, active_weekdays: [], start_date: null, end_date: null, is_active: true,
      }],
    },
  });
  mockApi.previewKioskSponsorships.mockResolvedValue({ data: { hours: [], items: [], assignments: [] } });
  mockApi.putKioskSponsorships.mockResolvedValue({ data: { kiosk: KIOSKS[0], items: [] } });
  mockApi.copyKioskSponsorships.mockResolvedValue({ data: { dry_run: true, source_kiosk_id: 1, item_count: 1, targets: [] } });
  mockApi.simulateKioskSponsorship.mockResolvedValue({ data: {} });
});

async function mountAndSelect() {
  const wrapper = mount(KioskSponsorship);
  await flushPromises();
  await wrapper.vm.selectKiosk(KIOSKS[0]);
  await flushPromises();
  return wrapper;
}

describe('KioskSponsorship.vue', () => {
  it('kiosk listesini yükler', async () => {
    const wrapper = mount(KioskSponsorship);
    await flushPromises();
    expect(mockApi.listSponsorshipKiosks).toHaveBeenCalled();
    expect(wrapper.text()).toContain('Kiosk A');
    expect(wrapper.text()).toContain('Kiosk B');
  });

  it('kiosk seçince sponsorluklar yüklenir', async () => {
    const wrapper = await mountAndSelect();
    expect(mockApi.getKioskSponsorships).toHaveBeenCalledWith(1);
    expect(wrapper.vm.rows.length).toBe(1);
    expect(wrapper.text()).toContain('Bayer');
  });

  it('satır ekleyip kaydedince PUT doğru gövdeyle çağrılır', async () => {
    const wrapper = await mountAndSelect();
    // c2'yi ekle
    wrapper.vm.addCampaignId = 'c2';
    wrapper.vm.addRow();
    await flushPromises();
    expect(wrapper.vm.rows.length).toBe(2);
    expect(wrapper.vm.dirty).toBe(true);

    await wrapper.vm.save();
    await flushPromises();

    expect(mockApi.putKioskSponsorships).toHaveBeenCalledTimes(1);
    const [kioskId, items] = mockApi.putKioskSponsorships.mock.calls[0];
    expect(kioskId).toBe(1);
    expect(items).toHaveLength(2);
    // rowToPayload sözleşmesi: campaign_id + window + count + null weekday
    expect(items[1]).toMatchObject({
      campaign_id: 'c2', window_start: '08:00', window_end: '19:00',
      active_weekdays: null, is_active: true,
    });
    expect(typeof items[1].count).toBe('number');
  });

  it('capacity_exceeded hatası gösterilir ve state kirli kalır', async () => {
    const wrapper = await mountAndSelect();
    mockApi.putKioskSponsorships.mockRejectedValueOnce({
      response: { status: 400, data: {
        code: 'capacity_exceeded', detail: 'Kapasite aşıldı.',
        conflicts: [{ date: '2026-05-01', campaign_id: 'c1', campaign_name: 'Bayer', requested: 50, placed: 40 }],
      } },
    });
    // değişiklik yap
    wrapper.vm.rows[0].count = 999;
    await flushPromises();
    await wrapper.vm.save();
    await flushPromises();

    expect(wrapper.vm.capacityConflicts.length).toBe(1);
    expect(wrapper.vm.dirty).toBe(true);        // kaydedilemedi, kirli kaldı
    expect(wrapper.text()).toContain('Kapasite aşıldı');
  });

  it('kopyalama akışı önce dry_run sonra gerçek copy çağırır', async () => {
    const wrapper = await mountAndSelect();
    wrapper.vm.activeTab = 'copy';
    wrapper.vm.copyTargets = [2];
    await flushPromises();

    await wrapper.vm.previewCopy();
    await flushPromises();
    expect(mockApi.copyKioskSponsorships).toHaveBeenLastCalledWith(1, { target_kiosk_ids: [2], dry_run: true });

    await wrapper.vm.confirmCopy();
    await flushPromises();
    expect(mockApi.copyKioskSponsorships).toHaveBeenLastCalledWith(1, { target_kiosk_ids: [2], dry_run: false });
    expect(mockApi.copyKioskSponsorships).toHaveBeenCalledTimes(2);
  });

  it('simülasyon probe sonucu render edilir', async () => {
    const wrapper = await mountAndSelect();
    mockApi.simulateKioskSponsorship.mockResolvedValueOnce({ data: {
      kiosk_id: 1, date_from: '2026-05-01', date_to: '2026-05-01',
      probe: { duration_seconds: 15, window_start: '08:00', window_end: '19:00',
               max_shows_min: 2640, max_shows_max: 2640, window_seconds: 39600,
               free_seconds_min: 39600, days: [{ date: '2026-05-01', max_shows: 2640, free_seconds: 39600 }] },
      scenario: null,
    } });
    wrapper.vm.activeTab = 'simulate';
    await flushPromises();
    await wrapper.vm.runSimulation();
    await flushPromises();

    expect(mockApi.simulateKioskSponsorship).toHaveBeenCalled();
    expect(wrapper.vm.simResult.probe.max_shows_min).toBe(2640);
    expect(wrapper.text()).toContain('2640');
  });
});
