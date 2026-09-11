import { writable } from 'svelte/store';
import { fetchDeviceConfig } from './api.js';

export const DEFAULT_DEVICE_CONFIG = Object.freeze({
  interaction_timeout_seconds: 20,
  idle_content_min_seconds: 10,
  idle_content_max_seconds: 12,
  idle_content_refresh_seconds: 300,
  idle_audio_delay_seconds: 1200,
  idle_audio_repeat_seconds: 300,
  idle_audio_schedule_mode: 'ALL_DAY',
  idle_audio_play_on_duty: false,
  idle_audio_duty_dates: [],
  idle_audio: Object.freeze({ enabled: false, files: [], media_url: '', original_name: '' }),
});

export const deviceConfig = writable(DEFAULT_DEVICE_CONFIG);

let refreshTimer = null;

function normalize(payload = {}) {
  const integer = (value, fallback) => Number.isInteger(Number(value)) ? Number(value) : fallback;
  const min = integer(payload.idle_content_min_seconds, DEFAULT_DEVICE_CONFIG.idle_content_min_seconds);
  const max = Math.max(min, integer(payload.idle_content_max_seconds, DEFAULT_DEVICE_CONFIG.idle_content_max_seconds));
  return {
    interaction_timeout_seconds: integer(payload.interaction_timeout_seconds, DEFAULT_DEVICE_CONFIG.interaction_timeout_seconds),
    idle_content_min_seconds: min,
    idle_content_max_seconds: max,
    idle_content_refresh_seconds: integer(payload.idle_content_refresh_seconds, DEFAULT_DEVICE_CONFIG.idle_content_refresh_seconds),
    idle_audio_delay_seconds: integer(payload.idle_audio_delay_seconds, DEFAULT_DEVICE_CONFIG.idle_audio_delay_seconds),
    idle_audio_repeat_seconds: integer(payload.idle_audio_repeat_seconds, DEFAULT_DEVICE_CONFIG.idle_audio_repeat_seconds),
    idle_audio_schedule_mode: payload.idle_audio_schedule_mode === 'BUSINESS_HOURS' ? 'BUSINESS_HOURS' : 'ALL_DAY',
    idle_audio_play_on_duty: payload.idle_audio_play_on_duty === true,
    idle_audio_duty_dates: Array.isArray(payload.idle_audio_duty_dates) ? payload.idle_audio_duty_dates : [],
    idle_audio: {
      enabled: payload?.idle_audio?.enabled === true,
      files: Array.isArray(payload?.idle_audio?.files) ? payload.idle_audio.files : [],
      media_url: payload?.idle_audio?.media_url || '',
      original_name: payload?.idle_audio?.original_name || '',
    },
  };
}

async function refresh() {
  try {
    deviceConfig.set(normalize(await fetchDeviceConfig()));
  } catch {
    // Offline/local API gecici hatasi: son basarili config korunur.
  }
}

export function startDeviceConfig() {
  if (refreshTimer) return;
  refresh();
  // Lokal snapshot hafif bir endpoint'tir; merkezi backend'e dogrudan cikmaz.
  refreshTimer = setInterval(refresh, 60_000);
}

export function stopDeviceConfig() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = null;
}
