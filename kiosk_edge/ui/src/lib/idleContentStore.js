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

const REFRESH_MS = 5 * 60 * 1000;
const DWELL_MIN = 10000;
const DWELL_MAX = 12000;
const WELCOME_DWELL = 12000;
const WELCOME_EVERY = 5; // TEST: hemen welcome göster

/** Normal içerik veya `{_type:'welcome', eczane_adi:string}` */
export const currentIdleContent = writable(null);
export const eczaneAdi = writable('');
export const kioskId   = writable(''); // kiosk_adi (display name) tutar

let contents = [];
let bag = [];
let lastShownId = null;
let rotateTimer = null;
let refreshTimer = null;
let started = false;
let shownSinceWelcome = 0; // welcome'a kadar gösterilen içerik sayacı

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
  if (item?._type === 'welcome') return WELCOME_DWELL;
  const len = (item?.metin || '').length;
  return Math.min(DWELL_MAX, Math.max(DWELL_MIN, DWELL_MIN + len * 27));
}

function clearRotate() {
  if (rotateTimer) { clearTimeout(rotateTimer); rotateTimer = null; }
}

function advance() {
  clearRotate();
  if (contents.length === 0) { currentIdleContent.set(null); return; }

  // Her WELCOME_EVERY normal içerikten sonra welcome slaytı göster
  if (shownSinceWelcome >= WELCOME_EVERY) {
    shownSinceWelcome = 0;
    const adi = get(eczaneAdi);
    currentIdleContent.set({ _type: 'welcome', eczane_adi: adi });
    rotateTimer = setTimeout(advance, WELCOME_DWELL);
    return;
  }

  if (contents.length === 1) {
    const only = contents[0];
    if (get(currentIdleContent)?.id !== only.id) currentIdleContent.set(only);
    lastShownId = only.id;
    shownSinceWelcome += 1;
    return;
  }
  if (bag.length === 0) refillBag();
  const next = bag.shift();
  lastShownId = next.id;
  shownSinceWelcome += 1;
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
  refreshTimer = setInterval(refresh, REFRESH_MS);
}

export function stopIdleContent() {
  started = false;
  clearRotate();
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}
