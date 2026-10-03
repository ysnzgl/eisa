import { describe, expect, it, vi } from 'vitest';
import { createApplicationRefresher } from '../src/maintenance.js';

function setup({ provisioned = true, manifest = false, bootstrapConfig = null } = {}) {
  const calls = [];
  const refreshedSettings = { doohKioskAck: manifest, bootstrapDeviceConfig: bootstrapConfig };
  const dependencies = {
    db: { name: 'db' },
    settings: { name: 'settings' },
    resolveRuntimeSettings: vi.fn(async () => { calls.push('provision'); return refreshedSettings; }),
    hasAppKeyCredentials: vi.fn(() => provisioned),
    syncDeviceConfig: vi.fn(async () => { calls.push('device-config'); }),
    pullFromCentral: vi.fn(async () => { calls.push('pull'); }),
    pingAndSyncPlaylist: vi.fn(async () => { calls.push('playlist'); }),
    pingAndSyncManifest: vi.fn(async () => { calls.push('manifest'); }),
  };
  return { calls, dependencies, refresh: createApplicationRefresher(dependencies) };
}

describe('uygulama yenileme', () => {
  it('provision uzlastirma, cihaz ayari, pull ve playlist adimlarini sirayla calistirir', async () => {
    const { calls, refresh } = setup({ bootstrapConfig: { interaction_timeout_seconds: 30 } });
    await expect(refresh()).resolves.toEqual({ provisioned: true, synced: true });
    expect(calls).toEqual(['provision', 'device-config', 'pull', 'playlist']);
  });

  it('DOOH ACK modunda manifest ping kullanir', async () => {
    const { calls, refresh } = setup({ manifest: true });
    await refresh();
    expect(calls).toEqual(['provision', 'pull', 'manifest']);
  });

  it('provision tamam degilse merkezi pull yapmaz', async () => {
    const { calls, refresh } = setup({ provisioned: false });
    await expect(refresh()).resolves.toEqual({ provisioned: false, synced: false });
    expect(calls).toEqual(['provision']);
  });

  it('ayni anda gelen yenilemeleri tek bir akista birlestirir', async () => {
    let release;
    const gate = new Promise((resolve) => { release = resolve; });
    const { dependencies, refresh } = setup();
    dependencies.resolveRuntimeSettings.mockImplementation(async () => {
      await gate;
      return { doohKioskAck: false, bootstrapDeviceConfig: null };
    });
    const first = refresh();
    const second = refresh();
    expect(first).toBe(second);
    release();
    await first;
    expect(dependencies.resolveRuntimeSettings).toHaveBeenCalledOnce();
  });
});
