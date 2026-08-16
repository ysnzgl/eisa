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
//  - Offline: son başarılı içerik korunur (fetch hatası yut).

import { writable, get } from 'svelte/store';
import { fetchIdleContents } from './api.js';

const REFRESH_MS = 5 * 60 * 1000; // ~5 dk yenileme
const DWELL_MIN = 12000;
const DWELL_MAX = 20000;

/** @type {import('svelte/store').Writable<{id:number,baslik:string,metin:string}|null>} */
export const currentIdleContent = writable(null);

let contents = [];        // aktif içerik listesi
let bag = [];             // karıştırılmış kalan sıra
let lastShownId = null;   // torbalar arası tekrar önleme
let rotateTimer = null;
let refreshTimer = null;
let started = false;

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
  const len = (item?.metin || '').length;
  return Math.min(DWELL_MAX, Math.max(DWELL_MIN, DWELL_MIN + len * 27));
}

function clearRotate() {
  if (rotateTimer) { clearTimeout(rotateTimer); rotateTimer = null; }
}

function advance() {
  clearRotate();
  if (contents.length === 0) { currentIdleContent.set(null); return; }
  if (contents.length === 1) {
    const only = contents[0];
    if (get(currentIdleContent)?.id !== only.id) currentIdleContent.set(only);
    lastShownId = only.id;
    return; // tek içerik: timer yok, yeniden daktilo yok
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
  const stillValid = cur && contents.some((c) => c.id === cur.id);
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
  refresh();
  refreshTimer = setInterval(refresh, REFRESH_MS);
}

export function stopIdleContent() {
  started = false;
  clearRotate();
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}
