import { afterEach, describe, expect, it } from 'vitest';

import { getDeviceConfig, syncDeviceConfig } from '../src/deviceConfig.js';
import { fakeSettings, makeMemoryDb } from './helpers.js';


describe('kiosk device config', () => {
  let db;
  afterEach(() => db?.close());

  it('mevcut kiosk davranisini koruyan varsayilanlari üretir', () => {
    db = makeMemoryDb();
    expect(getDeviceConfig(db)).toMatchObject({
      interaction_timeout_seconds: 20,
      idle_content_min_seconds: 10,
      idle_content_max_seconds: 12,
      idle_content_refresh_seconds: 300,
      idle_audio_delay_seconds: 1200,
      idle_audio_repeat_seconds: 300,
      idle_audio: { enabled: false, files: [], media_url: '' },
    });
  });

  it("kiosk-bazli zamanlari lokal snapshot'a uygular", async () => {
    db = makeMemoryDb();
    await syncDeviceConfig(db, {
      interaction_timeout_seconds: 45,
      idle_content_min_seconds: 15,
      idle_content_max_seconds: 25,
      idle_content_refresh_seconds: 600,
      idle_audio_delay_seconds: 900,
      idle_audio_repeat_seconds: 420,
      idle_audio: { enabled: false },
    }, fakeSettings);
    expect(getDeviceConfig(db)).toMatchObject({
      interaction_timeout_seconds: 45,
      idle_content_min_seconds: 15,
      idle_content_max_seconds: 25,
      idle_content_refresh_seconds: 600,
      idle_audio_delay_seconds: 900,
      idle_audio_repeat_seconds: 420,
      idle_audio: { enabled: false },
    });
  });
});
