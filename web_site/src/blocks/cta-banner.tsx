/**
 * cta_banner — CTA Bandı. CONTRACT §8.
 * Koyu veya kırmızı panel; hareketli aurora arka plan + ızgara dokusu.
 */

import { AkilliLink } from "@/components/ui/AkilliLink";
import { ButonGrubu } from "@/components/ui/ButonLink";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { NoiseOverlay } from "@/components/ui/Dekor";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import type { Buton, CtaBannerVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

/** Kırmızı zeminde birincil kırmızı buton kaybolur → beyaz/çerçeveli varyantlar. */
function KirmiziButonlar({ butonlar }: { butonlar: Buton[] }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
      {butonlar.map((b, i) => {
        const ana = b.stil === "birincil" || (i === 0 && b.stil !== "hayalet");
        const link = (
          <AkilliLink
            href={b.href}
            className={cn(
              "inline-flex h-14 items-center justify-center gap-2 rounded-buton px-8 font-semibold transition-all duration-300 ease-eisa active:scale-[0.98]",
              ana
                ? "bg-white text-primary-hover shadow-koyu hover:bg-white/90"
                : "border border-white/40 text-white hover:border-white hover:bg-white/10",
            )}
          >
            {b.etiket}
          </AkilliLink>
        );
        return ana ? <MagneticButton key={i}>{link}</MagneticButton> : <span key={i}>{link}</span>;
      })}
    </div>
  );
}

export default function CtaBanner({ veri, blokId }: BlokProps<CtaBannerVeri>) {
  const kirmizi = veri.stil === "kirmizi";
  const baslikId = `${blokId}-baslik`;
  return (
    <Section arka_plan="acik" aria-labelledby={baslikId}>
      <Reveal>
        <div
          data-zemin="koyu"
          className={cn(
            "relative isolate overflow-hidden rounded-panel px-6 py-16 text-center shadow-koyu sm:px-12 md:py-24",
            kirmizi ? "bg-primary-aa" : "bg-dark",
          )}
        >
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
            <div
              className={cn(
                "absolute -top-1/2 left-[10%] h-[160%] w-[45%] animate-aurora rounded-full blur-3xl",
                kirmizi ? "bg-white/20" : "bg-primary/35",
              )}
            />
            <div
              style={{ animationDelay: "-7s" }}
              className={cn(
                "absolute -bottom-1/2 right-[5%] h-[150%] w-[40%] animate-aurora rounded-full blur-3xl",
                kirmizi ? "bg-[#7a0a0f]/60" : "bg-[#2b6cb0]/25",
              )}
            />
            <div className="doku-izgara absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />
          </div>
          <NoiseOverlay />

          {veri.rozet ? (
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm font-medium text-white">
              <span aria-hidden className="relative flex size-2">
                <span className={cn("absolute inset-0 animate-nabiz rounded-full", kirmizi ? "bg-white" : "bg-primary")} />
                <span className={cn("relative size-2 rounded-full", kirmizi ? "bg-white" : "bg-primary")} />
              </span>
              {veri.rozet}
            </p>
          ) : null}
          <h2 id={baslikId} className="mx-auto max-w-3xl font-display text-4xl leading-[1.08] font-bold text-white md:text-5xl lg:text-6xl">
            {veri.baslik}
          </h2>
          {veri.metin ? (
            <p className={cn("mx-auto mt-6 max-w-2xl text-lg leading-relaxed", kirmizi ? "text-white/85" : "text-white/70")}>
              {veri.metin}
            </p>
          ) : null}
          {veri.butonlar?.length ? (
            <div className="mt-10">
              {kirmizi ? (
                <KirmiziButonlar butonlar={veri.butonlar} />
              ) : (
                <ButonGrubu butonlar={veri.butonlar} boyut="buyuk" className="justify-center" />
              )}
            </div>
          ) : null}
        </div>
      </Reveal>
    </Section>
  );
}