"use client";

/**
 * CMS medyası için next/image sarmalayıcısı. `MEDIA_BASE_URL + yol` otomatik eklenir.
 *
 *   <MediaImage medya={veri.gorsel} sizes="(min-width: 1024px) 50vw, 100vw" className="rounded-kart" />
 *   <MediaImage medya={kisi.foto} fill sizes="200px"><VarsayilanAvatar /></MediaImage>  // null → children
 *
 * - `fill` verilmezse ve medyada genişlik/yükseklik varsa intrinsic boyutla render eder;
 *   boyut bilinmiyorsa otomatik `fill` moduna geçer (ebeveyn `relative` + boyutlu olmalı).
 * - `alt` medyadaki `alt` alanından gelir; `alt` prop'u ile ezilebilir (dekoratifse alt="").
 */

import Image from "next/image";
import type { ReactNode } from "react";
import { useMediaUrl } from "@/components/SiteProvider";
import { medyaVarMi } from "@/lib/media";
import type { MediaRef } from "@/lib/types";

export interface MediaImageProps {
  medya: MediaRef | null | undefined;
  /** Medya yoksa gösterilecek yedek içerik */
  children?: ReactNode;
  alt?: string;
  fill?: boolean;
  sizes?: string;
  priority?: boolean;
  className?: string;
  /** 75 dışında değerler için next.config images.qualities'e eklenmeli. */
  quality?: number;
}

export function MediaImage({ medya, children, alt, fill, sizes, priority, className, quality }: MediaImageProps) {
  const url = useMediaUrl();
  if (!medyaVarMi(medya)) return <>{children ?? null}</>;
  const src = url(medya.yol);
  if (!src) return <>{children ?? null}</>;

  const altMetin = alt ?? medya.alt ?? "";
  const boyutVar = Boolean(medya.genislik && medya.yukseklik);

  if (fill || !boyutVar) {
    return (
      <Image
        src={src}
        alt={altMetin}
        fill
        sizes={sizes ?? "100vw"}
        priority={priority}
        quality={quality}
        className={className ?? "object-cover"}
      />
    );
  }

  return (
    <Image
      src={src}
      alt={altMetin}
      width={medya.genislik ?? undefined}
      height={medya.yukseklik ?? undefined}
      sizes={sizes}
      priority={priority}
      quality={quality}
      className={className}
    />
  );
}
