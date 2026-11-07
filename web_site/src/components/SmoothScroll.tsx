"use client";

/**
 * Lenis yumuşak kaydırma + route/anchor kaydırma davranışları.
 *
 * - prefers-reduced-motion açıksa Lenis BAŞLATILMAZ (native kaydırma).
 * - Route değişiminde (hash yoksa) sayfanın en üstüne döner.
 * - URL'de hash varsa (ör. başka sayfadan /#pilot'a gelindiğinde) yükleme/geçiş sonrası
 *   header offset'li doğru konuma iner; geç yüklenen font/görsel kaymalarına karşı bir kez daha düzeltir.
 */

import Lenis from "lenis";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { azHareketTercihi, enUsteKaydir, hedefeKaydir, lenisAyarla } from "@/lib/kaydirma";

export function SmoothScroll() {
  const pathname = usePathname();
  const ilkRender = useRef(true);

  // Lenis kurulumu
  useEffect(() => {
    if (azHareketTercihi()) return;
    const lenis = new Lenis({
      autoRaf: true,
      lerp: 0.12,
      smoothWheel: true,
      anchors: false, // anchor tıklamaları AkilliLink/hedefeKaydir ile yönetilir
      stopInertiaOnNavigate: true,
    });
    lenisAyarla(lenis);
    return () => {
      lenisAyarla(null);
      lenis.destroy();
    };
  }, []);

  // Route değişimi / ilk yükleme
  useEffect(() => {
    const hash = window.location.hash;
    const ilk = ilkRender.current;
    ilkRender.current = false;

    if (!hash) {
      if (!ilk) enUsteKaydir(true);
      return;
    }

    // Hash'li geliş: içerik yerleşince konumlan, sonra geç kaymalara karşı düzelt.
    // Kullanıcı kendisi kaydırmaya başlarsa düzeltmeler iptal edilir.
    let iptal = false;
    const zamanlayicilar: number[] = [];
    const konumlan = () => {
      if (!iptal) hedefeKaydir(hash, { anlik: true });
    };
    const kullaniciEtkilesimi = () => {
      iptal = true;
    };
    const olaylar = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
    olaylar.forEach((o) => window.addEventListener(o, kullaniciEtkilesimi, { passive: true, once: true }));
    const raf = requestAnimationFrame(konumlan);
    zamanlayicilar.push(window.setTimeout(konumlan, 350));
    const yuklendi = () => konumlan();
    if (document.readyState !== "complete") window.addEventListener("load", yuklendi, { once: true });
    void document.fonts?.ready.then(() => konumlan());
    // 2 sn sonra artık düzeltme yapma.
    zamanlayicilar.push(window.setTimeout(kullaniciEtkilesimi, 2000));

    return () => {
      iptal = true;
      cancelAnimationFrame(raf);
      zamanlayicilar.forEach((z) => clearTimeout(z));
      window.removeEventListener("load", yuklendi);
      olaylar.forEach((o) => window.removeEventListener(o, kullaniciEtkilesimi));
    };
  }, [pathname]);

  return null;
}
