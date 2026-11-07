/**
 * sayaclar — Sayaçlar. CONTRACT §8.
 * Görünür olunca sayan büyük rakamlar; ince ayırıcılı panel.
 */

import { AnimatedCounter } from "@/components/ui/AnimatedCounter";
import { Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import type { SayaclarVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

const SUTUN: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-3",
  4: "grid-cols-2 lg:grid-cols-4",
  5: "grid-cols-2 lg:grid-cols-5",
  6: "grid-cols-2 md:grid-cols-3 lg:grid-cols-6",
};

export default function Sayaclar({ veri, blokId }: BlokProps<SayaclarVeri>) {
  const ogeler = veri.ogeler ?? [];
  if (!ogeler.length) return null;
  const baslikId = `${blokId}-baslik`;
  return (
    <Section arka_plan={veri.arka_plan} aria-labelledby={veri.baslik ? baslikId : undefined}>
      {veri.baslik ? (
        <h2 id={baslikId} className="mx-auto mb-12 max-w-3xl text-center font-display text-2xl font-bold text-zemin-baslik md:text-3xl">
          {veri.baslik}
        </h2>
      ) : null}
      <Stagger
        as="dl"
        className={cn(
          "grid gap-px overflow-hidden rounded-panel border border-zemin-cizgi bg-zemin-cizgi shadow-kart",
          SUTUN[Math.min(6, ogeler.length)],
        )}
      >
        {ogeler.map((o, i) => (
          <StaggerItem key={i} className="group relative flex flex-col-reverse items-center bg-zemin-kart px-6 py-10 text-center">
            <dt className="mt-3 text-sm leading-snug font-medium text-zemin-soluk">{o.etiket}</dt>
            <dd className="font-display text-5xl font-bold tracking-tight text-zemin-baslik md:text-6xl">
              <AnimatedCounter deger={Number(o.deger) || 0} onek={o.onek ?? ""} sonek={o.sonek ?? ""} />
            </dd>
            <span
              aria-hidden
              className="absolute top-0 left-1/2 h-0.5 w-10 -translate-x-1/2 rounded-full bg-primary transition-all duration-500 group-hover:w-20"
            />
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}