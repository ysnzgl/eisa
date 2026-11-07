/**
 * Buton görünümlü link — CONTRACT `Buton` tipinden render edilir.
 *
 *   <ButonLink buton={{ etiket, href, stil }} />
 *   <ButonLink href="/iletisim" stil="ikincil">İletişim</ButonLink>
 *
 * - İç linkler next/link, `#x` / `/#x` anchor'ları header offset'li kaydırma, dış linkler
 *   yeni sekme + rel (AkilliLink üzerinden).
 * - Renkler bulunduğu Section'ın zeminine göre otomatik uyum sağlar (koyu zeminde ikincil/hayalet açık renk).
 * - Server component'te kullanılabilir.
 */

import type { ReactNode } from "react";
import { ArrowRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowRight";
import { ArrowUpRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowUpRight";
import type { Buton, ButonStil } from "@/lib/types";
import { cn, disLinkMi } from "@/lib/utils";
import { AkilliLink } from "./AkilliLink";
import { MagneticButton } from "./MagneticButton";

export type ButonBoyut = "kucuk" | "normal" | "buyuk";

const TEMEL =
  "group/buton relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-buton font-semibold transition-[background-color,border-color,color,box-shadow,transform] duration-300 ease-eisa active:scale-[0.98]";

const BOYUT: Record<ButonBoyut, string> = {
  kucuk: "h-10 px-4 text-sm",
  normal: "h-12 px-6 text-[0.9375rem]",
  buyuk: "h-14 px-8 text-base",
};

const STIL: Record<ButonStil, string> = {
  birincil: "bg-primary-aa text-white shadow-cta hover:bg-primary-hover",
  ikincil:
    "border border-zemin-cizgi bg-zemin-kart text-zemin-baslik shadow-kart hover:border-primary/40 hover:shadow-kart-hover",
  hayalet: "text-zemin-baslik hover:text-zemin-vurgu px-2!",
};

export function butonSiniflari(stil: ButonStil = "birincil", boyut: ButonBoyut = "normal", ek?: string): string {
  return cn(TEMEL, BOYUT[boyut], STIL[stil] ?? STIL.birincil, ek);
}

export interface ButonLinkProps {
  /** CONTRACT Buton nesnesi. Verilirse href/stil/children yerine kullanılır. */
  buton?: Buton;
  href?: string;
  stil?: ButonStil;
  children?: ReactNode;
  boyut?: ButonBoyut;
  /** Ok ikonu: varsayılan birincil/hayalet için açık */
  ok?: boolean;
  /** Mıknatıs etkisi (yalnızca fare ile), varsayılan birincil için açık */
  miknatis?: boolean;
  className?: string;
  yeniSekme?: boolean;
}

export function ButonLink({
  buton,
  href,
  stil,
  children,
  boyut = "normal",
  ok,
  miknatis,
  className,
  yeniSekme,
}: ButonLinkProps) {
  const hedef = buton?.href ?? href ?? "#";
  const gorunum: ButonStil = buton?.stil ?? stil ?? "birincil";
  const icerik = buton?.etiket ?? children;
  const disLink = disLinkMi(hedef);
  const okGoster = ok ?? gorunum !== "ikincil";
  const OkIkonu = disLink ? ArrowUpRightIcon : ArrowRightIcon;

  const link = (
    <AkilliLink href={hedef} yeniSekme={yeniSekme} className={butonSiniflari(gorunum, boyut, className)}>
      <span>{icerik}</span>
      {okGoster ? (
        <OkIkonu
          aria-hidden
          weight="bold"
          className="size-4 transition-transform duration-300 group-hover/buton:translate-x-0.5"
        />
      ) : null}
    </AkilliLink>
  );

  return (miknatis ?? gorunum === "birincil") ? <MagneticButton>{link}</MagneticButton> : link;
}

/** Buton listesini sarmalayan yardımcı (0-3 buton). Boşsa null. */
export function ButonGrubu({
  butonlar,
  className,
  boyut,
}: {
  butonlar: Buton[] | null | undefined;
  className?: string;
  boyut?: ButonBoyut;
}) {
  if (!butonlar?.length) return null;
  return (
    <div className={cn("flex flex-wrap items-center gap-3 sm:gap-4", className)}>
      {butonlar.map((b, i) => (
        <ButonLink key={`${b.href}-${i}`} buton={b} boyut={boyut} />
      ))}
    </div>
  );
}
