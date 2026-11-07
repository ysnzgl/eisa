/**
 * Kelime kelime yükselerek beliren başlık (hero, sayfa_basligi).
 * Saf CSS animasyonu (`giris` utility) → sunucuda render edilir, hidrasyonu beklemez;
 * reduced-motion'da globals.css süreleri sıfırlar ve metin anında görünür.
 */

import type { CSSProperties } from "react";
import { cn, vurguParcala } from "@/lib/utils";

export interface KelimeBaslikProps {
  metin: string;
  /** Metin içinde vurgulanacak alt-metin */
  vurgu?: string | null;
  as?: "h1" | "h2" | "p";
  id?: string;
  className?: string;
  /** Vurgulu kelimelere eklenecek sınıf */
  vurguClassName?: string;
  /** İlk kelimenin gecikmesi (sn) */
  baslangic?: number;
  /** Kelimeler arası gecikme (sn) */
  aralik?: number;
}

interface Kelime {
  metin: string;
  vurgu: boolean;
  gecikme: number;
}

function kelimelereBol(metin: string, vurgu: string | null | undefined, baslangic: number, aralik: number): Kelime[] {
  const sonuc: Kelime[] = [];
  for (const parca of vurguParcala(metin, vurgu)) {
    for (const k of parca.metin.split(/\s+/).filter(Boolean)) {
      sonuc.push({ metin: k, vurgu: parca.vurgu, gecikme: baslangic + sonuc.length * aralik });
    }
  }
  return sonuc;
}

/** Başlık animasyonunun bitiş zamanı (sn) — sonraki öğelerin gecikmesini hesaplamak için. */
export function kelimeAnimasyonSuresi(metin: string, baslangic = 0.1, aralik = 0.06): number {
  const adet = metin.split(/\s+/).filter(Boolean).length;
  return baslangic + Math.max(0, adet - 1) * aralik + 0.5;
}

export function KelimeBaslik({
  metin,
  vurgu,
  as: Etiket = "h1",
  id,
  className,
  vurguClassName = "metin-gradyan",
  baslangic = 0.1,
  aralik = 0.06,
}: KelimeBaslikProps) {
  const kelimeler = kelimelereBol(metin, vurgu, baslangic, aralik);
  return (
    <Etiket id={id} className={className}>
      {kelimeler.map((k, i) => (
        <span key={i}>
          <span
            className={cn("giris inline-block", k.vurgu && vurguClassName)}
            style={{ "--gecikme": `${k.gecikme.toFixed(2)}s` } as CSSProperties}
          >
            {k.metin}
          </span>
          {i < kelimeler.length - 1 ? " " : null}
        </span>
      ))}
    </Etiket>
  );
}