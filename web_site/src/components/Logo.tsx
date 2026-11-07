import Image from "next/image";
import { cn } from "@/lib/utils";

/** Logo oranı (viewBox 502.8 × 211). */
const ORAN = 502.8 / 211;

export interface LogoProps {
  /** koyu: açık zemin için (siyah yazı); beyaz: koyu zemin için */
  varyant?: "koyu" | "beyaz";
  /** px yükseklik, varsayılan 36 */
  yukseklik?: number;
  className?: string;
  priority?: boolean;
  alt?: string;
}

export function Logo({ varyant = "koyu", yukseklik = 36, className, priority, alt = "e-isa" }: LogoProps) {
  return (
    <Image
      src={varyant === "beyaz" ? "/brand/logo-white.svg" : "/brand/logo.svg"}
      alt={alt}
      width={Math.round(yukseklik * ORAN)}
      height={yukseklik}
      priority={priority}
      unoptimized
      className={cn("h-auto select-none", className)}
      style={{ height: yukseklik, width: "auto" }}
    />
  );
}
