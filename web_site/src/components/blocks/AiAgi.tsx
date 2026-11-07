"use client";

/**
 * Hero arka planı: hafif "yapay zeka ağı" (noktalar + yakın noktalar arası çizgiler).
 * - Canvas 2D, DPR en fazla 1.5, nokta sayısı alana göre (en fazla 80).
 * - Görünmezken (IntersectionObserver / sekme gizli) durur.
 * - prefers-reduced-motion: tek statik kare çizilir.
 * - Fare bölüm üzerindeyken yakındaki noktalara kırmızı bağlantılar çizilir.
 */

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface Nokta {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  kirmizi: boolean;
}

const BAG_MESAFESI = 140;
const FARE_MESAFESI = 190;

export function AiAgi({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const azHareket = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let w = 0;
    let h = 0;
    let noktalar: Nokta[] = [];
    let raf = 0;
    let gorunur = true;
    let fare: { x: number; y: number } | null = null;

    const kur = () => {
      const r = canvas.getBoundingClientRect();
      w = r.width;
      h = r.height;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const adet = Math.min(80, Math.max(24, Math.round((w * h) / 16000)));
      noktalar = Array.from({ length: adet }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.4 + 0.6,
        kirmizi: Math.random() < 0.18,
      }));
    };

    const ciz = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.lineWidth = 1;
      for (let i = 0; i < noktalar.length; i++) {
        const a = noktalar[i];
        for (let j = i + 1; j < noktalar.length; j++) {
          const b = noktalar[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < BAG_MESAFESI) {
            ctx.strokeStyle = `rgba(255,255,255,${((1 - d / BAG_MESAFESI) * 0.16).toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        if (fare) {
          const d = Math.hypot(a.x - fare.x, a.y - fare.y);
          if (d < FARE_MESAFESI) {
            ctx.strokeStyle = `rgba(237,28,36,${((1 - d / FARE_MESAFESI) * 0.55).toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(fare.x, fare.y);
            ctx.stroke();
          }
        }
      }
      for (const n of noktalar) {
        ctx.fillStyle = n.kirmizi ? "rgba(255,90,96,0.9)" : "rgba(255,255,255,0.55)";
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.kirmizi ? n.r + 0.6 : n.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const adim = () => {
      for (const n of noktalar) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
      }
      ciz();
      raf = requestAnimationFrame(adim);
    };

    const baslat = () => {
      if (!raf && gorunur && !document.hidden && !azHareket) raf = requestAnimationFrame(adim);
    };
    const durdur = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };

    kur();
    ciz();
    baslat();

    const ro = new ResizeObserver(() => {
      kur();
      ciz();
    });
    ro.observe(canvas);

    const io = new IntersectionObserver(([g]) => {
      gorunur = Boolean(g?.isIntersecting);
      if (gorunur) baslat();
      else durdur();
    });
    io.observe(canvas);

    const gorunurluk = () => (document.hidden ? durdur() : baslat());
    document.addEventListener("visibilitychange", gorunurluk);

    const alan = canvas.closest("section") ?? canvas.parentElement;
    const hareket = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const r = canvas.getBoundingClientRect();
      fare = { x: e.clientX - r.left, y: e.clientY - r.top };
      if (azHareket) ciz();
    };
    const cik = () => {
      fare = null;
      if (azHareket) ciz();
    };
    alan?.addEventListener("pointermove", hareket);
    alan?.addEventListener("pointerleave", cik);

    return () => {
      durdur();
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", gorunurluk);
      alan?.removeEventListener("pointermove", hareket);
      alan?.removeEventListener("pointerleave", cik);
    };
  }, []);

  return <canvas ref={ref} aria-hidden className={cn("pointer-events-none absolute inset-0 h-full w-full", className)} />;
}