/**
 * ozellik_kartlari — Özellik Kartları. CONTRACT §8.
 * Kart ızgarası; fareyi takip eden ışık, ikon hover animasyonu, sıralı belirme.
 */

import { SpotlightKart } from "@/components/blocks/SpotlightKart";
import { Icon } from "@/components/ui/Icon";
import { Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { OzellikKartlariVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

const IZGARA: Record<number, string> = {
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-2 lg:grid-cols-3",
  4: "sm:grid-cols-2 lg:grid-cols-4",
};

export default function OzellikKartlari({ veri, blokId }: BlokProps<OzellikKartlariVeri>) {
  const kartlar = veri.kartlar ?? [];
  if (!kartlar.length) return null;
  const sutun = [2, 3, 4].includes(Number(veri.sutun)) ? Number(veri.sutun) : 3;
  const koyu = veri.arka_plan === "koyu";
  const baslikId = `${blokId}-baslik`;

  return (
    <Section arka_plan={veri.arka_plan} aria-labelledby={veri.baslik ? baslikId : undefined}>
      <SectionHeading ust_baslik={veri.ust_baslik} baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} />
      <Stagger as="ul" className={cn("grid gap-5 md:gap-6", IZGARA[sutun])}>
        {kartlar.map((k, i) => (
          <StaggerItem as="li" key={i} className="h-full">
            <SpotlightKart
              className={cn(
                "h-full rounded-kart border border-zemin-cizgi bg-zemin-kart p-7 transition-[transform,box-shadow,border-color] duration-500 ease-eisa hover:-translate-y-1 hover:border-primary/30 md:p-8",
                koyu ? "hover:shadow-koyu" : "shadow-kart hover:shadow-kart-hover",
              )}
            >
              <span
                aria-hidden
                className="absolute top-7 right-7 font-display text-sm font-semibold text-zemin-soluk/60 tabular-nums"
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                className={cn(
                  "flex size-14 items-center justify-center rounded-2xl ring-1 transition-transform duration-500 ease-eisa group-hover/kart:scale-110 group-hover/kart:-rotate-6",
                  koyu ? "bg-primary/15 text-[#ff5a60] ring-primary/25" : "bg-primary-soft text-primary ring-primary/10",
                )}
              >
                <Icon ad={k.ikon} boyut={28} />
              </span>
              <h3 className="mt-6 font-display text-xl leading-snug font-semibold text-zemin-baslik">{k.baslik}</h3>
              {k.metin ? <p className="mt-3 leading-relaxed text-zemin-soluk">{k.metin}</p> : null}
            </SpotlightKart>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}