/**
 * surec_adimlari — Süreç Adımları. CONTRACT §8.
 * Masaüstünde yatay zaman çizelgesi (bağlantı çizgisi görünür olunca çizilir), mobilde dikey.
 */

import { CizilenCizgi } from "@/components/blocks/CizilenCizgi";
import { Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { SurecAdimlariVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

const SUTUN: Record<number, string> = {
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
};

const HALKA = {
  acik: "ring-bg",
  gri: "ring-gri",
  koyu: "ring-dark",
} as const;

export default function SurecAdimlari({ veri, blokId }: BlokProps<SurecAdimlariVeri>) {
  const adimlar = veri.adimlar ?? [];
  if (!adimlar.length) return null;
  const n = adimlar.length;
  const tekSatir = n <= 4;
  const zemin = veri.arka_plan === "gri" || veri.arka_plan === "koyu" ? veri.arka_plan : "acik";
  const baslikId = `${blokId}-baslik`;

  return (
    <Section arka_plan={zemin} aria-labelledby={baslikId}>
      <SectionHeading ust_baslik={veri.ust_baslik} baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} />
      <div className="relative">
        {/* Yatay çizgi: ilk ve son dairenin merkezleri arasında */}
        {tekSatir ? (
          <div aria-hidden className="absolute top-7 hidden h-px lg:block" style={{ left: `${50 / n}%`, right: `${50 / n}%` }}>
            <CizilenCizgi yon="yatay" className="absolute inset-0" />
          </div>
        ) : null}
        <span aria-hidden className="absolute top-2 bottom-2 left-7 w-px lg:hidden">
          <CizilenCizgi yon="dikey" className="absolute inset-0" />
        </span>

        <Stagger as="ol" aralik={0.12} className={cn("relative grid gap-10 lg:gap-8", tekSatir ? SUTUN[Math.max(2, n)] : "lg:grid-cols-4")}>
          {adimlar.map((a, i) => (
            <StaggerItem as="li" key={i} className="relative pl-20 lg:pl-0 lg:text-center">
              <span
                className={cn(
                  "absolute top-0 left-0 z-10 flex size-14 items-center justify-center rounded-full bg-primary font-display text-lg font-bold text-white shadow-cta ring-8 lg:relative lg:mx-auto",
                  HALKA[zemin],
                )}
              >
                {i + 1}
              </span>
              <h3 className="pt-3 font-display text-xl font-semibold text-zemin-baslik lg:mt-6 lg:pt-0">{a.baslik}</h3>
              {a.metin ? <p className="mt-2 leading-relaxed text-zemin-soluk lg:mx-auto lg:max-w-xs">{a.metin}</p> : null}
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </Section>
  );
}