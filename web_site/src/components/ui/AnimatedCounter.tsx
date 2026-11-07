"use client";

/**
 * Görünür olunca 0'dan hedef değere sayan sayaç (tr-TR biçimi: 185.000).
 * - Ekran okuyucular ve JS'siz render için son değer her zaman metin olarak bulunur.
 * - reduced-motion açıksa animasyonsuz son değer gösterilir.
 */

import { animate, useInView } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useAzHareket, useHidrasyonTamam } from "@/lib/hooks";
import { sayiFormatla } from "@/lib/utils";

export interface AnimatedCounterProps {
  deger: number;
  onek?: string;
  sonek?: string;
  /** sn, varsayılan 1.6 */
  sure?: number;
  /** Ondalık basamak, varsayılan 0 */
  ondalik?: number;
  className?: string;
}

export function AnimatedCounter({ deger, onek = "", sonek = "", sure = 1.6, ondalik = 0, className }: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const gorundu = useInView(ref, { once: true, amount: 0.6 });
  const azHareket = useAzHareket();
  const hidrasyonTamam = useHidrasyonTamam();
  const [gosterilen, setGosterilen] = useState<number | null>(null);

  useEffect(() => {
    if (!gorundu || azHareket) return;
    const kontrol = animate(0, deger, {
      duration: sure,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setGosterilen(v),
      onComplete: () => setGosterilen(null),
    });
    return () => kontrol.stop();
  }, [gorundu, azHareket, deger, sure]);

  const bicim = (v: number) =>
    sayiFormatla(v, { minimumFractionDigits: ondalik, maximumFractionDigits: ondalik });
  const sonMetin = `${onek}${bicim(deger)}${sonek}`;
  // SSR/JS'siz: son değer. Hidrasyondan sonra, görünmeden önce 0; görününce sayar.
  const animasyonBekliyor = hidrasyonTamam && !azHareket && !gorundu;
  const anlik = gosterilen ?? (animasyonBekliyor ? 0 : deger);

  return (
    <span ref={ref} className={className}>
      <span className="sr-only">{sonMetin}</span>
      <span aria-hidden className="tabular-nums">
        {onek}
        {bicim(anlik)}
        {sonek}
      </span>
    </span>
  );
}
