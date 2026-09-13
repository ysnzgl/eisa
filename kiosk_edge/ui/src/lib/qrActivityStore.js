import { writable } from 'svelte/store';
import { fetchLastQrActivity } from './api.js';

export const qrActivity = writable({ lastQrCreatedAt: null });

let refreshTimer = null;
let qrMutationVersion = 0;

export async function refreshQrActivity() {
  const requestVersion = qrMutationVersion;
  try {
    const data = await fetchLastQrActivity();
    const lastQrCreatedAt = data?.last_qr_created_at || null;
    // QR olusturulurken baslamis eski bir polling istegi, markQrCreated ile
    // yazilan daha yeni zamani sonradan ezmesin.
    if (requestVersion === qrMutationVersion) {
      qrActivity.update((current) => ({
        lastQrCreatedAt: lastQrCreatedAt || current.lastQrCreatedAt || null,
      }));
    }
    return lastQrCreatedAt;
  } catch {
    // Lokal API gecici ulasilamazsa son bilinen QR zamani korunur.
    return null;
  }
}

export function markQrCreated(createdAt = new Date().toISOString()) {
  qrMutationVersion += 1;
  qrActivity.set({ lastQrCreatedAt: createdAt || new Date().toISOString() });
}

export function startQrActivity() {
  if (refreshTimer) return;
  refreshQrActivity();
  refreshTimer = setInterval(refreshQrActivity, 30_000);
}

export function stopQrActivity() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = null;
}
