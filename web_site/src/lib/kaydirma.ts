/**
 * Kaydırma yardımcıları (yalnızca tarayıcıda çağrılır).
 *
 * Lenis örneği SmoothScroll tarafından `lenisAyarla()` ile kaydedilir. Lenis yoksa
 * (reduced-motion, henüz yüklenmedi) native `window.scrollTo` kullanılır.
 * Anchor kaydırmalarında sabit header yüksekliği kadar offset uygulanır.
 */

import type Lenis from "lenis";

let lenisOrnegi: Lenis | null = null;

export function lenisAyarla(l: Lenis | null): void {
  lenisOrnegi = l;
}

export function lenisGetir(): Lenis | null {
  return lenisOrnegi;
}

export function azHareketTercihi(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** CSS değişkeninden px cinsinden uzunluk okur (rem/px destekli). */
function cssUzunluk(degisken: string, varsayilanPx: number): number {
  if (typeof window === "undefined") return varsayilanPx;
  const ham = getComputedStyle(document.documentElement).getPropertyValue(degisken).trim();
  if (!ham) return varsayilanPx;
  const sayi = parseFloat(ham);
  if (Number.isNaN(sayi)) return varsayilanPx;
  if (ham.endsWith("rem")) return sayi * parseFloat(getComputedStyle(document.documentElement).fontSize || "16");
  return sayi;
}

/** Anchor hedefinin üstünde bırakılacak boşluk: daralmış header + önizleme bandı + 16px. */
export function headerOffset(): number {
  return cssUzunluk("--header-yukseklik-dar", 64) + cssUzunluk("--onizleme-bant", 0) + 16;
}

/** `#x`, `x` veya element → element */
function hedefBul(hedef: string | HTMLElement): HTMLElement | null {
  if (typeof hedef !== "string") return hedef;
  const id = decodeURIComponent(hedef.replace(/^#/, ""));
  if (!id) return null;
  return document.getElementById(id);
}

/**
 * Hedef elemente header offset'li yumuşak kaydırma. Hedef yoksa false döner.
 * `anlik`: animasyonsuz (sayfa yüklemesi sonrası konumlandırma için).
 */
export function hedefeKaydir(hedef: string | HTMLElement, secenek: { anlik?: boolean } = {}): boolean {
  const el = hedefBul(hedef);
  if (!el) return false;
  const anlik = secenek.anlik || azHareketTercihi();
  const offset = headerOffset();
  if (lenisOrnegi) {
    lenisOrnegi.scrollTo(el, { offset: -offset, immediate: anlik, force: true });
  } else {
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: Math.max(0, top), behavior: anlik ? "auto" : "smooth" });
  }
  // Erişilebilirlik: odak hedefe taşınır (görsel kaydırma olmadan).
  if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
  el.focus({ preventScroll: true });
  return true;
}

/** Sayfanın en üstüne kaydırır. */
export function enUsteKaydir(anlik = true): void {
  if (lenisOrnegi) {
    lenisOrnegi.scrollTo(0, { immediate: anlik, force: true });
  } else {
    window.scrollTo({ top: 0, behavior: anlik || azHareketTercihi() ? "auto" : "smooth" });
  }
}

/** Mobil menü / modal için gövde kaydırma kilidi. */
export function kaydirmaKilidi(kilitli: boolean): void {
  document.documentElement.classList.toggle("kaydirma-kilitli", kilitli);
  if (lenisOrnegi) {
    if (kilitli) lenisOrnegi.stop();
    else lenisOrnegi.start();
  }
}
