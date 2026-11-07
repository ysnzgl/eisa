/**
 * vurgu_bandi — Vurgu Bandı. CONTRACT §8.
 * Büyük slogan/alıntı bandı; vurgu cümlesi görünür olunca kelime kelime belirir.
 * stil: kirmizi | koyu | acik
 */

import { Container } from "@/components/ui/Container";
import { GradientBackdrop, NoiseOverlay } from "@/components/ui/Dekor";
import { Icon } from "@/components/ui/Icon";
import { Paragraflar } from "@/components/ui/Paragraflar";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/Reveal";
import type { VurguBandiVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

const ZEMIN = {
  kirmizi: "bg-primary-aa",
  koyu: "bg-dark",
  acik: "bg-bg",
} as const;

export default function VurguBandi({ veri, blokId }: BlokProps<VurguBandiVeri>) {
  const stil = veri.stil in ZEMIN ? veri.stil : "kirmizi";
  const acik = stil === "acik";
  const baslikId = `${blokId}-baslik`;
  const kelimeler = (veri.vurgu_cumlesi ?? "").split(/\s+/).filter(Boolean);

  return (
    <section
      data-zemin={acik ? "acik" : "koyu"}
      aria-labelledby={baslikId}
      className={cn("relative isolate overflow-hidden py-20 md:py-28", ZEMIN[stil], acik ? "text-ink" : "text-white")}
    >
      <GradientBackdrop varyant={stil === "kirmizi" ? "kirmizi" : acik ? "acik" : "koyu"} izgara />
      {!acik ? <NoiseOverlay /> : null}
      <Container>
        <div className={cn("grid gap-12 lg:grid-cols-12 lg:items-center", !kelimeler.length && "max-w-3xl")}>
          <Reveal className={kelimeler.length ? "lg:col-span-5" : "lg:col-span-12"}>
            <span
              className={cn(
                "flex size-14 items-center justify-center rounded-2xl ring-1",
                stil === "kirmizi" ? "bg-white/15 text-white ring-white/25" : "bg-primary/15 text-primary ring-primary/25",
              )}
            >
              <Icon ad={veri.ikon} boyut={30} />
            </span>
            <h2 id={baslikId} className="mt-6 font-display text-3xl leading-tight font-bold text-zemin-baslik md:text-4xl">
              {veri.baslik}
            </h2>
            {veri.metin ? (
              <Paragraflar
                metin={veri.metin}
                className={cn("mt-5 text-lg leading-relaxed", stil === "kirmizi" ? "text-white/85" : "text-zemin-metin")}
              />
            ) : null}
          </Reveal>

          {kelimeler.length ? (
            <figure className="relative lg:col-span-7">
              <span
                aria-hidden
                className={cn(
                  "absolute -top-14 -left-2 font-display text-[9rem] leading-none select-none",
                  stil === "kirmizi" ? "text-white/20" : "text-primary/25",
                )}
              >
                &ldquo;
              </span>
              <Stagger as="p" aralik={0.05} esik={0.4} className="relative font-display text-3xl leading-[1.2] font-bold text-zemin-baslik sm:text-4xl lg:text-5xl">
                {kelimeler.map((k, i) => (
                  <StaggerItem key={i} as="span" mesafe={16} className="mr-[0.28em] inline-block">
                    {k}
                  </StaggerItem>
                ))}
              </Stagger>
              <Reveal gecikme={0.4}>
                <span
                  aria-hidden
                  className={cn("mt-8 block h-1 w-20 rounded-full", stil === "kirmizi" ? "bg-white" : "bg-primary")}
                />
              </Reveal>
            </figure>
          ) : null}
        </div>
      </Container>
    </section>
  );
}