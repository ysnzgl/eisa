/**
 * dooh.js servis katmanı — endpoint URL/metot/gövde sözleşmesi testleri.
 *
 * axios mock'lanır; her fonksiyonun doğru HTTP metodunu, yolu ve gövdeyi
 * çağırdığı doğrulanır (Kiosk Sponsorluk yeni sözleşmesi).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', async () => {
  const mockHttp = {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  return { default: { create: vi.fn(() => mockHttp) }, __mockHttp: mockHttp };
});

import * as dooh from '../../services/dooh.js';

let http;
beforeEach(async () => {
  vi.clearAllMocks();
  const { default: axiosMock } = await import('axios');
  http = axiosMock.create();
});

describe('Sponsorluk tanımları (campaigns)', () => {
  it('listCampaignsV2 GET campaigns/', () => {
    dooh.listCampaignsV2({ search: 'a' });
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/', { params: { search: 'a' } });
  });
  it('createCampaignV2 POST campaigns/', () => {
    dooh.createCampaignV2({ name: 'X' });
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/', { name: 'X' });
  });
  it('updateCampaignV2 PATCH campaigns/{id}/', () => {
    dooh.updateCampaignV2('c1', { status: 'PAUSED' });
    expect(http.patch).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/c1/', { status: 'PAUSED' });
  });
  it('bulkActionCampaignsV2 POST bulk-action/', () => {
    dooh.bulkActionCampaignsV2('delete', [1, 2]);
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/bulk-action/', { action: 'delete', ids: [1, 2] });
  });
  it('getCampaignKiosks GET campaigns/{id}/kiosks/', () => {
    dooh.getCampaignKiosks('c1');
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/c1/kiosks/');
  });
  it('assignKiosksToCampaign POST assign-kiosks/ doğru gövde', () => {
    const body = { kiosk_ids: [1, 2], window_start: '08:00', window_end: '19:00', count: 10, dry_run: true };
    dooh.assignKiosksToCampaign('c1', body);
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/campaigns/c1/assign-kiosks/', body);
  });
});

describe('Kiosk bazlı sponsorluk yönetimi', () => {
  it('listSponsorshipKiosks GET sponsorship-kiosks/ (unassigned filtresi)', () => {
    dooh.listSponsorshipKiosks({ unassigned: 1 });
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/', { params: { unassigned: 1 } });
  });
  it('getKioskSponsorships GET sponsorship-kiosks/{id}/sponsorships/', () => {
    dooh.getKioskSponsorships(7);
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/7/sponsorships/');
  });
  it('putKioskSponsorships PUT {items} sarar', () => {
    const items = [{ campaign_id: 1, window_start: '08:00', window_end: '19:00', count: 5 }];
    dooh.putKioskSponsorships(7, items);
    expect(http.put).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/7/sponsorships/', { items });
  });
  it('previewKioskSponsorships POST preview/', () => {
    const body = { date: '2026-05-01', items: [] };
    dooh.previewKioskSponsorships(7, body);
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/7/preview/', body);
  });
  it('copyKioskSponsorships POST copy/', () => {
    const body = { target_kiosk_ids: [2, 3], dry_run: true };
    dooh.copyKioskSponsorships(7, body);
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/7/copy/', body);
  });
  it('simulateKioskSponsorship POST simulate/', () => {
    const body = { date_from: '2026-05-01', date_to: '2026-05-07', include_existing: true, probe: null, scenario: [] };
    dooh.simulateKioskSponsorship(7, body);
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/sponsorship-kiosks/7/simulate/', body);
  });
});

describe('Korunan endpoint\'ler', () => {
  it('getKioskDayStream GET day-stream/', () => {
    dooh.getKioskDayStream(7, '2026-05-01');
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/playlists/day-stream/', { params: { kiosk: 7, date: '2026-05-01' } });
  });
  it('generatePlaylists / listGenerationJobs / getKioskHealth korunur', () => {
    dooh.generatePlaylists({ kiosk: 1 });
    dooh.listGenerationJobs();
    dooh.getKioskHealth();
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/playlists/generate/', { kiosk: 1 });
    expect(http.get).toHaveBeenCalledWith('/api/campaigns/v2/playlists/jobs/');
    expect(http.get).toHaveBeenCalledWith('/api/pharmacies/kiosks/');
  });
  it('creative CRUD korunur', () => {
    dooh.createCreative({ campaign: 'c1', duration_seconds: 15 });
    dooh.updateCreative('cr1', { duration_seconds: 30 });
    dooh.deleteCreative('cr1');
    expect(http.post).toHaveBeenCalledWith('/api/campaigns/v2/creatives/', { campaign: 'c1', duration_seconds: 15 });
    expect(http.patch).toHaveBeenCalledWith('/api/campaigns/v2/creatives/cr1/', { duration_seconds: 30 });
    expect(http.delete).toHaveBeenCalledWith('/api/campaigns/v2/creatives/cr1/');
  });
});

describe('Kaldırılan endpoint\'ler export edilmiyor', () => {
  const removed = [
    'getCampaignRules', 'setCampaignRules', 'getCampaignTimeline', 'getCampaignCalendar',
    'getCampaignTargets', 'setCampaignTargets', 'simulateCampaign', 'activateCampaign',
    'previewCampaignCapacity', 'getInventoryAvailability', 'getPricingMatrix', 'updatePricingMatrix',
    'listPlaylistTemplates', 'listHourPlans', 'listDayPlans', 'listScheduleRules',
    'getPharmaciesForTargeting', 'getEczanelerByIlce',
  ];
  it.each(removed)('%s artık yok', (fn) => {
    expect(dooh[fn]).toBeUndefined();
  });
});
