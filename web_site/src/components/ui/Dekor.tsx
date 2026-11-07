/**
 * Dekoratif arka plan yardımcıları (aria-hidden, pointer-events yok, server component).
 * Ebeveyn `relative isolate` olmalı (Section bunu zaten verir).
 */

import { cn } from "@/lib/utils";

export interface GradientBackdropProps {
  /** koyu: kırmızı + soğuk mavi parıltılar; acik: hafif kırmızı/yeşil; kirmizi: canlı kırmızı */
  varyant?: "koyu" | "acik" | "kirmizi";
  /** Izgara deseni ekle */
  izgara?: boolean;
  className?: string;
}

/** Yumuşak, bulanık renk lekeleri + opsiyonel ızgara. */
export function GradientBackdrop({ varyant = "koyu", izgara = false, className }: GradientBackdropProps) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 -z-10 overflow-hidden", className)}>
      {varyant === "koyu" && (
        <>
          <div className="absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-primary/25 blur-[120px]" />
          <div className="absolute -bottom-48 -left-24 h-[28rem] w-[28rem] rounded-full bg-[#2b6cb0]/20 blur-[120px]" />
          <div className="absolute top-1/3 -right-32 h-[24rem] w-[24rem] rounded-full bg-[#3f514d]/40 blur-[100px]" />
        </>
      )}
      {varyant === "acik" && (
        <>
          <div className="absolute -top-32 right-0 h-[28rem] w-[28rem] rounded-full bg-primary/10 blur-[110px]" />
          <div className="absolute -bottom-40 -left-20 h-[26rem] w-[26rem] rounded-full bg-[#3f514d]/10 blur-[110px]" />
        </>
      )}
      {varyant === "kirmizi" && (
        <>
          <div className="absolute -top-24 -left-24 h-[26rem] w-[26rem] rounded-full bg-white/15 blur-[100px]" />
          <div className="absolute -bottom-32 right-0 h-[30rem] w-[30rem] rounded-full bg-[#8f0a10]/50 blur-[110px]" />
        </>
      )}
      {izgara && (
        <div
          className={cn(
            "absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]",
            varyant === "acik" ? "doku-izgara-acik" : "doku-izgara",
          )}
        />
      )}
    </div>
  );
}

export interface NoiseOverlayProps {
  /** 0-1, varsayılan 0.06 */
  opaklik?: number;
  className?: string;
}

/** İnce film greni dokusu — koyu zeminlerde derinlik hissi. */
export function NoiseOverlay({ opaklik = 0.06, className }: NoiseOverlayProps) {
  return (
    <div
      aria-hidden
      className={cn("doku-noise pointer-events-none absolute inset-0 -z-10 mix-blend-overlay", className)}
      style={{ opacity: opaklik }}
    />
  );
}
