/**
 * gorsel_metin — Görsel + Metin. CONTRACT §8.
 * İki kolon; görsel yoksa dekoratif teknoloji illüstrasyonu çizilir.
 */

import { TeknolojiIllustrasyonu } from "@/components/blocks/TeknolojiIllustrasyonu";
import { ButonGrubu } from "@/components/ui/ButonLink";
import { Icon } from "@/components/ui/Icon";
import { MediaImage } from "@/components/ui/MediaImage";
import { Paragraflar } from "@/components/ui/Paragraflar";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { medyaVarMi } from "@/lib/media";
import type { GorselMetinVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

export default function GorselMetin({ veri, blokId }: BlokProps<GorselMetinVeri>) {
  const solda = veri.gorsel_konumu === "sol";
  const koyu = veri.arka_plan === "koyu";
  const baslikId = `${blokId}-baslik`;

  return (
    <Section arka_plan={veri.arka_plan} aria-labelledby={baslikId}>
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
        <Reveal yon={solda ? "sag" : "sol"} mesafe={40} className={cn(solda ? "lg:order-first" : "lg:order-last")}>
          {medyaVarMi(veri.gorsel) ? (
            <div className="relative aspect-[4/3.3] overflow-hidden rounded-panel shadow-kart-hover">
              <MediaImage
                medya={veri.gorsel}
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-cover transition-transform duration-700 ease-eisa hover:scale-105"
              />
            </div>
          ) : (
            <TeknolojiIllustrasyonu />
          )}
        </Reveal>

        <Reveal>
          {veri.ust_baslik ? (
            <p className="eyebrow mb-4 inline-flex items-center gap-2 text-zemin-vurgu">
              <span aria-hidden className="inline-block size-1.5 rounded-full bg-primary" />
              {veri.ust_baslik}
            </p>
          ) : null}
          <h2 id={baslikId} className="font-display text-3xl leading-tight font-bold text-zemin-baslik sm:text-4xl lg:text-[2.75rem]">
            {veri.baslik}
          </h2>
          <Paragraflar metin={veri.metin} className="mt-6 text-lg leading-relaxed text-zemin-metin" />
          {veri.maddeler?.length ? (
            <Stagger as="ul" className="mt-8 grid gap-3 sm:grid-cols-2">
              {veri.maddeler.map((m, i) => (
                <StaggerItem
                  as="li"
                  key={i}
                  className="flex items-center gap-3 rounded-2xl border border-zemin-cizgi bg-zemin-kart px-4 py-3 text-sm font-medium text-zemin-metin"
                >
                  <span
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-xl",
                      koyu ? "bg-primary/15 text-[#ff5a60]" : "bg-primary-soft text-primary",
                    )}
                  >
                    <Icon ad={m.ikon} boyut={20} />
                  </span>
                  {m.metin}
                </StaggerItem>
              ))}
            </Stagger>
          ) : null}
          <ButonGrubu butonlar={veri.butonlar} className="mt-9" />
        </Reveal>
      </div>
    </Section>
  );
}