// İdle içerik (İçerik Yönetimi — başlık/metin) rotasyon deposu.
//
// Aktif idle içeriklerini lokal api-node'dan çeker ve karıştırılmış-torba
// (shuffled-bag / Fisher–Yates) algoritmasıyla döndürür. `currentIdleContent`
// store'u AdPromo large görünümü tarafından okunur; başlık fade + metin daktilo
// animasyonu içerik değişiminde tetiklenir.
//
// Kurallar:
//  - 0 içerik → currentIdleContent = null (başlık/metin gösterilmez).
//  - 1 içerik → sabit kalır; aynı metin tekrar tekrar daktilo edilmez.
//  - >1 içerik → torba tüketilene kadar her içerik birer kez gösterilir;
//    torba bitince yeniden karıştırılır ve yeni torbanın ilki önceki torbanın
//    son gösterilenıyla aynıysa değiştirilir (arka arkaya tekrar önlenir).
//  - Dwell süresi metin uzunluğuna göre 12–20 sn arasında hesaplanır.
//  - Her 6 içerikten sonra 1 kez eczane hoşgeldiniz slaytı gösterilir (8 sn).
//  - Offline: son başarılı içerik korunur (fetch hatası yut).

import { writable, get } from 'svelte/store';
import { fetchIdleContents, fetchKioskInfo } from './api.js';
import { deviceConfig, DEFAULT_DEVICE_CONFIG } from './deviceConfigStore.js';

export const currentIdleContent = writable(null);
export const eczaneAdi = writable('');
export const kioskId = writable(''); // kiosk_adi (display name) tutar

let contents = [];
let bag = [];
let lastShownId = null;
let rotateTimer = null;
let refreshTimer = null;
let started = false;
let configUnsubscribe = null;

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function refillBag() {
  if (contents.length <= 1) { bag = contents.slice(); return; }
  const next = shuffle(contents);
  if (lastShownId != null && next.length > 1 && next[0].id === lastShownId) {
    [next[0], next[1]] = [next[1], next[0]];
  }
  bag = next;
}

function dwellFor(item) {
  const config = get(deviceConfig);
  const dwellMin = (config.idle_content_min_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_min_seconds) * 1000;
  const dwellMax = (config.idle_content_max_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_max_seconds) * 1000;
  const len = (item?.metin || '').length;
  return Math.min(dwellMax, Math.max(dwellMin, dwellMin + len * 27));
}

function clearRotate() {
  if (rotateTimer) { clearTimeout(rotateTimer); rotateTimer = null; }
}

function advance() {
  clearRotate();
  if (contents.length === 0) {
    currentIdleContent.set(null);
    return;
  }

  if (contents.length === 1) {
    const only = contents[0];
    if (get(currentIdleContent)?.id !== only.id) currentIdleContent.set(only);
    lastShownId = only.id;
    return;
  }

  if (bag.length === 0) refillBag();
  const next = bag.shift();
  lastShownId = next.id;
  currentIdleContent.set(next);
  rotateTimer = setTimeout(advance, dwellFor(next));
}

function applyContents(list) {
  const active = (list || []).filter((c) => c && c.aktif !== false);
  contents = active;
  bag = [];

  if (contents.length === 0) {
    currentIdleContent.set(null);
    clearRotate();
    return;
  }
  if (contents.length === 1) {
    advance();
    return;
  }
  const cur = get(currentIdleContent);
  const stillValid = cur && !cur._type && contents.some((c) => c.id === cur.id);
  if (!stillValid) {
    advance();
  } else if (!rotateTimer) {
    rotateTimer = setTimeout(advance, dwellFor(cur));
  }
}

async function refresh() {
  try {
    const list = await fetchIdleContents();
    applyContents(list);
  } catch {
    // Offline: son başarılı içeriği koru.
  }
}

export function startIdleContent() {
  if (started) return;
  started = true;
  // Eczane adını bir kez çek, sessizce güncelle
  fetchKioskInfo().then((info) => {
    if (info?.eczane_adi) eczaneAdi.set(info.eczane_adi);
    if (info?.kiosk_adi)  kioskId.set(info.kiosk_adi);
  });
  refresh();
  configUnsubscribe = deviceConfig.subscribe((config) => {
    if (!started) return;
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(
      refresh,
      (config.idle_content_refresh_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_refresh_seconds) * 1000,
    );
    if (contents.length > 1) {
      clearRotate();
      rotateTimer = setTimeout(advance, dwellFor(get(currentIdleContent)));
    }
  });
}

export function stopIdleContent() {
  started = false;
  clearRotate();
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  configUnsubscribe?.();
  configUnsubscribe = null;
}
