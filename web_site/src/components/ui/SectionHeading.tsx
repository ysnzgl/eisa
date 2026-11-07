import type { ReactNode } from "react";
import { cn, vurguParcala } from "@/lib/utils";
import { Reveal } from "./Reveal";

export interface SectionHeadingProps {
  /** Eyebrow (CONTRACT `ust_baslik`) */
  ust_baslik?: string | null;
  baslik?: string | null;
  /** Başlık içinde kırmızı vurgulanacak alt-metin (opsiyonel). */
  vurgu?: string | null;
  aciklama?: string | null;
  hizalama?: "sol" | "orta";
  /** Sayfa başına tek h1: yalnızca hero / sayfa_basligi h1 kullanır. Varsayılan h2. */
  seviye?: "h1" | "h2" | "h3";
  /** Başlık elementinin id'si (Section'da aria-labelledby için). */
  baslikId?: string;
  boyut?: "normal" | "buyuk";
  /** false → animasyonsuz */
  animasyon?: boolean;
  /** false → varsayılan alt boşluk (mb-12/16) eklenmez; boşluğu className ile verin. */
  altBosluk?: boolean;
  className?: string;
  /** Açıklamanın altına ek içerik (ör. butonlar) */
  children?: ReactNode;
}

/**
 * Bölüm başlığı: eyebrow + başlık + açıklama. Renkler zemine göre otomatik (text-zemin-*).
 * İçerik boşsa hiçbir şey render etmez.
 */
export function SectionHeading({
  ust_baslik,
  baslik,
  vurgu,
  aciklama,
  hizalama = "orta",
  seviye = "h2",
  baslikId,
  boyut = "normal",
  animasyon = true,
  altBosluk = true,
  className,
  children,
}: SectionHeadingProps) {
  if (!ust_baslik && !baslik && !aciklama && !children) return null;
  const Baslik = seviye;
  const orta = hizalama === "orta";

  const icerik = (
    <>
      {ust_baslik ? (
        <p className={cn("eyebrow mb-4 inline-flex items-center gap-2 text-zemin-vurgu", orta && "justify-center")}>
          <span aria-hidden className="inline-block size-1.5 rounded-full bg-primary" />
          {ust_baslik}
        </p>
      ) : null}
      {baslik ? (
        <Baslik
          id={baslikId}
          className={cn(
            "font-display font-bold text-zemin-baslik",
            boyut === "buyuk"
              ? "text-4xl leading-[1.05] sm:text-5xl lg:text-6xl"
              : "text-3xl leading-tight sm:text-4xl lg:text-[2.75rem]",
          )}
        >
          {vurguParcala(baslik, vurgu).map((p, i) =>
            p.vurgu ? (
              <span key={i} className="text-primary">
                {p.metin}
              </span>
            ) : (
              <span key={i}>{p.metin}</span>
            ),
          )}
        </Baslik>
      ) : null}
      {aciklama ? (
        <p className={cn("mt-5 text-lg leading-relaxed text-zemin-soluk", orta && "mx-auto", "max-w-3xl")}>{aciklama}</p>
      ) : null}
      {children ? <div className={cn("mt-8", orta && "flex justify-center")}>{children}</div> : null}
    </>
  );

  const sinif = cn(altBosluk && "mb-12 md:mb-16", orta ? "mx-auto max-w-4xl text-center" : "max-w-3xl", className);

  return animasyon ? <Reveal className={sinif}>{icerik}</Reveal> : <div className={sinif}>{icerik}</div>;
}
