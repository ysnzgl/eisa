/**
 * Blok dışı sayfalar (blog, 404, hata) için koyu sayfa üst alanı.
 * `data-ilk-blok="koyu"` verir → header en üstte şeffaf/açık metin modunda başlar.
 */

import type { ReactNode } from "react";
import { GradientBackdrop, NoiseOverlay } from "@/components/ui/Dekor";
import { Section } from "@/components/ui/Section";
import type { ContainerGenislik } from "@/components/ui/Container";
import { cn } from "@/lib/utils";

export interface SayfaUstuProps {
  children: ReactNode;
  genislik?: ContainerGenislik;
  className?: string;
  /** Alt boşluk; altına binen içerik (ör. kapak görseli) için büyütülebilir */
  altBosluk?: string;
}

export function SayfaUstu({ children, genislik = "orta", className, altBosluk = "pb-16 md:pb-20" }: SayfaUstuProps) {
  return (
    <div data-ilk-blok="koyu">
      <Section
        arka_plan="koyu"
        padding="yok"
        genislik={genislik}
        className={cn("overflow-hidden pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+3rem)]", altBosluk, className)}
      >
        <GradientBackdrop varyant="koyu" izgara />
        <NoiseOverlay />
        {children}
      </Section>
    </div>
  );
}
