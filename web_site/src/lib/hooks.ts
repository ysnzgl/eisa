/**
 * Ortak istemci hook'ları (yalnızca "use client" bileşenlerinde kullanın). Hepsi SSR/hidrasyon
 * güvenlidir: sunucuda ve hidrasyon sırasında "güvenli varsayılan" döner, hidrasyondan sonra
 * gerçek değere geçer (hydration mismatch olmaz).
 */

import { useSyncExternalStore } from "react";

function medyaSorgusuHook(sorgu: string, sunucuDegeri: boolean) {
  const abone = (bildir: () => void) => {
    const mql = window.matchMedia(sorgu);
    mql.addEventListener("change", bildir);
    return () => mql.removeEventListener("change", bildir);
  };
  const anlik = () => window.matchMedia(sorgu).matches;
  const sunucu = () => sunucuDegeri;
  return function useMedya(): boolean {
    return useSyncExternalStore(abone, anlik, sunucu);
  };
}

/** prefers-reduced-motion: reduce → true (SSR/hidrasyonda false). */
export const useAzHareket = medyaSorgusuHook("(prefers-reduced-motion: reduce)", false);

/** Hassas işaretçi (fare/trackpad) → true. Dokunmatikte false. (SSR'da false) */
export const useInceIsaretci = medyaSorgusuHook("(hover: hover) and (pointer: fine)", false);

/** lg kırılımı ve üstü (≥1024px). (SSR'da false) */
export const useGenisEkran = medyaSorgusuHook("(min-width: 1024px)", false);

const bosAbone = () => () => {};

/** Hidrasyon tamamlandı mı? (SSR ve hidrasyon render'ında false) */
export function useHidrasyonTamam(): boolean {
  return useSyncExternalStore(
    bosAbone,
    () => true,
    () => false,
  );
}
