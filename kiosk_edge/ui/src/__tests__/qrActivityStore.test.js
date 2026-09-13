import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/api.js', () => ({
  fetchLastQrActivity: vi.fn(),
}));

import { fetchLastQrActivity } from '../lib/api.js';
import { markQrCreated, qrActivity, refreshQrActivity, stopQrActivity } from '../lib/qrActivityStore.js';

describe('QR activity store', () => {
  beforeEach(() => {
    stopQrActivity();
    qrActivity.set({ lastQrCreatedAt: null });
    vi.clearAllMocks();
  });

  it('lokal DB son QR zamanini store ile uzlastirir', async () => {
    fetchLastQrActivity.mockResolvedValue({ last_qr_created_at: '2026-09-13T19:34:46.508Z' });

    await refreshQrActivity();

    expect(get(qrActivity).lastQrCreatedAt).toBe('2026-09-13T19:34:46.508Z');
  });

  it('QR olustuktan sonra gec donen eski polling yaniti yeni zamani ezmez', async () => {
    let resolveRequest;
    fetchLastQrActivity.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
    const pendingRefresh = refreshQrActivity();

    markQrCreated('2026-09-13T19:40:00.000Z');
    resolveRequest({ last_qr_created_at: '2026-09-13T19:30:00.000Z' });
    await pendingRefresh;

    expect(get(qrActivity).lastQrCreatedAt).toBe('2026-09-13T19:40:00.000Z');
  });
});
