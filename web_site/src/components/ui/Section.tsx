import type { ElementType, ReactNode } from "react";
import type { ArkaPlan } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Container, type ContainerGenislik } from "./Container";

export type SectionPadding = "yok" | "kucuk" | "normal" | "buyuk";

const PADDING: Record<SectionPadding, string> = {
  yok: "",
  kucuk: "py-12 md:py-16",
  normal: "py-20 md:py-28",
  buyuk: "py-28 md:py-36",
};

const ZEMIN: Record<ArkaPlan, string> = {
  acik: "bg-bg text-zemin-metin",
  gri: "bg-gri text-zemin-metin",
  koyu: "bg-dark text-zemin-metin",
};

export interface SectionProps {
  children: ReactNode;
  /** CONTRACT `arka_plan`. Bilinmeyen değer → `acik`. */
  arka_plan?: ArkaPlan | string;
  padding?: SectionPadding;
  /** false → Container sarmalayıcısı olmadan (tam genişlik içerik). */
  container?: boolean;
  genislik?: ContainerGenislik;
  as?: ElementType;
  /**
   * DOM id. NOT: Blok anchor id'leri BlockRenderer'ın sarmalayıcısına verilir;
   * bloklar bunu kullanmaz. Blok dışı sayfalar (blog vb.) için vardır.
   */
  id?: string;
  className?: string;
  containerClassName?: string;
  "aria-labelledby"?: string;
  "aria-label"?: string;
}

/**
 * Bölüm iskeleti: zemin rengi, dikey boşluk, Container.
 * `data-zemin` niteliği verir → içerideki `text-zemin-*`, `border-zemin-cizgi`, `bg-zemin-kart`
 * utility'leri ve ButonLink / SectionHeading renkleri zemine göre otomatik ayarlanır.
 */
export function Section({
  children,
  arka_plan = "acik",
  padding = "normal",
  container = true,
  genislik = "normal",
  as: Etiket = "section",
  id,
  className,
  containerClassName,
  ...aria
}: SectionProps) {
  const zemin: ArkaPlan = arka_plan === "gri" || arka_plan === "koyu" ? arka_plan : "acik";
  return (
    <Etiket
      id={id}
      data-zemin={zemin}
      className={cn("relative isolate", ZEMIN[zemin], PADDING[padding], className)}
      {...aria}
    >
      {container ? (
        <Container genislik={genislik} className={containerClassName}>
          {children}
        </Container>
      ) : (
        children
      )}
    </Etiket>
  );
}
